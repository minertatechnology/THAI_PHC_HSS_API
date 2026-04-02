from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from app.models.enum_models import NewRegistrationAllowanceStatusEnum, OsmShowbbodyEnum
from app.models.geography_model import District, Province, Subdistrict, Village
from app.models.health_model import HealthService
from tortoise.queryset import Q

from app.models.osm_model import OSMProfile
from app.repositories.dashboard_summary_repository import DashboardSummaryRepository


GEO_LEVEL_PROVINCE = "province"
GEO_LEVEL_DISTRICT = "district"
GEO_LEVEL_SUBDISTRICT = "subdistrict"
VALID_GEO_LEVELS = {GEO_LEVEL_PROVINCE, GEO_LEVEL_DISTRICT, GEO_LEVEL_SUBDISTRICT}


def resolve_geo_level(
    *,
    explicit_level: Optional[str] = None,
    district_code: Optional[str] = None,
    district_codes: Optional[Sequence[str]] = None,
    subdistrict_code: Optional[str] = None,
    subdistrict_codes: Optional[Sequence[str]] = None,
) -> str:
    if explicit_level:
        if explicit_level not in VALID_GEO_LEVELS:
            raise ValueError(f"Unsupported geography level: {explicit_level}")
        return explicit_level

    if subdistrict_code or (subdistrict_codes and len(subdistrict_codes) > 0):
        return GEO_LEVEL_SUBDISTRICT

    if district_code or (district_codes and len(district_codes) > 0):
        return GEO_LEVEL_DISTRICT

    return GEO_LEVEL_PROVINCE


@dataclass
class DashboardSummaryDTO:
    year_buddhist: int
    province_code: Optional[str]
    province_name_th: Optional[str]
    province_name_en: Optional[str]
    level: str = GEO_LEVEL_PROVINCE
    district_code: Optional[str] = None
    district_name_th: Optional[str] = None
    district_name_en: Optional[str] = None
    subdistrict_code: Optional[str] = None
    subdistrict_name_th: Optional[str] = None
    subdistrict_name_en: Optional[str] = None
    district_count: int = 0
    subdistrict_count: int = 0
    village_count: int = 0
    community_count: int = 0
    pcu_count: int = 0
    hosp_satang_count: int = 0
    hosp_general_count: int = 0
    quota: int = 0
    osm_count: int = 0
    osm_allowance_eligible_count: int = 0
    osm_training_budget_count: int = 0
    osm_payment_training_count: int = 0
    osm_showbbody_paid_count: int = 0
    osm_showbbody_not_paid_count: int = 0
    osm_showbbody_pending_count: int = 0
    osm_no_showbbody_status_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["geography_level"] = payload.pop("level", GEO_LEVEL_PROVINCE)
        return payload


