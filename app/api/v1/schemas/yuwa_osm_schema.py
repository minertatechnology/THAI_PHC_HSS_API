from __future__ import annotations

from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, EmailStr, Field, model_validator

from app.models.enum_models import ApprovalStatus


class YuwaOSMCreateSchema(BaseModel):
    """Front-end payload for registering a new Yuwa OSM account."""

    prefix: Optional[str] = Field(default=None, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    gender: Optional[str] = Field(default=None, max_length=10)
    phone: str = Field(
        ...,
        min_length=4,
        max_length=20,
        validation_alias=AliasChoices("phone", "phone_number"),
        description="Unique phone number for login",
    )
    email: Optional[EmailStr] = Field(default=None, validation_alias=AliasChoices("email", "email_address"))
    line_id: Optional[str] = Field(default=None, max_length=100)
    school: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("school", "school_or_org"))
    organization: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("organization", "org"))
    province: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("province", "province_name"))
    province_code: Optional[str] = Field(default=None, max_length=10)
    district: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("district", "district_name"))
    district_code: Optional[str] = Field(default=None, max_length=10)
    sub_district: Optional[str] = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("sub_district", "subdistrict", "subdistrict_name"),
    )
    subdistrict_code: Optional[str] = Field(default=None, max_length=10)
    profile_image: Optional[str] = Field(default=None, max_length=1024)
    reason: Optional[str] = Field(default=None, max_length=1024)
    photo_1inch: Optional[str] = Field(default=None, max_length=1024)
    attachments: Optional[List[Any]] = Field(default=None)
    citizen_id: str = Field(..., min_length=13, max_length=13)
    password: Optional[str] = Field(
        default=None,
        min_length=6,
        max_length=128,
        description="Initial password that will be hashed; generated automatically if omitted",
    )
    birthday: Optional[date] = None

    model_config = {"extra": "forbid", "populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _map_school_or_org(cls, values):
        if not isinstance(values, dict):
            return values
        legacy = values.get("school_or_org")
        if legacy:
            values.setdefault("school", legacy)
            values.setdefault("organization", legacy)
        return values


class YuwaOSMUpdateSchema(BaseModel):
    prefix: Optional[str] = Field(default=None, max_length=50)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    gender: Optional[str] = Field(default=None, max_length=10)
    phone: Optional[str] = Field(default=None, min_length=4, max_length=20)
    email: Optional[EmailStr] = Field(default=None, validation_alias=AliasChoices("email", "email_address"))
    line_id: Optional[str] = Field(default=None, max_length=100)
    school: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("school", "school_or_org"))
    organization: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("organization", "org"))
    province: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("province", "province_name"))
    province_code: Optional[str] = Field(default=None, max_length=10)
    district: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("district", "district_name"))
    district_code: Optional[str] = Field(default=None, max_length=10)
    sub_district: Optional[str] = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("sub_district", "subdistrict", "subdistrict_name"),
    )
    subdistrict_code: Optional[str] = Field(default=None, max_length=10)
    profile_image: Optional[str] = Field(default=None, max_length=1024)
    reason: Optional[str] = Field(default=None, max_length=1024)
    photo_1inch: Optional[str] = Field(default=None, max_length=1024)
    attachments: Optional[List[Any]] = Field(default=None)
    citizen_id: Optional[str] = Field(default=None, min_length=13, max_length=13)
    birthday: Optional[date] = None
    is_active: Optional[bool] = None

    model_config = {"extra": "forbid", "populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _map_school_or_org(cls, values):
        if not isinstance(values, dict):
            return values
        legacy = values.get("school_or_org")
        if legacy:
            values.setdefault("school", legacy)
            values.setdefault("organization", legacy)
        return values


class YuwaOSMQueryParams(BaseModel):
    search: Optional[str] = Field(default=None, description="Keyword search across name, citizen ID, phone")
    approval_status: Optional[ApprovalStatus | str] = Field(default=None)
    is_active: Optional[str | bool] = Field(
        default=None,
        description="Supports active/inactive booleans or approval keywords: approved, pending, rejected",
    )
    province_code: Optional[str] = Field(default=None, max_length=10)
    district_code: Optional[str] = Field(default=None, max_length=10)
    subdistrict_code: Optional[str] = Field(default=None, max_length=10)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    order_by: Optional[str] = Field(default="created_at", description="Field used for ordering")
    sort_dir: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")

    model_config = {"extra": "forbid"}


class YuwaOSMSummaryQueryParams(BaseModel):
    province: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Alias for province_code or province_name",
    )
    province_code: Optional[str] = Field(default=None, max_length=10)
    province_name: Optional[str] = Field(default=None, max_length=255)
    birthday: Optional[date] = Field(default=None, description="Exact birthday filter (YYYY-MM-DD)")
    school: Optional[str] = Field(default=None, max_length=255, validation_alias=AliasChoices("school", "school_or_org"))
    organization: Optional[str] = Field(default=None, max_length=255)
    approval_status: Optional[ApprovalStatus | str] = Field(default=None)
    min_age: Optional[int] = Field(default=None, ge=0, description="Minimum age (years)")
    max_age: Optional[int] = Field(default=None, ge=0, description="Maximum age (years)")

    model_config = {"extra": "forbid", "populate_by_name": True}


class YuwaOSMDecisionPayload(BaseModel):
    note: Optional[str] = Field(default=None, max_length=1024)


class YuwaOSMRejectPayload(YuwaOSMDecisionPayload):
    reason: str = Field(..., min_length=1, max_length=1024)


class YuwaOSMResponseSchema(BaseModel):
    id: UUID
    citizen_id: Optional[str] = None
    yuwa_osm_code: Optional[str] = None
    phone_number: Optional[str] = None
    first_name: str
    last_name: str
    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    line_id: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    province_code: Optional[str] = None
    province_name: Optional[str] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    subdistrict_code: Optional[str] = None
    subdistrict_name: Optional[str] = None
    profile_image: Optional[str] = None
    registration_reason: Optional[str] = None
    photo_1inch: Optional[str] = None
    attachments: Optional[List[Any]] = None
    birthday: Optional[date] = None
    is_active: bool
    approval_status: ApprovalStatus
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[UUID] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    people_id: Optional[UUID] = None
    source_people_id: Optional[UUID] = None
    transferred_by: Optional[UUID] = None
    transferred_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class YuwaOSMBatchIdsSchema(BaseModel):
    """Schema for batch fetching Yuwa OSM users by IDs."""

    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Yuwa OSM user IDs (UUID or yuwa_osm_code) to fetch",
    )


class YuwaOSMTransferRequest(BaseModel):
    people_id: UUID
    note: Optional[str] = Field(default=None, max_length=1024)
