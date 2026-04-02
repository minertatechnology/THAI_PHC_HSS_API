from tortoise import fields, models
from uuid import uuid4

# ตารางภูมิภาค
class Region(models.Model):
    code = fields.CharField(max_length=255, pk=True, index=True) # รหัสภูมิภาค
    region_name_th = fields.CharField(max_length=255) # ชื่อภูมิภาค ภาษาไทย
    region_name_en = fields.CharField(max_length=255) # ชื่อภูมิภาค ภาษาอังกฤษ
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "regions"

# #ตารางเขต
class Area(models.Model):
    code = fields.CharField(max_length=255, pk=True, index=True) # รหัสเขต
    area_name_th = fields.CharField(max_length=255) # ชื่อเขต ภาษาไทย
    area_name_en = fields.CharField(max_length=255) # ชื่อเขต ภาษาอังกฤษ
    
    region = fields.ForeignKeyField("models.Region", related_name="areas", to_field="code", null=True) # รหัสภูมิภาค
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "areas"

# ตารางจังหวัด
class Province(models.Model):
    province_code = fields.CharField(max_length=255, pk=True, index=True) # รหัสจังหวัด
    province_name_th = fields.CharField(max_length=255) # ชื่อจังหวัด ภาษาไทย
    province_name_en = fields.CharField(max_length=255, null=True) # ชื่อจังหวัด ภาษาอังกฤษ
    
    area = fields.ForeignKeyField("models.Area", related_name="provinces", to_field="code", null=True) # รหัสเขต
    region = fields.ForeignKeyField("models.Region", related_name="provinces", to_field="code", null=True) # รหัสภูมิภาค
    health_area = fields.ForeignKeyField("models.HealthArea", related_name="provinces", to_field="code", null=True) # รหัสเขตสุขภาพ
    
    latitude = fields.FloatField(null=True) # ละติจูด
    longitude = fields.FloatField(null=True) # ลองจิจูด
    quota = fields.IntField(default=0) # จำนวนโควต้า อสม. ที่จัดสรรให้จังหวัด
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)



    class Meta:
        table = "provinces"

# ตารางอำเภอ
class District(models.Model):
    district_code = fields.CharField(max_length=255, pk=True, index=True) # รหัสอำเภอ
    district_name_th = fields.CharField(max_length=255) # ชื่ออำเภอ ภาษาไทย
    district_name_en = fields.CharField(max_length=255, null=True) # ชื่ออำเภอ ภาษาอังกฤษ
    
    province = fields.ForeignKeyField("models.Province", related_name="districts", to_field="province_code")
    
    latitude = fields.FloatField(null=True) # ละติจูด
    longitude = fields.FloatField(null=True) # ลองจิจูด
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)



    class Meta:
        table = "districts"

# ตารางตำบล
class Subdistrict(models.Model):
    subdistrict_code = fields.CharField(max_length=255, pk=True, index=True) # รหัสตำบล
    subdistrict_name_th = fields.CharField(max_length=255) # ชื่อตำบล ภาษาไทย
    subdistrict_name_en = fields.CharField(max_length=255, null=True) # ชื่อตำบล ภาษาอังกฤษ
    
    district = fields.ForeignKeyField("models.District", related_name="subdistricts", to_field="district_code")       
    
    latitude = fields.FloatField(null=True) # ละติจูด
    longitude = fields.FloatField(null=True) # ลองจิจูด
    postal_code = fields.CharField(max_length=255, null=True) # รหัสไปรษณีย์
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "subdistricts"


class Village(models.Model):
    """ตารางข้อมูลหมู่บ้าน (legacy villcode-based records)."""

    village_code = fields.CharField(max_length=255, pk=True, index=True)  # รหัสหมู่บ้าน villcode 9 หลัก
    village_code_8digit = fields.CharField(max_length=255, null=True, index=True)  # รหัสหมู่บ้าน 8 หลัก (ตัด digit ที่ 7 ออก)
    village_no = fields.IntField(null=True, index=True)  # เลขหมู่บ้าน (vill_no)
    village_name_th = fields.CharField(max_length=255)  # ชื่อหมู่บ้าน ภาษาไทย (vname)
    village_name_en = fields.CharField(max_length=255, null=True)  # ชื่อหมู่บ้าน ภาษาอังกฤษ ถ้ามี
    metro_status = fields.CharField(max_length=50, null=True)  # สถานะเมือง/ชนบท (v_metro)

    subdistrict = fields.ForeignKeyField(
        "models.Subdistrict",
        related_name="villages",
        to_field="subdistrict_code",
    )  # อ้างอิงตำบล (TambonId)

    government_id = fields.CharField(max_length=50, null=True, index=True)  # รหัสหน่วยงาน (GovId)
    latitude = fields.FloatField(null=True)  # พิกัดละติจูด
    longitude = fields.FloatField(null=True)  # พิกัดลองจิจูด

    health_service = fields.ForeignKeyField(
        "models.HealthService",
        related_name="villages",
        to_field="health_service_code",
        null=True,
    )  # รหัสหน่วยบริการ (hosp_id)

    external_url = fields.CharField(max_length=255, null=True)  # ที่อยู่เว็บไซต์ (url)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "villages"