class DashboardSummaryAggregator:
    """Aggregate raw data into dashboard summary snapshots."""

    PCU_TYPES = {"หน่วยบริการปฐมภูมิ (PCU)"}
    HOSP_RPST_TYPES = {"โรงพยาบาลส่งเสริมสุขภาพตำบล", "สถานีอนามัย"}
    HOSP_GENERAL_TYPES = {"โรงพยาบาลทั่วไป", "โรงพยาบาลชุมชน", "โรงพยาบาลศูนย์"}

    ALLOWANCE_ELIGIBLE_STATUSES = {
        NewRegistrationAllowanceStatusEnum.ACCEPTED,
        NewRegistrationAllowanceStatusEnum.ACCEPTED_WITH_INCOMPLETE_PROOF,
        NewRegistrationAllowanceStatusEnum.PENDING,
    }

    @staticmethod
    def current_buddhist_year() -> int:
        return datetime.utcnow().year + 543

    @classmethod
    async def recalculate(
        cls,
        year_buddhist: Optional[int] = None,
        *,
        level: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
    ) -> List[DashboardSummaryDTO]:
        target_year = year_buddhist or cls.current_buddhist_year()
        resolved_level = resolve_geo_level(
            explicit_level=level,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
        )

        if resolved_level == GEO_LEVEL_PROVINCE:
            return await cls._recalculate_provinces(target_year=target_year, province_code=province_code)

        if resolved_level == GEO_LEVEL_DISTRICT:
            return await cls._recalculate_districts(
                target_year=target_year,
                province_code=province_code,
                district_code=district_code,
            )

        return await cls._recalculate_subdistricts(
            target_year=target_year,
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
        )

    @classmethod
    async def _recalculate_provinces(
        cls,
        *,
        target_year: int,
        province_code: Optional[str] = None,
    ) -> List[DashboardSummaryDTO]:
        provinces_query = Province.all().order_by("province_code")
        if province_code:
            provinces_query = provinces_query.filter(province_code=province_code)

        provinces = await provinces_query
        if not provinces:
            return []

        include_totals = province_code is None
        totals = (
            DashboardSummaryDTO(
                year_buddhist=target_year,
                province_code=None,
                province_name_th="ทั้งหมด",
                province_name_en="All",
                level=GEO_LEVEL_PROVINCE,
            )
            if include_totals
            else None
        )

        results: List[DashboardSummaryDTO] = []
        for province in provinces:
            data = await cls._build_summary_for_province(
                year_buddhist=target_year,
                province=province,
            )
            await DashboardSummaryRepository.upsert_summary(
                year_buddhist=target_year,
                geography_level=GEO_LEVEL_PROVINCE,
                province_code=province.province_code,
                district_code=None,
                subdistrict_code=None,
                payload=data.to_dict(),
            )
            results.append(data)
            if totals:
                cls._accumulate(totals, data)

        if totals:
            await DashboardSummaryRepository.upsert_summary(
                year_buddhist=target_year,
                geography_level=GEO_LEVEL_PROVINCE,
                province_code=None,
                district_code=None,
                subdistrict_code=None,
                payload=totals.to_dict(),
            )
            results.append(totals)

        return results

    @classmethod
    async def _recalculate_districts(
        cls,
        *,
        target_year: int,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
    ) -> List[DashboardSummaryDTO]:
        districts_query = District.all().order_by("district_code").prefetch_related("province")
        if district_code:
            districts_query = districts_query.filter(district_code=district_code)
        elif province_code:
            districts_query = districts_query.filter(province_id=province_code)

        districts = await districts_query
        if not districts:
            return []

        results: List[DashboardSummaryDTO] = []
        for district in districts:
            province = getattr(district, "province", None)
            quota = getattr(province, "quota", 0) if province else 0
            data = await cls._build_summary_for_district(
                year_buddhist=target_year,
                district=district,
                province_quota=quota,
            )
            await DashboardSummaryRepository.upsert_summary(
                year_buddhist=target_year,
                geography_level=GEO_LEVEL_DISTRICT,
                province_code=district.province_id,
                district_code=district.district_code,
                subdistrict_code=None,
                payload=data.to_dict(),
            )
            results.append(data)

        return results

    @classmethod
    async def _recalculate_subdistricts(
        cls,
        *,
        target_year: int,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
    ) -> List[DashboardSummaryDTO]:
        subdistricts_query = (
            Subdistrict.all()
            .order_by("subdistrict_code")
            .prefetch_related("district__province")
        )

        if subdistrict_code:
            subdistricts_query = subdistricts_query.filter(subdistrict_code=subdistrict_code)
        elif district_code:
            subdistricts_query = subdistricts_query.filter(district_id=district_code)
        elif province_code:
            subdistricts_query = subdistricts_query.filter(district__province_id=province_code)

        subdistricts = await subdistricts_query
        if not subdistricts:
            return []

        results: List[DashboardSummaryDTO] = []
        for subdistrict in subdistricts:
            district = getattr(subdistrict, "district", None)
            province = getattr(district, "province", None) if district else None
            quota = getattr(province, "quota", 0) if province else 0
            data = await cls._build_summary_for_subdistrict(
                year_buddhist=target_year,
                subdistrict=subdistrict,
                province_quota=quota,
            )
            await DashboardSummaryRepository.upsert_summary(
                year_buddhist=target_year,
                geography_level=GEO_LEVEL_SUBDISTRICT,
                province_code=district.province_id if district else None,
                district_code=subdistrict.district_id,
                subdistrict_code=subdistrict.subdistrict_code,
                payload=data.to_dict(),
            )
            results.append(data)

        return results

    @classmethod
    async def _build_summary_for_province(cls, *, year_buddhist: int, province: Province) -> DashboardSummaryDTO:
        province_code = province.province_code
        district_count = await District.filter(province_id=province_code).count()
        subdistrict_count = await Subdistrict.filter(district__province_id=province_code).count()
        village_count = await Village.filter(subdistrict__district__province_id=province_code).count()

        pcu_count = await cls._count_health_services(
            province_code=province_code,
            type_names=cls.PCU_TYPES,
        )
        hosp_rpst_count = await cls._count_health_services(
            province_code=province_code,
            type_names=cls.HOSP_RPST_TYPES,
        )
        hosp_general_count = await cls._count_health_services(
            province_code=province_code,
            type_names=cls.HOSP_GENERAL_TYPES,
        )

        base_query = cls._osm_base_query(province_code=province_code)
        osm_count = await base_query.count()
        allowance_count = await base_query.filter(
            new_registration_allowance_status__in=tuple(cls.ALLOWANCE_ELIGIBLE_STATUSES)
        ).count()

        showbbody_paid = await base_query.filter(
            osm_showbbody__in=[OsmShowbbodyEnum.PAID_TYPE1, OsmShowbbodyEnum.PAID_TYPE2]
        ).count()
        showbbody_not_paid = await base_query.filter(osm_showbbody=OsmShowbbodyEnum.NOT_PAID).count()
        showbbody_pending = await base_query.filter(osm_showbbody=OsmShowbbodyEnum.PENDING).count()
        no_showbbody_status = osm_count - showbbody_paid - showbbody_not_paid - showbbody_pending

        return DashboardSummaryDTO(
            year_buddhist=year_buddhist,
            province_code=province_code,
            province_name_th=province.province_name_th,
            province_name_en=province.province_name_en,
            level=GEO_LEVEL_PROVINCE,
            district_count=district_count,
            subdistrict_count=subdistrict_count,
            village_count=village_count,
            community_count=0,
            pcu_count=pcu_count,
            hosp_satang_count=hosp_rpst_count,
            hosp_general_count=hosp_general_count,
            quota=int(getattr(province, "quota", 0) or 0),
            osm_count=osm_count,
            osm_allowance_eligible_count=allowance_count,
            osm_training_budget_count=0,
            osm_payment_training_count=0,
            osm_showbbody_paid_count=showbbody_paid,
            osm_showbbody_not_paid_count=showbbody_not_paid,
            osm_showbbody_pending_count=showbbody_pending,
            osm_no_showbbody_status_count=no_showbbody_status,
        )

    @classmethod
    async def _build_summary_for_district(
        cls,
        *,
        year_buddhist: int,
        district: District,
        province_quota: int,
    ) -> DashboardSummaryDTO:
        province = getattr(district, "province", None)
        subdistrict_count = await Subdistrict.filter(district_id=district.district_code).count()
        village_count = await Village.filter(subdistrict__district_id=district.district_code).count()

        pcu_count = await cls._count_health_services(
            province_code=district.province_id,
            district_code=district.district_code,
            type_names=cls.PCU_TYPES,
        )
        hosp_rpst_count = await cls._count_health_services(
            province_code=district.province_id,
            district_code=district.district_code,
            type_names=cls.HOSP_RPST_TYPES,
        )
        hosp_general_count = await cls._count_health_services(
            province_code=district.province_id,
            district_code=district.district_code,
            type_names=cls.HOSP_GENERAL_TYPES,
        )

        base_query = cls._osm_base_query(
            province_code=district.province_id,
            district_code=district.district_code,
        )
        osm_count = await base_query.count()
        allowance_count = await base_query.filter(
            new_registration_allowance_status__in=tuple(cls.ALLOWANCE_ELIGIBLE_STATUSES)
        ).count()

        showbbody_paid = await base_query.filter(
            osm_showbbody__in=[OsmShowbbodyEnum.PAID_TYPE1, OsmShowbbodyEnum.PAID_TYPE2]
        ).count()
        showbbody_not_paid = await base_query.filter(osm_showbbody=OsmShowbbodyEnum.NOT_PAID).count()
        showbbody_pending = await base_query.filter(osm_showbbody=OsmShowbbodyEnum.PENDING).count()
        no_showbbody_status = osm_count - showbbody_paid - showbbody_not_paid - showbbody_pending

        return DashboardSummaryDTO(
            year_buddhist=year_buddhist,
            province_code=district.province_id,
            province_name_th=getattr(province, "province_name_th", None),
            province_name_en=getattr(province, "province_name_en", None),
            district_code=district.district_code,
            district_name_th=district.district_name_th,
            district_name_en=district.district_name_en,
            level=GEO_LEVEL_DISTRICT,
            district_count=1,
            subdistrict_count=subdistrict_count,
            village_count=village_count,
            community_count=0,
            pcu_count=pcu_count,
            hosp_satang_count=hosp_rpst_count,
            hosp_general_count=hosp_general_count,
            quota=int(province_quota or 0),
            osm_count=osm_count,
            osm_allowance_eligible_count=allowance_count,
            osm_training_budget_count=0,
            osm_payment_training_count=0,
            osm_showbbody_paid_count=showbbody_paid,
            osm_showbbody_not_paid_count=showbbody_not_paid,
            osm_showbbody_pending_count=showbbody_pending,
            osm_no_showbbody_status_count=no_showbbody_status,
        )

    @classmethod
    async def _build_summary_for_subdistrict(
        cls,
        *,
        year_buddhist: int,
        subdistrict: Subdistrict,
        province_quota: int,
    ) -> DashboardSummaryDTO:
        district = getattr(subdistrict, "district", None)
        province = getattr(district, "province", None) if district else None
        village_count = await Village.filter(subdistrict_id=subdistrict.subdistrict_code).count()

        province_code = district.province_id if district else None

        pcu_count = await cls._count_health_services(
            province_code=province_code,
            district_code=subdistrict.district_id,
            subdistrict_code=subdistrict.subdistrict_code,
            type_names=cls.PCU_TYPES,
        )
        hosp_rpst_count = await cls._count_health_services(
            province_code=province_code,
            district_code=subdistrict.district_id,
            subdistrict_code=subdistrict.subdistrict_code,
            type_names=cls.HOSP_RPST_TYPES,
        )
        hosp_general_count = await cls._count_health_services(
            province_code=province_code,
            district_code=subdistrict.district_id,
            subdistrict_code=subdistrict.subdistrict_code,
            type_names=cls.HOSP_GENERAL_TYPES,
        )

        base_query = cls._osm_base_query(
            province_code=province_code,
            district_code=subdistrict.district_id,
            subdistrict_code=subdistrict.subdistrict_code,
        )
        osm_count = await base_query.count()
        allowance_count = await base_query.filter(
            new_registration_allowance_status__in=tuple(cls.ALLOWANCE_ELIGIBLE_STATUSES)
        ).count()

        showbbody_paid = await base_query.filter(
            osm_showbbody__in=[OsmShowbbodyEnum.PAID_TYPE1, OsmShowbbodyEnum.PAID_TYPE2]
        ).count()
        showbbody_not_paid = await base_query.filter(osm_showbbody=OsmShowbbodyEnum.NOT_PAID).count()
        showbbody_pending = await base_query.filter(osm_showbbody=OsmShowbbodyEnum.PENDING).count()
        no_showbbody_status = osm_count - showbbody_paid - showbbody_not_paid - showbbody_pending

        return DashboardSummaryDTO(
            year_buddhist=year_buddhist,
            province_code=province_code,
            province_name_th=getattr(province, "province_name_th", None),
            province_name_en=getattr(province, "province_name_en", None),
            district_code=subdistrict.district_id,
            district_name_th=getattr(district, "district_name_th", None),
            district_name_en=getattr(district, "district_name_en", None),
            subdistrict_code=subdistrict.subdistrict_code,
            subdistrict_name_th=subdistrict.subdistrict_name_th,
            subdistrict_name_en=subdistrict.subdistrict_name_en,
            level=GEO_LEVEL_SUBDISTRICT,
            district_count=1,
            subdistrict_count=1,
            village_count=village_count,
            community_count=0,
            pcu_count=pcu_count,
            hosp_satang_count=hosp_rpst_count,
            hosp_general_count=hosp_general_count,
            quota=int(province_quota or 0),
            osm_count=osm_count,
            osm_allowance_eligible_count=allowance_count,
            osm_training_budget_count=0,
            osm_payment_training_count=0,
            osm_showbbody_paid_count=showbbody_paid,
            osm_showbbody_not_paid_count=showbbody_not_paid,
            osm_showbbody_pending_count=showbbody_pending,
            osm_no_showbbody_status_count=no_showbbody_status,
        )

    @classmethod
    async def _count_health_services(
        cls,
        *,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        type_names: set[str],
    ) -> int:
        if not type_names:
            return 0

        query = cls._health_service_query(
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
        )
        return await query.filter(
            health_service_type__health_service_type_name_th__in=tuple(type_names)
        ).count()

    @staticmethod
    def _health_service_query(
        *,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
    ):
        query = HealthService.filter()
        if province_code:
            query = query.filter(province_id=province_code)
        if district_code:
            query = query.filter(district_id=district_code)
        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)
        return query

    @staticmethod
    def _osm_base_query(
        *,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
    ):
        """Base query สำหรับ อสม. ที่ active (ไม่ลาออก/เสียชีวิต/พ้นสภาพ) และไม่ถูกลบ"""
        query = OSMProfile.filter(
            Q(osm_status__isnull=True) | Q(osm_status=""),
            deleted_at=None,
        )
        if province_code:
            query = query.filter(province_id=province_code)
        if district_code:
            query = query.filter(district_id=district_code)
        if subdistrict_code:
            query = query.filter(subdistrict_id=subdistrict_code)
        return query

    @staticmethod
    def _accumulate(target: DashboardSummaryDTO, source: DashboardSummaryDTO) -> None:
        target.district_count += source.district_count
        target.subdistrict_count += source.subdistrict_count
        target.village_count += source.village_count
        target.community_count += source.community_count
        target.pcu_count += source.pcu_count
        target.hosp_satang_count += source.hosp_satang_count
        target.hosp_general_count += source.hosp_general_count
        target.quota += source.quota
        target.osm_count += source.osm_count
        target.osm_allowance_eligible_count += source.osm_allowance_eligible_count
        target.osm_training_budget_count += source.osm_training_budget_count
        target.osm_payment_training_count += source.osm_payment_training_count
        target.osm_showbbody_paid_count += source.osm_showbbody_paid_count
        target.osm_showbbody_not_paid_count += source.osm_showbbody_not_paid_count
        target.osm_showbbody_pending_count += source.osm_showbbody_pending_count
        target.osm_no_showbbody_status_count += source.osm_no_showbbody_status_count


