from __future__ import annotations

import asyncio
import base64
import hmac as _hmac
import jwt as _pyjwt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

try:
    import requests  # type: ignore[import-not-found]
    from requests import RequestException  # type: ignore[import-not-found]
except ImportError as import_exc:  # pragma: no cover - environment guard
    requests = None  # type: ignore[assignment]

    class RequestException(Exception):  # type: ignore[no-redef]
        """Fallback exception when requests isn't installed."""

    _REQUESTS_IMPORT_ERROR = import_exc
else:  # pragma: no cover - trivial branch
    _REQUESTS_IMPORT_ERROR = None

from app.configs.config import settings
from app.models.thaid_models import ThaiIDAuthCode
from app.repositories.client_repository import (
    ClientRepository,
    OAuthConsentRepository,
    RefreshTokenRepository,
)
from app.repositories.officer_profile_repository import OfficerProfileRepository
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.repositories.people_user_repository import PeopleUserRepository
from app.services.oauth2_service import get_user_basic_info, Oauth2Service
from app.utils.client_access_control import is_user_type_allowed
from app.utils.security import create_access_token, create_id_token, create_refresh_token
from app.utils.thaid_utils import get_thaid_logger

logger = get_thaid_logger()


class ThaiDAuthError(Exception):
    """Raised when ThaiD login validation fails."""

    def __init__(self, detail: str, response_code: str = "4010") -> None:
        self.detail = detail
        self.response_code = response_code
        super().__init__(detail)


async def process_thaid_auth_code(payload: ThaiIDAuthCode) -> Dict[str, Any]:
    """Exchange ThaiD auth code and mint OAuth2 tokens aligned with /auth/login/json."""

    client = await _get_client(payload)
    config = _get_thaid_config()

    thaid_raw = await validate_thaid_token(
        payload.auth_code,
        config.get("THAID_REDIRECT_URI"),
        config=config,
    )
    if not thaid_raw:
        raise ThaiDAuthError("invalid_auth_code")

    id_claims = _extract_id_token_claims((thaid_raw or {}).get("id_token"))
    raw_pid = (thaid_raw or {}).get("pid")

    # DOPA v2 may return pid inside the id_token JWT instead of the top-level response
    if not raw_pid:
        raw_pid = id_claims.get("pid")

    if not raw_pid:
        raise ThaiDAuthError("thaid_missing_pid")
    # DOPA sandbox may return pid as integer — ensure it's always a string
    pid = str(raw_pid)

    try:
        user_info, actual_user_type = await _resolve_user_info(pid, payload.user_type)
    except ThaiDAuthError as exc:
        if exc.detail != "citizen_id_not_found":
            raise
        prefill = _extract_thaid_prefill(thaid_raw, id_claims, pid)
        return {
            "is_new_user": True,
            "register_required": True,
            "user_type": payload.user_type,
            "citizen_id": pid,
            "prefill": prefill,
            "thaid_token": thaid_raw.get("access_token", ""),
        }

    # --- Access control checks (same logic as direct_login) ---
    if not is_user_type_allowed(client, actual_user_type):
        raise ThaiDAuthError("user_type_not_allowed")

    user_id = user_info.get("user_id")
    if await Oauth2Service._is_user_denied_by_allowlist(client, user_id, actual_user_type):
        raise ThaiDAuthError("user_not_in_allowlist")

    if await Oauth2Service._is_user_blocked(client, user_id, actual_user_type):
        raise ThaiDAuthError("user_blocked")

    scopes = _determine_scopes(client, payload.scope)
    tokens = await _issue_tokens_for_user(user_info, actual_user_type, client, scopes)
    id_token = _maybe_create_id_token(user_info, client, scopes)

    logger.info(
        "ThaiD auth ok user=%s type=%s",
        user_info["user_id"],
        actual_user_type,
    )

    result: Dict[str, Any] = {
        "is_new_user": False,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens["expires_in"],
        "scope": tokens["scope"],
        "user_id": user_info["user_id"],
        "user_type": actual_user_type,
        "citizen_id": user_info.get("citizen_id") or pid,
        "thaid_token": thaid_raw.get("access_token", ""),
    }
    if id_token:
        result["id_token"] = id_token
    return result


