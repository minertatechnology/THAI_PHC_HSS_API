from tortoise import fields, models
from uuid import uuid4

class MunicipalityType(models.Model):
    code = fields.CharField(max_length=255, pk=True, index=True) # รหัสประเภทเทศบาล เช่น opt, tm
    municipality_type_name_th = fields.CharField(max_length=255) # ชื่อประเภทเทศบาล ภาษาไทย
    municipality_type_name_en = fields.CharField(max_length=255, null=True) # ชื่อประเภทเทศบาล ภาษาอังกฤษ
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "municipality_types"

class Municipality(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    municipality_name_th = fields.CharField(max_length=255) # ชื่อเทศบาล ภาษาไทย
    municipality_name_en = fields.CharField(max_length=255, null=True) # ชื่อเทศบาล ภาษาอังกฤษ
    
    municipality_type = fields.ForeignKeyField("models.MunicipalityType", related_name="municipalities", to_field="code")
    
    province = fields.ForeignKeyField("models.Province", related_name="municipalities", to_field="province_code", null=True)
    district = fields.ForeignKeyField("models.District", related_name="municipalities", to_field="district_code", null=True)
    subdistrict = fields.ForeignKeyField("models.Subdistrict", related_name="municipalities", to_field="subdistrict_code", null=True)
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "municipalities"