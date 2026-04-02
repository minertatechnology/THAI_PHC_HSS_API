from __future__ import annotations

from uuid import uuid4

from tortoise import fields, models


class DashboardAnnualSummary(models.Model):
    """ตารางเก็บข้อมูลสรุปรายปีแยกตามจังหวัดสำหรับแสดงบนแดชบอร์ด"""

    id = fields.UUIDField(pk=True, default=uuid4)
    year_buddhist = fields.IntField(index=True)
    geography_level = fields.CharField(max_length=20, default="province", index=True)
    province_code = fields.CharField(max_length=10, null=True, index=True)
    province_name_th = fields.CharField(max_length=255, null=True)
    province_name_en = fields.CharField(max_length=255, null=True)
    district_code = fields.CharField(max_length=10, null=True, index=True)
    district_name_th = fields.CharField(max_length=255, null=True)
    district_name_en = fields.CharField(max_length=255, null=True)
    subdistrict_code = fields.CharField(max_length=10, null=True, index=True)
    subdistrict_name_th = fields.CharField(max_length=255, null=True)
    subdistrict_name_en = fields.CharField(max_length=255, null=True)

    district_count = fields.IntField(default=0)
    subdistrict_count = fields.IntField(default=0)
    village_count = fields.IntField(default=0)
    community_count = fields.IntField(default=0)

    pcu_count = fields.IntField(default=0)
    hosp_satang_count = fields.IntField(default=0)
    hosp_general_count = fields.IntField(default=0)
    quota = fields.IntField(default=0)

    osm_count = fields.IntField(default=0)
    osm_allowance_eligible_count = fields.IntField(default=0)
    osm_training_budget_count = fields.IntField(default=0)
    osm_payment_training_count = fields.IntField(default=0)

    osm_showbbody_paid_count = fields.IntField(default=0)
    osm_showbbody_not_paid_count = fields.IntField(default=0)
    osm_showbbody_pending_count = fields.IntField(default=0)
    osm_no_showbbody_status_count = fields.IntField(default=0)

    last_calculated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "dashboard_annual_summary"
        unique_together = (
            "year_buddhist",
            "geography_level",
            "province_code",
            "district_code",
            "subdistrict_code",
        )
        indexes = (
            ("year_buddhist", "geography_level", "province_code"),
            ("year_buddhist", "geography_level", "district_code"),
            ("year_buddhist", "geography_level", "subdistrict_code"),
        )

    def __str__(self) -> str:
        province_display = self.province_name_th or self.province_code or "ALL"
        return f"DashboardAnnualSummary({self.year_buddhist}, {province_display})"
