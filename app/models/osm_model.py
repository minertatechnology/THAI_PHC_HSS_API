from tortoise import fields, models
from uuid import uuid4
from app.models.enum_models import (
    Gender,
    NewRegistrationAllowanceStatusEnum,
    VolunteerStatusEnum,
    NonFormalEducationLevelEnum,
    ApprovalStatus,
    OSMRetirementReasonEnum,
    MaritalStatusEnum,
    BloodTypeEnum,
    AllowanceConfirmationStatusEnum,
    AdministrativeLevelEnum,
    OsmStatusEnum,
    OsmShowbbodyEnum,
)




class OsmCodeCounter(models.Model):
    """Atomic counter for generating unique OSM codes per area prefix."""

    prefix = fields.CharField(max_length=32, pk=True)
    last_number = fields.IntField(default=0)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "osm_code_counters"


class OSMProfile(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)

    osm_code = fields.CharField(max_length=50, index=True, null=True)
    citizen_id = fields.CharField(max_length=13, index=True)

    prefix = fields.ForeignKeyField("models.Prefix", related_name="osm_profiles")
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    gender = fields.CharEnumField(Gender, default=Gender.OTHER)
    birth_date = fields.DateField(index=True, null=True)
    email = fields.CharField(max_length=255, null=True, index=True)
    phone = fields.CharField(max_length=50, null=True)
    profile_image = fields.CharField(max_length=1024, null=True)
    new_registration_allowance_status = fields.CharEnumField(NewRegistrationAllowanceStatusEnum, default=NewRegistrationAllowanceStatusEnum.REJECTED)
    is_allowance_supported = fields.BooleanField(default=False)  
    allowance_year = fields.IntField(null=True)
    allowance_months = fields.IntField(null=True)
    password_hash = fields.CharField(max_length=255, null=True)
    is_first_login = fields.BooleanField(default=True)
    password_attempts = fields.IntField(default=0)

    occupation = fields.ForeignKeyField("models.Occupation", related_name="osm_profiles")
    education = fields.ForeignKeyField("models.Education", related_name="osm_profiles")

    non_formal_education_level = fields.CharEnumField(NonFormalEducationLevelEnum, default=NonFormalEducationLevelEnum.NOT_STUDY)
    marital_status = fields.CharEnumField(MaritalStatusEnum, default=MaritalStatusEnum.SINGLE)
    number_of_children = fields.IntField(default=0)
    blood_type = fields.CharEnumField(BloodTypeEnum, default=BloodTypeEnum.OTHER)

    health_service = fields.ForeignKeyField("models.HealthService", related_name="osm_profiles", null=True)
    volunteer_status = fields.CharEnumField(VolunteerStatusEnum, default=VolunteerStatusEnum.NOT_INTERESTED)
    bank = fields.ForeignKeyField("models.Bank", related_name="osm_profiles", null=True)
    bank_account_number = fields.CharField(max_length=50, null=True)

    is_smartphone_owner = fields.BooleanField(default=False)
    address_number = fields.CharField(max_length=100)
    province = fields.ForeignKeyField("models.Province", related_name="osm_profiles", to_field="province_code", null=True)
    district = fields.ForeignKeyField("models.District", related_name="osm_profiles", to_field="district_code", null=True)
    subdistrict = fields.ForeignKeyField("models.Subdistrict", related_name="osm_profiles", to_field="subdistrict_code", null=True)
    village_no = fields.CharField(max_length=10, null=True)
    village_name = fields.CharField(max_length=255, null=True)
    village_code = fields.CharField(max_length=10, null=True)   
    alley = fields.CharField(max_length=255, null=True)
    street = fields.CharField(max_length=255, null=True)
    postal_code = fields.CharField(max_length=10, null=True)

    is_active = fields.BooleanField(default=False)
    osm_status = fields.CharEnumField(
        OsmStatusEnum,
        null=True,
        description="สถานะ อสม. (OsmStatusEnum: ''=ปกติ, 0=เสียชีวิต, 1=ลาออก, 2=พ้นสภาพ)",
        index=True,
    )
    osm_showbbody = fields.CharEnumField(
        OsmShowbbodyEnum,
        null=True,
        description="สถานะเงินเยียวยา/ค่าป่วยการ (1/2=ได้รับ, 5=ไม่ได้รับ, 6=รอ)",
        index=True,
    )
    osm_year = fields.IntField(null=True)
    approval_date = fields.DateField(null=True)
    approval_by = fields.CharField(max_length=255, null=True)
    user_key = fields.CharField(max_length=20, null=True)
    approval_status = fields.CharEnumField(ApprovalStatus, default=ApprovalStatus.PENDING)

    retirement_date = fields.DateField(null=True)
    retirement_reason = fields.CharEnumField(OSMRetirementReasonEnum, null=True)
    is_legacy_data = fields.BooleanField(default=False)
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "osm_profiles"


