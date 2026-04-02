from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from tortoise.expressions import Q

from app.models.enum_models import AdministrativeLevelEnum
from app.models.officer_model import OfficerProfile


class OfficerScopeError(Exception):
    """Raised when officer hierarchy context cannot be established."""


_LEVEL_RANK = {
    AdministrativeLevelEnum.COUNTRY: 6,
    AdministrativeLevelEnum.REGION: 5,
    AdministrativeLevelEnum.AREA: 4,
    AdministrativeLevelEnum.PROVINCE: 3,
    AdministrativeLevelEnum.DISTRICT: 2,
    AdministrativeLevelEnum.SUBDISTRICT: 1,
    AdministrativeLevelEnum.VILLAGE: 0,
}


def _coerce_level(value: str | AdministrativeLevelEnum | None) -> AdministrativeLevelEnum:
    if value is None:
        raise OfficerScopeError("area_type is required for officer scope")
    try:
        return value if isinstance(value, AdministrativeLevelEnum) else AdministrativeLevelEnum(value)
    except ValueError as exc:
        raise OfficerScopeError(f"unsupported area_type '{value}'") from exc


@dataclass(frozen=True)
class OfficerScope:
    level: AdministrativeLevelEnum
    health_area_id: Optional[str] = None
    health_service_id: Optional[str] = None
    province_id: Optional[str] = None
    district_id: Optional[str] = None
    subdistrict_id: Optional[str] = None
    village_code: Optional[str] = None
    region_code: Optional[str] = None

    @property
    def rank(self) -> int:
        return _LEVEL_RANK.get(self.level, -1)


