from __future__ import annotations

import json
import hmac
import secrets
from urllib.parse import urlencode, quote, urlparse

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.middleware.middleware import get_current_user
from app.cache.redis_client import cache_get, cache_set, cache_delete
from app.configs.config import settings
from app.models.thaid_models import (
    FormatResponseModel,
    MobileAuthorizeResponse,
    MobileTokenRequest,
    ThaiIDAuthCode,
    ThaiIDLoginResponse,
)
from app.repositories.client_repository import ClientRepository
from app.services.audit_service import AuditService
from app.services.thaid_service import ThaiDAuthError, process_thaid_auth_code
from app.utils.thaid_utils import (
    extract_request_metadata,
    format_response,
    mask_secret,
)

router = APIRouter(prefix="/thaid", tags=["thai digital id"], redirect_slashes=False)

# ---------------------------------------------------------------------------
# Top-level /callback router (mounted at app root, NOT under /api/v1)
# DOPA redirects users to  {THAID_REDIRECT_URI}  e.g.  https://domain/callback
# ---------------------------------------------------------------------------
callback_router = APIRouter(tags=["thai digital id callback"])

# ---------------------------------------------------------------------------
# Allowed redirect origins — prevents open-redirect attacks.
# Build the set once from CORS_ALLOWED_ORIGINS + the configured THAID_REDIRECT_URI origin.
# ---------------------------------------------------------------------------
_ALLOWED_REDIRECT_ORIGINS: set[str] | None = None


def _get_allowed_redirect_origins() -> set[str]:
    """Lazily compute allowed redirect origins from CORS config."""
    global _ALLOWED_REDIRECT_ORIGINS
    if _ALLOWED_REDIRECT_ORIGINS is not None:
        return _ALLOWED_REDIRECT_ORIGINS

    origins: set[str] = set()

    # From CORS config
    cors_raw = getattr(settings, "CORS_ALLOWED_ORIGINS", None) or ""
    for origin in cors_raw.split(","):
        origin = origin.strip()
        if origin:
            origins.add(origin.rstrip("/").lower())

    # The THAID_REDIRECT_URI itself (in case it's on a different domain)
    thaid_redir = settings.THAID_REDIRECT_URI
    if thaid_redir:
        parsed = urlparse(thaid_redir)
        if parsed.scheme and parsed.netloc:
            origins.add(f"{parsed.scheme}://{parsed.netloc}".lower())

    # Always allow localhost for development
    origins.add("http://localhost:3000")
    origins.add("http://127.0.0.1:3000")
    origins.add("http://localhost:8000")

    _ALLOWED_REDIRECT_ORIGINS = origins
    return origins


def _is_redirect_uri_allowed(redirect_uri: str) -> bool:
    """Return True if the redirect_uri origin is in the allowed set."""
    if not redirect_uri:
        return True  # No redirect = safe, falls back to "/"
    parsed = urlparse(redirect_uri)
    if not parsed.scheme or not parsed.netloc:
        # Relative path — allow
        return redirect_uri.startswith("/")
    origin = f"{parsed.scheme}://{parsed.netloc}".lower()
    return origin in _get_allowed_redirect_origins()


def _build_register_uri_from_fallback(fallback_uri: str) -> str:
    parsed = urlparse(fallback_uri)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/register"
    return "/register"


# ---------------------------------------------------------------------------
# HMAC state signing — prevents state tampering
# ---------------------------------------------------------------------------
def _get_state_key() -> bytes:
    """Derive a signing key from JWT_SECRET_KEY."""
    secret = getattr(settings, "JWT_SECRET_KEY", "") or ""
    return secret.encode("utf-8")


def _sign_state(state_json: str) -> str:
    """Return HMAC-SHA256 hex signature for the state JSON."""
    return hmac.new(_get_state_key(), state_json.encode("utf-8"), "sha256").hexdigest()


def _verify_state_signature(state_json: str, signature: str) -> bool:
    """Constant-time comparison of HMAC signatures."""
    expected = _sign_state(state_json)
    return hmac.compare_digest(expected, signature)