def _extract_id_token_claims(id_token: Optional[str]) -> Dict[str, Any]:
    if not id_token:
        return {}
    try:
        return _pyjwt.decode(
            id_token,
            options={"verify_signature": False},
            algorithms=["RS256", "HS256"],
        )
    except Exception as exc:
        logger.error("ThaiD id_token decode failed: %s", exc)
        return {}


def _extract_thaid_prefill(
    thaid_raw: Dict[str, Any],
    id_claims: Dict[str, Any],
    pid: str,
) -> Dict[str, str]:
    first_name = (
        (thaid_raw.get("given_name") or "").strip()
        or (thaid_raw.get("givenName") or "").strip()
        or (id_claims.get("given_name") or "").strip()
        or (id_claims.get("givenName") or "").strip()
    )
    last_name = (
        (thaid_raw.get("family_name") or "").strip()
        or (thaid_raw.get("familyName") or "").strip()
        or (id_claims.get("family_name") or "").strip()
        or (id_claims.get("familyName") or "").strip()
    )

    return {
        "citizen_id": str(pid or "").strip(),
        "first_name": first_name,
        "last_name": last_name,
    }


async def validate_thaid_token(
    auth_code: str,
    redirect_uri: Optional[str] = None,
    *,
    config: Dict[str, str] | None = None,
) -> Optional[Dict[str, Any]]:
    """Validate ThaiD authorization code via token endpoint."""

    if requests is None:
        logger.error(
            "ThaiD integration cannot call external API because the 'requests' package is missing: %s",
            _REQUESTS_IMPORT_ERROR,
        )
        raise ThaiDAuthError(
            "ThaiD integration requires the 'requests' package. Install dependencies with 'pip install -r requirements.txt'.",
            response_code="5002",
        )

    cfg = config or _get_thaid_config()

    basic_token = base64.b64encode(
        f"{cfg['THAID_CLIENT_ID']}:{cfg['THAID_CLIENT_SECRET']}".encode("utf-8")
    ).decode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_token}",
    }
    # Include API key if configured
    api_key = getattr(settings, "THAID_API_KEY", None)
    if api_key:
        headers["x-api-key"] = api_key
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
    }
    if redirect_uri:
        data["redirect_uri"] = redirect_uri

    try:
        response = await asyncio.to_thread(
            requests.post,
            cfg["THAID_REQUEST_URI"],
            data=data,
            headers=headers,
            timeout=15,
        )
    except RequestException as exc:
        logger.error("ThaiD token request network error: %s", exc)
        raise ThaiDAuthError("thaid_network_error") from exc

    if not (200 <= response.status_code < 300):
        logger.error("ThaiD token exchange failed HTTP %s", response.status_code)
        raise ThaiDAuthError(
            f"thaid_token_exchange_failed",
            response_code=str(response.status_code),
        )

    try:
        payload = response.json()
    except ValueError:
        logger.error("ThaiD token endpoint returned non-JSON response")
        return None

    return payload


def _get_thaid_config() -> Dict[str, str]:
    required = {
        "THAID_CLIENT_ID": settings.THAID_CLIENT_ID,
        "THAID_CLIENT_SECRET": settings.THAID_CLIENT_SECRET,
        "THAID_REQUEST_URI": settings.THAID_REQUEST_URI,
    }

    missing = [name for name, value in required.items() if not value]
    if missing:
        logger.error(
            "ThaiD integration missing required configuration keys: %s",
            ", ".join(sorted(missing)),
        )
        raise ThaiDAuthError("ThaiD integration is not configured", response_code="5001")

    config: Dict[str, str] = {name: value for name, value in required.items() if value}
    if settings.THAID_REDIRECT_URI:
        config["THAID_REDIRECT_URI"] = settings.THAID_REDIRECT_URI
    else:
        logger.warning("THAID_REDIRECT_URI is not set; continuing without redirect parameter")

    return config


async def _get_client(payload: ThaiIDAuthCode):
    client = await ClientRepository.find_client_by_client_id(payload.client_id)
    if not client or not getattr(client, "is_active", True):
        raise ThaiDAuthError("invalid_client")

    allowed_grants = set(client.grant_types or [])
    if not allowed_grants or not ({"direct_login", "password"} & allowed_grants):
        raise ThaiDAuthError("client_not_permitted_for_thaid")

    if not getattr(client, "public_client", True):
        if not payload.client_secret or not _hmac.compare_digest(
            payload.client_secret.encode("utf-8"),
            (client.client_secret or "").encode("utf-8"),
        ):
            raise ThaiDAuthError("invalid_client_secret")

    return client


