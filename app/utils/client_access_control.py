from __future__ import annotations

import json
from functools import lru_cache
from typing import Iterable, Optional, Set
from urllib.parse import urlparse

from app.configs.config import settings
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Default static rules that can be overridden via environment configuration.
# Keys may be any of: client_id, OAuth client UUID, absolute origin, or bare host.
_DEFAULT_RULES: dict[str, Set[str]] = {
    "https://phc-management.hss.moph.go.th": {"officer"},
    "phc-management.hss.moph.go.th": {"officer"},
    "https://dashboard.hss.moph.go.th": {"officer"},
    "dashboard.hss.moph.go.th": {"officer"},
    "https://osm-workreport.hss.moph.go.th": {"officer"},
    "osm-workreport.hss.moph.go.th": {"officer"},
    "https://thaiphc.hss.moph.go.th": {"officer"},
    "thaiphc.hss.moph.go.th": {"officer"},
    "https://phc-learning.hss.moph.go.th": {"osm", "yuwa_osm"},
    "phc-learning.hss.moph.go.th": {"osm", "yuwa_osm"},
    "https://genh.hss.moph.go.th": {"yuwa_osm", "gen_h"},
    "genh.hss.moph.go.th": {"yuwa_osm", "gen_h"},
    "mobile": {"osm", "yuwa_osm"},
}


def _normalize_key(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    trimmed = raw.strip().lower()
    return trimmed or None


def _iter_candidate_keys(client: object) -> Set[str]:
    keys: Set[str] = set()
    for attr in ("client_id", "id"):
        value = getattr(client, attr, None)
        norm = _normalize_key(str(value) if value is not None else None)
        if norm:
            keys.add(norm)
    for attr in ("redirect_uri", "login_url", "consent_url"):
        raw = getattr(client, attr, None)
        if not raw:
            continue
        norm = _normalize_key(str(raw))
        if norm:
            keys.add(norm)
        try:
            parsed = urlparse(str(raw))
        except ValueError:
            parsed = None
        if not parsed:
            continue
        if parsed.scheme and parsed.netloc:
            origin = _normalize_key(f"{parsed.scheme}://{parsed.netloc}")
            host = _normalize_key(parsed.netloc)
            if origin:
                keys.add(origin)
            if host:
                keys.add(host)
    return keys


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, Set[str]]:
    rules: dict[str, Set[str]] = {}
    raw = getattr(settings, "OAUTH_CLIENT_ACCESS_RULES", None)
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                for key, values in parsed.items():
                    norm_key = _normalize_key(str(key) if key is not None else None)
                    if not norm_key:
                        continue
                    if isinstance(values, str):
                        rules[norm_key] = {values.lower()}
                    elif isinstance(values, Iterable):
                        mapped = {str(v).lower() for v in values if isinstance(v, str) and v.strip()}
                        if mapped:
                            rules[norm_key] = mapped
                    else:
                        continue
        except Exception as exc:
            logger.warning("Failed to parse OAUTH_CLIENT_ACCESS_RULES: %s", exc)
    for key, values in _DEFAULT_RULES.items():
        if key not in rules:
            rules[key] = set(values)
    return rules


def reset_rules_cache() -> None:
    _load_rules.cache_clear()


def get_allowed_user_types(client: object) -> Optional[Set[str]]:
    dynamic = getattr(client, "allowed_user_types", None)
    if dynamic is not None:
        if isinstance(dynamic, str):
            values = [dynamic]
        elif isinstance(dynamic, Iterable):
            values = [v for v in dynamic if isinstance(v, str)]
        else:
            values = []
        cleaned = {v.strip().lower() for v in values if isinstance(v, str) and v.strip()}
        return cleaned

    rules = _load_rules()
    candidate_keys = _iter_candidate_keys(client)
    matched = False
    allowed: Set[str] = set()
    for key in candidate_keys:
        if key in rules:
            matched = True
            allowed.update(rules[key])
    return allowed if matched else None


def is_user_type_allowed(client: object, user_type: Optional[str]) -> bool:
    if not user_type:
        return False
    allowed = get_allowed_user_types(client)
    if allowed is None:
        # No explicit rule found — default open for backward compatibility.
        # Log a warning so ops teams can add explicit rules if needed.
        client_id = getattr(client, "client_id", "unknown")
        logger.warning(
            "No access-control rule for client '%s' — defaulting to ALLOW for user_type '%s'. "
            "Consider adding an explicit rule via allowed_user_types or OAUTH_CLIENT_ACCESS_RULES.",
            client_id,
            user_type,
        )
        return True
    return user_type.lower() in allowed
