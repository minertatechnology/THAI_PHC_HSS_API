from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.middleware.middleware import require_scopes
from app.api.v1.schemas.dashboard_schema import (
    DashboardProvinceAssignmentsResponse,
    DashboardSummaryResponse,
)
from app.cache.redis_client import cache_get_raw, cache_set, cache_delete_pattern, get_redis
from app.services.dashboard_assignment_service import DashboardAssignmentService
from app.services.dashboard_summary_service import DashboardSummaryService
from app.utils.scope_enforcement import enforce_scope_on_filters

DASHBOARD_CACHE_TTL = 14400  # 4 hours — dashboard data changes infrequently

# In-process locks to prevent stampede (multiple concurrent requests rebuilding the same cache)
_dashboard_locks: Dict[str, asyncio.Lock] = {}


dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _require_dashboard_scope(current_user=Depends(require_scopes({"profile"}))):
    return current_user


def _merge_code_params(
    *sources: Optional[List[str]],
    min_length: int,
    max_length: int,
    limit: int = 50,
) -> List[str]:
    merged: List[str] = []
    seen: set[str] = set()

    def _add_token(token: str) -> None:
        if len(token) < min_length or len(token) > max_length:
            raise HTTPException(status_code=400, detail="invalid_geography_code_length")
        if token in seen:
            return
        if limit and len(merged) >= limit:
            raise HTTPException(status_code=400, detail="too_many_geography_codes")
        merged.append(token)
        seen.add(token)

    for source in sources:
        if not source:
            continue
        for raw in source:
            if raw is None:
                continue
            chunks = str(raw).split(",")
            for chunk in chunks:
                token = chunk.strip()
                if not token:
                    continue
                _add_token(token)
    return merged


