from app.api.v1.schemas.query_schema import ReportOsmGenderQueryParams,ReportOsmFamilyQueryParams,ReportOsmPresidentQueryParams
from app.api.v1.schemas.response_schema import (
    osm_gender_summary_to_response,
    osm_family_summary_to_response,
    osm_president_summary_to_response,
    OsmGenderSummaryPaginatedResponse,
    OsmFamilySummaryPaginatedResponse,
    OsmPresidentPaginatedResponse,
)
from app.repositories.report_repository import ReportRepository


class ReportService:
    @staticmethod
    async def osm_genders(filter: ReportOsmGenderQueryParams) -> OsmGenderSummaryPaginatedResponse:
        items, total = await ReportRepository.osm_genders(filter)
        return OsmGenderSummaryPaginatedResponse(
            items=[osm_gender_summary_to_response(item) for item in items],
            total=total,
            page=filter.page,
            pageSize=filter.limit,
        )

    @staticmethod
    async def generate_osm_family_report(filter: ReportOsmFamilyQueryParams) -> OsmFamilySummaryPaginatedResponse:
        items, total = await ReportRepository.generate_osm_family_report(filter)
        return OsmFamilySummaryPaginatedResponse(
            items=[osm_family_summary_to_response(item) for item in items],
            total=total,
            page=filter.page,
            pageSize=filter.limit,
        )

    @staticmethod
    async def generate_osm_president_report(filter: ReportOsmPresidentQueryParams) -> OsmPresidentPaginatedResponse:
        items, total = await ReportRepository.generate_osm_president_report(filter)
        return OsmPresidentPaginatedResponse(
            items=[osm_president_summary_to_response(item) for item in items],
            total=total,
            page=filter.page,
            pageSize=filter.limit,
        )