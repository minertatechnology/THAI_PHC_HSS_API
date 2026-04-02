from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from tortoise.expressions import Q
from tortoise.query_utils import Prefetch
from tortoise.exceptions import IntegrityError

from app.models.personal_model import Prefix, Occupation, Education, Bank
from app.models.position_model import Position
from app.models.administration_model import Municipality
from app.models.geography_model import Province, District, Subdistrict, Area, Region, Village
from app.models.health_model import HealthArea, HealthService, HealthServiceType
from app.models.enum_models import AdministrativeLevelEnum
from app.models.osm_model import (
    OsmOfficialPosition,
    OsmSpecialSkill,
    OsmClubPosition,
    OsmTrainingCourse,
    OSMProfile,
)
from app.cache.redis_client import cache_delete_pattern


_LEVEL_LABELS = {
    AdministrativeLevelEnum.COUNTRY.value: "ระดับประเทศ",
    AdministrativeLevelEnum.REGION.value: "ระดับภาค",
    AdministrativeLevelEnum.AREA.value: "ระดับเขตสุขภาพ",
    AdministrativeLevelEnum.PROVINCE.value: "ระดับจังหวัด",
    AdministrativeLevelEnum.DISTRICT.value: "ระดับอำเภอ",
    AdministrativeLevelEnum.SUBDISTRICT.value: "ระดับตำบล",
    AdministrativeLevelEnum.VILLAGE.value: "ระดับหมู่บ้าน/ชุมชน",
}

_DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE = {
    "7310dd94-0395-48cb-845b-803279a54f6c",
    "96ca3348-49c2-4d89-903b-32939fd1c95c",
    "f464d614-c20e-4391-84a9-4c8edb7982a9",
}