class OfficerHierarchy:
    """Utility helpers for evaluating officer visibility/management scopes."""

    @staticmethod
    def scope_from_profile(officer: OfficerProfile) -> OfficerScope:
        if officer is None:
            raise OfficerScopeError("officer profile not found")

        level_source = getattr(officer, "area_type", None)
        position_level_source = None

        position = getattr(officer, "position", None)
        if position is not None:
            position_level_source = getattr(position, "scope_level", None)

        level = None
        resolved_area_level = None
        resolved_position_level = None
        last_error: OfficerScopeError | None = None

        if level_source is not None:
            try:
                resolved_area_level = _coerce_level(level_source)
            except OfficerScopeError as exc:
                last_error = exc
                resolved_area_level = None

        if position_level_source is not None:
            try:
                resolved_position_level = _coerce_level(position_level_source)
            except OfficerScopeError as exc:
                last_error = exc
                resolved_position_level = None

        # Officer's explicit area_type is the source of truth for operational scope.
        # Fallback to position scope only when area_type is missing/invalid.
        level = resolved_area_level or resolved_position_level

        if level is None:
            if last_error is not None:
                raise last_error
            raise OfficerScopeError("area_type is required for officer scope")
        health_area_id = getattr(officer, "health_area_id", None)
        health_service_id = getattr(officer, "health_service_id", None)
        province_id = getattr(officer, "province_id", None)
        district_id = getattr(officer, "district_id", None)
        subdistrict_id = getattr(officer, "subdistrict_id", None)
        region_code = None

        province = getattr(officer, "province", None)
        if province is not None:
            province_id = province_id or getattr(province, "province_code", None)
            province_health_area_id = getattr(province, "health_area_id", None)
            if province_health_area_id:
                health_area_id = province_health_area_id
            province_region_code = getattr(province, "region_id", None)
            if province_region_code:
                region_code = province_region_code

        district = getattr(officer, "district", None)
        if district is not None:
            district_id = district_id or getattr(district, "district_code", None)
            if province_id is None:
                province = getattr(district, "province", None)
                if province is not None:
                    province_id = getattr(province, "province_code", None)
                    province_health_area_id = getattr(province, "health_area_id", None)
                    if province_health_area_id:
                        health_area_id = province_health_area_id
                    province_region_code = getattr(province, "region_id", None)
                    if province_region_code:
                        region_code = province_region_code

        subdistrict = getattr(officer, "subdistrict", None)
        if subdistrict is not None:
            subdistrict_id = subdistrict_id or getattr(subdistrict, "subdistrict_code", None)
            if district_id is None:
                district = getattr(subdistrict, "district", None)
                if district is not None:
                    district_id = getattr(district, "district_code", None)
                    province = getattr(district, "province", None)
                    if province is not None:
                        province_id = province_id or getattr(province, "province_code", None)
                        province_health_area_id = getattr(province, "health_area_id", None)
                        if province_health_area_id:
                            health_area_id = province_health_area_id
                        province_region_code = getattr(province, "region_id", None)
                        if province_region_code:
                            region_code = province_region_code

        village_code = getattr(officer, "area_code", None)

        return OfficerScope(
            level=level,
            health_area_id=health_area_id,
            health_service_id=health_service_id,
            province_id=province_id,
            district_id=district_id,
            subdistrict_id=subdistrict_id,
            village_code=village_code,
            region_code=region_code,
        )

    @staticmethod
    def scope_from_payload(payload: Mapping[str, Optional[str]]) -> OfficerScope:
        level = _coerce_level(payload.get("area_type"))
        health_area_id = payload.get("health_area_id")
        health_service_id = payload.get("health_service_id")
        province_id = payload.get("province_id")
        district_id = payload.get("district_id")
        subdistrict_id = payload.get("subdistrict_id")
        village_code = payload.get("area_code")
        region_code = payload.get("region_code")

        required_fields: tuple[str, ...] = ()
        if level == AdministrativeLevelEnum.AREA:
            required_fields = ("health_area_id",)
        elif level == AdministrativeLevelEnum.PROVINCE:
            required_fields = ("province_id",)
        elif level == AdministrativeLevelEnum.DISTRICT:
            required_fields = ("province_id", "district_id")
        elif level == AdministrativeLevelEnum.SUBDISTRICT:
            required_fields = ("province_id", "district_id", "subdistrict_id")
        elif level == AdministrativeLevelEnum.VILLAGE:
            required_fields = ("province_id", "district_id", "subdistrict_id", "area_code")

        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            raise OfficerScopeError(f"missing required area fields: {', '.join(missing)}")

        return OfficerScope(
            level=level,
            health_area_id=health_area_id,
            health_service_id=health_service_id,
            province_id=province_id,
            district_id=district_id,
            subdistrict_id=subdistrict_id,
            village_code=village_code,
            region_code=region_code,
        )

    @staticmethod
    def manageable_levels(scope: OfficerScope) -> list[AdministrativeLevelEnum]:
        """Return administrative levels that are manageable by the given scope."""
        rank = scope.rank
        return [level for level, level_rank in _LEVEL_RANK.items() if level_rank <= rank]

    @staticmethod
    def build_visibility_filter(scope: OfficerScope) -> Optional[Q]:
        level = scope.level
        if level == AdministrativeLevelEnum.COUNTRY:
            return None
        if level == AdministrativeLevelEnum.REGION:
            if not scope.region_code:
                raise OfficerScopeError("region_code required for region level visibility")
            return (
                Q(province__region_id=scope.region_code)
                | Q(district__province__region_id=scope.region_code)
                | Q(subdistrict__district__province__region_id=scope.region_code)
                | Q(province__area__region_id=scope.region_code)
            )
        if level == AdministrativeLevelEnum.AREA:
            if not scope.health_area_id:
                raise OfficerScopeError("health_area_id required for health area visibility")
            return (
                Q(health_area_id=scope.health_area_id)
                | Q(province__health_area_id=scope.health_area_id)
                | Q(district__province__health_area_id=scope.health_area_id)
                | Q(subdistrict__district__province__health_area_id=scope.health_area_id)
            )
        if level == AdministrativeLevelEnum.PROVINCE:
            if not scope.province_id:
                raise OfficerScopeError("province_id required for province visibility")
            return (
                Q(province_id=scope.province_id)
                | Q(district__province_id=scope.province_id)
                | Q(subdistrict__district__province_id=scope.province_id)
            )
        if level == AdministrativeLevelEnum.DISTRICT:
            if not scope.district_id:
                raise OfficerScopeError("district_id required for district visibility")
            return (
                Q(district_id=scope.district_id)
                | Q(subdistrict__district_id=scope.district_id)
            )
        if level == AdministrativeLevelEnum.SUBDISTRICT:
            if not scope.subdistrict_id:
                raise OfficerScopeError("subdistrict_id required for subdistrict visibility")
            if not scope.health_service_id:
                return Q(id=None)
            return Q(subdistrict_id=scope.subdistrict_id) & Q(health_service_id=scope.health_service_id)
        if level == AdministrativeLevelEnum.VILLAGE:
            if not scope.village_code:
                raise OfficerScopeError("area_code required for village visibility")
            return Q(area_code=scope.village_code)
        raise OfficerScopeError(f"visibility handling not implemented for level {scope.level}")

    @staticmethod
    def can_manage(viewer: OfficerScope, target: OfficerScope) -> bool:
        if viewer.rank < target.rank:
            return False
        if viewer.level == AdministrativeLevelEnum.COUNTRY:
            return True
        if viewer.level == AdministrativeLevelEnum.REGION:
            return viewer.region_code is not None and viewer.region_code == target.region_code
        if viewer.level == AdministrativeLevelEnum.AREA:
            return (
                viewer.health_area_id is not None
                and viewer.health_area_id == target.health_area_id
            )
        if viewer.level == AdministrativeLevelEnum.PROVINCE:
            return (
                viewer.province_id is not None
                and viewer.province_id == target.province_id
            )
        if viewer.level == AdministrativeLevelEnum.DISTRICT:
            return (
                viewer.district_id is not None
                and viewer.district_id == target.district_id
            )
        if viewer.level == AdministrativeLevelEnum.SUBDISTRICT:
            if not (viewer.subdistrict_id is not None and viewer.subdistrict_id == target.subdistrict_id):
                return False
            if not viewer.health_service_id or not target.health_service_id:
                return False
            return viewer.health_service_id == target.health_service_id
        if viewer.level == AdministrativeLevelEnum.VILLAGE:
            return (
                viewer.village_code is not None
                and viewer.village_code == target.village_code
            )
        return False

    @staticmethod
    def can_view(viewer: OfficerScope, target: OfficerScope) -> bool:
        if viewer.level == AdministrativeLevelEnum.COUNTRY:
            return True
        if viewer.level == AdministrativeLevelEnum.REGION:
            return viewer.region_code is not None and viewer.region_code == target.region_code
        if viewer.level == AdministrativeLevelEnum.AREA:
            return viewer.health_area_id is not None and viewer.health_area_id == target.health_area_id
        if viewer.level == AdministrativeLevelEnum.PROVINCE:
            return viewer.province_id is not None and viewer.province_id == target.province_id
        if viewer.level == AdministrativeLevelEnum.DISTRICT:
            return viewer.district_id is not None and viewer.district_id == target.district_id
        if viewer.level == AdministrativeLevelEnum.SUBDISTRICT:
            if not (viewer.subdistrict_id is not None and viewer.subdistrict_id == target.subdistrict_id):
                return False
            if not viewer.health_service_id:
                return False
            if not target.health_service_id:
                return False
            return viewer.health_service_id == target.health_service_id
        if viewer.level == AdministrativeLevelEnum.VILLAGE:
            return viewer.village_code is not None and viewer.village_code == target.village_code
        return False