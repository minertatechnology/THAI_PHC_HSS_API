from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, Query, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPAuthorizationCredentials, HTTPBearer
from app.api.v1.controllers.oauth2 import Oauth2Controller
from app.api.v1.schemas.oauth2_schema import (
    CreateClientSchema,
    UpdateClientSchema,
    PreLoginResponse,
    PreLoginRequest,
    SetPasswordRequest,
    SetPasswordResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    DirectLoginRequest,
    TokenResponse,
    RefreshRequest,
    ConsentAcceptRequest,
    OAuthClientSummary,
    UpdateClientUserTypesRequest,
    ClientUserTypesDefault,
    UpdateClientUserTypesDefaultRequest,
    ClientBlockEntry,
    CreateClientBlockRequest,
    ClientBlockQueryParams,
    ClientBlockCandidate,
    PaginatedBlockCandidates,
    UpdateClientAllowlistModeRequest,
    ClientAllowEntry,
    CreateClientAllowRequest,
    ClientAllowQueryParams,
    UserType,
)
from fastapi.responses import RedirectResponse
from app.api.middleware.middleware import get_current_user, get_current_user_first_login
from app.api.v1.controllers.user_controller import UserController
from app.configs.config import settings
from app.services.permission_service import PermissionService
import base64
from cryptography.hazmat.primitives import serialization
from app.repositories.client_repository import ClientRepository, OAuthConsentRepository
from app.api.v1.exceptions.http_exceptions import UnauthorizedException
import json
from app.services.mock_auth_service import MockAuthService
from app.utils.client_access_control import get_allowed_user_types, is_user_type_allowed
from app.cache.redis_client import cache_get, cache_set
from app.api.middleware.middleware import _token_hash

AUTH_ME_CACHE_TTL = 120  # 2 minutes — same as token cache
from app.services.auth_me_service import AuthMeService
from app.services.permission_page_service import PermissionPageService


oauth2_router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBasic()
bearer_security = HTTPBearer(auto_error=False)


