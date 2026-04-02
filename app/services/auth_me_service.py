from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.officer_profile_repository import (
    OfficerProfileRepository,
)
from app.services.officer_service import OfficerService
from app.utils.officer_hierarchy import OfficerHierarchy, OfficerScopeError


class AuthMeService:
    """Helper utilities for composing the /auth/me payload."""

    LEVEL_NAME_TH: Dict[str, str] = {
        "country": "ประเทศ",
        "region": "ภูมิภาค",
        "area": "เขตสุขภาพ",
        "province": "จังหวัด",
        "district": "อำเภอ",
        "subdistrict": "ตำบล",
        "village": "หมู่บ้าน",
    }

    LEVEL_META: Dict[str, Dict[str, str]] = {
        key: {
            "id": key,
            "name_th": value,
            "scope_level": key,
            "scope_level_name_th": value,
        }
        for key, value in LEVEL_NAME_TH.items()
    }

    MANAGEABLE_LEVEL_SEQUENCE: List[str] = [
        "country",
        "region",
        "area",
        "province",
        "district",
        "subdistrict",
        "village",
    ]

    @classmethod
    def normalize_allowed_user_types(cls, raw_value: Any) -> Optional[List[str]]:
        """Normalize the different representations of allowed user types to a list."""
        if raw_value is None:
            return None
        if isinstance(raw_value, str):
            cleaned = raw_value.strip().lower()
            return [cleaned] if cleaned else None
        if isinstance(raw_value, (list, tuple, set)):
            mapped = {
                str(item).strip().lower()
                for item in raw_value
                if isinstance(item, str) and item.strip()
            }
            return sorted(mapped) if mapped else None
        return None

    @classmethod
    def _build_hierarchy_entry(
        cls, code: Optional[str], name: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        if not code:
            return None
        entry: Dict[str, str] = {"code": code}
        if name:
            entry["name"] = name
        return entry

    @classmethod
    def _decorate_levels(cls, levels: List[str]) -> List[Dict[str, str]]:
        decorated: List[Dict[str, str]] = []
        for level in levels:
            if not level:
                continue
            label = cls.LEVEL_NAME_TH.get(level, level)
            decorated.append({"id": level, "name_th": label})
        return decorated

    @classmethod
    def build_permission_scope_from_user_info(
        cls, user_info: Dict[str, Any], user_type: Optional[str]
    ) -> Dict[str, Any]:
        village_code = user_info.get("village_code") or None
        village_name = None
        if village_code:
            village_name = user_info.get("village_name_th") or user_info.get("village_name")

        hierarchy = {
            "country": cls._build_hierarchy_entry("TH", "Thailand"),
            "province": cls._build_hierarchy_entry(
                user_info.get("province_code"), user_info.get("province_name")
            ),
            "district": cls._build_hierarchy_entry(
                user_info.get("district_code"), user_info.get("district_name")
            ),
            "subdistrict": cls._build_hierarchy_entry(
                user_info.get("subdistrict_code"), user_info.get("subdistrict_name")
            ),
            "village": cls._build_hierarchy_entry(village_code, village_name),
        }
        level = "country"
        if hierarchy["subdistrict"]:
            level = "subdistrict"
        elif hierarchy["district"]:
            level = "district"
        elif hierarchy["province"]:
            level = "province"

        manageable_levels = [level] if user_type in {"osm", "yuwa_osm", "people"} else []
        return {
            "level": level,
            "level_name_th": cls.LEVEL_META.get(level, {}).get("name_th", level),
            "manageable_levels": manageable_levels,
            "manageable_levels_meta": cls._decorate_levels(manageable_levels),
            "codes": {
                "osm_code": user_info.get("osm_code"),
                "province_id": user_info.get("province_code"),
                "province_name_th": user_info.get("province_name_th")
                or user_info.get("province_name"),
                "district_id": user_info.get("district_code"),
                "district_name_th": user_info.get("district_name_th")
                or user_info.get("district_name"),
                "subdistrict_id": user_info.get("subdistrict_code"),
                "subdistrict_name_th": user_info.get("subdistrict_name_th")
                or user_info.get("subdistrict_name"),
                "village_name_th": village_name if village_code else None,
                "village_code": village_code,
            },
        }

    @classmethod
    def _build_permission_scope_for_officer(cls, officer_profile: Any) -> Optional[Dict[str, Any]]:
        try:
            scope = OfficerHierarchy.scope_from_profile(officer_profile)
            scope = OfficerService._cap_scope_by_position_for_local_levels(officer_profile, scope)
        except OfficerScopeError:
            return None

        derived_levels = [
            level.value if hasattr(level, "value") else str(level)
            for level in OfficerHierarchy.manageable_levels(scope)
        ]

        # Preserve the predefined ordering while respecting the dynamic scope caps.
        manageable_levels = [
            level for level in cls.MANAGEABLE_LEVEL_SEQUENCE if level in derived_levels
        ]

        # Append any non-standard levels while keeping the output deterministic.
        extras = [level for level in derived_levels if level not in cls.MANAGEABLE_LEVEL_SEQUENCE]
        manageable_levels.extend(sorted(extras))

        level_value = scope.level.value if hasattr(scope.level, "value") else scope.level
        province = getattr(officer_profile, "province", None)
        district = getattr(officer_profile, "district", None)
        subdistrict = getattr(officer_profile, "subdistrict", None)

        payload: Dict[str, Any] = {
            "level": level_value,
            "level_name_th": cls.LEVEL_META.get(level_value, {}).get(
                "name_th", level_value
            ),
            "manageable_levels": manageable_levels,
            "manageable_levels_meta": cls._decorate_levels(manageable_levels),
            "codes": {
                "health_area_id": scope.health_area_id,
                "osm_code": getattr(officer_profile, "osm_code", None)
                or getattr(getattr(officer_profile, "province", None), "osm_code", None),
                "province_id": scope.province_id,
                "province_name_th": getattr(
                    province, "province_name_th", None
                ),
                "district_id": scope.district_id,
                "district_name_th": getattr(
                    district, "district_name_th", None
                ),
                "subdistrict_id": scope.subdistrict_id,
                "subdistrict_name_th": getattr(
                    subdistrict, "subdistrict_name_th", None
                ),
                "village_code": scope.village_code,
                "region_code": scope.region_code,
            },
        }

        area_type = getattr(officer_profile, "area_type", None)
        if area_type is not None:
            payload["area_type"] = (
                area_type.value if hasattr(area_type, "value") else area_type
            )

        position = getattr(officer_profile, "position", None)
        if position is not None:
            level_value = getattr(position, "scope_level", None)
            if level_value is not None:
                scope_level = (
                    level_value.value if hasattr(level_value, "value") else level_value
                )
                payload["position_scope_level"] = scope_level
                payload["position_scope_level_name_th"] = cls.LEVEL_META.get(
                    scope_level, {}
                ).get("scope_level_name_th", cls.LEVEL_NAME_TH.get(scope_level, scope_level))
            else:
                scope_level = None

            payload["position"] = {
                "id": str(getattr(position, "id", "")) or None,
                "name_th": getattr(position, "position_name_th", None),
                "code": getattr(position, "position_code", None),
                "scope_level": scope_level,
                "scope_level_name_th": cls.LEVEL_META.get(scope_level, {}).get(
                    "scope_level_name_th", cls.LEVEL_NAME_TH.get(scope_level, scope_level)
                )
                if scope_level
                else None,
            }

        return payload

    @classmethod
    async def build_permission_scope(
        cls, user_id: str, user_type: Optional[str], user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        base_scope = cls.build_permission_scope_from_user_info(user_info, user_type)

        if user_type != "officer":
            return base_scope

        officer_profile = (
            await OfficerProfileRepository.find_officer_profile_with_related_fields(user_id)
        )
        if not officer_profile:
            return base_scope

        officer_scope = cls._build_permission_scope_for_officer(officer_profile)
        if not officer_scope:
            return base_scope

        return officer_scope