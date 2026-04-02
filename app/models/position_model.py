from tortoise import fields, models
from uuid import uuid4

from app.models.enum_models import AdministrativeLevelEnum

class Position(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    position_name_th = fields.CharField(max_length=255, index=True) # ชื่อตำแหน่ง ภาษาไทย
    position_name_en = fields.CharField(max_length=255, null=True) # ชื่อตำแหน่ง ภาษาอังกฤษ
    position_code = fields.CharField(max_length=255, unique=True, index=True) # รหัสตำแหน่ง
    scope_level = fields.CharEnumField(
        AdministrativeLevelEnum,
        null=True,
        index=True,
    )

    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "positions"