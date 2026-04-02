from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProvinceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    province_code: str = Field(..., max_length=255)
    province_name_th: str = Field(..., max_length=255)
    province_name_en: Optional[str] = Field(None, max_length=255)
    area_code: Optional[str] = Field(None, max_length=255)
    region_code: Optional[str] = Field(None, max_length=255)
    health_area_code: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    quota: Optional[int] = Field(0, ge=0)


class ProvinceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    province_name_th: Optional[str] = Field(None, max_length=255)
    province_name_en: Optional[str] = Field(None, max_length=255)
    area_code: Optional[str] = Field(None, max_length=255)
    region_code: Optional[str] = Field(None, max_length=255)
    health_area_code: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    quota: Optional[int] = Field(None, ge=0)


class ProvinceQuotaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quota: int = Field(..., ge=0)


class DistrictCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    district_code: str = Field(..., max_length=255)
    district_name_th: str = Field(..., max_length=255)
    district_name_en: Optional[str] = Field(None, max_length=255)
    province_code: str = Field(..., max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DistrictUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    district_name_th: Optional[str] = Field(None, max_length=255)
    district_name_en: Optional[str] = Field(None, max_length=255)
    province_code: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SubdistrictCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subdistrict_code: str = Field(..., max_length=255)
    subdistrict_name_th: str = Field(..., max_length=255)
    subdistrict_name_en: Optional[str] = Field(None, max_length=255)
    district_code: str = Field(..., max_length=255)
    postal_code: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SubdistrictUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subdistrict_name_th: Optional[str] = Field(None, max_length=255)
    subdistrict_name_en: Optional[str] = Field(None, max_length=255)
    district_code: Optional[str] = Field(None, max_length=255)
    postal_code: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VillageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    village_code: str = Field(..., max_length=255)
    village_code_8digit: Optional[str] = Field(None, max_length=255)
    village_no: Optional[int] = Field(None, ge=0)
    village_name_th: str = Field(..., max_length=255)
    village_name_en: Optional[str] = Field(None, max_length=255)
    metro_status: Optional[str] = Field(None, max_length=50)
    subdistrict_code: str = Field(..., max_length=255)
    government_id: Optional[str] = Field(None, max_length=50)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    health_service_code: Optional[str] = Field(None, max_length=255)
    external_url: Optional[str] = Field(None, max_length=255)


class VillageUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    village_code_8digit: Optional[str] = Field(None, max_length=255)
    village_no: Optional[int] = Field(None, ge=0)
    village_name_th: Optional[str] = Field(None, max_length=255)
    village_name_en: Optional[str] = Field(None, max_length=255)
    metro_status: Optional[str] = Field(None, max_length=50)
    subdistrict_code: Optional[str] = Field(None, max_length=255)
    government_id: Optional[str] = Field(None, max_length=50)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    health_service_code: Optional[str] = Field(None, max_length=255)
    external_url: Optional[str] = Field(None, max_length=255)


class HealthServiceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    health_service_code: str = Field(..., max_length=255)
    health_service_name_th: str = Field(..., max_length=255)
    health_service_name_en: Optional[str] = Field(None, max_length=255)
    legacy_5digit_code: Optional[str] = Field(None, max_length=255)
    legacy_9digit_code: Optional[str] = Field(None, max_length=255)
    health_service_type_id: str = Field(..., max_length=255)
    province_code: Optional[str] = Field(None, max_length=255)
    district_code: Optional[str] = Field(None, max_length=255)
    subdistrict_code: Optional[str] = Field(None, max_length=255)
    village_no: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HealthServiceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    health_service_name_th: Optional[str] = Field(None, max_length=255)
    health_service_name_en: Optional[str] = Field(None, max_length=255)
    legacy_5digit_code: Optional[str] = Field(None, max_length=255)
    legacy_9digit_code: Optional[str] = Field(None, max_length=255)
    health_service_type_id: Optional[str] = Field(None, max_length=255)
    province_code: Optional[str] = Field(None, max_length=255)
    district_code: Optional[str] = Field(None, max_length=255)
    subdistrict_code: Optional[str] = Field(None, max_length=255)
    village_no: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MunicipalityCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    municipality_name_th: str = Field(..., max_length=255)
    municipality_name_en: Optional[str] = Field(None, max_length=255)
    municipality_type_code: str = Field(..., max_length=255)
    province_code: str = Field(..., max_length=255)
    district_code: str = Field(..., max_length=255)
    subdistrict_code: str = Field(..., max_length=255)


class MunicipalityUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    municipality_name_th: Optional[str] = Field(None, max_length=255)
    municipality_name_en: Optional[str] = Field(None, max_length=255)
    municipality_type_code: Optional[str] = Field(None, max_length=255)
    province_code: Optional[str] = Field(None, max_length=255)
    district_code: Optional[str] = Field(None, max_length=255)
    subdistrict_code: Optional[str] = Field(None, max_length=255)


class HealthAreaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., max_length=255)
    health_area_name_th: str = Field(..., max_length=255)
    health_area_name_en: Optional[str] = Field(None, max_length=255)


class HealthAreaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    health_area_name_th: Optional[str] = Field(None, max_length=255)
    health_area_name_en: Optional[str] = Field(None, max_length=255)
