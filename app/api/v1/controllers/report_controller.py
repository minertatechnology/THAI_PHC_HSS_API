from app.services.report_service import ReportService
from app.api.v1.schemas.query_schema import ReportOsmGenderQueryParams,ReportOsmFamilyQueryParams,ReportOsmPresidentQueryParams

class  ReportController:
    async def osm_genders(filter: ReportOsmGenderQueryParams):
        result = await ReportService.osm_genders(filter)
        return result
    
    async def generate_osm_family_report(filter: ReportOsmFamilyQueryParams):
        result = await ReportService.generate_osm_family_report(filter)
        return result
    
    async def generate_osm_president_report(filter: ReportOsmPresidentQueryParams):
        result = await ReportService.generate_osm_president_report(filter)
        return result
