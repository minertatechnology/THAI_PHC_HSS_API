from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from pydantic import BaseModel, Field, validator


class PeopleCreateSchema(BaseModel):
    citizen_id: str = Field(..., min_length=13, max_length=13, description="เลขบัตรประชาชน")
    password: str = Field(..., min_length=8, description="รหัสผ่านสำหรับเข้าสู่ระบบ")
    prefix: Optional[str] = None
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    profile_image: Optional[str] = None
    registration_reason: Optional[str] = None
    photo_1inch: Optional[str] = None
    attachments: Optional[List[Any]] = None
    province_code: Optional[str] = None
    province_name: Optional[str] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    subdistrict_code: Optional[str] = None
    subdistrict_name: Optional[str] = None
    birthday: Optional[date] = None

    @validator("citizen_id")
    def validate_citizen_id(cls, value: str) -> str:
        if not value or len(value) != 13 or not value.isdigit():
            raise ValueError("เลขบัตรประชาชนต้องเป็นตัวเลข 13 หลัก")
        return value


class PeopleUpdateSchema(BaseModel):
    prefix: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    profile_image: Optional[str] = None
    registration_reason: Optional[str] = None
    photo_1inch: Optional[str] = None
    attachments: Optional[List[Any]] = None
    province_code: Optional[str] = None
    province_name: Optional[str] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    subdistrict_code: Optional[str] = None
    subdistrict_name: Optional[str] = None
    birthday: Optional[date] = None
    is_active: Optional[bool] = None


class PeopleResponseSchema(BaseModel):
    id: str
    citizen_id: str
    yuwa_osm_code: Optional[str] = None
    prefix: Optional[str] = None
    first_name: str
    last_name: str
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    profile_image: Optional[str] = None
    registration_reason: Optional[str] = None
    photo_1inch: Optional[str] = None
    attachments: Optional[List[Any]] = None
    province_code: Optional[str] = None
    province_name: Optional[str] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    subdistrict_code: Optional[str] = None
    subdistrict_name: Optional[str] = None
    birthday: Optional[date] = None
    is_active: bool
    is_first_login: bool
    is_transferred: Optional[bool] = None
    transferred_at: Optional[str] = None
    transferred_by: Optional[str] = None
    transferred_by_name: Optional[str] = None
    yuwa_osm_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PeopleBatchIdsSchema(BaseModel):
    """Schema for batch fetching People users by IDs."""

    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="People user IDs (UUID or citizen_id) to fetch",
    )