def _replace_none_with_empty(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, dict):
        return {key: _replace_none_with_empty(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_none_with_empty(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_replace_none_with_empty(item) for item in value)
    if isinstance(value, set):
        return [_replace_none_with_empty(item) for item in value]
    return value


@oauth2_router.post("/pre-login", response_model=PreLoginResponse)
async def oauth2_pre_login(request: PreLoginRequest):
    response = await Oauth2Controller.pre_login(request.citizen_id, request.user_type)
    return response

@oauth2_router.post("/set-password", response_model=SetPasswordResponse)
async def set_password(
    request: SetPasswordRequest,
    current_user_first_login: dict = Depends(get_current_user_first_login),
):
    citizen_id = current_user_first_login["citizen_id"]
    user_type = current_user_first_login["user_type"]
    response = await Oauth2Controller.set_password(citizen_id, user_type, request.password)
    return response


@oauth2_router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    return await Oauth2Controller.change_password(payload, current_user)

@oauth2_router.post("/login")
async def oauth2_login(
    request: Request,
    username: str = Form(None),
    password: str = Form(None),
    client_id: str = Form(None),
    state: str = Form(None),
    user_type: str = Form(None),
    redirect_to: str = Form("/"),
):
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        username_payload = payload.get("username")
        password_payload = payload.get("password")
        if not username_payload or not password_payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username_and_password_required")
        return MockAuthService.login(username_payload, password_payload)

    if None in {username, password, client_id, state}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_form_fields")
    response = await Oauth2Controller.login(username, password, client_id, state, user_type, redirect_to)
    return response

@oauth2_router.post("/login/json", response_model=TokenResponse)
async def oauth2_login_json(payload: DirectLoginRequest):
    """API-first login for mobile/SPA. Prefer mock users but fall back to full OAuth flow."""
    try:
        result = MockAuthService.login(payload.username, payload.password)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED and exc.detail in {"invalid_credentials", "user_not_found"}:
            # Fall back to the real OAuth2 direct login for production credentials
            return await Oauth2Controller.direct_login(payload)
        raise

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token"),
        expires_in=result.get("expires_in", settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        scope="profile",
        profile=result.get("profile"),
        needs_password_change=bool(result.get("needs_password_change", False)),
    )

@oauth2_router.get("/authorize", name="authorize")    
async def oauth2_authorize(request: Request):
    response = await Oauth2Controller.authorize(request)
    return response

@oauth2_router.post("/consent")
async def oauth2_consent_post(request: Request, client_id: str = Form(...), redirect_uri: str = Form(...), scopes: List[str] = Form(...), state: str = Form(...), action: str = Form(...)):
    if action == "approve":
        # ถ้าผู้ใช้ยินยอม consent
        response = await Oauth2Controller.consent(request, client_id, redirect_uri, scopes, state)
        return response
    
    # ถ้าผู้ใช้ปฏิเสธ consent ให้ redirect กลับไปยัง client พร้อม error
    error_url = f"{redirect_uri}?error=access_denied&state={state}"
    return RedirectResponse(url=error_url, status_code=303)

@oauth2_router.post("/token")
async def oauth2_token(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
):
    """
    Token endpoint ที่รองรับทั้ง authorization_code และ refresh_token
    """
    client_id = credentials.username
    client_secret = credentials.password
    result = await Oauth2Controller.token(request, client_id, client_secret, grant_type, code, redirect_uri, refresh_token, code_verifier)
    return result

@oauth2_router.post("/revoke")
async def oauth2_revoke(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None)
):
    """
    Token revocation endpoint ตาม RFC 7009
    """
    client_id = credentials.username
    client_secret = credentials.password
    result = await Oauth2Controller.revoke_token(request, client_id, client_secret, token, token_type_hint)
    return result

@oauth2_router.post("/clients", response_model=OAuthClientSummary)
async def client(request: Request, client: CreateClientSchema, current_user: dict = Depends(get_current_user)):
    # Admin-only client registration unless you implement RFC 7591 Dynamic Client Registration
    await PermissionService.require_officer(current_user)
    result = await Oauth2Controller.create_client(client, request)
    return result


@oauth2_router.put("/clients/{client_id}", response_model=OAuthClientSummary)
async def update_client(
    client_id: str,
    payload: UpdateClientSchema,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.update_client(client_id, payload, current_user)


@oauth2_router.get("/clients/allowed-domains", response_model=List[str])
async def get_allowed_registration_domains():
    """
    Public endpoint: Get allowed domains for registration returnUrl validation
    Returns list of unique hostnames extracted from OAuth clients' login_url
    No authentication required - used by public registration page
    """
    from urllib.parse import urlparse
    
    clients = await Oauth2Controller.list_clients()
    domains = set()
    
    # Extract unique domains from login_url
    for client in clients:
        login_url = client.get("login_url") if isinstance(client, dict) else getattr(client, "login_url", None)
        if login_url:
            try:
                parsed = urlparse(str(login_url))
                if parsed.hostname:
                    domains.add(parsed.hostname)
            except Exception:
                continue
    
    # Add localhost and 127.0.0.1 for development
    domains.add('localhost')
    domains.add('127.0.0.1')
    
    return list(domains)


@oauth2_router.get("/clients", response_model=List[OAuthClientSummary])
async def list_oauth_clients(current_user: dict = Depends(get_current_user)):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.list_clients()


@oauth2_router.put("/clients/{client_id}/allowed-user-types", response_model=OAuthClientSummary)
async def update_client_allowed_user_types(
    client_id: str,
    payload: UpdateClientUserTypesRequest,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.update_client_user_types(client_id, payload.allowed_user_types)


@oauth2_router.get("/clients/{client_id}/allowed-user-types/default", response_model=ClientUserTypesDefault)
async def get_client_allowed_user_types_default(
    client_id: str,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.get_client_user_types_default(client_id)


@oauth2_router.put("/clients/{client_id}/allowed-user-types/default", response_model=ClientUserTypesDefault)
async def update_client_allowed_user_types_default(
    client_id: str,
    payload: UpdateClientUserTypesDefaultRequest,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.set_client_user_types_default(client_id, payload.allowed_user_types, current_user)


@oauth2_router.post("/clients/{client_id}/allowed-user-types/reset-default", response_model=OAuthClientSummary)
async def reset_client_allowed_user_types_default(
    client_id: str,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.reset_client_user_types_to_default(client_id, current_user)


@oauth2_router.get("/clients/{client_id}/blocks", response_model=List[ClientBlockEntry])
async def list_client_blocks(
    client_id: str,
    search: str | None = Query(default=None, description="คำค้นหา citizen id หรือชื่อ"),
    user_type: UserType | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    filters = ClientBlockQueryParams(search=search, user_type=user_type)
    return await Oauth2Controller.list_client_blocks(client_id, filters)


@oauth2_router.put("/clients/{client_id}/allowlist-mode", response_model=OAuthClientSummary)
async def update_client_allowlist_mode(
    client_id: str,
    payload: UpdateClientAllowlistModeRequest,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.update_client_allowlist_mode(client_id, payload.allowlist_enabled, current_user)


@oauth2_router.get("/clients/{client_id}/allows", response_model=List[ClientAllowEntry])
async def list_client_allows(
    client_id: str,
    search: str | None = Query(default=None, description="คำค้นหา citizen id หรือชื่อ"),
    user_type: UserType | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    filters = ClientAllowQueryParams(search=search, user_type=user_type)
    return await Oauth2Controller.list_client_allows(client_id, filters)


@oauth2_router.post("/clients/{client_id}/allows", response_model=ClientAllowEntry, status_code=status.HTTP_201_CREATED)
async def create_client_allow(
    client_id: str,
    payload: CreateClientAllowRequest,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.create_client_allow(client_id, payload, current_user)


@oauth2_router.delete("/clients/{client_id}/allows/{allow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_allow(
    client_id: str,
    allow_id: str,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    await Oauth2Controller.delete_client_allow(client_id, allow_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@oauth2_router.post("/clients/{client_id}/blocks", response_model=ClientBlockEntry, status_code=status.HTTP_201_CREATED)
async def create_client_block(
    client_id: str,
    payload: CreateClientBlockRequest,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.create_client_block(client_id, payload, current_user)


@oauth2_router.delete("/clients/{client_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_block(
    client_id: str,
    block_id: str,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    await Oauth2Controller.delete_client_block(client_id, block_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@oauth2_router.get("/clients/block-candidates", response_model=PaginatedBlockCandidates)
async def search_block_candidates(
    user_type: UserType = Query(..., description="ประเภทผู้ใช้"),
    query: str = Query(..., description="คำค้นหา"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    return await Oauth2Controller.search_block_candidates(user_type, query, limit, offset)

@oauth2_router.post("/logout")
async def oauth2_logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_security)):
    """
    Revoke refresh tokens for either mock or OAuth-based sessions.
    """
    token = credentials.credentials if credentials else None
    if token:
        try:
            mock_user = MockAuthService.decode_access_token(token)
            MockAuthService.logout(mock_user["user"]["id"])
            return {"success": True, "message": "logged_out"}
        except HTTPException:
            pass
    current_user = await get_current_user(credentials)
    await Oauth2Controller.logout(
        current_user["user_id"], current_user["client_id"], current_user.get("user_type")
    )
    # Invalidate session + auth_me cache so other pods see the logout immediately
    from app.api.middleware.middleware import invalidate_session_cache
    from app.cache.redis_client import cache_delete_pattern
    await invalidate_session_cache(
        current_user["user_id"], current_user["client_id"], current_user.get("user_type", "")
    )
    await cache_delete_pattern("auth_me:*")
    return {"success": True, "message": "logged_out"}

@oauth2_router.post("/token/refresh", response_model=TokenResponse)
async def oauth2_token_refresh(payload: RefreshRequest):
    """
    API-first refresh endpoint for mobile/SPA. Allows public clients (no secret).
    """
    result = await Oauth2Controller.refresh_token_api(payload)
    return result


@oauth2_router.post("/refresh")
async def mock_refresh(payload: Dict[str, str]):
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refresh_token_required")
    return MockAuthService.refresh(refresh_token)

from app.api.middleware.middleware import require_scopes

@oauth2_router.get("/userinfo")
async def get_userinfo(current_user: dict = Depends(require_scopes({"openid"}))):
    """
    OpenID Connect UserInfo endpoint
    ใช้ access token ผ่าน middleware
    """
    user_id = current_user["user_id"]
    client_id = current_user.get("client_id")
    user_type = current_user.get("user_type")
    user_consents = await OAuthConsentRepository.get_user_consented_scopes(
        user_id, client_id, user_type
    )
    # ตรวจสอบว่ามี scope ที่จำเป็นสำหรับ userinfo
    if not user_consents or "openid" not in user_consents:
        raise UnauthorizedException(detail="Insufficient scope. 'openid' scope required.")
    
    user_info = await UserController.get_user_info(user_id, user_consents, user_type)
    
    # เพิ่ม client_id ใน response
    user_info["client_id"] = client_id
    
    return user_info

@oauth2_router.get("/me")
async def get_me(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_security),
):
    token = credentials.credentials if credentials else None
    if token:
        try:
            mock_user = MockAuthService.decode_access_token(token)
            profile = mock_user["user"]
            profile["client_id"] = "mock-client"
            profile["scopes"] = mock_user.get("scopes", [])
            profile["is_admin"] = "admin" in profile["scopes"]
            profile["token_scopes"] = profile["scopes"]
            profile["permission_scope"] = None
            profile.setdefault("village_code", None)
            profile.setdefault("village_name", None)
            client_context = {
                "client_id": "mock-client",
                "client_name": "Mock Client",
                "description": None,
                "allowed_user_types": None,
                "scopes": profile["scopes"],
                "grant_types": [],
                "public_client": True,
                "user_type_allowed": True,
                "is_active": True,
                "is_current_client": True,
            }
            profile["client_context"] = client_context
            profile.setdefault("prefix", None)
            profile.setdefault("hospital", None)
            profile.setdefault("service_unit", None)
            return {"success": True, "data": _replace_none_with_empty(profile)}
        except HTTPException:
            pass
    current_user = await get_current_user(credentials)

    # Fast path: return cached /me response for same token
    me_cache_key = f"auth_me:{_token_hash(token)}"
    cached_me = await cache_get(me_cache_key)
    if cached_me is not None:
        return cached_me

    user_id = current_user["user_id"]
    client_id = current_user.get("client_id")
    user_type = current_user.get("user_type")
    user_info = await UserController.get_user_info(user_id, None, user_type)
    user_info["client_id"] = client_id
    token_scopes = current_user.get("scopes") or []
    user_info["scopes"] = token_scopes
    user_info["token_scopes"] = token_scopes
    user_info["is_admin"] = await PermissionService.is_officer(current_user)

    permission_scope = await AuthMeService.build_permission_scope(user_id, user_type, user_info)
    user_info["permission_scope"] = permission_scope
    village_code = user_info.get("village_code")
    if not village_code and permission_scope:
        fallback_code = permission_scope.get("codes", {}).get("village_code")
        if fallback_code:
            village_code = fallback_code
    user_info["village_code"] = village_code

    village_name = user_info.get("village_name")
    if not village_name and permission_scope:
        fallback_name = permission_scope.get("codes", {}).get("village_name_th")
        if fallback_name:
            village_name = fallback_name
    user_info["village_name"] = village_name

    # back-fill area / health-area / region from permission_scope when not yet set
    if permission_scope:
        scope_codes = permission_scope.get("codes") or {}

        if not user_info.get("area_code") and scope_codes.get("village_code"):
            user_info["area_code"] = scope_codes["village_code"]

        if not user_info.get("health_area_code") and scope_codes.get("health_area_id"):
            user_info["health_area_code"] = scope_codes["health_area_id"]

        if not user_info.get("region_code") and scope_codes.get("region_code"):
            user_info["region_code"] = scope_codes["region_code"]

    client_context = None
    client = await ClientRepository.find_client_by_client_id(client_id)
    if client:
        allowed_user_types = AuthMeService.normalize_allowed_user_types(client.allowed_user_types)
        if allowed_user_types is None:
            dynamic_allowed = get_allowed_user_types(client)
            allowed_user_types = sorted(dynamic_allowed) if dynamic_allowed else None
        client_context = {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "description": client.client_description,
            "allowed_user_types": allowed_user_types,
            "scopes": client.scopes,
            "grant_types": client.grant_types,
            "public_client": client.public_client,
            "user_type_allowed": is_user_type_allowed(client, user_type),
            "is_active": client.is_active,
            "is_current_client": client_id == current_user.get("client_id"),
        }
    user_info["client_context"] = client_context

    me_result = {"success": True, "data": _replace_none_with_empty(user_info)}
    await cache_set(me_cache_key, me_result, AUTH_ME_CACHE_TTL)
    return me_result


@oauth2_router.get("/permission-pages")
async def get_permission_pages(
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Fetch page permissions for the currently authenticated user."""
    user_id = current_user["user_id"]
    user_type = current_user.get("user_type")
    user_info = await UserController.get_user_info(user_id, None, user_type)
    permission_scope = await AuthMeService.build_permission_scope(user_id, user_type, user_info)
    manageable_levels = permission_scope.get("manageable_levels") if permission_scope else []
    permission_pages = await PermissionPageService.list_accessible_pages(manageable_levels)
    return {"items": permission_pages}

# OpenID Connect Discovery endpoint
@oauth2_router.get("/.well-known/openid-configuration")
async def openid_configuration(request: Request):
    """
    OpenID Connect Discovery endpoint
    ตามมาตรฐาน RFC 8414
    """
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "issuer": f"{base_url}{settings.API_V1_PREFIX}/auth",
        "authorization_endpoint": f"{base_url}{settings.API_V1_PREFIX}/auth/authorize",
        "token_endpoint": f"{base_url}{settings.API_V1_PREFIX}/auth/token",
        "revocation_endpoint": f"{base_url}{settings.API_V1_PREFIX}/auth/revoke",
        "userinfo_endpoint": f"{base_url}{settings.API_V1_PREFIX}/auth/userinfo",
        "jwks_uri": f"{base_url}{settings.API_V1_PREFIX}/auth/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [settings.JWT_ALGORITHM],
        "scopes_supported": ["openid", "profile", "email", "address", "phone", "birth_date", "gender"],
        # Only client_secret_basic is currently supported at the token endpoint
        "token_endpoint_auth_methods_supported": ["client_secret_basic"],
        # PKCE support (RFC 7636)
        "code_challenge_methods_supported": ["S256", "plain"],
        "claims_supported": ["sub", "name", "email", "client_id"],
        # Supported OAuth2 grant types exposed at the token endpoint
        "grant_types_supported": ["authorization_code", "refresh_token"]
    }

# JWKS (JSON Web Key Set) endpoint
@oauth2_router.get("/.well-known/jwks.json")
async def jwks():
    """
    JSON Web Key Set endpoint
    ตามมาตรฐาน RFC 7517
    """
    try:
        # Multi-key: from settings.JWT_PUBLIC_KEYS if provided; else fallback to single key
        keys = []
        if getattr(settings, "JWT_PUBLIC_KEYS", None):
            try:
                mapping = json.loads(settings.JWT_PUBLIC_KEYS)
                for kid, path in mapping.items():
                    with open(path, 'r') as f:
                        public_key_pem = f.read()
                    public_key = serialization.load_pem_public_key(public_key_pem.encode())
                    public_numbers = public_key.public_numbers()
                    n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
                    e_bytes = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')
                    n_b64 = base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('=')
                    e_b64 = base64.urlsafe_b64encode(e_bytes).decode('utf-8').rstrip('=')
                    keys.append({
                        "kty": "RSA",
                        "kid": kid,
                        "use": "sig",
                        "alg": settings.JWT_ALGORITHM,
                        "n": n_b64,
                        "e": e_b64,
                    })
            except Exception:
                keys = []
        if not keys:
            with open(settings.JWT_PUBLIC_KEY_PATH, 'r') as f:
                public_key_pem = f.read()
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            public_numbers = public_key.public_numbers()
            n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
            e_bytes = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')
            n_b64 = base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('=')
            e_b64 = base64.urlsafe_b64encode(e_bytes).decode('utf-8').rstrip('=')
            keys.append({
                "kty": "RSA",
                "kid": getattr(settings, "JWT_ACTIVE_KID", "key-1"),
                "use": "sig",
                "alg": settings.JWT_ALGORITHM,
                "n": n_b64,
                "e": e_b64,
            })
        return {"keys": keys}
    except Exception as e:
        raise UnauthorizedException(detail="JWKS not available")

@oauth2_router.get("/client-scopes/{client_id}")
async def get_client_scopes(client_id: str):
    """
    ดึง scopes ที่ client ต้องการ
    """
    from app.repositories.client_repository import ClientRepository
    
    try:
        client = await ClientRepository.find_client_by_client_id(client_id)
        if not client:
            raise UnauthorizedException(detail="Client not found")
        
        # สร้าง scope descriptions
        scope_descriptions = {
            "openid": "Access to your basic profile information",
            "profile": "Access to your name and profile details",
            "email": "Access to your email address",
            "address": "Access to your address information",
            "phone": "Access to your phone number",
            "birth_date": "Access to your birth date",
            "gender": "Access to your gender information"
        }
        
        scopes_with_descriptions = []
        for scope in client.scopes:
            scopes_with_descriptions.append({
                "scope": scope,
                "description": scope_descriptions.get(scope, f"Access to {scope} information")
            })
        
        return {
            "client_id": client_id,
            "client_name": client.client_name,
            "scopes": scopes_with_descriptions
        }
    except Exception as e:
        raise UnauthorizedException(detail="Failed to get client scopes")


@oauth2_router.post("/consent/accept")
async def consent_accept(request: ConsentAcceptRequest, current_user: dict = Depends(get_current_user)):
    """
    Allow API-based consent acceptance for mobile/SPA flows without web UI.
    """
    if current_user.get("user_type") != request.user_type:
        raise UnauthorizedException(detail="user_type mismatch")
    from app.api.v1.controllers.oauth2 import Oauth2Controller
    # Store consent then return current scopes
    await OAuthConsentRepository.create_consent(
        current_user["user_id"], request.client_id, request.scopes, request.user_type
    )
    scopes = await OAuthConsentRepository.get_user_consented_scopes(
        current_user["user_id"], request.client_id, request.user_type
    )
    return {"client_id": request.client_id, "scopes": scopes}

@oauth2_router.get("/consent/details")
async def consent_details(client_id: str, scope: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """
    Return consent context for API clients to render a consent screen without a web UI.
    - Query params: client_id (required), scope (space-delimited, optional)
    - Returns: client info, requested scopes with descriptions, already-consented scopes
    """
    from app.repositories.client_repository import ClientRepository
    client = await ClientRepository.find_client_by_client_id(client_id)
    if not client:
        raise UnauthorizedException(detail="Client not found")

    requested_scopes = scope.split(" ") if scope else (client.scopes or [])
    scope_descriptions = {
        "openid": "Access to your basic profile information",
        "profile": "Access to your name and profile details",
        "email": "Access to your email address",
        "address": "Access to your address information",
        "phone": "Access to your phone number",
        "birth_date": "Access to your birth date",
        "gender": "Access to your gender information",
    }
    scopes_with_descriptions = [
        {"scope": s, "description": scope_descriptions.get(s, f"Access to {s} information")} for s in requested_scopes
    ]
    already_consented = await OAuthConsentRepository.get_user_consented_scopes(
        current_user["user_id"], client_id, current_user.get("user_type")
    ) or []
    return {
        "client_id": client_id,
        "client_name": client.client_name,
        "requested_scopes": scopes_with_descriptions,
        "already_consented": already_consented,
        "can_proceed": all(s in already_consented for s in requested_scopes) if requested_scopes else True,
    }


