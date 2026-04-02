from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
from enum import Enum
from app.models.enum_models import AdministrativeLevelEnum


class OfficialPositionResponse(BaseModel):
    assignment_id: uuid.UUID
    position_id: uuid.UUID
    position_name_th: Optional[str]
    position_level: Optional[str]
    legacy_code: Optional[int]
    custom_title: Optional[str]


class SpecialSkillResponse(BaseModel):
    assignment_id: uuid.UUID
    skill_id: uuid.UUID
    skill_name_th: Optional[str]
    legacy_code: Optional[int]
    custom_skill: Optional[str]


class ClubPositionResponse(BaseModel):
    assignment_id: uuid.UUID
    club_position_id: uuid.UUID
    club_position_name_th: Optional[str]
    appointed_level: Optional[str]


class TrainingRecordResponse(BaseModel):
    record_id: uuid.UUID
    course_id: Optional[uuid.UUID]
    course_name_th: Optional[str]
    legacy_code: Optional[int]
    trained_year: Optional[int]
    topic: Optional[str]

class SpouseResponse(BaseModel):
    id: uuid.UUID
    citizen_id: str
    prefix_id: uuid.UUID
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    phone: Optional[str]
    email: Optional[str]
    gender: str
    birth_date: Optional[str] = None
    occupation_id: uuid.UUID
    occupation_name_th: Optional[str]
    education_id: uuid.UUID
    education_name_th: Optional[str]
    blood_type: str
    address_number: str
    alley: Optional[str]
    street: Optional[str]
    village_no: Optional[str]
    village_name: Optional[str]
    province_id: str
    province_name_th: Optional[str]
    district_id: str
    district_name_th: Optional[str]
    subdistrict_id: str
    subdistrict_name_th: Optional[str]
    postal_code: Optional[str]

class ChildResponse(BaseModel):
    id: uuid.UUID
    order_of_children: int
    citizen_id: Optional[str]
    prefix_id: uuid.UUID
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    phone: Optional[str]
    email: Optional[str]
    gender: str
    birth_date: Optional[str] = None
    occupation_id: Optional[uuid.UUID]
    occupation_name_th: Optional[str]
    education_id: Optional[uuid.UUID]
    education_name_th: Optional[str]
    blood_type: Optional[str]
    address_number: str
    alley: Optional[str]
    street: Optional[str]
    village_no: Optional[str]
    village_name: Optional[str]
    province_id: str
    province_name_th: Optional[str]
    district_id: str
    district_name_th: Optional[str]
    subdistrict_id: str
    subdistrict_name_th: Optional[str]
    postal_code: Optional[str]

class OsmProfileResponse(BaseModel):
    id: uuid.UUID
    citizen_id: str
    prefix_id: uuid.UUID
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    phone: Optional[str]
    email: Optional[str]
    profile_image: Optional[str]
    gender: str
    osm_year: Optional[int] = None
    birth_date: Optional[str] = None
    marital_status: str
    number_of_children: int
    occupation_id: uuid.UUID
    occupation_name_th: Optional[str]
    education_id: uuid.UUID
    education_name_th: Optional[str]
    blood_type: str
    health_service_id: Optional[str] = None
    health_service_name_th: Optional[str]
    bank_id: Optional[uuid.UUID]
    bank_name_th: Optional[str]
    bank_account_number: Optional[str]
    volunteer_status: str
    is_smartphone_owner: bool
    address_number: str
    alley: Optional[str]
    street: Optional[str]
    village_no: Optional[str]
    village_name: Optional[str]
    province_id: str
    province_name_th: Optional[str]
    district_id: str
    district_name_th: Optional[str]
    subdistrict_id: str
    subdistrict_name_th: Optional[str]
    postal_code: Optional[str]
    is_active: bool
    approval_status: str
    created_at: str
    updated_at: str
    spouse: Optional[SpouseResponse] = None
    children: Optional[List[ChildResponse]] = None
    official_positions: List[OfficialPositionResponse] = Field(default_factory=list)
    special_skills: List[SpecialSkillResponse] = Field(default_factory=list)
    club_positions: List[ClubPositionResponse] = Field(default_factory=list)
    trainings: List[TrainingRecordResponse] = Field(default_factory=list)