class LookupService:
    """Shared lookup helpers for officer registration and admin utilities."""

    @staticmethod
    def _normalize_geo_name(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        lowered = cleaned.lower()
        if lowered in {"null", "undefined"}:
            return None
        return cleaned

    @staticmethod
    def _normalize_scope_level(value: Any) -> Optional[AdministrativeLevelEnum]:
        if value is None:
            return None
        if isinstance(value, AdministrativeLevelEnum):
            return value
        cleaned = str(value).strip().lower()
        if not cleaned:
            return None
        try:
            return AdministrativeLevelEnum(cleaned)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"invalid_scope_level:{cleaned}",
            ) from exc

    @staticmethod
    def _serialize_position_detail(row: Position) -> Dict[str, Any]:
        scope_level = row.scope_level.value if row.scope_level else None
        return {
            "id": str(row.id),
            "position_name_th": row.position_name_th,
            "position_name_en": row.position_name_en,
            "position_code": row.position_code,
            "scope_level": scope_level,
            "label": LookupService._build_label(row.position_name_th, row.position_name_en) or row.position_code,
            "name_th": row.position_name_th,
            "name_en": row.position_name_en,
            "code": row.position_code,
            "created_by": str(row.created_by) if getattr(row, "created_by", None) else None,
            "updated_by": str(row.updated_by) if getattr(row, "updated_by", None) else None,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "deleted_at": row.deleted_at,
        }

    @staticmethod
    def _build_label(th_name: Optional[str], en_name: Optional[str]) -> str:
        if th_name and en_name:
            return f"{th_name} / {en_name}"
        return th_name or en_name or ""

    @staticmethod
    async def list_prefixes(keyword: Optional[str] = None, limit: int = 50) -> List[Dict[str, object]]:
        query = Prefix.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(prefix_name_th__icontains=keyword) | Q(prefix_name_en__icontains=keyword)
            )
        rows = await query.order_by("prefix_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.prefix_name_th,
                "name_en": row.prefix_name_en,
                "label": LookupService._build_label(row.prefix_name_th, row.prefix_name_en),
            }
            for row in rows
        ]

    @staticmethod
    async def list_occupations(keyword: Optional[str] = None, limit: int = 200) -> List[Dict[str, object]]:
        query = Occupation.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(occupation_name_th__icontains=keyword)
                | Q(occupation_name_en__icontains=keyword)
            )
        rows = await query.order_by("occupation_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.occupation_name_th,
                "name_en": row.occupation_name_en,
                "label": LookupService._build_label(row.occupation_name_th, row.occupation_name_en)
                or str(row.id),
            }
            for row in rows
        ]

    @staticmethod
    async def list_educations(keyword: Optional[str] = None, limit: int = 200) -> List[Dict[str, object]]:
        query = Education.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(education_name_th__icontains=keyword)
                | Q(education_name_en__icontains=keyword)
            )
        rows = await query.order_by("education_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.education_name_th,
                "name_en": row.education_name_en,
                "label": LookupService._build_label(row.education_name_th, row.education_name_en)
                or str(row.id),
            }
            for row in rows
        ]

    @staticmethod
    async def list_osm_by_health_service(
        *,
        health_service_id: str,
        limit: int = 200,
    ) -> List[Dict[str, object]]:
        if not health_service_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_service_id_required")

        rows = await (
            OSMProfile
            .filter(health_service_id=health_service_id, deleted_at__isnull=True)
            .prefetch_related("prefix")
            .order_by("last_name", "first_name")
            .limit(limit)
        )

        items: List[Dict[str, object]] = []
        for row in rows:
            prefix = getattr(row, "prefix", None)
            items.append(
                {
                    "id": str(row.id),
                    "prefix_name_th": getattr(prefix, "prefix_name_th", None),
                    "first_name": row.first_name,
                    "last_name": row.last_name,
                    "phone": row.phone,
                    "email": row.email,
                    "gender": row.gender,
                    "birth_date": row.birth_date.isoformat() if row.birth_date else None,
                }
            )

        return items

    @staticmethod
    async def list_banks(keyword: Optional[str] = None, limit: int = 200) -> List[Dict[str, object]]:
        query = Bank.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(bank_name_th__icontains=keyword)
                | Q(bank_name_en__icontains=keyword)
                | Q(bank_code__icontains=keyword)
            )
        rows = await query.order_by("bank_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "code": row.bank_code,
                "name_th": row.bank_name_th,
                "name_en": row.bank_name_en,
                "label": LookupService._build_label(row.bank_name_th, row.bank_name_en)
                or row.bank_code
                or str(row.id),
            }
            for row in rows
        ]

    @staticmethod
    async def list_positions(keyword: Optional[str] = None, limit: int = 100) -> List[Dict[str, object]]:
        query = Position.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(position_name_th__icontains=keyword)
                | Q(position_name_en__icontains=keyword)
                | Q(position_code__icontains=keyword)
            )
        rows = await query.order_by("position_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.position_name_th,
                "name_en": row.position_name_en,
                "code": row.position_code,
                "scope_level": row.scope_level.value if row.scope_level else None,
                "label": LookupService._build_label(row.position_name_th, row.position_name_en) or row.position_code,
            }
            for row in rows
        ]

    @staticmethod
    async def list_position_levels() -> List[Dict[str, object]]:
        rows = await Position.filter(deleted_at__isnull=True, scope_level__isnull=False).values_list("scope_level", flat=True)
        normalized = [str(item).strip().lower() for item in rows if item]
        if not normalized:
            return []

        counts = Counter(normalized)
        ordered_levels = [level.value for level in AdministrativeLevelEnum if level.value in counts]
        for value in counts:
            if value not in ordered_levels:
                ordered_levels.append(value)

        items: List[Dict[str, object]] = []
        for value in ordered_levels:
            label = _LEVEL_LABELS.get(value) or value.replace("_", " ").title()
            items.append(
                {
                    "id": value,
                    "scope_level": value,
                    "label": label,
                    "position_count": counts.get(value, 0),
                }
            )
        return items

    @staticmethod
    async def create_position(payload: Dict[str, Any], *, actor_id: str) -> Dict[str, Any]:
        actor = str(actor_id or "").strip()
        if not actor:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")
        name_th = str(payload.get("position_name_th") or "").strip()
        if not name_th:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="position_name_th_required")
        code = str(payload.get("position_code") or "").strip()
        if not code:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="position_code_required")

        name_en_raw = payload.get("position_name_en")
        name_en = str(name_en_raw).strip() if isinstance(name_en_raw, str) else None
        scope_level = LookupService._normalize_scope_level(payload.get("scope_level"))

        try:
            row = await Position.create(
                position_name_th=name_th,
                position_name_en=name_en,
                position_code=code,
                scope_level=scope_level,
                created_by=actor,
                updated_by=actor,
            )
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="position_code_exists",
            ) from exc

        await cache_delete_pattern("lookup:positions:*")
        await cache_delete_pattern("lookup:position-levels")
        return LookupService._serialize_position_detail(row)

    @staticmethod
    async def update_position(position_id: str, payload: Dict[str, Any], *, actor_id: str) -> Dict[str, Any]:
        actor = str(actor_id or "").strip()
        if not actor:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")

        row = await Position.filter(id=position_id, deleted_at__isnull=True).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="position_not_found")

        if "position_name_th" in payload:
            name_th = str(payload.get("position_name_th") or "").strip()
            if not name_th:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="position_name_th_required")
            row.position_name_th = name_th
        if "position_name_en" in payload:
            name_en_raw = payload.get("position_name_en")
            row.position_name_en = str(name_en_raw).strip() if isinstance(name_en_raw, str) and name_en_raw.strip() else None
        if "position_code" in payload:
            code = str(payload.get("position_code") or "").strip()
            if not code:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="position_code_required")
            row.position_code = code
        if "scope_level" in payload:
            row.scope_level = LookupService._normalize_scope_level(payload.get("scope_level"))

        row.updated_by = actor

        try:
            await row.save()
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="position_code_exists",
            ) from exc

        await row.refresh_from_db()
        await cache_delete_pattern("lookup:positions:*")
        await cache_delete_pattern("lookup:position-levels")
        return LookupService._serialize_position_detail(row)

    @staticmethod
    async def delete_position(position_id: str, *, actor_id: str) -> None:
        actor = str(actor_id or "").strip()
        if not actor:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")

        row = await Position.filter(id=position_id, deleted_at__isnull=True).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="position_not_found")

        row.deleted_at = datetime.utcnow()
        row.updated_by = actor
        row.updated_at = datetime.utcnow()
        await row.save(update_fields=["deleted_at", "updated_by", "updated_at"])
        await cache_delete_pattern("lookup:positions:*")
        await cache_delete_pattern("lookup:position-levels")

    @staticmethod
    async def list_provinces(keyword: Optional[str] = None, limit: int = 100) -> List[Dict[str, object]]:
        query = Province.filter(deleted_at__isnull=True).prefetch_related("area", "region", "health_area")
        if keyword:
            query = query.filter(
                Q(province_name_th__icontains=keyword)
                | Q(province_name_en__icontains=keyword)
                | Q(province_code__icontains=keyword)
            )
        rows = await query.order_by("province_name_th").limit(limit)
        return [
            {
                "code": row.province_code,
                "id": row.province_code,
                "name_th": row.province_name_th,
                "name_en": row.province_name_en,
                "label": LookupService._build_label(row.province_name_th, row.province_name_en) or row.province_code,
                "area_code": getattr(row.area, "code", None),
                "region_code": getattr(row.region, "code", None),
                "health_area_id": getattr(row.health_area, "code", None),
                "quota": row.quota,
            }
            for row in rows
        ]

    @staticmethod
    async def resolve_geography_batch(items: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
        results: List[Dict[str, Optional[str]]] = []
        for item in items:
            province_name = LookupService._normalize_geo_name(item.get("province"))
            district_name = LookupService._normalize_geo_name(item.get("district"))
            subdistrict_name = LookupService._normalize_geo_name(item.get("subdistrict"))
            health_area_name = LookupService._normalize_geo_name(item.get("health_area"))
            health_service_name_th = LookupService._normalize_geo_name(item.get("health_service_name_th"))

            requested_health_area = None
            requested_health_area_id: Optional[str] = None
            requested_health_area_name_th: Optional[str] = None
            if health_area_name:
                requested_health_area = await HealthArea.filter(deleted_at__isnull=True).filter(
                    Q(health_area_name_th__iexact=health_area_name)
                    | Q(health_area_name_en__iexact=health_area_name)
                    | Q(code__iexact=health_area_name)
                ).first()
                requested_health_area_id = requested_health_area.code if requested_health_area else None
                requested_health_area_name_th = (
                    requested_health_area.health_area_name_th if requested_health_area else None
                )

            province = None
            if province_name:
                province_query = Province.filter(deleted_at__isnull=True).prefetch_related("health_area")
                if requested_health_area_id:
                    province_query = province_query.filter(
                        Q(health_area_id=requested_health_area_id) | Q(area_id=requested_health_area_id)
                    )
                province = await province_query.filter(
                    Q(province_name_th__iexact=province_name)
                    | Q(province_name_en__iexact=province_name)
                    | Q(province_code__iexact=province_name)
                ).first()

            district = None
            if district_name and province:
                district = await District.filter(
                    deleted_at__isnull=True,
                    province_id=province.province_code,
                ).filter(
                    Q(district_name_th__iexact=district_name)
                    | Q(district_name_en__iexact=district_name)
                    | Q(district_code__iexact=district_name)
                ).first()

            subdistrict = None
            if subdistrict_name and district:
                subdistrict = await Subdistrict.filter(
                    deleted_at__isnull=True,
                    district_id=district.district_code,
                ).filter(
                    Q(subdistrict_name_th__iexact=subdistrict_name)
                    | Q(subdistrict_name_en__iexact=subdistrict_name)
                    | Q(subdistrict_code__iexact=subdistrict_name)
                ).first()

            resolved_health_area_id = None
            resolved_health_area_name = None
            if health_area_name:
                resolved_health_area_id = requested_health_area_id
                resolved_health_area_name = requested_health_area_name_th
            elif province:
                resolved_health_area_id = getattr(province, "health_area_id", None)
                resolved_health_area_name = getattr(
                    getattr(province, "health_area", None),
                    "health_area_name_th",
                    None,
                )
                if not resolved_health_area_id:
                    inferred = await HealthArea.filter(
                        deleted_at__isnull=True,
                        code=getattr(province, "area_id", None),
                    ).first()
                    resolved_health_area_id = inferred.code if inferred else None
                    resolved_health_area_name = inferred.health_area_name_th if inferred else None

            health_services: Optional[List[Dict[str, object]]] = None
            if subdistrict:
                hs_query = HealthService.filter(
                    deleted_at__isnull=True,
                    subdistrict_id=subdistrict.subdistrict_code,
                ).exclude(
                    health_service_type_id__in=list(_DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE),
                )
                if health_service_name_th:
                    hs_query = hs_query.filter(
                        Q(health_service_name_th__iexact=health_service_name_th)
                    )
                hs_rows = await hs_query.order_by("health_service_name_th")
                if hs_rows:
                    health_services = [
                        {
                            "health_service_code": row.health_service_code,
                            "health_service_name_th": row.health_service_name_th,
                            "health_service_name_en": row.health_service_name_en,
                        }
                        for row in hs_rows
                    ]

            results.append(
                {
                    "province_id": province.province_code if province else None,
                    "province": province.province_name_th if province else None,
                    "district_id": district.district_code if district else None,
                    "district": district.district_name_th if district else None,
                    "subdistrict_id": subdistrict.subdistrict_code if subdistrict else None,
                    "subdistrict": subdistrict.subdistrict_name_th if subdistrict else None,
                    "health_area_id": resolved_health_area_id,
                    "health_area": resolved_health_area_name,
                    "health_services": health_services,
                }
            )
        return results

    @staticmethod
    async def list_districts(province_code: str, keyword: Optional[str] = None, limit: int = 150) -> List[Dict[str, object]]:
        query = District.filter(deleted_at__isnull=True, province_id=province_code).prefetch_related("province")
        if keyword:
            query = query.filter(
                Q(district_name_th__icontains=keyword)
                | Q(district_name_en__icontains=keyword)
                | Q(district_code__icontains=keyword)
            )
        rows = await query.order_by("district_name_th").limit(limit)
        return [
            {
                "code": row.district_code,
                "id": row.district_code,
                "name_th": row.district_name_th,
                "name_en": row.district_name_en,
                "label": LookupService._build_label(row.district_name_th, row.district_name_en) or row.district_code,
                "province_code": getattr(row.province, "province_code", None),
                "province_name_th": getattr(row.province, "province_name_th", None),
                "province_name_en": getattr(row.province, "province_name_en", None),
            }
            for row in rows
        ]

    @staticmethod
    async def list_subdistricts(district_code: str, keyword: Optional[str] = None, limit: int = 200) -> List[Dict[str, object]]:
        query = Subdistrict.filter(deleted_at__isnull=True, district_id=district_code).prefetch_related("district")
        if keyword:
            query = query.filter(
                Q(subdistrict_name_th__icontains=keyword)
                | Q(subdistrict_name_en__icontains=keyword)
                | Q(subdistrict_code__icontains=keyword)
            )
        rows = await query.order_by("subdistrict_name_th").limit(limit)
        items: List[Dict[str, object]] = []
        for row in rows:
            district = getattr(row, "district", None)
            province = getattr(district, "province", None) if district else None
            items.append(
                {
                    "code": row.subdistrict_code,
                    "id": row.subdistrict_code,
                    "name_th": row.subdistrict_name_th,
                    "name_en": row.subdistrict_name_en,
                    "postal_code": row.postal_code,
                    "label": LookupService._build_label(row.subdistrict_name_th, row.subdistrict_name_en)
                    or row.subdistrict_code,
                    "district_code": getattr(district, "district_code", None),
                    "district_name_th": getattr(district, "district_name_th", None),
                    "district_name_en": getattr(district, "district_name_en", None),
                    "province_code": getattr(province, "province_code", None),
                    "province_name_th": getattr(province, "province_name_th", None),
                    "province_name_en": getattr(province, "province_name_en", None),
                }
            )
        return items

    @staticmethod
    async def list_villages(
        *,
        keyword: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        health_service_code: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, object]]:
        query = Village.filter(deleted_at__isnull=True).prefetch_related(
            "subdistrict__district__province",
            "health_service",
        )
        if keyword:
            query = query.filter(
                Q(village_name_th__icontains=keyword)
                | Q(village_name_en__icontains=keyword)
                | Q(village_code__icontains=keyword)
                | Q(village_code_8digit__icontains=keyword)
            )
        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)
        if district_code:
            query = query.filter(subdistrict__district_id=district_code)
        if province_code:
            query = query.filter(subdistrict__district__province_id=province_code)
        if health_service_code:
            query = query.filter(health_service_id=health_service_code)

        rows = await query.order_by("village_name_th").limit(limit)
        items: List[Dict[str, object]] = []
        for row in rows:
            subdistrict = getattr(row, "subdistrict", None)
            district = getattr(subdistrict, "district", None) if subdistrict else None
            province = getattr(district, "province", None) if district else None
            health_service = getattr(row, "health_service", None)
            items.append(
                {
                    "code": row.village_code,
                    "village_code_8digit": row.village_code_8digit,
                    "id": row.village_code,
                    "name_th": row.village_name_th,
                    "name_en": row.village_name_en,
                    "village_no": row.village_no,
                    "metro_status": row.metro_status,
                    "label": LookupService._build_label(row.village_name_th, row.village_name_en)
                    or row.village_code,
                    "subdistrict_code": getattr(subdistrict, "subdistrict_code", None),
                    "subdistrict_name_th": getattr(subdistrict, "subdistrict_name_th", None),
                    "subdistrict_name_en": getattr(subdistrict, "subdistrict_name_en", None),
                    "district_code": getattr(district, "district_code", None),
                    "district_name_th": getattr(district, "district_name_th", None),
                    "district_name_en": getattr(district, "district_name_en", None),
                    "province_code": getattr(province, "province_code", None),
                    "province_name_th": getattr(province, "province_name_th", None),
                    "province_name_en": getattr(province, "province_name_en", None),
                    "health_service_code": getattr(health_service, "health_service_code", None),
                    "health_service_name_th": getattr(health_service, "health_service_name_th", None),
                    "health_service_name_en": getattr(health_service, "health_service_name_en", None),
                }
            )
        return items

    @staticmethod
    async def list_health_services(
        *,
        keyword: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        health_service_type_ids: Optional[List[str]] = None,
        health_service_type_ids_exclude: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, object]]:
        if health_service_type_ids_exclude:
            health_service_type_ids_exclude = list({
                *health_service_type_ids_exclude,
                *_DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE,
            })
        else:
            health_service_type_ids_exclude = list(_DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE)
        query = HealthService.filter(deleted_at__isnull=True).prefetch_related(
            "health_service_type",
            "province",
            "district",
            "subdistrict",
        )
        if keyword:
            query = query.filter(
                Q(health_service_name_th__icontains=keyword)
                | Q(health_service_name_en__icontains=keyword)
                | Q(health_service_code__icontains=keyword)
                | Q(legacy_5digit_code__icontains=keyword)
                | Q(legacy_9digit_code__icontains=keyword)
            )
        if province_code:
            query = query.filter(province_id=province_code)
        if district_code:
            query = query.filter(district_id=district_code)
        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)
        if health_service_type_ids:
            query = query.filter(health_service_type_id__in=health_service_type_ids)
        if health_service_type_ids_exclude:
            query = query.exclude(health_service_type_id__in=health_service_type_ids_exclude)

        rows = await query.order_by("health_service_name_th").limit(limit)
        items: List[Dict[str, object]] = []
        for row in rows:
            hs_type: Optional[HealthServiceType] = getattr(row, "health_service_type", None)
            province = getattr(row, "province", None)
            district = getattr(row, "district", None)
            subdistrict = getattr(row, "subdistrict", None)
            items.append(
                {
                    "code": row.health_service_code,
                    "id": row.health_service_code,
                    "name_th": row.health_service_name_th,
                    "name_en": row.health_service_name_en,
                    "label": LookupService._build_label(
                        row.health_service_name_th,
                        row.health_service_name_en,
                    )
                    or row.health_service_code,
                    "legacy_5digit_code": row.legacy_5digit_code,
                    "legacy_9digit_code": row.legacy_9digit_code,
                    "updated_at": row.updated_at,
                    "village_no": row.village_no,
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "health_service_type": {
                        "id": str(hs_type.id) if getattr(hs_type, "id", None) else None,
                        "name_th": getattr(hs_type, "health_service_type_name_th", None),
                        "name_en": getattr(hs_type, "health_service_type_name_en", None),
                    }
                    if hs_type
                    else None,
                    "province": {
                        "code": getattr(province, "province_code", None),
                        "name_th": getattr(province, "province_name_th", None),
                        "name_en": getattr(province, "province_name_en", None),
                    }
                    if province
                    else None,
                    "district": {
                        "code": getattr(district, "district_code", None),
                        "name_th": getattr(district, "district_name_th", None),
                        "name_en": getattr(district, "district_name_en", None),
                    }
                    if district
                    else None,
                    "subdistrict": {
                        "code": getattr(subdistrict, "subdistrict_code", None),
                        "name_th": getattr(subdistrict, "subdistrict_name_th", None),
                        "name_en": getattr(subdistrict, "subdistrict_name_en", None),
                    }
                    if subdistrict
                    else None,
                }
            )
        return items

    @staticmethod
    async def list_health_service_types(
        *,
        keyword: Optional[str] = None,
        health_service_type_ids_exclude: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, object]]:
        query = HealthServiceType.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(health_service_type_name_th__icontains=keyword)
                | Q(health_service_type_name_en__icontains=keyword)
            )

        if health_service_type_ids_exclude:
            exclude_ids = [value for value in health_service_type_ids_exclude if value]
            if exclude_ids:
                query = query.exclude(id__in=exclude_ids)

        rows = await query.order_by("health_service_type_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.health_service_type_name_th,
                "name_en": row.health_service_type_name_en,
                "label": LookupService._build_label(
                    row.health_service_type_name_th,
                    row.health_service_type_name_en,
                )
                or str(row.id),
            }
            for row in rows
        ]

    @staticmethod
    async def list_municipalities(
        *,
        keyword: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, object]]:
        query = Municipality.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(municipality_name_th__icontains=keyword)
                | Q(municipality_name_en__icontains=keyword)
            )
        if province_code:
            query = query.filter(province_id=province_code)
        if district_code:
            query = query.filter(district_id=district_code)
        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)
        rows = await query.order_by("municipality_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.municipality_name_th,
                "name_en": row.municipality_name_en,
                "label": LookupService._build_label(row.municipality_name_th, row.municipality_name_en) or str(row.id),
                "province_code": row.province_id,
                "district_code": row.district_id,
                "subdistrict_code": row.subdistrict_id,
            }
            for row in rows
        ]

    @staticmethod
    async def list_areas(keyword: Optional[str] = None, limit: int = 100) -> List[Dict[str, object]]:
        query = Area.filter(deleted_at__isnull=True).prefetch_related("region")
        if keyword:
            query = query.filter(
                Q(area_name_th__icontains=keyword)
                | Q(area_name_en__icontains=keyword)
                | Q(code__icontains=keyword)
            )
        rows = await query.order_by("area_name_th").limit(limit)
        return [
            {
                "code": row.code,
                "id": row.code,
                "name_th": row.area_name_th,
                "name_en": row.area_name_en,
                "label": LookupService._build_label(row.area_name_th, row.area_name_en) or row.code,
                "region_code": getattr(row.region, "code", None),
            }
            for row in rows
        ]

    @staticmethod
    async def list_regions(keyword: Optional[str] = None, limit: int = 20) -> List[Dict[str, object]]:
        query = Region.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(region_name_th__icontains=keyword)
                | Q(region_name_en__icontains=keyword)
                | Q(code__icontains=keyword)
            )
        rows = await query.order_by("region_name_th").limit(limit)
        return [
            {
                "code": row.code,
                "id": row.code,
                "name_th": row.region_name_th,
                "name_en": row.region_name_en,
                "label": LookupService._build_label(row.region_name_th, row.region_name_en) or row.code,
            }
            for row in rows
        ]

    @staticmethod
    async def list_health_areas(keyword: Optional[str] = None, limit: int = 100) -> List[Dict[str, object]]:
        query = HealthArea.filter(deleted_at__isnull=True).prefetch_related(
            Prefetch(
                "provinces",
                queryset=Province.filter(deleted_at__isnull=True).order_by("province_name_th"),
            )
        )
        if keyword:
            query = query.filter(
                Q(health_area_name_th__icontains=keyword)
                | Q(health_area_name_en__icontains=keyword)
                | Q(code__icontains=keyword)
            )
        rows = await query.order_by("health_area_name_th").limit(limit)

        items: List[Dict[str, object]] = []
        for row in rows:
            provinces = [
                {
                    "code": province.province_code,
                    "id": province.province_code,
                    "name_th": province.province_name_th,
                    "name_en": province.province_name_en,
                    "label": LookupService._build_label(province.province_name_th, province.province_name_en)
                    or province.province_code,
                }
                for province in getattr(row, "provinces", [])
            ]

            items.append(
                {
                    "code": row.code,
                    "id": row.code,
                    "name_th": row.health_area_name_th,
                    "name_en": row.health_area_name_en,
                    "label": LookupService._build_label(row.health_area_name_th, row.health_area_name_en)
                    or row.code,
                    "province_count": len(provinces),
                    "provinces": provinces,
                }
            )

        return items

    @staticmethod
    async def list_osm_official_positions(
        keyword: Optional[str] = None,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[Dict[str, object]]:
        query = OsmOfficialPosition.filter(deleted_at__isnull=True)
        if not include_inactive:
            query = query.filter(is_active=True)
        if keyword:
            filters = (
                Q(position_name_th__icontains=keyword)
                | Q(position_name_en__icontains=keyword)
            )
            if keyword.isdigit():
                filters |= Q(legacy_code=int(keyword))
            query = query.filter(filters)
        rows = await query.order_by("position_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.position_name_th,
                "name_en": row.position_name_en,
                "legacy_code": row.legacy_code,
                "position_level": row.position_level,
                "is_active": row.is_active,
                "label": LookupService._build_label(row.position_name_th, row.position_name_en)
                or (str(row.legacy_code) if row.legacy_code is not None else None)
                or str(row.id),
            }
            for row in rows
        ]

    @staticmethod
    async def list_osm_special_skills(
        keyword: Optional[str] = None,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[Dict[str, object]]:
        query = OsmSpecialSkill.filter(deleted_at__isnull=True)
        if not include_inactive:
            query = query.filter(is_active=True)
        if keyword:
            filters = (
                Q(skill_name_th__icontains=keyword)
                | Q(skill_name_en__icontains=keyword)
            )
            if keyword.isdigit():
                filters |= Q(legacy_code=int(keyword))
            query = query.filter(filters)
        rows = await query.order_by("skill_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.skill_name_th,
                "name_en": row.skill_name_en,
                "legacy_code": row.legacy_code,
                "is_active": row.is_active,
                "label": LookupService._build_label(row.skill_name_th, row.skill_name_en)
                or (str(row.legacy_code) if row.legacy_code is not None else None)
                or str(row.id),
            }
            for row in rows
        ]

    @staticmethod
    async def list_osm_club_positions(
        keyword: Optional[str] = None,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[Dict[str, object]]:
        query = OsmClubPosition.filter(deleted_at__isnull=True)
        if not include_inactive:
            query = query.filter(is_active=True)
        if keyword:
            filters = (
                Q(position_name_th__icontains=keyword)
                | Q(position_name_en__icontains=keyword)
            )
            if keyword.isdigit():
                filters |= Q(legacy_code=int(keyword))
            query = query.filter(filters)
        rows = await query.order_by("position_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.position_name_th,
                "name_en": row.position_name_en,
                "legacy_code": row.legacy_code,
                "is_active": row.is_active,
                "label": LookupService._build_label(row.position_name_th, row.position_name_en)
                or (str(row.legacy_code) if row.legacy_code is not None else None)
                or str(row.id),
            }
            for row in rows
        ]

    @staticmethod
    async def list_osm_training_courses(
        keyword: Optional[str] = None,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[Dict[str, object]]:
        query = OsmTrainingCourse.filter(deleted_at__isnull=True)
        if not include_inactive:
            query = query.filter(is_active=True)
        if keyword:
            filters = (
                Q(course_name_th__icontains=keyword)
                | Q(course_name_en__icontains=keyword)
            )
            if keyword.isdigit():
                filters |= Q(legacy_code=int(keyword))
            query = query.filter(filters)
        rows = await query.order_by("course_name_th").limit(limit)
        return [
            {
                "id": str(row.id),
                "name_th": row.course_name_th,
                "name_en": row.course_name_en,
                "legacy_code": row.legacy_code,
                "is_active": row.is_active,
                "label": LookupService._build_label(row.course_name_th, row.course_name_en)
                or (str(row.legacy_code) if row.legacy_code is not None else None)
                or str(row.id),
            }
            for row in rows
        ]
