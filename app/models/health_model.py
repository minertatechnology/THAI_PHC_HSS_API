from tortoise import fields, models
from uuid import uuid4

# ตารางเขตสุขภาพ
class HealthArea(models.Model):
    code = fields.CharField(max_length=255, pk=True, index=True) # รหัสเขตสุขภาพ เช่น 'HA1' ,'HA2', 'HA3', 'HA4'
    health_area_name_th = fields.CharField(max_length=255) # ชื่อเขตสุขภาพ ภาษาไทย เช่น 'เขตสุขภาพ1' ,'เขตสุขภาพ2' ,'เขตสุขภาพ3' ,'เขตสุขภาพ4'
    health_area_name_en = fields.CharField(max_length=255) # ชื่อเขตสุขภาพ ภาษาอังกฤษ เช่น 'Health Area1' ,'Health Area2' ,'Health Area3' ,'Health Area4'
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "health_areas"

# ตารางสถานบริการสุขภาพ
class HealthService(models.Model):
    health_service_code = fields.CharField(max_length=255, pk=True, index=True) # รหัสบริการสุขภาพ
    health_service_name_th = fields.CharField(max_length=255) # ชื่อบริการสุขภาพ ภาษาไทย
    health_service_name_en = fields.CharField(max_length=255, null=True) # ชื่อบริการสุขภาพ ภาษาอังกฤษ
    legacy_5digit_code = fields.CharField(max_length=255, null=True) # รหัสบริการสุขภาพเก่า 5 หลัก
    legacy_9digit_code = fields.CharField(max_length=255, null=True) # รหัสบริการสุขภาพเก่า 9 หลัก
    
    health_service_type = fields.ForeignKeyField("models.HealthServiceType", related_name="health_services")
    
    province = fields.ForeignKeyField("models.Province", related_name="health_services", to_field="province_code", null=True)
    district = fields.ForeignKeyField("models.District", related_name="health_services", to_field="district_code", null=True)
    subdistrict = fields.ForeignKeyField("models.Subdistrict", related_name="health_services", to_field="subdistrict_code", null=True)
    
    
    village_no = fields.CharField(max_length=255, null=True) # หมู่
    latitude = fields.FloatField(null=True) # ละติจูด
    longitude = fields.FloatField(null=True) # ลองจิจูด
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "health_services"

# ตารางประเภทสถานบริการสุขภาพ
class HealthServiceType(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    health_service_type_name_th = fields.CharField(max_length=255) # ชื่อประเภทบริการสุขภาพ ภาษาไทย
    health_service_type_name_en = fields.CharField(max_length=255, null=True) # ชื่อประเภทบริการสุขภาพ ภาษาอังกฤษ
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "health_service_types"