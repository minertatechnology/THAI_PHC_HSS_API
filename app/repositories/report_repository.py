from typing import Tuple, List

from app.api.v1.schemas.query_schema import ReportOsmGenderQueryParams,ReportOsmFamilyQueryParams,ReportOsmPresidentQueryParams
from app.models.report_model import OsmGenderSummary,OsmFamilySummary,OsmPresidentSummary


class ReportRepository:
    @staticmethod
    async def osm_genders(filter: ReportOsmGenderQueryParams) -> Tuple[List[OsmGenderSummary], int]:
        query = OsmGenderSummary.filter(snapshot_type="live")

        # Apply filters
        if filter.province_code:
            query = query.filter(province_id=filter.province_code)
        if filter.district_code:
            query = query.filter(district_id=filter.district_code)
        if filter.subdistrict_code:
            query = query.filter(subdistrict_id=filter.subdistrict_code)

        # Total count for pagination
        total = await query.count()

        # Pagination
        offset = (filter.page - 1) * filter.limit
        items = await query.offset(offset).limit(filter.limit)

        return items, total

    @staticmethod
    async def generate_osm_family_report(filter: ReportOsmFamilyQueryParams) -> Tuple[List[OsmFamilySummary], int]:
        query = OsmFamilySummary.all()

        # Apply filters
        if filter.province_code:
            query = query.filter(province_id=filter.province_code)
        if filter.district_code:
            query = query.filter(district_id=filter.district_code)
        if filter.subdistrict_code:
            query = query.filter(subdistrict_id=filter.subdistrict_code)
        if filter.status and filter.status != "all":
            query = query.filter(status=filter.status)

        # Total count for pagination
        total = await query.count()

        # Pagination
        offset = (filter.page - 1) * filter.limit
        items = await query.offset(offset).limit(filter.limit)

        return items, total

    @staticmethod
    async def generate_osm_president_report(filter: ReportOsmPresidentQueryParams) -> Tuple[List[OsmPresidentSummary], int]:
        query = OsmPresidentSummary.all()

        # Apply filters
        if filter.position_level:
            query = query.filter(position_level=filter.position_level)
        if filter.area_code:
            query = query.filter(area_name_th__icontains=filter.area_code)
        if filter.province_code:
            query = query.filter(province_name_th__icontains=filter.province_code)
        if filter.district_code:
            query = query.filter(district_name_th__icontains=filter.district_code)
        if filter.subdistrict_code:
            query = query.filter(subdistrict_name_th__icontains=filter.subdistrict_code)

        # Total count for pagination
        total = await query.count()

        # Pagination
        offset = (filter.page - 1) * filter.limit
        items = await query.offset(offset).limit(filter.limit)

        return items, total

