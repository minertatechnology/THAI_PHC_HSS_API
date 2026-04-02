from pydantic import BaseModel
from typing import Optional
from app.models.enum_models import AdministrativeLevelEnum

class OsmQueryParams(BaseModel):
    # OsmFilterParams fields
    citizen_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: Optional[str] = None
    health_service_code: Optional[str] = None

    # GeographyFilterParams fields
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    subdistrict_code: Optional[str] = None

    # PaginationParams fields
    page: Optional[int] = 1
    limit: Optional[int] = 10

    # Sorting
    order_by: Optional[str] = "created_at"
    sort_dir: Optional[str] = "desc"



class ReportOsmGenderQueryParams(BaseModel):
      # GeographyFilterParams fields
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    subdistrict_code: Optional[str] = None

    # PaginationParams fields
    page: Optional[int] = 1
    limit: Optional[int] = 10


class ReportOsmFamilyQueryParams(BaseModel):
    status: Optional[str] = "osm"
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    subdistrict_code: Optional[str] = None

    # PaginationParams fields
    page: Optional[int] = 1
    limit: Optional[int] = 10


class ReportOsmPresidentQueryParams(BaseModel):
    position_level: Optional[AdministrativeLevelEnum] = None
    area_code: Optional[str] = None
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    subdistrict_code: Optional[str] = None
    page: int = 1
    limit: int = 10