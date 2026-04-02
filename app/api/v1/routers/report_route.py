from fastapi import APIRouter, Depends  
from app.api.v1.controllers.report_controller import ReportController
from app.api.v1.schemas.query_schema import ReportOsmGenderQueryParams,ReportOsmFamilyQueryParams,ReportOsmPresidentQueryParams
from app.api.middleware.middleware import get_current_user, require_scopes
from app.api.v1.schemas.response_schema import (
    OsmGenderSummaryPaginatedResponse,
    OsmFamilySummaryPaginatedResponse,
    OsmPresidentPaginatedResponse,
)
from app.utils.scope_enforcement import enforce_scope_on_filters, apply_scope_to_query

report_router = APIRouter(prefix="/report", tags=["report"])

@report_router.get("/osm/summary/genders", response_model=OsmGenderSummaryPaginatedResponse)
async def osm_genders(
    filter: ReportOsmGenderQueryParams = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filter.province_code,
        district_code=filter.district_code,
        subdistrict_code=filter.subdistrict_code,
    )
    apply_scope_to_query(filter, override)
    result = await ReportController.osm_genders(filter)
    return result

@report_router.get("/osm/summary/osm-family-type", response_model=OsmFamilySummaryPaginatedResponse)
async def osm_family_type(
    filter: ReportOsmFamilyQueryParams = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filter.province_code,
        district_code=filter.district_code,
        subdistrict_code=filter.subdistrict_code,
    )
    apply_scope_to_query(filter, override)
    result = await ReportController.generate_osm_family_report(filter)
    return result

@report_router.get("/osm/summary/osm-president", response_model=OsmPresidentPaginatedResponse)
async def osm_president(
    filter: ReportOsmPresidentQueryParams = Depends(),
    current_user=Depends(require_scopes({"profile"})),
):
    override = await enforce_scope_on_filters(
        current_user,
        province_code=filter.province_code,
        district_code=filter.district_code,
        subdistrict_code=filter.subdistrict_code,
    )
    apply_scope_to_query(filter, override)
    result = await ReportController.generate_osm_president_report(filter)
    return result
