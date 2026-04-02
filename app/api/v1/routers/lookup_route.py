from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.middleware.middleware import get_current_user, require_scopes
from app.services.lookup_service import LookupService
from app.services.permission_service import PermissionService
from app.cache.redis_client import cache_get, cache_set
from app.api.v1.schemas.position_schema import PositionCreate, PositionResponse, PositionUpdate
from app.api.v1.schemas.lookup_schema import GeographyLookupItemRequest, GeographyLookupItemResponse
from app.models.enum_models import (
    ApprovalStatus,
    BloodTypeEnum,
    Gender,
    MaritalStatusEnum,
    VolunteerStatusEnum,
)

lookup_router = APIRouter(prefix="/lookups", tags=["lookups"])


def _build_enum_items(enum_cls, labels_th: Dict[str, str], labels_en: Optional[Dict[str, str]] = None) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    for member in enum_cls:
        value = member.value
        name_th = labels_th.get(value) or value
        name_en = (labels_en or {}).get(value)
        label = name_th
        items.append(
            {
                "id": value,
                "name_th": name_th,
                "name_en": name_en,
                "label": label,
            }
        )
    return items


async def _require_profile_scope(current_user=Depends(require_scopes({"profile"}))):
    return current_user


async def _require_officer_or_osm(current_user=Depends(require_scopes({"profile"}))):
    if await PermissionService.is_officer(current_user):
        return current_user
    if current_user and current_user.get("user_type") == "osm":
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _normalize_lookup_param(value: Optional[str]) -> Optional[str]:
    """Return None for blank, "null", or "undefined" query values."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    if lowered in {"null", "undefined"}:
        return None
    return stripped


def _normalize_lookup_list(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    normalized: List[str] = []
    for value in values:
        cleaned = _normalize_lookup_param(value)
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized or None


@lookup_router.get("/prefixes")
async def list_prefixes(
    keyword: Optional[str] = Query(None, description="ค้นหาจากชื่อคำนำหน้า"),
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:prefixes:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_prefixes(keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/occupations")
async def list_occupations(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่ออาชีพ"),
    limit: int = Query(200, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:occupations:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_occupations(keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/education-levels")
async def list_education_levels(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อระดับการศึกษา"),
    limit: int = Query(200, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:educations:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_educations(keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/banks")
async def list_banks(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อหรือรหัสธนาคาร"),
    limit: int = Query(200, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:banks:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_banks(keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/osm-by-health-service")
async def list_osm_by_health_service(
    health_service_id: str = Query(..., description="Health service ID"),
    limit: int = Query(200, ge=1, le=500),
    current_user: dict = Depends(_require_profile_scope),
):
    await PermissionService.require_officer(current_user)
    items = await LookupService.list_osm_by_health_service(
        health_service_id=_normalize_lookup_param(health_service_id) or "",
        limit=limit,
    )
    return {
        "status": "success",
        "data": items,
        "errors": [],
        "message": "ดึงข้อมูล OSM สำเร็จ",
    }


@lookup_router.get("/positions")
async def list_positions(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อตำแหน่ง"),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:positions:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_positions(keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/osm-official-positions")
async def list_osm_official_positions(
    keyword: Optional[str] = Query(None, description="ค้นหาตำแหน่งทางการ/ไม่ทางการของ อสม."),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = Query(False, description="รวมรายการที่ปิดใช้งาน"),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:osm-positions:{keyword}:{limit}:{include_inactive}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_osm_official_positions(keyword, limit, include_inactive)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/osm-special-skills")
async def list_osm_special_skills(
    keyword: Optional[str] = Query(None, description="ค้นหาความชำนาญของ อสม."),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = Query(False, description="รวมรายการที่ปิดใช้งาน"),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:osm-skills:{keyword}:{limit}:{include_inactive}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_osm_special_skills(keyword, limit, include_inactive)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/osm-club-positions")
async def list_osm_club_positions(
    keyword: Optional[str] = Query(None, description="ค้นหาตำแหน่งในชมรม อสม."),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = Query(False, description="รวมรายการที่ปิดใช้งาน"),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:osm-club:{keyword}:{limit}:{include_inactive}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_osm_club_positions(keyword, limit, include_inactive)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/osm-training-courses")
async def list_osm_training_courses(
    keyword: Optional[str] = Query(None, description="ค้นหาหลักสูตรอบรมของ อสม."),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = Query(False, description="รวมรายการที่ปิดใช้งาน"),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:osm-courses:{keyword}:{limit}:{include_inactive}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_osm_training_courses(keyword, limit, include_inactive)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.post("/positions", response_model=PositionResponse, status_code=201)
async def create_position(
    payload: PositionCreate,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    item = await LookupService.create_position(payload.dict(), actor_id=current_user.get("user_id"))
    return item


@lookup_router.put("/positions/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: str,
    payload: PositionUpdate,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    item = await LookupService.update_position(position_id, payload.dict(exclude_unset=True), actor_id=current_user.get("user_id"))
    return item


@lookup_router.delete("/positions/{position_id}", status_code=204)
async def delete_position(
    position_id: str,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    await LookupService.delete_position(position_id, actor_id=current_user.get("user_id"))


@lookup_router.get("/position-levels")
async def list_position_levels(
    _: dict = Depends(_require_profile_scope),
):
    cache_key = "lookup:position-levels"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_position_levels()
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/provinces")
async def list_provinces(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อจังหวัด"),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:provinces:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_provinces(keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)  # 24 hours
    return result


@lookup_router.get("/districts")
async def list_districts(
    province_code: str = Query(..., description="รหัสจังหวัด"),
    keyword: Optional[str] = Query(None, description="ค้นหาชื่ออำเภอ"),
    limit: int = Query(150, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:districts:{province_code}:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_districts(province_code, keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/subdistricts")
async def list_subdistricts(
    district_code: str = Query(..., description="รหัสอำเภอ"),
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อตำบล"),
    limit: int = Query(200, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:subdistricts:{district_code}:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_subdistricts(district_code, keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.post("/geography/resolve", response_model=List[GeographyLookupItemResponse])
async def resolve_geography_batch(
    payload: List[GeographyLookupItemRequest] = Body(..., description="รายการจังหวัด/อำเภอ/ตำบลแบบเรียงลำดับ"),
    current_user: dict = Depends(_require_officer_or_osm),
):
    items = await LookupService.resolve_geography_batch([item.model_dump() for item in payload])
    return items


@lookup_router.get("/villages")
async def list_villages(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อหมู่บ้าน"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    health_service_code: Optional[str] = Query(None, description="รหัสหน่วยบริการ"),
    limit: int = Query(200, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    nk = _normalize_lookup_param(keyword)
    npc = _normalize_lookup_param(province_code)
    ndc = _normalize_lookup_param(district_code)
    nsc = _normalize_lookup_param(subdistrict_code)
    nhc = _normalize_lookup_param(health_service_code)
    cache_key = f"lookup:villages:{npc}:{ndc}:{nsc}:{nhc}:{nk}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_villages(
        keyword=nk, province_code=npc, district_code=ndc,
        subdistrict_code=nsc, health_service_code=nhc, limit=limit,
    )
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/health-services")
async def list_health_services(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อหน่วยบริการสุขภาพ"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    provinceCode: Optional[str] = Query(None, include_in_schema=False),
    province: Optional[str] = Query(None, include_in_schema=False),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    districtCode: Optional[str] = Query(None, include_in_schema=False),
    district: Optional[str] = Query(None, include_in_schema=False),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    subdistrictCode: Optional[str] = Query(None, include_in_schema=False),
    subdistrict: Optional[str] = Query(None, include_in_schema=False),
    health_service_type_ids: Optional[List[str]] = Query(
        None,
        description="กรองเฉพาะประเภทหน่วยบริการ (ใส่ key ซ้ำได้หลายค่า)",
    ),
    health_service_type_ids_exclude: Optional[List[str]] = Query(
        None,
        description="ตัดประเภทหน่วยบริการที่ไม่ต้องการ (ใส่ key ซ้ำได้หลายค่า)",
    ),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    resolved_province_code = province_code or provinceCode or province
    resolved_district_code = district_code or districtCode or district
    resolved_subdistrict_code = subdistrict_code or subdistrictCode or subdistrict
    nk = _normalize_lookup_param(keyword)
    npc = _normalize_lookup_param(resolved_province_code)
    ndc = _normalize_lookup_param(resolved_district_code)
    nsc = _normalize_lookup_param(resolved_subdistrict_code)
    ntids = _normalize_lookup_list(health_service_type_ids)
    ntex = _normalize_lookup_list(health_service_type_ids_exclude)
    cache_key = f"lookup:hs:{npc}:{ndc}:{nsc}:{ntids}:{ntex}:{nk}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_health_services(
        keyword=nk, province_code=npc, district_code=ndc,
        subdistrict_code=nsc, health_service_type_ids=ntids,
        health_service_type_ids_exclude=ntex, limit=limit,
    )
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/health-service-types")
async def list_health_service_types(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อประเภทหน่วยบริการสุขภาพ"),
    health_service_type_ids_exclude: Optional[List[str]] = Query(
        None,
        description="ตัดประเภทหน่วยบริการที่ไม่ต้องการ (ใส่ key ซ้ำได้หลายค่า)",
    ),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    nk = _normalize_lookup_param(keyword)
    ntex = _normalize_lookup_list(health_service_type_ids_exclude)
    cache_key = f"lookup:hstypes:{ntex}:{nk}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_health_service_types(
        keyword=nk, health_service_type_ids_exclude=ntex, limit=limit,
    )
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/municipalities")
async def list_municipalities(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อเทศบาล"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    limit: int = Query(100, ge=1, le=300),
    _: dict = Depends(_require_profile_scope),
):
    nk = _normalize_lookup_param(keyword)
    npc = _normalize_lookup_param(province_code)
    ndc = _normalize_lookup_param(district_code)
    nsc = _normalize_lookup_param(subdistrict_code)
    cache_key = f"lookup:municipalities:{npc}:{ndc}:{nsc}:{nk}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_municipalities(
        keyword=nk, province_code=npc, district_code=ndc,
        subdistrict_code=nsc, limit=limit,
    )
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/areas")
async def list_areas(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อเขต"),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:areas:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_areas(keyword, limit)
    for item in items:
        region = item.get("region_code")
        if region:
            item.setdefault("region_name_th", None)
            item.setdefault("region_name_en", None)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/health-areas")
async def list_health_areas(
    keyword: Optional[str] = Query(None, description="ค้นชื่อเขตสุขภาพ"),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(_require_profile_scope),
):
    cache_key = f"lookup:health-areas:{keyword}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items = await LookupService.list_health_areas(keyword, limit)
    result = {"items": items}
    await cache_set(cache_key, result, 86400)
    return result


@lookup_router.get("/genders")
async def list_genders(
    _: dict = Depends(_require_profile_scope),
):
    labels_th = {
        Gender.MALE.value: "ชาย",
        Gender.FEMALE.value: "หญิง",
        Gender.OTHER.value: "อื่นๆ",
    }
    items = _build_enum_items(Gender, labels_th)
    return {"items": items}


@lookup_router.get("/marital-statuses")
async def list_marital_statuses(
    _: dict = Depends(_require_profile_scope),
):
    labels_th = {
        MaritalStatusEnum.SINGLE.value: "โสด",
        MaritalStatusEnum.MARRIED.value: "แต่งงาน",
        MaritalStatusEnum.DIVORCED.value: "หย่าร้าง",
        MaritalStatusEnum.WIDOWED.value: "เป็นหม้าย",
        MaritalStatusEnum.OTHER.value: "อื่นๆ",
    }
    items = _build_enum_items(MaritalStatusEnum, labels_th)
    return {"items": items}


@lookup_router.get("/blood-types")
async def list_blood_types(
    _: dict = Depends(_require_profile_scope),
):
    labels_th = {
        BloodTypeEnum.A.value: "กรุ๊ปเลือด A",
        BloodTypeEnum.B.value: "กรุ๊ปเลือด B",
        BloodTypeEnum.AB.value: "กรุ๊ปเลือด AB",
        BloodTypeEnum.O.value: "กรุ๊ปเลือด O",
        BloodTypeEnum.OTHER.value: "อื่นๆ",
        BloodTypeEnum.UNKNOWN.value: "ไม่ระบุ",
    }
    items = _build_enum_items(BloodTypeEnum, labels_th)
    return {"items": items}


@lookup_router.get("/volunteer-statuses")
async def list_volunteer_statuses(
    _: dict = Depends(_require_profile_scope),
):
    labels_th = {
        VolunteerStatusEnum.ALREADY_VOLUNTEER.value: "เป็นจิตอาสาอยู่แล้ว",
        VolunteerStatusEnum.WANTS_TO_BE_VOLUNTEER.value: "ประสงค์เป็นจิตอาสา",
        VolunteerStatusEnum.NOT_INTERESTED.value: "ไม่ประสงค์เป็นจิตอาสา",
    }
    items = _build_enum_items(VolunteerStatusEnum, labels_th)
    return {"items": items}


@lookup_router.get("/approval-statuses")
async def list_approval_statuses(
    _: dict = Depends(_require_profile_scope),
):
    labels_th = {
        ApprovalStatus.PENDING.value: "รออนุมัติ",
        ApprovalStatus.APPROVED.value: "อนุมัติ",
        ApprovalStatus.REJECTED.value: "ยกเลิก",
        ApprovalStatus.RETIRED.value: "พ้นสภาพ",
    }
    items = _build_enum_items(ApprovalStatus, labels_th)
    return {"items": items}
