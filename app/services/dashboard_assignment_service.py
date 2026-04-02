from __future__ import annotations

from math import ceil
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from tortoise.expressions import Q
from tortoise.functions import Count

from app.models.enum_models import AdministrativeLevelEnum
from app.models.osm_model import OSMProfile
from app.repositories.officer_profile_repository import OfficerProfileRepository
from app.utils.logging_utils import get_logger
from app.utils.officer_hierarchy import OfficerHierarchy, OfficerScope, OfficerScopeError

logger = get_logger(__name__)


class DashboardAssignmentService:
    """Provide dashboard-friendly views over OSM volunteer coverage."""

    @classmethod
    async def list_province_assignments(
        cls,
        *,
        current_user: dict,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        village_no: Optional[str] = None,
        status_filter: Optional[str] = None,
        osm_status_filter: Optional[str] = None,
        approval_status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        order_by: Optional[str] = None,
        sort_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        scope = await cls._resolve_scope(current_user)
        try:
            scope_filter = cls._build_scope_filter(scope) if scope else None
        except OfficerScopeError as exc:
            logger.warning("Invalid officer scope filter: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        status_bool = cls._parse_status(status_filter)
        approval_status = cls._parse_approval_status(approval_status_filter)

        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 200))
        offset = (safe_page - 1) * safe_page_size

        filtered_query = cls._build_queryset(
            scope_filter=scope_filter,
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
            village_no=village_no,
            status_bool=status_bool,
            osm_status_filter=osm_status_filter,
            approval_status=approval_status,
            search=search,
        )

        aggregates = await cls._aggregate_by_province(
            scope_filter=scope_filter,
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
            village_no=village_no,
            status_bool=status_bool,
            osm_status_filter=osm_status_filter,
            approval_status=approval_status,
            search=search,
        )

        total = await filtered_query.count()
        pages = ceil(total / safe_page_size) if total else 0

        items_query = filtered_query.prefetch_related("prefix", "province", "district", "subdistrict")
        order_fields = cls._build_order_fields(order_by=order_by, sort_dir=sort_dir)
        items = (
            await items_query
            .order_by(*order_fields)
            .offset(offset)
            .limit(safe_page_size)
        )

        serialized_items = [cls._serialize_profile(profile) for profile in items]

        return {
            "provinces": aggregates,
            "items": serialized_items,
            "pagination": {
                "page": safe_page,
                "limit": safe_page_size,
                "total": total,
                "pages": pages,
            },
        }

    @classmethod
    def _build_queryset(
        cls,
        *,
        scope_filter: Optional[Q],
        province_code: Optional[str],
        district_code: Optional[str],
        subdistrict_code: Optional[str],
        village_no: Optional[str],
        status_bool: Optional[bool],
        osm_status_filter: Optional[str],
        approval_status: Optional[str],
        search: Optional[str],
    ):
        query = OSMProfile.filter(deleted_at__isnull=True)
        
        # Expose osm_status in downstream serialization; keep query open to all statuses
        # (filtering by status happens only if explicitly requested via status_bool)

        if scope_filter is not None:
            query = query.filter(scope_filter)

        if province_code:
            province_cond = Q(province_id=province_code) | Q(district__province_id=province_code) | Q(
                subdistrict__district__province_id=province_code
            )
            query = query.filter(province_cond)

        if district_code:
            district_cond = Q(district_id=district_code) | Q(subdistrict__district_id=district_code)
            query = query.filter(district_cond)

        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)

        if village_no:
            query = query.filter(village_no=village_no.strip())

        if status_bool is not None:
            query = query.filter(is_active=status_bool)

        if approval_status is not None:
            query = query.filter(approval_status=approval_status)

        if osm_status_filter is not None:
            keyword = osm_status_filter.strip()
            if keyword == "":
                # ไม่ส่ง/ว่าง = ปกติ (osm_status is null or empty)
                query = query.filter(Q(osm_status="") | Q(osm_status__isnull=True))
            else:
                # ส่งค่าใดก็ได้ = พ้นสภาพทั้งหมด (osm_status not null and not empty)
                query = query.filter(~Q(osm_status="") & Q(osm_status__isnull=False))

        if search:
            keyword = search.strip()
            if keyword:
                search_condition = (
                    Q(first_name__icontains=keyword)
                    | Q(last_name__icontains=keyword)
                    | Q(prefix__prefix_name_th__icontains=keyword)
                    | Q(prefix__prefix_name_en__icontains=keyword)
                    | Q(citizen_id__icontains=keyword)
                    | Q(osm_code__icontains=keyword)
                )
                query = query.filter(search_condition)

        return query

    @classmethod
    async def _aggregate_by_province(
        cls,
        *,
        scope_filter: Optional[Q],
        province_code: Optional[str],
        district_code: Optional[str],
        subdistrict_code: Optional[str],
        village_no: Optional[str],
        status_bool: Optional[bool],
        osm_status_filter: Optional[str],
        approval_status: Optional[str],
        search: Optional[str],
    ) -> List[Dict[str, Any]]:
        aggregate_query = cls._build_queryset(
            scope_filter=scope_filter,
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
            village_no=village_no,
            status_bool=status_bool,
            osm_status_filter=osm_status_filter,
            approval_status=approval_status,
            search=search,
        )

        rows = await (
            aggregate_query
            .annotate(osm_total=Count("id"))
            .group_by("province_id", "province__province_name_th", "province__province_name_en")
            .values("province_id", "province__province_name_th", "province__province_name_en", "osm_total")
        )

        aggregates: List[Dict[str, Any]] = []
        for row in rows:
            province_id = row.get("province_id")
            if not province_id:
                continue
            aggregates.append(
                {
                    "provinceCode": province_id,
                    "provinceNameTh": row.get("province__province_name_th"),
                    "provinceNameEn": row.get("province__province_name_en"),
                    "osmCount": int(row.get("osm_total", 0) or 0),
                }
            )

        aggregates.sort(key=lambda item: (-item["osmCount"], item.get("provinceNameTh") or ""))
        return aggregates

    @classmethod
    async def _resolve_scope(cls, current_user: dict) -> Optional[OfficerScope]:
        if current_user.get("user_type") != "officer":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="officer_only")

        officer_id = current_user.get("user_id")
        if not officer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="officer_missing")

        profile = await OfficerProfileRepository.get_officer_by_id(str(officer_id))
        if not profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="officer_profile_not_found")

        try:
            return OfficerHierarchy.scope_from_profile(profile)
        except OfficerScopeError as exc:
            logger.warning("Failed to resolve officer scope: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @staticmethod
    def _build_scope_filter(scope: OfficerScope) -> Optional[Q]:
        level = scope.level
        if level == AdministrativeLevelEnum.COUNTRY:
            return None
        if level == AdministrativeLevelEnum.REGION:
            if not scope.region_code:
                raise OfficerScopeError("region_code required for region level visibility")
            return Q(province__region_id=scope.region_code)
        if level == AdministrativeLevelEnum.AREA:
            if not scope.health_area_id:
                raise OfficerScopeError("health_area_id required for area level visibility")
            return (
                Q(province__health_area_id=scope.health_area_id)
                | Q(district__province__health_area_id=scope.health_area_id)
                | Q(subdistrict__district__province__health_area_id=scope.health_area_id)
            )
        if level == AdministrativeLevelEnum.PROVINCE:
            if not scope.province_id:
                raise OfficerScopeError("province_id required for province level visibility")
            return (
                Q(province_id=scope.province_id)
                | Q(district__province_id=scope.province_id)
                | Q(subdistrict__district__province_id=scope.province_id)
            )
        if level == AdministrativeLevelEnum.DISTRICT:
            if not scope.district_id:
                raise OfficerScopeError("district_id required for district level visibility")
            return Q(district_id=scope.district_id) | Q(subdistrict__district_id=scope.district_id)
        if level == AdministrativeLevelEnum.SUBDISTRICT:
            if not scope.subdistrict_id:
                raise OfficerScopeError("subdistrict_id required for subdistrict level visibility")
            return Q(subdistrict_id=scope.subdistrict_id)
        if level == AdministrativeLevelEnum.VILLAGE:
            if not scope.village_code:
                raise OfficerScopeError("village_code required for village level visibility")
            return Q(village_code=scope.village_code) | Q(village_no=scope.village_code)
        raise OfficerScopeError(f"unsupported officer scope level: {level}")

    @staticmethod
    def _parse_status(raw: Optional[str]) -> Optional[bool]:
        if raw is None:
            return None
        keyword = raw.strip().lower()
        if not keyword:
            return None
        if keyword in {"1", "true", "yes", "active", "ใช้งาน"}:
            return True
        if keyword in {"0", "false", "no", "inactive", "ไม่ใช้งาน"}:
            return False
        return None

    @staticmethod
    def _parse_approval_status(raw: Optional[str]) -> Optional[str]:
        if raw is None:
            return None
        keyword = raw.strip().lower()
        if not keyword:
            return None
        if keyword in {"approved", "อนุมัติ"}:
            return "approved"
        if keyword in {"pending", "รออนุมัติ", "รอ"}:
            return "pending"
        if keyword in {"rejected", "ปฏิเสธ", "ไม่อนุมัติ"}:
            return "rejected"
        return None

    @staticmethod
    def _build_order_fields(*, order_by: Optional[str], sort_dir: Optional[str]) -> List[str]:
        keyword = (order_by or "").strip().lower()
        direction = (sort_dir or "desc").strip().lower()
        descending = direction not in {"asc", "ascending"}

        field_aliases = {
            "id": "id",
            "created_at": "created_at",
            "createdat": "created_at",
            "request_date": "created_at",
            "requestdate": "created_at",
            "updated_at": "updated_at",
            "updatedat": "updated_at",
            "approval_date": "approval_date",
            "approvaldate": "approval_date",
            "approved_date": "approval_date",
            "approveddate": "approval_date",
            "first_name": "first_name",
            "firstname": "first_name",
            "last_name": "last_name",
            "lastname": "last_name",
            "full_name": "first_name",
            "fullname": "first_name",
        }

        target_field = field_aliases.get(keyword)
        if not target_field:
            return ["province_id", "district_id", "subdistrict_id", "first_name", "last_name"]

        prefix = "-" if descending else ""
        order_fields = [f"{prefix}{target_field}"]

        if target_field != "first_name":
            order_fields.append(f"{prefix}first_name")
        if target_field != "last_name":
            order_fields.append(f"{prefix}last_name")

        order_fields.extend(["province_id", "district_id", "subdistrict_id"])
        return order_fields

    @staticmethod
    def _serialize_profile(profile: OSMProfile) -> Dict[str, Any]:
        prefix = getattr(profile, "prefix", None)
        province = getattr(profile, "province", None)
        district = getattr(profile, "district", None)
        subdistrict = getattr(profile, "subdistrict", None)

        prefix_name_th = getattr(prefix, "prefix_name_th", None)
        prefix_name_en = getattr(prefix, "prefix_name_en", None)
        first_name = getattr(profile, "first_name", None)
        last_name = getattr(profile, "last_name", None)

        full_name_parts = [part for part in (prefix_name_th, first_name, last_name) if part]
        full_name = " ".join(full_name_parts) if full_name_parts else None

        volunteer_status = getattr(profile, "volunteer_status", None)
        status_value = volunteer_status.value if hasattr(volunteer_status, "value") else volunteer_status

        return {
            "id": str(profile.id),
            "osmCode": getattr(profile, "osm_code", None),
            "citizenId": getattr(profile, "citizen_id", None),
            "prefixNameTh": prefix_name_th,
            "prefixNameEn": prefix_name_en,
            "firstName": first_name,
            "lastName": last_name,
            "fullName": full_name,
            "provinceCode": getattr(profile, "province_id", None),
            "provinceNameTh": getattr(province, "province_name_th", None) if province else None,
            "districtCode": getattr(profile, "district_id", None),
            "districtNameTh": getattr(district, "district_name_th", None) if district else None,
            "subdistrictCode": getattr(profile, "subdistrict_id", None),
            "subdistrictNameTh": getattr(subdistrict, "subdistrict_name_th", None) if subdistrict else None,
            "villageNo": getattr(profile, "village_no", None),
            "villageName": getattr(profile, "village_name", None),
            "isActive": bool(getattr(profile, "is_active", False)),
            "status": "ใช้งาน" if getattr(profile, "is_active", False) else "ไม่ใช้งาน",
            "osmStatus": getattr(profile, "osm_status", None) if profile.osm_status is not None else "",
            "approvalStatus": getattr(profile, "approval_status", None),
            "volunteerStatus": status_value,
            "createdAt": profile.created_at.isoformat() if getattr(profile, "created_at", None) else None,
            "requestDate": profile.created_at.isoformat() if getattr(profile, "created_at", None) else None,
            "updatedAt": profile.updated_at.isoformat() if getattr(profile, "updated_at", None) else None,
        }
