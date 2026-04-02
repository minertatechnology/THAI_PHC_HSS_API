from uuid import uuid4

from tortoise import fields, models


class PeopleUser(models.Model):
    """General People profile for unified SSO."""

    id = fields.UUIDField(pk=True, default=uuid4)
    citizen_id = fields.CharField(max_length=13, unique=True, index=True)
    prefix = fields.CharField(max_length=50, null=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    gender = fields.CharField(max_length=10, null=True)
    phone_number = fields.CharField(max_length=20, null=True, index=True)
    email = fields.CharField(max_length=255, null=True, index=True)
    line_id = fields.CharField(max_length=100, null=True)
    school = fields.CharField(max_length=255, null=True)
    organization = fields.CharField(max_length=255, null=True)
    profile_image = fields.CharField(max_length=1024, null=True)
    registration_reason = fields.TextField(null=True)
    photo_1inch = fields.CharField(max_length=1024, null=True)
    attachments = fields.JSONField(null=True)  # list of file paths / URLs
    province_code = fields.CharField(max_length=10, null=True, index=True)
    province_name = fields.CharField(max_length=255, null=True)
    district_code = fields.CharField(max_length=10, null=True, index=True)
    district_name = fields.CharField(max_length=255, null=True)
    subdistrict_code = fields.CharField(max_length=10, null=True, index=True)
    subdistrict_name = fields.CharField(max_length=255, null=True)
    birthday = fields.DateField(null=True)
    yuwa_osm_code = fields.CharField(max_length=9, null=True, index=True)
    password_hash = fields.CharField(max_length=255, null=True)
    is_first_login = fields.BooleanField(default=True)
    password_attempts = fields.IntField(default=0)
    is_active = fields.BooleanField(default=False)
    is_transferred = fields.BooleanField(default=False)
    transferred_at = fields.DatetimeField(null=True)
    transferred_by = fields.UUIDField(null=True, index=True)
    yuwa_osm_id = fields.UUIDField(null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "people_user"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.citizen_id})"
