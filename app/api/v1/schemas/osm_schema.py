from pydantic import BaseModel, Field, validator
from typing import Optional, List
import datetime
from datetime import date
import uuid


class OsmBatchIdsSchema(BaseModel):
    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="OSM profile IDs to fetch",
    )

class SpouseSchema(BaseModel):
    citizen_id: str = Field(..., min_length=13, max_length=13, description="เลขบัตรประชาชน")
    prefix_id: uuid.UUID = Field(..., description="ID ของคำนำหน้า")
    first_name: str = Field(..., max_length=100, description="ชื่อ")
    last_name: str = Field(..., max_length=100, description="นามสกุล")
    phone: Optional[str] = Field(None, max_length=50, description="เบอร์โทรศัพท์")
    email: Optional[str] = Field(None, max_length=255, description="อีเมล")
    profile_image: Optional[str] = Field(None, max_length=1024, description="URL รูปโปรไฟล์")
    gender: str = Field(..., description="เพศ")
    birth_date: datetime.date = Field(..., description="วันเกิด")
    occupation_id: Optional[uuid.UUID] = Field(
        None,
        description="ID ของอาชีพ (ไม่ระบุก็ได้)"
    )
    education_id: Optional[uuid.UUID] = Field(
        None,
        description="ID ของการศึกษา (ไม่ระบุก็ได้)"
    )
    blood_type: Optional[str] = Field(
        None,
        description="หมู่เลือด (ไม่ระบุก็ได้)"
    )
    address_number: str = Field(..., max_length=100, description="เลขที่")
    alley: Optional[str] = Field(None, max_length=255, description="ซอย")
    street: Optional[str] = Field(None, max_length=255, description="ถนน")
    village_no: Optional[str] = Field(None, max_length=10, description="หมู่ที่")
    village_name: Optional[str] = Field(None, max_length=255, description="ชื่อหมู่บ้าน")
    province_id: str = Field(..., description="รหัสจังหวัด")
    district_id: str = Field(..., description="รหัสอำเภอ")
    subdistrict_id: str = Field(..., description="รหัสตำบล")
    postal_code: str = Field(..., max_length=10, description="รหัสไปรษณีย์")

class ChildSchema(BaseModel):
    citizen_id: Optional[str] = Field(None, min_length=13, max_length=13, description="เลขบัตรประชาชน")
    order_of_children: int = Field(..., ge=1, description="ลำดับบุตร")
    prefix_id: uuid.UUID = Field(..., description="ID ของคำนำหน้า")
    first_name: str = Field(..., max_length=100, description="ชื่อ")
    last_name: str = Field(..., max_length=100, description="นามสกุล")
    phone: Optional[str] = Field(None, max_length=50, description="เบอร์โทรศัพท์")
    email: Optional[str] = Field(None, max_length=255, description="อีเมล")
    gender: str = Field(..., description="เพศ")
    birth_date: datetime.date = Field(..., description="วันเกิด")
    occupation_id: Optional[uuid.UUID] = Field(
        None,
        description="ID ของอาชีพ (ไม่ระบุก็ได้)"
    )
    education_id: Optional[uuid.UUID] = Field(
        None,
        description="ID ของการศึกษา (ไม่ระบุก็ได้)"
    )
    blood_type: Optional[str] = Field(
        None,
        description="หมู่เลือด (ไม่ระบุก็ได้)"
    )
    address_number: str = Field(..., max_length=100, description="เลขที่")
    alley: Optional[str] = Field(None, max_length=255, description="ซอย")
    street: Optional[str] = Field(None, max_length=255, description="ถนน")
    village_no: Optional[str] = Field(None, max_length=10, description="หมู่ที่")
    village_name: Optional[str] = Field(None, max_length=255, description="ชื่อหมู่บ้าน")
    province_id: str = Field(..., description="รหัสจังหวัด")
    district_id: str = Field(..., description="รหัสอำเภอ")
    subdistrict_id: str = Field(..., description="รหัสตำบล")
    postal_code: str = Field(..., max_length=10, description="รหัสไปรษณีย์")