class OsmSpouse(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField("models.OSMProfile", related_name="osm_spouses_profile")
    citizen_id = fields.CharField(max_length=13, index=True, unique=True)
    prefix = fields.ForeignKeyField("models.Prefix", related_name="osm_spouses_prefix")
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    phone = fields.CharField(max_length=50, null=True)
    email = fields.CharField(max_length=255, null=True)
    gender = fields.CharEnumField(Gender, default=Gender.OTHER)
    birth_date = fields.DateField(index=True, null=True)
    occupation = fields.ForeignKeyField("models.Occupation", related_name="osm_spouses_occupation")
    education = fields.ForeignKeyField("models.Education", related_name="osm_spouses_education")
    blood_type = fields.CharEnumField(BloodTypeEnum, default=BloodTypeEnum.OTHER)
    address_number = fields.CharField(max_length=100)
    alley = fields.CharField(max_length=255, null=True)
    street = fields.CharField(max_length=255, null=True)
    village_no = fields.CharField(max_length=10, null=True)
    village_name = fields.CharField(max_length=255, null=True)
    village_code = fields.CharField(max_length=10, null=True)   
    province = fields.ForeignKeyField("models.Province", related_name="osm_spouses_province")
    district = fields.ForeignKeyField("models.District", related_name="osm_spouses_district")
    subdistrict = fields.ForeignKeyField("models.Subdistrict", related_name="osm_spouses_subdistrict")
    postal_code = fields.CharField(max_length=10, null=True)

    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "osm_spouses"

class OsmChild(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField("models.OSMProfile", related_name="osm_children_profile")
    order_of_children = fields.IntField(null=True)
    citizen_id = fields.CharField(max_length=13, index=True, null=True)
    prefix = fields.ForeignKeyField("models.Prefix", related_name="osm_children_prefix")
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    phone = fields.CharField(max_length=50, null=True)
    email = fields.CharField(max_length=255, null=True)
    gender = fields.CharEnumField(Gender, default=Gender.OTHER)
    birth_date = fields.DateField(index=True, null=True)
    occupation = fields.ForeignKeyField(
        "models.Occupation",
        related_name="osm_children_occupation",
        null=True,
    )
    education = fields.ForeignKeyField(
        "models.Education",
        related_name="osm_children_education",
        null=True,
    )
    blood_type = fields.CharEnumField(
        BloodTypeEnum,
        default=None,
        null=True,
    )
    address_number = fields.CharField(max_length=100)
    alley = fields.CharField(max_length=255, null=True)
    street = fields.CharField(max_length=255, null=True)
    village_no = fields.CharField(max_length=10, null=True)
    village_name = fields.CharField(max_length=255, null=True)
    village_code = fields.CharField(max_length=10, null=True)   
    province = fields.ForeignKeyField("models.Province", related_name="osm_children_province")
    district = fields.ForeignKeyField("models.District", related_name="osm_children_district")
    subdistrict = fields.ForeignKeyField("models.Subdistrict", related_name="osm_children_subdistrict")
    postal_code = fields.CharField(max_length=10, null=True)

    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "osm_children"

class OsmOutstanding(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField("models.OSMProfile", related_name="osm_outstandings_profile")
    award_level = fields.ForeignKeyField("models.AwardLevel", related_name="osm_outstandings_award_level", null=True)
    award_category = fields.ForeignKeyField("models.AwardCategory", related_name="osm_outstandings_award_category", null=True)
    award_year = fields.IntField()
    title = fields.CharField(max_length=500, null=True)  # ชื่อผลงานดีเด่น
    description = fields.TextField(null=True)  # รายละเอียดผลงาน

    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "osm_outstandings"


class OsmOutstandingImage(models.Model):
    """ใบประกาศนียบัตร / รูปภาพแนบของข้อมูลดีเด่น"""
    id = fields.UUIDField(pk=True, default=uuid4)
    outstanding = fields.ForeignKeyField(
        "models.OsmOutstanding",
        related_name="images",
        on_delete=fields.CASCADE,
    )
    image_url = fields.CharField(max_length=1024)  # relative path เช่น uploads/outstanding-certificates/xxx.jpg
    sort_order = fields.IntField(default=0)
    caption = fields.CharField(max_length=500, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "osm_outstanding_images"
        ordering = ["sort_order", "created_at"]

class OsmPin(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField("models.OSMProfile", related_name="osm_pins_profile")
    pin = fields.ForeignKeyField("models.Pin", related_name="osm_pins_pin")
    received_pin_year = fields.IntField()

    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "osm_pins"

class OsmLeadershipPosition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField("models.OSMProfile", related_name="osm_leadership_positions_profile")
    leadership_position = fields.ForeignKeyField("models.LeadershipPosition", related_name="osm_leadership_positions_leadership_position")

    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)    

    class Meta:
        table = "osm_leadership_positions"


class OsmOfficialPosition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    position_name_th = fields.CharField(max_length=255, index=True)
    position_name_en = fields.CharField(max_length=255, null=True)
    legacy_code = fields.IntField(null=True, unique=True, index=True)
    position_level = fields.CharEnumField(AdministrativeLevelEnum, null=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.CharField(max_length=255, null=True, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_official_positions"


class OsmProfileOfficialPosition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField(
        "models.OSMProfile",
        related_name="official_position_links",
    )
    official_position = fields.ForeignKeyField(
        "models.OsmOfficialPosition",
        related_name="profile_assignments",
    )
    custom_title = fields.CharField(max_length=255, null=True)
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_profile_official_positions"


class OsmSpecialSkill(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    skill_name_th = fields.CharField(max_length=255, index=True)
    skill_name_en = fields.CharField(max_length=255, null=True)
    legacy_code = fields.IntField(null=True, unique=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.CharField(max_length=255, null=True, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_special_skills"


class OsmProfileSpecialSkill(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField(
        "models.OSMProfile",
        related_name="special_skill_links",
    )
    special_skill = fields.ForeignKeyField(
        "models.OsmSpecialSkill",
        related_name="profile_assignments",
    )
    custom_skill = fields.CharField(max_length=255, null=True)
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_profile_special_skills"


class OsmClubPosition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    position_name_th = fields.CharField(max_length=255, index=True)
    position_name_en = fields.CharField(max_length=255, null=True)
    legacy_code = fields.IntField(null=True, unique=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.CharField(max_length=255, null=True, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_club_positions"


class OsmProfileClubPosition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField(
        "models.OSMProfile",
        related_name="club_position_links",
    )
    club_position = fields.ForeignKeyField(
        "models.OsmClubPosition",
        related_name="profile_assignments",
    )
    appointed_level = fields.CharField(max_length=255, null=True)
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_profile_club_positions"


class OsmTrainingCourse(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    course_name_th = fields.CharField(max_length=255, index=True)
    course_name_en = fields.CharField(max_length=255, null=True)
    legacy_code = fields.IntField(null=True, unique=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.CharField(max_length=255, null=True, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_training_courses"


class OsmProfileTraining(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField(
        "models.OSMProfile",
        related_name="training_records",
    )
    training_course = fields.ForeignKeyField(
        "models.OsmTrainingCourse",
        related_name="profile_assignments",
        null=True,
        on_delete=fields.SET_NULL,
    )
    trained_year = fields.IntField(null=True, index=True)
    topic = fields.CharField(max_length=255, null=True)
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_profile_trainings"


class OsmBenefitClaim(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField(
        "models.OSMProfile",
        related_name="benefit_claims",
    )
    claim_type = fields.CharField(max_length=50, index=True)
    claim_date = fields.DateField(index=True)
    claim_round = fields.IntField(null=True)
    amount = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    status = fields.CharField(max_length=30, index=True)
    decision_date = fields.DateField(null=True, index=True)
    paid_date = fields.DateField(null=True, index=True)
    note = fields.TextField(null=True)
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_benefit_claims"


class OsmAward(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField(
        "models.OSMProfile",
        related_name="awards",
    )
    award_type = fields.CharField(max_length=50, index=True)
    award_name = fields.CharField(max_length=255, null=True)
    award_code = fields.CharField(max_length=50, null=True, index=True)
    awarded_date = fields.DateField(index=True)
    criteria = fields.TextField(null=True)
    issuer = fields.CharField(max_length=255, null=True)
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_awards"


class OsmPositionConfirmation(models.Model):
    """
    ตารางการยืนยันตำแหน่งและสิทธิ์เงินค่าป่วยการ อสม.
    """
    id = fields.UUIDField(pk=True, default=uuid4)
    
    # อ้างอิง OSM Profile
    osm_profile = fields.ForeignKeyField("models.OSMProfile", related_name="position_confirmations")
    
    # ตำแหน่งที่ยืนยัน (หลายตำแหน่ง)
    osm_positions = fields.ManyToManyField(
        "models.OsmPosition", 
        related_name="osm_position_confirmations",
        through="osm_position_confirmation_positions"
    )
    
    # สถานะการยืนยันสิทธิ์เงินค่าป่วยการ
    allowance_confirmation_status = fields.CharEnumField(
        AllowanceConfirmationStatusEnum, 
        default=AllowanceConfirmationStatusEnum.NOT_CONFIRMED,
        description="สถานะการยืนยันสิทธิ์เงินค่าป่วยการ"
    )
    
    # Audit fields
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "osm_position_confirmations"


class OsmPositionConfirmationPosition(models.Model):
    """
    ตารางเชื่อมโยงระหว่าง OsmPositionConfirmation และ LeadershipPosition (Many-to-Many)
    """
    id = fields.UUIDField(pk=True, default=uuid4)
    
    position_confirmation = fields.ForeignKeyField(
        "models.OsmPositionConfirmation", 
        related_name="confirmation_positions"
    )
    osm_position = fields.ForeignKeyField(
        "models.OsmPosition", 
        related_name="confirmation_positions"
    )
    # Audit fields
    created_by = fields.CharField(max_length=255, null=False, index=True)
    updated_by = fields.CharField(max_length=255, null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "osm_position_confirmation_positions"


#ตารางตำแหน่งประธานของ อสม.
class LeadershipPosition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    position_name_th = fields.CharField(max_length=255, index=True) # ชื่อตำแหน่ง ภาษาไทย
    position_name_en = fields.CharField(max_length=255, null=True) # ชื่อตำแหน่ง ภาษาอังกฤษ
    
    position_level = fields.CharEnumField(AdministrativeLevelEnum, index=True) # ระดับตำแหน่ง
    legacy_id = fields.IntField(null=True)
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "leadership_positions"
    
class OsmPosition(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    position_name_th = fields.CharField(max_length=255, index=True) # ชื่อตำแหน่ง ภาษาไทย
    position_name_en = fields.CharField(max_length=255, null=True) # ชื่อตำแหน่ง ภาษาอังกฤษ
    
    position_level = fields.CharEnumField(AdministrativeLevelEnum, index=True, null=True) # ระดับตำแหน่ง
    legacy_id = fields.IntField(null=True)
    
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "osm_positions"


class OsmStatusHistory(models.Model):
    """ประวัติการเปลี่ยนแปลง osm_status / is_active ของ อสม.
    ใช้ติดตามเส้นทางสถานะ เช่น ปกติ → พ้นสภาพ → ย้ายที่อยู่ → กลับเป็นปกติ"""

    id = fields.UUIDField(pk=True, default=uuid4)
    osm_profile = fields.ForeignKeyField(
        "models.OSMProfile",
        related_name="status_history",
        on_delete=fields.CASCADE,
        index=True,
    )

    # snapshot ค่าก่อน-หลัง
    previous_osm_status = fields.CharField(max_length=10, null=True)
    new_osm_status = fields.CharField(max_length=10, null=True)
    previous_is_active = fields.BooleanField(null=True)
    new_is_active = fields.BooleanField()
    previous_approval_status = fields.CharField(max_length=20, null=True)
    new_approval_status = fields.CharField(max_length=20, null=True)

    # ข้อมูลพื้นที่ ณ ขณะเปลี่ยน (snapshot เพื่อ track ย้ายที่อยู่)
    province_code = fields.CharField(max_length=6, null=True, index=True)
    district_code = fields.CharField(max_length=8, null=True)
    subdistrict_code = fields.CharField(max_length=10, null=True)
    village_no = fields.CharField(max_length=10, null=True)

    # เหตุผล
    retirement_reason = fields.CharField(max_length=50, null=True)
    remark = fields.CharField(max_length=500, null=True)

    # ผู้กระทำ
    changed_by = fields.UUIDField(index=True)
    changed_by_name = fields.CharField(max_length=100, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "osm_status_history"
        ordering = ["-created_at"]