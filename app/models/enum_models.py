from enum import Enum


class Gender(str, Enum):
        MALE = "male" # ชาย
        FEMALE = "female" # หญิง
        OTHER = "other" # อื่นๆ

class ApprovalStatus(str, Enum):
    PENDING = "pending" # รออนุมัติ
    APPROVED = "approved" # อนุมัติ
    REJECTED = "rejected" # ยกเลิก
    RETIRED = "retired" # พ้นสภาพ

class VolunteerStatusEnum(str, Enum):
    ALREADY_VOLUNTEER = "already_volunteer" # เป็นจิตอาสาอยู่แล้ว
    WANTS_TO_BE_VOLUNTEER = "wants_to_be_volunteer" # ประสงค์เป็นจิตอาสา
    NOT_INTERESTED = "not_interested" # ไม่ประสงค์เป็นจิตอาสา

class NonFormalEducationLevelEnum(str, Enum):
    NOT_STUDY = "not_study" # ไม่เรียน
    PRIMARY = "primary" # เรียน กศน. ระดับประถม
    JUNIOR_HIGH = "junior_high" # เรียน กศน. ระดับ ม.ต้น
    SENIOR_HIGH = "senior_high" # เรียน กศน. ระดับ ม.ปลาย
    VOCATIONAL = "vocational" # เรียน กศน. ระดับสายอาชีพ
    HIGHER_EDUCATION = "higher_education" # เรียน กศน. ระดับอุดมศึกษา

class NewRegistrationAllowanceStatusEnum(str, Enum):
    ACCEPTED = "accepted" # รับสิทธิ์
    ACCEPTED_WITH_INCOMPLETE_PROOF = "accepted_with_incomplete_proof" # ได้รับการยืนยัน แต่หลักฐานไม่ครบ
    NOT_VERIFIED_IDENTITY = "not_verified_identity" # ยังไม่มายืนยันตน
    NEW_OSM_2553 = "new_osm_2553" # เป็น อสม ใหม่ปี 2553 
    REJECTED = "rejected" # ไม่รับสิทธิ์
    PENDING = "pending" # รอรับสิทธิ์

class OSMRetirementReasonEnum(str, Enum):
    DIED = "died"
    RESIGNED = "resigned"
    MOVED_OR_ABSENT = "moved_or_absent"
    SICK_OR_DISABLED = "sick_or_disabled"
    NEVER_PARTICIPATED_IN_OSM_ACTIVITIES = "never_participated_in_osm_activities"
    COMMUNITY_REQUESTS_REMOVAL = "community_requests_removal"
    BEHAVIOR_DAMAGING_REPUTATION = "behavior_damaging_reputation"

    # Fallback value to prevent runtime crashes when legacy/dirty data exists in DB.
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        """Tolerate legacy/invalid retirement reason codes.

        Historically some datasets stored MySQL-style codes (OC1..OC7) or other
        variants. Returning a member here prevents ORM/model hydration from
        raising ValueError and taking down API endpoints.
        """
        if value is None:
            return cls.UNKNOWN

        raw = str(value).strip()
        if raw == "":
            return cls.UNKNOWN

        legacy_map = {
            # Legacy MySQL OutCause codes
            "OC1": cls.DIED,
            "OC2": cls.RESIGNED,
            "OC3": cls.MOVED_OR_ABSENT,
            "OC4": cls.SICK_OR_DISABLED,
            "OC5": cls.NEVER_PARTICIPATED_IN_OSM_ACTIVITIES,
            "OC6": cls.COMMUNITY_REQUESTS_REMOVAL,
            "OC7": cls.BEHAVIOR_DAMAGING_REPUTATION,

            # Common data variants
            "community_requests_removals": cls.COMMUNITY_REQUESTS_REMOVAL,
        }

        direct = legacy_map.get(raw)
        if direct is not None:
            return direct

        upper = legacy_map.get(raw.upper())
        if upper is not None:
            return upper

        # Allow case-insensitive matching for canonical values
        lowered = raw.lower()
        for member in cls:
            if member.value == lowered:
                return member

        return cls.UNKNOWN

