from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from tortoise import connections
from tortoise.queryset import QuerySet

from app.api.v1.schemas.report_standard_schema import (
    FamilyAddressReportItem,
    FamilyAddressReportQuery,
    FamilyAddressReportResponse,
    AverageAgeReportItem,
    AverageAgeReportQuery,
    AverageAgeReportResponse,
    NewVolunteerByYearItem,
    NewVolunteerByYearQuery,
    NewVolunteerByYearResponse,
    VolunteerTenureItem,
    VolunteerTenureQuery,
    VolunteerTenureResponse,
    BenefitClaimItem,
    BenefitClaimQuery,
    BenefitClaimResponse,
    QualifiedBenefitItem,
    QualifiedBenefitQuery,
    QualifiedBenefitResponse,
    ResignedVolunteerItem,
    ResignedVolunteerQuery,
    ResignedVolunteerResponse,
    ResignedReportItem,
    ResignedReportQuery,
    ResignedReportResponse,
    PositionsByVillageItem,
    PositionsByVillageQuery,
    PositionsByVillageResponse,
    PresidentListItem,
    PresidentListQuery,
    PresidentListResponse,
    PresidentByLevelItem,
    PresidentByLevelQuery,
    PresidentByLevelResponse,
    AwardByAreaItem,
    AwardByAreaQuery,
    AwardByAreaResponse,
    TrainingByAreaItem,
    TrainingByAreaQuery,
    TrainingByAreaResponse,
    SpecialtyByAreaItem,
    SpecialtyByAreaQuery,
    SpecialtyByAreaResponse,
    StandardGenderReportItem,
    StandardGenderReportQuery,
    StandardGenderReportResponse,
    StandardGenderSnapshotCreateRequest,
    StandardGenderSnapshotItem,
    StandardGenderSnapshotQuery,
    StandardGenderSnapshotResponse,
    SnapshotMutationResponse,
)
from app.models.report_model import OsmGenderSummary


