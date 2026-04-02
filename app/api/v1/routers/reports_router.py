from __future__ import annotations

from typing import Callable, Dict, Optional

from fastapi import APIRouter, Depends

from app.api.middleware.middleware import require_scopes
from app.api.middleware.mock_auth import get_mock_current_user
from app.api.v1.schemas.report_standard_schema import (
    FamilyAddressReportQuery,
    FamilyAddressReportResponse,
    AverageAgeReportQuery,
    AverageAgeReportResponse,
    NewVolunteerByYearQuery,
    NewVolunteerByYearResponse,
    VolunteerTenureQuery,
    VolunteerTenureResponse,
    BenefitClaimQuery,
    BenefitClaimResponse,
    QualifiedBenefitQuery,
    QualifiedBenefitResponse,
    ResignedVolunteerQuery,
    ResignedVolunteerResponse,
    ResignedReportQuery,
    ResignedReportResponse,
    PositionsByVillageQuery,
    PositionsByVillageResponse,
    PresidentListQuery,
    PresidentListResponse,
    PresidentByLevelQuery,
    PresidentByLevelResponse,
    AwardByAreaQuery,
    AwardByAreaResponse,
    TrainingByAreaQuery,
    TrainingByAreaResponse,
    SpecialtyByAreaQuery,
    SpecialtyByAreaResponse,
    StandardGenderReportQuery,
    StandardGenderReportResponse,
    StandardGenderSnapshotCreateRequest,
    StandardGenderSnapshotQuery,
    StandardGenderSnapshotResponse,
    SnapshotMutationResponse,
)
from app.services.mock_data_store import MockDataStore
from app.services.standard_report_service import StandardReportService
from app.services.permission_service import PermissionService
from app.utils.scope_enforcement import enforce_scope_on_filters, apply_scope_to_query


reports_router = APIRouter(prefix="/reports", tags=["reports"])


_REPORT_MAP: Dict[str, str] = {
    "volunteer-address": "volunteer-address",
    "president-list": "president-list",
    "benefit-claim": "benefit-claim",
    "volunteer-tenure": "volunteer-tenure",
    "vaccine-levels": "vaccine-levels",
    "tracking-by-level": "tracking-by-level",
    "resigned-summary": "resigned-summary",
}


@reports_router.get(
    "/volunteer-gender",
    response_model=StandardGenderReportResponse,
)
async def volunteer_gender_report(
    filters: StandardGenderReportQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    """Production-ready volunteer gender report."""
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=filters.village_code,
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.volunteer_gender(filters)


@reports_router.get(
    "/volunteer-family",
    response_model=FamilyAddressReportResponse,
)
async def volunteer_family_report(
    filters: FamilyAddressReportQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=filters.village_code,
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.volunteer_family_report(filters)


@reports_router.get(
    "/average-age",
    response_model=AverageAgeReportResponse,
)
async def average_age_report(
    filters: AverageAgeReportQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.average_age_report(filters)


@reports_router.get(
    "/new-volunteers",
    response_model=NewVolunteerByYearResponse,
)
async def new_volunteers_by_year(
    filters: NewVolunteerByYearQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.new_volunteers_by_year(filters)


@reports_router.get(
    "/volunteer-tenure",
    response_model=VolunteerTenureResponse,
)
async def volunteer_tenure(
    filters: VolunteerTenureQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.volunteer_tenure(filters)


@reports_router.get(
    "/qualified-benefit",
    response_model=QualifiedBenefitResponse,
)
async def qualified_benefit(
    filters: QualifiedBenefitQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.qualified_benefit(filters)


@reports_router.get(
    "/benefit-claims",
    response_model=BenefitClaimResponse,
)
async def benefit_claims(
    filters: BenefitClaimQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.benefit_claim_list(filters)


@reports_router.get(
    "/resigned-volunteers",
    response_model=ResignedVolunteerResponse,
)
async def resigned_volunteers(
    filters: ResignedVolunteerQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.resigned_volunteers(filters)


@reports_router.get(
    "/resigned-report",
    response_model=ResignedReportResponse,
)
async def resigned_report(
    filters: ResignedReportQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.resigned_report(filters)


@reports_router.get(
    "/positions-by-village",
    response_model=PositionsByVillageResponse,
)
async def positions_by_village(
    filters: PositionsByVillageQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.positions_by_village(filters)


@reports_router.get(
    "/president-by-level",
    response_model=PresidentByLevelResponse,
)
async def president_by_level(
    filters: PresidentByLevelQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.president_by_level(filters)


@reports_router.get(
    "/president-list",
    response_model=PresidentListResponse,
)
async def president_list(
    filters: PresidentListQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.president_list(filters)


@reports_router.get(
    "/training-by-area",
    response_model=TrainingByAreaResponse,
)
async def training_by_area(
    filters: TrainingByAreaQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.training_by_area(filters)


@reports_router.get(
    "/awards-by-area",
    response_model=AwardByAreaResponse,
)
async def awards_by_area(
    filters: AwardByAreaQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.awards_by_area(filters)


@reports_router.get(
    "/standard-confirmed-by-area",
    response_model=AwardByAreaResponse,
)
async def standard_confirmed_by_area(
    filters: AwardByAreaQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    """รายงานผู้ได้รับรางวัล/เข็ม แยกตามพื้นที่ ใช้ข้อมูลเดียวกับ awards-by-area."""
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.awards_by_area(filters)


@reports_router.get(
    "/specialty-by-area",
    response_model=SpecialtyByAreaResponse,
)
async def specialty_by_area(
    filters: SpecialtyByAreaQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.specialty_by_area(filters)


@reports_router.post(
    "/volunteer-gender/refresh",
    response_model=SnapshotMutationResponse,
)
async def refresh_volunteer_gender(current_user=Depends(require_scopes({"profile"}))):
    await PermissionService.require_officer(current_user)
    return await StandardReportService.refresh_gender_summary()


@reports_router.post(
    "/volunteer-gender/snapshots",
    response_model=SnapshotMutationResponse,
)
async def capture_volunteer_gender_snapshot(
    payload: StandardGenderSnapshotCreateRequest,
    current_user=Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    triggered_by = current_user.get("user_id")
    return await StandardReportService.capture_gender_snapshot(payload, triggered_by)


@reports_router.get(
    "/volunteer-gender/snapshots",
    response_model=StandardGenderSnapshotResponse,
)
async def volunteer_gender_snapshots(
    filters: StandardGenderSnapshotQuery = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filters.province_code,
        district_code=filters.district_code,
        subdistrict_code=filters.subdistrict_code,
        village_code=getattr(filters, "village_code", None),
    )
    apply_scope_to_query(filters, override)
    return await StandardReportService.volunteer_gender_snapshot(filters)


def _build_handler(report_key: str) -> Callable:
    async def _handler(
        province: Optional[str] = None,
        district: Optional[str] = None,
        year: Optional[str] = None,
        page: int = 1,
        pageSize: int = 20,
        current_user=Depends(get_mock_current_user),
    ):
        filters = {
            "province": province,
            "district": district,
            "year": year,
        }
        return MockDataStore.get_report(report_key, filters, page, pageSize)

    return _handler


for path, key in _REPORT_MAP.items():
    reports_router.add_api_route(f"/{path}", _build_handler(key), methods=["GET"])
