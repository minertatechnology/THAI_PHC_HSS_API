import hashlib

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.security import decode_jwt_token, decode_first_login_token
from typing import Optional, Set
import jwt
from app.api.v1.exceptions.http_exceptions import UnauthorizedException
from app.repositories.client_repository import ClientRepository, RefreshTokenRepository
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.repositories.officer_profile_repository import OfficerProfileRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.repositories.people_user_repository import PeopleUserRepository
from app.utils.logging_utils import get_logger, log_error
from app.configs.config import settings
from app.cache.redis_client import cache_get, cache_set, cache_delete, cache_delete_pattern

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)

# Cache TTL constants (seconds)
TOKEN_CACHE_TTL = 120         # 2 minutes — full user result per token (skip JWT decode)
CLIENT_CACHE_TTL = 3600       # 1 hour — client data rarely changes
CITIZEN_ID_CACHE_TTL = 3600   # 1 hour — citizen_id never changes
SESSION_CACHE_TTL = 300       # 5 minutes — balance between performance and security


async def _get_client_cached(client_id: str):
    """Get OAuth client with Redis cache."""
    cache_key = f"client:{client_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    client = await ClientRepository.find_client_by_client_id(client_id)
    if client:
        client_data = {"id": str(client.id), "client_id": client.client_id, "is_active": client.is_active}
        await cache_set(cache_key, client_data, CLIENT_CACHE_TTL)
        return client_data
    return None


async def _get_citizen_id_cached(user_type: str, user_id: str) -> Optional[str]:
    """Get citizen_id with Redis cache."""
    cache_key = f"cid:{user_type}:{user_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    citizen_id = None
    try:
        if user_type == "osm":
            citizen_id = await OSMProfileRepository.get_citizen_id_by_id(user_id)
        elif user_type == "officer":
            citizen_id = await OfficerProfileRepository.get_citizen_id_by_id(user_id)
        elif user_type == "yuwa_osm":
            citizen_id = await YuwaOSMUserRepository.get_citizen_id_by_id(user_id)
        elif user_type == "people":
            citizen_id = await PeopleUserRepository.get_citizen_id_by_id(user_id)
        elif user_type == "gen_h":
            from app.repositories.gen_h_user_repository import GenHUserRepository
            profile = await GenHUserRepository.find_basic_profile_by_id(user_id)
            citizen_id = getattr(profile, "gen_h_code", None) if profile else None
    except Exception as repo_error:
        log_error(logger, "Failed to resolve citizen_id for current user", exc=repo_error)

    if citizen_id:
        await cache_set(cache_key, citizen_id, CITIZEN_ID_CACHE_TTL)
    return citizen_id


async def _has_active_session_cached(user_id: str, client_id: str, user_type: str) -> bool:
    """Check active session with Redis cache."""
    cache_key = f"session:{user_id}:{client_id}:{user_type}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    has_session = await RefreshTokenRepository.has_active_refresh_token(
        user_id, client_id, user_type
    )
    if has_session:
        await cache_set(cache_key, True, SESSION_CACHE_TTL)
    return has_session


async def invalidate_session_cache(user_id: str, client_id: str, user_type: str) -> None:
    """Invalidate session cache on logout/revoke."""
    await cache_delete(f"session:{user_id}:{client_id}:{user_type}")
    # Also clear all token caches so revoked sessions take effect immediately
    await cache_delete_pattern("token:*")


async def invalidate_user_sessions(user_id: str) -> None:
    """Invalidate all session caches for a user (e.g., password change)."""
    await cache_delete_pattern(f"session:{user_id}:*")
    await cache_delete_pattern("token:*")


async def invalidate_client_cache(client_id: str) -> None:
    """Invalidate client cache when client is updated."""
    await cache_delete(f"client:{client_id}")


