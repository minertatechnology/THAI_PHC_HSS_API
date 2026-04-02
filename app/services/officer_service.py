from datetime import datetime

import secrets
import string
from typing import Any, Dict, Iterable, Optional, List

from fastapi import HTTPException, status

from app.api.v1.schemas.officer_schema import (
    OfficerCreateSchema,
    OfficerApprovalActionSchema,
    OfficerQueryParams,
    OfficerUpdateSchema,
)
from app.api.v1.schemas.response_schema import (
    officer_to_list_response,
    officer_to_response,
)
from app.models.geography_model import Province, District, Subdistrict
from app.models.health_model import HealthArea, HealthService
from app.repositories.officer_profile_repository import OfficerProfileRepository
from app.repositories.client_repository import RefreshTokenRepository
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.repositories.people_user_repository import PeopleUserRepository
from app.repositories.gen_h_user_repository import GenHUserRepository
from app.models.gen_h_model import GenHUser
from app.models.enum_models import ApprovalStatus, AdministrativeLevelEnum, Gender
from app.models.audit_model import AdminAuditLog
from app.models.position_model import Position
from app.utils.officer_hierarchy import (
    OfficerHierarchy,
    OfficerScope,
    OfficerScopeError,
)
from app.services.oauth2_service import bcrypt_hash_password
from app.services.lookup_service import LookupService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.utils.logging_utils import get_logger, log_error, log_info
from app.cache.redis_client import cache_delete_pattern
from app.api.middleware.middleware import invalidate_user_sessions


logger = get_logger(__name__)


