from typing import Any, Iterable, List, Optional
from urllib.parse import urlencode
from app.utils.logging_utils import get_logger, log_error, log_info
from app.utils.client_access_control import get_allowed_user_types, is_user_type_allowed
from app.api.v1.schemas.oauth2_schema import LoginResponse, TokenResponse, DirectLoginRequest, RefreshRequest
from app.api.v1.exceptions.http_exceptions import UnauthorizedException, InternalServerErrorException, BadRequestException, NotFoundException
import hashlib
from urllib.parse import urlparse
import base64
import bcrypt
import asyncio
from app.models.auth_model import OAuthClient, OAuthClientBlock
from app.models.osm_model import OSMProfile
from app.models.officer_model import OfficerProfile
from app.models.yuwa_osm_model import YuwaOSMUser
from app.models.people_model import PeopleUser
from app.models.gen_h_model import GenHUser
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.repositories.officer_profile_repository import OfficerProfileRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.repositories.people_user_repository import PeopleUserRepository
from app.repositories.gen_h_user_repository import GenHUserRepository
from app.repositories.client_repository import (
    ClientRepository,
    OAuthConsentRepository,
    OAuthAuthorizationCodeRepository,
    RefreshTokenRepository,
    OAuthClientBlockRepository,
    OAuthClientAllowRepository,
    OAuthClientUserTypeDefaultRepository,
)
from fastapi import Request
from app.utils.security import  create_access_token, create_refresh_token, create_first_login_token, decode_jwt_session_token, create_session_token, create_id_token
from fastapi.responses import RedirectResponse
import uuid
from datetime import datetime, timedelta, timezone
from app.configs.config import settings
from app.api.v1.schemas.oauth2_schema import (
    CreateClientSchema,
    UpdateClientSchema,
    PreLoginResponse,
    SetPasswordResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    CreateClientBlockRequest,
    ClientBlockQueryParams,
)
from tortoise.exceptions import OperationalError

logger = get_logger(__name__)


def _extract_origin(redirect_uri: str | None) -> str | None:
    """Return scheme://host[:port] from a redirect_uri for building frontend URLs."""
    if not redirect_uri:
        return None
    try:
        u = urlparse(redirect_uri)
        if not u.scheme or not u.netloc:
            return None
        origin = f"{u.scheme}://{u.netloc}"
        return origin
    except Exception:
        return None


def _normalize_client_url(configured_url: str | None, base_origin: str | None, default_path: str) -> str:
    """
    If client provided an absolute URL, use it.
    Else if base_origin is known (from redirect_uri), join with default_path.
    Else return default_path so caller can decide a global fallback.
    """
    if configured_url:
        return configured_url
    if base_origin:
        # ensure default_path starts with '/'
        path = default_path if default_path.startswith('/') else f'/{default_path}'
        return f"{base_origin}{path}"
    return default_path


USER_TYPE_PRIORITY: tuple[str, ...] = ("officer", "osm", "yuwa_osm", "people", "gen_h")
VALID_USER_TYPES: set[str] = set(USER_TYPE_PRIORITY)
_STATE_PLACEHOLDER = "STATE_PLACEHOLDER"


def _build_url_with_params(base_url: str | None, params: list[tuple[str, str]]) -> str | None:
    if not base_url:
        return None
    if not params:
        return base_url
    # Preserve insertion order for readability
    query = urlencode(params, doseq=True)
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{query}"