class DashboardSummaryService:
    """Facade for dashboard summary retrieval and aggregation."""

    @staticmethod
    def current_buddhist_year() -> int:
        return DashboardSummaryAggregator.current_buddhist_year()

    @classmethod
    async def list_summary(
        cls,
        *,
        year_buddhist: Optional[int] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        district_codes: Optional[Sequence[str]] = None,
        subdistrict_code: Optional[str] = None,
        subdistrict_codes: Optional[Sequence[str]] = None,
        refresh_if_missing: bool = True,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        current_year = cls.current_buddhist_year()
        target_year = year_buddhist or current_year
        allow_auto_refresh = target_year == current_year
        district_code_values = cls._merge_code_inputs(district_code, district_codes)
        subdistrict_code_values = cls._merge_code_inputs(subdistrict_code, subdistrict_codes)
        single_district_code = district_code_values[0] if len(district_code_values) == 1 else None
        multi_district_codes = district_code_values if len(district_code_values) > 1 else None
        single_subdistrict_code = subdistrict_code_values[0] if len(subdistrict_code_values) == 1 else None
        multi_subdistrict_codes = subdistrict_code_values if len(subdistrict_code_values) > 1 else None
        level = resolve_geo_level(
            district_code=single_district_code,
            district_codes=multi_district_codes,
            subdistrict_code=single_subdistrict_code,
            subdistrict_codes=multi_subdistrict_codes,
        )
        records = await DashboardSummaryRepository.list_summaries(
            year_buddhist=target_year,
            level=level,
            province_code=province_code,
            district_code=single_district_code,
            district_codes=multi_district_codes,
            subdistrict_code=single_subdistrict_code,
            subdistrict_codes=multi_subdistrict_codes,
        )

        multi_filters_requested = bool(multi_district_codes) or bool(multi_subdistrict_codes)

        if refresh_if_missing and allow_auto_refresh and not multi_filters_requested and not records:
            await DashboardSummaryAggregator.recalculate(
                year_buddhist=target_year,
                level=level,
                province_code=province_code,
                district_code=single_district_code,
                subdistrict_code=single_subdistrict_code,
            )
            records = await DashboardSummaryRepository.list_summaries(
                year_buddhist=target_year,
                level=level,
                province_code=province_code,
                district_code=single_district_code,
                district_codes=multi_district_codes,
                subdistrict_code=single_subdistrict_code,
                subdistrict_codes=multi_subdistrict_codes,
            )
        elif refresh_if_missing and allow_auto_refresh and multi_district_codes and not records:
            # Auto-refresh missing multiple districts for current year
            for code in multi_district_codes:
                await DashboardSummaryAggregator.recalculate(
                    year_buddhist=target_year,
                    level=level,
                    province_code=province_code,
                    district_code=code,
                    subdistrict_code=None,
                )
            records = await DashboardSummaryRepository.list_summaries(
                year_buddhist=target_year,
                level=level,
                province_code=province_code,
                district_code=None,
                district_codes=multi_district_codes,
                subdistrict_code=None,
                subdistrict_codes=None,
            )
        elif refresh_if_missing and allow_auto_refresh and multi_subdistrict_codes and not records:
            # Auto-refresh missing multiple subdistricts for current year
            for code in multi_subdistrict_codes:
                await DashboardSummaryAggregator.recalculate(
                    year_buddhist=target_year,
                    level=level,
                    province_code=province_code,
                    district_code=None,
                    subdistrict_code=code,
                )
            records = await DashboardSummaryRepository.list_summaries(
                year_buddhist=target_year,
                level=level,
                province_code=province_code,
                district_code=None,
                district_codes=None,
                subdistrict_code=None,
                subdistrict_codes=multi_subdistrict_codes,
            )

        records = cls._order_records(records, level, province_code)
        filtered_records = cls._filter_records(records, search)
        return [cls._serialize(record) for record in filtered_records]

    @classmethod
    async def refresh_summary(
        cls,
        *,
        year_buddhist: Optional[int] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
    ) -> int:
        target_year = year_buddhist or cls.current_buddhist_year()
        target_year = cls._ensure_current_year(target_year)
        level = resolve_geo_level(
            district_code=district_code,
            subdistrict_code=subdistrict_code,
        )
        await DashboardSummaryAggregator.recalculate(
            year_buddhist=target_year,
            level=level,
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
        )
        return target_year

    @staticmethod
    def _serialize(record) -> Dict[str, Any]:
        return {
            "level": getattr(record, "geography_level", GEO_LEVEL_PROVINCE),
            "year": record.year_buddhist,
            "provinceCode": record.province_code,
            "provinceNameTh": record.province_name_th,
            "provinceNameEn": record.province_name_en,
            "districtCode": getattr(record, "district_code", None),
            "districtNameTh": getattr(record, "district_name_th", None),
            "districtNameEn": getattr(record, "district_name_en", None),
            "subdistrictCode": getattr(record, "subdistrict_code", None),
            "subdistrictNameTh": getattr(record, "subdistrict_name_th", None),
            "subdistrictNameEn": getattr(record, "subdistrict_name_en", None),
            "districtCount": record.district_count,
            "subdistrictCount": record.subdistrict_count,
            "villageCount": record.village_count,
            "communityCount": record.community_count,
            "pcuCount": record.pcu_count,
            "rpsCount": record.hosp_satang_count,
            "rptCount": record.hosp_general_count,
            "quota": record.quota,
            "osmCount": record.osm_count,
            "osmAllowanceEligibleCount": record.osm_allowance_eligible_count,
            "osmTrainingBudgetCount": record.osm_training_budget_count,
            "osmPaymentTrainingCount": record.osm_payment_training_count,
            "osmShowbbodyPaidCount": record.osm_showbbody_paid_count,
            "osmShowbbodyNotPaidCount": record.osm_showbbody_not_paid_count,
            "osmShowbbodyPendingCount": record.osm_showbbody_pending_count,
            "osmNoShowbbodyStatusCount": record.osm_no_showbbody_status_count,
            "lastCalculatedAt": record.last_calculated_at.isoformat() if record.last_calculated_at else None,
            "updatedAt": record.updated_at.isoformat() if record.updated_at else None,
        }

    @staticmethod
    def _order_records(records, level: str, province_code: Optional[str]):
        if level == GEO_LEVEL_PROVINCE and province_code is None:
            return sorted(records, key=lambda record: (record.province_code is None, record.province_code or ""))
        return records

    @staticmethod
    def _filter_records(records, search: Optional[str]):
        if not search:
            return records

        keyword = search.strip().lower()
        if not keyword:
            return records

        filtered = []
        for record in records:
            code = (record.province_code or "").lower()
            name_th = (record.province_name_th or "").lower()
            name_en = (record.province_name_en or "").lower()
            district_code = (getattr(record, "district_code", "") or "").lower()
            district_name_th = (getattr(record, "district_name_th", "") or "").lower()
            district_name_en = (getattr(record, "district_name_en", "") or "").lower()
            subdistrict_code = (getattr(record, "subdistrict_code", "") or "").lower()
            subdistrict_name_th = (getattr(record, "subdistrict_name_th", "") or "").lower()
            subdistrict_name_en = (getattr(record, "subdistrict_name_en", "") or "").lower()

            if keyword in code or keyword in name_th or keyword in name_en:
                filtered.append(record)
                continue

            if keyword in district_code or keyword in district_name_th or keyword in district_name_en:
                filtered.append(record)
                continue

            if keyword in subdistrict_code or keyword in subdistrict_name_th or keyword in subdistrict_name_en:
                filtered.append(record)

        return filtered

    @staticmethod
    def _ensure_current_year(target_year: int) -> int:
        current_year = DashboardSummaryAggregator.current_buddhist_year()
        if target_year != current_year:
            raise ValueError(
                "Refresh operations are limited to the current Buddhist year. Please run data pipeline jobs for historical adjustments.",
            )
        return target_year

    @staticmethod
    def _merge_code_inputs(
        singular: Optional[str],
        multiple: Optional[Sequence[str]],
    ) -> List[str]:
        merged: List[str] = []
        seen: set[str] = set()

        def _add(value: Optional[str]) -> None:
            token = (value or "").strip()
            if not token or token in seen:
                return
            merged.append(token)
            seen.add(token)

        _add(singular)
        if multiple:
            for raw in multiple:
                _add(raw)

        return merged
