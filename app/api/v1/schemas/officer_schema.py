from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class OfficerCreateSchema(BaseModel):
    citizen_id: str
    prefix_id: str
    first_name: str
    last_name: str
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_image: Optional[str] = None
    position_id: str
    address_number: str
    password: str = Field(min_length=8)
    province_id: Optional[str] = None
    district_id: Optional[str] = None
    subdistrict_id: Optional[str] = None
    village_no: Optional[str] = None
    alley: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    municipality_id: Optional[str] = None
    health_area_id: Optional[str] = None
    health_service_id: Optional[str] = None
    area_type: Optional[str] = None
    area_code: Optional[str] = None

    @field_validator(
        "gender",
        "email",
        "phone",
        "profile_image",
        "province_id",
        "district_id",
        "subdistrict_id",
        "village_no",
        "alley",
        "street",
        "postal_code",
        "municipality_id",
        "health_area_id",
        "health_service_id",
        "area_type",
        "area_code",
        mode="before",
    )
    @classmethod
    def _blank_string_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("birth_date", mode="before")
    @classmethod
    def _blank_birth_date_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class OfficerUpdateSchema(BaseModel):
    prefix_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_image: Optional[str] = None
    position_id: Optional[str] = None
    address_number: Optional[str] = None
    province_id: Optional[str] = None
    district_id: Optional[str] = None
    subdistrict_id: Optional[str] = None
    village_no: Optional[str] = None
    alley: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    municipality_id: Optional[str] = None
    health_area_id: Optional[str] = None
    health_service_id: Optional[str] = None
    area_type: Optional[str] = None
    area_code: Optional[str] = None
    is_active: Optional[bool] = None
    approval_status: Optional[str] = None
    approval_by: Optional[str] = None
    approval_date: Optional[date] = None

    @field_validator(
        "prefix_id",
        "first_name",
        "last_name",
        "gender",
        "email",
        "phone",
        "profile_image",
        "position_id",
        "address_number",
        "province_id",
        "district_id",
        "subdistrict_id",
        "village_no",
        "alley",
        "street",
        "postal_code",
        "municipality_id",
        "health_area_id",
        "health_service_id",
        "area_type",
        "area_code",
        "approval_status",
        "approval_by",
        mode="before",
    )
    @classmethod
    def _blank_string_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("birth_date", "approval_date", mode="before")
    @classmethod
    def _blank_date_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = {"extra": "forbid"}


class OfficerTransferSchema(BaseModel):
    health_area_id: Optional[str] = None
    province_id: Optional[str] = None
    district_id: Optional[str] = None
    subdistrict_id: Optional[str] = None
    health_service_id: Optional[str] = None
    note: Optional[str] = None

    model_config = {"extra": "forbid"}


class OfficerQueryParams(BaseModel):
    search: Optional[str] = None
    area_code: Optional[str] = None
    health_service_id: Optional[str] = None
    position_id: Optional[str] = None
    province_id: Optional[str] = None
    district_id: Optional[str] = None
    subdistrict_id: Optional[str] = None
    is_active: Optional[bool] = None
    approval_status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    order_by: Optional[str] = "created_at"
    sort_dir: Optional[str] = "desc"


class OfficerBatchIdsSchema(BaseModel):
    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Officer IDs to fetch",
    )


class OfficerActiveStatusSchema(BaseModel):
    is_active: bool = Field(..., description="สถานะเปิดใช้งานของบัญชี")


class LookupItemSchema(BaseModel):
    id: Optional[str] = None
    code: Optional[str] = None
    label: Optional[str] = None
    name_th: Optional[str] = None
    name_en: Optional[str] = None
    scope_level: Optional[str] = None
    postal_code: Optional[str] = None
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    subdistrict_code: Optional[str] = None
    region_code: Optional[str] = None
    region_name_th: Optional[str] = None
    region_name_en: Optional[str] = None


class LookupResponseSchema(BaseModel):
    items: List[LookupItemSchema]


class OfficerRegistrationMetaSchema(BaseModel):
    prefixes: List[LookupItemSchema]
    genders: List[LookupItemSchema]
    positions: List[LookupItemSchema]
    provinces: List[LookupItemSchema]
    health_areas: List[LookupItemSchema]
    areas: List[LookupItemSchema]
    regions: List[LookupItemSchema]


class OfficerApprovalActionSchema(BaseModel):
    note: Optional[str] = Field(default=None, description="หมายเหตุเพิ่มเติมสำหรับการอนุมัติ/ปฏิเสธ")


class OfficerRegistrationResponseSchema(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None