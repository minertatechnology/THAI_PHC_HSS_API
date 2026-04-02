from tortoise import fields, models
from uuid import uuid4


class ReportDefinition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    name = fields.CharField(max_length=100, unique=True, index=True)
    label = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.CharField(max_length=255, null=True, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "report_definitions"

class OsmGenderSummary(models.Model):
    id = fields.IntField(pk=True)
    province_id = fields.CharField(max_length=10, pk=False, index=True)
    district_id = fields.CharField(max_length=10, pk=False, index=True)
    subdistrict_id = fields.CharField(max_length=10, pk=False, index=True)
    village_code = fields.CharField(max_length=10, null=True, index=True)
    village_no = fields.CharField(max_length=10, null=True)
    village_name_th = fields.CharField(max_length=255, null=True)
    total_count = fields.IntField()
    male_count = fields.IntField()
    female_count = fields.IntField()
    province_name_th = fields.CharField(max_length=255, null=True)
    district_name_th = fields.CharField(max_length=255, null=True)
    subdistrict_name_th = fields.CharField(max_length=255, null=True)
    snapshot_type = fields.CharField(max_length=20, default="live", index=True)
    fiscal_year = fields.IntField(null=True, index=True)
    captured_at = fields.DatetimeField(auto_now_add=True, index=True)
    triggered_by = fields.CharField(max_length=255, null=True, index=True)
    note = fields.TextField(null=True)

    class Meta:
        table = "osm_gender_summary"
        managed = False

class OsmFamilySummary(models.Model):
    id = fields.IntField(pk=True)
    prefix_name_th = fields.CharField(max_length=255, pk=False, index=True)
    first_name = fields.CharField(max_length=255, pk=False, index=True)
    last_name = fields.CharField(max_length=255, pk=False, index=True)
    gender = fields.CharField(max_length=255, pk=False, index=True)
    address = fields.CharField(max_length=255, pk=False, index=True)
    village_no = fields.CharField(max_length=255, pk=False, index=True)
    province_id = fields.CharField(max_length=10, pk=False, index=True)
    province_name_th = fields.CharField(max_length=255, pk=False, index=True)
    district_id = fields.CharField(max_length=10, pk=False, index=True)
    district_name_th = fields.CharField(max_length=255, pk=False, index=True)
    subdistrict_id = fields.CharField(max_length=10, pk=False, index=True)
    subdistrict_name_th = fields.CharField(max_length=255, pk=False, index=True)
    status = fields.CharField(max_length=255, pk=False, index=True)

    class Meta:
        table = "osm_family_summary"
        managed = False

class OsmPresidentSummary(models.Model):
    id = fields.IntField(pk=True)
    area_name_th = fields.CharField(max_length=255, null=True, index=True)
    first_name = fields.CharField(max_length=255, index=True)
    last_name = fields.CharField(max_length=255, index=True)
    province_name_th = fields.CharField(max_length=255, null=True, index=True)
    district_name_th = fields.CharField(max_length=255, null=True, index=True)
    subdistrict_name_th = fields.CharField(max_length=255, null=True, index=True)
    registration_year = fields.IntField(null=True, index=True)
    position_name_th = fields.CharField(max_length=255, index=True)
    position_level = fields.CharField(max_length=50, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "osm_president_summary"
        managed = False