class Oauth2Service:
    MAX_PASSWORD_CHANGE_ATTEMPTS = 10
    async def pre_login(citizen_id: str, user_type: str | None = None):
        for candidate in _resolve_candidate_user_types(user_type):
            state = await _probe_first_login_state(candidate, citizen_id)
            if not state:
                continue

            needs_setup = bool(state.get("is_first_login", False) or not state.get("password_hash"))
            token = create_first_login_token(citizen_id, candidate) if needs_setup else None
            return PreLoginResponse(
                exist=True,
                needs_password_setup=needs_setup,
                token=token,
                user_type=candidate,
            )

        return PreLoginResponse(exist=False, needs_password_setup=False)
        
    
    async def set_password(citizen_id: str, password: str, user_type: str):
        hashed_password = bcrypt_hash_password(password)
        try:
            match user_type:
                case "osm":
                    await OSMProfileRepository.set_password(citizen_id, hashed_password)
                case "officer":
                    await OfficerProfileRepository.set_password(citizen_id, hashed_password)
                case "yuwa_osm":
                    await YuwaOSMUserRepository.set_password(citizen_id, hashed_password)
                case "people":
                    await PeopleUserRepository.set_password(citizen_id, hashed_password)
                case "gen_h":
                    await GenHUserRepository.set_password(citizen_id, hashed_password)
                case _:
                    raise BadRequestException(detail="unsupported_user_type")
            return SetPasswordResponse(message="set_password_success")
        except Exception as e:
            raise InternalServerErrorException(detail="set_password_failed")

    async def login(username: str, password: str, redirect_to: str = "/", client_id: str | None = None, state: str | None = None, user_type: str | None = None):
        # 1. If client_id is provided, fetch client and use its login_url for redirect
        client = None
        try:
            client = await ClientRepository.find_client_by_client_id(client_id)
            if not client or not client.is_active:
                base_origin = _extract_origin(getattr(client, "redirect_uri", None))
                login_url = _normalize_client_url(getattr(client, "login_url", None), base_origin, "/login")
                if not login_url.startswith("http"):
                    # fallback absolute default
                    login_url = "http://localhost:3000/login"
                # ✅ คืน query params ทั้งหมดกลับไป
                error_url = f"{login_url}?error=invalid_client&client_id={client_id}&redirect_uri={redirect_to}&state={state}"
                return RedirectResponse(url=error_url, status_code=303)
        except Exception as e:
            log_error(logger, "Error finding client", exc=e)
            # ✅ คืน query params ทั้งหมดกลับไป
            error_url = f"http://localhost:3000/login?error=invalid_client&client_id={client_id}&redirect_uri={redirect_to}&state={state}"
            return RedirectResponse(url=error_url, status_code=303)

        user_basic_info = await _validate_credentials(username, password, user_type)
        if not user_basic_info:
            # ✅ คืน query params ทั้งหมดกลับไป
            login_url = client.login_url if client and client.login_url else "http://localhost:3000/login"
            error_url = f"{login_url}?error=invalid_username_or_password&client_id={client_id}&redirect_uri={redirect_to}&state={state}"
            return RedirectResponse(url=error_url, status_code=303)

        actual_user_type = user_basic_info.get("user_type")

        if user_type and actual_user_type != user_type:
            login_url = client.login_url if client and client.login_url else "http://localhost:3000/login"
            error_url = f"{login_url}?error=invalid_username_or_password&client_id={client_id}&redirect_uri={redirect_to}&state={state}"
            return RedirectResponse(url=error_url, status_code=303)

        if not is_user_type_allowed(client, actual_user_type):
            allowed_roles = ",".join(sorted(get_allowed_user_types(client) or []))
            log_info(
                logger,
                "login: user type not allowed for client",
                extra={
                    "client_id": client_id,
                    "user_type": actual_user_type,
                    "allowed": allowed_roles,
                },
            )
            login_url = client.login_url if client and client.login_url else "http://localhost:3000/login"
            error_url = f"{login_url}?error=user_type_not_allowed&client_id={client_id}&redirect_uri={redirect_to}&state={state}"
            return RedirectResponse(url=error_url, status_code=303)

        if await Oauth2Service._is_user_denied_by_allowlist(client, user_basic_info.get("user_id"), actual_user_type):
            log_info(
                logger,
                "login: user not in allowlist for client",
                extra={
                    "client_id": client_id,
                    "user_id": user_basic_info.get("user_id"),
                    "user_type": actual_user_type,
                },
            )
            login_url = client.login_url if client and client.login_url else "http://localhost:3000/login"
            error_url = f"{login_url}?error=user_not_allowed&client_id={client_id}&redirect_uri={redirect_to}&state={state}"
            return RedirectResponse(url=error_url, status_code=303)

        if await Oauth2Service._is_user_blocked(client, user_basic_info.get("user_id"), actual_user_type):
            log_info(
                logger,
                "login: user blocked for client",
                extra={
                    "client_id": client_id,
                    "user_id": user_basic_info.get("user_id"),
                    "user_type": actual_user_type,
                },
            )
            login_url = client.login_url if client and client.login_url else "http://localhost:3000/login"
            error_url = f"{login_url}?error=user_blocked&client_id={client_id}&redirect_uri={redirect_to}&state={state}"
            return RedirectResponse(url=error_url, status_code=303)

        response = RedirectResponse(url=redirect_to, status_code=303)
        set_user_cookie(response, user_basic_info)
        return response

    async def authorize(request: Request):
        # เช็คว่า user เคย login หรือยัง ถ้าไม่ได้ login ก็จะส่งกลับหน้า login
        client_id = request.query_params.get("client_id")
        scopes = request.query_params.get("scope")
        redirect_uri = request.query_params.get("redirect_uri")
        state = request.query_params.get("state")
        response_type = request.query_params.get("response_type", "code")
        # PKCE params (optional for confidential, recommended/required for public)
        code_challenge = request.query_params.get("code_challenge")
        code_challenge_method = request.query_params.get("code_challenge_method")
        # OIDC nonce (optional)
        nonce = request.query_params.get("nonce")

        try:
            client = await ClientRepository.find_client_by_client_id(client_id)
        except Exception as e:
            log_error(logger, "authorize: invalid_client lookup failed", exc=e)
            raise BadRequestException(detail="invalid_client")

        if not client or not client.is_active or client.redirect_uri != redirect_uri:
            raise BadRequestException(detail="invalid_client")

        # Validate response_type per discovery (support only code)
        if response_type != "code":
            return RedirectResponse(url=f"{redirect_uri}?error=unsupported_response_type&state={state}", status_code=303)

        # Determine requested scopes (default to client's configured scopes if not provided)
        requested_scopes = scopes.split(" ") if scopes else (client.scopes or [])
        allowed_scopes_set = set(client.scopes or [])
        # Validate requested scopes are allowed
        if any(s not in allowed_scopes_set for s in requested_scopes):
            # Per RFC 6749, redirect back with error=invalid_scope
            return RedirectResponse(url=f"{redirect_uri}?error=invalid_scope&state={state}", status_code=303)

        scopes_array = requested_scopes
        scopes_str = " ".join(scopes_array) if scopes_array else ""

        base_origin = _extract_origin(redirect_uri)
        login_url = _normalize_client_url(getattr(client, "login_url", None), base_origin, "/login")
        if not login_url.startswith("http"):
            login_url = "http://localhost:3000/login"
        user_info = _get_authenticated_user(request)
        if not user_info:
            login_url_with_param = f"{login_url}?client_id={client_id}&redirect_uri={redirect_uri}&scope={scopes_str}&state={state}"
            return RedirectResponse(url=login_url_with_param, status_code=303)

        if not is_user_type_allowed(client, user_info.get("user_type")):
            log_info(
                logger,
                "authorize: user type not allowed",
                extra={"client_id": client_id, "user_type": user_info.get("user_type")},
            )
            return RedirectResponse(
                url=f"{redirect_uri}?error=access_denied&error_description=user_type_not_allowed&state={state}",
                status_code=303,
            )

        if await Oauth2Service._is_user_denied_by_allowlist(client, user_info.get("user_id"), user_info.get("user_type")):
            log_info(
                logger,
                "authorize: user not in allowlist",
                extra={"client_id": client_id, "user_id": user_info.get("user_id")},
            )
            return RedirectResponse(
                url=f"{redirect_uri}?error=access_denied&error_description=user_not_allowed&state={state}",
                status_code=303,
            )

        if await Oauth2Service._is_user_blocked(client, user_info.get("user_id"), user_info.get("user_type")):
            log_info(
                logger,
                "authorize: user blocked",
                extra={"client_id": client_id, "user_id": user_info.get("user_id")},
            )
            return RedirectResponse(
                url=f"{redirect_uri}?error=access_denied&error_description=user_blocked&state={state}",
                status_code=303,
            )

        # เช็คว่า user เคยกดยินยอม consent หรือยัง  ถ้ายังไม่เคยกดยินยอม consent ก็จะส่งกลับหน้ายินยอม consent
        is_user_consented = await OAuthConsentRepository.has_user_consented(
            user_info["user_id"], client_id, scopes_array, user_info.get("user_type")
        )
        if not is_user_consented:
            # ใช้ consent_url จาก client หรือ fallback เป็น frontend default
            consent_url = _normalize_client_url(getattr(client, "consent_url", None), base_origin, "/consent")
            if not consent_url.startswith("http"):
                consent_url = "http://localhost:3000/consent"
            consent_url_with_param = f"{consent_url}?client_id={client_id}&redirect_uri={redirect_uri}&scope={scopes_str}&state={state}"
            return RedirectResponse(url=consent_url_with_param, status_code=303)
        # Enforce PKCE for public clients
        if getattr(client, "public_client", True) and not code_challenge:
            return RedirectResponse(url=f"{redirect_uri}?error=invalid_request&error_description=pkce_required&state={state}", status_code=303)
        # สร้าง code และ บันทึกลง database เมื่อยินยอม consent แล้ว
        code = await create_auth_code(
            user_info["user_id"],
            user_info["user_type"],
            client_id,
            scopes_array,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
        )
        return RedirectResponse(url=f"{redirect_uri}?code={code}&state={state}")


    async def consent(request: Request, client_id: str, redirect_uri: str, scopes: List[str], state: str):
        user_info = _get_authenticated_user(request)

        try:
            result = await OAuthConsentRepository.create_consent(
                user_info["user_id"], client_id, scopes, user_info.get("user_type")
            )

            # join scopes list เป็น string แยกด้วย space ก่อนส่งเป็น query param
            scopes_str = " ".join(scopes)
            # กลับไป authorize ใหม่หลังจากบันทึก consent แล้ว
            return RedirectResponse(
                url=f"{settings.API_V1_PREFIX}/auth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope={scopes_str}&state={state}",status_code=303
            )
        except Exception as e:
            log_error(logger, "consent: create_consent failed", exc=e)
            raise InternalServerErrorException(detail="internal_server_error")

    async def token(request: Request, client_id: str, client_secret: str, grant_type: str, code: str = None, redirect_uri: str = None, refresh_token: str = None, code_verifier: str | None = None):
        """
        Token endpoint ที่รองรับทั้ง authorization_code และ refresh_token
        """
        if grant_type == "authorization_code":
            return await _handle_authorization_code_grant(request, client_id, client_secret, code, redirect_uri, code_verifier)
        elif grant_type == "refresh_token":
            return await _handle_refresh_token_grant(request, client_id, client_secret, refresh_token)
        else:
            raise UnauthorizedException(detail="unsupported_grant_type")

    async def revoke_token(request: Request, client_id: str, client_secret: str, token: str, token_type_hint: str = None):
        """
        Token revocation endpoint ตาม RFC 7009
        """
        # ตรวจสอบ client
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise UnauthorizedException(detail="invalid_client")
        
        # For confidential clients, verify secret
        if not client.public_client:
            if not client_secret or client.client_secret != client_secret:
                raise UnauthorizedException(detail="invalid_client")
        
        # ลอง revoke refresh token ก่อน
        revoked = await RefreshTokenRepository.revoke_refresh_token(token)
        
        # ถ้าไม่ใช่ refresh token หรือ revoke ไม่สำเร็จ ให้ return success ตาม RFC 7009
        return {"status": "success"}

    @staticmethod
    async def logout(user_id: str, client_id: str, user_type: str | None = None):
        """Revoke all refresh tokens for a user on a client. Useful for API/mobile logout."""
        await RefreshTokenRepository.revoke_all_user_refresh_tokens(user_id, client_id, user_type)
        return {"status": "success"}

    @staticmethod
    async def change_password(current_user: dict, payload: ChangePasswordRequest) -> ChangePasswordResponse:
        user_id = current_user.get("user_id")
        user_type = current_user.get("user_type")
        client_id = current_user.get("client_id")

        if not user_id or not user_type:
            raise BadRequestException(detail="user_context_missing")

        # Resolve repository based on user_type
        repo_map = {
            "officer": OfficerProfileRepository,
            "osm": OSMProfileRepository,
            "yuwa_osm": YuwaOSMUserRepository,
            "people": PeopleUserRepository,
            "gen_h": GenHUserRepository,
        }
        repo = repo_map.get(user_type)
        if not repo:
            raise BadRequestException(detail="unsupported_user_type")

        record = await repo.get_password_state(str(user_id))
        if not record or not getattr(record, "password_hash", None):
            raise BadRequestException(detail="password_not_set")

        stored_hash = getattr(record, "password_hash", None)
        stored_bytes = stored_hash.encode() if isinstance(stored_hash, str) else stored_hash

        passwords_match = False
        if stored_bytes:
            try:
                passwords_match = await asyncio.to_thread(
                    bcrypt.checkpw,
                    payload.old_password.encode(),
                    stored_bytes,
                )
            except ValueError:
                passwords_match = False

        if not passwords_match:
            current_attempts = getattr(record, "password_attempts", 0) or 0
            new_attempts = current_attempts + 1
            deactivate = new_attempts >= Oauth2Service.MAX_PASSWORD_CHANGE_ATTEMPTS
            await repo.update_password_attempts(
                str(user_id),
                new_attempts,
                deactivate=deactivate,
            )
            if deactivate:
                try:
                    await RefreshTokenRepository.revoke_all_user_refresh_tokens(str(user_id), None, user_type)
                except Exception as exc:
                    log_error(logger, "change_password revoke tokens after lock failed", exc=exc)
                raise BadRequestException(detail="account_locked")
            raise BadRequestException(detail="old_password_incorrect")

        if payload.old_password == payload.new_password:
            raise BadRequestException(detail="password_unchanged")

        hashed = bcrypt_hash_password(payload.new_password)
        await repo.set_password_by_id(
            str(user_id),
            hashed,
            mark_first_login=False,
            reset_attempts=True,
            reactivate=True,
        )

        try:
            await RefreshTokenRepository.revoke_all_user_refresh_tokens(str(user_id), None, user_type)
        except Exception as exc:
            log_error(logger, "change_password revoke tokens failed", exc=exc)

        # Invalidate all cached sessions/tokens so the password change takes effect immediately
        from app.api.middleware.middleware import invalidate_user_sessions
        from app.cache.redis_client import cache_delete_pattern
        await invalidate_user_sessions(str(user_id))
        await cache_delete_pattern("auth_me:*")

        return ChangePasswordResponse()

    async def create_client(client: CreateClientSchema, request: Request):
        # user_info = _get_authenticated_user(request)
        client_id = str(uuid.uuid4())
        client_secret = str(uuid.uuid4())
        test_created_by = str(uuid.uuid4())
        scopes = Oauth2Service._normalize_scopes(client.scopes)
        grant_types = Oauth2Service._normalize_grant_types(client.grant_types)
        client_name = Oauth2Service._require_non_empty(client.client_name, "client_name")
        redirect_uri = Oauth2Service._require_non_empty(client.redirect_uri, "redirect_uri")
        login_url = Oauth2Service._require_non_empty(client.login_url, "login_url")
        consent_url = Oauth2Service._require_non_empty(client.consent_url, "consent_url")
        description = client.client_description.strip() if client.client_description else None
        result = await ClientRepository.create_client(
            client_id,
            client_secret,
            client_name,
            description,
            redirect_uri,
            login_url,
            consent_url,
            scopes,
            grant_types,
            test_created_by,
            public_client=client.public_client,
        )
        return Oauth2Service._serialize_client(result)

    @staticmethod
    async def direct_login(payload: DirectLoginRequest) -> TokenResponse:
        """API-first: validate credentials and issue tokens directly without web redirects."""
        client = await ClientRepository.find_client_by_client_id(payload.client_id)
        if not client or not client.is_active:
            raise UnauthorizedException(detail="invalid_client")
        allowed_grants = set((client.grant_types or []))
        if not ({"direct_login", "password"} & allowed_grants):
            raise UnauthorizedException(detail="unsupported_grant_type")

        # Validate credentials
        user_info = await _validate_credentials(payload.username, payload.password, payload.user_type)
        if not user_info:
            raise UnauthorizedException(detail="invalid_username_or_password")

        actual_user_type = user_info.get("user_type", payload.user_type)
        if payload.user_type and actual_user_type != payload.user_type:
            raise UnauthorizedException(detail="invalid_username_or_password")

        if not is_user_type_allowed(client, actual_user_type):
            log_info(
                logger,
                "direct_login: user type not allowed",
                extra={"client_id": payload.client_id, "user_type": actual_user_type},
            )
            raise UnauthorizedException(detail="user_type_not_allowed")

        if await Oauth2Service._is_user_denied_by_allowlist(client, user_info.get("user_id"), actual_user_type):
            log_info(
                logger,
                "direct_login: user not in allowlist",
                extra={"client_id": payload.client_id, "user_id": user_info.get("user_id")},
            )
            raise UnauthorizedException(detail="user_not_allowed")

        if await Oauth2Service._is_user_blocked(client, user_info.get("user_id"), actual_user_type):
            log_info(
                logger,
                "direct_login: user blocked",
                extra={"client_id": payload.client_id, "user_id": user_info.get("user_id")},
            )
            raise UnauthorizedException(detail="user_blocked")

        # Determine scopes from payload or default to client scopes; enforce subset
        requested_scopes = list(payload.scope or client.scopes or [])
        allowed_scopes_set = set(client.scopes or [])
        if any(s not in allowed_scopes_set for s in requested_scopes):
            raise UnauthorizedException(detail="invalid_scope")
        scopes = requested_scopes
        if "openid" not in scopes:
            scopes.append("openid")

        # Issue tokens
        access_token = create_access_token(user_info["user_id"], payload.client_id, actual_user_type, scopes=scopes)
        refresh_token_jwt = create_refresh_token(user_info["user_id"], payload.client_id, actual_user_type)

        # Persist refresh token
        if getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 0) and settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0:
            refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
        await RefreshTokenRepository.create_refresh_token(
            token=refresh_token_jwt,
            user_id=user_info["user_id"],
            user_type=actual_user_type,
            client_id=payload.client_id,
            scopes=scopes,
            expires_at=refresh_token_expires_at,
        )

        # Auto-consent for API-first login to avoid separate consent step for first-party/mobile
        try:
            is_consented = await OAuthConsentRepository.has_user_consented(
                user_info["user_id"], payload.client_id, scopes, actual_user_type
            )
            if not is_consented:
                await OAuthConsentRepository.create_consent(
                    user_info["user_id"], payload.client_id, scopes, actual_user_type
                )
        except Exception as e:
            # Do not block login on consent persistence issues; user can consent later via API
            log_error(logger, "auto consent failed", exc=e)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_jwt,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            scope=" ".join(scopes) if scopes else None,
            needs_password_change=bool(user_info.get("is_first_login")),
            requires_citizen_id=user_info.get("requires_citizen_id"),
            yuwa_osm_user_id=user_info.get("yuwa_osm_user_id"),
        )

    @staticmethod
    async def refresh_token_api(payload: RefreshRequest) -> TokenResponse:
        """API-first refresh supporting public clients (no secret)."""
        client = await ClientRepository.find_client_by_client_id(payload.client_id)
        if not client or not client.is_active:
            raise UnauthorizedException(detail="invalid_client")
        allowed_grants = set((client.grant_types or []))
        if "refresh_token" not in allowed_grants:
            raise UnauthorizedException(detail="unsupported_grant_type")

        # If client_secret is provided, enforce match (confidential); otherwise allow public
        if payload.client_secret and client.client_secret != payload.client_secret:
            raise UnauthorizedException(detail="invalid_client")

        db_refresh = await RefreshTokenRepository.find_refresh_token_by_token(payload.refresh_token)
        if not db_refresh:
            raise UnauthorizedException(detail="invalid_refresh_token")
        if db_refresh.client_id != payload.client_id:
            raise UnauthorizedException(detail="invalid_client")
        if db_refresh.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException(detail="refresh_token_expired")

        if not is_user_type_allowed(client, db_refresh.user_type):
            log_info(
                logger,
                "refresh_token_api: user type not allowed",
                extra={"client_id": payload.client_id, "user_type": db_refresh.user_type},
            )
            raise UnauthorizedException(detail="user_type_not_allowed")

        if await Oauth2Service._is_user_denied_by_allowlist(client, db_refresh.user_id, db_refresh.user_type):
            log_info(
                logger,
                "refresh_token_api: user not in allowlist",
                extra={"client_id": payload.client_id, "user_id": db_refresh.user_id},
            )
            raise UnauthorizedException(detail="user_not_allowed")

        if await Oauth2Service._is_user_blocked(client, db_refresh.user_id, db_refresh.user_type):
            log_info(
                logger,
                "refresh_token_api: user blocked",
                extra={"client_id": payload.client_id, "user_id": db_refresh.user_id},
            )
            raise UnauthorizedException(detail="user_blocked")

        # Rotate
        await RefreshTokenRepository.revoke_refresh_token(payload.refresh_token)

        user_id_str = str(db_refresh.user_id)
        user_type = db_refresh.user_type
        new_access = create_access_token(user_id_str, payload.client_id, user_type, scopes=db_refresh.scopes)
        new_refresh = create_refresh_token(user_id_str, payload.client_id, user_type)

        if getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 0) and settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0:
            new_refresh_exp = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            new_refresh_exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
        await RefreshTokenRepository.create_refresh_token(
            token=new_refresh,
            user_id=user_id_str,
            user_type=user_type,
            client_id=payload.client_id,
            scopes=db_refresh.scopes,
            expires_at=new_refresh_exp,
        )

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            scope=" ".join(db_refresh.scopes) if db_refresh.scopes else None,
        )

    # ------------------------------------------------------------------
    # Client access management helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _serialize_client(client: OAuthClient) -> dict:
        """Serialize OAuthClient model for API responses."""
        allowed = getattr(client, "allowed_user_types", None)
        normalized: list[str] | None
        if allowed is None:
            normalized = None
        else:
            if isinstance(allowed, str):
                values = [allowed]
            elif isinstance(allowed, Iterable):
                values = [v for v in allowed if isinstance(v, str)]
            else:
                values = []
            normalized = sorted({v.strip().lower() for v in values if isinstance(v, str) and v.strip() and v.strip().lower() in VALID_USER_TYPES})

        scope_value = " ".join(client.scopes or [])
        base_params = [
            ("client_id", client.client_id),
            ("redirect_uri", client.redirect_uri),
        ]
        if scope_value:
            base_params.append(("scope", scope_value))
        base_params.append(("state", _STATE_PLACEHOLDER))

        login_example = _build_url_with_params(client.login_url, list(base_params))
        consent_example = _build_url_with_params(client.consent_url, list(base_params))

        return {
            "id": str(client.id),
            "client_id": client.client_id,
            "client_name": client.client_name,
            "client_description": client.client_description,
            "redirect_uri": client.redirect_uri,
            "login_url": client.login_url,
            "login_url_example": login_example,
            "consent_url": client.consent_url,
            "consent_url_example": consent_example,
            "scopes": client.scopes,
            "grant_types": client.grant_types,
            "public_client": client.public_client,
            "allowed_user_types": normalized,
            "allowlist_enabled": bool(getattr(client, "allowlist_enabled", False)),
            "is_active": client.is_active,
        }

    @staticmethod
    def _normalize_user_types_payload(user_types: list[str] | None) -> list[str] | None:
        if user_types is None:
            return None
        if not isinstance(user_types, list):
            raise BadRequestException(detail="allowed_user_types_must_be_list")
        cleaned = {str(value).strip().lower() for value in user_types if isinstance(value, str) and value.strip()}
        invalid = cleaned - set(VALID_USER_TYPES)
        if invalid:
            raise BadRequestException(detail="invalid_user_type")
        return sorted(cleaned)

    @staticmethod
    def _normalize_user_types_value(values: Iterable[str] | None) -> list[str] | None:
        if values is None:
            return None
        if isinstance(values, str):
            raw_values = [values]
        elif isinstance(values, Iterable):
            raw_values = [v for v in values if isinstance(v, str)]
        else:
            raw_values = []
        normalized = {v.strip().lower() for v in raw_values if isinstance(v, str) and v.strip()}
        normalized = {v for v in normalized if v in VALID_USER_TYPES}
        return sorted(normalized)

    @staticmethod
    async def _is_user_denied_by_allowlist(client: OAuthClient | None, user_id: str | None, user_type: str | None) -> bool:
        if not client or not user_id or not user_type:
            return False
        if not bool(getattr(client, "allowlist_enabled", False)):
            return False
        try:
            allowed = await OAuthClientAllowRepository.is_user_allowed(str(client.id), str(user_id), str(user_type))
            return not allowed
        except OperationalError:
            log_info(
                logger,
                "allowlist lookup skipped (table missing?)",
                extra={"client_id": getattr(client, "client_id", None)},
            )
            return False
        except Exception as exc:
            log_error(logger, "allowlist lookup failed", exc=exc)
            raise InternalServerErrorException(detail="allowlist_lookup_failed")

    @staticmethod
    def _normalize_string_collection(values: Iterable[str] | None) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values or []:
            if not isinstance(raw, str):
                continue
            trimmed = raw.strip()
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            cleaned.append(trimmed)
        return cleaned

    @staticmethod
    def _normalize_scopes(values: Iterable[str] | None) -> list[str]:
        scopes = Oauth2Service._normalize_string_collection(values)
        if not scopes:
            raise BadRequestException(detail="scopes_required")
        if "openid" not in scopes:
            scopes.insert(0, "openid")
        return scopes

    @staticmethod
    def _normalize_grant_types(values: Iterable[str] | None) -> list[str]:
        grants = Oauth2Service._normalize_string_collection(values)
        if not grants:
            raise BadRequestException(detail="grant_types_required")
        return grants

    @staticmethod
    def _require_non_empty(value: Optional[str], field: str) -> str:
        if value is None:
            raise BadRequestException(detail=f"{field}_required")
        trimmed = value.strip()
        if not trimmed:
            raise BadRequestException(detail=f"{field}_required")
        return trimmed

    @staticmethod
    def _serialize_block(entry: OAuthClientBlock, client: OAuthClient) -> dict:
        return {
            "id": str(entry.id),
            "client_id": client.client_id,
            "client_uuid": str(client.id),
            "user_id": str(entry.user_id),
            "user_type": entry.user_type,
            "citizen_id": entry.citizen_id,
            "full_name": entry.full_name,
            "note": entry.note,
            "created_by": str(entry.created_by) if entry.created_by else None,
            "created_at": entry.created_at,
        }

    @staticmethod
    async def _is_user_blocked(client: OAuthClient | None, user_id: str | None, user_type: str | None) -> bool:
        if not client or not user_id or not user_type:
            return False
        try:
            return await OAuthClientBlockRepository.is_user_blocked(str(client.id), str(user_id), user_type)
        except OperationalError as exc:
            log_info(
                logger,
                "block lookup skipped (table missing?)",
                extra={"client_id": getattr(client, "client_id", None)},
            )
            return False
        except Exception as exc:
            log_error(logger, "block lookup failed", exc=exc)
            raise InternalServerErrorException(detail="block_lookup_failed")

    @staticmethod
    def _serialize_allow(entry: Any, client: OAuthClient) -> dict:
        return {
            "id": str(entry.id),
            "client_id": client.client_id,
            "client_uuid": str(client.id),
            "user_id": str(entry.user_id),
            "user_type": entry.user_type,
            "citizen_id": entry.citizen_id,
            "full_name": entry.full_name,
            "note": entry.note,
            "created_by": str(entry.created_by) if entry.created_by else None,
            "created_at": entry.created_at,
        }

    @staticmethod
    async def update_client_allowlist_mode(client_id: str, enabled: bool, actor: dict | None = None) -> dict:
        actor_id = None
        actor_type = None
        if actor is not None:
            actor_value = actor.get("user_id")
            if actor_value:
                actor_id = str(actor_value)
            actor_type_value = actor.get("user_type")
            if actor_type_value:
                actor_type = str(actor_type_value)

        client = await ClientRepository.set_allowlist_enabled(client_id, enabled, updated_by=actor_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        if bool(enabled):
            # Ensure the actor who enabled allowlist is not locked out.
            if actor_id and actor_type and actor_type in VALID_USER_TYPES:
                try:
                    exists = await OAuthClientAllowRepository.find_existing_allow(str(client.id), actor_id, actor_type)
                    if not exists:
                        identity = await Oauth2Service._load_identity_by_id(actor_type, actor_id)
                        await OAuthClientAllowRepository.create_allow(
                            client_db_id=str(client.id),
                            user_id=actor_id,
                            user_type=actor_type,
                            citizen_id=(identity or {}).get("citizen_id"),
                            full_name=(identity or {}).get("full_name"),
                            note="auto-added (enabled allowlist)",
                            created_by=str(actor_id),
                        )
                except OperationalError:
                    log_info(
                        logger,
                        "auto-add actor to allowlist skipped (table missing?)",
                        extra={"client_id": getattr(client, "client_id", None)},
                    )
                except Exception as exc:
                    log_error(logger, "auto-add actor to allowlist failed", exc=exc)

            try:
                if actor_id and actor_type and actor_type in VALID_USER_TYPES:
                    await RefreshTokenRepository.revoke_all_client_refresh_tokens_except_user(
                        actor_id,
                        client.client_id,
                        actor_type,
                    )
                else:
                    await RefreshTokenRepository.revoke_all_client_refresh_tokens(client.client_id)
            except Exception as exc:
                log_error(logger, "revoke_all_client_refresh_tokens_failed", exc=exc)

        return Oauth2Service._serialize_client(client)

    @staticmethod
    async def list_client_allows(client_id: str, filters: Any | None = None) -> List[dict]:
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        params = filters
        user_type = getattr(params, "user_type", None) if params is not None else None
        search = getattr(params, "search", None) if params is not None else None
        try:
            entries = await OAuthClientAllowRepository.list_allows(
                str(client.id),
                user_type=user_type,
                search=search,
            )
        except OperationalError:
            log_info(
                logger,
                "list_client_allows skipped (table missing?)",
                extra={"client_id": client.client_id},
            )
            return []
        return [Oauth2Service._serialize_allow(entry, client) for entry in entries]

    @staticmethod
    async def create_client_allow(client_id: str, payload: Any, actor: dict) -> dict:
        if payload.user_type not in VALID_USER_TYPES:
            raise BadRequestException(detail="invalid_user_type")

        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client or not client.is_active:
            raise NotFoundException(detail="client_not_found")

        actor_id = actor.get("user_id")
        if not actor_id:
            raise BadRequestException(detail="actor_missing")

        identity = await Oauth2Service._load_identity_by_id(payload.user_type, payload.user_id)
        if not identity:
            raise NotFoundException(detail="user_not_found")

        try:
            existing = await OAuthClientAllowRepository.find_existing_allow(
                str(client.id), payload.user_id, payload.user_type
            )
        except OperationalError:
            log_info(
                logger,
                "create_client_allow skipped during lookup (table missing?)",
                extra={"client_id": client.client_id},
            )
            raise InternalServerErrorException(detail="allowlist_feature_not_ready")

        if existing:
            raise BadRequestException(detail="user_already_allowed")

        try:
            entry = await OAuthClientAllowRepository.create_allow(
                client_db_id=str(client.id),
                user_id=payload.user_id,
                user_type=payload.user_type,
                citizen_id=identity.get("citizen_id"),
                full_name=identity.get("full_name"),
                note=getattr(payload, "note", None),
                created_by=str(actor_id),
            )
        except OperationalError:
            log_info(
                logger,
                "create_client_allow skipped (table missing?)",
                extra={"client_id": client.client_id},
            )
            raise InternalServerErrorException(detail="allowlist_feature_not_ready")

        return Oauth2Service._serialize_allow(entry, client)

    @staticmethod
    async def delete_client_allow(client_id: str, allow_id: str) -> None:
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        try:
            deleted = await OAuthClientAllowRepository.delete_allow(allow_id, str(client.id))
        except OperationalError:
            log_info(
                logger,
                "delete_client_allow skipped (table missing?)",
                extra={"client_id": client.client_id},
            )
            raise NotFoundException(detail="allowlist_feature_not_ready")
        if not deleted:
            raise NotFoundException(detail="allow_not_found")

    @staticmethod
    def _format_full_name(first_name: Optional[str], last_name: Optional[str]) -> str:
        parts = [part.strip() for part in [first_name or "", last_name or ""] if part and part.strip()]
        return " ".join(parts) if parts else (first_name or last_name or "")

    @staticmethod
    async def list_oauth_clients() -> list[dict]:
        clients = await ClientRepository.list_clients()
        return [Oauth2Service._serialize_client(client) for client in clients]

    @staticmethod
    async def update_client_user_types(client_id: str, user_types: list[str] | None) -> dict:
        normalized_list = Oauth2Service._normalize_user_types_payload(user_types)

        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        existing_default = await OAuthClientUserTypeDefaultRepository.get_default(str(client.id))
        if not existing_default:
            current_value = Oauth2Service._normalize_user_types_value(getattr(client, "allowed_user_types", None))
            await OAuthClientUserTypeDefaultRepository.ensure_default(str(client.id), current_value)

        client = await ClientRepository.set_allowed_user_types(client_id, normalized_list)
        if not client:
            raise NotFoundException(detail="client_not_found")

        return Oauth2Service._serialize_client(client)

    @staticmethod
    async def get_client_user_types_default(client_id: str) -> dict:
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        default_entry = await OAuthClientUserTypeDefaultRepository.get_default(str(client.id))
        allowed = Oauth2Service._normalize_user_types_value(
            getattr(default_entry, "allowed_user_types", None) if default_entry else None
        )
        return {
            "client_id": client.client_id,
            "allowed_user_types": allowed,
            "updated_at": getattr(default_entry, "updated_at", None) if default_entry else None,
        }

    @staticmethod
    async def set_client_user_types_default(client_id: str, user_types: list[str] | None, actor: dict | None = None) -> dict:
        normalized_list = Oauth2Service._normalize_user_types_payload(user_types)
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        actor_id = None
        if actor is not None:
            actor_value = actor.get("user_id")
            if actor_value:
                actor_id = str(actor_value)

        default_entry = await OAuthClientUserTypeDefaultRepository.upsert_default(
            str(client.id),
            normalized_list,
            actor_id=actor_id,
        )

        allowed = Oauth2Service._normalize_user_types_value(getattr(default_entry, "allowed_user_types", None))
        return {
            "client_id": client.client_id,
            "allowed_user_types": allowed,
            "updated_at": getattr(default_entry, "updated_at", None),
        }

    @staticmethod
    async def reset_client_user_types_to_default(client_id: str, actor: dict | None = None) -> dict:
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        default_entry = await OAuthClientUserTypeDefaultRepository.get_default(str(client.id))
        if default_entry is None:
            current_value = Oauth2Service._normalize_user_types_value(getattr(client, "allowed_user_types", None))
            default_entry = await OAuthClientUserTypeDefaultRepository.ensure_default(
                str(client.id),
                current_value,
            )

        normalized_default = Oauth2Service._normalize_user_types_value(
            getattr(default_entry, "allowed_user_types", None)
        )
        updated_client = await ClientRepository.set_allowed_user_types(client_id, normalized_default)
        if not updated_client:
            raise NotFoundException(detail="client_not_found")

        return Oauth2Service._serialize_client(updated_client)

    @staticmethod
    async def update_client_details(client_id: str, payload: UpdateClientSchema, actor: dict | None = None) -> dict:
        scopes = Oauth2Service._normalize_scopes(payload.scopes)
        grant_types = Oauth2Service._normalize_grant_types(payload.grant_types)
        client_name = Oauth2Service._require_non_empty(payload.client_name, "client_name")
        redirect_uri = Oauth2Service._require_non_empty(payload.redirect_uri, "redirect_uri")
        login_url = Oauth2Service._require_non_empty(payload.login_url, "login_url")
        consent_url = Oauth2Service._require_non_empty(payload.consent_url, "consent_url")
        description = payload.client_description.strip() if payload.client_description else None

        actor_id = None
        if actor is not None:
            actor_value = actor.get("user_id")
            if actor_value:
                actor_id = str(actor_value)

        updated = await ClientRepository.update_client_details(
            client_id,
            client_name=client_name,
            client_description=description,
            redirect_uri=redirect_uri,
            login_url=login_url,
            consent_url=consent_url,
            scopes=scopes,
            grant_types=grant_types,
            public_client=payload.public_client,
            updated_by=actor_id,
        )

        if not updated:
            raise NotFoundException(detail="client_not_found")

        return Oauth2Service._serialize_client(updated)

    @staticmethod
    async def list_client_blocks(client_id: str, filters: ClientBlockQueryParams | None = None) -> List[dict]:
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        params = filters or ClientBlockQueryParams()
        try:
            entries = await OAuthClientBlockRepository.list_blocks(
                str(client.id),
                user_type=params.user_type,
                search=params.search,
            )
        except OperationalError:
            log_info(
                logger,
                "list_client_blocks skipped (table missing?)",
                extra={"client_id": client.client_id},
            )
            return []
        return [Oauth2Service._serialize_block(entry, client) for entry in entries]

    @staticmethod
    async def create_client_block(client_id: str, payload: CreateClientBlockRequest, actor: dict) -> dict:
        if payload.user_type not in VALID_USER_TYPES:
            raise BadRequestException(detail="invalid_user_type")

        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client or not client.is_active:
            raise NotFoundException(detail="client_not_found")

        actor_id = actor.get("user_id")
        if not actor_id:
            raise BadRequestException(detail="actor_missing")

        identity = await Oauth2Service._load_identity_by_id(payload.user_type, payload.user_id)
        if not identity:
            raise NotFoundException(detail="user_not_found")

        try:
            existing = await OAuthClientBlockRepository.find_existing_block(
                str(client.id), payload.user_id, payload.user_type
            )
        except OperationalError:
            log_info(
                logger,
                "create_client_block skipped during lookup (table missing?)",
                extra={"client_id": client.client_id},
            )
            raise InternalServerErrorException(detail="block_feature_not_ready")

        if existing:
            raise BadRequestException(detail="user_already_blocked")

        try:
            entry = await OAuthClientBlockRepository.create_block(
                client_db_id=str(client.id),
                user_id=payload.user_id,
                user_type=payload.user_type,
                citizen_id=identity.get("citizen_id"),
                full_name=identity.get("full_name"),
                note=payload.note,
                created_by=str(actor_id),
            )
        except OperationalError:
            log_info(
                logger,
                "create_client_block skipped (table missing?)",
                extra={"client_id": client.client_id},
            )
            raise InternalServerErrorException(detail="block_feature_not_ready")

        try:
            await RefreshTokenRepository.revoke_all_user_refresh_tokens(payload.user_id, client.client_id, payload.user_type)
        except Exception as exc:
            log_error(logger, "revoke_refresh_tokens_failed", exc=exc)

        return Oauth2Service._serialize_block(entry, client)

    @staticmethod
    async def delete_client_block(client_id: str, block_id: str) -> None:
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise NotFoundException(detail="client_not_found")

        try:
            deleted = await OAuthClientBlockRepository.delete_block(block_id, str(client.id))
        except OperationalError:
            log_info(
                logger,
                "delete_client_block skipped (table missing?)",
                extra={"client_id": client.client_id},
            )
            raise NotFoundException(detail="block_feature_not_ready")
        if not deleted:
            raise NotFoundException(detail="block_not_found")

    @staticmethod
    async def search_block_candidates(user_type: str, query: str, limit: int = 20, offset: int = 0) -> dict:
        normalized_type = (user_type or "").strip().lower()
        if normalized_type not in VALID_USER_TYPES:
            raise BadRequestException(detail="invalid_user_type")

        search_term = (query or "").strip()
        if not search_term:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}

        capped_limit = max(1, min(limit, 50))
        capped_offset = max(0, offset)

        total = 0
        if normalized_type == "officer":
            records, total = await OfficerProfileRepository.search_active_officers(
                search_term,
                capped_limit,
                active_only=False,
                offset=capped_offset,
            )
        elif normalized_type == "osm":
            records, total = await OSMProfileRepository.search_active_osm(
                search_term,
                capped_limit,
                active_only=False,
                offset=capped_offset,
            )
        elif normalized_type == "yuwa_osm":
            records, total = await YuwaOSMUserRepository.search_active_users(
                search_term,
                capped_limit,
                active_only=False,
                offset=capped_offset,
            )
        elif normalized_type == "people":
            records, total = await PeopleUserRepository.search_active_users(
                search_term,
                capped_limit,
                active_only=False,
                offset=capped_offset,
            )
        elif normalized_type == "gen_h":
            records, total = await GenHUserRepository.search_active_users(
                search_term,
                capped_limit,
                active_only=False,
                offset=capped_offset,
            )
        else:  # pragma: no cover - safeguard
            records = []

        def _get_related_attribute(obj: object, attr: str, name_field: str) -> Any:
            related = getattr(obj, attr, None)
            if not related:
                return None
            return getattr(related, name_field, None)

        results: List[dict] = []
        for profile in records:
            full_name = Oauth2Service._format_full_name(
                getattr(profile, "first_name", None), getattr(profile, "last_name", None)
            )

            phone = getattr(profile, "phone", None)
            email = getattr(profile, "email", None)
            province_name = None
            district_name = None
            subdistrict_name = None
            organization = None
            role = None
            province_code = None
            district_code = None
            subdistrict_code = None
            village_code = None
            region_code = None
            health_area_code = None
            is_transferred = None
            transferred_at = None
            transferred_by = None
            yuwa_osm_id = None
            yuwa_osm_code = None

            if normalized_type == "officer":
                phone = getattr(profile, "phone", None)
                email = getattr(profile, "email", None)
                province_name = _get_related_attribute(profile, "province", "province_name_th")
                district_name = _get_related_attribute(profile, "district", "district_name_th")
                subdistrict_name = _get_related_attribute(profile, "subdistrict", "subdistrict_name_th")
                organization = _get_related_attribute(profile, "health_area", "health_area_name_th")
                role = _get_related_attribute(profile, "position", "position_name_th")
                province_code = getattr(profile, "province_id", None)
                district_code = getattr(profile, "district_id", None)
                subdistrict_code = getattr(profile, "subdistrict_id", None)
                village_code = getattr(profile, "area_code", None)
                province = getattr(profile, "province", None)
                if province is not None:
                    region_code = getattr(province, "region_id", None)
                    health_area_code = getattr(province, "health_area_id", None)
                health_area_code = health_area_code or getattr(profile, "health_area_id", None)
            elif normalized_type == "osm":
                phone = getattr(profile, "phone", None)
                email = getattr(profile, "email", None)
                province_name = _get_related_attribute(profile, "province", "province_name_th")
                district_name = _get_related_attribute(profile, "district", "district_name_th")
                subdistrict_name = _get_related_attribute(profile, "subdistrict", "subdistrict_name_th")
                organization = _get_related_attribute(profile, "health_service", "health_service_name_th")
                role = "อสม."
                province_code = getattr(profile, "province_id", None)
                district_code = getattr(profile, "district_id", None)
                subdistrict_code = getattr(profile, "subdistrict_id", None)
                village_code = getattr(profile, "village_code", None)
                province = getattr(profile, "province", None)
                if province is not None:
                    region_code = getattr(province, "region_id", None)
                    health_area_code = getattr(province, "health_area_id", None)
            elif normalized_type == "yuwa_osm":
                phone = getattr(profile, "phone_number", None)
                email = getattr(profile, "email", None)
                province_name = getattr(profile, "province_name", None)
                district_name = getattr(profile, "district_name", None)
                subdistrict_name = getattr(profile, "subdistrict_name", None)
                organization = getattr(profile, "organization", None) or getattr(profile, "school", None)
                role = "Yuwa OSM"
                province_code = getattr(profile, "province_code", None)
                district_code = getattr(profile, "district_code", None)
                subdistrict_code = getattr(profile, "subdistrict_code", None)
            elif normalized_type == "people":
                phone = getattr(profile, "phone_number", None)
                email = getattr(profile, "email", None)
                province_name = getattr(profile, "province_name", None)
                district_name = getattr(profile, "district_name", None)
                subdistrict_name = getattr(profile, "subdistrict_name", None)
                role = "People"
                province_code = getattr(profile, "province_code", None)
                district_code = getattr(profile, "district_code", None)
                subdistrict_code = getattr(profile, "subdistrict_code", None)
                is_transferred = bool(getattr(profile, "is_transferred", False))
                transferred_at = getattr(profile, "transferred_at", None)
                transferred_by = getattr(profile, "transferred_by", None)
                yuwa_osm_id = getattr(profile, "yuwa_osm_id", None)
                yuwa_osm_code = getattr(profile, "yuwa_osm_code", None)
                if not is_transferred and not yuwa_osm_id:
                    yuwa = await YuwaOSMUserRepository.get_user_by_source_people_id(str(getattr(profile, "id")))
                    if not yuwa and getattr(profile, "citizen_id", None):
                        yuwa = await YuwaOSMUserRepository.get_user_by_citizen_id(profile.citizen_id)
                    if yuwa:
                        is_transferred = True
                        yuwa_osm_id = yuwa.id
                        yuwa_osm_code = getattr(yuwa, "yuwa_osm_code", None) or yuwa_osm_code
                        transferred_at = getattr(yuwa, "transferred_at", None)
                        transferred_by = getattr(yuwa, "transferred_by", None)
            elif normalized_type == "gen_h":
                phone = getattr(profile, "phone_number", None)
                email = getattr(profile, "email", None)
                province_name = getattr(profile, "province_name", None)
                district_name = getattr(profile, "district_name", None)
                subdistrict_name = getattr(profile, "subdistrict_name", None)
                organization = getattr(profile, "school", None)
                role = "Gen H"
                province_code = getattr(profile, "province_code", None)
                district_code = getattr(profile, "district_code", None)
                subdistrict_code = getattr(profile, "subdistrict_code", None)

            results.append(
                {
                    "user_id": str(getattr(profile, "id")),
                    "user_type": normalized_type,
                    "full_name": full_name,
                    "citizen_id": getattr(profile, "citizen_id", None),
                    "phone": phone,
                    "email": email,
                    "is_active": bool(getattr(profile, "is_active", True)),
                    "is_transferred": is_transferred,
                    "transferred_at": transferred_at,
                    "transferred_by": str(transferred_by) if transferred_by else None,
                    "yuwa_osm_id": str(yuwa_osm_id) if yuwa_osm_id else None,
                    "yuwa_osm_code": yuwa_osm_code,
                    "province_name": province_name,
                    "district_name": district_name,
                    "subdistrict_name": subdistrict_name,
                    "organization": organization,
                    "role": role,
                    "province_code": province_code,
                    "district_code": district_code,
                    "subdistrict_code": subdistrict_code,
                    "village_code": village_code,
                    "region_code": region_code,
                    "health_area_code": health_area_code,
                }
            )

        return {"items": results, "total": total, "limit": capped_limit, "offset": capped_offset}

    @staticmethod
    async def _load_identity_by_id(user_type: str, user_id: str) -> Optional[dict]:
        if not user_type or not user_id:
            return None

        match user_type:
            case "officer":
                profile = await OfficerProfileRepository.get_basic_officer_by_id(user_id)
            case "osm":
                profile = await OSMProfileRepository.find_basic_profile_by_id(user_id)
            case "yuwa_osm":
                profile = await YuwaOSMUserRepository.find_basic_profile_by_id(user_id)
            case "people":
                profile = await PeopleUserRepository.find_basic_profile_by_id(user_id)
            case "gen_h":
                profile = await GenHUserRepository.find_basic_profile_by_id(user_id)
            case _:
                return None

        if not profile:
            return None

        full_name = Oauth2Service._format_full_name(getattr(profile, "first_name", None), getattr(profile, "last_name", None))
        citizen_id = getattr(profile, "citizen_id", None) or getattr(profile, "gen_h_code", None)

        return {
            "id": str(getattr(profile, "id")),
            "citizen_id": citizen_id,
            "full_name": full_name,
            "is_active": getattr(profile, "is_active", True),
        }