class OfficerService:
    _TEMP_PASSWORD_LENGTH = 12

    _AREA_LEVEL_RANK = {
        AdministrativeLevelEnum.COUNTRY: 6,
        AdministrativeLevelEnum.REGION: 5,
        AdministrativeLevelEnum.AREA: 4,
        AdministrativeLevelEnum.PROVINCE: 3,
        AdministrativeLevelEnum.DISTRICT: 2,
        AdministrativeLevelEnum.SUBDISTRICT: 1,
        AdministrativeLevelEnum.VILLAGE: 0,
    }

    @staticmethod
    def _reconcile_area_scope(payload: dict) -> tuple[dict, bool, AdministrativeLevelEnum | None, AdministrativeLevelEnum | None]:
        level_requirements: list[tuple[AdministrativeLevelEnum, tuple[str, ...]]] = [
            (AdministrativeLevelEnum.VILLAGE, ("province_id", "district_id", "subdistrict_id", "area_code")),
            (AdministrativeLevelEnum.SUBDISTRICT, ("province_id", "district_id", "subdistrict_id")),
            (AdministrativeLevelEnum.DISTRICT, ("province_id", "district_id")),
            (AdministrativeLevelEnum.PROVINCE, ("province_id",)),
            (AdministrativeLevelEnum.AREA, ("health_area_id",)),
            (AdministrativeLevelEnum.REGION, ("region_code",)),
            (AdministrativeLevelEnum.COUNTRY, ()),
        ]

        current_level: AdministrativeLevelEnum | None = None
        raw_area_type = payload.get("area_type")
        if raw_area_type:
            try:
                current_level = raw_area_type if isinstance(raw_area_type, AdministrativeLevelEnum) else AdministrativeLevelEnum(str(raw_area_type))
            except ValueError:
                current_level = None

        target_level: AdministrativeLevelEnum | None = None
        for level, required_fields in level_requirements:
            if all(payload.get(field) for field in required_fields):
                target_level = level
                break

        if target_level is None:
            target_level = AdministrativeLevelEnum.COUNTRY

        changed = False
        if current_level is None or OfficerService._AREA_LEVEL_RANK[current_level] < OfficerService._AREA_LEVEL_RANK[target_level]:
            if current_level != target_level:
                changed = True
            payload["area_type"] = target_level.value

        return payload, changed, current_level, target_level

    @staticmethod
    def _generate_temporary_password(length: int | None = None) -> str:
        alphabet = string.ascii_letters + string.digits
        size = length or OfficerService._TEMP_PASSWORD_LENGTH
        return "".join(secrets.choice(alphabet) for _ in range(size))

    @staticmethod
    def _normalize_code(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    @staticmethod
    def _normalize_lookup_param(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _normalize_lookup_list(values: Optional[List[str]]) -> Optional[List[str]]:
        if not values:
            return None
        cleaned = [str(value).strip() for value in values if value is not None]
        cleaned = [value for value in cleaned if value]
        return cleaned or None

    @staticmethod
    def _cap_scope_by_position_for_local_levels(profile, scope: OfficerScope) -> OfficerScope:
        if profile is None or scope is None:
            return scope

        position = getattr(profile, "position", None)
        if position is None:
            return scope

        raw_scope_level = getattr(position, "scope_level", None)
        if raw_scope_level is None:
            return scope

        try:
            position_level = (
                raw_scope_level
                if isinstance(raw_scope_level, AdministrativeLevelEnum)
                else AdministrativeLevelEnum(str(raw_scope_level))
            )
        except ValueError:
            return scope

        # Only cap by position for local roles (province and below).
        # High-level roles remain unchanged.
        if position_level in [
            AdministrativeLevelEnum.COUNTRY,
            AdministrativeLevelEnum.REGION,
            AdministrativeLevelEnum.AREA,
        ]:
            return scope

        position_rank = OfficerService._AREA_LEVEL_RANK.get(position_level, -1)
        scope_rank = OfficerService._AREA_LEVEL_RANK.get(scope.level, -1)
        if position_rank < 0 or scope_rank < 0:
            return scope
        if position_rank >= scope_rank:
            return scope

        return OfficerScope(
            level=position_level,
            health_area_id=scope.health_area_id,
            health_service_id=scope.health_service_id,
            province_id=scope.province_id,
            district_id=scope.district_id,
            subdistrict_id=scope.subdistrict_id,
            village_code=scope.village_code,
            region_code=scope.region_code,
        )

    @staticmethod
    def _build_scope_from_geography(
        *,
        region_code: Optional[str] = None,
        health_area_id: Optional[str] = None,
        province_id: Optional[str] = None,
        district_id: Optional[str] = None,
        subdistrict_id: Optional[str] = None,
        village_code: Optional[str] = None,
    ) -> OfficerScope:
        if village_code:
            level = AdministrativeLevelEnum.VILLAGE
        elif subdistrict_id:
            level = AdministrativeLevelEnum.SUBDISTRICT
        elif district_id:
            level = AdministrativeLevelEnum.DISTRICT
        elif province_id:
            level = AdministrativeLevelEnum.PROVINCE
        elif health_area_id:
            level = AdministrativeLevelEnum.AREA
        elif region_code:
            level = AdministrativeLevelEnum.REGION
        else:
            level = AdministrativeLevelEnum.COUNTRY

        return OfficerScope(
            level=level,
            health_area_id=health_area_id,
            province_id=province_id,
            district_id=district_id,
            subdistrict_id=subdistrict_id,
            village_code=village_code,
            region_code=region_code,
        )

    @staticmethod
    async def _resolve_osm_management_context(profile) -> tuple[OfficerScope, Dict[str, Optional[str]]]:
        province = getattr(profile, "province", None)
        province_code = OfficerService._normalize_code(getattr(profile, "province_id", None))
        if not province and province_code:
            province = await Province.filter(province_code=province_code).first()
        if province and not province_code:
            province_code = OfficerService._normalize_code(getattr(province, "province_code", None))

        district = getattr(profile, "district", None)
        district_code = OfficerService._normalize_code(getattr(profile, "district_id", None))
        if not district and district_code:
            district = await District.filter(district_code=district_code).first()
        if district and not district_code:
            district_code = OfficerService._normalize_code(getattr(district, "district_code", None))

        subdistrict = getattr(profile, "subdistrict", None)
        subdistrict_code = OfficerService._normalize_code(getattr(profile, "subdistrict_id", None))
        if not subdistrict and subdistrict_code:
            subdistrict = await Subdistrict.filter(subdistrict_code=subdistrict_code).select_related("district__province").first()
        if subdistrict and not subdistrict_code:
            subdistrict_code = OfficerService._normalize_code(getattr(subdistrict, "subdistrict_code", None))
        if subdistrict and not district:
            district = getattr(subdistrict, "district", None)
            if district and not district_code:
                district_code = OfficerService._normalize_code(getattr(district, "district_code", None))
        if district and not province:
            province = getattr(district, "province", None)
            if province and not province_code:
                province_code = OfficerService._normalize_code(getattr(province, "province_code", None))

        health_area_id = OfficerService._normalize_code(getattr(province, "health_area_id", None)) if province else None
        region_code = OfficerService._normalize_code(getattr(province, "region_id", None)) if province else None
        village_code = OfficerService._normalize_code(getattr(profile, "village_code", None))

        target_scope = OfficerService._build_scope_from_geography(
            region_code=region_code,
            health_area_id=health_area_id,
            province_id=province_code,
            district_id=district_code,
            subdistrict_id=subdistrict_code,
            village_code=village_code,
        )

        context = {
            "province_code": province_code,
            "district_code": district_code,
            "subdistrict_code": subdistrict_code,
            "village_code": village_code,
            "health_area_id": health_area_id,
            "region_code": region_code,
        }
        return target_scope, context

    @staticmethod
    async def _resolve_yuwa_management_context(profile) -> tuple[OfficerScope, Dict[str, Optional[str]]]:
        province_code = OfficerService._normalize_code(getattr(profile, "province_code", None))
        district_code = OfficerService._normalize_code(getattr(profile, "district_code", None))
        subdistrict_code = OfficerService._normalize_code(getattr(profile, "subdistrict_code", None))

        province = None
        if province_code:
            province = await Province.filter(province_code=province_code).first()

        district = None
        if not province and district_code:
            district = await District.filter(district_code=district_code).select_related("province").first()
            if district:
                province = getattr(district, "province", None)

        subdistrict = None
        if not province and subdistrict_code:
            subdistrict = await Subdistrict.filter(subdistrict_code=subdistrict_code).select_related("district__province").first()
            if subdistrict:
                district = getattr(subdistrict, "district", None)
                if district and not district_code:
                    district_code = OfficerService._normalize_code(getattr(district, "district_code", None))
                province = getattr(district, "province", None) if district else None
        elif subdistrict_code:
            subdistrict = await Subdistrict.filter(subdistrict_code=subdistrict_code).select_related("district__province").first()
            if subdistrict and not district_code:
                district = getattr(subdistrict, "district", None)
                if district:
                    district_code = OfficerService._normalize_code(getattr(district, "district_code", None))
                    if not province:
                        province = getattr(district, "province", None)

        if province and not province_code:
            province_code = OfficerService._normalize_code(getattr(province, "province_code", None))
        if district and not district_code:
            district_code = OfficerService._normalize_code(getattr(district, "district_code", None))
        if subdistrict and not subdistrict_code:
            subdistrict_code = OfficerService._normalize_code(getattr(subdistrict, "subdistrict_code", None))

        health_area_id = OfficerService._normalize_code(getattr(province, "health_area_id", None)) if province else None
        region_code = OfficerService._normalize_code(getattr(province, "region_id", None)) if province else None

        target_scope = OfficerService._build_scope_from_geography(
            region_code=region_code,
            health_area_id=health_area_id,
            province_id=province_code,
            district_id=district_code,
            subdistrict_id=subdistrict_code,
        )

        context = {
            "province_code": province_code,
            "district_code": district_code,
            "subdistrict_code": subdistrict_code,
            "health_area_id": health_area_id,
            "region_code": region_code,
        }
        return target_scope, context

    @staticmethod
    async def _resolve_people_management_context(profile) -> tuple[OfficerScope, Dict[str, Optional[str]]]:
        province_code = OfficerService._normalize_code(getattr(profile, "province_code", None))
        district_code = OfficerService._normalize_code(getattr(profile, "district_code", None))
        subdistrict_code = OfficerService._normalize_code(getattr(profile, "subdistrict_code", None))

        province = None
        if province_code:
            province = await Province.filter(province_code=province_code).first()

        district = None
        if not province and district_code:
            district = await District.filter(district_code=district_code).select_related("province").first()
            if district:
                province = getattr(district, "province", None)

        subdistrict = None
        if not province and subdistrict_code:
            subdistrict = await Subdistrict.filter(subdistrict_code=subdistrict_code).select_related("district__province").first()
            if subdistrict:
                district = getattr(subdistrict, "district", None)
                if district and not district_code:
                    district_code = OfficerService._normalize_code(getattr(district, "district_code", None))
                province = getattr(district, "province", None) if district else None
        elif subdistrict_code:
            subdistrict = await Subdistrict.filter(subdistrict_code=subdistrict_code).select_related("district__province").first()
            if subdistrict and not district_code:
                district = getattr(subdistrict, "district", None)
                if district:
                    district_code = OfficerService._normalize_code(getattr(district, "district_code", None))
                    if not province:
                        province = getattr(district, "province", None)

        if province and not province_code:
            province_code = OfficerService._normalize_code(getattr(province, "province_code", None))
        if district and not district_code:
            district_code = OfficerService._normalize_code(getattr(district, "district_code", None))
        if subdistrict and not subdistrict_code:
            subdistrict_code = OfficerService._normalize_code(getattr(subdistrict, "subdistrict_code", None))

        health_area_id = OfficerService._normalize_code(getattr(province, "health_area_id", None)) if province else None
        region_code = OfficerService._normalize_code(getattr(province, "region_id", None)) if province else None

        target_scope = OfficerService._build_scope_from_geography(
            region_code=region_code,
            health_area_id=health_area_id,
            province_id=province_code,
            district_id=district_code,
            subdistrict_id=subdistrict_code,
        )

        context = {
            "province_code": province_code,
            "district_code": district_code,
            "subdistrict_code": subdistrict_code,
            "health_area_id": health_area_id,
            "region_code": region_code,
        }
        return target_scope, context

    @staticmethod
    def _enum_value(value: Any) -> Any:
        if value is None:
            return None
        return getattr(value, "value", value)

    @staticmethod
    def _resolve_area_type(*, position_scope, provided, fallback) -> str:
        scope_value = OfficerService._enum_value(position_scope)
        provided_value = OfficerService._enum_value(provided)
        fallback_value = OfficerService._enum_value(fallback)

        resolved = None
        if scope_value:
            if provided_value and provided_value != scope_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="area_type_position_mismatch",
                )
            resolved = scope_value
        elif provided_value:
            resolved = provided_value
        else:
            resolved = fallback_value

        if not resolved:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="area_type_required")

        try:
            AdministrativeLevelEnum(resolved)
        except ValueError as exc:  # pragma: no cover - validation guard
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_area_type") from exc

        return resolved

    @staticmethod
    async def _load_position(position_id: str) -> Position:
        if not position_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="position_missing")

        position = await Position.filter(id=position_id, deleted_at__isnull=True).first()
        if not position:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="position_not_found")

        return position

    @staticmethod
    def _clean_blank_strings(payload: dict, keys: Optional[Iterable[str]] = None) -> dict:
        target_keys = keys if keys is not None else payload.keys()
        for field in target_keys:
            if field in payload and isinstance(payload[field], str) and payload[field] == "":
                payload[field] = None
        return payload

    @staticmethod
    async def _augment_location_context(payload: dict) -> dict:
        enriched = dict(payload)
        province_id = enriched.get("province_id")
        district_id = enriched.get("district_id")
        subdistrict_id = enriched.get("subdistrict_id")

        subdistrict = None
        if subdistrict_id:
            subdistrict = await Subdistrict.filter(subdistrict_code=subdistrict_id).first()
            if not subdistrict:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subdistrict_not_found")
            subdistrict_district_id = getattr(subdistrict, "district_id", None)
            if district_id and subdistrict_district_id and district_id != subdistrict_district_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_location_hierarchy")
            district_id = district_id or subdistrict_district_id

        district = None
        if district_id:
            district = await District.filter(district_code=district_id).first()
            if not district:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="district_not_found")
            district_province_id = getattr(district, "province_id", None)
            if province_id and district_province_id and province_id != district_province_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_location_hierarchy")
            province_id = province_id or district_province_id

        province = None
        if province_id:
            province = await Province.filter(province_code=province_id).first()
            if not province:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="province_not_found")

        enriched["province_id"] = province_id
        enriched["district_id"] = district_id
        enriched["subdistrict_id"] = subdistrict_id

        if province:
            enriched["health_area_id"] = getattr(province, "health_area_id", None)
            enriched["region_code"] = getattr(province, "region_id", None)

        return enriched

    # Known health-service codes.
    _COUNTRY_HEALTH_SERVICE_CODE = "IA0015214"  # กรมสนับสนุนบริการสุขภาพ
    _BANGKOK_HEALTH_SERVICE_CODE = "IA0012499"  # สำนักอนามัยกรุงเทพมหานคร
    _BANGKOK_PROVINCE_CODE = "10"

    @staticmethod
    async def _auto_resolve_health_service(payload: dict) -> dict:
        """Auto-map health_service_id for country/area/province/district levels.

        - country  -> IA0015214 (กรมสนับสนุนบริการสุขภาพ)
        - area     -> IA code of สำนักงานเขตสุขภาพที่ {N}
        - province -> AA code whose province matches
        - district -> BA code whose district matches
        - Bangkok (province 10) at any local level -> IA0012499 (สำนักอนามัย กทม.)
        - subdistrict / village -> unchanged (user picks manually)
        """
        area_type = payload.get("area_type")
        if not area_type:
            return payload

        level_str = area_type if isinstance(area_type, str) else str(area_type)

        # Only auto-resolve when the caller did NOT already supply a health_service_id.
        if payload.get("health_service_id"):
            return payload

        resolved_code: Optional[str] = None

        # Bangkok special case: province/district in กทม. -> สำนักอนามัย กทม.
        province_id = payload.get("province_id")
        is_bangkok = str(province_id) == OfficerService._BANGKOK_PROVINCE_CODE if province_id else False

        if level_str == AdministrativeLevelEnum.COUNTRY.value:
            hs = await HealthService.filter(
                health_service_code=OfficerService._COUNTRY_HEALTH_SERVICE_CODE,
            ).first()
            if hs:
                resolved_code = hs.health_service_code

        elif level_str == AdministrativeLevelEnum.AREA.value:
            health_area_id = payload.get("health_area_id")
            if health_area_id:
                area_num = str(health_area_id).replace("HA", "")
                search_name = f"สำนักงานเขตสุขภาพที่ {area_num}"
                hs = await HealthService.filter(
                    health_service_code__startswith="IA",
                    health_service_name_th=search_name,
                ).first()
                if hs:
                    resolved_code = hs.health_service_code

        elif level_str == AdministrativeLevelEnum.PROVINCE.value:
            if is_bangkok:
                hs = await HealthService.filter(
                    health_service_code=OfficerService._BANGKOK_HEALTH_SERVICE_CODE,
                ).first()
                if hs:
                    resolved_code = hs.health_service_code
            elif province_id:
                hs = await HealthService.filter(
                    health_service_code__startswith="AA",
                    province_id=province_id,
                ).first()
                if hs:
                    resolved_code = hs.health_service_code

        elif level_str == AdministrativeLevelEnum.DISTRICT.value:
            if is_bangkok:
                hs = await HealthService.filter(
                    health_service_code=OfficerService._BANGKOK_HEALTH_SERVICE_CODE,
                ).first()
                if hs:
                    resolved_code = hs.health_service_code
            else:
                district_id = payload.get("district_id")
                if district_id:
                    hs = await HealthService.filter(
                        health_service_code__startswith="BA",
                        district_id=district_id,
                    ).first()
                    if hs:
                        resolved_code = hs.health_service_code

        if resolved_code:
            payload["health_service_id"] = resolved_code
            log_info(
                logger,
                "Auto-resolved health_service_id",
                area_type=level_str,
                health_service_id=resolved_code,
            )

        return payload

    @staticmethod
    async def _resolve_officer_scope(current_user: dict, require_active: bool = False):
        if current_user.get("user_type") != "officer":
            return None, None

        profile = await OfficerProfileRepository.get_officer_by_id(str(current_user.get("user_id")))
        if not profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="officer_profile_not_found")

        if require_active:
            if not profile.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="creator_not_active")

            if profile.approval_status != ApprovalStatus.APPROVED:
                position = getattr(profile, "position", None)
                position_scope = getattr(position, "scope_level", None)
                if position_scope != AdministrativeLevelEnum.COUNTRY:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="creator_not_active")

        try:
            scope = OfficerHierarchy.scope_from_profile(profile)
        except OfficerScopeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        scope = OfficerService._cap_scope_by_position_for_local_levels(profile, scope)

        return profile, scope

    @staticmethod
    def _ensure_scope_permission(
        viewer_scope,
        target_scope,
        *,
        require_strict: bool = False,
        allow_same_level: bool = False,
    ):
        if viewer_scope is None:
            return

        if not OfficerHierarchy.can_manage(viewer_scope, target_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient_scope_view_record",
            )

        if require_strict and viewer_scope.rank == target_scope.rank and not allow_same_level:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_same_level")

    @staticmethod
    def _ensure_view_permission(viewer_scope, target_scope):
        if viewer_scope is None:
            return
        if not OfficerHierarchy.can_view(viewer_scope, target_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient_scope_view_record",
            )

    @staticmethod
    async def _ensure_visibility_permission_for_officer(viewer_scope, officer_id: str) -> None:
        if viewer_scope is None:
            return
        try:
            visibility_filter = OfficerHierarchy.build_visibility_filter(viewer_scope)
        except OfficerScopeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        visible = await OfficerProfileRepository.is_officer_visible(officer_id, visibility_filter)
        log_info(
            logger,
            "Officer visibility check",
            officer_id=officer_id,
            viewer_level=getattr(getattr(viewer_scope, "level", None), "value", getattr(viewer_scope, "level", None)),
            viewer_ha=getattr(viewer_scope, "health_area_id", None),
            viewer_province=getattr(viewer_scope, "province_id", None),
            viewer_district=getattr(viewer_scope, "district_id", None),
            visible=visible,
        )
        if not visible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient_scope_view_record",
            )

    @staticmethod
    def _build_permission_snapshot(viewer_profile, viewer_scope, target_profile, target_scope=None):
        is_self = False
        if viewer_profile is not None and getattr(viewer_profile, "id", None) is not None:
            is_self = str(viewer_profile.id) == str(getattr(target_profile, "id", None))

        computed_target_scope = target_scope
        if computed_target_scope is None:
            try:
                computed_target_scope = OfficerHierarchy.scope_from_profile(target_profile)
            except OfficerScopeError:
                computed_target_scope = None

        same_rank = False
        if viewer_scope is not None and computed_target_scope is not None:
            same_rank = viewer_scope.rank == computed_target_scope.rank

        if viewer_scope is None:
            # Non-officer actors bypass scope checks in service-level logic.
            can_manage = True
        else:
            can_manage = False
            if computed_target_scope is not None:
                can_manage = OfficerHierarchy.can_manage(viewer_scope, computed_target_scope)

        can_edit = bool(is_self)
        if not is_self:
            if viewer_scope is None:
                can_edit = True
            else:
                can_edit = can_manage and not same_rank

        can_perform_strict_actions = (viewer_scope is None and not is_self) or (can_manage and not same_rank and not is_self)
        can_approve = (viewer_scope is None and not is_self) or (can_manage and not is_self)
        can_transfer = False
        if viewer_scope is None:
            can_transfer = not is_self
        else:
            allow_same_level_transfer = viewer_scope.level in [AdministrativeLevelEnum.SUBDISTRICT, AdministrativeLevelEnum.VILLAGE]
            can_transfer = (
                can_manage
                and (allow_same_level_transfer or not same_rank)
                and not is_self
            )

        return {
            "can_edit": bool(can_edit),
            "can_toggle_active": bool(can_perform_strict_actions),
            "can_reset_password": bool(can_perform_strict_actions),
            "can_delete": bool(can_perform_strict_actions),
            "can_approve": bool(can_approve),
            "can_manage": bool(can_manage and not is_self),
            "can_transfer": bool(can_transfer),
            "is_self": bool(is_self),
            "is_same_level": bool(same_rank),
        }

    @staticmethod
    def _ensure_transfer_destination_permission(
        viewer_scope: OfficerScope,
        current_scope: OfficerScope,
        new_scope: OfficerScope,
    ) -> None:
        def _raise_forbidden(detail: str) -> None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

        level = viewer_scope.level

        if level == AdministrativeLevelEnum.COUNTRY:
            return

        if level == AdministrativeLevelEnum.REGION:
            if viewer_scope.region_code is None:
                _raise_forbidden("insufficient_scope_transfer")
            if current_scope.region_code != viewer_scope.region_code:
                _raise_forbidden("insufficient_scope_transfer")
            if new_scope.region_code != viewer_scope.region_code:
                _raise_forbidden("insufficient_scope_transfer")
            return

        if level == AdministrativeLevelEnum.AREA:
            if viewer_scope.health_area_id is None:
                _raise_forbidden("insufficient_scope_transfer")
            if current_scope.health_area_id != viewer_scope.health_area_id:
                _raise_forbidden("insufficient_scope_transfer")
            if new_scope.health_area_id != viewer_scope.health_area_id:
                _raise_forbidden("insufficient_scope_transfer")
            return

        if level == AdministrativeLevelEnum.PROVINCE:
            if viewer_scope.province_id is None:
                _raise_forbidden("insufficient_scope_transfer")
            if current_scope.province_id != viewer_scope.province_id:
                _raise_forbidden("insufficient_scope_transfer")
            if new_scope.province_id != viewer_scope.province_id:
                _raise_forbidden("insufficient_scope_transfer")
            return

        if level == AdministrativeLevelEnum.DISTRICT:
            if viewer_scope.district_id is None:
                _raise_forbidden("insufficient_scope_transfer")
            if current_scope.district_id != viewer_scope.district_id:
                _raise_forbidden("insufficient_scope_transfer")
            if new_scope.district_id != viewer_scope.district_id:
                _raise_forbidden("insufficient_scope_transfer")
            if new_scope.level not in [AdministrativeLevelEnum.SUBDISTRICT, AdministrativeLevelEnum.VILLAGE]:
                _raise_forbidden("insufficient_scope_transfer")
            return

        if level == AdministrativeLevelEnum.SUBDISTRICT:
            if viewer_scope.subdistrict_id is None:
                _raise_forbidden("insufficient_scope_transfer")
            if current_scope.subdistrict_id != viewer_scope.subdistrict_id:
                _raise_forbidden("insufficient_scope_transfer")
            if new_scope.subdistrict_id != viewer_scope.subdistrict_id:
                _raise_forbidden("insufficient_scope_transfer")
            if not new_scope.health_service_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_service_required")
            return

        if level == AdministrativeLevelEnum.VILLAGE:
            if viewer_scope.subdistrict_id is None:
                _raise_forbidden("insufficient_scope_transfer")
            if current_scope.subdistrict_id != viewer_scope.subdistrict_id:
                _raise_forbidden("insufficient_scope_transfer")
            if new_scope.subdistrict_id != viewer_scope.subdistrict_id:
                _raise_forbidden("insufficient_scope_transfer")
            if not new_scope.health_service_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_service_required")
            return

    @staticmethod
    def _ensure_position_based_transfer_boundary(viewer_profile, current_scope: OfficerScope, new_scope: OfficerScope) -> None:
        if viewer_profile is None:
            return

        position = getattr(viewer_profile, "position", None)
        raw_scope_level = getattr(position, "scope_level", None) if position is not None else None
        if raw_scope_level is None:
            return

        try:
            position_level = (
                raw_scope_level
                if isinstance(raw_scope_level, AdministrativeLevelEnum)
                else AdministrativeLevelEnum(str(raw_scope_level))
            )
        except ValueError:
            return

        area_type = OfficerService._enum_value(getattr(viewer_profile, "area_type", None))
        position_name_th = (
            getattr(position, "position_name_th", None)
            if position is not None
            else None
        )
        normalized_position_name = str(position_name_th or "").strip()

        is_district_position = position_level == AdministrativeLevelEnum.DISTRICT
        is_district_area_type = area_type == AdministrativeLevelEnum.DISTRICT.value
        is_district_named_position = (
            bool(normalized_position_name)
            and "อำเภอ" in normalized_position_name
            and "จังหวัด" not in normalized_position_name
            and "เขต" not in normalized_position_name
            and "ภาค" not in normalized_position_name
            and "ประเทศ" not in normalized_position_name
        )

        if not (is_district_position or is_district_area_type or is_district_named_position):
            return

        viewer_district_id = OfficerService._normalize_code(getattr(viewer_profile, "district_id", None))
        if not viewer_district_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_transfer")

        if current_scope.district_id != viewer_district_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_transfer")

        if new_scope.district_id != viewer_district_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_transfer")

    @staticmethod
    async def transfer_officer(officer_id: str, transfer_data, current_user: dict):
        existing = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        is_self = viewer_profile is not None and str(viewer_profile.id) == str(existing.id)
        if is_self:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_self_action")

        payload = transfer_data.model_dump(exclude_unset=True)
        note = payload.pop("note", None)
        payload = OfficerService._clean_blank_strings(payload)
        if not payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="transfer_payload_required")

        if "health_area_id" in payload and "province_id" not in payload:
            payload["province_id"] = None
            payload["district_id"] = None
            payload["subdistrict_id"] = None
            payload["health_service_id"] = None
        if "province_id" in payload and "district_id" not in payload:
            payload["district_id"] = None
            payload["subdistrict_id"] = None
            payload["health_service_id"] = None
        if "district_id" in payload and "subdistrict_id" not in payload:
            payload["subdistrict_id"] = None
            payload["health_service_id"] = None
        if "subdistrict_id" in payload and "health_service_id" not in payload:
            payload["health_service_id"] = None

        current_scope = OfficerHierarchy.scope_from_profile(existing)
        if viewer_scope is not None:
            allow_same_level_transfer = viewer_scope.level in [AdministrativeLevelEnum.SUBDISTRICT, AdministrativeLevelEnum.VILLAGE]
            OfficerService._ensure_scope_permission(
                viewer_scope,
                current_scope,
                require_strict=not allow_same_level_transfer,
                allow_same_level=allow_same_level_transfer,
            )

        combined_location = {
            "area_type": OfficerService._enum_value(existing.area_type),
            "province_id": payload.get("province_id", existing.province_id),
            "district_id": payload.get("district_id", existing.district_id),
            "subdistrict_id": payload.get("subdistrict_id", existing.subdistrict_id),
            "area_code": existing.area_code,
            "health_area_id": payload.get("health_area_id", getattr(existing, "health_area_id", None)),
            "health_service_id": payload.get("health_service_id", getattr(existing, "health_service_id", None)),
        }
        combined_location = await OfficerService._augment_location_context(combined_location)
        combined_location = await OfficerService._auto_resolve_health_service(combined_location)

        if (
            combined_location.get("area_type") == AdministrativeLevelEnum.SUBDISTRICT.value
            and not combined_location.get("health_service_id")
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_service_required")

        try:
            new_scope = OfficerHierarchy.scope_from_payload(combined_location)
        except OfficerScopeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        if viewer_scope is not None:
            allow_same_level_transfer = viewer_scope.level in [AdministrativeLevelEnum.SUBDISTRICT, AdministrativeLevelEnum.VILLAGE]
            OfficerService._ensure_scope_permission(
                viewer_scope,
                new_scope,
                require_strict=not allow_same_level_transfer,
                allow_same_level=allow_same_level_transfer,
            )
            OfficerService._ensure_position_based_transfer_boundary(viewer_profile, current_scope, new_scope)
            OfficerService._ensure_transfer_destination_permission(viewer_scope, current_scope, new_scope)

        update_payload = {
            "province_id": combined_location.get("province_id"),
            "district_id": combined_location.get("district_id"),
            "subdistrict_id": combined_location.get("subdistrict_id"),
            "health_service_id": combined_location.get("health_service_id"),
            "health_area_id": combined_location.get("health_area_id"),
            "area_type": combined_location.get("area_type"),
        }

        old_province_name = getattr(getattr(existing, "province", None), "province_name_th", None)
        old_district_name = getattr(getattr(existing, "district", None), "district_name_th", None)
        old_subdistrict_name = getattr(getattr(existing, "subdistrict", None), "subdistrict_name_th", None)
        old_health_service_name = getattr(getattr(existing, "health_service", None), "health_service_name_th", None)
        old_health_area_name = getattr(getattr(existing, "health_area", None), "health_area_name_th", None)

        new_province_name = None
        new_district_name = None
        new_subdistrict_name = None
        new_health_service_name = None
        new_health_area_name = None

        if update_payload.get("province_id"):
            province = await Province.filter(province_code=update_payload.get("province_id")).first()
            if province:
                new_province_name = province.province_name_th
        if update_payload.get("district_id"):
            district = await District.filter(district_code=update_payload.get("district_id")).first()
            if district:
                new_district_name = district.district_name_th
        if update_payload.get("subdistrict_id"):
            subdistrict = await Subdistrict.filter(subdistrict_code=update_payload.get("subdistrict_id")).first()
            if subdistrict:
                new_subdistrict_name = subdistrict.subdistrict_name_th
        if update_payload.get("health_service_id"):
            health_service = await HealthService.filter(health_service_code=update_payload.get("health_service_id")).first()
            if health_service:
                new_health_service_name = health_service.health_service_name_th
        if update_payload.get("health_area_id"):
            health_area = await HealthArea.filter(code=update_payload.get("health_area_id")).first()
            if health_area:
                new_health_area_name = health_area.health_area_name_th

        updated = await OfficerProfileRepository.update_officer(officer_id, update_payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="update_failed")

        actor_id = None
        if viewer_profile is not None:
            actor_id = str(viewer_profile.id)
        elif current_user.get("user_id"):
            actor_id = str(current_user.get("user_id"))

        await AuditService.log_action(
            user_id=actor_id,
            action_type="transfer",
            target_type="officer",
            description="โยกย้ายเจ้าหน้าที่",
            old_data={
                "officerId": officer_id,
                "area_type": OfficerService._enum_value(existing.area_type),
                "health_area_id": getattr(existing, "health_area_id", None),
                "health_area_name_th": old_health_area_name,
                "province_id": existing.province_id,
                "province_name_th": old_province_name,
                "district_id": existing.district_id,
                "district_name_th": old_district_name,
                "subdistrict_id": existing.subdistrict_id,
                "subdistrict_name_th": old_subdistrict_name,
                "health_service_id": existing.health_service_id,
                "health_service_name_th": old_health_service_name,
            },
            new_data={
                "officerId": officer_id,
                "area_type": update_payload.get("area_type"),
                "health_area_id": update_payload.get("health_area_id"),
                "health_area_name_th": new_health_area_name,
                "province_id": update_payload.get("province_id"),
                "province_name_th": new_province_name,
                "district_id": update_payload.get("district_id"),
                "district_name_th": new_district_name,
                "subdistrict_id": update_payload.get("subdistrict_id"),
                "subdistrict_name_th": new_subdistrict_name,
                "health_service_id": update_payload.get("health_service_id"),
                "health_service_name_th": new_health_service_name,
                "note": note,
            },
        )

        refreshed = await OfficerProfileRepository.get_officer_by_id(officer_id)
        permissions = OfficerService._build_permission_snapshot(viewer_profile, viewer_scope, refreshed)
        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(officer_id)
        except Exception:
            pass
        return {
            "status": "success",
            "data": officer_to_response(refreshed, permissions=permissions),
            "message": "โยกย้ายเจ้าหน้าที่สำเร็จ",
        }

    @staticmethod
    async def get_transfer_history(officer_id: str, page: int, page_size: int, current_user: dict):
        existing = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is not None:
            await OfficerService._ensure_visibility_permission_for_officer(viewer_scope, officer_id)

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        query = AdminAuditLog.filter(
            target_type="officer",
            action_type="transfer",
            new_data__contains={"officerId": officer_id},
        ).order_by("-created_at")

        total = await query.count()
        logs = await query.offset((page - 1) * page_size).limit(page_size)

        items = [
            {
                "id": str(log.id),
                "timestamp": log.created_at.isoformat() if isinstance(log.created_at, datetime) else str(log.created_at),
                "action": log.action_type,
                "description": log.description,
                "by": str(log.user_id) if getattr(log, "user_id", None) else None,
                "success": log.success,
                "old_data": log.old_data,
                "new_data": log.new_data,
            }
            for log in logs
        ]

        return {
            "status": "success",
            "message": "transfer_history_fetched",
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def list_officers(filter_params: OfficerQueryParams, current_user: dict):
        visibility_filter = None
        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user)
        if viewer_scope:
            try:
                visibility_filter = OfficerHierarchy.build_visibility_filter(viewer_scope)
            except OfficerScopeError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        viewer_id = str(current_user.get("user_id")) if current_user.get("user_id") else None
        manageable_levels = None
        if viewer_scope:
            manageable_levels = OfficerHierarchy.manageable_levels(viewer_scope)

        officers, total_count = await OfficerProfileRepository.list_officers(
            filter_params,
            visibility_filter=visibility_filter,
            manageable_levels=manageable_levels,
            exclude_ids=[viewer_id] if viewer_id else None,
        )

        officer_responses = []
        for officer in officers:
            target_scope = None
            permissions_payload = None
            if viewer_scope is not None or viewer_profile is not None:
                try:
                    target_scope = OfficerHierarchy.scope_from_profile(officer)
                except OfficerScopeError:
                    target_scope = None
                permissions_payload = OfficerService._build_permission_snapshot(
                    viewer_profile,
                    viewer_scope,
                    officer,
                    target_scope,
                )
            officer_responses.append(
                officer_to_list_response(
                    officer,
                    permissions=permissions_payload,
                )
            )
        total_pages = 0
        if filter_params.limit > 0 and total_count > 0:
            total_pages = (total_count + filter_params.limit - 1) // filter_params.limit

        return {
            "items": officer_responses,
            "pagination": {
                "page": filter_params.page,
                "limit": filter_params.limit,
                "total": total_count,
                "pages": total_pages,
            },
        }

    @staticmethod
    async def create_officer(officer: OfficerCreateSchema, creator: dict):
        # Prevent duplicate citizen_id
        existing = await OfficerProfileRepository.find_any_officer_by_citizen_id(officer.citizen_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="citizen_id_already_exists",
            )

        creator_id_raw = creator.get("user_id")
        if not creator_id_raw:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="creator_missing")
        creator_id = str(creator_id_raw)
        _, creator_scope = await OfficerService._resolve_officer_scope(creator, require_active=True)

        payload = officer.model_dump()
        optional_fields = (
            "gender",
            "birth_date",
            "province_id",
            "district_id",
            "subdistrict_id",
            "municipality_id",
            "health_area_id",
            "health_service_id",
            "area_code",
            "village_no",
            "alley",
            "street",
            "profile_image",
        )
        payload = OfficerService._clean_blank_strings(payload, optional_fields)

        password_plain = payload.pop("password", None)
        if not password_plain:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_required")

        payload["password_hash"] = bcrypt_hash_password(password_plain)
        payload["is_first_login"] = False

        position = await OfficerService._load_position(payload.get("position_id"))
        if getattr(position, "scope_level", None) == AdministrativeLevelEnum.SUBDISTRICT and not payload.get("health_service_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="health_service_required")
        payload["area_type"] = OfficerService._resolve_area_type(
            position_scope=getattr(position, "scope_level", None),
            provided=payload.get("area_type"),
            fallback=None,
        )

        payload = await OfficerService._augment_location_context(payload)
        payload = await OfficerService._auto_resolve_health_service(payload)
        payload = OfficerService._clean_blank_strings(payload, optional_fields)
        payload, area_adjusted, previous_level, resolved_level = OfficerService._reconcile_area_scope(payload)
        if area_adjusted:
            log_info(
                logger,
                "Adjusted officer area_type to match available location data",
                previous_level=previous_level.value if isinstance(previous_level, AdministrativeLevelEnum) else previous_level,
                resolved_level=resolved_level.value if resolved_level else None,
            )
            auto_approve = False

        try:
            target_scope = OfficerHierarchy.scope_from_payload(payload)
        except OfficerScopeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        payload.pop("region_code", None)

        auto_approve = False
        if creator_scope:
            try:
                OfficerService._ensure_scope_permission(creator_scope, target_scope)
                auto_approve = True
            except HTTPException as scope_error:
                is_scope_denied = (
                    scope_error.status_code == status.HTTP_403_FORBIDDEN
                    and scope_error.detail in {"insufficient_scope", "insufficient_scope_same_level"}
                )
                if not is_scope_denied:
                    raise
                log_error(
                    logger,
                    "Creator lacks management scope for auto-approval; falling back to pending approval",
                    extra={
                        "creator_id": creator_id,
                        "creator_scope": creator_scope,
                        "target_payload": payload,
                    },
                )

        if auto_approve:
            payload["approval_status"] = ApprovalStatus.APPROVED.value
            payload["approval_by"] = str(creator_id)
            payload["approval_date"] = datetime.utcnow().date()
            payload["is_active"] = True
        else:
            payload["approval_status"] = ApprovalStatus.PENDING.value
            payload["approval_by"] = None
            payload["is_active"] = False
            payload["approval_date"] = None

        created = await OfficerProfileRepository.create_officer(payload)

        # Notify relevant officers about new officer creation
        action = "create" if auto_approve else "register"
        await NotificationService.create_notification_from_officer_profile(
            actor_id=creator_id,
            action_type=action,
            officer_profile=created,
        )

        return {
            "status": "success",
            "data": officer_to_response(created),
            "message": "สร้าง Officer Profile สำเร็จ",
        }

    @staticmethod
    async def register_officer(officer: OfficerCreateSchema):
        existing = await OfficerProfileRepository.find_any_officer_by_citizen_id(officer.citizen_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="citizen_id_already_exists",
            )

        payload = officer.model_dump()
        optional_fields = (
            "gender",
            "birth_date",
            "province_id",
            "district_id",
            "subdistrict_id",
            "municipality_id",
            "health_area_id",
            "health_service_id",
            "area_code",
            "village_no",
            "alley",
            "street",
            "profile_image",
        )
        payload = OfficerService._clean_blank_strings(payload, optional_fields)
        password_plain = payload.pop("password", None)
        if not password_plain:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_required")

        payload["password_hash"] = bcrypt_hash_password(password_plain)
        payload["is_first_login"] = False

        position = await OfficerService._load_position(payload.get("position_id"))
        payload["area_type"] = OfficerService._resolve_area_type(
            position_scope=getattr(position, "scope_level", None),
            provided=payload.get("area_type"),
            fallback=None,
        )

        payload = await OfficerService._augment_location_context(payload)
        payload = await OfficerService._auto_resolve_health_service(payload)
        payload = OfficerService._clean_blank_strings(payload, optional_fields)

        try:
            OfficerHierarchy.scope_from_payload(payload)
        except OfficerScopeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        payload.pop("region_code", None)
        payload["approval_status"] = ApprovalStatus.PENDING.value
        payload["approval_by"] = None
        payload["approval_date"] = None
        payload["is_active"] = False

        created = await OfficerProfileRepository.create_officer(payload)

        # Notify relevant officers about new self-registration (pending approval)
        await NotificationService.create_notification_from_officer_profile(
            actor_id=None,  # self-registration, no actor (shown as "ระบบ")
            action_type="register",
            officer_profile=created,
        )

        return {
            "status": "success",
            "message": "ลงทะเบียนสำเร็จ กรุณารอผู้มีสิทธิ์อนุมัติ",
            "data": {"id": str(created.id)},
        }

    @staticmethod
    async def get_officer_by_id(officer_id: str, current_user: dict):
        officer = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not officer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user)
        target_scope = None
        if viewer_scope:
            await OfficerService._ensure_visibility_permission_for_officer(viewer_scope, officer_id)
            try:
                target_scope = OfficerHierarchy.scope_from_profile(officer)
            except OfficerScopeError:
                target_scope = None

        permissions = OfficerService._build_permission_snapshot(viewer_profile, viewer_scope, officer, target_scope)

        return {
            "status": "success",
            "data": officer_to_response(officer, permissions=permissions),
            "message": "ดึงข้อมูล Officer Profile สำเร็จ",
        }

    @staticmethod
    async def get_officers_by_ids(officer_ids: List[str], current_user: dict):
        if not officer_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids_required")

        unique_ids = list(dict.fromkeys(officer_ids))
        items: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        for officer_id in unique_ids:
            try:
                result = await OfficerService.get_officer_by_id(officer_id, current_user)
                items.append(result.get("data"))
            except HTTPException as exc:
                errors.append({"id": officer_id, "error": str(exc.detail)})

        return {
            "status": "success",
            "data": items,
            "errors": errors,
            "message": "ดึงข้อมูล Officer Profiles สำเร็จ",
        }

    @staticmethod
    async def update_officer(officer_id: str, update_data: OfficerUpdateSchema, current_user: dict):
        existing = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        is_self_update = viewer_profile is not None and str(viewer_profile.id) == str(existing.id)

        if viewer_scope and not is_self_update:
            try:
                target_scope = OfficerHierarchy.scope_from_profile(existing)
            except OfficerScopeError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        payload = update_data.model_dump(exclude_unset=True)

        existing_position = getattr(existing, "position", None)
        position_scope = getattr(existing_position, "scope_level", None)
        if "position_id" in payload:
            new_position = await OfficerService._load_position(payload["position_id"])
            position_scope = getattr(new_position, "scope_level", None)

        resolved_area_type = OfficerService._resolve_area_type(
            position_scope=position_scope,
            provided=payload.get("area_type"),
            fallback=existing.area_type,
        )
        current_area_type = OfficerService._enum_value(existing.area_type)
        if (
            "area_type" in payload
            or "position_id" in payload
            or resolved_area_type != current_area_type
        ):
            payload["area_type"] = resolved_area_type

        location_fields = {
            "area_type",
            "province_id",
            "district_id",
            "subdistrict_id",
            "area_code",
            "health_area_id",
            "position_id",
        }
        if any(field in payload for field in location_fields):
            combined_location = {
                "area_type": payload.get("area_type", resolved_area_type),
                "province_id": payload.get("province_id", existing.province_id),
                "district_id": payload.get("district_id", existing.district_id),
                "subdistrict_id": payload.get("subdistrict_id", existing.subdistrict_id),
                "area_code": payload.get("area_code", existing.area_code),
                "health_area_id": payload.get("health_area_id", getattr(existing, "health_area_id", None)),
            }

            combined_location = await OfficerService._augment_location_context(combined_location)
            combined_location = await OfficerService._auto_resolve_health_service(combined_location)

            try:
                new_scope = OfficerHierarchy.scope_from_payload(combined_location)
            except OfficerScopeError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

            if viewer_scope and not is_self_update:
                OfficerService._ensure_scope_permission(viewer_scope, new_scope, require_strict=True)

            combined_location.pop("region_code", None)
            for key in ("province_id", "district_id", "subdistrict_id", "area_code", "health_area_id", "health_service_id"):
                if key in combined_location:
                    value = combined_location.get(key)
                    if value is None:
                        payload.pop(key, None)
                    else:
                        payload[key] = value

        # Ensure approval_by is set if approval_status changes without explicit approver
        if "approval_status" in payload and "approval_by" not in payload:
            payload["approval_by"] = str(current_user.get("user_id"))

        updated = await OfficerProfileRepository.update_officer(officer_id, payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="update_failed")

        refreshed = await OfficerProfileRepository.get_officer_by_id(officer_id)
        permissions = OfficerService._build_permission_snapshot(viewer_profile, viewer_scope, refreshed)
        await cache_delete_pattern("dashboard:*")
        return {
            "status": "success",
            "data": officer_to_response(refreshed, permissions=permissions),
            "message": "อัปเดตข้อมูล Officer Profile สำเร็จ",
        }

    @staticmethod
    async def set_active_status(officer_id: str, is_active: bool, current_user: dict):
        existing = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)

        if viewer_profile and str(viewer_profile.id) == str(existing.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_self_action")

        if viewer_scope:
            try:
                target_scope = OfficerHierarchy.scope_from_profile(existing)
            except OfficerScopeError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        actor_id = None
        if viewer_profile:
            actor_id = str(viewer_profile.id)
        elif current_user.get("user_id"):
            actor_id = str(current_user.get("user_id"))

        updated = await OfficerProfileRepository.update_officer(
            officer_id,
            {
                "is_active": is_active,
                "active_status_by": actor_id,
                "active_status_at": datetime.utcnow(),
            },
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="update_failed")

        refreshed = await OfficerProfileRepository.get_officer_by_id(officer_id)
        permissions = OfficerService._build_permission_snapshot(viewer_profile, viewer_scope, refreshed)
        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(officer_id)
        except Exception:
            pass
        return {
            "status": "success",
            "data": officer_to_response(refreshed, permissions=permissions),
            "message": "อัปเดตสถานะการใช้งาน Officer สำเร็จ",
        }

    @staticmethod
    async def _apply_approval_decision(
        officer_id: str,
        decision: ApprovalStatus,
        current_user: dict,
        note: Optional[str] = None,
    ):
        officer = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not officer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        approver_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None or approver_profile is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope")

        try:
            target_scope = OfficerHierarchy.scope_from_profile(officer)
        except OfficerScopeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        if str(approver_profile.id) == str(officer.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_self_action")

        OfficerService._ensure_scope_permission(
            viewer_scope,
            target_scope,
            require_strict=True,
            allow_same_level=(decision == ApprovalStatus.APPROVED),
        )

        current_status_raw = OfficerService._enum_value(officer.approval_status)
        current_status_enum = None
        if current_status_raw:
            try:
                current_status_enum = ApprovalStatus(current_status_raw)
            except ValueError:
                current_status_enum = None

        if decision == ApprovalStatus.APPROVED and current_status_enum == ApprovalStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already_approved")
        if decision == ApprovalStatus.REJECTED and current_status_enum == ApprovalStatus.REJECTED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already_rejected")

        update_payload = {
            "approval_status": decision.value,
            "approval_by": str(approver_profile.id),
            "approval_date": datetime.utcnow().date(),
            "is_active": decision == ApprovalStatus.APPROVED,
            "active_status_by": str(approver_profile.id),
            "active_status_at": datetime.utcnow(),
        }

        updated = await OfficerProfileRepository.update_officer(officer_id, update_payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="update_failed")

        refreshed = await OfficerProfileRepository.get_officer_by_id(officer_id)
        permissions = OfficerService._build_permission_snapshot(approver_profile, viewer_scope, refreshed)
        message = "อนุมัติคำขอสำเร็จ" if decision == ApprovalStatus.APPROVED else "ปฏิเสธคำขอสำเร็จ"
        if note:
            logger.info("Officer %s approval decision %s with note: %s", officer_id, decision.value, note)

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(officer_id)
        except Exception:
            pass

        # Notify relevant officers about approval/rejection decision
        action_type = "approve" if decision == ApprovalStatus.APPROVED else "reject"
        await NotificationService.create_notification_from_officer_profile(
            actor_id=str(approver_profile.id),
            action_type=action_type,
            officer_profile=refreshed,
        )

        return {
            "status": "success",
            "data": officer_to_response(refreshed, permissions=permissions),
            "message": message,
        }

    @staticmethod
    async def approve_officer(
        officer_id: str,
        payload: OfficerApprovalActionSchema,
        current_user: dict,
    ):
        note = payload.note if payload else None
        return await OfficerService._apply_approval_decision(
            officer_id,
            ApprovalStatus.APPROVED,
            current_user,
            note,
        )

    @staticmethod
    async def reject_officer(
        officer_id: str,
        payload: OfficerApprovalActionSchema,
        current_user: dict,
    ):
        note = payload.note if payload else None
        return await OfficerService._apply_approval_decision(
            officer_id,
            ApprovalStatus.REJECTED,
            current_user,
            note,
        )

    @staticmethod
    async def soft_delete_officer(officer_id: str, current_user: dict):
        existing = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_profile and str(viewer_profile.id) == str(existing.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_self_action")

        if viewer_scope:
            try:
                target_scope = OfficerHierarchy.scope_from_profile(existing)
            except OfficerScopeError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        deleted = await OfficerProfileRepository.soft_delete_officer(officer_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")
        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(officer_id)
        except Exception:
            pass
        return {
            "status": "success",
            "message": "ลบ Officer Profile สำเร็จ",
        }

    @staticmethod
    async def reset_password(officer_id: str, current_user: dict):
        existing = await OfficerProfileRepository.get_officer_by_id(officer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")

        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_profile and str(viewer_profile.id) == str(existing.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_self_action")

        if viewer_scope:
            try:
                target_scope = OfficerHierarchy.scope_from_profile(existing)
            except OfficerScopeError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        temp_password = OfficerService._generate_temporary_password()
        hashed_password = bcrypt_hash_password(temp_password)

        updated = await OfficerProfileRepository.set_password_by_id(
            officer_id,
            hashed_password,
            mark_first_login=True,
            reset_attempts=True,
            reactivate=True,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_reset_failed")

        try:
            await RefreshTokenRepository.revoke_all_user_refresh_tokens(officer_id, None, "officer")
        except Exception as exc:
            log_error(logger, "reset_password revoke tokens failed", exc=exc)
        try:
            await invalidate_user_sessions(officer_id)
        except Exception:
            pass

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="reset_password",
            target_type="officer",
            description=f"Officer reset password for officer {officer_id}",
            new_data={
                "officerId": officer_id,
            },
        )

        return {
            "status": "success",
            "data": {
                "temporary_password": temp_password,
            },
            "message": "รีเซ็ตรหัสผ่านสำเร็จ",
        }

    @staticmethod
    async def reset_yuwa_password(user_id: str, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            await OfficerService._ensure_visibility_permission_for_officer(viewer_scope, officer_id)
        target_profile = await YuwaOSMUserRepository.get_user_for_management(user_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        target_scope, location_context = await OfficerService._resolve_yuwa_management_context(target_profile)

        OfficerService._ensure_scope_permission(viewer_scope, target_scope)

        temp_password = OfficerService._generate_temporary_password()
        hashed_password = bcrypt_hash_password(temp_password)

        updated = await YuwaOSMUserRepository.set_password_by_id(
            user_id,
            hashed_password,
            mark_first_login=True,
            reactivate=True,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_reset_failed")

        try:
            await RefreshTokenRepository.revoke_all_user_refresh_tokens(user_id, None, "yuwa_osm")
        except Exception as exc:
            log_error(logger, "reset_password revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="reset_password",
            target_type="yuwa_osm",
            description=f"Officer reset password for Yuwa OSM user {user_id}",
            new_data={
                "yuwaUserId": user_id,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        return {
            "status": "success",
            "data": {
                "temporary_password": temp_password,
            },
            "message": "รีเซ็ตรหัสผ่านสำเร็จ",
        }

    @staticmethod
    async def reset_people_password(user_id: str, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        target_profile = await PeopleUserRepository.get_user_for_management(user_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="people_user_not_found")

        target_scope, location_context = await OfficerService._resolve_people_management_context(target_profile)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope)

        temp_password = OfficerService._generate_temporary_password()
        hashed_password = bcrypt_hash_password(temp_password)

        updated = await PeopleUserRepository.set_password_by_id(
            user_id,
            hashed_password,
            mark_first_login=True,
            reactivate=True,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_reset_failed")

        try:
            await RefreshTokenRepository.revoke_all_user_refresh_tokens(user_id, None, "people")
        except Exception as exc:
            log_error(logger, "reset_password revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="reset_password",
            target_type="people",
            description=f"Officer reset password for People user {user_id}",
            new_data={
                "peopleUserId": user_id,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        return {
            "status": "success",
            "data": {
                "temporary_password": temp_password,
            },
            "message": "รีเซ็ตรหัสผ่านสำเร็จ",
        }

    @staticmethod
    async def reset_osm_password(osm_id: str, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        target_profile = await OSMProfileRepository.get_profile_for_management(osm_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="osm_not_found")

        target_scope, location_context = await OfficerService._resolve_osm_management_context(target_profile)

        OfficerService._ensure_scope_permission(viewer_scope, target_scope)

        temp_password = OfficerService._generate_temporary_password()
        hashed_password = bcrypt_hash_password(temp_password)

        updated = await OSMProfileRepository.set_password_by_id(
            osm_id,
            hashed_password,
            mark_first_login=True,
            reactivate=True,
            updated_by=str(current_user.get("user_id")) if current_user.get("user_id") else None,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_reset_failed")

        try:
            await RefreshTokenRepository.revoke_all_user_refresh_tokens(osm_id, None, "osm")
        except Exception as exc:
            log_error(logger, "reset_password revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="reset_password",
            target_type="osm",
            description=f"Officer reset password for OSM profile {osm_id}",
            new_data={
                "osmProfileId": osm_id,
                "provinceId": location_context.get("province_code"),
                "districtId": location_context.get("district_code"),
                "subdistrictId": location_context.get("subdistrict_code"),
                "villageCode": location_context.get("village_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        return {
            "status": "success",
            "data": {
                "temporary_password": temp_password,
            },
            "message": "รีเซ็ตรหัสผ่านสำเร็จ",
        }

    @staticmethod
    async def set_yuwa_active_status(user_id: str, is_active: bool, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        target_profile = await YuwaOSMUserRepository.get_user_for_management(user_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        target_scope, location_context = await OfficerService._resolve_yuwa_management_context(target_profile)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        updated = await YuwaOSMUserRepository.set_active_status(user_id, is_active)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status_update_failed")

        if not is_active:
            try:
                await RefreshTokenRepository.revoke_all_user_refresh_tokens(user_id, None, "yuwa_osm")
            except Exception as exc:
                log_error(logger, "toggle_yuwa_status revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="set_active_status",
            target_type="yuwa_osm",
            description=f"Officer updated Yuwa OSM active status for user {user_id}",
            new_data={
                "yuwaUserId": user_id,
                "isActive": is_active,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(user_id)
        except Exception:
            pass
        message = "เปิดใช้งานบัญชีสำเร็จ" if is_active else "ปิดใช้งานบัญชีสำเร็จ"
        return {
            "status": "success",
            "data": {
                "is_active": is_active,
            },
            "message": message,
        }

    @staticmethod
    async def set_people_active_status(user_id: str, is_active: bool, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        target_profile = await PeopleUserRepository.get_user_for_management(user_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="people_user_not_found")

        target_scope, location_context = await OfficerService._resolve_people_management_context(target_profile)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        # Prevent re-activating a transferred People account — data now lives in yuwa_osm
        if is_active and getattr(target_profile, "is_transferred", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="people_already_transferred",
            )

        updated = await PeopleUserRepository.set_active_status(user_id, is_active)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status_update_failed")

        if not is_active:
            try:
                await RefreshTokenRepository.revoke_all_user_refresh_tokens(user_id, None, "people")
            except Exception as exc:
                log_error(logger, "toggle_people_status revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="set_active_status",
            target_type="people",
            description=f"Officer updated People active status for user {user_id}",
            new_data={
                "peopleUserId": user_id,
                "isActive": is_active,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        try:
            await invalidate_user_sessions(user_id)
        except Exception:
            pass
        message = "เปิดใช้งานบัญชีสำเร็จ" if is_active else "ปิดใช้งานบัญชีสำเร็จ"
        return {
            "status": "success",
            "data": {
                "is_active": is_active,
            },
            "message": message,
        }

    @staticmethod
    async def set_osm_active_status(osm_id: str, is_active: bool, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        target_profile = await OSMProfileRepository.get_profile_for_management(osm_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="osm_not_found")

        target_scope, location_context = await OfficerService._resolve_osm_management_context(target_profile)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        updated = await OSMProfileRepository.set_active_status(
            osm_id,
            is_active,
            str(current_user.get("user_id")) if current_user.get("user_id") else None,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status_update_failed")

        if not is_active:
            try:
                await RefreshTokenRepository.revoke_all_user_refresh_tokens(osm_id, None, "osm")
            except Exception as exc:
                log_error(logger, "toggle_osm_status revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="set_active_status",
            target_type="osm",
            description=f"Officer updated OSM active status for profile {osm_id}",
            new_data={
                "osmProfileId": osm_id,
                "isActive": is_active,
                "provinceId": location_context.get("province_code"),
                "districtId": location_context.get("district_code"),
                "subdistrictId": location_context.get("subdistrict_code"),
                "villageCode": location_context.get("village_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(osm_id)
        except Exception:
            pass
        message = "เปิดใช้งานบัญชีสำเร็จ" if is_active else "ปิดใช้งานบัญชีสำเร็จ"
        return {
            "status": "success",
            "data": {
                "is_active": is_active,
            },
            "message": message,
        }

    @staticmethod
    async def _resolve_gen_h_management_context(profile) -> tuple[OfficerScope, Dict[str, Optional[str]]]:
        province_code = OfficerService._normalize_code(getattr(profile, "province_code", None))
        district_code = OfficerService._normalize_code(getattr(profile, "district_code", None))
        subdistrict_code = OfficerService._normalize_code(getattr(profile, "subdistrict_code", None))

        province = None
        if province_code:
            province = await Province.filter(province_code=province_code).first()

        district = None
        if district_code:
            district = await District.filter(district_code=district_code).select_related("province").first()
            if district and not province:
                province = getattr(district, "province", None)

        if province and not province_code:
            province_code = OfficerService._normalize_code(getattr(province, "province_code", None))

        health_area_id = OfficerService._normalize_code(getattr(province, "health_area_id", None)) if province else None
        region_code = OfficerService._normalize_code(getattr(province, "region_id", None)) if province else None

        target_scope = OfficerService._build_scope_from_geography(
            region_code=region_code,
            health_area_id=health_area_id,
            province_id=province_code,
            district_id=district_code,
            subdistrict_id=subdistrict_code,
        )

        context = {
            "province_code": province_code,
            "district_code": district_code,
            "subdistrict_code": subdistrict_code,
            "health_area_id": health_area_id,
            "region_code": region_code,
        }
        return target_scope, context

    @staticmethod
    async def reset_gen_h_password(user_id: str, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        target_profile = await GenHUserRepository.get_by_id(user_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="gen_h_user_not_found")

        target_scope, location_context = await OfficerService._resolve_gen_h_management_context(target_profile)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope)

        temp_password = OfficerService._generate_temporary_password()
        hashed_password = bcrypt_hash_password(temp_password)

        updated = await GenHUserRepository.set_password_by_id(
            user_id,
            hashed_password,
            mark_first_login=True,
            reactivate=True,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_reset_failed")

        try:
            await RefreshTokenRepository.revoke_all_user_refresh_tokens(user_id, None, "gen_h")
        except Exception as exc:
            log_error(logger, "reset_gen_h_password revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="reset_password",
            target_type="gen_h",
            description=f"Officer reset password for Gen H user {user_id}",
            new_data={
                "genHUserId": user_id,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        return {
            "status": "success",
            "data": {
                "temporary_password": temp_password,
            },
            "message": "รีเซ็ตรหัสผ่านสำเร็จ",
        }

    @staticmethod
    async def set_gen_h_active_status(user_id: str, is_active: bool, current_user: dict):
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        if viewer_scope is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        target_profile = await GenHUserRepository.get_by_id(user_id)
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="gen_h_user_not_found")

        target_scope, location_context = await OfficerService._resolve_gen_h_management_context(target_profile)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        # Prevent re-activating a Gen H account that has been transferred to people_user
        if is_active and getattr(target_profile, "people_user_id", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="gen_h_already_transferred",
            )

        updated = await GenHUser.filter(id=user_id).update(
            is_active=is_active,
            updated_at=datetime.utcnow(),
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status_update_failed")

        if not is_active:
            try:
                await RefreshTokenRepository.revoke_all_user_refresh_tokens(user_id, None, "gen_h")
            except Exception as exc:
                log_error(logger, "toggle_gen_h_status revoke tokens failed", exc=exc)

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="set_active_status",
            target_type="gen_h",
            description=f"Officer updated Gen H active status for user {user_id}",
            new_data={
                "genHUserId": user_id,
                "isActive": is_active,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
                "performedBy": str(current_user.get("user_id")) if current_user.get("user_id") else None,
            },
        )

        try:
            await invalidate_user_sessions(user_id)
        except Exception:
            pass
        message = "เปิดใช้งานบัญชีสำเร็จ" if is_active else "ปิดใช้งานบัญชีสำเร็จ"
        return {
            "status": "success",
            "data": {
                "is_active": is_active,
            },
            "message": message,
        }

    @staticmethod
    async def get_registration_meta():
        gender_labels = {
            Gender.MALE: ("ชาย", "ชาย"),
            Gender.FEMALE: ("หญิง", "หญิง"),
            Gender.OTHER: ("อื่น ๆ", "อื่น ๆ"),
        }
        genders = [
            {
                "code": gender.value,
                "label": label,
                "name_th": label_th,
            }
            for gender, (label, label_th) in gender_labels.items()
        ]

        prefixes = await LookupService.list_prefixes(limit=200)
        positions = await LookupService.list_positions(limit=500)
        provinces = await LookupService.list_provinces(limit=1000)
        health_areas = await LookupService.list_health_areas(limit=200)
        areas = await LookupService.list_areas(limit=200)
        regions = await LookupService.list_regions(limit=50)

        return {
            "prefixes": prefixes,
            "genders": genders,
            "positions": positions,
            "provinces": provinces,
            "health_areas": health_areas,
            "areas": areas,
            "regions": regions,
        }

    @staticmethod
    async def get_registration_genders():
        gender_labels = {
            Gender.MALE: ("ชาย", "ชาย"),
            Gender.FEMALE: ("หญิง", "หญิง"),
            Gender.OTHER: ("อื่น ๆ", "อื่น ๆ"),
        }
        genders = [
            {
                "code": gender.value,
                "label": label,
                "name_th": label_th,
            }
            for gender, (label, label_th) in gender_labels.items()
        ]
        return {"items": genders}

    @staticmethod
    async def get_registration_prefixes(keyword: Optional[str] = None, limit: int = 200):
        items = await LookupService.list_prefixes(keyword, limit)
        return {"items": items}

    @staticmethod
    async def get_registration_positions(keyword: Optional[str] = None, limit: int = 500):
        items = await LookupService.list_positions(keyword, limit)
        return {"items": items}

    @staticmethod
    async def get_registration_provinces(keyword: Optional[str] = None, limit: int = 1000):
        items = await LookupService.list_provinces(keyword, limit)
        return {"items": items}

    @staticmethod
    async def get_registration_districts(province_code: str, keyword: Optional[str] = None):
        if not province_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="province_code_required")
        items = await LookupService.list_districts(province_code, keyword)
        return {"items": items}

    @staticmethod
    async def get_registration_subdistricts(district_code: str, keyword: Optional[str] = None):
        if not district_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="district_code_required")
        items = await LookupService.list_subdistricts(district_code, keyword)
        return {"items": items}

    @staticmethod
    async def get_registration_municipalities(
        *,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        keyword: Optional[str] = None,
    ):
        items = await LookupService.list_municipalities(
            keyword=keyword,
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
        )
        return {"items": items}

    @staticmethod
    async def get_registration_health_services(
        *,
        keyword: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        health_service_type_ids: Optional[List[str]] = None,
        health_service_type_ids_exclude: Optional[List[str]] = None,
        limit: int = 100,
    ):
        items = await LookupService.list_health_services(
            keyword=OfficerService._normalize_lookup_param(keyword),
            province_code=OfficerService._normalize_lookup_param(province_code),
            district_code=OfficerService._normalize_lookup_param(district_code),
            subdistrict_code=OfficerService._normalize_lookup_param(subdistrict_code),
            health_service_type_ids=OfficerService._normalize_lookup_list(health_service_type_ids),
            health_service_type_ids_exclude=OfficerService._normalize_lookup_list(health_service_type_ids_exclude),
            limit=limit,
        )
        return {"items": items}