class OsmCreateResponse(BaseModel):
    status: str
    message: str
    data: Optional[OsmProfileResponse] = None

class OsmProfileListResponse(BaseModel):
    """Schema สำหรับ find_all_osm ที่มีเฉพาะ fields ที่จำเป็น"""
    id: uuid.UUID
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    province_name_th: Optional[str]
    district_name_th: Optional[str]
    subdistrict_name_th: Optional[str]

class OsmPublicSummaryResponse(BaseModel):
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    province_name_th: Optional[str]
    district_name_th: Optional[str]
    subdistrict_name_th: Optional[str]

class OsmProfileSummaryResponse(BaseModel):
    status: str
    message: str
    data: Optional[OsmPublicSummaryResponse] = None

class OsmProfileDetailResponse(BaseModel):
    """Schema สำหรับ find_osm_by_id ที่มี spouse และ children"""
    id: uuid.UUID
    citizen_id: str
    prefix_id: uuid.UUID
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    phone: Optional[str]
    email: Optional[str]
    profile_image: Optional[str]
    gender: str
    osm_year: Optional[int] = None
    birth_date: Optional[str] = None
    marital_status: str
    number_of_children: int
    occupation_id: uuid.UUID
    occupation_name_th: Optional[str]
    education_id: uuid.UUID
    education_name_th: Optional[str]
    blood_type: str
    health_service_id: Optional[str] = None
    health_service_name_th: Optional[str]
    bank_id: Optional[uuid.UUID]
    bank_name_th: Optional[str]
    bank_account_number: Optional[str]
    volunteer_status: str
    is_smartphone_owner: bool
    address_number: str
    alley: Optional[str]
    street: Optional[str]
    village_no: Optional[str]
    village_name: Optional[str]
    province_id: str
    province_name_th: Optional[str]
    district_id: str
    district_name_th: Optional[str]
    subdistrict_id: str
    subdistrict_name_th: Optional[str]
    postal_code: Optional[str]
    is_active: bool
    approval_status: str
    created_at: str
    updated_at: str
    spouse: Optional[SpouseResponse] = None
    children: Optional[List[ChildResponse]] = []
    official_positions: List[OfficialPositionResponse] = Field(default_factory=list)
    special_skills: List[SpecialSkillResponse] = Field(default_factory=list)
    club_positions: List[ClubPositionResponse] = Field(default_factory=list)
    trainings: List[TrainingRecordResponse] = Field(default_factory=list)

class OsmGenderSummaryResponse(BaseModel):
    province_code: str
    province_name_th: Optional[str]
    district_code: str
    district_name_th: Optional[str]
    subdistrict_code: str
    subdistrict_name_th: Optional[str]
    total_count: int
    male_count: int
    female_count: int


class OsmGenderSummaryPaginatedResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[OsmGenderSummaryResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    pageSize: int = 10


class ReportStatusEnum(str, Enum):
    OSM = "osm"  # อสม.
    SPOUSE = "spouse"  # คู่สมรส
    CHILD = "child"  # บุตร


class OsmFamilySummaryResponse(BaseModel):
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    gender: str
    address: str
    village_no: Optional[str]
    subdistrict_name: str
    status: ReportStatusEnum = Field(default=ReportStatusEnum.OSM)


class OsmFamilySummaryPaginatedResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[OsmFamilySummaryResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    pageSize: int = 10


class OsmPresidentResponse(BaseModel):
    area_name_th: Optional[str]
    first_name: str
    last_name: str
    province_name_th: Optional[str]
    district_name_th: Optional[str]
    subdistrict_name_th: Optional[str]
    registration_year: Optional[int]
    position_name_th: str
    position_level: AdministrativeLevelEnum


class OsmPresidentPaginatedResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    items: List[OsmPresidentResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    pageSize: int = 10


class OfficerPermissionResponse(BaseModel):
    can_edit: bool = False
    can_toggle_active: bool = False
    can_reset_password: bool = False
    can_delete: bool = False
    can_approve: bool = False
    can_manage: bool = False
    can_transfer: bool = False
    is_self: bool = False
    is_same_level: bool = False


class OfficerProfileListResponse(BaseModel):
    id: uuid.UUID
    citizen_id: str
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    profile_image: Optional[str]
    position_name_th: Optional[str]
    health_service_id: Optional[str]
    health_service_name_th: Optional[str]
    province_name_th: Optional[str]
    district_name_th: Optional[str]
    subdistrict_name_th: Optional[str]
    area_type: Optional[AdministrativeLevelEnum]
    area_code: Optional[str]
    approval_status: str
    is_active: bool
    permissions: Optional[OfficerPermissionResponse] = None


class OfficerProfileResponse(BaseModel):
    id: uuid.UUID
    citizen_id: str
    prefix_id: uuid.UUID
    prefix_name_th: Optional[str]
    first_name: str
    last_name: str
    gender: Optional[str]
    birth_date: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    profile_image: Optional[str]
    position_id: uuid.UUID
    position_name_th: Optional[str]
    address_number: str
    alley: Optional[str]
    street: Optional[str]
    village_no: Optional[str]
    postal_code: Optional[str]
    province_id: Optional[str]
    province_name_th: Optional[str]
    district_id: Optional[str]
    district_name_th: Optional[str]
    subdistrict_id: Optional[str]
    subdistrict_name_th: Optional[str]
    municipality_id: Optional[uuid.UUID]
    municipality_name_th: Optional[str]
    health_area_id: Optional[str]
    health_area_name_th: Optional[str]
    health_service_id: Optional[str]
    health_service_name_th: Optional[str]
    area_type: Optional[AdministrativeLevelEnum]
    area_code: Optional[str]
    is_active: bool
    approval_status: str
    approval_by: Optional[uuid.UUID]
    approval_date: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]
    permissions: Optional[OfficerPermissionResponse] = None


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class OfficerListPaginatedResponse(BaseModel):
    items: List[OfficerProfileListResponse]
    pagination: PaginationMeta

def get_related_name(obj, field_name, name_field="name_th"):
    """Helper function to safely get related object name"""
    try:
        if hasattr(obj, field_name) and getattr(obj, field_name):
            related_obj = getattr(obj, field_name)
            if hasattr(related_obj, name_field):
                return getattr(related_obj, name_field)
    except Exception:
        pass
    return None

def spouse_to_response(spouse):
    """แปลงข้อมูลคู่สมรสเป็น response format"""
    if not spouse:
        return None
    
    return SpouseResponse(
        id=spouse.id,
        citizen_id=spouse.citizen_id,
        prefix_id=spouse.prefix_id,
        prefix_name_th=get_related_name(spouse, 'prefix', 'prefix_name_th'),
        first_name=spouse.first_name,
        last_name=spouse.last_name,
        phone=spouse.phone,
        email=spouse.email,
        gender=spouse.gender,
        birth_date=str(spouse.birth_date) if spouse.birth_date else None,
        occupation_id=spouse.occupation_id,
        occupation_name_th=get_related_name(spouse, 'occupation', 'occupation_name_th'),
        education_id=spouse.education_id,
        education_name_th=get_related_name(spouse, 'education', 'education_name_th'),
        blood_type=spouse.blood_type,
        address_number=spouse.address_number,
        alley=spouse.alley,
        street=spouse.street,
        village_no=spouse.village_no,
        village_name=spouse.village_name,
        province_id=spouse.province_id,
        province_name_th=get_related_name(spouse, 'province', 'province_name_th'),
        district_id=spouse.district_id,
        district_name_th=get_related_name(spouse, 'district', 'district_name_th'),
        subdistrict_id=spouse.subdistrict_id,
        subdistrict_name_th=get_related_name(spouse, 'subdistrict', 'subdistrict_name_th'),
        postal_code=spouse.postal_code
    )

def child_to_response(child):
    """แปลงข้อมูลบุตรเป็น response format"""
    if not child:
        return None
    
    return ChildResponse(
        id=child.id,
        order_of_children=child.order_of_children,
        citizen_id=child.citizen_id,
        prefix_id=child.prefix_id,
        prefix_name_th=get_related_name(child, 'prefix', 'prefix_name_th'),
        first_name=child.first_name,
        last_name=child.last_name,
        phone=child.phone,
        email=child.email,
        gender=child.gender,
        birth_date=str(child.birth_date) if child.birth_date else None,
        occupation_id=child.occupation_id,
        occupation_name_th=get_related_name(child, 'occupation', 'occupation_name_th'),
        education_id=child.education_id,
        education_name_th=get_related_name(child, 'education', 'education_name_th'),
        blood_type=child.blood_type,
        address_number=child.address_number,
        alley=child.alley,
        street=child.street,
        village_no=child.village_no,
        village_name=child.village_name,
        province_id=child.province_id,
        province_name_th=get_related_name(child, 'province', 'province_name_th'),
        district_id=child.district_id,
        district_name_th=get_related_name(child, 'district', 'district_name_th'),
        subdistrict_id=child.subdistrict_id,
        subdistrict_name_th=get_related_name(child, 'subdistrict', 'subdistrict_name_th'),
        postal_code=child.postal_code
    )


def official_position_to_response(link):
    if not link:
        return None

    position = getattr(link, "official_position", None)
    return OfficialPositionResponse(
        assignment_id=link.id,
        position_id=link.official_position_id,
        position_name_th=getattr(position, "position_name_th", None) if position else None,
        position_level=getattr(position, "position_level", None) if position else None,
        legacy_code=getattr(position, "legacy_code", None) if position else None,
        custom_title=getattr(link, "custom_title", None),
    )


def special_skill_to_response(link):
    if not link:
        return None

    skill = getattr(link, "special_skill", None)
    return SpecialSkillResponse(
        assignment_id=link.id,
        skill_id=link.special_skill_id,
        skill_name_th=getattr(skill, "skill_name_th", None) if skill else None,
        legacy_code=getattr(skill, "legacy_code", None) if skill else None,
        custom_skill=getattr(link, "custom_skill", None),
    )


def club_position_to_response(link):
    if not link:
        return None

    club_position = getattr(link, "club_position", None)
    return ClubPositionResponse(
        assignment_id=link.id,
        club_position_id=link.club_position_id,
        club_position_name_th=getattr(club_position, "position_name_th", None) if club_position else None,
        appointed_level=getattr(link, "appointed_level", None),
    )


def training_record_to_response(link):
    if not link:
        return None

    course = getattr(link, "training_course", None)
    return TrainingRecordResponse(
        record_id=link.id,
        course_id=link.training_course_id,
        course_name_th=getattr(course, "course_name_th", None) if course else None,
        legacy_code=getattr(course, "legacy_code", None) if course else None,
        trained_year=getattr(link, "trained_year", None),
        topic=getattr(link, "topic", None),
    )

def osm_gender_summary_to_response(summary):
    return OsmGenderSummaryResponse(
        province_code=summary.province_id,
        province_name_th=summary.province_name_th,
        district_code=summary.district_id,
        district_name_th=summary.district_name_th,
        subdistrict_code=summary.subdistrict_id,
        subdistrict_name_th=summary.subdistrict_name_th,
        total_count=summary.total_count,
        male_count=summary.male_count,
        female_count=summary.female_count,
    )



def osm_family_summary_to_response(summary):
    return OsmFamilySummaryResponse(
        prefix_name_th=get_related_name(summary, 'prefix', 'prefix_name_th'),
        first_name=summary.first_name,
        last_name=summary.last_name,
        gender=summary.gender,
        address=summary.address,
        village_no=summary.village_no,
        subdistrict_name=summary.subdistrict_name_th,
        status=ReportStatusEnum(summary.status),
    )

def osm_president_summary_to_response(summary):
    return OsmPresidentResponse(
        area_name_th=summary.area_name_th,
        first_name=summary.first_name,
        last_name=summary.last_name,
        province_name_th=summary.province_name_th,
        district_name_th=summary.district_name_th,
        subdistrict_name_th=summary.subdistrict_name_th,
        registration_year=summary.registration_year,
        position_name_th=summary.position_name_th,
        position_level=summary.position_level
    )


def officer_to_list_response(officer, *, permissions: Optional[Dict[str, Any]] = None):
    permission_payload = None
    if permissions is not None:
        permission_payload = OfficerPermissionResponse(**permissions)

    return OfficerProfileListResponse(
        id=officer.id,
        citizen_id=officer.citizen_id,
        prefix_name_th=get_related_name(officer, "prefix", "prefix_name_th"),
        first_name=officer.first_name,
        last_name=officer.last_name,
        profile_image=getattr(officer, "profile_image", None),
        position_name_th=get_related_name(officer, "position", "position_name_th"),
        health_service_id=getattr(officer, "health_service_id", None),
        health_service_name_th=get_related_name(officer, "health_service", "health_service_name_th"),
        province_name_th=get_related_name(officer, "province", "province_name_th"),
        district_name_th=get_related_name(officer, "district", "district_name_th"),
        subdistrict_name_th=get_related_name(officer, "subdistrict", "subdistrict_name_th"),
        area_type=officer.area_type,
        area_code=officer.area_code,
        approval_status=officer.approval_status.value if getattr(officer.approval_status, "value", None) else officer.approval_status,
        is_active=officer.is_active,
        permissions=permission_payload,
    )


def officer_to_response(officer, *, permissions: Optional[Dict[str, Any]] = None):
    permission_payload = None
    if permissions is not None:
        permission_payload = OfficerPermissionResponse(**permissions)

    return OfficerProfileResponse(
        id=officer.id,
        citizen_id=officer.citizen_id,
        prefix_id=officer.prefix_id,
        prefix_name_th=get_related_name(officer, "prefix", "prefix_name_th"),
        first_name=officer.first_name,
        last_name=officer.last_name,
        gender=officer.gender.value if getattr(officer.gender, "value", None) else officer.gender,
        birth_date=str(officer.birth_date) if officer.birth_date else None,
        email=officer.email,
        phone=officer.phone,
        profile_image=getattr(officer, "profile_image", None),
        position_id=officer.position_id,
        position_name_th=get_related_name(officer, "position", "position_name_th"),
        address_number=officer.address_number,
        alley=officer.alley,
        street=officer.street,
        village_no=officer.village_no,
        postal_code=officer.postal_code,
        province_id=officer.province_id,
        province_name_th=get_related_name(officer, "province", "province_name_th"),
        district_id=officer.district_id,
        district_name_th=get_related_name(officer, "district", "district_name_th"),
        subdistrict_id=officer.subdistrict_id,
        subdistrict_name_th=get_related_name(officer, "subdistrict", "subdistrict_name_th"),
        municipality_id=officer.municipality_id,
        municipality_name_th=get_related_name(officer, "municipality", "municipality_name_th"),
        health_area_id=officer.health_area_id,
        health_area_name_th=get_related_name(officer, "health_area", "health_area_name_th"),
        health_service_id=officer.health_service_id,
        health_service_name_th=get_related_name(officer, "health_service", "health_service_name_th"),
        area_type=officer.area_type,
        area_code=officer.area_code,
        is_active=officer.is_active,
        approval_status=officer.approval_status.value if getattr(officer.approval_status, "value", None) else officer.approval_status,
        approval_by=officer.approval_by,
        approval_date=str(officer.approval_date) if officer.approval_date else None,
        created_at=str(officer.created_at) if officer.created_at else None,
        updated_at=str(officer.updated_at) if officer.updated_at else None,
        deleted_at=str(officer.deleted_at) if officer.deleted_at else None,
        permissions=permission_payload,
    )

def osm_to_response(
    osm,
    *,
    spouses=None,
    children=None,
    official_positions=None,
    special_skills=None,
    club_positions=None,
    trainings=None,
):
    """แปลงข้อมูล OSM เป็น response format"""

    def _normalize_related(raw):
        if raw is None:
            return []

        # Common tortoise types that can appear when reverse relations were not fetched.
        type_name = type(raw).__name__
        if type_name in {"ReverseRelation", "QuerySet"}:
            fetched = getattr(raw, "_fetched", False)
            if fetched:
                try:
                    return [item for item in list(raw) if item]
                except Exception:
                    return []
            return []

        if isinstance(raw, list):
            return [item for item in raw if item]

        # Single model instance
        return [raw] if raw else []

    spouse_source = spouses if spouses is not None else getattr(osm, 'osm_spouses_profile', None)
    child_source = children if children is not None else getattr(osm, 'osm_children_profile', None)
    position_source = official_positions if official_positions is not None else getattr(osm, 'official_position_links', None)
    skill_source = special_skills if special_skills is not None else getattr(osm, 'special_skill_links', None)
    club_source = club_positions if club_positions is not None else getattr(osm, 'club_position_links', None)
    training_source = trainings if trainings is not None else getattr(osm, 'training_records', None)

    spouse_items = _normalize_related(spouse_source)
    child_items = _normalize_related(child_source)
    position_items = _normalize_related(position_source)
    skill_items = _normalize_related(skill_source)
    club_items = _normalize_related(club_source)
    training_items = _normalize_related(training_source)

    spouse_data = spouse_to_response(spouse_items[0]) if spouse_items else None
    children_data = [child_to_response(child) for child in child_items] if child_items else None
    official_positions_data = [official_position_to_response(link) for link in position_items]
    special_skills_data = [special_skill_to_response(link) for link in skill_items]
    club_positions_data = [club_position_to_response(link) for link in club_items]
    training_records_data = [training_record_to_response(link) for link in training_items]

    return OsmProfileResponse(
        id=osm.id,
        citizen_id=osm.citizen_id,
        prefix_id=osm.prefix_id,
        prefix_name_th=get_related_name(osm, 'prefix', 'prefix_name_th'),
        first_name=osm.first_name,
        last_name=osm.last_name,
        phone=osm.phone,
        email=osm.email,
        profile_image=getattr(osm, "profile_image", None),
        gender=osm.gender,
        osm_year=osm.osm_year,
        birth_date=str(osm.birth_date) if osm.birth_date else None,
        marital_status=osm.marital_status,
        number_of_children=osm.number_of_children,
        occupation_id=osm.occupation_id,
        occupation_name_th=get_related_name(osm, 'occupation', 'occupation_name_th'),
        education_id=osm.education_id,
        education_name_th=get_related_name(osm, 'education', 'education_name_th'),
        blood_type=osm.blood_type,
        health_service_id=osm.health_service_id,
        health_service_name_th=get_related_name(osm, 'health_service', 'health_service_name_th'),
        bank_id=osm.bank_id,
        bank_name_th=get_related_name(osm, 'bank', 'bank_name_th'),
        bank_account_number=osm.bank_account_number,
        volunteer_status=osm.volunteer_status,
        is_smartphone_owner=osm.is_smartphone_owner,
        address_number=osm.address_number,
        alley=osm.alley,
        street=osm.street,
        village_no=osm.village_no,
        village_name=osm.village_name,
        province_id=osm.province_id,
        province_name_th=get_related_name(osm, 'province', 'province_name_th'),
        district_id=osm.district_id,
        district_name_th=get_related_name(osm, 'district', 'district_name_th'),
        subdistrict_id=osm.subdistrict_id,
        subdistrict_name_th=get_related_name(osm, 'subdistrict', 'subdistrict_name_th'),
        postal_code=osm.postal_code,
        is_active=osm.is_active,
        approval_status=osm.approval_status,
        created_at=str(osm.created_at),
        updated_at=str(osm.updated_at),
        spouse=spouse_data,
        children=children_data,
        official_positions=[item for item in official_positions_data if item],
        special_skills=[item for item in special_skills_data if item],
        club_positions=[item for item in club_positions_data if item],
        trainings=[item for item in training_records_data if item],
    )

def osm_to_list_response(osm):
    """แปลงข้อมูล OSM เป็น response format สำหรับ list (เฉพาะ fields ที่จำเป็น)"""
    return OsmProfileListResponse(
        id=osm.id,
        prefix_name_th=get_related_name(osm, 'prefix', 'prefix_name_th'),
        first_name=osm.first_name,
        last_name=osm.last_name,
        province_name_th=get_related_name(osm, 'province', 'province_name_th'),
        district_name_th=get_related_name(osm, 'district', 'district_name_th'),
        subdistrict_name_th=get_related_name(osm, 'subdistrict', 'subdistrict_name_th')
    )

def osm_to_public_summary_response(osm):
    """แปลงข้อมูล OSM เป็น response format แบบย่อ (ไม่รวม id)"""
    return OsmPublicSummaryResponse(
        prefix_name_th=get_related_name(osm, 'prefix', 'prefix_name_th'),
        first_name=osm.first_name,
        last_name=osm.last_name,
        province_name_th=get_related_name(osm, 'province', 'province_name_th'),
        district_name_th=get_related_name(osm, 'district', 'district_name_th'),
        subdistrict_name_th=get_related_name(osm, 'subdistrict', 'subdistrict_name_th')
    )

def osm_to_detail_response(osm):
    """แปลงข้อมูล OSM เป็น response format สำหรับ detail (มี spouse และ children)"""
    # แปลงข้อมูลคู่สมรส
    spouse_data = None
    if hasattr(osm, 'osm_spouses_profile') and osm.osm_spouses_profile:
        # ตรวจสอบว่าเป็น list หรือ single object
        if isinstance(osm.osm_spouses_profile, list) and len(osm.osm_spouses_profile) > 0:
            spouse_data = spouse_to_response(osm.osm_spouses_profile[0])
        elif hasattr(osm.osm_spouses_profile, 'id'):
            spouse_data = spouse_to_response(osm.osm_spouses_profile)
    
    # แปลงข้อมูลบุตร
    children_data = []
    if hasattr(osm, 'osm_children_profile') and osm.osm_children_profile:
        if isinstance(osm.osm_children_profile, list):
            children_data = [child_to_response(child) for child in osm.osm_children_profile]
        else:
            children_data = [child_to_response(osm.osm_children_profile)]

    official_positions_data: List[OfficialPositionResponse] = []
    if hasattr(osm, 'official_position_links') and osm.official_position_links:
        if isinstance(osm.official_position_links, list):
            official_positions_data = [official_position_to_response(link) for link in osm.official_position_links]
        else:
            official_positions_data = [official_position_to_response(osm.official_position_links)]

    special_skills_data: List[SpecialSkillResponse] = []
    if hasattr(osm, 'special_skill_links') and osm.special_skill_links:
        if isinstance(osm.special_skill_links, list):
            special_skills_data = [special_skill_to_response(link) for link in osm.special_skill_links]
        else:
            special_skills_data = [special_skill_to_response(osm.special_skill_links)]

    club_positions_data: List[ClubPositionResponse] = []
    if hasattr(osm, 'club_position_links') and osm.club_position_links:
        if isinstance(osm.club_position_links, list):
            club_positions_data = [club_position_to_response(link) for link in osm.club_position_links]
        else:
            club_positions_data = [club_position_to_response(osm.club_position_links)]

    training_records_data: List[TrainingRecordResponse] = []
    if hasattr(osm, 'training_records') and osm.training_records:
        if isinstance(osm.training_records, list):
            training_records_data = [training_record_to_response(link) for link in osm.training_records]
        else:
            training_records_data = [training_record_to_response(osm.training_records)]
    
    return OsmProfileDetailResponse(
        id=osm.id,
        citizen_id=osm.citizen_id,
        prefix_id=osm.prefix_id,
        prefix_name_th=get_related_name(osm, 'prefix', 'prefix_name_th'),
        first_name=osm.first_name,
        last_name=osm.last_name,
        phone=osm.phone,
        email=osm.email,
        profile_image=getattr(osm, "profile_image", None),
        gender=osm.gender,
        osm_year=osm.osm_year,
        birth_date=str(osm.birth_date) if osm.birth_date else None,
        marital_status=osm.marital_status,
        number_of_children=osm.number_of_children,
        occupation_id=osm.occupation_id,
        occupation_name_th=get_related_name(osm, 'occupation', 'occupation_name_th'),
        education_id=osm.education_id,
        education_name_th=get_related_name(osm, 'education', 'education_name_th'),
        blood_type=osm.blood_type,
        health_service_id=osm.health_service_id,
        health_service_name_th=get_related_name(osm, 'health_service', 'health_service_name_th'),
        bank_id=osm.bank_id,
        bank_name_th=get_related_name(osm, 'bank', 'bank_name_th'),
        bank_account_number=osm.bank_account_number,
        volunteer_status=osm.volunteer_status,
        is_smartphone_owner=osm.is_smartphone_owner,
        address_number=osm.address_number,
        alley=osm.alley,
        street=osm.street,
        village_no=osm.village_no,
        village_name=osm.village_name,
        province_id=osm.province_id,
        province_name_th=get_related_name(osm, 'province', 'province_name_th'),
        district_id=osm.district_id,
        district_name_th=get_related_name(osm, 'district', 'district_name_th'),
        subdistrict_id=osm.subdistrict_id,
        subdistrict_name_th=get_related_name(osm, 'subdistrict', 'subdistrict_name_th'),
        postal_code=osm.postal_code,
        is_active=osm.is_active,
        approval_status=osm.approval_status,
        created_at=str(osm.created_at),
        updated_at=str(osm.updated_at),
        spouse=spouse_data,
        children=children_data,
        official_positions=[item for item in official_positions_data if item],
        special_skills=[item for item in special_skills_data if item],
        club_positions=[item for item in club_positions_data if item],
        trainings=[item for item in training_records_data if item],
    )

# Position Confirmation Response Functions
def osm_position_confirmation_to_response(confirmation):
    """
    แปลงข้อมูลการยืนยันตำแหน่งเป็น response format
    """
    position_names = []
    if hasattr(confirmation, 'osm_positions') and confirmation.osm_positions:
        for position in confirmation.osm_positions:
            position_names.append(position.position_name_th)
    
    return {
        "id": str(confirmation.id),
        "osm_profile_id": str(confirmation.osm_profile_id),
        "osm_profile_name": f"{confirmation.osm_profile.first_name} {confirmation.osm_profile.last_name}" if confirmation.osm_profile else "",
        "osm_position_names": position_names,
        "allowance_confirmation_status": confirmation.allowance_confirmation_status,
        "created_at": str(confirmation.created_at),
        "updated_at": str(confirmation.updated_at)
    }

def osm_position_to_response(position):
    """
    แปลงข้อมูลตำแหน่ง OSM เป็น response format
    """
    return {
        "id": str(position.id),
        "position_name_th": position.position_name_th,
        "position_name_en": position.position_name_en,
        "position_level": position.position_level
    }