class OfficialPositionItem(BaseModel):
    position_id: uuid.UUID = Field(..., description="ID ของตำแหน่งทางการ/ไม่ทางการ")
    custom_title: Optional[str] = Field(
        None,
        max_length=255,
        description="รายละเอียดเพิ่มเติมเมื่อเลือก 'อื่นๆ'",
    )


class SpecialSkillItem(BaseModel):
    skill_id: uuid.UUID = Field(..., description="ID ของความชำนาญพิเศษ")
    custom_skill: Optional[str] = Field(
        None,
        max_length=255,
        description="รายละเอียดเพิ่มเติมเมื่อเลือก 'อื่นๆ'",
    )


class ClubPositionItem(BaseModel):
    club_position_id: uuid.UUID = Field(..., description="ID ของตำแหน่งชมรม อสม.")
    appointed_level: Optional[str] = Field(
        None,
        max_length=255,
        description="รายละเอียดระดับ/พื้นที่ถ้ามี",
    )


class TrainingRecord(BaseModel):
    course_id: Optional[uuid.UUID] = Field(
        None,
        description="ID ของหลักสูตรที่อบรม",
    )
    trained_year: Optional[int] = Field(
        None,
        ge=2500,
        le=2700,
        description="ปีที่อบรม",
    )
    topic: Optional[str] = Field(
        None,
        max_length=255,
        description="หัวข้อหรือเนื้อหาเพิ่มเติม",
    )

class OsmDetailSchema(BaseModel):
    # Basic Information
    citizen_id: str = Field(..., min_length=13, max_length=13, description="เลขบัตรประชาชน")
    prefix_id: uuid.UUID = Field(..., description="ID ของคำนำหน้า")
    first_name: str = Field(..., max_length=100, description="ชื่อ")
    last_name: str = Field(..., max_length=100, description="นามสกุล")
    phone: Optional[str] = Field(None, max_length=50, description="เบอร์โทรศัพท์")
    email: Optional[str] = Field(None, max_length=255, description="อีเมล")
    profile_image: Optional[str] = Field(None, max_length=1024, description="URL รูปโปรไฟล์")
    gender: str = Field(..., description="เพศ")
    osm_year: int = Field(..., ge=2500, le=2600, description="ปีที่เริ่มเป็น อสม.")
    birth_date: datetime.date = Field(..., description="วันเกิด")
    marital_status: str = Field(..., description="สถานะการสมรส")
    number_of_children: int = Field(..., ge=0, description="จำนวนบุตร")
    health_service_id: str = Field(..., description="รหัสสถานบริการสุขภาพ")
    bank_id: Optional[uuid.UUID] = Field(None, description="ID ของธนาคาร")
    bank_account_number: Optional[str] = Field(None, max_length=50, description="เลขบัญชีธนาคาร")
    volunteer_status: str = Field(..., description="สถานะอาสาสมัคร")
    is_smartphone_owner: bool = Field(..., description="เป็นเจ้าของสมาร์ทโฟน")

    osm_showbbody: Optional[str] = Field(
        None,
        description="สถานะเงินเยียวยา/ค่าป่วยการ (OsmShowbbodyEnum: 1/2=ได้รับ,5=ไม่ได้รับ,6=รอ)",
    )
    showbody: Optional[str] = Field(
        None,
        description="alias ของ osm_showbbody (รองรับ client ที่ส่งชื่อ showbody)",
    )

    new_registration_allowance_status: Optional[str] = Field(
        None,
        description="สถานะสิทธิ์ค่าป่วยการตอนสมัครใหม่ (เช่น accepted/rejected/pending)",
    )

    # Occupation and Education
    occupation_id: uuid.UUID = Field(..., description="ID ของอาชีพ")
    education_id: uuid.UUID = Field(..., description="ID ของการศึกษา")
    blood_type: str = Field(..., description="หมู่เลือด")

    # Address
    address_number: str = Field(..., max_length=100, description="เลขที่")
    alley: Optional[str] = Field(None, max_length=255, description="ซอย")
    street: Optional[str] = Field(None, max_length=255, description="ถนน")
    village_no: Optional[str] = Field(None, max_length=10, description="หมู่ที่")
    village_name: Optional[str] = Field(None, max_length=255, description="ชื่อหมู่บ้าน")

    # Province, District, Subdistrict
    province_id: str = Field(..., description="รหัสจังหวัด")
    district_id: str = Field(..., description="รหัสอำเภอ")
    subdistrict_id: str = Field(..., description="รหัสตำบล")
    postal_code: str = Field(..., max_length=10, description="รหัสไปรษณีย์")

    # Spouse
    spouse: Optional[SpouseSchema] = Field(None, description="ข้อมูลคู่สมรส")

    # Children
    children: Optional[List[ChildSchema]] = Field(None, description="ข้อมูลบุตร")
    official_positions: Optional[List[OfficialPositionItem]] = Field(
        None,
        description="ตำแหน่งทางการ/ไม่ทางการที่เกี่ยวข้อง",
    )
    special_skills: Optional[List[SpecialSkillItem]] = Field(
        None,
        description="ความชำนาญหรือความสามารถพิเศษ",
    )
    club_positions: Optional[List[ClubPositionItem]] = Field(
        None,
        description="ตำแหน่งในชมรม อสม.",
    )
    trainings: Optional[List[TrainingRecord]] = Field(
        None,
        description="ข้อมูลการอบรมหลักสูตรของ อสม.",
    )

    @validator('citizen_id')
    def validate_citizen_id(cls, v):
        if not v.isdigit():
            raise ValueError('เลขบัตรประชาชนต้องเป็นตัวเลขเท่านั้น')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('-', '').replace(' ', '').isdigit():
            raise ValueError('เบอร์โทรศัพท์ต้องเป็นตัวเลขเท่านั้น')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('รูปแบบอีเมลไม่ถูกต้อง')
        return v

