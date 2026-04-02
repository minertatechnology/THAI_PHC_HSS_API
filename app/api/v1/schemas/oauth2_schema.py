from datetime import datetime
from typing import Any, List, Optional, Literal

from pydantic import BaseModel, Field


UserType = Literal["osm", "officer", "yuwa_osm", "people", "gen_h"]


class SetPasswordRequest(BaseModel):
    password: str
    user_type: UserType

class SetPasswordResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class ChangePasswordResponse(BaseModel):
    success: bool = True
    message: str = "password_changed"


class PreLoginRequest(BaseModel):
    citizen_id: str
    user_type: Optional[UserType] = None
class PreLoginResponse(BaseModel):
    exist: bool
    needs_password_setup: bool
    token: Optional[str] = None
    user_type: Optional[UserType] = None

class LoginRequest(BaseModel):
    username: str
    password: str
    client_id: str

class LoginResponse(BaseModel):
    user_id: str
    name: str
    user_type: UserType

class CreateClientSchema(BaseModel):
    client_name: str
    client_description: Optional[str]
    redirect_uri: str
    login_url: str
    consent_url: str
    scopes: List[str] = Field(default=["openid", "profile"])
    grant_types: List[str] = Field(default=["authorization_code", "refresh_token", "direct_login"])
    public_client: bool = Field(default=True, description="For mobile/SPA: no client_secret at runtime")


class UpdateClientSchema(BaseModel):
    client_name: str
    client_description: Optional[str] = None
    redirect_uri: str
    login_url: str
    consent_url: str
    scopes: List[str]
    grant_types: List[str]
    public_client: bool


# ===== Mobile/API-first additions =====
class TokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None
    profile: Optional[dict[str, Any]] = None
    needs_password_change: bool = False
    requires_citizen_id: Optional[bool] = None
    yuwa_osm_user_id: Optional[str] = None


class DirectLoginRequest(BaseModel):
    username: str
    password: str
    client_id: str
    user_type: Optional[UserType] = None
    scope: Optional[List[str]] = None


class RefreshRequest(BaseModel):
    client_id: str
    refresh_token: str
    client_secret: Optional[str] = None  # for confidential clients; omit for public


class ConsentAcceptRequest(BaseModel):
    client_id: str
    scopes: List[str]
    user_type: UserType


class OAuthClientSummary(BaseModel):
    id: str
    client_id: str
    client_name: str
    client_description: Optional[str] = None
    redirect_uri: str
    login_url: Optional[str] = None
    login_url_example: Optional[str] = None
    consent_url: Optional[str] = None
    consent_url_example: Optional[str] = None
    scopes: List[str]
    grant_types: List[str]
    public_client: bool
    allowed_user_types: Optional[List[UserType]] = None
    allowlist_enabled: bool = False
    is_active: bool


class UpdateClientUserTypesRequest(BaseModel):
    allowed_user_types: Optional[List[UserType]] = None


class ClientUserTypesDefault(BaseModel):
    client_id: str
    allowed_user_types: Optional[List[UserType]] = None
    updated_at: Optional[datetime] = None


class UpdateClientUserTypesDefaultRequest(BaseModel):
    allowed_user_types: Optional[List[UserType]] = None


class ClientBlockEntry(BaseModel):
    id: str
    client_id: str
    client_uuid: str
    user_id: str
    user_type: UserType
    citizen_id: Optional[str] = None
    full_name: Optional[str] = None
    note: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime


class UpdateClientAllowlistModeRequest(BaseModel):
    allowlist_enabled: bool = Field(default=False, description="If true: only allowed users can access this client")


class ClientAllowEntry(BaseModel):
    id: str
    client_id: str
    client_uuid: str
    user_id: str
    user_type: UserType
    citizen_id: Optional[str] = None
    full_name: Optional[str] = None
    note: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime


class CreateClientAllowRequest(BaseModel):
    user_id: str
    user_type: UserType
    note: Optional[str] = None


class ClientAllowQueryParams(BaseModel):
    search: Optional[str] = None
    user_type: Optional[UserType] = None


class CreateClientBlockRequest(BaseModel):
    user_id: str
    user_type: UserType
    note: Optional[str] = None


class ClientBlockQueryParams(BaseModel):
    search: Optional[str] = None
    user_type: Optional[UserType] = None


class ClientBlockCandidate(BaseModel):
    user_id: str
    user_type: UserType
    full_name: str = ""
    citizen_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    is_transferred: Optional[bool] = None
    transferred_at: Optional[datetime] = None
    transferred_by: Optional[str] = None
    yuwa_osm_id: Optional[str] = None
    yuwa_osm_code: Optional[str] = None
    province_name: Optional[str] = None
    district_name: Optional[str] = None
    subdistrict_name: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    subdistrict_code: Optional[str] = None
    village_code: Optional[str] = None
    region_code: Optional[str] = None
    health_area_code: Optional[str] = None


class PaginatedBlockCandidates(BaseModel):
    items: List[ClientBlockCandidate] = []
    total: int = 0
    limit: int = 20
    offset: int = 0
