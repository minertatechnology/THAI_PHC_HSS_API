from tortoise import fields, models
from uuid import uuid4
from app.models.enum_models import AdministrativeLevelEnum


# ตารางระดับดีเด่น
class AwardLevel(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    award_level_name = fields.CharField(max_length=255, index=True) # ระดับดีเด่น เช่น ดีเด่นระดับหมู่บ้าน, ดีเด่นระดับตำบล, ดีเด่นระดับอำเภอ, ดีเด่นระดับจังหวัด, ดีเด่นระดับภาค, ดีเด่นระดับประเทศ
    award_level = fields.CharEnumField(AdministrativeLevelEnum, index=True) # ระดับดีเด่น
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "award_levels"

# ตารางประเภทดีเด่น
class AwardCategory(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    award_category_name = fields.CharField(max_length=255, index=True)
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "award_categories"



# ตารางเข็ม
class Pin(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    pin_name_th = fields.CharField(max_length=255, index=True) # ชื่อเข็มภาษาไทย
    pin_name_en = fields.CharField(max_length=255, null=True) # ชื่อเข็มภาษาอังกฤษ
    legacy_id = fields.IntField(null=True)
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "pins"

# หมวดหมู่การอบรม
class TrainingCategory(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    training_category_name_th = fields.CharField(max_length=255, index=True) # ชื่อประเภทการอบรม ภาษาไทย
    training_category_name_en = fields.CharField(max_length=255, null=True) # ชื่อประเภทการอบรม ภาษาอังกฤษ
    legacy_id = fields.IntField(null=True)
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "training_categories"

# ตารางการอบรม
class Training(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    training_name_th = fields.CharField(max_length=255, index=True) # ชื่อการอบรม ภาษาไทย
    training_name_en = fields.CharField(max_length=255, null=True) # ชื่อการอบรม ภาษาอังกฤษ
    legacy_id = fields.IntField(null=True)
    training_category: fields.ForeignKeyRelation["TrainingCategory"] = fields.ForeignKeyField(
        "models.TrainingCategory", related_name="trainings", index=True
    )
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "trainings"