class OsmCreateSchema(OsmDetailSchema):
    osm_year: Optional[int] = Field(None, ge=2500, le=2600, description="ปีที่เริ่มเป็น อสม. (ไม่บังคับตอนสร้าง จะตั้งค่าตอนอนุมัติ)")

class OsmUpdateSchema(BaseModel):
    # Optional fields for update (same structure as creation but all nullable)
    citizen_id: Optional[str] = Field(None, min_length=13, max_length=13)
    prefix_id: Optional[uuid.UUID] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    profile_image: Optional[str] = Field(None, max_length=1024)
    gender: Optional[str] = None
    osm_year: Optional[int] = Field(None, ge=2500, le=2600)
    birth_date: Optional[datetime.date] = None
    marital_status: Optional[str] = None
    number_of_children: Optional[int] = Field(None, ge=0)
    health_service_id: Optional[str] = None
    bank_id: Optional[uuid.UUID] = None
    bank_account_number: Optional[str] = Field(None, max_length=50)
    volunteer_status: Optional[str] = None
    is_smartphone_owner: Optional[bool] = None
    osm_showbbody: Optional[str] = None
    showbody: Optional[str] = None
    new_registration_allowance_status: Optional[str] = None
    occupation_id: Optional[uuid.UUID] = None
    education_id: Optional[uuid.UUID] = None
    blood_type: Optional[str] = None
    address_number: Optional[str] = Field(None, max_length=100)
    alley: Optional[str] = Field(None, max_length=255)
    street: Optional[str] = Field(None, max_length=255)
    village_no: Optional[str] = Field(None, max_length=10)
    village_name: Optional[str] = Field(None, max_length=255)
    province_id: Optional[str] = None
    district_id: Optional[str] = None
    subdistrict_id: Optional[str] = None
    postal_code: Optional[str] = Field(None, max_length=10)

    # Nested relation fields — ถ้าส่งมาจะทำ replace/sync ตามรายการที่ส่งมา
    spouse: Optional[SpouseSchema] = Field(
        None,
        description="ข้อมูลคู่สมรส (ถ้าส่งมาจะ upsert, ถ้าส่ง null จะลบ)",
    )
    children: Optional[List[ChildSchema]] = Field(
        None,
        description="ข้อมูลบุตร (ถ้าส่งมาจะ replace ทั้งหมด)",
    )
    official_positions: Optional[List[OfficialPositionItem]] = Field(
        None,
        description="ตำแหน่งทางการ/ไม่ทางการ (ถ้าส่งมาจะ replace ทั้งหมด)",
    )
    special_skills: Optional[List[SpecialSkillItem]] = Field(
        None,
        description="ความชำนาญพิเศษ (ถ้าส่งมาจะ replace ทั้งหมด)",
    )
    club_positions: Optional[List[ClubPositionItem]] = Field(
        None,
        description="ตำแหน่งชมรม อสม. (ถ้าส่งมาจะ replace ทั้งหมด)",
    )
    trainings: Optional[List[TrainingRecord]] = Field(
        None,
        description="ข้อมูลการอบรมหลักสูตรของ อสม. (ถ้าส่งมาใน PUT จะทำการ replace/sync ตามรายการที่ส่งมา)",
    )
    osm_registered_date: Optional[datetime.date] = Field(
        None,
        description="วันที่ลงทะเบียน อสม.",
    )

    @validator('citizen_id')
    def validate_optional_citizen_id(cls, v):
        if v and not v.isdigit():
            raise ValueError('เลขบัตรประชาชนต้องเป็นตัวเลขเท่านั้น')
        return v

    @validator('phone')
    def validate_optional_phone(cls, v):
        if v and not v.replace('-', '').replace(' ', '').isdigit():
            raise ValueError('เบอร์โทรศัพท์ต้องเป็นตัวเลขเท่านั้น')
        return v

    @validator('email')
    def validate_optional_email(cls, v):
        if v and '@' not in v:
            raise ValueError('รูปแบบอีเมลไม่ถูกต้อง')
        return v

