from uuid import uuid4

from tortoise import fields, models


class GenHUser(models.Model):
    """Gen H (เยาวชนก่อนเป็นยุวอสม.) profile."""

    id = fields.UUIDField(pk=True, default=uuid4)
    gen_h_code = fields.CharField(max_length=20, unique=True, index=True)
    prefix = fields.CharField(max_length=50, null=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    gender = fields.CharField(max_length=10, null=True)
    phone_number = fields.CharField(max_length=20, null=True, index=True)
    email = fields.CharField(max_length=255, null=True, index=True)
    line_id = fields.CharField(max_length=100, null=True)
    school = fields.CharField(max_length=255, null=True)
    province_code = fields.CharField(max_length=10, null=True, index=True)
    province_name = fields.CharField(max_length=255, null=True)
    district_code = fields.CharField(max_length=10, null=True, index=True)
    district_name = fields.CharField(max_length=255, null=True)
    subdistrict_code = fields.CharField(max_length=10, null=True, index=True)
    subdistrict_name = fields.CharField(max_length=255, null=True)
    profile_image_url = fields.CharField(max_length=1024, null=True)
    photo_1inch = fields.CharField(max_length=1024, null=True)
    member_card_url = fields.CharField(max_length=1024, null=True)
    attachments = fields.JSONField(null=True)
    points = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)

    # Personal info
    citizen_id = fields.CharField(max_length=13, null=True, index=True)
    birthday = fields.DateField(null=True)
    organization = fields.CharField(max_length=255, null=True)
    registration_reason = fields.TextField(null=True)

    # Auth fields
    password_hash = fields.CharField(max_length=255, null=True)
    is_first_login = fields.BooleanField(default=True)
    password_attempts = fields.IntField(default=0)

    # Link to existing user system
    people_user_id = fields.UUIDField(null=True, index=True)
    yuwa_osm_user_id = fields.UUIDField(null=True, index=True)
    transferred_at = fields.DatetimeField(null=True)

    # 'migration' | 'self_register'
    source_type = fields.CharField(max_length=20, default="self_register")

    created_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "gen_h_user"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.gen_h_code})"