def check_legacy_password(password: str, hashed_password: str) -> bool:
    is_password_match = hashlib.md5(password.encode()).hexdigest() == hashed_password
    """
    ตรวจสอบว่ารหัสผ่านที่ระบุตรงกับรหัสผ่าน MD5 แบบเก่าที่แฮชไว้หรือไม่
    """
    return is_password_match

def bcrypt_hash_password(password: str) -> str:
    """
    จัดการรหัสผ่านโดยใช้ bcrypt เพื่อทำการแฮชรหัสผ่าน
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _get_authenticated_user(request: Request):
        """
        ตรวจสอบ JWT token ใน header Authorization ว่ายัง valid และถอดรหัสได้ไหม
        คืนข้อมูล user payload ถ้าถูกต้อง หรือ None ถ้าไม่พบหรือหมดอายุ
        """
        session_token = request.cookies.get("session_token")
        if not session_token:
            return None

        try:
            payload = decode_jwt_session_token(session_token)
            user_id = payload.get("user_id")
            user_type = payload.get("ut")
            return {"user_id": user_id, "user_type": user_type}
        except Exception as e:
            return None

async def create_auth_code(user_id: str, user_type: str, client_id: str, scopes: List[str], code_challenge: str | None = None, code_challenge_method: str | None = None, nonce: str | None = None):
    code = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(minutes=settings.OAUTH2_AUTHORIZATION_CODE_EXPIRE_MINUTES)
    await OAuthAuthorizationCodeRepository.create_authorization_code(
        code,
        user_id,
        user_type,
        client_id,
        scopes,
        expires_at,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
    )
    return code


def _resolve_candidate_user_types(requested_user_type: str | None) -> Iterable[str]:
    if not requested_user_type:
        return USER_TYPE_PRIORITY
    if requested_user_type in VALID_USER_TYPES:
        return (requested_user_type,)
    return ()


async def _probe_first_login_state(user_type: str, citizen_id: str):
    match user_type:
        case "osm":
            return await OSMProfileRepository.is_citizen_id_exist_and_is_first_login(citizen_id)
        case "officer":
            return await OfficerProfileRepository.is_citizen_id_exist_and_is_first_login(citizen_id)
        case "yuwa_osm":
            return await YuwaOSMUserRepository.is_citizen_id_exist_and_is_first_login(citizen_id)
        case "people":
            return await PeopleUserRepository.is_citizen_id_exist_and_is_first_login(citizen_id)
        case "gen_h":
            return await GenHUserRepository.is_gen_h_code_exist_and_is_first_login(citizen_id)
        case _:
            return None


async def _validate_credentials(username: str, password: str, user_type: str | None) -> dict | None:
    for candidate in _resolve_candidate_user_types(user_type):
        profile = None
        try:
            match candidate:
                case "osm":
                    profile = await OSMProfileRepository.find_osm_basic_profile_by_citizen_id(username)
                case "officer":
                    profile = await OfficerProfileRepository.find_officer_basic_profile_by_citizen_id(username)
                case "yuwa_osm":
                    profile = await YuwaOSMUserRepository.find_basic_profile_by_citizen_id(username)
                    # รองรับ login ด้วย gen_h_code สำหรับ user ที่ upgrade จาก gen-h
                    if not profile:
                        profile = await YuwaOSMUserRepository.find_basic_profile_by_gen_h_code(username)
                case "people":
                    profile = await PeopleUserRepository.find_basic_profile_by_citizen_id(username)
                case "gen_h":
                    profile = await GenHUserRepository.find_basic_profile_by_gen_h_code(username)
                    # รองรับ login ด้วย citizen_id สำหรับ gen_h ที่กรอก citizen_id ตอน register
                    if not profile:
                        profile = await GenHUserRepository.find_basic_profile_by_citizen_id(username)
                case _:
                    continue
        except Exception as exc:
            log_error(logger, f"validate {candidate} credentials failed", exc=exc)
            continue

        if not profile or not getattr(profile, "password_hash", None):
            continue

        # Skip inactive accounts regardless of password outcome
        if hasattr(profile, "is_active") and not getattr(profile, "is_active"):
            continue

        # Skip transferred People accounts — user must login as yuwa_osm instead
        if candidate == "people" and getattr(profile, "is_transferred", False):
            continue

        hashed_value = profile.password_hash
        hashed_bytes = hashed_value.encode() if isinstance(hashed_value, str) else hashed_value

        is_password_match = False
        try:
            is_password_match = await asyncio.to_thread(bcrypt.checkpw, password.encode(), hashed_bytes)
        except ValueError:
            if isinstance(hashed_value, str) and len(hashed_value) == 32:
                is_password_match = check_legacy_password(password, hashed_value)
        if not is_password_match:
            continue

        cid = getattr(profile, "citizen_id", None) or getattr(profile, "gen_h_code", None)
        return get_user_basic_info(profile, candidate, citizen_id=cid)

    return None


def get_user_basic_info(profile: OSMProfile | OfficerProfile | YuwaOSMUser | PeopleUser | GenHUser, user_type: str, citizen_id: str | None = None):
    first_name = getattr(profile, "first_name", "") or ""
    last_name = getattr(profile, "last_name", "") or ""
    full_name = " ".join(part for part in [first_name.strip(), last_name.strip()] if part)

    info = {
        "user_id": str(profile.id),
        "name": full_name.strip() or first_name or str(profile.id),
        "user_type": user_type,
        "citizen_id": citizen_id or getattr(profile, "citizen_id", None),
    }

    province_code = getattr(profile, "province_id", None) or getattr(profile, "province_code", None)
    district_code = getattr(profile, "district_id", None) or getattr(profile, "district_code", None)
    subdistrict_code = getattr(profile, "subdistrict_id", None) or getattr(profile, "subdistrict_code", None)

    if province_code is not None:
        info["province_code"] = province_code
    if district_code is not None:
        info["district_code"] = district_code
    if subdistrict_code is not None:
        info["subdistrict_code"] = subdistrict_code

    phone = getattr(profile, "phone", None) or getattr(profile, "phone_number", None)
    if phone is not None:
        info["phone"] = phone

    email = getattr(profile, "email", None)
    if email is not None:
        info["email"] = email

    info["is_first_login"] = bool(getattr(profile, "is_first_login", False))

    # gen_h migration ยังไม่มี citizen_id → frontend ต้องบังคับกรอก citizen_id เพื่อ upgrade เป็น yuwa_osm
    # gen_h self_register → ไม่ต้องกรอก citizen_id (เป็น gen_h ปกติ)
    if user_type == "gen_h":
        source_type = getattr(profile, "source_type", "self_register") or "self_register"
        citizen_id_val = getattr(profile, "citizen_id", None) or ""
        yuwa_osm_user_id = getattr(profile, "yuwa_osm_user_id", None)
        info["requires_citizen_id"] = source_type == "migration" and not citizen_id_val.strip()
        info["yuwa_osm_user_id"] = str(yuwa_osm_user_id) if yuwa_osm_user_id else None

    return info
def set_user_cookie(response: RedirectResponse, user: dict):
    session_token = create_session_token(user["user_id"],user["user_type"])
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,  # ปลอดภัยจาก JS
        max_age=1800,   # 30 นาที
        secure=getattr(settings, "COOKIE_SECURE", True),    # ใช้ https เท่านั้น (prod)
        samesite=getattr(settings, "COOKIE_SAMESITE", "Lax"),  # ป้องกัน CSRF บางส่วน
    )
        

async def _handle_authorization_code_grant(request: Request, client_id: str, client_secret: str, code: str, redirect_uri: str, code_verifier: str | None = None):
    """Handle authorization code grant type"""
    auth_code = await OAuthAuthorizationCodeRepository.find_authorization_code_by_code(code)
    if not auth_code:
        raise UnauthorizedException(detail="invalid_code")
    if auth_code.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedException(detail="code_expired")
    if auth_code.client_id != client_id:
        raise UnauthorizedException(detail="invalid_client_id")
    
    client = await ClientRepository.find_client_by_client_id(client_id)
    if not client:
        raise UnauthorizedException(detail="invalid_client")
    
    # For confidential clients (public_client=False), verify client_secret
    # For public clients (public_client=True), skip secret verification (use PKCE instead)
    if not client.public_client:
        if not client_secret or client.client_secret != client_secret:
            raise UnauthorizedException(detail="invalid_client")
    
    if client.redirect_uri != redirect_uri:
        raise UnauthorizedException(detail="invalid_redirect_uri")

    if not is_user_type_allowed(client, auth_code.user_type):
        log_info(
            logger,
            "token: authorization_code grant denied",
            extra={"client_id": client_id, "user_type": auth_code.user_type},
        )
        raise UnauthorizedException(detail="user_type_not_allowed")

    if await Oauth2Service._is_user_denied_by_allowlist(client, auth_code.user_id, auth_code.user_type):
        log_info(
            logger,
            "token: authorization_code denied by allowlist",
            extra={"client_id": client_id, "user_id": auth_code.user_id},
        )
        raise UnauthorizedException(detail="user_not_allowed")
    if await Oauth2Service._is_user_blocked(client, auth_code.user_id, auth_code.user_type):
        log_info(
            logger,
            "token: authorization_code blocked",
            extra={"client_id": client_id, "user_id": auth_code.user_id},
        )
        raise UnauthorizedException(detail="user_blocked")
    # PKCE verification if code_challenge present or client is public
    # code_verifier comes from router; avoid re-reading form body
    if auth_code.code_challenge:
        method = (auth_code.code_challenge_method or "S256").upper()
        if not code_verifier:
            raise UnauthorizedException(detail="invalid_request: code_verifier required")
        verifier_bytes = code_verifier.encode()
        if method == "S256":
            digest = hashlib.sha256(verifier_bytes).digest()
            calculated = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        elif method == "plain":
            calculated = code_verifier
        else:
            raise UnauthorizedException(detail="invalid_request: unsupported code_challenge_method")
        if calculated != auth_code.code_challenge:
            raise UnauthorizedException(detail="invalid_grant: code_verifier mismatch")
    
    user_id_str = str(auth_code.user_id)
    user_type = auth_code.user_type
    
    # สร้าง access token และ refresh token
    access_token = create_access_token(user_id_str, client_id, user_type, scopes=auth_code.scopes)
    refresh_token_jwt = create_refresh_token(user_id_str, client_id,user_type)
    
    # บันทึก refresh token ลง database
    # Use DAYS if configured (>0), else fallback to MINUTES
    if getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 0) and settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0:
        refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    await RefreshTokenRepository.create_refresh_token(
        token=refresh_token_jwt,
        user_id=user_id_str,
        user_type=auth_code.user_type,
        client_id=client_id,
        scopes=auth_code.scopes,
        expires_at=refresh_token_expires_at
    )
    
    # ลบ authorization code
    try:
        await OAuthAuthorizationCodeRepository.delete_authorization_code(code)
    except Exception as e:
        log_error(logger, "delete_authorization_code failed", exc=e)
        raise InternalServerErrorException(detail="internal_server_error")

    response = {
        "access_token": access_token,
        "refresh_token": refresh_token_jwt,
        "token_type": "Bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # แปลงเป็นวินาที
        "scope": " ".join(auth_code.scopes)
    }
    if "openid" in (auth_code.scopes or []):
        issuer = settings.OIDC_ISSUER or f"{str(request.base_url).rstrip('/')}{settings.API_V1_PREFIX}/auth"
        response["id_token"] = create_id_token(user_id_str, client_id, issuer, nonce=auth_code.nonce)
    return response

async def _handle_refresh_token_grant(request: Request, client_id: str, client_secret: str, refresh_token: str):
    """Handle refresh token grant type"""
    # ตรวจสอบ client
    client = await ClientRepository.find_client_by_client_id(client_id)
    if not client:
        raise UnauthorizedException(detail="invalid_client")
    
    # For confidential clients, verify secret
    if not client.public_client:
        if not client_secret or client.client_secret != client_secret:
            raise UnauthorizedException(detail="invalid_client")
    
    # ตรวจสอบ refresh token ใน database
    db_refresh_token = await RefreshTokenRepository.find_refresh_token_by_token(refresh_token)
    if not db_refresh_token:
        raise UnauthorizedException(detail="invalid_refresh_token")
    
    # ตรวจสอบว่า refresh token หมดอายุหรือยัง
    if db_refresh_token.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedException(detail="refresh_token_expired")
    
    # ตรวจสอบว่า refresh token ตรงกับ client หรือไม่
    if db_refresh_token.client_id != client_id:
        raise UnauthorizedException(detail="invalid_client")
    
    if not is_user_type_allowed(client, db_refresh_token.user_type):
        log_info(
            logger,
            "token: refresh grant denied",
            extra={"client_id": client_id, "user_type": db_refresh_token.user_type},
        )
        raise UnauthorizedException(detail="user_type_not_allowed")
    if await Oauth2Service._is_user_denied_by_allowlist(client, db_refresh_token.user_id, db_refresh_token.user_type):
        log_info(
            logger,
            "token: refresh grant denied by allowlist",
            extra={"client_id": client_id, "user_id": db_refresh_token.user_id},
        )
        raise UnauthorizedException(detail="user_not_allowed")
    if await Oauth2Service._is_user_blocked(client, db_refresh_token.user_id, db_refresh_token.user_type):
        log_info(
            logger,
            "token: refresh grant blocked",
            extra={"client_id": client_id, "user_id": db_refresh_token.user_id},
        )
        raise UnauthorizedException(detail="user_blocked")

    # Re-validate account state (active + normal status) before issuing new tokens
    identity = await Oauth2Service._load_identity_by_id(db_refresh_token.user_type, db_refresh_token.user_id)
    if not identity or not bool(identity.get("is_active", True)):
        # Revoke current refresh token to prevent reuse when account is inactive/terminated
        await RefreshTokenRepository.revoke_refresh_token(refresh_token)
        raise UnauthorizedException(detail="account_inactive")

    # Revoke refresh token เดิม (token rotation)
    await RefreshTokenRepository.revoke_refresh_token(refresh_token)
    
    # สร้าง access token และ refresh token ใหม่
    user_id_str = str(db_refresh_token.user_id)
    user_type = db_refresh_token.user_type
    new_access_token = create_access_token(user_id_str, client_id, user_type, scopes=db_refresh_token.scopes)
    new_refresh_token_jwt = create_refresh_token(user_id_str, client_id, user_type)
    
    # บันทึก refresh token ใหม่ลง database
    if getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 0) and settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0:
        new_refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        new_refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    await RefreshTokenRepository.create_refresh_token(
        token=new_refresh_token_jwt,
        user_id=user_id_str,
        user_type=user_type,
        client_id=client_id,
        scopes=db_refresh_token.scopes,
        expires_at=new_refresh_token_expires_at
    )
    
    response = {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token_jwt,
        "token_type": "Bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # แปลงเป็นวินาที
        "scope": " ".join(db_refresh_token.scopes)
    }
    if db_refresh_token.scopes and "openid" in db_refresh_token.scopes:
        issuer = settings.OIDC_ISSUER or f"{str(request.base_url).rstrip('/')}{settings.API_V1_PREFIX}/auth"
        response["id_token"] = create_id_token(user_id_str, client_id, issuer)
    return response