# Position Confirmation Schemas
class OsmPositionConfirmationCreateSchema(BaseModel):
    osm_profile_id: str = Field(..., description="ID ของ OSM Profile")
    osm_position_ids: List[str] = Field(..., description="รายการ ID ของตำแหน่งที่เลือก")
    allowance_confirmation_status: str = Field(..., description="สถานะการยืนยันสิทธิ์เงินค่าป่วยการ")

class OsmPositionConfirmationUpdateSchema(BaseModel):
    osm_position_ids: Optional[List[str]] = Field(None, description="รายการ ID ของตำแหน่งที่เลือก")
    allowance_confirmation_status: Optional[str] = Field(None, description="สถานะการยืนยันสิทธิ์เงินค่าป่วยการ")

class OsmPositionConfirmationResponse(BaseModel):
    id: str
    osm_profile_id: str
    osm_profile_name: str
    osm_position_names: List[str]
    allowance_confirmation_status: str
    created_at: str
    updated_at: str

class OsmPositionResponse(BaseModel):
    id: str
    position_name_th: str
    position_name_en: Optional[str]
    position_level: str

class SimpleResponse(BaseModel):
    status: str
    message: str


class OsmActiveStatusSchema(BaseModel):
    is_active: bool = Field(..., description="สถานะเปิดใช้งานของบัญชี OSM")
    approval_status: Optional[str] = Field(
        default=None,
        description="สถานะการอนุมัติ (approved/pending/rejected). ไม่ระบุจะ derive จาก is_active",
    )
    osm_status: Optional[str] = Field(
        default=None,
        description="รหัสสถานะ อสม. (OsmStatusEnum: ''=ปกติ, 0=เสียชีวิต, 1=ลาออก, 2=พ้นสภาพ)"
    )
    osm_showbbody: Optional[str] = Field(
        default=None,
        description="สถานะเงินเยียวยา/ค่าป่วยการ (OsmShowbbodyEnum: 1/2=ได้รับ,5=ไม่ได้รับ,6=รอ)"
    )
    retirement_date: Optional[date] = Field(
        default=None,
        description="วันที่พ้นสภาพ/ลาออก หาก osm_status ระบุว่าออกหรือเสียชีวิต จะใช้ค่านี้ (ไม่ส่งจะ default วันนี้)"
    )
    retirement_reason: Optional[str] = Field(
        default=None,
        description="เหตุผลการลาออก (OSMRetirementReasonEnum)"
    )