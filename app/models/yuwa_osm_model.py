from uuid import uuid4

from tortoise import fields, models

from app.models.enum_models import ApprovalStatus


class YuwaOSMUser(models.Model):
    """Central Yuwa member profile persisted for unified SSO."""

    id = fields.UUIDField(pk=True, default=uuid4)
    prefix = fields.CharField(max_length=50, null=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    citizen_id = fields.CharField(max_length=13, null=True, unique=True, index=True)
    gender = fields.CharField(max_length=10, null=True)
    phone_number = fields.CharField(max_length=20, null=True, unique=True, index=True)
    email = fields.CharField(max_length=255, null=True, index=True)
    line_id = fields.CharField(max_length=100, null=True)
    school = fields.CharField(max_length=255, null=True)
    organization = fields.CharField(max_length=255, null=True)
    yuwa_osm_code = fields.CharField(max_length=9, null=True, index=True)
    province_code = fields.CharField(max_length=10, null=True, index=True)
    province_name = fields.CharField(max_length=255, null=True)
    district_code = fields.CharField(max_length=10, null=True, index=True)
    district_name = fields.CharField(max_length=255, null=True)
    subdistrict_code = fields.CharField(max_length=10, null=True, index=True)
    subdistrict_name = fields.CharField(max_length=255, null=True)
    profile_image = fields.CharField(max_length=1024, null=True)
    registration_reason = fields.TextField(null=True)
    photo_1inch = fields.CharField(max_length=1024, null=True)
    attachments = fields.JSONField(null=True)  # list of file paths / URLs
    birthday = fields.DateField(null=True)
    password_hash = fields.CharField(max_length=255, null=True)
    is_first_login = fields.BooleanField(default=True)
    password_attempts = fields.IntField(default=0)
    is_active = fields.BooleanField(default=False)
    approval_status = fields.CharEnumField(ApprovalStatus, default=ApprovalStatus.PENDING)
    approved_by = fields.UUIDField(null=True, index=True)
    approved_at = fields.DatetimeField(null=True)
    rejected_by = fields.UUIDField(null=True, index=True)
    rejected_at = fields.DatetimeField(null=True)
    rejection_reason = fields.TextField(null=True)
    source_people_id = fields.UUIDField(null=True, index=True)
    transferred_by = fields.UUIDField(null=True, index=True)
    transferred_at = fields.DatetimeField(null=True)
    # Gen-H link (populated when user migrated from gen_h → yuwa_osm)
    gen_h_code = fields.CharField(max_length=20, null=True, unique=True, index=True)
    gen_h_id = fields.UUIDField(null=True, index=True)
    # 'migration' | 'people_transfer' | 'new_registration'
    source_type = fields.CharField(max_length=20, default="new_registration")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "yuwa_osm_user"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
