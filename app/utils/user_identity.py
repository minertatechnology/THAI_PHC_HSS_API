from __future__ import annotations

from typing import Any


def encode_user_id_for_oauth(user_id: str, user_type: str | None) -> str:
    """Normalize user identifiers so OAuth storage works across user types."""
    if user_type == "yuwa_osm":
        return str(user_id)
    return user_id


def decode_user_id_from_oauth(stored_user_id: Any, user_type: str | None) -> str:
    """Inverse of encode_user_id_for_oauth; returns the external identifier."""
    if user_type == "yuwa_osm":
        return str(stored_user_id)
    return str(stored_user_id)