_VALID_USER_TYPES = {"osm", "officer", "yuwa_osm", "people"}

# ---------------------------------------------------------------------------
# Mobile flow: Redis key helpers
# TTL = 300 seconds (5 minutes) — enough time for user to authenticate
# ---------------------------------------------------------------------------
_MOBILE_STATE_TTL = 300
_MOBILE_RESULT_TTL = 120  # result available for 2 minutes after callback


def _mobile_state_key(state_token: str) -> str:
    return f"thaid:mobile:state:{state_token}"


def _mobile_result_key(state_token: str) -> str:
    return f"thaid:mobile:result:{state_token}"


# ===========================================================================
# Existing web endpoints (unchanged)
# ===========================================================================


@router.get("/authorize", summary="Start ThaiD login — redirect user to DOPA")
async def thaid_authorize(
    request: Request,
    client_id: str = Query(..., description="OAuth2 client_id of the calling application"),
    user_type: str = Query("osm", description="Requested user type: osm, officer, yuwa_osm, people"),
    redirect_uri: str | None = Query(None, description="Frontend URI to redirect to after callback"),
) -> RedirectResponse:
    """Build the DOPA authorization URL and redirect the user there.

    Security checks performed:
    1. client_id must exist and be active in the database.
    2. user_type must be one of the 4 valid types.
    3. redirect_uri must be in the allowed origins whitelist.
    4. State parameter is HMAC-signed to prevent tampering.
    """
    request_meta = extract_request_metadata(request)

    # --- Validate user_type ---
    if user_type not in _VALID_USER_TYPES:
        await AuditService.log_action(
            action_type="LOGIN",
            target_type="THAID_AUTHORIZE",
            description=f"ThaiD authorize rejected: invalid user_type '{user_type}'",
            success=False,
            error_message="invalid_user_type",
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        return RedirectResponse(
            url=f"{redirect_uri or '/'}?error=invalid_user_type",
            status_code=302,
        )

    # --- Validate redirect_uri against whitelist ---
    if redirect_uri and not _is_redirect_uri_allowed(redirect_uri):
        await AuditService.log_action(
            action_type="LOGIN",
            target_type="THAID_AUTHORIZE",
            description=f"ThaiD authorize rejected: redirect_uri not allowed",
            success=False,
            error_message="redirect_uri_not_allowed",
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        return RedirectResponse(url="/?error=redirect_uri_not_allowed", status_code=302)

    # --- Validate client_id exists and is active in DB ---
    client = await ClientRepository.find_client_by_client_id(client_id)
    if not client or not getattr(client, "is_active", True):
        await AuditService.log_action(
            action_type="LOGIN",
            target_type="THAID_AUTHORIZE",
            description=f"ThaiD authorize rejected: invalid client_id",
            success=False,
            error_message="invalid_client",
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        return RedirectResponse(
            url=f"{redirect_uri or '/'}?error=invalid_client",
            status_code=302,
        )

    authorize_uri = settings.THAID_AUTHORIZE_URI
    if not authorize_uri:
        return RedirectResponse(
            url=f"{redirect_uri or '/'}?error=thaid_not_configured",
            status_code=302,
        )

    thaid_client_id = settings.THAID_CLIENT_ID
    thaid_redirect_uri = settings.THAID_REDIRECT_URI

    if not thaid_client_id or not thaid_redirect_uri:
        return RedirectResponse(
            url=f"{redirect_uri or '/'}?error=thaid_not_configured",
            status_code=302,
        )

    # Encode context into opaque state + HMAC signature
    state_payload = {
        "client_id": client_id,
        "user_type": user_type,
        "nonce": secrets.token_urlsafe(16),
    }
    if redirect_uri:
        state_payload["redirect_uri"] = redirect_uri

    state_json = json.dumps(state_payload, separators=(",", ":"), sort_keys=True)
    state_sig = _sign_state(state_json)

    # Combine state + signature so callback can verify integrity
    signed_state = json.dumps({"d": state_json, "s": state_sig}, separators=(",", ":"))

    params = {
        "response_type": "code",
        "client_id": thaid_client_id,
        "redirect_uri": thaid_redirect_uri,
        "scope": "pid openid given_name family_name",
        # "scope": "pid given_name family_name gender address",
        "state": signed_state,
    }

    dopa_url = f"{authorize_uri}?{urlencode(params, quote_via=quote)}"
    return RedirectResponse(url=dopa_url, status_code=302)


@callback_router.get("/callback", summary="ThaiD DOPA callback — exchange code for tokens", response_model=None)
async def thaid_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from DOPA"),
    state: str | None = Query(None, description="State parameter passed through DOPA"),
) -> RedirectResponse | HTMLResponse:
    """Handle the redirect from DOPA after user authenticates with ThaiD.

    Supports both web flow (redirect with tokens) and mobile flow (store result in Redis).

    Security checks performed:
    1. State HMAC signature is verified (prevents tampering).
    2. client_id from state is re-validated against the database.
    3. redirect_uri from state is re-validated against the whitelist.
    4. All errors redirect safely (never to unvalidated URLs).
    """
    request_meta = extract_request_metadata(request)

    # --- Parse & verify state ---
    client_id = ""
    user_type = "osm"
    redirect_uri = ""
    mobile_state_token = ""

    if state:
        try:
            signed_data = json.loads(state)
            state_json = signed_data.get("d", "")
            state_sig = signed_data.get("s", "")

            # Verify HMAC signature — reject tampered state
            if not state_json or not state_sig or not _verify_state_signature(state_json, state_sig):
                await AuditService.log_action(
                    action_type="LOGIN",
                    target_type="THAID_CALLBACK",
                    description="ThaiD callback rejected: tampered state signature",
                    success=False,
                    error_message="state_tampered",
                    ip=request_meta["ip"],
                    user_agent=request_meta["user_agent"],
                )
                return RedirectResponse(url="/?error=state_tampered", status_code=302)

            state_data = json.loads(state_json)
            client_id = state_data.get("client_id", "")
            user_type = state_data.get("user_type", "osm")
            redirect_uri = state_data.get("redirect_uri", "")
            mobile_state_token = state_data.get("mobile_state", "")
        except (json.JSONDecodeError, TypeError):
            return RedirectResponse(url="/?error=invalid_state", status_code=302)

    # --- Mobile flow: validate state token exists in Redis ---
    is_mobile_flow = bool(mobile_state_token)
    if is_mobile_flow:
        stored = await cache_get(_mobile_state_key(mobile_state_token))
        if not stored:
            return RedirectResponse(url="/?error=mobile_state_expired", status_code=302)
        # Clean up the state key — it's single-use
        await cache_delete(_mobile_state_key(mobile_state_token))

    # Validate redirect_uri from state against whitelist (re-check)
    if redirect_uri and not _is_redirect_uri_allowed(redirect_uri):
        redirect_uri = ""

    # fallback redirect — always safe
    fallback_uri = redirect_uri or "/"

    if not client_id:
        if is_mobile_flow:
            await cache_set(
                _mobile_result_key(mobile_state_token),
                {"status": "error", "error": "missing_client_id"},
                _MOBILE_RESULT_TTL,
            )
            return _mobile_success_page()
        return RedirectResponse(
            url=f"{fallback_uri}?error=missing_client_id",
            status_code=302,
        )

    try:
        auth_payload = ThaiIDAuthCode(
            auth_code=code,
            client_id=client_id,
            user_type=user_type,
        )
        result = await process_thaid_auth_code(auth_payload)
    except ThaiDAuthError as exc:
        await AuditService.log_action(
            action_type="LOGIN",
            target_type="THAID_CALLBACK",
            description="ThaiD callback authentication",
            success=False,
            error_message=exc.detail,
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        if is_mobile_flow:
            await cache_set(
                _mobile_result_key(mobile_state_token),
                {"status": "error", "error": exc.detail},
                _MOBILE_RESULT_TTL,
            )
            return _mobile_success_page()
        return RedirectResponse(
            url=f"{fallback_uri}?error={exc.detail}",
            status_code=302,
        )
    except Exception as exc:
        await AuditService.log_action(
            action_type="LOGIN",
            target_type="THAID_CALLBACK",
            description="ThaiD callback authentication",
            success=False,
            error_message=str(exc),
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        if is_mobile_flow:
            await cache_set(
                _mobile_result_key(mobile_state_token),
                {"status": "error", "error": "internal_error"},
                _MOBILE_RESULT_TTL,
            )
            return _mobile_success_page()
        return RedirectResponse(
            url=f"{fallback_uri}?error=internal_error",
            status_code=302,
        )

    # --- Registration required ---
    if result.get("register_required"):
        if is_mobile_flow:
            prefill = result.get("prefill") or {}
            await cache_set(
                _mobile_result_key(mobile_state_token),
                {
                    "status": "register_required",
                    "user_type": result.get("user_type") or user_type,
                    "citizen_id": prefill.get("citizen_id") or result.get("citizen_id") or "",
                    "first_name": prefill.get("first_name") or "",
                    "last_name": prefill.get("last_name") or "",
                },
                _MOBILE_RESULT_TTL,
            )
            return _mobile_success_page()

        prefill = result.get("prefill") or {}
        register_uri = _build_register_uri_from_fallback(fallback_uri)
        params = urlencode(
            {
                "source": "thaid",
                "user_type": result.get("user_type") or user_type,
                "citizen_id": prefill.get("citizen_id") or result.get("citizen_id") or "",
                "first_name": prefill.get("first_name") or "",
                "last_name": prefill.get("last_name") or "",
            }
        )
        return RedirectResponse(url=f"{register_uri}?{params}", status_code=302)

    # --- Login success ---
    login_response = ThaiIDLoginResponse(**result)

    await AuditService.log_action(
        user_id=login_response.user_id,
        action_type="LOGIN",
        target_type="THAID_CALLBACK",
        description="ThaiD callback authentication",
        success=True,
        new_data={
            "client_id": client_id,
            "user_type": login_response.user_type,
            "source": "mobile" if is_mobile_flow else "web",
        },
        ip=request_meta["ip"],
        user_agent=request_meta["user_agent"],
    )

    # --- Mobile flow: store tokens in Redis, show close-browser page ---
    if is_mobile_flow:
        await cache_set(
            _mobile_result_key(mobile_state_token),
            {
                "status": "success",
                "access_token": login_response.access_token,
                "refresh_token": login_response.refresh_token or "",
                "token_type": login_response.token_type,
                "expires_in": login_response.expires_in,
                "user_type": login_response.user_type,
                "user_id": login_response.user_id,
            },
            _MOBILE_RESULT_TTL,
        )
        return _mobile_success_page()

    # --- Web flow: redirect back to frontend with tokens (unchanged) ---
    sep = "&" if "?" in fallback_uri else "?"
    params = urlencode({
        "access_token": login_response.access_token,
        "refresh_token": login_response.refresh_token or "",
        "token_type": login_response.token_type,
        "expires_in": str(login_response.expires_in),
        "user_type": login_response.user_type,
        "user_id": login_response.user_id,
    })
    return RedirectResponse(
        url=f"{fallback_uri}{sep}{params}",
        status_code=302,
    )


def _mobile_success_page() -> HTMLResponse:
    """Return a simple HTML page telling the user to go back to the app."""
    html = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ThaiD - กลับไปที่แอป</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #bae6fd 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 48px 32px;
            max-width: 400px;
            width: 100%;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.08);
        }
        .icon {
            width: 64px; height: 64px;
            background: #dcfce7;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 24px;
        }
        .icon svg { width: 32px; height: 32px; color: #16a34a; }
        h1 { font-size: 20px; color: #0f172a; margin-bottom: 12px; }
        p { font-size: 15px; color: #64748b; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">
            <svg fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
        </div>
        <h1>ยืนยันตัวตนสำเร็จ</h1>
        <p>กรุณากลับไปที่แอปเพื่อดำเนินการต่อ</p>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


# ===========================================================================
# Mobile-specific endpoints
# ===========================================================================


@router.get(
    "/mobile/authorize",
    response_model=FormatResponseModel,
    summary="Start ThaiD login for mobile — returns auth URL as JSON",
)
async def thaid_mobile_authorize(
    request: Request,
    client_id: str = Query(..., description="OAuth2 client_id of the calling application"),
    user_type: str = Query("osm", description="Requested user type: osm, officer, yuwa_osm, people"),
) -> FormatResponseModel:
    """Mobile version of /thaid/authorize.

    Instead of returning a 302 redirect, returns a JSON response with the
    DOPA authorization URL so the mobile app can open it in a system browser
    (Chrome Custom Tabs / SFSafariViewController).

    The response includes a `state` token that the mobile app must send back
    via POST /thaid/mobile/token to retrieve the authentication result.
    """
    request_meta = extract_request_metadata(request)

    # --- Validate user_type ---
    if user_type not in _VALID_USER_TYPES:
        return format_response("4010", {"error": "invalid_user_type"})

    # --- Validate client_id ---
    client = await ClientRepository.find_client_by_client_id(client_id)
    if not client or not getattr(client, "is_active", True):
        return format_response("4010", {"error": "invalid_client"})

    authorize_uri = settings.THAID_AUTHORIZE_URI
    thaid_client_id = settings.THAID_CLIENT_ID
    thaid_redirect_uri = settings.THAID_REDIRECT_URI

    if not authorize_uri or not thaid_client_id or not thaid_redirect_uri:
        return format_response("5001", {"error": "thaid_not_configured"})

    # Generate a unique state token for this mobile session
    mobile_state_token = secrets.token_urlsafe(32)

    # Store mobile session in Redis
    await cache_set(
        _mobile_state_key(mobile_state_token),
        {
            "client_id": client_id,
            "user_type": user_type,
            "ip": request_meta["ip"],
        },
        _MOBILE_STATE_TTL,
    )

    # Build DOPA state with mobile_state marker (same HMAC signing as web flow)
    state_payload = {
        "client_id": client_id,
        "mobile_state": mobile_state_token,
        "nonce": secrets.token_urlsafe(16),
        "user_type": user_type,
    }

    state_json = json.dumps(state_payload, separators=(",", ":"), sort_keys=True)
    state_sig = _sign_state(state_json)
    signed_state = json.dumps({"d": state_json, "s": state_sig}, separators=(",", ":"))

    params = {
        "response_type": "code",
        "client_id": thaid_client_id,
        "redirect_uri": thaid_redirect_uri,
        "scope": "pid openid given_name family_name",
        "state": signed_state,
    }

    dopa_url = f"{authorize_uri}?{urlencode(params, quote_via=quote)}"

    await AuditService.log_action(
        action_type="LOGIN",
        target_type="THAID_MOBILE_AUTHORIZE",
        description="ThaiD mobile authorize started",
        success=True,
        new_data={"client_id": client_id, "user_type": user_type},
        ip=request_meta["ip"],
        user_agent=request_meta["user_agent"],
    )

    return format_response(
        "0000",
        MobileAuthorizeResponse(
            auth_url=dopa_url,
            state=mobile_state_token,
            expires_in=_MOBILE_STATE_TTL,
        ).model_dump(),
    )


@router.post(
    "/mobile/token",
    response_model=FormatResponseModel,
    summary="Exchange mobile state for tokens — poll after ThaiD authentication",
)
async def thaid_mobile_token(
    request: Request,
    body: MobileTokenRequest,
) -> FormatResponseModel:
    """Mobile app calls this after user authenticates via ThaiD in the browser.

    The mobile app should poll this endpoint (e.g. every 2-3 seconds) after
    opening the DOPA auth URL. Possible responses:

    - status=pending  → user hasn't completed authentication yet, keep polling
    - status=success  → tokens are included in the response
    - status=error    → authentication failed, error code included
    - status=register_required → user needs to register first
    - state expired   → the state token has expired (> 5 minutes)
    """
    request_meta = extract_request_metadata(request)
    state_token = body.state

    if not state_token:
        return format_response("4010", {"error": "missing_state"})

    # Check if result is ready
    result = await cache_get(_mobile_result_key(state_token))

    if result:
        # Result found — delete it (single-use) and return
        await cache_delete(_mobile_result_key(state_token))

        status = result.get("status", "error")

        if status == "success":
            await AuditService.log_action(
                user_id=result.get("user_id"),
                action_type="LOGIN",
                target_type="THAID_MOBILE_TOKEN",
                description="ThaiD mobile token exchange",
                success=True,
                new_data={"user_type": result.get("user_type")},
                ip=request_meta["ip"],
                user_agent=request_meta["user_agent"],
            )
            return format_response("0000", result)

        if status == "register_required":
            return format_response("0000", result)

        # Error
        return format_response("4010", result)

    # No result yet — check if the state is still valid (pending)
    state_data = await cache_get(_mobile_state_key(state_token))
    if state_data:
        return format_response("0000", {"status": "pending"})

    # State not found in either key — expired or invalid
    return format_response("4010", {"status": "expired", "error": "mobile_state_expired"})


# ===========================================================================
# Existing direct API endpoints (unchanged)
# ===========================================================================


@router.post("/auth", response_model=FormatResponseModel)
async def thaid_auth(
    request: Request,
    auth_data: ThaiIDAuthCode,
) -> FormatResponseModel:
    request_meta = extract_request_metadata(request)

    try:
        result = await process_thaid_auth_code(auth_data)
    except ThaiDAuthError as exc:
        await AuditService.log_action(
            action_type="LOGIN",
            target_type="THAID",
            description="ThaiD authentication",
            success=False,
            error_message=exc.detail,
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        return format_response(exc.response_code, {"error": exc.detail})
    except Exception as exc:  # pragma: no cover - defensive logging
        await AuditService.log_action(
            action_type="LOGIN",
            target_type="THAID",
            description="ThaiD authentication",
            success=False,
            error_message=str(exc),
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        return format_response("5000", {"error": f"Internal server error: {str(exc)}"})

    if result.get("register_required"):
        return format_response(
            "0000",
            {
                "is_new_user": True,
                "register_required": True,
                "user_type": result.get("user_type") or auth_data.user_type,
                "citizen_id": result.get("citizen_id") or "",
                "prefill": result.get("prefill") or {},
            },
        )

    login_response = ThaiIDLoginResponse(**result)

    await AuditService.log_action(
        user_id=login_response.user_id,
        action_type="LOGIN",
        target_type="THAID",
        description="ThaiD authentication",
        success=True,
        new_data={
            "client_id": auth_data.client_id,
            "user_type": login_response.user_type,
            "thaid_token": mask_secret(login_response.thaid_token),
        },
        ip=request_meta["ip"],
        user_agent=request_meta["user_agent"],
    )

    return format_response("0000", login_response.model_dump())


@router.post("/logout", response_model=FormatResponseModel)
async def thaid_logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> FormatResponseModel:
    request_meta = extract_request_metadata(request)
    user_id = current_user.get("user_id") if isinstance(current_user, dict) else None
    try:
        await AuditService.log_action(
            user_id=user_id,
            action_type="LOGOUT",
            target_type="THAID",
            description="ThaiD logout",
            success=True,
            new_data={"message": "ThaiD logout logged"},
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        return format_response("0000", {"message": "ThaiD logout logged"})
    except Exception as exc:  # pragma: no cover - defensive logging
        await AuditService.log_action(
            user_id=user_id,
            action_type="LOGOUT",
            target_type="THAID",
            description="ThaiD logout",
            success=False,
            error_message=str(exc),
            ip=request_meta["ip"],
            user_agent=request_meta["user_agent"],
        )
        return format_response("5000", {"error": f"Logout failed: {str(exc)}"})
