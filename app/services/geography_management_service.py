from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from tortoise.expressions import Q
from tortoise.query_utils import Prefetch

from app.models.administration_model import Municipality, MunicipalityType
from app.models.geography_model import (
    Area,
    District,
    Province,
    Region,
    Subdistrict,
    Village,
)
from app.models.health_model import HealthArea, HealthService, HealthServiceType
from app.cache.redis_client import cache_delete_pattern


class GeographyManagementService:
    """Provide CRUD helpers for geo dictionaries restricted to officer users."""

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    async def _invalidate_geo_cache(*lookup_patterns: str) -> None:
        """Invalidate lookup + dashboard caches after geo mutations."""
        for pattern in lookup_patterns:
            await cache_delete_pattern(pattern)
        await cache_delete_pattern("dashboard:*")

    @staticmethod
    def _normalize_code(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _parse_actor(actor_id: Optional[str]) -> Optional[UUID]:
        if actor_id is None:
            return None
        try:
            return UUID(str(actor_id))
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_actor_id") from exc

    @staticmethod
    async def _ensure_region(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            return
        exists = await Region.filter(code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="region_not_found")

    @staticmethod
    async def _ensure_area(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            return
        exists = await Area.filter(code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="area_not_found")

    @staticmethod
    async def _ensure_health_area(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            return
        exists = await HealthArea.filter(code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_area_not_found")

    @staticmethod
    async def _ensure_health_service_type(value: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(value)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_service_type_required")
        exists = await HealthServiceType.filter(id=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_service_type_not_found")

    @staticmethod
    async def _ensure_province(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            return
        exists = await Province.filter(province_code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="province_not_found")

    @staticmethod
    async def _ensure_district(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            return
        exists = await District.filter(district_code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="district_not_found")

    @staticmethod
    async def _ensure_subdistrict(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            return
        exists = await Subdistrict.filter(subdistrict_code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subdistrict_not_found")

    @staticmethod
    async def _ensure_municipality_type(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="municipality_type_required")
        exists = await MunicipalityType.filter(code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="municipality_type_not_found")

    @staticmethod
    async def _ensure_health_service(code: Optional[str]) -> None:
        normalized = GeographyManagementService._normalize_code(code)
        if not normalized:
            return
        exists = await HealthService.filter(health_service_code=normalized, deleted_at__isnull=True).exists()
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_service_not_found")

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _serialize_region(region: Optional[Region]) -> Optional[Dict[str, object]]:
        if not region:
            return None
        return {
            "code": region.code,
            "name_th": region.region_name_th,
            "name_en": region.region_name_en,
        }

    @staticmethod
    def _serialize_area(area: Optional[Area]) -> Optional[Dict[str, object]]:
        if not area:
            return None
        return {
            "code": area.code,
            "name_th": area.area_name_th,
            "name_en": area.area_name_en,
        }

    @staticmethod
    def _serialize_health_area(area: Optional[HealthArea]) -> Optional[Dict[str, object]]:
        if not area:
            return None
        return {
            "code": area.code,
            "name_th": area.health_area_name_th,
            "name_en": area.health_area_name_en,
        }

    @staticmethod
    def _serialize_province(province: Province) -> Dict[str, object]:
        area = getattr(province, "area", None)
        region = getattr(province, "region", None)
        health_area = getattr(province, "health_area", None)
        return {
            "province_code": province.province_code,
            "province_name_th": province.province_name_th,
            "province_name_en": province.province_name_en,
            "latitude": province.latitude,
            "longitude": province.longitude,
            "quota": province.quota,
            "area": GeographyManagementService._serialize_area(area),
            "region": GeographyManagementService._serialize_region(region),
            "health_area": GeographyManagementService._serialize_health_area(health_area),
            "created_at": province.created_at,
            "updated_at": province.updated_at,
        }

    @staticmethod
    def _serialize_district(district: District) -> Dict[str, object]:
        province = getattr(district, "province", None)
        return {
            "district_code": district.district_code,
            "district_name_th": district.district_name_th,
            "district_name_en": district.district_name_en,
            "latitude": district.latitude,
            "longitude": district.longitude,
            "province": {
                "province_code": getattr(province, "province_code", None),
                "province_name_th": getattr(province, "province_name_th", None),
                "province_name_en": getattr(province, "province_name_en", None),
            }
            if province
            else None,
            "created_at": district.created_at,
            "updated_at": district.updated_at,
        }

    @staticmethod
    def _serialize_subdistrict(subdistrict: Subdistrict) -> Dict[str, object]:
        district = getattr(subdistrict, "district", None)
        province = getattr(district, "province", None) if district else None
        return {
            "subdistrict_code": subdistrict.subdistrict_code,
            "subdistrict_name_th": subdistrict.subdistrict_name_th,
            "subdistrict_name_en": subdistrict.subdistrict_name_en,
            "postal_code": subdistrict.postal_code,
            "latitude": subdistrict.latitude,
            "longitude": subdistrict.longitude,
            "district": {
                "district_code": getattr(district, "district_code", None),
                "district_name_th": getattr(district, "district_name_th", None),
                "district_name_en": getattr(district, "district_name_en", None),
            }
            if district
            else None,
            "province": {
                "province_code": getattr(province, "province_code", None),
                "province_name_th": getattr(province, "province_name_th", None),
                "province_name_en": getattr(province, "province_name_en", None),
            }
            if province
            else None,
            "created_at": subdistrict.created_at,
            "updated_at": subdistrict.updated_at,
        }

    @staticmethod
    def _serialize_village(village: Village) -> Dict[str, object]:
        subdistrict = getattr(village, "subdistrict", None)
        district = getattr(subdistrict, "district", None) if subdistrict else None
        province = getattr(district, "province", None) if district else None
        health_service = getattr(village, "health_service", None)
        return {
            "village_code": village.village_code,
            "village_code_8digit": village.village_code_8digit,
            "village_no": village.village_no,
            "village_name_th": village.village_name_th,
            "village_name_en": village.village_name_en,
            "metro_status": village.metro_status,
            "government_id": village.government_id,
            "latitude": village.latitude,
            "longitude": village.longitude,
            "external_url": village.external_url,
            "subdistrict": {
                "subdistrict_code": getattr(subdistrict, "subdistrict_code", None),
                "subdistrict_name_th": getattr(subdistrict, "subdistrict_name_th", None),
                "subdistrict_name_en": getattr(subdistrict, "subdistrict_name_en", None),
            }
            if subdistrict
            else None,
            "district": {
                "district_code": getattr(district, "district_code", None),
                "district_name_th": getattr(district, "district_name_th", None),
                "district_name_en": getattr(district, "district_name_en", None),
            }
            if district
            else None,
            "province": {
                "province_code": getattr(province, "province_code", None),
                "province_name_th": getattr(province, "province_name_th", None),
                "province_name_en": getattr(province, "province_name_en", None),
            }
            if province
            else None,
            "health_service": {
                "health_service_code": getattr(health_service, "health_service_code", None),
                "health_service_name_th": getattr(health_service, "health_service_name_th", None),
                "health_service_name_en": getattr(health_service, "health_service_name_en", None),
            }
            if health_service
            else None,
            "created_at": village.created_at,
            "updated_at": village.updated_at,
        }

    @staticmethod
    def _serialize_health_service(service: HealthService) -> Dict[str, object]:
        health_service_type = getattr(service, "health_service_type", None)
        province = getattr(service, "province", None)
        district = getattr(service, "district", None)
        subdistrict = getattr(service, "subdistrict", None)
        return {
            "health_service_code": service.health_service_code,
            "health_service_name_th": service.health_service_name_th,
            "health_service_name_en": service.health_service_name_en,
            "legacy_5digit_code": service.legacy_5digit_code,
            "legacy_9digit_code": service.legacy_9digit_code,
            "village_no": service.village_no,
            "latitude": service.latitude,
            "longitude": service.longitude,
            "health_service_type": {
                "id": str(getattr(health_service_type, "id", "")) or None,
                "name_th": getattr(health_service_type, "health_service_type_name_th", None),
                "name_en": getattr(health_service_type, "health_service_type_name_en", None),
            }
            if health_service_type
            else None,
            "province": {
                "province_code": getattr(province, "province_code", None),
                "province_name_th": getattr(province, "province_name_th", None),
                "province_name_en": getattr(province, "province_name_en", None),
            }
            if province
            else None,
            "district": {
                "district_code": getattr(district, "district_code", None),
                "district_name_th": getattr(district, "district_name_th", None),
                "district_name_en": getattr(district, "district_name_en", None),
            }
            if district
            else None,
            "subdistrict": {
                "subdistrict_code": getattr(subdistrict, "subdistrict_code", None),
                "subdistrict_name_th": getattr(subdistrict, "subdistrict_name_th", None),
                "subdistrict_name_en": getattr(subdistrict, "subdistrict_name_en", None),
            }
            if subdistrict
            else None,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "deleted_at": service.deleted_at,
        }

    @staticmethod
    def _serialize_municipality(municipality: Municipality) -> Dict[str, object]:
        municipality_type = getattr(municipality, "municipality_type", None)
        province = getattr(municipality, "province", None)
        district = getattr(municipality, "district", None)
        subdistrict = getattr(municipality, "subdistrict", None)
        return {
            "id": str(municipality.id),
            "municipality_name_th": municipality.municipality_name_th,
            "municipality_name_en": municipality.municipality_name_en,
            "municipality_type": {
                "code": getattr(municipality_type, "code", None),
                "name_th": getattr(municipality_type, "municipality_type_name_th", None),
                "name_en": getattr(municipality_type, "municipality_type_name_en", None),
            }
            if municipality_type
            else None,
            "province": {
                "province_code": getattr(province, "province_code", None),
                "province_name_th": getattr(province, "province_name_th", None),
                "province_name_en": getattr(province, "province_name_en", None),
            }
            if province
            else None,
            "district": {
                "district_code": getattr(district, "district_code", None),
                "district_name_th": getattr(district, "district_name_th", None),
                "district_name_en": getattr(district, "district_name_en", None),
            }
            if district
            else None,
            "subdistrict": {
                "subdistrict_code": getattr(subdistrict, "subdistrict_code", None),
                "subdistrict_name_th": getattr(subdistrict, "subdistrict_name_th", None),
                "subdistrict_name_en": getattr(subdistrict, "subdistrict_name_en", None),
            }
            if subdistrict
            else None,
            "created_at": municipality.created_at,
            "updated_at": municipality.updated_at,
        }

    @staticmethod
    def _serialize_health_area_with_provinces(area: HealthArea) -> Dict[str, object]:
        province_list: List[Dict[str, object]] = []
        for province in getattr(area, "provinces", []) or []:
            if getattr(province, "deleted_at", None) is not None:
                continue
            province_list.append(
                {
                    "province_code": province.province_code,
                    "province_name_th": province.province_name_th,
                    "province_name_en": province.province_name_en,
                    "quota": getattr(province, "quota", 0),
                }
            )
        return {
            "code": area.code,
            "health_area_name_th": area.health_area_name_th,
            "health_area_name_en": area.health_area_name_en,
            "province_count": len(province_list),
            "provinces": province_list,
            "created_at": area.created_at,
            "updated_at": area.updated_at,
        }

    # ------------------------------------------------------------------
    # Province management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_provinces(
        *,
        keyword: Optional[str],
        area_code: Optional[str],
        region_code: Optional[str],
        health_area_code: Optional[str],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = Province.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(province_name_th__icontains=keyword)
                | Q(province_name_en__icontains=keyword)
                | Q(province_code__icontains=keyword)
            )
        if area_code:
            query = query.filter(area_id=area_code)
        if region_code:
            query = query.filter(region_id=region_code)
        if health_area_code:
            query = query.filter(health_area_id=health_area_code)
        total = await query.count()
        rows = (
            await query.order_by("province_name_th")
            .offset(offset)
            .limit(limit)
            .prefetch_related("area", "region", "health_area")
        )
        items = [GeographyManagementService._serialize_province(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_province(province_code: str) -> Dict[str, object]:
        province = (
            await Province.filter(province_code=province_code, deleted_at__isnull=True)
            .prefetch_related("area", "region", "health_area")
            .first()
        )
        if not province:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="province_not_found")
        return {"item": GeographyManagementService._serialize_province(province)}

    @staticmethod
    async def create_province(payload: Dict[str, object]) -> Dict[str, object]:
        province_code = str(payload["province_code"]).strip()
        if await Province.filter(province_code=province_code).exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="province_code_in_use")
        area_code = GeographyManagementService._normalize_code(payload.get("area_code"))
        region_code = GeographyManagementService._normalize_code(payload.get("region_code"))
        health_area_code = GeographyManagementService._normalize_code(payload.get("health_area_code"))
        await GeographyManagementService._ensure_area(area_code)
        await GeographyManagementService._ensure_region(region_code)
        await GeographyManagementService._ensure_health_area(health_area_code)
        province = await Province.create(
            province_code=province_code,
            province_name_th=str(payload.get("province_name_th")),
            province_name_en=payload.get("province_name_en"),
            area_id=area_code,
            region_id=region_code,
            health_area_id=health_area_code,
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            quota=int(payload.get("quota") or 0),
        )
        await province.fetch_related("area", "region", "health_area")
        await GeographyManagementService._invalidate_geo_cache("lookup:provinces:*")
        return {"item": GeographyManagementService._serialize_province(province)}

    @staticmethod
    async def update_province(province_code: str, payload: Dict[str, object]) -> Dict[str, object]:
        province = (
            await Province.filter(province_code=province_code, deleted_at__isnull=True)
            .prefetch_related("area", "region", "health_area")
            .first()
        )
        if not province:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="province_not_found")
        data = payload.copy()
        if "area_code" in data:
            area_code = GeographyManagementService._normalize_code(data.get("area_code"))
            await GeographyManagementService._ensure_area(area_code)
            province.area_id = area_code
        if "region_code" in data:
            region_code = GeographyManagementService._normalize_code(data.get("region_code"))
            await GeographyManagementService._ensure_region(region_code)
            province.region_id = region_code
        if "health_area_code" in data:
            health_area_code = GeographyManagementService._normalize_code(data.get("health_area_code"))
            await GeographyManagementService._ensure_health_area(health_area_code)
            province.health_area_id = health_area_code
        if "province_name_th" in data:
            province.province_name_th = data.get("province_name_th")
        if "province_name_en" in data:
            province.province_name_en = data.get("province_name_en")
        if "latitude" in data:
            province.latitude = data.get("latitude")
        if "longitude" in data:
            province.longitude = data.get("longitude")
        if "quota" in data:
            quota_value = data.get("quota")
            province.quota = int(quota_value) if quota_value is not None else 0
        await province.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:provinces:*")
        await province.fetch_related("area", "region", "health_area")
        return {"item": GeographyManagementService._serialize_province(province)}

    @staticmethod
    async def update_province_quota(province_code: str, quota_value: int) -> Dict[str, object]:
        province = (
            await Province.filter(province_code=province_code, deleted_at__isnull=True)
            .prefetch_related("area", "region", "health_area")
            .first()
        )
        if not province:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="province_not_found")
        province.quota = int(quota_value or 0)
        await province.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:provinces:*")
        await province.fetch_related("area", "region", "health_area")
        return {"item": GeographyManagementService._serialize_province(province)}

    @staticmethod
    async def delete_province(province_code: str) -> Dict[str, object]:
        deleted = await Province.filter(province_code=province_code, deleted_at__isnull=True).update(
            deleted_at=datetime.utcnow()
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="province_not_found")
        await GeographyManagementService._invalidate_geo_cache("lookup:provinces:*")
        return {"success": True}

    # ------------------------------------------------------------------
    # District management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_districts(
        *,
        keyword: Optional[str],
        province_code: Optional[str],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = District.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(district_name_th__icontains=keyword)
                | Q(district_name_en__icontains=keyword)
                | Q(district_code__icontains=keyword)
            )
        if province_code:
            query = query.filter(province_id=province_code)
        total = await query.count()
        rows = (
            await query.order_by("district_name_th")
            .offset(offset)
            .limit(limit)
            .prefetch_related("province")
        )
        items = [GeographyManagementService._serialize_district(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_district(district_code: str) -> Dict[str, object]:
        district = (
            await District.filter(district_code=district_code, deleted_at__isnull=True)
            .prefetch_related("province")
            .first()
        )
        if not district:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="district_not_found")
        return {"item": GeographyManagementService._serialize_district(district)}

    @staticmethod
    async def create_district(payload: Dict[str, object]) -> Dict[str, object]:
        district_code = str(payload["district_code"]).strip()
        if await District.filter(district_code=district_code).exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="district_code_in_use")
        province_code = GeographyManagementService._normalize_code(payload.get("province_code"))
        await GeographyManagementService._ensure_province(province_code)
        district = await District.create(
            district_code=district_code,
            district_name_th=str(payload.get("district_name_th")),
            district_name_en=payload.get("district_name_en"),
            province_id=province_code,
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
        )
        await district.fetch_related("province")
        await GeographyManagementService._invalidate_geo_cache("lookup:districts:*")
        return {"item": GeographyManagementService._serialize_district(district)}

    @staticmethod
    async def update_district(district_code: str, payload: Dict[str, object]) -> Dict[str, object]:
        district = (
            await District.filter(district_code=district_code, deleted_at__isnull=True)
            .prefetch_related("province")
            .first()
        )
        if not district:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="district_not_found")
        data = payload.copy()
        if "province_code" in data:
            province_code = GeographyManagementService._normalize_code(data.get("province_code"))
            await GeographyManagementService._ensure_province(province_code)
            district.province_id = province_code
        if "district_name_th" in data:
            district.district_name_th = data.get("district_name_th")
        if "district_name_en" in data:
            district.district_name_en = data.get("district_name_en")
        if "latitude" in data:
            district.latitude = data.get("latitude")
        if "longitude" in data:
            district.longitude = data.get("longitude")
        await district.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:districts:*")
        await district.fetch_related("province")
        return {"item": GeographyManagementService._serialize_district(district)}

    @staticmethod
    async def delete_district(district_code: str) -> Dict[str, object]:
        deleted = await District.filter(district_code=district_code, deleted_at__isnull=True).update(
            deleted_at=datetime.utcnow()
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="district_not_found")
        await GeographyManagementService._invalidate_geo_cache("lookup:districts:*")
        return {"success": True}

    # ------------------------------------------------------------------
    # Subdistrict management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_subdistricts(
        *,
        keyword: Optional[str],
        province_code: Optional[str],
        district_code: Optional[str],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = Subdistrict.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(subdistrict_name_th__icontains=keyword)
                | Q(subdistrict_name_en__icontains=keyword)
                | Q(subdistrict_code__icontains=keyword)
            )
        if district_code:
            query = query.filter(district_id=district_code)
        if province_code:
            query = query.filter(district__province_id=province_code)
        total = await query.count()
        rows = (
            await query.order_by("subdistrict_name_th")
            .offset(offset)
            .limit(limit)
            .prefetch_related("district__province")
        )
        items = [GeographyManagementService._serialize_subdistrict(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_subdistrict(subdistrict_code: str) -> Dict[str, object]:
        subdistrict = (
            await Subdistrict.filter(subdistrict_code=subdistrict_code, deleted_at__isnull=True)
            .prefetch_related("district__province")
            .first()
        )
        if not subdistrict:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subdistrict_not_found")
        return {"item": GeographyManagementService._serialize_subdistrict(subdistrict)}

    @staticmethod
    async def create_subdistrict(payload: Dict[str, object]) -> Dict[str, object]:
        subdistrict_code = str(payload["subdistrict_code"]).strip()
        if await Subdistrict.filter(subdistrict_code=subdistrict_code).exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subdistrict_code_in_use")
        district_code = GeographyManagementService._normalize_code(payload.get("district_code"))
        await GeographyManagementService._ensure_district(district_code)
        subdistrict = await Subdistrict.create(
            subdistrict_code=subdistrict_code,
            subdistrict_name_th=str(payload.get("subdistrict_name_th")),
            subdistrict_name_en=payload.get("subdistrict_name_en"),
            district_id=district_code,
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            postal_code=payload.get("postal_code"),
        )
        await subdistrict.fetch_related("district__province")
        await GeographyManagementService._invalidate_geo_cache("lookup:subdistricts:*")
        return {"item": GeographyManagementService._serialize_subdistrict(subdistrict)}

    @staticmethod
    async def update_subdistrict(subdistrict_code: str, payload: Dict[str, object]) -> Dict[str, object]:
        subdistrict = (
            await Subdistrict.filter(subdistrict_code=subdistrict_code, deleted_at__isnull=True)
            .prefetch_related("district__province")
            .first()
        )
        if not subdistrict:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subdistrict_not_found")
        data = payload.copy()
        if "district_code" in data:
            district_code = GeographyManagementService._normalize_code(data.get("district_code"))
            await GeographyManagementService._ensure_district(district_code)
            subdistrict.district_id = district_code
        if "subdistrict_name_th" in data:
            subdistrict.subdistrict_name_th = data.get("subdistrict_name_th")
        if "subdistrict_name_en" in data:
            subdistrict.subdistrict_name_en = data.get("subdistrict_name_en")
        if "latitude" in data:
            subdistrict.latitude = data.get("latitude")
        if "longitude" in data:
            subdistrict.longitude = data.get("longitude")
        if "postal_code" in data:
            subdistrict.postal_code = data.get("postal_code")
        await subdistrict.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:subdistricts:*")
        await subdistrict.fetch_related("district__province")
        return {"item": GeographyManagementService._serialize_subdistrict(subdistrict)}

    @staticmethod
    async def delete_subdistrict(subdistrict_code: str) -> Dict[str, object]:
        deleted = await Subdistrict.filter(subdistrict_code=subdistrict_code, deleted_at__isnull=True).update(
            deleted_at=datetime.utcnow()
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subdistrict_not_found")
        await GeographyManagementService._invalidate_geo_cache("lookup:subdistricts:*")
        return {"success": True}

    # ------------------------------------------------------------------
    # Village management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_villages(
        *,
        keyword: Optional[str],
        province_code: Optional[str],
        district_code: Optional[str],
        subdistrict_code: Optional[str],
        health_service_code: Optional[str],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = Village.filter(deleted_at__isnull=True)
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
        total = await query.count()
        rows = (
            await query.order_by("village_name_th")
            .offset(offset)
            .limit(limit)
            .prefetch_related("subdistrict__district__province", "health_service")
        )
        items = [GeographyManagementService._serialize_village(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_village(village_code: str) -> Dict[str, object]:
        village = (
            await Village.filter(village_code=village_code, deleted_at__isnull=True)
            .prefetch_related("subdistrict__district__province", "health_service")
            .first()
        )
        if not village:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="village_not_found")
        return {"item": GeographyManagementService._serialize_village(village)}

    @staticmethod
    async def create_village(payload: Dict[str, object]) -> Dict[str, object]:
        village_code = str(payload["village_code"]).strip()
        if await Village.filter(village_code=village_code).exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="village_code_in_use")
        subdistrict_code = GeographyManagementService._normalize_code(payload.get("subdistrict_code"))
        await GeographyManagementService._ensure_subdistrict(subdistrict_code)
        health_service_code = GeographyManagementService._normalize_code(payload.get("health_service_code"))
        await GeographyManagementService._ensure_health_service(health_service_code)
        village = await Village.create(
            village_code=village_code,
            village_code_8digit=payload.get("village_code_8digit"),
            village_no=payload.get("village_no"),
            village_name_th=str(payload.get("village_name_th")),
            village_name_en=payload.get("village_name_en"),
            metro_status=payload.get("metro_status"),
            subdistrict_id=subdistrict_code,
            government_id=payload.get("government_id"),
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            health_service_id=health_service_code,
            external_url=payload.get("external_url"),
        )
        await village.fetch_related("subdistrict__district__province", "health_service")
        await GeographyManagementService._invalidate_geo_cache("lookup:villages:*")
        return {"item": GeographyManagementService._serialize_village(village)}

    @staticmethod
    async def update_village(village_code: str, payload: Dict[str, object]) -> Dict[str, object]:
        village = (
            await Village.filter(village_code=village_code, deleted_at__isnull=True)
            .prefetch_related("subdistrict__district__province", "health_service")
            .first()
        )
        if not village:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="village_not_found")
        data = payload.copy()
        if "subdistrict_code" in data:
            subdistrict_code = GeographyManagementService._normalize_code(data.get("subdistrict_code"))
            await GeographyManagementService._ensure_subdistrict(subdistrict_code)
            village.subdistrict_id = subdistrict_code
        if "health_service_code" in data:
            health_service_code = GeographyManagementService._normalize_code(data.get("health_service_code"))
            await GeographyManagementService._ensure_health_service(health_service_code)
            village.health_service_id = health_service_code
        for field in [
            "village_code_8digit",
            "village_no",
            "village_name_th",
            "village_name_en",
            "metro_status",
            "government_id",
            "latitude",
            "longitude",
            "external_url",
        ]:
            if field in data:
                setattr(village, field, data.get(field))
        await village.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:villages:*")
        await village.fetch_related("subdistrict__district__province", "health_service")
        return {"item": GeographyManagementService._serialize_village(village)}

    @staticmethod
    async def delete_village(village_code: str) -> Dict[str, object]:
        deleted = await Village.filter(village_code=village_code, deleted_at__isnull=True).update(
            deleted_at=datetime.utcnow()
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="village_not_found")
        await GeographyManagementService._invalidate_geo_cache("lookup:villages:*")
        return {"success": True}

    # ------------------------------------------------------------------
    # Health service management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_health_services(
        *,
        keyword: Optional[str],
        province_code: Optional[str],
        district_code: Optional[str],
        subdistrict_code: Optional[str],
        health_service_code: Optional[str],
        legacy_5digit_code: Optional[str],
        legacy_9digit_code: Optional[str],
        health_service_type_id: Optional[str],
        health_service_type_ids_exclude: Optional[List[str]],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = HealthService.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(health_service_name_th__icontains=keyword)
                | Q(health_service_name_en__icontains=keyword)
                | Q(health_service_code__icontains=keyword)
                | Q(legacy_5digit_code__icontains=keyword)
                | Q(legacy_9digit_code__icontains=keyword)
            )
        if health_service_code:
            query = query.filter(health_service_code=GeographyManagementService._normalize_code(health_service_code))
        if legacy_5digit_code:
            query = query.filter(legacy_5digit_code=GeographyManagementService._normalize_code(legacy_5digit_code))
        if legacy_9digit_code:
            query = query.filter(legacy_9digit_code=GeographyManagementService._normalize_code(legacy_9digit_code))
        if province_code:
            query = query.filter(province_id=province_code)
        if district_code:
            query = query.filter(district_id=district_code)
        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)
        if health_service_type_id:
            query = query.filter(health_service_type_id=health_service_type_id)
        if health_service_type_ids_exclude:
            exclude_ids = [
                GeographyManagementService._normalize_code(value)
                for value in health_service_type_ids_exclude
                if value is not None
            ]
            exclude_ids = [value for value in exclude_ids if value]
            if exclude_ids:
                query = query.exclude(health_service_type_id__in=exclude_ids)

        total = await query.count()
        rows = (
            await query.order_by("health_service_name_th")
            .offset(offset)
            .limit(limit)
            .prefetch_related("health_service_type", "province", "district", "subdistrict")
        )
        items = [GeographyManagementService._serialize_health_service(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_health_service(health_service_code: str) -> Dict[str, object]:
        health_service = (
            await HealthService.filter(
                health_service_code=health_service_code,
                deleted_at__isnull=True,
            )
            .prefetch_related("health_service_type", "province", "district", "subdistrict")
            .first()
        )
        if not health_service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_service_not_found")
        return {"item": GeographyManagementService._serialize_health_service(health_service)}

    @staticmethod
    async def create_health_service(payload: Dict[str, object], *, actor_id: Optional[str]) -> Dict[str, object]:
        health_service_code = str(payload["health_service_code"]).strip()
        if await HealthService.filter(health_service_code=health_service_code).exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_service_code_in_use")
        await GeographyManagementService._ensure_health_service_type(payload.get("health_service_type_id"))
        province_code = GeographyManagementService._normalize_code(payload.get("province_code"))
        district_code = GeographyManagementService._normalize_code(payload.get("district_code"))
        subdistrict_code = GeographyManagementService._normalize_code(payload.get("subdistrict_code"))
        await GeographyManagementService._ensure_province(province_code)
        await GeographyManagementService._ensure_district(district_code)
        await GeographyManagementService._ensure_subdistrict(subdistrict_code)
        actor = GeographyManagementService._parse_actor(actor_id)
        health_service = await HealthService.create(
            health_service_code=health_service_code,
            health_service_name_th=str(payload.get("health_service_name_th")),
            health_service_name_en=payload.get("health_service_name_en"),
            legacy_5digit_code=payload.get("legacy_5digit_code"),
            legacy_9digit_code=payload.get("legacy_9digit_code"),
            health_service_type_id=GeographyManagementService._normalize_code(
                payload.get("health_service_type_id")
            ),
            province_id=province_code,
            district_id=district_code,
            subdistrict_id=subdistrict_code,
            village_no=payload.get("village_no"),
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            created_by=actor,
            updated_by=actor,
        )
        await health_service.fetch_related("health_service_type", "province", "district", "subdistrict")
        await GeographyManagementService._invalidate_geo_cache("lookup:hs:*")
        return {"item": GeographyManagementService._serialize_health_service(health_service)}

    @staticmethod
    async def update_health_service(
        health_service_code: str,
        payload: Dict[str, object],
        *,
        actor_id: Optional[str],
    ) -> Dict[str, object]:
        health_service = (
            await HealthService.filter(
                health_service_code=health_service_code,
                deleted_at__isnull=True,
            )
            .prefetch_related("health_service_type", "province", "district", "subdistrict")
            .first()
        )
        if not health_service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_service_not_found")

        data = payload.copy()
        if "health_service_type_id" in data:
            await GeographyManagementService._ensure_health_service_type(data.get("health_service_type_id"))
            health_service.health_service_type_id = GeographyManagementService._normalize_code(
                data.get("health_service_type_id")
            )
        if "province_code" in data:
            province_code = GeographyManagementService._normalize_code(data.get("province_code"))
            await GeographyManagementService._ensure_province(province_code)
            health_service.province_id = province_code
        if "district_code" in data:
            district_code = GeographyManagementService._normalize_code(data.get("district_code"))
            await GeographyManagementService._ensure_district(district_code)
            health_service.district_id = district_code
        if "subdistrict_code" in data:
            subdistrict_code = GeographyManagementService._normalize_code(data.get("subdistrict_code"))
            await GeographyManagementService._ensure_subdistrict(subdistrict_code)
            health_service.subdistrict_id = subdistrict_code
        for field in [
            "health_service_name_th",
            "health_service_name_en",
            "legacy_5digit_code",
            "legacy_9digit_code",
            "village_no",
            "latitude",
            "longitude",
        ]:
            if field in data:
                setattr(health_service, field, data.get(field))

        health_service.updated_by = GeographyManagementService._parse_actor(actor_id)
        await health_service.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:hs:*")
        await health_service.fetch_related("health_service_type", "province", "district", "subdistrict")
        return {"item": GeographyManagementService._serialize_health_service(health_service)}

    @staticmethod
    async def delete_health_service(health_service_code: str, *, actor_id: Optional[str]) -> Dict[str, object]:
        actor = GeographyManagementService._parse_actor(actor_id)
        updated = await HealthService.filter(
            health_service_code=health_service_code,
            deleted_at__isnull=True,
        ).update(
            deleted_at=datetime.utcnow(),
            updated_by=actor,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_service_not_found")
        await GeographyManagementService._invalidate_geo_cache("lookup:hs:*")
        return {"success": True}

    # ------------------------------------------------------------------
    # Municipality management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_municipalities(
        *,
        keyword: Optional[str],
        municipality_type_code: Optional[str],
        province_code: Optional[str],
        district_code: Optional[str],
        subdistrict_code: Optional[str],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = Municipality.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(municipality_name_th__icontains=keyword)
                | Q(municipality_name_en__icontains=keyword)
            )
        if municipality_type_code:
            query = query.filter(municipality_type_id=municipality_type_code)
        if province_code:
            query = query.filter(province_id=province_code)
        if district_code:
            query = query.filter(district_id=district_code)
        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)
        total = await query.count()
        rows = (
            await query.order_by("municipality_name_th")
            .offset(offset)
            .limit(limit)
            .prefetch_related("municipality_type", "province", "district", "subdistrict")
        )
        items = [GeographyManagementService._serialize_municipality(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_municipality(municipality_id: str) -> Dict[str, object]:
        municipality = (
            await Municipality.filter(id=municipality_id, deleted_at__isnull=True)
            .prefetch_related("municipality_type", "province", "district", "subdistrict")
            .first()
        )
        if not municipality:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="municipality_not_found")
        return {"item": GeographyManagementService._serialize_municipality(municipality)}

    @staticmethod
    async def create_municipality(payload: Dict[str, object], *, actor_id: Optional[str]) -> Dict[str, object]:
        await GeographyManagementService._ensure_municipality_type(payload.get("municipality_type_code"))
        province_code = GeographyManagementService._normalize_code(payload.get("province_code"))
        district_code = GeographyManagementService._normalize_code(payload.get("district_code"))
        subdistrict_code = GeographyManagementService._normalize_code(payload.get("subdistrict_code"))
        await GeographyManagementService._ensure_province(province_code)
        await GeographyManagementService._ensure_district(district_code)
        await GeographyManagementService._ensure_subdistrict(subdistrict_code)
        actor = GeographyManagementService._parse_actor(actor_id)
        municipality = await Municipality.create(
            municipality_name_th=str(payload.get("municipality_name_th")),
            municipality_name_en=payload.get("municipality_name_en"),
            municipality_type_id=GeographyManagementService._normalize_code(payload.get("municipality_type_code")),
            province_id=province_code,
            district_id=district_code,
            subdistrict_id=subdistrict_code,
            created_by=actor,
            updated_by=actor,
        )
        await municipality.fetch_related("municipality_type", "province", "district", "subdistrict")
        await GeographyManagementService._invalidate_geo_cache("lookup:municipalities:*")
        return {"item": GeographyManagementService._serialize_municipality(municipality)}

    @staticmethod
    async def update_municipality(
        municipality_id: str,
        payload: Dict[str, object],
        *,
        actor_id: Optional[str],
    ) -> Dict[str, object]:
        municipality = (
            await Municipality.filter(id=municipality_id, deleted_at__isnull=True)
            .prefetch_related("municipality_type", "province", "district", "subdistrict")
            .first()
        )
        if not municipality:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="municipality_not_found")
        data = payload.copy()
        if "municipality_type_code" in data:
            await GeographyManagementService._ensure_municipality_type(data.get("municipality_type_code"))
            municipality.municipality_type_id = GeographyManagementService._normalize_code(data.get("municipality_type_code"))
        if "province_code" in data:
            province_code = GeographyManagementService._normalize_code(data.get("province_code"))
            await GeographyManagementService._ensure_province(province_code)
            municipality.province_id = province_code
        if "district_code" in data:
            district_code = GeographyManagementService._normalize_code(data.get("district_code"))
            await GeographyManagementService._ensure_district(district_code)
            municipality.district_id = district_code
        if "subdistrict_code" in data:
            subdistrict_code = GeographyManagementService._normalize_code(data.get("subdistrict_code"))
            await GeographyManagementService._ensure_subdistrict(subdistrict_code)
            municipality.subdistrict_id = subdistrict_code
        if "municipality_name_th" in data:
            municipality.municipality_name_th = data.get("municipality_name_th")
        if "municipality_name_en" in data:
            municipality.municipality_name_en = data.get("municipality_name_en")
        actor = GeographyManagementService._parse_actor(actor_id)
        municipality.updated_by = actor
        await municipality.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:municipalities:*")
        await municipality.fetch_related("municipality_type", "province", "district", "subdistrict")
        return {"item": GeographyManagementService._serialize_municipality(municipality)}

    @staticmethod
    async def delete_municipality(municipality_id: str, *, actor_id: Optional[str]) -> Dict[str, object]:
        actor = GeographyManagementService._parse_actor(actor_id)
        updated = await Municipality.filter(id=municipality_id, deleted_at__isnull=True).update(
            deleted_at=datetime.utcnow(),
            updated_by=actor,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="municipality_not_found")
        await GeographyManagementService._invalidate_geo_cache("lookup:municipalities:*")
        return {"success": True}

    # ------------------------------------------------------------------
    # Health area management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_health_areas(
        *,
        keyword: Optional[str],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = HealthArea.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(
                Q(health_area_name_th__icontains=keyword)
                | Q(health_area_name_en__icontains=keyword)
                | Q(code__icontains=keyword)
            )
        total = await query.count()
        rows = (
            await query.order_by("health_area_name_th")
            .offset(offset)
            .limit(limit)
            .prefetch_related(Prefetch("provinces", queryset=Province.filter(deleted_at__isnull=True)))
        )
        items = [GeographyManagementService._serialize_health_area_with_provinces(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_health_area(code: str) -> Dict[str, object]:
        health_area = (
            await HealthArea.filter(code=code, deleted_at__isnull=True)
            .prefetch_related(Prefetch("provinces", queryset=Province.filter(deleted_at__isnull=True)))
            .first()
        )
        if not health_area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_area_not_found")
        return {"item": GeographyManagementService._serialize_health_area_with_provinces(health_area)}

    @staticmethod
    async def create_health_area(payload: Dict[str, object], *, actor_id: Optional[str]) -> Dict[str, object]:
        code = str(payload["code"]).strip()
        if await HealthArea.filter(code=code).exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_area_code_in_use")
        actor = GeographyManagementService._parse_actor(actor_id)
        health_area = await HealthArea.create(
            code=code,
            health_area_name_th=str(payload.get("health_area_name_th")),
            health_area_name_en=payload.get("health_area_name_en"),
            created_by=actor,
            updated_by=actor,
        )
        await health_area.fetch_related("provinces")
        await GeographyManagementService._invalidate_geo_cache("lookup:health-areas:*")
        return {"item": GeographyManagementService._serialize_health_area_with_provinces(health_area)}

    @staticmethod
    async def update_health_area(code: str, payload: Dict[str, object], *, actor_id: Optional[str]) -> Dict[str, object]:
        health_area = (
            await HealthArea.filter(code=code, deleted_at__isnull=True)
            .prefetch_related(Prefetch("provinces", queryset=Province.filter(deleted_at__isnull=True)))
            .first()
        )
        if not health_area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_area_not_found")
        actor = GeographyManagementService._parse_actor(actor_id)
        if "health_area_name_th" in payload:
            health_area.health_area_name_th = payload.get("health_area_name_th")
        if "health_area_name_en" in payload:
            health_area.health_area_name_en = payload.get("health_area_name_en")
        health_area.updated_by = actor
        await health_area.save()
        await GeographyManagementService._invalidate_geo_cache("lookup:health-areas:*")
        await health_area.fetch_related("provinces")
        return {"item": GeographyManagementService._serialize_health_area_with_provinces(health_area)}

    @staticmethod
    async def delete_health_area(code: str, *, actor_id: Optional[str]) -> Dict[str, object]:
        actor = GeographyManagementService._parse_actor(actor_id)
        updated = await HealthArea.filter(code=code, deleted_at__isnull=True).update(
            deleted_at=datetime.utcnow(),
            updated_by=actor,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="health_area_not_found")
        await GeographyManagementService._invalidate_geo_cache("lookup:health-areas:*")
        return {"success": True}