# User type priority is the same as in oauth2_service
_USER_TYPE_PRIORITY: tuple[str, ...] = ("officer", "osm", "yuwa_osm", "people")
_VALID_USER_TYPES: set[str] = set(_USER_TYPE_PRIORITY)


async def _resolve_user_info(pid: str, requested_user_type: str) -> tuple[Dict[str, Any], str]:
    """Resolve a citizen_id (pid) into user_info dict + actual user_type.

    Supports all four user types: officer, osm, yuwa_osm, people.
    When a specific user_type is requested, only that type is probed.
    """

    candidates = (requested_user_type,) if requested_user_type in _VALID_USER_TYPES else _USER_TYPE_PRIORITY

    for candidate in candidates:
        profile = None
        try:
            match candidate:
                case "osm":
                    profile = await OSMProfileRepository.find_osm_basic_profile_by_citizen_id(pid)
                case "officer":
                    profile = await OfficerProfileRepository.find_officer_basic_profile_by_citizen_id(pid)
                case "yuwa_osm":
                    profile = await YuwaOSMUserRepository.find_basic_profile_by_citizen_id(pid)
                case "people":
                    profile = await PeopleUserRepository.find_basic_profile_by_citizen_id(pid)
                case _:
                    continue
        except Exception as exc:
            logger.warning("ThaiD profile lookup failed type=%s: %s", candidate, exc)
            continue

        if not profile:
            continue

        # Skip inactive
        if hasattr(profile, "is_active") and not getattr(profile, "is_active"):
            continue

        # Skip transferred People accounts — user should login as yuwa_osm
        if candidate == "people" and getattr(profile, "is_transferred", False):
            continue

        return get_user_basic_info(profile, candidate, citizen_id=pid), candidate

    raise ThaiDAuthError("citizen_id_not_found")


def _determine_scopes(client, requested_scopes: Optional[list[str]]) -> list[str]:
    allowed_scopes = list(client.scopes or [])
    scopes = list(dict.fromkeys(requested_scopes or allowed_scopes)) if (requested_scopes or allowed_scopes) else []

    if requested_scopes:
        invalid = [scope for scope in scopes if allowed_scopes and scope not in allowed_scopes]
        if invalid:
            raise ThaiDAuthError("invalid_scope")

    if not scopes:
        scopes = ["openid"]

    if "openid" not in scopes:
        scopes.append("openid")

    return scopes


async def _issue_tokens_for_user(
    user_info: Dict[str, Any],
    user_type: str,
    client,
    scopes: list[str],
) -> Dict[str, Any]:
    client_id = client.client_id
    access_token = create_access_token(user_info["user_id"], client_id, user_type, scopes=scopes)
    refresh_token = create_refresh_token(user_info["user_id"], client_id, user_type)

    if getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 0) and settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0:
        refresh_exp = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        refresh_exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)

    await RefreshTokenRepository.create_refresh_token(
        token=refresh_token,
        user_id=user_info["user_id"],
        user_type=user_type,
        client_id=client_id,
        scopes=scopes,
        expires_at=refresh_exp,
    )

    try:
        consented = await OAuthConsentRepository.has_user_consented(
            user_info["user_id"], client_id, scopes, user_type
        )
        if not consented:
            await OAuthConsentRepository.create_consent(
                user_info["user_id"], client_id, scopes, user_type
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "ThaiD auto consent failed for user %s client %s: %s",
            user_info["user_id"],
            client_id,
            exc,
        )

    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    scope_str = " ".join(scopes) if scopes else None
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "scope": scope_str,
    }


def _maybe_create_id_token(user_info: Dict[str, Any], client, scopes: list[str]) -> Optional[str]:
    if "openid" not in scopes:
        return None
    issuer = getattr(settings, "OIDC_ISSUER", None)
    if not issuer:
        return None
    try:
        return create_id_token(user_info["user_id"], client.client_id, issuer)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Failed to create id_token for user %s client %s: %s",
            user_info["user_id"],
            client.client_id,
            exc,
        )
        return None
