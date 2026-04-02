from __future__ import annotations

from typing import List, Optional
from datetime import date

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class StandardGenderReportQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    village_code: Optional[str] = Field(
        default=None,
        alias="village",
        validation_alias=AliasChoices("village", "villageCode", "village_code"),
        serialization_alias="village",
    )
    year: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=20,
        ge=1,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class StandardGenderReportItem(BaseModel):
    province_code: str = Field(alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(
        default=None, alias="provinceName", serialization_alias="provinceName"
    )
    district_code: Optional[str] = Field(
        default=None, alias="districtCode", serialization_alias="districtCode"
    )
    district_name: Optional[str] = Field(
        default=None, alias="districtName", serialization_alias="districtName"
    )
    subdistrict_code: Optional[str] = Field(
        default=None, alias="subdistrictCode", serialization_alias="subdistrictCode"
    )
    subdistrict_name: Optional[str] = Field(
        default=None, alias="subdistrictName", serialization_alias="subdistrictName"
    )
    village_code: Optional[str] = Field(
        default=None, alias="villageCode", serialization_alias="villageCode"
    )
    village_no: Optional[str] = Field(
        default=None, alias="villageNo", serialization_alias="villageNo"
    )
    village_name: Optional[str] = Field(
        default=None, alias="villageName", serialization_alias="villageName"
    )
    total: int
    male: int
    female: int

    model_config = ConfigDict(populate_by_name=True)


class StandardGenderReportResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[StandardGenderReportItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(
        default=20, alias="pageSize", serialization_alias="pageSize"
    )

    model_config = ConfigDict(populate_by_name=True)


class StandardGenderSnapshotQuery(StandardGenderReportQuery):
    fiscal_year: Optional[int] = Field(
        default=None,
        alias="fiscalYear",
        validation_alias=AliasChoices("fiscalYear", "fiscal_year"),
        serialization_alias="fiscalYear",
    )


class StandardGenderSnapshotItem(StandardGenderReportItem):
    fiscal_year: int = Field(alias="fiscalYear", serialization_alias="fiscalYear")
    captured_at: str = Field(alias="capturedAt", serialization_alias="capturedAt")
    note: Optional[str] = None


class StandardGenderSnapshotResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    fiscal_year: Optional[int] = Field(default=None, alias="fiscalYear", serialization_alias="fiscalYear")
    items: List[StandardGenderSnapshotItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=20, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


class StandardGenderSnapshotCreateRequest(BaseModel):
    fiscal_year: Optional[int] = Field(
        default=None,
        alias="fiscalYear",
        validation_alias=AliasChoices("fiscalYear", "fiscal_year"),
        serialization_alias="fiscalYear",
    )
    note: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class SnapshotMutationResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    fiscal_year: Optional[int] = Field(default=None, alias="fiscalYear", serialization_alias="fiscalYear")
    records: int = 0

    model_config = ConfigDict(populate_by_name=True)


class FamilyAddressReportQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    village_code: Optional[str] = Field(
        default=None,
        alias="village",
        validation_alias=AliasChoices("village", "villageCode", "village_code"),
        serialization_alias="village",
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=20,
        ge=1,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class FamilyAddressReportItem(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_no: Optional[str] = Field(default=None, alias="villageNo", serialization_alias="villageNo")
    village_name: Optional[str] = Field(default=None, alias="villageName", serialization_alias="villageName")
    osm_code: Optional[str] = Field(default=None, alias="osmCode", serialization_alias="osmCode")
    citizen_id: Optional[str] = Field(default=None, alias="citizenId", serialization_alias="citizenId")
    prefix_name: Optional[str] = Field(default=None, alias="prefixName", serialization_alias="prefixName")
    first_name: Optional[str] = Field(default=None, alias="firstName", serialization_alias="firstName")
    last_name: Optional[str] = Field(default=None, alias="lastName", serialization_alias="lastName")
    full_name: Optional[str] = Field(default=None, alias="fullName", serialization_alias="fullName")
    gender: Optional[str] = None
    address: Optional[str] = None
    status_code: str = Field(alias="status", serialization_alias="status")
    status_label: str = Field(alias="statusLabel", serialization_alias="statusLabel")
    volunteer_id: Optional[str] = Field(default=None, alias="volunteerId", serialization_alias="volunteerId")
    volunteer_name: Optional[str] = Field(default=None, alias="volunteerName", serialization_alias="volunteerName")

    model_config = ConfigDict(populate_by_name=True)


class FamilyAddressReportResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[FamilyAddressReportItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=20, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Average age report
# ---------------------------------------------------------------------------


class AverageAgeReportQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=100,
        ge=1,
        le=500,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class AverageAgeReportItem(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    total: int
    average_age: float = Field(alias="averageAge", serialization_alias="averageAge")
    min_age: float = Field(alias="minAge", serialization_alias="minAge")
    max_age: float = Field(alias="maxAge", serialization_alias="maxAge")

    model_config = ConfigDict(populate_by_name=True)


class AverageAgeReportResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[AverageAgeReportItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=100, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# New volunteers by year report
# ---------------------------------------------------------------------------


class NewVolunteerByYearQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    village_code: Optional[str] = Field(
        default=None,
        alias="villageCode",
        validation_alias=AliasChoices("villageCode", "village", "village_code"),
        serialization_alias="villageCode",
    )
    year_from: Optional[int] = Field(default=None, alias="yearFrom", serialization_alias="yearFrom")
    year_to: Optional[int] = Field(default=None, alias="yearTo", serialization_alias="yearTo")
    tenure_bucket: Optional[str] = Field(
        default=None,
        alias="tenureBucket",
        validation_alias=AliasChoices("tenureBucket", "tenure_bucket", "bucket"),
        serialization_alias="tenureBucket",
        description="One of: <1, 1, 2, 3, 4, 5, 6+",
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class NewVolunteerByYearItem(BaseModel):
    id: str
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_no: Optional[str] = Field(default=None, alias="villageNo", serialization_alias="villageNo")
    village_name: Optional[str] = Field(default=None, alias="villageName", serialization_alias="villageName")
    citizen_id: Optional[str] = Field(default=None, alias="citizenId", serialization_alias="citizenId")
    osm_code: Optional[str] = Field(default=None, alias="osmCode", serialization_alias="osmCode")
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    gender: Optional[str] = None
    start_year: Optional[int] = Field(default=None, alias="startYear", serialization_alias="startYear")
    tenure_years: Optional[int] = Field(default=None, alias="tenureYears", serialization_alias="tenureYears")
    tenure_bucket: Optional[str] = Field(default=None, alias="tenureBucket", serialization_alias="tenureBucket")
    osm_year: Optional[int] = Field(default=None, alias="osmYear", serialization_alias="osmYear")
    created_at: Optional[str] = Field(default=None, alias="createdAt", serialization_alias="createdAt")
    approval_date: Optional[str] = Field(default=None, alias="approvalDate", serialization_alias="approvalDate")
    approval_status: Optional[str] = Field(default=None, alias="approvalStatus", serialization_alias="approvalStatus")
    volunteer_status: Optional[str] = Field(default=None, alias="volunteerStatus", serialization_alias="volunteerStatus")

    model_config = ConfigDict(populate_by_name=True)


class NewVolunteerByYearResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[NewVolunteerByYearItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Volunteer tenure (allAndDurationList)
# ---------------------------------------------------------------------------


class VolunteerTenureQuery(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="province", serialization_alias="province")
    district_code: Optional[str] = Field(default=None, alias="district", serialization_alias="district")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrict", serialization_alias="subdistrict")
    # NOTE: FastAPI's BaseModel-as-Depends only binds known field aliases.
    # To support multiple query parameter names, we define explicit fields and
    # coalesce them into `village_code`.
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_code_legacy: Optional[str] = Field(default=None, alias="village", serialization_alias="village")
    village_code_snake: Optional[str] = Field(default=None, alias="village_code", serialization_alias="village_code")
    osm_status: Optional[str] = Field(default=None, alias="osmStatus", serialization_alias="osmStatus")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    @model_validator(mode="after")
    def _coalesce_village_code(self):
        if self.village_code is not None:
            return self
        fallback = self.village_code_legacy or self.village_code_snake
        if fallback is None:
            return self
        return self.model_copy(update={"village_code": fallback})

    model_config = ConfigDict(populate_by_name=True)


class VolunteerTenureItem(BaseModel):
    id: str
    citizen_id: Optional[str] = Field(default=None, alias="citizenId", serialization_alias="citizenId")
    osm_code: Optional[str] = Field(default=None, alias="osmCode", serialization_alias="osmCode")
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    start_year: Optional[int] = Field(default=None, alias="startYear", serialization_alias="startYear")
    tenure_years: Optional[int] = Field(default=None, alias="tenureYears", serialization_alias="tenureYears")
    osm_year: Optional[int] = Field(default=None, alias="osmYear", serialization_alias="osmYear")
    approval_date: Optional[str] = Field(default=None, alias="approvalDate", serialization_alias="approvalDate")
    retirement_date: Optional[str] = Field(default=None, alias="retirementDate", serialization_alias="retirementDate")
    retirement_reason: Optional[str] = Field(default=None, alias="retirementReason", serialization_alias="retirementReason")
    osm_status: Optional[str] = Field(default=None, alias="osmStatus", serialization_alias="osmStatus")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_no: Optional[str] = Field(default=None, alias="villageNo", serialization_alias="villageNo")
    village_name: Optional[str] = Field(default=None, alias="villageName", serialization_alias="villageName")

    model_config = ConfigDict(populate_by_name=True)


class VolunteerTenureResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[VolunteerTenureItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Qualified for benefit (ค่าป่วยการ) report
# ---------------------------------------------------------------------------


class QualifiedBenefitQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    status: Optional[str] = Field(
        default="confirmed_with_allowance",
        description="ค่าจาก AllowanceConfirmationStatusEnum; ถ้าไม่ระบุใช้ confirmed_with_allowance",
    )
    showbbody_status: Optional[str] = Field(
        default=None,
        alias="showbbody",
        serialization_alias="showbbody",
        description="สถานะเงินเยียวยา/ค่าป่วยการจาก OsmShowbbodyEnum (1/2=ได้รับ,5=ไม่ได้รับ,6=รอ)",
    )
    year_from: Optional[int] = Field(default=None, alias="yearFrom", serialization_alias="yearFrom")
    year_to: Optional[int] = Field(default=None, alias="yearTo", serialization_alias="yearTo")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class QualifiedBenefitItem(BaseModel):
    id: str
    citizen_id: Optional[str] = Field(default=None, alias="citizenId", serialization_alias="citizenId")
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_no: Optional[str] = Field(default=None, alias="villageNo", serialization_alias="villageNo")
    village_name: Optional[str] = Field(default=None, alias="villageName", serialization_alias="villageName")
    allowance_status: Optional[str] = Field(default=None, alias="allowanceStatus", serialization_alias="allowanceStatus")
    allowance_year: Optional[int] = Field(default=None, alias="allowanceYear", serialization_alias="allowanceYear")
    allowance_months: Optional[int] = Field(default=None, alias="allowanceMonths", serialization_alias="allowanceMonths")
    is_allowance_supported: Optional[bool] = Field(default=None, alias="isAllowanceSupported", serialization_alias="isAllowanceSupported")
    showbbody_status: Optional[str] = Field(default=None, alias="showbbodyStatus", serialization_alias="showbbodyStatus")
    volunteer_status: Optional[str] = Field(default=None, alias="volunteerStatus", serialization_alias="volunteerStatus")
    approval_status: Optional[str] = Field(default=None, alias="approvalStatus", serialization_alias="approvalStatus")

    model_config = ConfigDict(populate_by_name=True)


class QualifiedBenefitResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[QualifiedBenefitItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Benefit claims (ค่าป่วยการที่ยื่นขอ) report
# ---------------------------------------------------------------------------


class BenefitClaimQuery(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="province", serialization_alias="province")
    province_code_legacy: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_code_snake: Optional[str] = Field(default=None, alias="province_code", serialization_alias="province_code")

    district_code: Optional[str] = Field(default=None, alias="district", serialization_alias="district")
    district_code_legacy: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_code_snake: Optional[str] = Field(default=None, alias="district_code", serialization_alias="district_code")

    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrict", serialization_alias="subdistrict")
    subdistrict_code_legacy: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_code_snake: Optional[str] = Field(default=None, alias="subdistrict_code", serialization_alias="subdistrict_code")

    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_code_legacy: Optional[str] = Field(default=None, alias="village", serialization_alias="village")
    village_code_snake: Optional[str] = Field(default=None, alias="village_code", serialization_alias="village_code")

    osm_showbbody: Optional[str] = Field(
        default=None,
        alias="osmShowbbody",
        validation_alias=AliasChoices("osmShowbbody", "osm_showbbody", "showbbody"),
        serialization_alias="osmShowbbody",
        description="สถานะสิทธิค่าป่วยการ (1/2=ได้รับ, 5=ไม่ได้รับ, 6=รอ)",
    )
    osm_status: Optional[str] = Field(
        default=None,
        alias="osmStatus",
        validation_alias=AliasChoices("osmStatus", "osm_status"),
        serialization_alias="osmStatus",
        description="สถานะ อสม. (''=ปกติ, 0=เสียชีวิต, 1=ลาออก, 2=พ้นสภาพ)",
    )
    active_only: bool = Field(
        default=False,
        alias="activeOnly",
        validation_alias=AliasChoices("activeOnly", "active_only", "excludeInactive"),
        serialization_alias="activeOnly",
        description="เมื่อ true จะแสดงเฉพาะสถานะปกติ (osm_status ว่าง/NULL)",
    )
    status: Optional[str] = Field(default=None, description="claim status")
    claim_type: Optional[str] = Field(default=None, alias="claimType", serialization_alias="claimType")
    date_from: Optional[date] = Field(default=None, alias="dateFrom", serialization_alias="dateFrom")
    date_to: Optional[date] = Field(default=None, alias="dateTo", serialization_alias="dateTo")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    @model_validator(mode="after")
    def _coalesce_admin_codes(self):
        updates = {}
        if self.province_code is None:
            updates["province_code"] = self.province_code_legacy or self.province_code_snake
        if self.district_code is None:
            updates["district_code"] = self.district_code_legacy or self.district_code_snake
        if self.subdistrict_code is None:
            updates["subdistrict_code"] = self.subdistrict_code_legacy or self.subdistrict_code_snake
        if self.village_code is None:
            updates["village_code"] = self.village_code_legacy or self.village_code_snake
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            return self
        return self.model_copy(update=updates)

    model_config = ConfigDict(populate_by_name=True)


class BenefitClaimItem(BaseModel):
    claim_id: Optional[str] = Field(default=None, alias="claimId", serialization_alias="claimId")
    osm_profile_id: str = Field(alias="osmProfileId", serialization_alias="osmProfileId")
    citizen_id: Optional[str] = Field(default=None, alias="citizenId", serialization_alias="citizenId")
    osm_code: Optional[str] = Field(default=None, alias="osmCode", serialization_alias="osmCode")
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    approval_date: Optional[str] = Field(default=None, alias="approvalDate", serialization_alias="approvalDate")
    allowance_year: Optional[int] = Field(default=None, alias="allowanceYear", serialization_alias="allowanceYear")
    osm_showbbody: Optional[str] = Field(default=None, alias="osmShowbbody", serialization_alias="osmShowbbody")
    benefit_status: Optional[str] = Field(
        default=None,
        alias="benefitStatus",
        serialization_alias="benefitStatus",
        description="mapped from osm_showbbody: eligible|ineligible|pending",
    )
    claim_type: str = Field(alias="claimType", serialization_alias="claimType")
    claim_date: str = Field(alias="claimDate", serialization_alias="claimDate")
    claim_round: Optional[int] = Field(default=None, alias="claimRound", serialization_alias="claimRound")
    amount: Optional[float] = None
    status: str
    decision_date: Optional[str] = Field(default=None, alias="decisionDate", serialization_alias="decisionDate")
    paid_date: Optional[str] = Field(default=None, alias="paidDate", serialization_alias="paidDate")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_no: Optional[str] = Field(default=None, alias="villageNo", serialization_alias="villageNo")
    village_name: Optional[str] = Field(default=None, alias="villageName", serialization_alias="villageName")

    model_config = ConfigDict(populate_by_name=True)


class BenefitClaimResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[BenefitClaimItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Resigned volunteers report
# ---------------------------------------------------------------------------


class ResignedVolunteerQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    osm_status: Optional[str] = Field(
        default=None,
        alias="osmStatus",
        serialization_alias="osmStatus",
        description="รหัสสถานะ อสม. จาก OsmStatusEnum (''=ปกติ, 0=เสียชีวิต, 1=ลาออก, 2=พ้นสภาพ)",
    )
    reason: Optional[str] = Field(default=None, description="ค่าจาก OSMRetirementReasonEnum")
    year_from: Optional[int] = Field(default=None, alias="yearFrom", serialization_alias="yearFrom")
    year_to: Optional[int] = Field(default=None, alias="yearTo", serialization_alias="yearTo")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class ResignedVolunteerItem(BaseModel):
    id: str
    citizen_id: Optional[str] = Field(default=None, alias="citizenId", serialization_alias="citizenId")
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    retirement_date: Optional[str] = Field(default=None, alias="retirementDate", serialization_alias="retirementDate")
    retirement_reason: Optional[str] = Field(default=None, alias="retirementReason", serialization_alias="retirementReason")
    osm_status: Optional[str] = Field(default=None, alias="osmStatus", serialization_alias="osmStatus")
    volunteer_status: Optional[str] = Field(default=None, alias="volunteerStatus", serialization_alias="volunteerStatus")
    approval_status: Optional[str] = Field(default=None, alias="approvalStatus", serialization_alias="approvalStatus")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_no: Optional[str] = Field(default=None, alias="villageNo", serialization_alias="villageNo")
    village_name: Optional[str] = Field(default=None, alias="villageName", serialization_alias="villageName")

    model_config = ConfigDict(populate_by_name=True)


class ResignedVolunteerResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[ResignedVolunteerItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Positions by village
# ---------------------------------------------------------------------------


class PositionsByVillageQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class PositionsByVillageItem(BaseModel):
    village_code: Optional[str] = Field(default=None, alias="villageCode", serialization_alias="villageCode")
    village_no: Optional[str] = Field(default=None, alias="villageNo", serialization_alias="villageNo")
    village_name: Optional[str] = Field(default=None, alias="villageName", serialization_alias="villageName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    position_name: Optional[str] = Field(default=None, alias="positionName", serialization_alias="positionName")
    count: int

    model_config = ConfigDict(populate_by_name=True)


class PositionsByVillageResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[PositionsByVillageItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# President by level / president list
# ---------------------------------------------------------------------------


class PresidentListQuery(BaseModel):
    area_name: Optional[str] = Field(default=None, alias="area", serialization_alias="area")
    province_code: Optional[str] = Field(default=None, alias="province", serialization_alias="province")
    district_code: Optional[str] = Field(default=None, alias="district", serialization_alias="district")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrict", serialization_alias="subdistrict")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class PresidentListItem(BaseModel):
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    position_name: Optional[str] = Field(default=None, alias="positionName", serialization_alias="positionName")
    position_level: Optional[str] = Field(default=None, alias="positionLevel", serialization_alias="positionLevel")
    area_name: Optional[str] = Field(default=None, alias="areaName", serialization_alias="areaName")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")

    model_config = ConfigDict(populate_by_name=True)


class PresidentListResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[PresidentListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


class PresidentByLevelQuery(BaseModel):
    position_level: Optional[str] = Field(default=None, alias="positionLevel", serialization_alias="positionLevel")
    area_name: Optional[str] = Field(default=None, alias="area", serialization_alias="area")
    province_code: Optional[str] = Field(default=None, alias="province", serialization_alias="province")
    district_code: Optional[str] = Field(default=None, alias="district", serialization_alias="district")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrict", serialization_alias="subdistrict")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class PresidentByLevelItem(BaseModel):
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    position_name: Optional[str] = Field(default=None, alias="positionName", serialization_alias="positionName")
    position_level: Optional[str] = Field(default=None, alias="positionLevel", serialization_alias="positionLevel")
    area_name: Optional[str] = Field(default=None, alias="areaName", serialization_alias="areaName")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")

    model_config = ConfigDict(populate_by_name=True)


class PresidentByLevelResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[PresidentByLevelItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Awards / confirmed by area
# ---------------------------------------------------------------------------


class AwardByAreaQuery(BaseModel):
    award_type: Optional[str] = Field(default=None, alias="awardType", serialization_alias="awardType")
    date_from: Optional[date] = Field(default=None, alias="dateFrom", serialization_alias="dateFrom")
    date_to: Optional[date] = Field(default=None, alias="dateTo", serialization_alias="dateTo")
    province_code: Optional[str] = Field(default=None, alias="province", serialization_alias="province")
    district_code: Optional[str] = Field(default=None, alias="district", serialization_alias="district")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrict", serialization_alias="subdistrict")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize", ge=1, le=200)

    model_config = ConfigDict(populate_by_name=True)


class AwardByAreaItem(BaseModel):
    award_id: str = Field(alias="awardId", serialization_alias="awardId")
    osm_profile_id: str = Field(alias="osmProfileId", serialization_alias="osmProfileId")
    first_name: str = Field(alias="firstName", serialization_alias="firstName")
    last_name: str = Field(alias="lastName", serialization_alias="lastName")
    award_type: str = Field(alias="awardType", serialization_alias="awardType")
    award_name: Optional[str] = Field(default=None, alias="awardName", serialization_alias="awardName")
    award_code: Optional[str] = Field(default=None, alias="awardCode", serialization_alias="awardCode")
    awarded_date: str = Field(alias="awardedDate", serialization_alias="awardedDate")
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")

    model_config = ConfigDict(populate_by_name=True)


class AwardByAreaResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[AwardByAreaItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Training by area
# ---------------------------------------------------------------------------


class TrainingByAreaQuery(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="province", serialization_alias="province")
    district_code: Optional[str] = Field(default=None, alias="district", serialization_alias="district")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrict", serialization_alias="subdistrict")
    year_from: Optional[int] = Field(default=None, alias="yearFrom", serialization_alias="yearFrom")
    year_to: Optional[int] = Field(default=None, alias="yearTo", serialization_alias="yearTo")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize", ge=1, le=200)

    model_config = ConfigDict(populate_by_name=True)


class TrainingByAreaItem(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    course_name: Optional[str] = Field(default=None, alias="courseName", serialization_alias="courseName")
    trained_year: Optional[int] = Field(default=None, alias="trainedYear", serialization_alias="trainedYear")
    count: int

    model_config = ConfigDict(populate_by_name=True)


class TrainingByAreaResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[TrainingByAreaItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Specialty (skill) by area
# ---------------------------------------------------------------------------


class SpecialtyByAreaQuery(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="province", serialization_alias="province")
    district_code: Optional[str] = Field(default=None, alias="district", serialization_alias="district")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrict", serialization_alias="subdistrict")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize", ge=1, le=200)

    model_config = ConfigDict(populate_by_name=True)


class SpecialtyByAreaItem(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    skill_name: Optional[str] = Field(default=None, alias="skillName", serialization_alias="skillName")
    count: int

    model_config = ConfigDict(populate_by_name=True)


class SpecialtyByAreaResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[SpecialtyByAreaItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Resigned report (summary / aggregate)
# ---------------------------------------------------------------------------


class ResignedReportQuery(BaseModel):
    province_code: Optional[str] = Field(
        default=None,
        alias="province",
        validation_alias=AliasChoices("province", "provinceCode", "province_code"),
        serialization_alias="province",
    )
    district_code: Optional[str] = Field(
        default=None,
        alias="district",
        validation_alias=AliasChoices("district", "districtCode", "district_code"),
        serialization_alias="district",
    )
    subdistrict_code: Optional[str] = Field(
        default=None,
        alias="subdistrict",
        validation_alias=AliasChoices("subdistrict", "subdistrictCode", "subdistrict_code"),
        serialization_alias="subdistrict",
    )
    reason: Optional[str] = Field(default=None, description="ค่าจาก OSMRetirementReasonEnum")
    year_from: Optional[int] = Field(default=None, alias="yearFrom", serialization_alias="yearFrom")
    year_to: Optional[int] = Field(default=None, alias="yearTo", serialization_alias="yearTo")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        alias="pageSize",
        validation_alias=AliasChoices("pageSize", "page_size", "limit"),
        serialization_alias="pageSize",
    )

    model_config = ConfigDict(populate_by_name=True)


class ResignedReportItem(BaseModel):
    province_code: Optional[str] = Field(default=None, alias="provinceCode", serialization_alias="provinceCode")
    province_name: Optional[str] = Field(default=None, alias="provinceName", serialization_alias="provinceName")
    district_code: Optional[str] = Field(default=None, alias="districtCode", serialization_alias="districtCode")
    district_name: Optional[str] = Field(default=None, alias="districtName", serialization_alias="districtName")
    subdistrict_code: Optional[str] = Field(default=None, alias="subdistrictCode", serialization_alias="subdistrictCode")
    subdistrict_name: Optional[str] = Field(default=None, alias="subdistrictName", serialization_alias="subdistrictName")
    retirement_reason: Optional[str] = Field(default=None, alias="retirementReason", serialization_alias="retirementReason")
    total_resigned: int = Field(default=0, alias="totalResigned", serialization_alias="totalResigned")

    model_config = ConfigDict(populate_by_name=True)


class ResignedReportResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[ResignedReportItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize", serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)
