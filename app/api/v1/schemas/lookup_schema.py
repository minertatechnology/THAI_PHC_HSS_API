from typing import Optional

from pydantic import BaseModel, Field


class GeographyLookupItemRequest(BaseModel):
    province: Optional[str] = Field(default=None, description="ชื่อจังหวัด")
    district: Optional[str] = Field(default=None, description="ชื่ออำเภอ")
    subdistrict: Optional[str] = Field(default=None, description="ชื่อตำบล")
    health_area: Optional[str] = Field(default=None, description="ชื่อ/รหัสเขตสุขภาพ")
    health_service_name_th: Optional[str] = Field(default=None, description="ชื่อหน่วยบริการสุขภาพ (ภาษาไทย)")


class GeographyLookupItemResponse(BaseModel):
    province_id: Optional[str] = None
    province: Optional[str] = None
    district_id: Optional[str] = None
    district: Optional[str] = None
    subdistrict_id: Optional[str] = None
    subdistrict: Optional[str] = None
    health_area_id: Optional[str] = None
    health_area: Optional[str] = None
    health_services: Optional[list[dict]] = None


