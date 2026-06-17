from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserSyncCreateSchema(BaseModel):
    """Schema สำหรับ POST /user/sync/users — สร้าง user ใหม่จาก mobile sync."""

    id: str = Field(..., description="UUID จาก Keycloak (sub)")
    email: Optional[str] = None
    username: Optional[str] = Field(None, description="citizen_id (แปลงไป citizen_id)")
    thai_id: Optional[str] = Field(None, description="citizen_id (ซ้ำกับ username)")
    full_name: Optional[str] = Field(None, description="prefix + first_name + last_name")
    phone_number: Optional[str] = None
    prefix: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    province_id: Optional[str] = Field(None, description="แปลงไป province_code")
    province_name: Optional[str] = None
    district_id: Optional[str] = Field(None, description="แปลงไป district_code")
    district_name: Optional[str] = None
    sub_district_id: Optional[str] = Field(None, description="แปลงไป subdistrict_code")
    sub_district_name: Optional[str] = None
    village_code: Optional[str] = None
    village_name: Optional[str] = None
    profile_image_url: Optional[str] = Field(None, description="แปลงไป profile_image")
    line_id: Optional[str] = None
    is_active: Optional[bool] = True
    is_approved: Optional[bool] = None
    is_superuser: Optional[bool] = None
    reason: Optional[str] = Field(None, description="registration_reason")


class UserSyncUpdateSchema(BaseModel):
    """Schema สำหรับ PUT /user/sync/users/{uuid} — อัปเดต user จาก mobile sync."""

    email: Optional[str] = None
    username: Optional[str] = Field(None, description="citizen_id (แปลงไป citizen_id)")
    thai_id: Optional[str] = Field(None, description="citizen_id (ซ้ำกับ username)")
    full_name: Optional[str] = Field(None, description="prefix + first_name + last_name")
    phone_number: Optional[str] = None
    prefix: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    province_id: Optional[str] = Field(None, description="แปลงไป province_code")
    province_name: Optional[str] = None
    district_id: Optional[str] = Field(None, description="แปลงไป district_code")
    district_name: Optional[str] = None
    sub_district_id: Optional[str] = Field(None, description="แปลงไป subdistrict_code")
    sub_district_name: Optional[str] = None
    village_code: Optional[str] = None
    village_name: Optional[str] = None
    profile_image_url: Optional[str] = Field(None, description="แปลงไป profile_image")
    line_id: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    is_superuser: Optional[bool] = None
    reason: Optional[str] = Field(None, description="registration_reason")


class UserSyncResponseSchema(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
