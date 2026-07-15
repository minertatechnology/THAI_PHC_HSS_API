from typing import Tuple, List, Optional

from app.api.v1.schemas.query_schema import ReportOsmGenderQueryParams,ReportOsmFamilyQueryParams,ReportOsmPresidentQueryParams
from app.models.report_model import OsmGenderSummary,OsmFamilySummary,OsmPresidentSummary
from app.models.health_model import HealthService, HealthServiceArea


class ReportRepository:
    @staticmethod
    async def _resolve_subdistrict_codes(
        subdistrict_code: Optional[str], health_service_id: Optional[str]
    ) -> Optional[List[str]]:
        """ถ้ามี health_service_id (รพ.สต.) → resolve เป็นรหัสตำบลทั้งหมดที่หน่วยบริการครอบคลุม
        (ที่ตั้งหลัก + service_areas) ใช้กรอง report แทนตำบลเดียว"""
        if health_service_id:
            codes: List[str] = []
            hs = await HealthService.filter(health_service_code=health_service_id).only("subdistrict_id").first()
            if hs and hs.subdistrict_id:
                codes.append(hs.subdistrict_id)
            areas = await HealthServiceArea.filter(
                health_service_id=health_service_id, deleted_at__isnull=True
            ).only("subdistrict_id")
            for area in areas:
                if area.subdistrict_id and area.subdistrict_id not in codes:
                    codes.append(area.subdistrict_id)
            if codes:
                return codes
        if subdistrict_code:
            return [subdistrict_code]
        return None

    @staticmethod
    async def osm_genders(filter: ReportOsmGenderQueryParams) -> Tuple[List[OsmGenderSummary], int]:
        query = OsmGenderSummary.filter(snapshot_type="live")

        # Apply filters
        if filter.province_code:
            query = query.filter(province_id=filter.province_code)
        if filter.district_code:
            query = query.filter(district_id=filter.district_code)
        sd_codes = await ReportRepository._resolve_subdistrict_codes(
            filter.subdistrict_code, filter.health_service_id
        )
        if sd_codes:
            query = query.filter(subdistrict_id__in=sd_codes)

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
        sd_codes = await ReportRepository._resolve_subdistrict_codes(
            filter.subdistrict_code, filter.health_service_id
        )
        if sd_codes:
            query = query.filter(subdistrict_id__in=sd_codes)
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
        sd_codes = await ReportRepository._resolve_subdistrict_codes(
            filter.subdistrict_code, filter.health_service_id
        )
        if sd_codes:
            query = query.filter(subdistrict_name_th__in=sd_codes)

        # Total count for pagination
        total = await query.count()

        # Pagination
        offset = (filter.page - 1) * filter.limit
        items = await query.offset(offset).limit(filter.limit)

        return items, total