def _token_hash(token: str) -> str:
    """Short hash of token for cache key (avoid storing full JWT in Redis)."""
    return hashlib.sha256(token.encode()).hexdigest()[:24]


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Middleware สำหรับตรวจสอบ access token
    ใช้ Redis cache: ถ้า token เดิม → return ผลเดิมทันที (skip JWT decode + DB queries)
    """
    if credentials is None or not getattr(credentials, "credentials", None):
        raise UnauthorizedException(detail="Authentication credentials were not provided")
    token = credentials.credentials

    # Fast path: check token-level cache (skip JWT decode entirely)
    token_key = f"token:{_token_hash(token)}"
    cached_user = await cache_get(token_key)
    if cached_user is not None:
        return cached_user

    try:
        payload = decode_jwt_token(token)
        # ตรวจสอบว่าเป็น access token
        token_type = payload.get("type")
        if token_type != "access":
            raise UnauthorizedException(detail="Invalid token type. Access token required.")
        # ตรวจสอบ issuer/audience ถ้าตั้งค่าไว้
        iss = payload.get("iss")
        aud = payload.get("aud")
        if getattr(settings, "OIDC_ISSUER", None) and iss != settings.OIDC_ISSUER:
            raise UnauthorizedException(detail="Invalid token issuer")
        expected_aud = getattr(settings, "ACCESS_TOKEN_AUDIENCE", None)
        if expected_aud is not None:
            aud_list = aud if isinstance(aud, list) else [aud]
            if expected_aud not in aud_list:
                raise UnauthorizedException(detail="Invalid token audience")

        user_id = payload.get("sub")  # subject = user_id
        client_id = payload.get("cid")  # client ID
        user_type = payload.get("ut")
        if user_id is None or client_id is None:
            raise UnauthorizedException(detail="Invalid authentication credentials")
        # อ่าน scopes จาก claim (OAuth uses space-delimited string)
        scopes = payload.get("scope") or payload.get("scopes") or ""
        if isinstance(scopes, str):
            scopes = [s for s in scopes.split(" ") if s]

        # Query 1: Client lookup (cached 1 hour)
        client = await _get_client_cached(client_id)
        if not client or not client.get("is_active"):
            raise UnauthorizedException(detail="Client is not active or invalid")

        # Query 2: Citizen ID lookup (cached 1 hour)
        citizen_id = await _get_citizen_id_cached(user_type, user_id)

        # Query 3: Session check (cached 5 minutes)
        has_active_session = await _has_active_session_cached(user_id, client_id, user_type)
        if not has_active_session:
            raise UnauthorizedException(detail="Session has expired or been revoked")

        user_result = {
            "user_id": user_id,
            "client_id": client_id,
            "user_type": user_type,
            "scopes": scopes,
            "citizen_id": citizen_id,
        }

        # Cache full result keyed by token hash (TTL 2 min, shorter than token expiry)
        await cache_set(token_key, user_result, TOKEN_CACHE_TTL)
        return user_result

    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(detail="Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(detail="Invalid authentication credentials")
    except UnauthorizedException:
        raise
    except Exception as e:
        log_error(logger, "get_current_user failed", exc=e)
        raise UnauthorizedException(detail="Authentication failed")

def require_scopes(required: Set[str]):
    """FastAPI dependency to enforce OAuth2 scopes on endpoints."""
    async def _dep(user = Depends(get_current_user)):
        token_scopes = set(user.get("scopes") or [])
        if not set(required).issubset(token_scopes):
            raise UnauthorizedException(detail="Insufficient scope")
        return user
    return _dep

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
):
    """Return authenticated user details when Authorization header is provided; otherwise None."""
    if not credentials:
        return None
    return await get_current_user(credentials)

async def get_current_user_first_login(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = decode_first_login_token(token)
        citizen_id = payload.get("sub")
        user_type = payload.get("ut")
        purpose = payload.get("purpose")
        if purpose != "set-password" or citizen_id is None or user_type is None:
            raise UnauthorizedException(detail="Invalid authentication credentials")
        return {"citizen_id": citizen_id, "user_type": user_type}

    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(detail="Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(detail="Invalid authentication credentials")
    except Exception as e:
        log_error(logger, "get_current_user_first_login failed", exc=e)
        raise UnauthorizedException(detail="Authentication failed")
