from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.api.v1.schemas.response_schema import PaginationMeta


class DashboardSummaryItem(BaseModel):
    level: str
    year: int
    provinceCode: Optional[str]
    provinceNameTh: Optional[str]
    provinceNameEn: Optional[str]
    districtCode: Optional[str]
    districtNameTh: Optional[str]
    districtNameEn: Optional[str]
    subdistrictCode: Optional[str]
    subdistrictNameTh: Optional[str]
    subdistrictNameEn: Optional[str]
    districtCount: int
    subdistrictCount: int
    villageCount: int
    communityCount: int
    pcuCount: int
    rpsCount: int
    rptCount: int
    quota: int
    osmCount: int
    osmAllowanceEligibleCount: int
    osmTrainingBudgetCount: int
    osmPaymentTrainingCount: int
    osmShowbbodyPaidCount: int
    osmShowbbodyNotPaidCount: int
    osmShowbbodyPendingCount: int
    osmNoShowbbodyStatusCount: int
    lastCalculatedAt: Optional[datetime]
    updatedAt: Optional[datetime]


class DashboardSummaryResponse(BaseModel):
    items: List[DashboardSummaryItem]


class DashboardProvinceAggregate(BaseModel):
    provinceCode: Optional[str]
    provinceNameTh: Optional[str]
    provinceNameEn: Optional[str]
    osmCount: int


class DashboardVolunteerRow(BaseModel):
    id: str
    osmCode: Optional[str]
    citizenId: Optional[str]
    prefixNameTh: Optional[str]
    prefixNameEn: Optional[str]
    firstName: Optional[str]
    lastName: Optional[str]
    fullName: Optional[str]
    provinceCode: Optional[str]
    provinceNameTh: Optional[str]
    districtCode: Optional[str]
    districtNameTh: Optional[str]
    subdistrictCode: Optional[str]
    subdistrictNameTh: Optional[str]
    villageNo: Optional[str]
    villageName: Optional[str]
    isActive: bool
    status: str
    osmStatus: Optional[str]
    approvalStatus: Optional[str]
    volunteerStatus: Optional[str]
    createdAt: Optional[datetime]
    requestDate: Optional[datetime]
    updatedAt: Optional[datetime]


class DashboardProvinceAssignmentsResponse(BaseModel):
    provinces: List[DashboardProvinceAggregate]
    items: List[DashboardVolunteerRow]
    pagination: PaginationMeta