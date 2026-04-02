from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional, Sequence

from app.models.dashboard_model import DashboardAnnualSummary


class DashboardSummaryRepository:
    """Data access layer for dashboard summary snapshots."""

    @staticmethod
    async def list_summaries(
        *,
        year_buddhist: Optional[int] = None,
        level: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        district_codes: Optional[Sequence[str]] = None,
        subdistrict_code: Optional[str] = None,
        subdistrict_codes: Optional[Sequence[str]] = None,
    ) -> List[DashboardAnnualSummary]:
        query = DashboardAnnualSummary.all().order_by(
            "geography_level",
            "province_code",
            "district_code",
            "subdistrict_code",
        )

        if year_buddhist is not None:
            query = query.filter(year_buddhist=year_buddhist)

        if level is not None:
            query = query.filter(geography_level=level)

        if province_code is not None:
            query = query.filter(province_code=province_code)

        normalized_district_codes = DashboardSummaryRepository._sanitize_code_list(district_codes)
        if normalized_district_codes:
            query = query.filter(district_code__in=normalized_district_codes)
        elif district_code is not None:
            query = query.filter(district_code=district_code)

        normalized_subdistrict_codes = DashboardSummaryRepository._sanitize_code_list(subdistrict_codes)
        if normalized_subdistrict_codes:
            query = query.filter(subdistrict_code__in=normalized_subdistrict_codes)
        elif subdistrict_code is not None:
            query = query.filter(subdistrict_code=subdistrict_code)

        return await query

    @staticmethod
    async def upsert_summary(
        *,
        year_buddhist: int,
        geography_level: str,
        province_code: Optional[str],
        district_code: Optional[str],
        subdistrict_code: Optional[str],
        payload: dict,
    ) -> DashboardAnnualSummary:
        defaults = {**payload}
        defaults.setdefault("last_calculated_at", datetime.utcnow())

        summary, created = await DashboardAnnualSummary.get_or_create(
            year_buddhist=year_buddhist,
            geography_level=geography_level,
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
            defaults=defaults,
        )

        if created:
            return summary

        for field, value in defaults.items():
            setattr(summary, field, value)

        await summary.save(update_fields=list(defaults.keys()) + ["updated_at"])
        return summary

    @staticmethod
    async def delete_year(year_buddhist: int) -> int:
        deleted = await DashboardAnnualSummary.filter(year_buddhist=year_buddhist).delete()
        return deleted

    @staticmethod
    async def list_years() -> Iterable[int]:
        records = await DashboardAnnualSummary.all().order_by("year_buddhist").values_list("year_buddhist", flat=True)
        return list(dict.fromkeys(records))

    @staticmethod
    def _sanitize_code_list(values: Optional[Sequence[str]]) -> List[str]:
        if not values:
            return []
        sanitized: List[str] = []
        seen: set[str] = set()
        for raw in values:
            token = (raw or "").strip()
            if not token or token in seen:
                continue
            sanitized.append(token)
            seen.add(token)
        return sanitized