class StandardReportService:
    """Service layer for production-grade reporting endpoints."""
    # ------------------------------------------------------------------
    # Qualified benefit (ค่าป่วยการ) report
    # ------------------------------------------------------------------

    @staticmethod
    async def qualified_benefit(filters: QualifiedBenefitQuery) -> QualifiedBenefitResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = ["op.deleted_at IS NULL", "(op.osm_status IS NULL OR op.osm_status = '')"]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)
        if filters.status:
            add_filter("opc.allowance_confirmation_status =", filters.status)
        if filters.showbbody_status:
            add_filter("op.osm_showbbody =", filters.showbbody_status)
        if filters.year_from:
            add_filter("op.allowance_year >=", filters.year_from)
        if filters.year_to:
            add_filter("op.allowance_year <=", filters.year_to)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            op.id,
            op.citizen_id,
            op.first_name,
            op.last_name,
            opc.allowance_confirmation_status::text AS allowance_status,
            op.osm_showbbody::text AS showbbody_status,
            op.allowance_year,
            op.allowance_months,
            op.is_allowance_supported,
            op.volunteer_status::text AS volunteer_status,
            op.approval_status::text AS approval_status,
            op.province_id AS province_code,
            p.province_name_th AS province_name,
            op.district_id AS district_code,
            d.district_name_th AS district_name,
            op.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            op.village_code::text AS village_code,
            COALESCE(v.village_no::text, op.village_no::text) AS village_no,
            COALESCE(v.village_name_th, op.village_name) AS village_name
        FROM osm_profiles op
        LEFT JOIN osm_position_confirmations opc ON opc.osm_profile_id = op.id AND opc.deleted_at IS NULL
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        LEFT JOIN villages v ON v.village_code::text = op.village_code::text AND v.deleted_at IS NULL
        {where_sql}
        ORDER BY op.allowance_year DESC NULLS LAST, op.updated_at DESC
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_profiles op
        LEFT JOIN osm_position_confirmations opc ON opc.osm_profile_id = op.id AND opc.deleted_at IS NULL
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            QualifiedBenefitItem(
                id=str(row.get("id")),
                citizen_id=row.get("citizen_id"),
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                allowance_status=row.get("allowance_status"),
                showbbody_status=row.get("showbbody_status"),
                allowance_year=row.get("allowance_year"),
                allowance_months=row.get("allowance_months"),
                is_allowance_supported=row.get("is_allowance_supported"),
                volunteer_status=row.get("volunteer_status"),
                approval_status=row.get("approval_status"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                village_code=row.get("village_code"),
                village_no=row.get("village_no"),
                village_name=row.get("village_name"),
            )
            for row in rows
        ]

        return QualifiedBenefitResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Volunteer tenure (allAndDurationList)
    # ------------------------------------------------------------------

    @staticmethod
    async def volunteer_tenure(filters: VolunteerTenureQuery) -> VolunteerTenureResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = ["op.deleted_at IS NULL"]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)
        if getattr(filters, "village_code", None):
            add_filter("op.village_code::text =", str(filters.village_code))
        if filters.osm_status is not None:
            add_filter("op.osm_status =", filters.osm_status)
        else:
            # default: นับเฉพาะ อสม. สถานะปกติ (osm_status IS NULL หรือ '')
            clauses.append("(op.osm_status IS NULL OR op.osm_status::text = '')")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        tenure_years_expr = """
        CASE
            WHEN op.osm_year IS NULL THEN NULL
            ELSE GREATEST(
                0,
                (
                    (COALESCE(EXTRACT(YEAR FROM op.retirement_date), EXTRACT(YEAR FROM CURRENT_DATE))::int + 543)
                    - op.osm_year::int
                )
            )::int
        END
        """

        list_sql = f"""
        SELECT
            op.id,
            op.citizen_id,
            op.osm_code,
            op.first_name,
            op.last_name,
            op.osm_year,
            op.approval_date,
            op.retirement_date,
            op.retirement_reason::text AS retirement_reason,
            op.osm_status::text AS osm_status,
            op.province_id AS province_code,
            p.province_name_th AS province_name,
            op.district_id AS district_code,
            d.district_name_th AS district_name,
            op.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            op.village_code::text AS village_code,
            COALESCE(v.village_no::text, op.village_no::text) AS village_no,
            COALESCE(v.village_name_th::text, op.village_name::text) AS village_name,
            op.osm_year::int AS start_year,
            {tenure_years_expr} AS tenure_years
        FROM osm_profiles op
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        LEFT JOIN villages v ON v.village_code::text = op.village_code::text
        {where_sql}
        ORDER BY tenure_years DESC NULLS LAST, op.created_at DESC
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_profiles op
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            VolunteerTenureItem(
                id=str(row.get("id")),
                citizen_id=row.get("citizen_id"),
                osm_code=row.get("osm_code"),
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                osm_year=row.get("osm_year"),
                approval_date=str(row.get("approval_date")) if row.get("approval_date") else None,
                retirement_date=str(row.get("retirement_date")) if row.get("retirement_date") else None,
                retirement_reason=row.get("retirement_reason"),
                osm_status=row.get("osm_status"),
                start_year=row.get("start_year"),
                tenure_years=row.get("tenure_years"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                village_code=row.get("village_code"),
                village_no=row.get("village_no"),
                village_name=row.get("village_name"),
            )
            for row in rows
        ]

        return VolunteerTenureResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Benefit claim list
    # ------------------------------------------------------------------

    @staticmethod
    async def benefit_claim_list(filters: BenefitClaimQuery) -> BenefitClaimResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        # Report is primarily driven by osm_profiles.osm_showbbody (benefit eligibility).
        # We also include the latest claim record when it exists.
        clauses: List[str] = [
            "op.deleted_at IS NULL",
            "op.osm_showbbody IS NOT NULL",
            # default: นับเฉพาะ อสม. สถานะปกติ
            "(op.osm_status IS NULL OR op.osm_status::text = '')",
        ]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)
        if getattr(filters, "village_code", None):
            add_filter("op.village_code::text =", str(filters.village_code))
        if getattr(filters, "osm_showbbody", None):
            add_filter("op.osm_showbbody =", filters.osm_showbbody)
        # Claim-related filters (only apply when caller wants to filter by claim fields)
        if filters.status:
            add_filter("bc.status =", filters.status)
        if filters.claim_type:
            # IMPORTANT:
            # - For this report, "eligibility for 2,000" is derived from osm_showbbody (1/2).
            # - Many records may not have a claim row yet (bc is NULL due to LEFT JOIN).
            # If the client sends claimType=2000, treat it as "eligible 2,000" (showbbody 1/2)
            # instead of requiring bc.claim_type to match (which would filter out all NULL-claim rows).
            if str(filters.claim_type) == "2000":
                clauses.append("op.osm_showbbody::text IN ('1','2')")
            else:
                add_filter("bc.claim_type =", filters.claim_type)
        if filters.date_from:
            add_filter("bc.claim_date >=", filters.date_from)
        if filters.date_to:
            add_filter("bc.claim_date <=", filters.date_to)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            bc.id AS claim_id,
            op.id AS osm_profile_id,
            bc.claim_type,
            bc.claim_date,
            bc.claim_round,
            bc.amount,
            bc.status,
            bc.decision_date,
            bc.paid_date,
            op.citizen_id,
            op.osm_code,
            op.first_name,
            op.last_name,
            op.approval_date,
            op.allowance_year,
            op.osm_showbbody::text AS osm_showbbody,
            CASE
                WHEN op.osm_showbbody::text IN ('1', '2') THEN 'eligible'
                WHEN op.osm_showbbody::text = '5' THEN 'ineligible'
                WHEN op.osm_showbbody::text = '6' THEN 'pending'
                ELSE NULL
            END AS benefit_status,
            op.province_id AS province_code,
            p.province_name_th AS province_name,
            op.district_id AS district_code,
            d.district_name_th AS district_name,
            op.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            op.village_code::text AS village_code,
            COALESCE(v.village_no::text, op.village_no::text) AS village_no,
            COALESCE(v.village_name_th::text, op.village_name::text) AS village_name
        FROM osm_profiles op
        LEFT JOIN LATERAL (
            SELECT bc.*
            FROM osm_benefit_claims bc
            WHERE bc.osm_profile_id = op.id AND bc.deleted_at IS NULL
            ORDER BY bc.claim_date DESC NULLS LAST, bc.created_at DESC NULLS LAST
            LIMIT 1
        ) bc ON true
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        LEFT JOIN villages v ON v.village_code::text = op.village_code::text
        {where_sql}
        ORDER BY bc.claim_date DESC NULLS LAST, bc.created_at DESC NULLS LAST, op.created_at DESC
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_profiles op
        LEFT JOIN LATERAL (
            SELECT bc.*
            FROM osm_benefit_claims bc
            WHERE bc.osm_profile_id = op.id AND bc.deleted_at IS NULL
            ORDER BY bc.claim_date DESC NULLS LAST, bc.created_at DESC NULLS LAST
            LIMIT 1
        ) bc ON true
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            BenefitClaimItem(
                claim_id=str(row.get("claim_id")) if row.get("claim_id") else None,
                osm_profile_id=str(row.get("osm_profile_id")),
                citizen_id=row.get("citizen_id"),
                osm_code=row.get("osm_code"),
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                approval_date=str(row.get("approval_date")) if row.get("approval_date") else None,
                allowance_year=row.get("allowance_year"),
                osm_showbbody=row.get("osm_showbbody"),
                benefit_status=row.get("benefit_status"),
                claim_type=row.get("claim_type") if row.get("claim_type") is not None else "",
                claim_date=str(row.get("claim_date")) if row.get("claim_date") else "",
                claim_round=row.get("claim_round"),
                amount=float(row.get("amount")) if row.get("amount") is not None else None,
                status=row.get("status") or "",
                decision_date=str(row.get("decision_date")) if row.get("decision_date") else None,
                paid_date=str(row.get("paid_date")) if row.get("paid_date") else None,
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                village_code=row.get("village_code"),
                village_no=row.get("village_no"),
                village_name=row.get("village_name"),
            )
            for row in rows
        ]

        return BenefitClaimResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Resigned volunteers report
    # ------------------------------------------------------------------

    @staticmethod
    async def resigned_volunteers(filters: ResignedVolunteerQuery) -> ResignedVolunteerResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = ["op.deleted_at IS NULL", "op.retirement_date IS NOT NULL"]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)
        if filters.osm_status is not None:
            add_filter("op.osm_status =", filters.osm_status)
        else:
            # resigned report defaults to non-active statuses
            clauses.append("op.osm_status IS NOT NULL")
        if filters.reason:
            add_filter("op.retirement_reason =", filters.reason)
        if filters.year_from:
            add_filter("EXTRACT(YEAR FROM op.retirement_date) >=", filters.year_from)
        if filters.year_to:
            add_filter("EXTRACT(YEAR FROM op.retirement_date) <=", filters.year_to)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            op.id,
            op.citizen_id,
            op.first_name,
            op.last_name,
            op.retirement_date,
            op.retirement_reason::text AS retirement_reason,
            op.osm_status::text AS osm_status,
            op.volunteer_status::text AS volunteer_status,
            op.approval_status::text AS approval_status,
            op.province_id AS province_code,
            p.province_name_th AS province_name,
            op.district_id AS district_code,
            d.district_name_th AS district_name,
            op.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            op.village_code::text AS village_code,
            COALESCE(v.village_no::text, op.village_no::text) AS village_no,
            COALESCE(v.village_name_th, op.village_name) AS village_name
        FROM osm_profiles op
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        LEFT JOIN villages v ON v.village_code::text = op.village_code::text AND v.deleted_at IS NULL
        {where_sql}
        ORDER BY op.retirement_date DESC NULLS LAST, op.updated_at DESC
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_profiles op
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            ResignedVolunteerItem(
                id=str(row.get("id")),
                citizen_id=row.get("citizen_id"),
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                retirement_date=row.get("retirement_date").isoformat() if row.get("retirement_date") else None,
                retirement_reason=row.get("retirement_reason"),
                osm_status=row.get("osm_status"),
                volunteer_status=row.get("volunteer_status"),
                approval_status=row.get("approval_status"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                village_code=row.get("village_code"),
                village_no=row.get("village_no"),
                village_name=row.get("village_name"),
            )
            for row in rows
        ]

        return ResignedVolunteerResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Resigned report (summary / aggregate by geography + reason)
    # ------------------------------------------------------------------

    @staticmethod
    async def resigned_report(filters: "ResignedReportQuery") -> "ResignedReportResponse":
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = ["op.deleted_at IS NULL", "op.retirement_date IS NOT NULL", "op.osm_status IS NOT NULL"]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)
        if filters.reason:
            add_filter("op.retirement_reason =", filters.reason)
        if filters.year_from:
            add_filter("EXTRACT(YEAR FROM op.retirement_date) >=", filters.year_from)
        if filters.year_to:
            add_filter("EXTRACT(YEAR FROM op.retirement_date) <=", filters.year_to)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            op.province_id AS province_code,
            p.province_name_th AS province_name,
            op.district_id AS district_code,
            d.district_name_th AS district_name,
            op.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            op.retirement_reason::text AS retirement_reason,
            COUNT(*) AS total_resigned
        FROM osm_profiles op
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        {where_sql}
        GROUP BY
            op.province_id,
            p.province_name_th,
            op.district_id,
            d.district_name_th,
            op.subdistrict_id,
            s.subdistrict_name_th,
            op.retirement_reason
        ORDER BY p.province_name_th NULLS LAST, d.district_name_th NULLS LAST, s.subdistrict_name_th NULLS LAST, op.retirement_reason NULLS LAST
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total FROM (
            SELECT 1
            FROM osm_profiles op
            LEFT JOIN provinces p ON p.province_code = op.province_id
            LEFT JOIN districts d ON d.district_code = op.district_id
            LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
            {where_sql}
            GROUP BY
                op.province_id,
                p.province_name_th,
                op.district_id,
                d.district_name_th,
                op.subdistrict_id,
                s.subdistrict_name_th,
                op.retirement_reason
        ) grouped
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            ResignedReportItem(
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                retirement_reason=row.get("retirement_reason"),
                total_resigned=row.get("total_resigned", 0),
            )
            for row in rows
        ]

        return ResignedReportResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Positions by village (count positions per village)
    # ------------------------------------------------------------------

    @staticmethod
    async def positions_by_village(filters: PositionsByVillageQuery) -> PositionsByVillageResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        # WHERE clauses applied to the geography / position base tables
        geo_clauses: List[str] = ["s.deleted_at IS NULL", "po.is_active = TRUE"]
        # Extra conditions pushed into the LEFT JOIN on osm_profiles
        osm_join_conditions: List[str] = ["op.deleted_at IS NULL", "(op.osm_status IS NULL OR op.osm_status = '')"]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            geo_clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("p.province_code =", filters.province_code)
        if filters.district_code:
            add_filter("d.district_code =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("s.subdistrict_code =", filters.subdistrict_code)

        where_sql = f"WHERE {' AND '.join(geo_clauses)}" if geo_clauses else ""
        osm_join_sql = " AND ".join(osm_join_conditions)

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            NULLIF(op.village_code, '') AS village_code,
            v.village_no::text AS village_no,
            v.village_name_th AS village_name,
            s.subdistrict_code AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            d.district_code AS district_code,
            d.district_name_th AS district_name,
            p.province_code AS province_code,
            p.province_name_th AS province_name,
            po.position_name_th AS position_name,
            COUNT(opp.id) AS count
        FROM subdistricts s
        INNER JOIN districts d ON d.district_code = s.district_id
        INNER JOIN provinces p ON p.province_code = d.province_id
        CROSS JOIN osm_official_positions po
        LEFT JOIN osm_profiles op
            ON op.subdistrict_id = s.subdistrict_code
            AND {osm_join_sql}
        LEFT JOIN osm_profile_official_positions opp
            ON opp.osm_profile_id = op.id
            AND opp.official_position_id = po.id
            AND opp.deleted_at IS NULL
        LEFT JOIN villages v
            ON v.village_code = NULLIF(op.village_code, '')
            AND v.deleted_at IS NULL
        {where_sql}
        GROUP BY
            NULLIF(op.village_code, ''),
            v.village_no,
            v.village_name_th,
            s.subdistrict_code,
            s.subdistrict_name_th,
            d.district_code,
            d.district_name_th,
            p.province_code,
            p.province_name_th,
            po.position_name_th
        ORDER BY p.province_code NULLS LAST, d.district_code NULLS LAST, s.subdistrict_code NULLS LAST, NULLIF(op.village_code, '') NULLS LAST, po.position_name_th
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total FROM (
            SELECT 1
            FROM subdistricts s
            INNER JOIN districts d ON d.district_code = s.district_id
            INNER JOIN provinces p ON p.province_code = d.province_id
            CROSS JOIN osm_official_positions po
            {where_sql}
            GROUP BY s.subdistrict_code, d.district_code, p.province_code, po.position_name_th
        ) grouped
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            PositionsByVillageItem(
                village_code=row.get("village_code"),
                village_no=str(row["village_no"]) if row.get("village_no") is not None else None,
                village_name=row.get("village_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                position_name=row.get("position_name"),
                count=row.get("count", 0),
            )
            for row in rows
        ]

        return PositionsByVillageResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # President by level/list
    # ------------------------------------------------------------------

    @staticmethod
    async def president_by_level(filters: PresidentByLevelQuery) -> PresidentByLevelResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = [
            "op.deleted_at IS NULL",
            "(op.osm_status IS NULL OR op.osm_status = '')",
            "opp.deleted_at IS NULL",
            "o.deleted_at IS NULL",
            "o.is_active = TRUE",
        ]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.position_level:
            add_filter("o.position_level =", filters.position_level)
        if filters.area_name:
            add_filter("COALESCE(op.village_name, s.subdistrict_name_th, d.district_name_th, p.province_name_th) ILIKE", f"%{filters.area_name}%")
        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            op.first_name,
            op.last_name,
            o.position_name_th AS position_name,
            o.position_level::text AS position_level,
            COALESCE(op.village_name, s.subdistrict_name_th, d.district_name_th, p.province_name_th) AS area_name,
            p.province_code AS province_code,
            p.province_name_th AS province_name,
            d.district_code AS district_code,
            d.district_name_th AS district_name,
            s.subdistrict_code AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name
        FROM osm_profile_official_positions opp
        INNER JOIN osm_profiles op ON op.id = opp.osm_profile_id
        INNER JOIN osm_official_positions o ON o.id = opp.official_position_id
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        {where_sql}
        ORDER BY o.position_level NULLS LAST, o.position_name_th, p.province_name_th, d.district_name_th, s.subdistrict_name_th, op.first_name, op.last_name
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_profile_official_positions opp
        INNER JOIN osm_profiles op ON op.id = opp.osm_profile_id
        INNER JOIN osm_official_positions o ON o.id = opp.official_position_id
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            PresidentByLevelItem(
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                position_name=row.get("position_name"),
                position_level=row.get("position_level"),
                area_name=row.get("area_name"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
            )
            for row in rows
        ]

        return PresidentByLevelResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # President list (ตำแหน่งที่มีคำว่า ประธาน)
    # ------------------------------------------------------------------

    @staticmethod
    async def president_list(filters: PresidentListQuery) -> PresidentListResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = [
            "op.deleted_at IS NULL",
            "(op.osm_status IS NULL OR op.osm_status = '')",
            "opp.deleted_at IS NULL",
            "o.deleted_at IS NULL",
            "o.is_active = TRUE",
            "o.position_name_th ILIKE '%ประธาน%'",
        ]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.area_name:
            add_filter("COALESCE(op.village_name, s.subdistrict_name_th, d.district_name_th, p.province_name_th) ILIKE", f"%{filters.area_name}%")
        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            op.first_name,
            op.last_name,
            o.position_name_th AS position_name,
            o.position_level::text AS position_level,
            COALESCE(op.village_name, s.subdistrict_name_th, d.district_name_th, p.province_name_th) AS area_name,
            p.province_code AS province_code,
            p.province_name_th AS province_name,
            d.district_code AS district_code,
            d.district_name_th AS district_name,
            s.subdistrict_code AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name
        FROM osm_profile_official_positions opp
        INNER JOIN osm_profiles op ON op.id = opp.osm_profile_id
        INNER JOIN osm_official_positions o ON o.id = opp.official_position_id
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        {where_sql}
        ORDER BY o.position_level NULLS LAST, o.position_name_th, p.province_name_th, d.district_name_th, s.subdistrict_name_th, op.first_name, op.last_name
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_profile_official_positions opp
        INNER JOIN osm_profiles op ON op.id = opp.osm_profile_id
        INNER JOIN osm_official_positions o ON o.id = opp.official_position_id
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            PresidentListItem(
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                position_name=row.get("position_name"),
                position_level=row.get("position_level"),
                area_name=row.get("area_name"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
            )
            for row in rows
        ]

        return PresidentListResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Awards / confirmed by area
    # ------------------------------------------------------------------

    @staticmethod
    async def awards_by_area(filters: AwardByAreaQuery) -> AwardByAreaResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = ["aw.deleted_at IS NULL", "op.deleted_at IS NULL", "(op.osm_status IS NULL OR op.osm_status = '')"]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.award_type:
            add_filter("aw.award_type =", filters.award_type)
        if filters.date_from:
            add_filter("aw.awarded_date >=", filters.date_from)
        if filters.date_to:
            add_filter("aw.awarded_date <=", filters.date_to)
        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            aw.id AS award_id,
            aw.osm_profile_id,
            aw.award_type,
            aw.award_name,
            aw.award_code,
            aw.awarded_date,
            op.first_name,
            op.last_name,
            op.province_id AS province_code,
            p.province_name_th AS province_name,
            op.district_id AS district_code,
            d.district_name_th AS district_name,
            op.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name
        FROM osm_awards aw
        INNER JOIN osm_profiles op ON op.id = aw.osm_profile_id
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        {where_sql}
        ORDER BY aw.awarded_date DESC, aw.created_at DESC
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_awards aw
        INNER JOIN osm_profiles op ON op.id = aw.osm_profile_id
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            AwardByAreaItem(
                award_id=str(row.get("award_id")),
                osm_profile_id=str(row.get("osm_profile_id")),
                award_type=row.get("award_type"),
                award_name=row.get("award_name"),
                award_code=row.get("award_code"),
                awarded_date=str(row.get("awarded_date")) if row.get("awarded_date") else None,
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
            )
            for row in rows
        ]

        return AwardByAreaResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Training by area (group by course/year/area)
    # ------------------------------------------------------------------

    @staticmethod
    async def training_by_area(filters: TrainingByAreaQuery) -> TrainingByAreaResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        # Geography filter clauses (applied to the geography base)
        geo_clauses: List[str] = ["s.deleted_at IS NULL"]
        # OSM / training join conditions (pushed into LEFT JOIN)
        osm_conditions: List[str] = ["op.deleted_at IS NULL", "(op.osm_status IS NULL OR op.osm_status = '')", "opt.deleted_at IS NULL"]

        year_conditions: List[str] = []

        def add_geo_filter(condition: str, value: object) -> None:
            base_params.append(value)
            geo_clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_geo_filter("p.province_code =", filters.province_code)
        if filters.district_code:
            add_geo_filter("d.district_code =", filters.district_code)
        if filters.subdistrict_code:
            add_geo_filter("s.subdistrict_code =", filters.subdistrict_code)
        if filters.year_from:
            base_params.append(filters.year_from)
            year_conditions.append(f"opt.trained_year >= ${len(base_params)}")
        if filters.year_to:
            base_params.append(filters.year_to)
            year_conditions.append(f"opt.trained_year <= ${len(base_params)}")

        geo_where = f"WHERE {' AND '.join(geo_clauses)}" if geo_clauses else ""
        osm_join_extra = " AND ".join(osm_conditions + year_conditions) if (osm_conditions or year_conditions) else "TRUE"

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            p.province_code AS province_code,
            p.province_name_th AS province_name,
            d.district_code AS district_code,
            d.district_name_th AS district_name,
            s.subdistrict_code AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            tc.course_name_th AS course_name,
            opt.trained_year,
            COUNT(opt.id) AS count
        FROM subdistricts s
        INNER JOIN districts d ON d.district_code = s.district_id
        INNER JOIN provinces p ON p.province_code = d.province_id
        LEFT JOIN osm_profiles op
            ON op.subdistrict_id = s.subdistrict_code
            AND op.deleted_at IS NULL
            AND (op.osm_status IS NULL OR op.osm_status = '')
        LEFT JOIN osm_profile_trainings opt
            ON opt.osm_profile_id = op.id
            AND opt.deleted_at IS NULL
            {"AND " + " AND ".join(year_conditions) if year_conditions else ""}
        LEFT JOIN osm_training_courses tc ON tc.id = opt.training_course_id
        {geo_where}
        GROUP BY
            p.province_code,
            p.province_name_th,
            d.district_code,
            d.district_name_th,
            s.subdistrict_code,
            s.subdistrict_name_th,
            tc.course_name_th,
            opt.trained_year
        ORDER BY opt.trained_year DESC NULLS LAST, p.province_code, d.district_code, s.subdistrict_code, tc.course_name_th
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total FROM (
            SELECT 1
            FROM subdistricts s
            INNER JOIN districts d ON d.district_code = s.district_id
            INNER JOIN provinces p ON p.province_code = d.province_id
            LEFT JOIN osm_profiles op
                ON op.subdistrict_id = s.subdistrict_code
                AND op.deleted_at IS NULL
                AND (op.osm_status IS NULL OR op.osm_status = '')
            LEFT JOIN osm_profile_trainings opt
                ON opt.osm_profile_id = op.id
                AND opt.deleted_at IS NULL
                {"AND " + " AND ".join(year_conditions) if year_conditions else ""}
            LEFT JOIN osm_training_courses tc ON tc.id = opt.training_course_id
            {geo_where}
            GROUP BY p.province_code, d.district_code, s.subdistrict_code, opt.trained_year, opt.training_course_id
        ) grouped
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            TrainingByAreaItem(
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                course_name=row.get("course_name"),
                trained_year=row.get("trained_year"),
                count=row.get("count", 0),
            )
            for row in rows
        ]

        return TrainingByAreaResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Specialty by area (skill counts)
    # ------------------------------------------------------------------

    @staticmethod
    async def specialty_by_area(filters: SpecialtyByAreaQuery) -> SpecialtyByAreaResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        geo_clauses: List[str] = ["s.deleted_at IS NULL", "sk.is_active = TRUE"]
        osm_conditions: List[str] = ["op.deleted_at IS NULL", "(op.osm_status IS NULL OR op.osm_status = '')", "ops.deleted_at IS NULL"]

        def add_geo_filter(condition: str, value: object) -> None:
            base_params.append(value)
            geo_clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_geo_filter("p.province_code =", filters.province_code)
        if filters.district_code:
            add_geo_filter("d.district_code =", filters.district_code)
        if filters.subdistrict_code:
            add_geo_filter("s.subdistrict_code =", filters.subdistrict_code)

        geo_where = f"WHERE {' AND '.join(geo_clauses)}" if geo_clauses else ""
        osm_join_extra = " AND ".join(osm_conditions)

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            p.province_code AS province_code,
            p.province_name_th AS province_name,
            d.district_code AS district_code,
            d.district_name_th AS district_name,
            s.subdistrict_code AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            sk.skill_name_th AS skill_name,
            COUNT(ops.id) AS count
        FROM subdistricts s
        INNER JOIN districts d ON d.district_code = s.district_id
        INNER JOIN provinces p ON p.province_code = d.province_id
        CROSS JOIN osm_special_skills sk
        LEFT JOIN osm_profiles op
            ON op.subdistrict_id = s.subdistrict_code
            AND op.deleted_at IS NULL
            AND (op.osm_status IS NULL OR op.osm_status = '')
        LEFT JOIN osm_profile_special_skills ops
            ON ops.osm_profile_id = op.id
            AND ops.special_skill_id = sk.id
            AND ops.deleted_at IS NULL
        {geo_where}
        GROUP BY
            p.province_code,
            p.province_name_th,
            d.district_code,
            d.district_name_th,
            s.subdistrict_code,
            s.subdistrict_name_th,
            sk.skill_name_th
        ORDER BY p.province_code, d.district_code, s.subdistrict_code, sk.skill_name_th
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total FROM (
            SELECT 1
            FROM subdistricts s
            INNER JOIN districts d ON d.district_code = s.district_id
            INNER JOIN provinces p ON p.province_code = d.province_id
            CROSS JOIN osm_special_skills sk
            {geo_where}
            GROUP BY p.province_code, d.district_code, s.subdistrict_code, sk.skill_name_th
        ) grouped
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            SpecialtyByAreaItem(
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                skill_name=row.get("skill_name"),
                count=row.get("count", 0),
            )
            for row in rows
        ]

        return SpecialtyByAreaResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    _BANGKOK_TZ = ZoneInfo("Asia/Bangkok")

    REFRESH_GENDER_SUMMARY_SQL = """
    DELETE FROM osm_gender_summary WHERE snapshot_type = 'live';

    INSERT INTO osm_gender_summary (
        province_id,
        district_id,
        subdistrict_id,
        village_code,
        village_no,
        village_name_th,
        total_count,
        male_count,
        female_count,
        province_name_th,
        district_name_th,
        subdistrict_name_th,
        snapshot_type,
        fiscal_year,
        captured_at,
        triggered_by,
        note
    )
    SELECT
        p.province_code AS province_id,
        d.district_code AS district_id,
        s.subdistrict_code AS subdistrict_id,
        NULLIF(op.village_code, '') AS village_code,
        v.village_no,
        v.village_name_th,
        COUNT(op.id) AS total_count,
        COUNT(op.id) FILTER (WHERE op.gender = 'male') AS male_count,
        COUNT(op.id) FILTER (WHERE op.gender = 'female') AS female_count,
        p.province_name_th,
        d.district_name_th,
        s.subdistrict_name_th,
        'live' AS snapshot_type,
        NULL AS fiscal_year,
        CURRENT_TIMESTAMP,
        NULL,
        NULL
    FROM subdistricts s
    INNER JOIN districts d ON d.district_code = s.district_id
    INNER JOIN provinces p ON p.province_code = d.province_id
    LEFT JOIN osm_profiles op
        ON op.subdistrict_id = s.subdistrict_code
        AND op.deleted_at IS NULL
        AND (op.osm_status IS NULL OR op.osm_status = '')
    LEFT JOIN villages v
        ON v.village_code = NULLIF(op.village_code, '')
        AND v.deleted_at IS NULL
    WHERE s.deleted_at IS NULL
    GROUP BY
        NULLIF(op.village_code, ''),
        v.village_no,
        v.village_name_th,
        s.subdistrict_code,
        s.subdistrict_name_th,
        d.district_code,
        d.district_name_th,
        p.province_code,
        p.province_name_th;
    """

    FAMILY_ADDRESS_REPORT_CTE = """
    WITH family_union AS (
        SELECT
            'volunteer' AS status_code,
            'อสม.' AS status_label,
            vol_pref.prefix_name_th AS prefix_name,
            o.first_name,
            o.last_name,
            o.gender::text AS gender,
            o.osm_code AS osm_code,
            o.citizen_id AS citizen_id,
            TRIM(
                CONCAT_WS(
                    ' ',
                    NULLIF(o.address_number, ''),
                    NULLIF(o.alley, ''),
                    NULLIF(o.street, '')
                )
            ) AS address,
            o.village_no,
            o.village_code,
            COALESCE(v.village_name_th, o.village_name) AS village_name,
            o.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            o.district_id AS district_code,
            d.district_name_th AS district_name,
            o.province_id AS province_code,
            p.province_name_th AS province_name,
            o.id AS volunteer_id,
            vol_pref.prefix_name_th AS volunteer_prefix_name,
            o.first_name AS volunteer_first_name,
            o.last_name AS volunteer_last_name
        FROM osm_profiles o
        LEFT JOIN prefixes vol_pref ON vol_pref.id = o.prefix_id
        LEFT JOIN provinces p ON p.province_code = o.province_id
        LEFT JOIN districts d ON d.district_code = o.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = o.subdistrict_id
        LEFT JOIN villages v ON v.village_code = o.village_code
        WHERE o.deleted_at IS NULL AND (o.osm_status IS NULL OR o.osm_status = '')

        UNION ALL

        SELECT
            'spouse' AS status_code,
            'คู่สมรส' AS status_label,
            pref.prefix_name_th AS prefix_name,
            sp.first_name,
            sp.last_name,
            sp.gender::text AS gender,
            o.osm_code AS osm_code,
            sp.citizen_id AS citizen_id,
            TRIM(
                CONCAT_WS(
                    ' ',
                    NULLIF(sp.address_number, ''),
                    NULLIF(sp.alley, ''),
                    NULLIF(sp.street, '')
                )
            ) AS address,
            COALESCE(sp.village_no, o.village_no) AS village_no,
            COALESCE(sp.village_code, o.village_code) AS village_code,
            COALESCE(v.village_name_th, sp.village_name, o.village_name) AS village_name,
            COALESCE(sp.subdistrict_id, o.subdistrict_id) AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            COALESCE(sp.district_id, o.district_id) AS district_code,
            d.district_name_th AS district_name,
            COALESCE(sp.province_id, o.province_id) AS province_code,
            p.province_name_th AS province_name,
            o.id AS volunteer_id,
            vol_pref.prefix_name_th AS volunteer_prefix_name,
            o.first_name AS volunteer_first_name,
            o.last_name AS volunteer_last_name
        FROM osm_spouses sp
        INNER JOIN osm_profiles o ON o.id = sp.osm_profile_id
        LEFT JOIN prefixes pref ON pref.id = sp.prefix_id
        LEFT JOIN prefixes vol_pref ON vol_pref.id = o.prefix_id
        LEFT JOIN provinces p ON p.province_code = COALESCE(sp.province_id, o.province_id)
        LEFT JOIN districts d ON d.district_code = COALESCE(sp.district_id, o.district_id)
        LEFT JOIN subdistricts s ON s.subdistrict_code = COALESCE(sp.subdistrict_id, o.subdistrict_id)
        LEFT JOIN villages v ON v.village_code = COALESCE(sp.village_code, o.village_code)
        WHERE sp.deleted_at IS NULL AND o.deleted_at IS NULL AND (o.osm_status IS NULL OR o.osm_status = '')

        UNION ALL

        SELECT
            'child' AS status_code,
            'บุตร' AS status_label,
            pref.prefix_name_th AS prefix_name,
            c.first_name,
            c.last_name,
            c.gender::text AS gender,
            o.osm_code AS osm_code,
            c.citizen_id AS citizen_id,
            TRIM(
                CONCAT_WS(
                    ' ',
                    NULLIF(c.address_number, ''),
                    NULLIF(c.alley, ''),
                    NULLIF(c.street, '')
                )
            ) AS address,
            COALESCE(c.village_no, o.village_no) AS village_no,
            COALESCE(c.village_code, o.village_code) AS village_code,
            COALESCE(v.village_name_th, c.village_name, o.village_name) AS village_name,
            COALESCE(c.subdistrict_id, o.subdistrict_id) AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            COALESCE(c.district_id, o.district_id) AS district_code,
            d.district_name_th AS district_name,
            COALESCE(c.province_id, o.province_id) AS province_code,
            p.province_name_th AS province_name,
            o.id AS volunteer_id,
            vol_pref.prefix_name_th AS volunteer_prefix_name,
            o.first_name AS volunteer_first_name,
            o.last_name AS volunteer_last_name
        FROM osm_children c
        INNER JOIN osm_profiles o ON o.id = c.osm_profile_id
        LEFT JOIN prefixes pref ON pref.id = c.prefix_id
        LEFT JOIN prefixes vol_pref ON vol_pref.id = o.prefix_id
        LEFT JOIN provinces p ON p.province_code = COALESCE(c.province_id, o.province_id)
        LEFT JOIN districts d ON d.district_code = COALESCE(c.district_id, o.district_id)
        LEFT JOIN subdistricts s ON s.subdistrict_code = COALESCE(c.subdistrict_id, o.subdistrict_id)
        LEFT JOIN villages v ON v.village_code = COALESCE(c.village_code, o.village_code)
        WHERE c.deleted_at IS NULL AND o.deleted_at IS NULL AND (o.osm_status IS NULL OR o.osm_status = '')
    )
    """

    @staticmethod
    async def volunteer_gender(
        filters: StandardGenderReportQuery,
    ) -> StandardGenderReportResponse:
        """Return volunteer gender counts grouped by admin boundary."""

        query: QuerySet[OsmGenderSummary] = (
            OsmGenderSummary.filter(snapshot_type="live")
            .order_by(
                "province_id",
                "district_id",
                "subdistrict_id",
                "village_code",
            )
        )

        if filters.province_code:
            query = query.filter(province_id=filters.province_code)
        if filters.district_code:
            query = query.filter(district_id=filters.district_code)
        if filters.subdistrict_code:
            query = query.filter(subdistrict_id=filters.subdistrict_code)
        if filters.village_code:
            query = query.filter(village_code=filters.village_code)

        total = await query.count()
        offset = (filters.page - 1) * filters.page_size
        rows: List[OsmGenderSummary] = await query.offset(offset).limit(filters.page_size)

        items = [
            StandardGenderReportItem(
                province_code=row.province_id,
                province_name=row.province_name_th,
                district_code=row.district_id,
                district_name=row.district_name_th,
                subdistrict_code=row.subdistrict_id,
                subdistrict_name=row.subdistrict_name_th,
                village_code=row.village_code,
                village_no=row.village_no,
                village_name=row.village_name_th,
                total=row.total_count,
                male=row.male_count,
                female=row.female_count,
            )
            for row in rows
        ]

        return StandardGenderReportResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    @staticmethod
    async def volunteer_family_report(
        filters: FamilyAddressReportQuery,
    ) -> FamilyAddressReportResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        clauses: List[str] = []

        def add_filter(condition: str, value: str) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("family.province_code =", filters.province_code)
        if filters.district_code:
            add_filter("family.district_code =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("family.subdistrict_code =", filters.subdistrict_code)
        if filters.village_code:
            add_filter("family.village_code =", filters.village_code)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        limit_params = list(base_params)
        limit_params.append(filters.page_size)
        limit_placeholder = f"${len(limit_params)}"
        offset = (filters.page - 1) * filters.page_size
        limit_params.append(offset)
        offset_placeholder = f"${len(limit_params)}"

        list_sql = f"""{StandardReportService.FAMILY_ADDRESS_REPORT_CTE}
        SELECT *
        FROM family_union family
        {where_sql}
        ORDER BY
            family.province_code NULLS LAST,
            family.district_code NULLS LAST,
            family.subdistrict_code NULLS LAST,
            family.village_code NULLS LAST,
            family.volunteer_id,
            CASE family.status_code
                WHEN 'volunteer' THEN 0
                WHEN 'spouse' THEN 1
                ELSE 2
            END,
            family.prefix_name,
            family.first_name,
            family.last_name
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, limit_params)

        count_sql = f"""{StandardReportService.FAMILY_ADDRESS_REPORT_CTE}
        SELECT COUNT(*) AS total
        FROM family_union family
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            FamilyAddressReportItem(
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                village_code=row.get("village_code"),
                village_no=row.get("village_no"),
                village_name=row.get("village_name"),
                osm_code=row.get("osm_code"),
                citizen_id=row.get("citizen_id"),
                prefix_name=row.get("prefix_name"),
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                full_name=" ".join(
                    filter(None, [row.get("prefix_name"), row.get("first_name"), row.get("last_name")])
                )
                or None,
                gender=row.get("gender"),
                address=row.get("address"),
                status_code=row.get("status_code"),
                status_label=row.get("status_label"),
                volunteer_id=str(row.get("volunteer_id")) if row.get("volunteer_id") else None,
                volunteer_name=" ".join(
                    filter(
                        None,
                        [
                            row.get("volunteer_prefix_name"),
                            row.get("volunteer_first_name"),
                            row.get("volunteer_last_name"),
                        ],
                    )
                )
                or None,
            )
            for row in rows
        ]

        return FamilyAddressReportResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # Average age report
    # ------------------------------------------------------------------

    @staticmethod
    async def average_age_report(filters: AverageAgeReportQuery) -> AverageAgeReportResponse:
        connection = connections.get("default")
        params: List[object] = []
        geo_clauses: List[str] = ["s.deleted_at IS NULL"]

        def add_filter(condition: str, value: object) -> None:
            params.append(value)
            geo_clauses.append(f"{condition} ${len(params)}")

        if filters.province_code:
            add_filter("p.province_code =", filters.province_code)
        if filters.district_code:
            add_filter("d.district_code =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("s.subdistrict_code =", filters.subdistrict_code)

        geo_where = f"WHERE {' AND '.join(geo_clauses)}" if geo_clauses else ""

        # pagination on grouped rows
        limit_params = list(params)
        limit_params.append(filters.page_size)
        limit_placeholder = f"${len(limit_params)}"
        offset = (filters.page - 1) * filters.page_size
        limit_params.append(offset)
        offset_placeholder = f"${len(limit_params)}"

        list_sql = f"""
        SELECT
            p.province_code AS province_code,
            p.province_name_th AS province_name,
            d.district_code AS district_code,
            d.district_name_th AS district_name,
            s.subdistrict_code AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            COUNT(op.id) AS total,
            AVG(EXTRACT(YEAR FROM age(current_date, op.birth_date))) AS average_age,
            MIN(EXTRACT(YEAR FROM age(current_date, op.birth_date))) AS min_age,
            MAX(EXTRACT(YEAR FROM age(current_date, op.birth_date))) AS max_age
        FROM subdistricts s
        INNER JOIN districts d ON d.district_code = s.district_id
        INNER JOIN provinces p ON p.province_code = d.province_id
        LEFT JOIN osm_profiles op
            ON op.subdistrict_id = s.subdistrict_code
            AND op.deleted_at IS NULL
            AND (op.osm_status IS NULL OR op.osm_status = '')
            AND op.birth_date IS NOT NULL
        {geo_where}
        GROUP BY
            p.province_code,
            p.province_name_th,
            d.district_code,
            d.district_name_th,
            s.subdistrict_code,
            s.subdistrict_name_th
        ORDER BY
            p.province_code NULLS LAST,
            d.district_code NULLS LAST,
            s.subdistrict_code NULLS LAST
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, limit_params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM (
            SELECT 1
            FROM subdistricts s
            INNER JOIN districts d ON d.district_code = s.district_id
            INNER JOIN provinces p ON p.province_code = d.province_id
            {geo_where}
            GROUP BY
                p.province_code,
                d.district_code,
                s.subdistrict_code
        ) grouped
        """
        count_result = await connection.execute_query_dict(count_sql, params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            AverageAgeReportItem(
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                total=row.get("total", 0),
                average_age=float(row.get("average_age")) if row.get("average_age") is not None else 0.0,
                min_age=float(row.get("min_age")) if row.get("min_age") is not None else 0.0,
                max_age=float(row.get("max_age")) if row.get("max_age") is not None else 0.0,
            )
            for row in rows
        ]

        return AverageAgeReportResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    # ------------------------------------------------------------------
    # New volunteers by year report
    # ------------------------------------------------------------------

    @staticmethod
    async def new_volunteers_by_year(filters: NewVolunteerByYearQuery) -> NewVolunteerByYearResponse:
        connection = connections.get("default")
        base_params: List[object] = []
        # "New volunteers" report: default to active volunteers (osm_status NULL or empty string)
        # and use Buddhist Era (พ.ศ.) arithmetic for years.
        clauses: List[str] = ["op.deleted_at IS NULL", "(op.osm_status IS NULL OR op.osm_status::text = '')"]

        def add_filter(condition: str, value: object) -> None:
            base_params.append(value)
            clauses.append(f"{condition} ${len(base_params)}")

        if filters.province_code:
            add_filter("op.province_id =", filters.province_code)
        if filters.district_code:
            add_filter("op.district_id =", filters.district_code)
        if filters.subdistrict_code:
            add_filter("op.subdistrict_id =", filters.subdistrict_code)
        if getattr(filters, "village_code", None):
            add_filter("op.village_code::text =", str(filters.village_code))

        start_year_expr = "COALESCE(op.osm_year::int, (EXTRACT(YEAR FROM op.created_at)::int + 543))"

        if filters.year_from:
            add_filter(f"{start_year_expr} >=", filters.year_from)
        if filters.year_to:
            add_filter(f"{start_year_expr} <=", filters.year_to)

        tenure_years_expr = f"GREATEST(0, ((EXTRACT(YEAR FROM CURRENT_DATE)::int + 543) - {start_year_expr}))::int"
        tenure_bucket_expr = f"""
        CASE
            WHEN {tenure_years_expr} <= 0 THEN '<1'
            WHEN {tenure_years_expr} = 1 THEN '1'
            WHEN {tenure_years_expr} = 2 THEN '2'
            WHEN {tenure_years_expr} = 3 THEN '3'
            WHEN {tenure_years_expr} = 4 THEN '4'
            WHEN {tenure_years_expr} = 5 THEN '5'
            ELSE '6+'
        END
        """

        if getattr(filters, "tenure_bucket", None):
            bucket = str(filters.tenure_bucket).strip()
            if bucket in {"<1", "0"}:
                clauses.append(f"{tenure_years_expr} <= 0")
            elif bucket in {"1", "2", "3", "4", "5"}:
                base_params.append(int(bucket))
                clauses.append(f"{tenure_years_expr} = ${len(base_params)}")
            elif bucket in {"6+", "6", ">=6", ">6"}:
                clauses.append(f"{tenure_years_expr} >= 6")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params = list(base_params)
        params.append(filters.page_size)
        limit_placeholder = f"${len(params)}"
        offset = (filters.page - 1) * filters.page_size
        params.append(offset)
        offset_placeholder = f"${len(params)}"

        list_sql = f"""
        SELECT
            op.id,
            op.citizen_id,
            op.osm_code,
            op.first_name,
            op.last_name,
            op.gender::text AS gender,
            op.osm_year,
            {start_year_expr} AS start_year,
            {tenure_years_expr} AS tenure_years,
            {tenure_bucket_expr} AS tenure_bucket,
            op.created_at,
            op.approval_date,
            op.approval_status::text AS approval_status,
            op.volunteer_status::text AS volunteer_status,
            op.province_id AS province_code,
            p.province_name_th AS province_name,
            op.district_id AS district_code,
            d.district_name_th AS district_name,
            op.subdistrict_id AS subdistrict_code,
            s.subdistrict_name_th AS subdistrict_name,
            op.village_code::text AS village_code,
            COALESCE(v.village_no::text, op.village_no::text) AS village_no,
            COALESCE(v.village_name_th::text, op.village_name::text) AS village_name
        FROM osm_profiles op
        LEFT JOIN provinces p ON p.province_code = op.province_id
        LEFT JOIN districts d ON d.district_code = op.district_id
        LEFT JOIN subdistricts s ON s.subdistrict_code = op.subdistrict_id
        LEFT JOIN villages v ON v.village_code::text = op.village_code::text
        {where_sql}
        ORDER BY start_year DESC, op.created_at DESC
        LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """

        rows = await connection.execute_query_dict(list_sql, params)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM osm_profiles op
        {where_sql}
        """
        count_result = await connection.execute_query_dict(count_sql, base_params)
        total = count_result[0]["total"] if count_result else 0

        items = [
            NewVolunteerByYearItem(
                id=str(row.get("id")),
                citizen_id=row.get("citizen_id"),
                osm_code=row.get("osm_code"),
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                gender=row.get("gender"),
                start_year=row.get("start_year"),
                tenure_years=row.get("tenure_years"),
                tenure_bucket=row.get("tenure_bucket"),
                osm_year=row.get("osm_year"),
                created_at=row.get("created_at").isoformat() if row.get("created_at") else None,
                approval_date=str(row.get("approval_date")) if row.get("approval_date") else None,
                approval_status=row.get("approval_status"),
                volunteer_status=row.get("volunteer_status"),
                province_code=row.get("province_code"),
                province_name=row.get("province_name"),
                district_code=row.get("district_code"),
                district_name=row.get("district_name"),
                subdistrict_code=row.get("subdistrict_code"),
                subdistrict_name=row.get("subdistrict_name"),
                village_code=row.get("village_code"),
                village_no=row.get("village_no"),
                village_name=row.get("village_name"),
            )
            for row in rows
        ]

        return NewVolunteerByYearResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    @staticmethod
    async def refresh_gender_summary() -> SnapshotMutationResponse:
        connection = connections.get("default")
        await connection.execute_script(StandardReportService.REFRESH_GENDER_SUMMARY_SQL)
        total_rows = await OsmGenderSummary.filter(snapshot_type="live").count()
        return SnapshotMutationResponse(
            message="Refreshed live gender summary",
            records=total_rows,
        )

    @staticmethod
    def _current_fiscal_year(target: Optional[datetime] = None) -> int:
        now = target or datetime.now(StandardReportService._BANGKOK_TZ)
        thai_year = now.year + 543
        if now.month >= 10:
            return thai_year + 1
        return thai_year

    @staticmethod
    async def capture_gender_snapshot(
        payload: StandardGenderSnapshotCreateRequest,
        triggered_by: Optional[str],
    ) -> SnapshotMutationResponse:
        fiscal_year = StandardReportService._current_fiscal_year()

        rows = await OsmGenderSummary.filter(snapshot_type="live")
        if not rows:
            return SnapshotMutationResponse(
                success=True,
                message="No data available to snapshot",
                fiscal_year=fiscal_year,
                records=0,
            )

        captured_at = datetime.now(timezone.utc)
        snapshots = [
            OsmGenderSummary(
                fiscal_year=fiscal_year,
                captured_at=captured_at,
                triggered_by=triggered_by,
                note=payload.note,
                province_id=row.province_id,
                district_id=row.district_id,
                subdistrict_id=row.subdistrict_id,
                village_code=row.village_code,
                village_no=row.village_no,
                village_name_th=row.village_name_th,
                total_count=row.total_count,
                male_count=row.male_count,
                female_count=row.female_count,
                province_name_th=row.province_name_th,
                district_name_th=row.district_name_th,
                subdistrict_name_th=row.subdistrict_name_th,
                snapshot_type="snapshot",
            )
            for row in rows
        ]
        await OsmGenderSummary.filter(snapshot_type="snapshot", fiscal_year=fiscal_year).delete()
        await OsmGenderSummary.bulk_create(snapshots)

        return SnapshotMutationResponse(
            message="Captured gender summary snapshot",
            fiscal_year=fiscal_year,
            records=len(snapshots),
        )

    @staticmethod
    async def volunteer_gender_snapshot(
        filters: StandardGenderSnapshotQuery,
    ) -> StandardGenderSnapshotResponse:
        fiscal_year = filters.fiscal_year or StandardReportService._current_fiscal_year()

        query: QuerySet[OsmGenderSummary] = (
            OsmGenderSummary.filter(snapshot_type="snapshot", fiscal_year=fiscal_year)
            .order_by("province_id", "district_id", "subdistrict_id", "village_code")
        )

        if filters.province_code:
            query = query.filter(province_id=filters.province_code)
        if filters.district_code:
            query = query.filter(district_id=filters.district_code)
        if filters.subdistrict_code:
            query = query.filter(subdistrict_id=filters.subdistrict_code)
        if filters.village_code:
            query = query.filter(village_code=filters.village_code)

        total = await query.count()
        offset = (filters.page - 1) * filters.page_size
        rows: List[OsmGenderSummary] = await query.offset(offset).limit(filters.page_size)

        items = [
            StandardGenderSnapshotItem(
                fiscal_year=row.fiscal_year,
                captured_at=row.captured_at.isoformat() if row.captured_at else "",
                note=row.note,
                province_code=row.province_id,
                province_name=row.province_name_th,
                district_code=row.district_id,
                district_name=row.district_name_th,
                subdistrict_code=row.subdistrict_id,
                subdistrict_name=row.subdistrict_name_th,
                village_code=row.village_code,
                village_no=row.village_no,
                village_name=row.village_name_th,
                total=row.total_count,
                male=row.male_count,
                female=row.female_count,
            )
            for row in rows
        ]

        return StandardGenderSnapshotResponse(
            fiscal_year=fiscal_year,
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )
