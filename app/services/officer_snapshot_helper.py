from __future__ import annotations

from typing import Dict, Optional

from app.repositories.officer_profile_repository import OfficerProfileRepository

_SCOPE_LABELS = {
    "village": "ระดับหมู่บ้าน",
    "subdistrict": "ระดับตำบล",
    "district": "ระดับอำเภอ",
    "province": "ระดับจังหวัด",
    "area": "ระดับเขตสุขภาพ",
    "region": "ระดับภูมิภาค",
    "country": "ระดับกรม",
}


def translate_scope_level(scope: Optional[str]) -> Optional[str]:
    """Return a Thai display label for the given officer scope level."""
    if not scope:
        return None
    normalized = scope.lower()
    return _SCOPE_LABELS.get(normalized, scope)


def ensure_snapshot_keys(payload: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """Ensure snapshot dict has all expected keys present."""
    defaults = {
        "name": None,
        "position_name": None,
        "scope_level": None,
        "scope_label": None,
    }
    return {**defaults, **payload}


async def build_officer_snapshot(user_id: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
    """Resolve officer display metadata for a given user identifier."""
    if not user_id:
        return None
    snapshot = await OfficerProfileRepository.get_display_snapshot_by_id(str(user_id))
    if not snapshot:
        return None
    scope_level = snapshot.get("scope_level")
    result = {
        "name": snapshot.get("name"),
        "position_name": snapshot.get("position_name"),
        "scope_level": scope_level,
        "scope_label": translate_scope_level(scope_level),
    }
    return ensure_snapshot_keys(result)
