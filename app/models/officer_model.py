
from tortoise import fields, models
from app.models.enum_models import ApprovalStatus, Gender, AdministrativeLevelEnum
from uuid import uuid4


class OfficerProfile(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    citizen_id = fields.CharField(max_length=255, unique=True, index=True)

    prefix = fields.ForeignKeyField("models.Prefix", related_name="officer_profiles")
    first_name = fields.CharField(max_length=255, index=True)
    last_name = fields.CharField(max_length=255, index=True)
    gender = fields.CharEnumField(Gender, null=True)

    birth_date = fields.DateField(index=True, null=True)
    email = fields.CharField(max_length=255, null=True)
    phone = fields.CharField(max_length=255, null=True)
    profile_image = fields.CharField(max_length=1024, null=True)

    password_hash = fields.CharField(max_length=255, null=True)
    is_first_login = fields.BooleanField(default=True)
    password_attempts = fields.IntField(default=0)

    position = fields.ForeignKeyField("models.Position", related_name="officer_profiles")
    address_number = fields.CharField(max_length=100)
    province = fields.ForeignKeyField("models.Province", related_name="officer_profiles", null=True)
    district = fields.ForeignKeyField("models.District", related_name="officer_profiles", null=True)
    subdistrict = fields.ForeignKeyField("models.Subdistrict", related_name="officer_profiles", null=True)
    village_no = fields.CharField(max_length=10, null=True)
    alley = fields.CharField(max_length=255, null=True)
    street = fields.CharField(max_length=255, null=True)
    postal_code = fields.CharField(max_length=5, null=True)
    municipality = fields.ForeignKeyField("models.Municipality", related_name="officer_profiles", null=True)
    health_area = fields.ForeignKeyField("models.HealthArea", related_name="officer_profiles", null=True)
    health_service = fields.ForeignKeyField("models.HealthService", related_name="officer_profiles", null=True)
    area_type = fields.CharEnumField(AdministrativeLevelEnum, related_name="officer_profiles")  # ระดับการปกครอง/พื้นที่ในประเทศไทย
    area_code = fields.CharField(max_length=255, null=True, index=True)  # รหัสพื้นที่การปกครอง
    is_active = fields.BooleanField(default=False)
    approval_date = fields.DateField(null=True)

    approval_by = fields.UUIDField(null=True, index=True)

    active_status_at = fields.DatetimeField(null=True)
    active_status_by = fields.UUIDField(null=True, index=True)

    approval_status = fields.CharEnumField(ApprovalStatus, default=ApprovalStatus.PENDING)

    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "officers"