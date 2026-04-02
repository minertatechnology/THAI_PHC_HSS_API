from fastapi import HTTPException
from app.api.v1.schemas.query_schema import OsmQueryParams
from app.models.osm_model import (
    OSMProfile,
    OsmCodeCounter,
    OsmSpouse,
    OsmChild,
    OsmPositionConfirmation,
    OsmPosition,
    OsmPositionConfirmationPosition,
    OsmProfileOfficialPosition,
    OsmProfileSpecialSkill,
    OsmProfileClubPosition,
    OsmProfileTraining,
)
from app.utils.constant import ALLOWED_SORT_FIELDS
from app.api.v1.schemas.osm_schema import OsmCreateSchema
from app.models.enum_models import ApprovalStatus
from tortoise.transactions import atomic, in_transaction
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise import connections
from tortoise.expressions import Q
from typing import Dict, Any, List, Optional
import datetime
import bcrypt as _bcrypt
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

class OSMProfileRepository:

    @staticmethod
    async def _osm_code_counter_table_exists() -> bool:
        """Return True when the osm_code_counters table exists in the current DB.

        Important: In Postgres, referencing a missing table inside a transaction aborts
        the whole transaction, so we must *probe* existence using functions that don't
        error (like to_regclass) before using the counter-table strategy.
        """
        connection = connections.get("default")
        try:
            rows = await connection.execute_query_dict(
                "SELECT to_regclass($1) AS regclass",
                ["osm_code_counters"],
            )
            regclass = (rows[0] or {}).get("regclass") if rows else None
            return regclass is not None
        except Exception:
            # Likely non-Postgres (or limited SQL dialect). Treat as not available.
            return False

    @staticmethod
    def _build_osm_code_prefix(payload: Dict[str, Any]) -> str:
        """Build 9-digit prefix: province(2)+district(2)+subdistrict(2)+village(3).

        Notes:
        - district_id/subdistrict_id may be full codes (e.g., 3201 / 320101), so we take last 2 digits.
        - village_no is padded to 3 digits.
        - if village_no is missing/blank, fallback to "000" to keep code generation working.
        """

        def _two_digits(value: Any) -> str:
            raw = "" if value is None else str(value).strip()
            if raw == "" or not raw.isdigit():
                raise HTTPException(status_code=400, detail="invalid_location_for_osm_code")
            return raw[-2:].zfill(2)

        province_part = _two_digits(payload.get("province_id"))
        district_part = _two_digits(payload.get("district_id"))
        subdistrict_part = _two_digits(payload.get("subdistrict_id"))

        village_raw = "" if payload.get("village_no") is None else str(payload.get("village_no")).strip()
        if village_raw == "":
            village_part = "000"
        elif not village_raw.isdigit():
            raise HTTPException(status_code=400, detail="missing_or_invalid_village_no_for_osm_code")
        else:
            village_part = str(int(village_raw)).zfill(3)

        return f"{province_part}{district_part}{subdistrict_part}{village_part}"

    @staticmethod
    async def _allocate_next_osm_code_run(prefix: str) -> int:
        """Allocate the next 6-digit running number for a given prefix.

        Primary strategy:
        - Use the osm_code_counters table with row-level locking (SELECT ... FOR UPDATE).

        Fallback strategy (when the counter table isn't migrated yet):
        - Use a Postgres advisory transaction lock + MAX(osm_code) per prefix.

        Both are safe under multi-replica (K8s) concurrency as long as the DB is shared.
        """
        # 1) Try counter-table strategy (only if table exists).
        if await OSMProfileRepository._osm_code_counter_table_exists():
            for attempt in range(3):
                try:
                    counter = await OsmCodeCounter.select_for_update().get_or_none(prefix=prefix)
                    if counter is None:
                        try:
                            await OsmCodeCounter.create(prefix=prefix, last_number=0)
                        except IntegrityError:
                            # Another transaction created it first; retry selecting with lock.
                            counter = None

                    counter = await OsmCodeCounter.select_for_update().get(prefix=prefix)
                    counter.last_number = int(counter.last_number or 0) + 1
                    await counter.save(update_fields=["last_number", "updated_at"])
                    return int(counter.last_number)
                except IntegrityError:
                    if attempt >= 2:
                        raise

        # 2) Fallback: advisory transaction lock + max-per-prefix.
        connection = connections.get("default")
        try:
            await connection.execute_query_dict(
                "SELECT pg_advisory_xact_lock(hashtext($1)) AS locked",
                [prefix],
            )
        except Exception:
            # Non-Postgres DBs won't have pg_advisory_xact_lock; proceed without it.
            pass

        rows = await connection.execute_query_dict(
            """
            SELECT
                COALESCE(MAX(CAST(RIGHT(osm_code, 6) AS INT)), 0) + 1 AS next_no
            FROM osm_profiles
            WHERE osm_code IS NOT NULL
              AND osm_code LIKE $1 || '%'
              AND LENGTH(osm_code) >= 15
            """,
            [prefix],
        )
        next_no = int((rows[0] or {}).get("next_no") or 1)
        if next_no < 1:
            next_no = 1
        if next_no > 999_999:
            raise HTTPException(status_code=400, detail="osm_code_run_number_exhausted")
        return next_no

    @staticmethod
    def _get_forward_related_fields():
        """รายการ forward related fields ที่ต้อง prefetch"""
        return [
            "prefix",
            "occupation", 
            "education",
            "bank",
            "province",
            "district",
            "subdistrict", 
            "health_service"
        ]
    
    @staticmethod
    def _get_list_related_fields():
        """รายการ related fields สำหรับ find_all_osm (เฉพาะที่จำเป็น)"""
        return [
            "prefix",
            "province",
            "district",
            "subdistrict",
            "health_service"
        ]

    @staticmethod
    def _build_filter_kwargs(filter: OsmQueryParams) -> dict[str, Any]:
        filters: dict[str, Any] = {}

        if filter.citizen_id:
            filters["citizen_id"] = filter.citizen_id
        if filter.first_name:
            filters["first_name__icontains"] = filter.first_name
        if filter.last_name:
            filters["last_name__icontains"] = filter.last_name
        if filter.status:
            filters["volunteer_status"] = filter.status
        if filter.health_service_code:
            filters["health_service_id"] = filter.health_service_code
        if filter.province_code:
            filters["province_id"] = filter.province_code
        if filter.district_code:
            filters["district_id"] = filter.district_code
        if filter.subdistrict_code:
            filters["subdistrict_id"] = filter.subdistrict_code
        return filters
    
    @staticmethod
    def _get_reverse_related_fields():
        """รายการ reverse related fields ที่ต้อง prefetch"""
        return [
            "osm_spouses_profile",
            "osm_children_profile",
            "official_position_links",
            "official_position_links__official_position",
            "special_skill_links",
            "special_skill_links__special_skill",
            "club_position_links",
            "club_position_links__club_position",
            "training_records",
            "training_records__training_course",
        ]
    


    @atomic()
    async def create_osm(
        osm_data: OsmCreateSchema,
        user_id: Optional[str],
        *,
        auto_approve: bool = False,
        approval_by: Optional[str] = None,
        approval_date: Optional[datetime.date] = None,
    ):
        """
        สร้าง OSM Profile พร้อมข้อมูลคู่สมรสและบุตร
        ใช้ transaction เพื่อให้ rollback เมื่อเกิดข้อผิดพลาด
        """
        try:
            # แยกข้อมูล OSM หลัก
            osm_dict = osm_data.model_dump(exclude={'spouse', 'children'}, exclude_none=True)
            print("OSM Data:", osm_dict)

            payload = dict(osm_dict)

            # รองรับ client ที่ส่ง alias "showbody" และ map ให้ลง field จริง "osm_showbbody"
            showbody = payload.pop("showbody", None)
            if payload.get("osm_showbbody") is None and showbody is not None:
                payload["osm_showbbody"] = showbody

            # normalize new_registration_allowance_status: treat empty string as missing
            raw_allowance_value = payload.get("new_registration_allowance_status")
            if raw_allowance_value is None:
                # Column is non-nullable; omit to use model default.
                payload.pop("new_registration_allowance_status", None)
            else:
                raw_allowance = str(raw_allowance_value).strip()
                if raw_allowance == "":
                    payload.pop("new_registration_allowance_status", None)

            # normalize/validate osm_showbbody (accept eligible/ineligible/pending too)
            if payload.get("osm_showbbody") is not None:
                raw = str(payload.get("osm_showbbody")).strip()
                if raw == "":
                    payload.pop("osm_showbbody", None)
                else:
                    lowered = raw.lower()
                    mapped = {
                        "eligible": "1",
                        "ineligible": "5",
                        "pending": "6",
                    }.get(lowered, raw)
                    mapped_str = str(mapped).strip()
                    if mapped_str not in {"1", "2", "5", "6"}:
                        raise HTTPException(status_code=400, detail="invalid_osm_showbbody")
                    payload["osm_showbbody"] = mapped_str

            creator_reference = str(user_id) if user_id else "self-registration"
            payload["created_by"] = creator_reference

            if auto_approve:
                approver_reference = approval_by or user_id
                payload["approval_status"] = ApprovalStatus.APPROVED.value
                payload["approval_by"] = str(approver_reference) if approver_reference else None
                payload["approval_date"] = approval_date or datetime.date.today()
                payload["is_active"] = True
            else:
                payload["approval_status"] = ApprovalStatus.PENDING.value
                payload["approval_by"] = None
                payload["approval_date"] = None
                payload["is_active"] = False

            # Generate osm_code (15 digits) only when auto-approved.
            # For pending profiles (district/subdistrict officers or self-registration),
            # osm_code will be generated later when the profile is approved.
            if auto_approve:
                prefix = OSMProfileRepository._build_osm_code_prefix(payload)
                run_no = await OSMProfileRepository._allocate_next_osm_code_run(prefix)
                payload["osm_code"] = f"{prefix}{run_no:06d}"
                # Also store the 9-digit village_code derived from location.
                payload.setdefault("village_code", prefix)
                # สร้างรหัสผ่านเริ่มต้น (hash จาก citizen_id) เพื่อให้ login ได้ทันที
                citizen_id = payload.get("citizen_id")
                if citizen_id and not payload.get("password_hash"):
                    payload["password_hash"] = _bcrypt.hashpw(
                        citizen_id.encode(), _bcrypt.gensalt()
                    ).decode()
                    payload["is_first_login"] = True
            else:
                payload["osm_code"] = None
                # Still store village_code for village_name lookup if possible.
                try:
                    vc_prefix = OSMProfileRepository._build_osm_code_prefix(payload)
                    payload.setdefault("village_code", vc_prefix)
                except Exception:
                    pass  # village_no may be missing; village_code will be set on approval

            # สร้าง OSM Profile หลัก
            osm_profile = await OSMProfile.create(**payload)
            print("Created OSM Profile:", osm_profile.id)

            audit_user_id = str(user_id) if user_id else str(osm_profile.id)
            if not user_id and creator_reference != audit_user_id:
                await OSMProfile.filter(id=osm_profile.id).update(created_by=audit_user_id)
            
            # สร้างข้อมูลคู่สมรส (ถ้ามี)
            if osm_data.spouse:
                try:
                    spouse_dict = osm_data.spouse.model_dump()
                    spouse_dict['osm_profile_id'] = osm_profile.id
                    spouse_dict['created_by'] = audit_user_id
                    print("Creating spouse with data:", spouse_dict)
                    await OsmSpouse.create(**spouse_dict)
                    print("Spouse created successfully")
                except Exception as e:
                    print(f"Error creating spouse: {e}")
                    raise Exception(f"ไม่สามารถสร้างข้อมูลคู่สมรสได้: {str(e)}")
            
            # สร้างข้อมูลบุตร (ถ้ามี)
            if osm_data.children:
                for i, child_data in enumerate(osm_data.children):
                    try:
                        child_dict = child_data.model_dump()
                        child_dict['osm_profile_id'] = osm_profile.id
                        child_dict['created_by'] = audit_user_id
                        print(f"Creating child {i+1} with data:", child_dict)
                        await OsmChild.create(**child_dict)
                        print(f"Child {i+1} created successfully")
                    except Exception as e:
                        print(f"Error creating child {i+1}: {e}")
                        raise Exception(f"ไม่สามารถสร้างข้อมูลบุตรคนที่ {i+1} ได้: {str(e)}")

            # บันทึกตำแหน่งทางการ/ไม่ทางการ
            if osm_data.official_positions:
                for position_item in osm_data.official_positions:
                    try:
                        await OsmProfileOfficialPosition.create(
                            osm_profile_id=osm_profile.id,
                            official_position_id=position_item.position_id,
                            custom_title=position_item.custom_title,
                            created_by=audit_user_id,
                            updated_by=audit_user_id,
                        )
                    except Exception as e:
                        print(f"Error creating official position assignment: {e}")
                        raise Exception(f"ไม่สามารถบันทึกตำแหน่งที่เลือกได้: {str(e)}")

            # บันทึกความชำนาญพิเศษ
            if osm_data.special_skills:
                for skill_item in osm_data.special_skills:
                    try:
                        await OsmProfileSpecialSkill.create(
                            osm_profile_id=osm_profile.id,
                            special_skill_id=skill_item.skill_id,
                            custom_skill=skill_item.custom_skill,
                            created_by=audit_user_id,
                            updated_by=audit_user_id,
                        )
                    except Exception as e:
                        print(f"Error creating special skill assignment: {e}")
                        raise Exception(f"ไม่สามารถบันทึกความชำนาญพิเศษได้: {str(e)}")

            # บันทึกตำแหน่งชมรม อสม.
            if osm_data.club_positions:
                for club_item in osm_data.club_positions:
                    try:
                        await OsmProfileClubPosition.create(
                            osm_profile_id=osm_profile.id,
                            club_position_id=club_item.club_position_id,
                            appointed_level=club_item.appointed_level,
                            created_by=audit_user_id,
                            updated_by=audit_user_id,
                        )
                    except Exception as e:
                        print(f"Error creating club position assignment: {e}")
                        raise Exception(f"ไม่สามารถบันทึกตำแหน่งชมรม อสม. ได้: {str(e)}")

            # บันทึกข้อมูลการอบรมหลักสูตร
            if osm_data.trainings:
                for training_item in osm_data.trainings:
                    try:
                        await OsmProfileTraining.create(
                            osm_profile_id=osm_profile.id,
                            training_course_id=training_item.course_id,
                            trained_year=training_item.trained_year,
                            topic=training_item.topic,
                            created_by=audit_user_id,
                            updated_by=audit_user_id,
                        )
                    except Exception as e:
                        print(f"Error creating training record: {e}")
                        raise Exception(f"ไม่สามารถบันทึกข้อมูลการอบรมได้: {str(e)}")
            
            # Return success message with basic info
            return {
                "id": str(osm_profile.id),
                "citizen_id": osm_profile.citizen_id,
                "first_name": osm_profile.first_name,
                "last_name": osm_profile.last_name,
                "message": "สร้าง OSM Profile สำเร็จ"
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error in create_osm transaction: {str(e)}")
            # Transaction จะ rollback อัตโนมัติเมื่อเกิด exception
            raise HTTPException(
                status_code=500,
                detail=f"ไม่สามารถสร้าง OSM ได้: {str(e)}"
            )

    @staticmethod
    async def search_active_osm(term: str, limit: int = 10, *, active_only: bool = True, offset: int = 0):
        if not term:
            return [], 0
        try:
            base_qs = (
                OSMProfile
                .filter(deleted_at__isnull=True)
                .filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(citizen_id__icontains=term)
                )
            )
            if active_only:
                base_qs = base_qs.filter(is_active=True)
            total = await base_qs.count()
            query = (
                base_qs
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "phone",
                    "email",
                    "is_active",
                    "province_id",
                    "district_id",
                    "subdistrict_id",
                    "health_service_id",
                )
                .prefetch_related("province", "district", "subdistrict", "health_service")
                .order_by("first_name")
                .offset(offset)
                .limit(limit)
            )
            items = await query
            return items, total
        except Exception as e:
            logger.error(f"Error searching OSM profiles: {e}")
            raise e

    @staticmethod
    async def set_active_status(osm_id: str, is_active: bool, updated_by: Optional[str] = None) -> bool:
        if not osm_id:
            return False
        payload: Dict[str, Any] = {
            "is_active": is_active,
            "updated_at": datetime.datetime.utcnow(),
        }
        if updated_by:
            payload["updated_by"] = updated_by
        try:
            updated = await OSMProfile.filter(id=osm_id).update(**payload)
            return bool(updated)
        except Exception as exc:
            logger.error(f"Error updating active status for OSM profile {osm_id}: {exc}")
            raise

    @staticmethod
    async def find_basic_profile_by_id(osm_id: str):
        if not osm_id:
            return None
        try:
            return (
                await OSMProfile
                .filter(
                    Q(id=osm_id)
                    & Q(deleted_at__isnull=True)
                    & Q(is_active=True)
                    & (Q(osm_status__isnull=True) | Q(osm_status=""))
                )
                .only("id", "first_name", "last_name", "citizen_id", "is_active", "osm_status")
                .first()
            )
        except Exception as e:
            logger.error(f"Error retrieving OSM basic profile {osm_id}: {e}")
            raise e

    @staticmethod
    async def find_list_profile_by_id(osm_id: str):
        if not osm_id:
            return None
        try:
            return await (
                OSMProfile
                .filter(id=osm_id)
                .prefetch_related(*OSMProfileRepository._get_list_related_fields())
                .first()
            )
        except Exception as e:
            logger.error(f"Error retrieving OSM list profile {osm_id}: {e}")
            raise e

    @staticmethod
    async def get_profile_for_management(osm_id: str) -> Optional[OSMProfile]:
        if not osm_id:
            return None
        try:
            return await (
                OSMProfile
                .filter(id=osm_id, deleted_at__isnull=True)
                .select_related(
                    "province",
                    "district",
                    "district__province",
                    "subdistrict",
                    "subdistrict__district",
                    "subdistrict__district__province",
                )
                .first()
            )
        except Exception as exc:
            logger.error(f"Error loading OSM profile for management {osm_id}: {exc}")
            raise

    async def find_osm_by_id(osm_id: str):
        """
        ค้นหา OSM Profile ด้วย ID
        """
        try:
            # ใช้ prefetch_related เฉพาะ forward relations
            osm_profile = await OSMProfile.filter(id=osm_id).prefetch_related(
                *OSMProfileRepository._get_forward_related_fields()
            ).first()
            
            if not osm_profile:
                return None
            
            # ดึงข้อมูล spouse และ children แยกต่างหาก
            spouses = []
            children = []
            official_positions = []
            special_skills = []
            club_positions = []
            trainings = []
            
            try:
                from app.models.osm_model import OsmSpouse, OsmChild
                spouses = await OsmSpouse.filter(osm_profile_id=osm_id, deleted_at__isnull=True).prefetch_related(
                    "prefix", "occupation", "education", "province", "district", "subdistrict"
                )
            except Exception as e:
                print(f"Warning: Could not fetch spouses: {e}")
                
            try:
                from app.models.osm_model import OsmChild
                children = await OsmChild.filter(osm_profile_id=osm_id, deleted_at__isnull=True).prefetch_related(
                    "prefix", "occupation", "education", "province", "district", "subdistrict"
                ).order_by("order_of_children")
            except Exception as e:
                print(f"Warning: Could not fetch children: {e}")
            
            # ดึงข้อมูลส่วนขยายอื่น ๆ
            try:
                official_positions = await (
                    OsmProfileOfficialPosition
                    .filter(osm_profile_id=osm_id, deleted_at__isnull=True)
                    .prefetch_related("official_position")
                )
            except Exception as e:
                print(f"Warning: Could not fetch official positions: {e}")

            try:
                special_skills = await (
                    OsmProfileSpecialSkill
                    .filter(osm_profile_id=osm_id, deleted_at__isnull=True)
                    .prefetch_related("special_skill")
                )
            except Exception as e:
                print(f"Warning: Could not fetch special skills: {e}")

            try:
                club_positions = await (
                    OsmProfileClubPosition
                    .filter(osm_profile_id=osm_id, deleted_at__isnull=True)
                    .prefetch_related("club_position")
                )
            except Exception as e:
                print(f"Warning: Could not fetch club positions: {e}")

            try:
                trainings = await (
                    OsmProfileTraining
                    .filter(osm_profile_id=osm_id, deleted_at__isnull=True)
                    .prefetch_related("training_course")
                )
            except Exception as e:
                print(f"Warning: Could not fetch training records: {e}")

            # ส่งกลับเป็น dictionary ที่มี osm_profile และ related data
            return {
                "osm_profile": osm_profile,
                "spouses": spouses,
                "children": children,
                "official_positions": official_positions,
                "special_skills": special_skills,
                "club_positions": club_positions,
                "trainings": trainings,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการค้นหา OSM: {str(e)}"
            )
        
    async def is_citizen_id_exist_and_is_first_login(citizen_id: str):
        """
        ค้นหา OSM Profile ด้วยเลขบัตรประชาชน
        """

        # ตรวจสอบความยาว citizen_id
        if len(citizen_id) != 13:
            return False
        
        # ตรวจสอบว่าเป็นตัวเลขหรือไม่
        if not citizen_id.isdigit():
            return False
        
        result = await OSMProfile.filter(
            citizen_id=citizen_id,
            is_active=True,
        ).values("citizen_id", "is_first_login", "password_hash")
        
        if result:
            return result[0]
        else:
            return None 
    async def find_osm_by_citizen_id(citizen_id: str):
        """
        ค้นหา OSM Profile ด้วยเลขบัตรประชาชน
        """
        try:
            # ใช้ prefetch_related เฉพาะ forward relations
            osm_profile = await OSMProfile.filter(citizen_id=citizen_id).prefetch_related(
                *OSMProfileRepository._get_forward_related_fields()
            ).first()
            
            if not osm_profile:
                return None
            
            # ใช้ fetch_related สำหรับ reverse relations
            try:
                await osm_profile.fetch_related(*OSMProfileRepository._get_reverse_related_fields())
            except Exception as e:
                print(f"Warning: Could not fetch reverse relations: {e}")
                
            return osm_profile
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการค้นหา OSM: {str(e)}"
            )

    async def find_osm_basic_profile_by_citizen_id(citizen_id: str):
        """
        ดึง OSM Profile เฉพาะ basic fields สำหรับ login validation
        """
        logger.info(f"Looking for OSM profile with citizen_id: {citizen_id}")
        
        try:
            # ใช้ .only() สำหรับ basic fields เท่านั้น และหลีกเลี่ยง exception กรณีไม่พบ
            osm_profile = (
                await OSMProfile
                .filter(
                    Q(citizen_id=citizen_id)
                    & Q(is_active=True)
                    & (Q(osm_status__isnull=True) | Q(osm_status=""))
                )
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "osm_code",
                    "phone",
                    "email",
                    "gender",
                    "birth_date",
                    "province_id",
                    "district_id",
                    "subdistrict_id",
                    "password_hash",
                    "is_first_login",
                    "is_active",
                    "osm_status",
                )
                .first()
            )
            return osm_profile
        except Exception as e:
            logger.error(f"Error finding OSM profile: {e}")
            raise e

    async def find_osm_profile_with_related_fields(user_credential_id: str):
        """
        ดึง OSM Profile พร้อม related fields สำหรับ UserInfo endpoint
        """
        logger.info(f"Looking for OSM profile with related fields: {user_credential_id}")
        
        try:
            # รวม prefetch related fields ในคำสั่งเดียว และหลีกเลี่ยง exception กรณีไม่พบ
            osm_profile = (
                await OSMProfile
                .filter(id=user_credential_id)
                .prefetch_related(
                    "prefix",
                    "province",
                    "district",
                    "subdistrict",
                    "health_service__health_service_type",
                )
                .first()
            )
            logger.info(f"Found OSM profile with related fields: {osm_profile}")
            return osm_profile
        except Exception as e:
            logger.error(f"Error finding OSM profile with related fields: {e}")
            raise e

    @staticmethod
    async def get_citizen_id_by_id(user_id: str) -> str | None:
        try:
            profile = (
                await OSMProfile
                .filter(id=user_id)
                .only("citizen_id")
                .first()
            )
            return profile.citizen_id if profile else None
        except Exception as e:
            logger.error(f"Error retrieving citizen_id for OSM user {user_id}: {e}")
            raise e
    
    async def find_all_osm(filter: OsmQueryParams):
        filters = OSMProfileRepository._build_filter_kwargs(filter)

        # Sorting
        field = filter.order_by or "created_at"
        if field not in ALLOWED_SORT_FIELDS:
            field = "created_at"  # fallback to default

        order = f"-{field}" if filter.sort_dir == "desc" else field

        # Query with prefetch_related เฉพาะ fields ที่จำเป็นสำหรับ list และเลือกเฉพาะคอลัมน์ที่แสดงผล
        query = (
            OSMProfile
            .filter(**filters)
            .order_by(order)
            .offset((filter.page - 1) * filter.limit)
            .limit(filter.limit)
            .only(
                "id",
                "prefix_id",
                "first_name",
                "last_name",
                "health_service_id",
                "province_id",
                "district_id",
                "subdistrict_id",
            )
            .prefetch_related(*OSMProfileRepository._get_list_related_fields())
        )

        return await query

    async def count_filtered_osm(filter: OsmQueryParams) -> int:
        filters = OSMProfileRepository._build_filter_kwargs(filter)
        return await OSMProfile.filter(**filters).count()

    async def update_osm(osm_id: str, osm_data: Dict[str, Any], user_id: str):
        """
        อัปเดตข้อมูล OSM Profile
        """
        try:
            osm_profile = await OSMProfile.get(id=osm_id)
            
            # Fields ที่อนุญาตให้ set เป็น None ได้ (reset to null)
            _nullable_fields = {
                "osm_showbbody", "retirement_date", "retirement_reason",
                "deleted_at", "approval_by", "approval_date",
                "osm_code", "password_hash",
            }

            # อัปเดตข้อมูลหลัก
            for field, value in osm_data.items():
                if not hasattr(osm_profile, field):
                    continue
                if value is not None:
                    setattr(osm_profile, field, value)
                elif field in _nullable_fields:
                    setattr(osm_profile, field, value)
            
            osm_profile.updated_by = user_id
            await osm_profile.save()
            
            # ดึงข้อมูลที่อัปเดตแล้วพร้อม related fields
            updated_osm = await OSMProfile.filter(id=osm_id).prefetch_related(
                *OSMProfileRepository._get_forward_related_fields()
            ).first()
            
            # ใช้ fetch_related สำหรับ reverse relations
            if updated_osm:
                try:
                    await updated_osm.fetch_related(*OSMProfileRepository._get_reverse_related_fields())
                except Exception as e:
                    logger.error(f"Warning: Could not fetch reverse relations: {e}")
            
            return updated_osm
            
        except DoesNotExist:    
            logger.error(f"DoesNotExist: {osm_id}")
            raise HTTPException(
                status_code=404,
                detail="ไม่พบ OSM Profile ที่ต้องการอัปเดต"
            )
        except Exception as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการอัปเดต OSM: {str(e)}"
            )

    @staticmethod
    async def replace_osm_trainings(
        *,
        osm_id: str,
        trainings: List[Any],
        user_id: str,
    ) -> None:
        """Replace (sync) training records for an OSM profile.

        Implementation choice: hard-delete all existing rows for this profile, then insert
        the payload. This guarantees the final visible list matches exactly what client sends.
        """

        async with in_transaction():
            before_count = await OsmProfileTraining.filter(osm_profile_id=osm_id).count()
            logger.info(f"[replace_osm_trainings] osm_id={osm_id} before_count={before_count} payload={len(trainings or [])}")

            # 1) hard-delete all existing training records for this profile
            await OsmProfileTraining.filter(osm_profile_id=osm_id).delete()

            # 2) insert payload trainings
            for training_item in trainings or []:
                course_id = getattr(training_item, "course_id", None) or getattr(
                    training_item, "training_course_id", None
                )
                trained_year = getattr(training_item, "trained_year", None)
                topic = getattr(training_item, "topic", None)

                if not course_id:
                    continue

                await OsmProfileTraining.create(
                    osm_profile_id=osm_id,
                    training_course_id=course_id,
                    trained_year=trained_year,
                    topic=topic,
                    created_by=user_id,
                    updated_by=user_id,
                )

            after_count = await OsmProfileTraining.filter(osm_profile_id=osm_id).count()
            logger.info(f"[replace_osm_trainings] osm_id={osm_id} after_count={after_count}")

    @staticmethod
    async def upsert_osm_trainings(
        *,
        osm_id: str,
        trainings: List[Any],
        user_id: str,
    ) -> None:
        """Upsert training records for an OSM profile.

        Semantics: merge/upsert only (never deletes existing records).
        Match key is (training_course_id, trained_year). If a record exists (even soft-deleted), it will be updated/revived.
        """

        if not trainings:
            return

        async with in_transaction():
            for training_item in trainings:
                course_id = getattr(training_item, "course_id", None) or getattr(
                    training_item, "training_course_id", None
                )
                trained_year = getattr(training_item, "trained_year", None)
                topic = getattr(training_item, "topic", None)

                # ถ้าไม่มี course_id ให้ข้าม เพื่อไม่ทำให้ระบบ 500
                if not course_id:
                    continue

                existing = await (
                    OsmProfileTraining
                    .filter(
                        osm_profile_id=osm_id,
                        training_course_id=course_id,
                        trained_year=trained_year,
                    )
                    .order_by("created_at")
                    .first()
                )

                if existing:
                    # revive soft-deleted
                    if getattr(existing, "deleted_at", None):
                        existing.deleted_at = None
                    existing.topic = topic
                    existing.updated_by = user_id
                    await existing.save()
                else:
                    await OsmProfileTraining.create(
                        osm_profile_id=osm_id,
                        training_course_id=course_id,
                        trained_year=trained_year,
                        topic=topic,
                        created_by=user_id,
                        updated_by=user_id,
                    )

    # ────────────────────────────────────────────────
    # Replace / Upsert helpers for nested relations
    # ────────────────────────────────────────────────

    @staticmethod
    async def upsert_osm_spouse(
        *,
        osm_id: str,
        spouse_data: Any,
        user_id: str,
    ) -> None:
        """Upsert (create or update) the spouse record for an OSM profile.

        If *spouse_data* is ``None`` / falsy the existing spouse row (if any) is deleted.
        """
        async with in_transaction():
            existing = await OsmSpouse.filter(osm_profile_id=osm_id).first()

            if not spouse_data:
                # ลบคู่สมรสเดิม (ถ้ามี)
                if existing:
                    await existing.delete()
                return

            spouse_dict = (
                spouse_data.model_dump()
                if hasattr(spouse_data, "model_dump")
                else dict(spouse_data)
            )

            if existing:
                for field, value in spouse_dict.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                existing.updated_by = user_id
                await existing.save()
            else:
                spouse_dict["osm_profile_id"] = osm_id
                spouse_dict["created_by"] = user_id
                await OsmSpouse.create(**spouse_dict)

    @staticmethod
    async def replace_osm_children(
        *,
        osm_id: str,
        children: List[Any],
        user_id: str,
    ) -> None:
        """Replace all children records for an OSM profile (delete-then-insert)."""

        async with in_transaction():
            await OsmChild.filter(osm_profile_id=osm_id).delete()

            for child_data in children or []:
                child_dict = (
                    child_data.model_dump()
                    if hasattr(child_data, "model_dump")
                    else dict(child_data)
                )
                child_dict["osm_profile_id"] = osm_id
                child_dict["created_by"] = user_id
                await OsmChild.create(**child_dict)

    @staticmethod
    async def replace_osm_official_positions(
        *,
        osm_id: str,
        positions: List[Any],
        user_id: str,
    ) -> None:
        """Replace all official-position assignments for an OSM profile."""

        async with in_transaction():
            await OsmProfileOfficialPosition.filter(osm_profile_id=osm_id).delete()

            for pos in positions or []:
                position_id = getattr(pos, "position_id", None)
                custom_title = getattr(pos, "custom_title", None)
                if not position_id:
                    continue
                await OsmProfileOfficialPosition.create(
                    osm_profile_id=osm_id,
                    official_position_id=position_id,
                    custom_title=custom_title,
                    created_by=user_id,
                    updated_by=user_id,
                )

    @staticmethod
    async def replace_osm_special_skills(
        *,
        osm_id: str,
        skills: List[Any],
        user_id: str,
    ) -> None:
        """Replace all special-skill assignments for an OSM profile."""

        async with in_transaction():
            await OsmProfileSpecialSkill.filter(osm_profile_id=osm_id).delete()

            for skill in skills or []:
                skill_id = getattr(skill, "skill_id", None)
                custom_skill = getattr(skill, "custom_skill", None)
                if not skill_id:
                    continue
                await OsmProfileSpecialSkill.create(
                    osm_profile_id=osm_id,
                    special_skill_id=skill_id,
                    custom_skill=custom_skill,
                    created_by=user_id,
                    updated_by=user_id,
                )

    @staticmethod
    async def replace_osm_club_positions(
        *,
        osm_id: str,
        club_positions: List[Any],
        user_id: str,
    ) -> None:
        """Replace all club-position assignments for an OSM profile."""

        async with in_transaction():
            await OsmProfileClubPosition.filter(osm_profile_id=osm_id).delete()

            for cp in club_positions or []:
                club_position_id = getattr(cp, "club_position_id", None)
                appointed_level = getattr(cp, "appointed_level", None)
                if not club_position_id:
                    continue
                await OsmProfileClubPosition.create(
                    osm_profile_id=osm_id,
                    club_position_id=club_position_id,
                    appointed_level=appointed_level,
                    created_by=user_id,
                    updated_by=user_id,
                )

    async def delete_osm(osm_id: str):
        """
        ลบ OSM Profile (Soft Delete)
        """
        try:
            osm_profile = await OSMProfile.get(id=osm_id)
            await osm_profile.delete()
            return {"message": "ลบ OSM Profile สำเร็จ"}
            
        except DoesNotExist:
            logger.error(f"DoesNotExist: {osm_id}")
            raise HTTPException(
                status_code=404,
                detail="ไม่พบ OSM Profile ที่ต้องการลบ"
            )
        except Exception as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการลบ OSM: {str(e)}"
            )

    async def count_all_osm():
        """
        นับจำนวน OSM ทั้งหมด
        """
        return await OSMProfile.all().count()

    async def count_osm_by_gender(gender: str):
        """
        นับจำนวน OSM ตามเพศ
        """
        return await OSMProfile.filter(gender=gender).count()

    async def get_osm_stats_by_province():
        """
        ดึงสถิติ OSM ตามจังหวัด
        """
        from tortoise.functions import Count
        
        stats = await OSMProfile.annotate(
            count=Count('id')
        ).group_by('province_id').values('province_id', 'count')
        
        return stats

    # Position Confirmation Methods
    async def create_or_update_position_confirmation(osm_profile_id: str, osm_position_ids: List[str], allowance_confirmation_status: str, user_id: str):
        """
        สร้างหรืออัปเดตการยืนยันตำแหน่งและสิทธิ์เงินค่าป่วยการ (upsert)
        """
        try:
            # ตรวจสอบว่า OSM Profile มีอยู่หรือไม่
            osm_profile = await OSMProfile.get(id=osm_profile_id)
            if not osm_profile:
                logger.error(f"OSM Profile not found: {osm_profile_id}")
                raise HTTPException(
                    status_code=404,
                    detail="ไม่พบ OSM Profile ที่ต้องการ"
                )
            
            # ตรวจสอบว่า OSM Positions มีอยู่หรือไม่
            osm_positions = []
            for position_id in osm_position_ids:
                position = await OsmPosition.get(id=position_id)
                if not position:
                    logger.error(f"Position not found: {position_id}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"ไม่พบตำแหน่ง ID: {position_id}"
                    )
                osm_positions.append(position)
            
            # ใช้ update_or_create เพื่อ upsert
            position_confirmation, created = await OsmPositionConfirmation.update_or_create(
                osm_profile_id=osm_profile_id,
                defaults={
                    'allowance_confirmation_status': allowance_confirmation_status,
                    'created_by': user_id, 
                    'updated_by': user_id
                }
            )
            # ลบตำแหน่งเดิมทั้งหมดจาก through table
            await OsmPositionConfirmationPosition.filter(
                position_confirmation_id=position_confirmation.id
            ).delete()

            # เพิ่มตำแหน่งใหม่ผ่าน through table
            for position in osm_positions:
                await OsmPositionConfirmationPosition.create(
                    position_confirmation_id=position_confirmation.id,
                    osm_position_id=position.id,
                    created_by=user_id,
                    updated_by=user_id
                )
            
            return position_confirmation
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการสร้างหรืออัปเดตการยืนยันตำแหน่ง: {str(e)}"
            )

    async def get_position_confirmation_by_osm_id(osm_profile_id: str):
        """
        ดึงการยืนยันตำแหน่งของ OSM Profile
        """
        try:
            position_confirmation = await OsmPositionConfirmation.filter(
                osm_profile_id=osm_profile_id,
                deleted_at__isnull=True
            ).prefetch_related('osm_positions', 'osm_profile').first()
            
            return position_confirmation
            
        except Exception as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงการยืนยันตำแหน่ง: {str(e)}"
            )

    async def delete_position_confirmation(confirmation_id: str, user_id: str):
        """
        ลบการยืนยันตำแหน่ง (Soft Delete)
        """
        try:
            position_confirmation = await OsmPositionConfirmation.get(id=confirmation_id)
            position_confirmation.deleted_at = datetime.datetime.now()
            position_confirmation.updated_by = user_id
            await position_confirmation.save()
            
            return {"message": "ลบการยืนยันตำแหน่งสำเร็จ"}
            
        except DoesNotExist:
            logger.error(f"DoesNotExist: {confirmation_id}")
            raise HTTPException(
                status_code=404,
                detail="ไม่พบการยืนยันตำแหน่งที่ต้องการลบ"
            )
        except Exception as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการลบการยืนยันตำแหน่ง: {str(e)}"
            )

    async def get_all_osm_positions():
        """
        ดึงตำแหน่ง OSM ทั้งหมด
        """
        try:
            positions = await OsmPosition.filter(deleted_at__isnull=True).order_by('position_name_th')
            return positions
        except Exception as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงตำแหน่ง OSM: {str(e)}"
            )
        
    async def set_password(citizen_id: str, hashed_password: str):
        """
        ตั้งรหัสผ่าน OSM Profile (pre-login flow)
        รองรับทั้งกรณี:
        - password_hash IS NULL (ยังไม่เคยมีรหัส)
        - password_hash IS NOT NULL แต่ is_first_login=True (bulk set default password)
        """
        # กรณี 1: ยังไม่มี password_hash เลย
        osm_profile = await OSMProfile.filter(
            citizen_id=citizen_id,
            is_first_login=True,
            password_hash__isnull=True,
        ).first()

        # กรณี 2: มี password_hash แล้ว แต่ยัง is_first_login=True (เช่น bulk set default password)
        if not osm_profile:
            osm_profile = await OSMProfile.filter(
                citizen_id=citizen_id,
                is_first_login=True,
            ).first()

        if not osm_profile:
            raise DoesNotExist("OSMProfile not found or already changed password")

        osm_profile.password_hash = hashed_password
        osm_profile.is_first_login = False
        await osm_profile.save()
        return osm_profile

    @staticmethod
    async def set_password_by_id(
        osm_id: str,
        hashed_password: str,
        *,
        mark_first_login: bool = False,
        reset_attempts: bool = True,
        reactivate: bool = True,
        updated_by: Optional[str] = None,
    ) -> bool:
        if not osm_id:
            return False
        try:
            update_payload: Dict[str, Any] = {
                "password_hash": hashed_password,
                "updated_at": datetime.datetime.utcnow(),
            }
            update_payload["is_first_login"] = bool(mark_first_login)
            if reset_attempts:
                update_payload["password_attempts"] = 0
            if reactivate:
                update_payload["is_active"] = True
            if updated_by:
                update_payload["updated_by"] = updated_by
            updated = (
                await OSMProfile
                .filter(id=osm_id, deleted_at__isnull=True)
                .update(**update_payload)
            )
            return bool(updated)
        except Exception as exc:
            logger.error(f"Error updating OSM password for id {osm_id}: {exc}")
            raise

    @staticmethod
    async def get_password_state(osm_id: str):
        try:
            return (
                await OSMProfile
                .filter(id=osm_id, deleted_at__isnull=True)
                .only("id", "password_hash", "password_attempts", "is_active")
                .first()
            )
        except Exception as exc:
            logger.error(f"Error retrieving password state for OSM {osm_id}: {exc}")
            raise

    @staticmethod
    async def update_password_attempts(osm_id: str, attempts: int, *, deactivate: bool = False) -> None:
        try:
            update_payload: Dict[str, Any] = {"password_attempts": attempts, "updated_at": datetime.datetime.utcnow()}
            if deactivate:
                update_payload["is_active"] = False
            await OSMProfile.filter(id=osm_id, deleted_at__isnull=True).update(**update_payload)
        except Exception as exc:
            logger.error(f"Error updating password attempts for OSM {osm_id}: {exc}")
            raise