@dashboard_router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    year: Optional[int] = Query(
        None,
        description="ปี พ.ศ. สำหรับการดึงข้อมูล หากไม่ระบุจะใช้ปีปัจจุบัน",
    ),
    provinceCode: Optional[str] = Query(
        None,
        min_length=2,
        max_length=10,
        description="รหัสจังหวัด (ถ้าไม่ระบุจะส่งข้อมูลทุกจังหวัด)",
    ),
    districtCode: Optional[List[str]] = Query(
        None,
        description="รหัสอำเภอสำหรับสรุปข้อมูล (ระบุซ้ำได้ หรือคั่นด้วย ,)",
    ),
    subdistrictCode: Optional[List[str]] = Query(
        None,
        description="รหัสตำบลสำหรับสรุปข้อมูล (ระบุซ้ำได้ หรือคั่นด้วย ,)",
    ),
    search: Optional[str] = Query(
        None,
        description="คำค้นสำหรับจังหวัด (รองรับทั้งรหัส ภาษาไทย และภาษาอังกฤษ)",
    ),
    forceRefresh: bool = Query(
        False,
        description="กำหนด true เพื่อให้ระบบคำนวณสรุปใหม่ก่อนตอบกลับ",
    ),
    provinceAlias: Optional[str] = Query(
        None,
        alias="province",
        min_length=2,
        max_length=10,
        include_in_schema=False,
    ),
    districtAlias: Optional[List[str]] = Query(
        None,
        alias="district",
        include_in_schema=False,
    ),
    subdistrictAlias: Optional[List[str]] = Query(
        None,
        alias="subdistrict",
        include_in_schema=False,
    ),
    current_user: dict = Depends(_require_dashboard_scope),
) -> DashboardSummaryResponse:
    target_year = year

    provinceCode = provinceCode or provinceAlias
    districtCode = _merge_code_params(districtCode, districtAlias, min_length=4, max_length=10)
    subdistrictCode = _merge_code_params(subdistrictCode, subdistrictAlias, min_length=6, max_length=10)

    # ── early cache check (before scope enforcement DB query) ─────────
    # For requests without forceRefresh, try cache with raw params first.
    # This avoids the expensive resolve_officer_context DB call on every hit.
    if not forceRefresh:
        early_key = f"dashboard:{target_year}:{provinceCode}:{','.join(sorted(districtCode))}:{','.join(sorted(subdistrictCode))}:{search}"
        cached = await cache_get_raw(early_key)
        if cached is not None:
            return Response(content=cached, media_type="application/json")
    # ──────────────────────────────────────────────────────────────────

    # ── scope enforcement ──────────────────────────────────────────────
    scope_override = await enforce_scope_on_filters(
        current_user,
        province_code=provinceCode,
        district_code=districtCode[0] if len(districtCode) == 1 else None,
        subdistrict_code=subdistrictCode[0] if len(subdistrictCode) == 1 else None,
    )
    provinceCode = scope_override.province_code
    if scope_override.enforced:
        if scope_override.district_code:
            districtCode = [scope_override.district_code]
        if scope_override.subdistrict_code:
            subdistrictCode = [scope_override.subdistrict_code]
    # ───────────────────────────────────────────────────────────────────

    district_code_single = districtCode[0] if len(districtCode) == 1 else None
    subdistrict_code_single = subdistrictCode[0] if len(subdistrictCode) == 1 else None
    multi_district_requested = len(districtCode) > 1
    multi_subdistrict_requested = len(subdistrictCode) > 1

    if forceRefresh and (multi_district_requested or multi_subdistrict_requested):
        raise HTTPException(status_code=400, detail="force_refresh_requires_single_target")

    if forceRefresh:
        # Clear all dashboard cache when force refresh
        await cache_delete_pattern("dashboard:*")
        try:
            target_year = await DashboardSummaryService.refresh_summary(
                year_buddhist=year,
                province_code=provinceCode,
                district_code=district_code_single,
                subdistrict_code=subdistrict_code_single,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Build cache key from effective params (after scope enforcement)
    cache_key = f"dashboard:{target_year}:{provinceCode}:{','.join(sorted(districtCode))}:{','.join(sorted(subdistrictCode))}:{search}"

    if not forceRefresh:
        cached = await cache_get_raw(cache_key)
        if cached is not None:
            return Response(content=cached, media_type="application/json")

    # Stampede protection: only one coroutine per cache_key computes; others wait & reuse.
    # Layer 1: in-process asyncio.Lock (prevents stampede within a single worker)
    # Layer 2: Redis SETNX lock (prevents stampede across all pods/workers)
    if cache_key not in _dashboard_locks:
        _dashboard_locks[cache_key] = asyncio.Lock()
    async with _dashboard_locks[cache_key]:
        # Double-check after acquiring in-process lock
        if not forceRefresh:
            cached = await cache_get_raw(cache_key)
            if cached is not None:
                return Response(content=cached, media_type="application/json")

        # Try to acquire distributed lock (30s TTL auto-expire as safety net)
        lock_key = f"lock:{cache_key}"
        r = get_redis()
        acquired = False
        if r:
            try:
                acquired = await r.set(
                    f"hss:{lock_key}", "1", nx=True, ex=30,
                )
            except Exception:
                acquired = True  # On Redis error, proceed anyway

        if acquired or not r:
            # We are the leader — compute and cache the result
            try:
                items = await DashboardSummaryService.list_summary(
                    year_buddhist=target_year,
                    province_code=provinceCode,
                    district_code=district_code_single,
                    district_codes=districtCode or None,
                    subdistrict_code=subdistrict_code_single,
                    subdistrict_codes=subdistrictCode or None,
                    refresh_if_missing=not forceRefresh,
                    search=search,
                )
                result = DashboardSummaryResponse(items=items)
                await cache_set(cache_key, result.model_dump(), DASHBOARD_CACHE_TTL)
                return result
            finally:
                if r:
                    try:
                        await r.delete(f"hss:{lock_key}")
                    except Exception:
                        pass
        else:
            # Another pod is computing — wait briefly then use its cached result
            for _ in range(60):  # up to 6 seconds
                await asyncio.sleep(0.1)
                cached = await cache_get_raw(cache_key)
                if cached is not None:
                    return Response(content=cached, media_type="application/json")
            # Fallback: compute ourselves if leader took too long
            items = await DashboardSummaryService.list_summary(
                year_buddhist=target_year,
                province_code=provinceCode,
                district_code=district_code_single,
                district_codes=districtCode or None,
                subdistrict_code=subdistrict_code_single,
                subdistrict_codes=subdistrictCode or None,
                refresh_if_missing=not forceRefresh,
                search=search,
            )
            result = DashboardSummaryResponse(items=items)
            await cache_set(cache_key, result.model_dump(), DASHBOARD_CACHE_TTL)
            return result


@dashboard_router.get("/assignments", response_model=DashboardProvinceAssignmentsResponse)
async def get_dashboard_assignments(
    provinceCode: Optional[str] = Query(
        None,
        min_length=2,
        max_length=10,
        description="รหัสจังหวัดสำหรับกรองข้อมูล",
    ),
    districtCode: Optional[str] = Query(
        None,
        min_length=4,
        max_length=10,
        description="รหัสอำเภอสำหรับกรองข้อมูล",
    ),
    subdistrictCode: Optional[str] = Query(
        None,
        min_length=6,
        max_length=10,
        description="รหัสตำบลสำหรับกรองข้อมูล",
    ),
    villageNo: Optional[str] = Query(
        None,
        description="หมายเลขหมู่บ้าน",
    ),
    status: Optional[str] = Query(
        None,
        description="สถานะการใช้งานของ อสม. (active / inactive)",
    ),
    isActive: Optional[str] = Query(
        None,
        alias="is_active",
        description="alias ของ status สำหรับกรอง is_active",
    ),
    osmStatus: Optional[str] = Query(
        None,
        description="สถานะ อสม. (ไม่ส่ง/ว่าง=ปกติ, ส่งค่าใดก็ได้=พ้นสภาพทั้งหมด)",
        alias="osm_status",
    ),
    approvalStatus: Optional[str] = Query(
        None,
        alias="approval_status",
        description="สถานะการอนุมัติของ อสม. (approved / pending / rejected)",
    ),
    search: Optional[str] = Query(
        None,
        description="คำค้นหาสำหรับชื่อ อสม. หรือรหัสบัตรประชาชน",
    ),
    page: int = Query(1, ge=1, description="หน้าปัจจุบัน"),
    pageSize: int = Query(10, ge=1, le=200, description="จำนวนรายการต่อหน้า"),
    orderBy: Optional[str] = Query(
        None,
        alias="order_by",
        description="ฟิลด์สำหรับจัดลำดับ (id, created_at, request_date, updated_at, approval_date, first_name, last_name)",
    ),
    sortDir: Optional[str] = Query(
        None,
        alias="sort_dir",
        description="ทิศทางการจัดลำดับ (asc หรือ desc)",
    ),
    current_user: dict = Depends(_require_dashboard_scope),
) -> DashboardProvinceAssignmentsResponse:
    effective_status = isActive if isActive is not None else status

    result = await DashboardAssignmentService.list_province_assignments(
        current_user=current_user,
        province_code=provinceCode,
        district_code=districtCode,
        subdistrict_code=subdistrictCode,
        village_no=villageNo,
        status_filter=effective_status,
        osm_status_filter=osmStatus,
        approval_status_filter=approvalStatus,
        search=search,
        page=page,
        page_size=pageSize,
        order_by=orderBy,
        sort_dir=sortDir,
    )
    return DashboardProvinceAssignmentsResponse(**result)
