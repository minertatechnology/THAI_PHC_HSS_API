from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, EmailStr, Field


class GenHCreateSchema(BaseModel):
    """Schema for registering a new Gen H user."""

    gen_h_code: Optional[str] = Field(None, max_length=20, description="รหัสบัตรสมาชิก Gen H")
    citizen_id: Optional[str] = Field(None, min_length=13, max_length=13, pattern=r"^\d{13}$")
    password: str = Field(..., min_length=6, max_length=128)
    prefix: Optional[str] = Field(None, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    gender: Optional[str] = Field(None, max_length=10)
    birthday: Optional[date] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    line_id: Optional[str] = Field(None, max_length=100)
    school: Optional[str] = Field(None, max_length=255)
    organization: Optional[str] = Field(None, max_length=255)
    registration_reason: Optional[str] = None
    province_code: Optional[str] = Field(None, max_length=10)
    province_name: Optional[str] = Field(None, max_length=255)
    district_code: Optional[str] = Field(None, max_length=10)
    district_name: Optional[str] = Field(None, max_length=255)
    subdistrict_code: Optional[str] = Field(None, max_length=10)
    subdistrict_name: Optional[str] = Field(None, max_length=255)
    profile_image_url: Optional[str] = Field(
        None, max_length=1024,
        validation_alias=AliasChoices("profile_image_url", "profile_image"),
    )
    photo_1inch: Optional[str] = Field(None, max_length=1024)
    member_card_url: Optional[str] = Field(None, max_length=1024)
    attachments: Optional[List[Any]] = None


class GenHUpdateSchema(BaseModel):
    """Schema for updating a Gen H user."""

    prefix: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[str] = Field(None, max_length=10)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    line_id: Optional[str] = Field(None, max_length=100)
    school: Optional[str] = Field(None, max_length=255)
    province_code: Optional[str] = Field(None, max_length=10)
    province_name: Optional[str] = Field(None, max_length=255)
    district_code: Optional[str] = Field(None, max_length=10)
    district_name: Optional[str] = Field(None, max_length=255)
    subdistrict_code: Optional[str] = Field(None, max_length=10)
    subdistrict_name: Optional[str] = Field(None, max_length=255)
    profile_image_url: Optional[str] = Field(None, max_length=1024)
    member_card_url: Optional[str] = Field(None, max_length=1024)
    points: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class GenHQueryParams(BaseModel):
    """Query parameters for listing Gen H users."""

    search: Optional[str] = None
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    gender: Optional[str] = None
    school: Optional[str] = None
    is_active: Optional[bool] = None
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class GenHResponseSchema(BaseModel):
    """Response schema for Gen H user."""

    id: UUID
    gen_h_code: str
    source_type: str = "self_register"
    citizen_id: Optional[str] = None
    prefix: Optional[str] = None
    first_name: str
    last_name: str
    gender: Optional[str] = None
    birthday: Optional[date] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    registration_reason: Optional[str] = None
    province_code: Optional[str] = None
    province_name: Optional[str] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    subdistrict_code: Optional[str] = None
    subdistrict_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    photo_1inch: Optional[str] = None
    member_card_url: Optional[str] = None
    attachments: Optional[List[Any]] = None
    points: int = 0
    is_active: bool = True
    people_user_id: Optional[UUID] = None
    yuwa_osm_user_id: Optional[UUID] = None
    transferred_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GenHTransferToPeopleRequest(BaseModel):
    """Request to transfer a Gen H user to people_user."""

    citizen_id: str = Field(..., min_length=13, max_length=13, pattern=r"^\d{13}$", description="เลขบัตรประชาชน 13 หลัก")
    birthday: Optional[str] = Field(None, description="วันเกิด (YYYY-MM-DD)")
    organization: Optional[str] = Field(None, max_length=255)
    registration_reason: Optional[str] = None


class GenHUpgradeToYuwaOSMRequest(BaseModel):
    """Self-service request: gen_h user กรอก citizen_id เพื่อ upgrade เป็น yuwa_osm.

    หลัง upgrade สำเร็จ:
    - gen_h record จะถูก deactivate
    - yuwa_osm record ใหม่ จะ active ทันที (source_type='migration', approval_status=APPROVED)
    - login ได้ทั้ง gen_h_code และ citizen_id ที่ yuwa_osm
    """

    citizen_id: str = Field(
        ..., min_length=13, max_length=13, pattern=r"^\d{13}$",
        description="เลขบัตรประชาชน 13 หลัก (required)",
    )
    birthday: Optional[str] = Field(None, description="วันเกิด (YYYY-MM-DD)")
    phone_number: Optional[str] = Field(None, max_length=20, description="เบอร์โทร (ถ้าต่างจาก gen_h)")
    organization: Optional[str] = Field(None, max_length=255)
    registration_reason: Optional[str] = Field(None, description="เหตุผลการสมัคร")


class GenHSummaryResponse(BaseModel):
    """Summary statistics for Gen H dashboard."""

    total: int = 0
    active: int = 0
    male: int = 0
    female: int = 0
    lgbtq_plus: int = 0
    transferred_to_yuwa: int = 0
    by_province: list[dict] = []


class GenHBatchIdsSchema(BaseModel):
    """Schema for batch fetching Gen H users by IDs."""

    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Gen H user IDs (UUID or gen_h_code) to fetch",
    )
