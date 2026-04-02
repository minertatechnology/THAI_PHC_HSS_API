from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ThaiIDAddress(BaseModel):
    formatted: str


class ThaiIDTokenResponse(BaseModel):
    expires_in: int
    access_token: str
    refresh_token: str
    token_type: str
    scope: str
    pid: str
    address: ThaiIDAddress | None = None
    address_other: ThaiIDAddress | None = None
    given_name: str
    family_name: str
    gender: str
    titleTh: str | None = Field(default=None)


class ThaiIDLoginResponse(BaseModel):
    """ThaiD login response aligned with OAuth2 direct login tokens."""

    is_new_user: bool = False
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int
    scope: str | None = None
    user_id: str
    user_type: str
    citizen_id: str
    thaid_token: str
    id_token: str | None = None


class ThaiIDAuthCode(BaseModel):
    auth_code: str
    client_id: str = Field(..., description="OAuth2 client issuing the ThaiD login")
    user_type: Literal["osm", "officer", "yuwa_osm", "people"] = Field(
        default="osm", description="Requested user type mapping for downstream tokens"
    )
    scope: list[str] | None = Field(
        default=None, description="Requested scopes; defaults to client registered scopes"
    )
    client_secret: str | None = Field(
        default=None,
        description="Client secret for confidential clients; omit for public clients",
    )


class ThaiDCallbackRequest(BaseModel):
    """Query parameters received from DOPA redirect at /callback."""

    code: str = Field(..., description="Authorization code from DOPA")
    state: str | None = Field(
        default=None,
        description="Opaque state passed through the DOPA redirect; contains client_id, user_type, and optional redirect_uri",
    )


class FormatResponseModel(BaseModel):
    res_code: str
    res_message: str
    res_data: Any


class MobileAuthorizeResponse(BaseModel):
    """Response from GET /thaid/mobile/authorize — gives the mobile app a URL to open."""

    auth_url: str = Field(..., description="DOPA authorization URL for the mobile app to open in a system browser")
    state: str = Field(..., description="Opaque state token — send back via POST /thaid/mobile/token")
    expires_in: int = Field(default=300, description="Seconds before this state expires")


class MobileTokenRequest(BaseModel):
    """Request body for POST /thaid/mobile/token — mobile app polls with the state."""

    state: str = Field(..., description="State token received from GET /thaid/mobile/authorize")


class UserRole(str, Enum):
    STAFF = "staff"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
