from tortoise import fields, models
from uuid import uuid4

# ตารางคำนำหน้า
class Prefix(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    prefix_name_th = fields.CharField(max_length=255) # ชื่อคำนำหน้า ภาษาไทย
    prefix_name_en = fields.CharField(max_length=255) # ชื่อคำนำหน้า ภาษาอังกฤษ
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "prefixes"


# # ตารางอาชีพ
class Occupation(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    occupation_name_th = fields.CharField(max_length=255) # ชื่ออาชีพ ภาษาไทย
    occupation_name_en = fields.CharField(max_length=255, null=True) # ชื่ออาชีพ ภาษาอังกฤษ
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "occupations"

# ตารางระดับการศึกษา
class Education(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    education_name_th = fields.CharField(max_length=255) # ชื่อระดับการศึกษา ภาษาไทย
    education_name_en = fields.CharField(max_length=255) # ชื่อระดับการศึกษา ภาษาอังกฤษ
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "educations"

# ตารางธนาคาร
class Bank(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    bank_name_th = fields.CharField(max_length=255) # ชื่อธนาคาร ภาษาไทย
    bank_name_en = fields.CharField(max_length=255) # ชื่อธนาคาร ภาษาอังกฤษ
    bank_code = fields.CharField(max_length=3, null=True) # รหัสธนาคาร
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "banks"