class AdministrativeLevelEnum(str, Enum):
    """
    ระดับการปกครอง/พื้นที่ในประเทศไทย
    """
    VILLAGE = "village"
    SUBDISTRICT = "subdistrict"
    DISTRICT = "district"
    PROVINCE = "province"
    AREA = "area"
    REGION = "region"
    COUNTRY = "country" 


class MaritalStatusEnum(str, Enum):
    SINGLE = "single" # โสด
    MARRIED = "married" # แต่งงาน
    DIVORCED = "divorced" # หย่าร้าง
    WIDOWED = "widowed" # เป็นหม้าย
    OTHER = "other" # อื่นๆ

class BloodTypeEnum(str, Enum):
    A = "A" # กรุ๊ปเลือด A
    B = "B" # กรุ๊ปเลือด B
    AB = "AB" # กรุ๊ปเลือด AB
    O = "O" # กรุ๊ปเลือด O
    OTHER = "other" # อื่นๆ
    UNKNOWN = "unknown" # ไม่ระบุ

    @classmethod
    def _missing_(cls, value):
        if value is None:
            return cls.UNKNOWN

        raw = str(value).strip()
        if raw == "":
            return cls.UNKNOWN

        alias_map = {
            "special": cls.OTHER,
            "others": cls.OTHER,
            "other": cls.OTHER,
            "unknown": cls.UNKNOWN,
            "not_specified": cls.UNKNOWN,
            "-": cls.UNKNOWN,
        }

        lowered = raw.lower()
        mapped = alias_map.get(lowered)
        if mapped is not None:
            return mapped

        # Accept canonical blood groups case-insensitively.
        upper = raw.upper()
        for member in (cls.A, cls.B, cls.AB, cls.O):
            if member.value == upper:
                return member

        return cls.UNKNOWN

class AllowanceConfirmationStatusEnum(str, Enum):
    """
    สถานะการยืนยันสิทธิ์เงินค่าป่วยการ อสม.
    """
    CONFIRMED_WITH_ALLOWANCE = "confirmed_with_allowance"  # มีเวลาเพียงพอ สามารถปฏิบัติหน้าที่ตามหลักเกณฑ์ และยืนยันขอรับเงินค่าป่วยการ อสม.
    CONFIRMED_WITHOUT_ALLOWANCE = "confirmed_without_allowance"  # มีเวลาเพียงพอ สามารถปฏิบัติหน้าที่ตามหลักเกณฑ์ แต่ไม่ประสงค์รับเงินค่าป่วยการ อสม.
    NOT_CONFIRMED = "not_confirmed"  # ไม่มีเวลาเพียงพอ ในการปฏิบัติหน้าที่ตามหลักเกณฑ์ และไม่ประสงค์รับเงินค่าป่วยการ อสม.


# ---------------------------------------------------------------------------
# สถานะ อสม. (OsmStatus) และสถานะเงินเยียวยา/ค่าป่วยการ (OsmShowbbody)
# รหัสที่ผู้ใช้แจ้ง: OsmStatus ใช้ค่าสั้น ๆ (เช่น 0/1/2) สำหรับ ปกติ/พ้นสภาพ/เสียชีวิต
# OsmShowbbody: 1,2 = ได้รับเงิน, 5 = ไม่ได้รับ, 6 = รอ/ค้างอยู่
# ใช้ str enum เพื่อตรงกับรหัสในฐานข้อมูล
# ---------------------------------------------------------------------------


class OsmStatusEnum(str, Enum):
    ACTIVE = ""  # ปกติ
    DECEASED = "0"  # เสียชีวิต
    MISCONDUCT = "1"  # ลาออก
    RESIGNED = "2"  # พ้นสภาพ


class OsmShowbbodyEnum(str, Enum):
    PAID_TYPE1 = "1"  # ได้รับเงินเยียวยา/ค่าป่วยการ (รูปแบบ 1)
    PAID_TYPE2 = "2"  # ได้รับเงินเยียวยา/ค่าป่วยการ (รูปแบบ 2)
    NOT_PAID = "5"  # ไม่ได้รับเงิน
    PENDING = "6"  # รอ/ค้างอยู่