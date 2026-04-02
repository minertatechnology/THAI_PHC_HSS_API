from datetime import datetime, date
from typing import List, Optional, Mapping, Any

from fastapi import HTTPException

from app.api.v1.schemas.osm_schema import OsmCreateSchema, OsmUpdateSchema
from app.api.v1.schemas.query_schema import OsmQueryParams
from app.api.v1.schemas.response_schema import (
    osm_to_list_response,
    osm_to_public_summary_response,
    osm_to_response,
)
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.repositories.osm_status_history_repository import OsmStatusHistoryRepository
from app.services.oauth2_service import bcrypt_hash_password
from app.services.officer_snapshot_helper import build_officer_snapshot
from app.services.permission_service import PermissionService
from app.models.enum_models import AdministrativeLevelEnum, ApprovalStatus
from app.utils.officer_hierarchy import OfficerHierarchy, OfficerScope
from app.models.geography_model import Province, Village
from app.models.osm_model import OSMProfile
from app.services.notification_service import NotificationService
from app.utils.logging_utils import get_logger
from app.cache.redis_client import cache_delete_pattern
from app.api.middleware.middleware import invalidate_user_sessions

logger = get_logger(__name__)

class OsmService:
    @staticmethod
    def _normalize_osm_showbbody_input(value: Any) -> Optional[str]:
        if value is None:
            return None
        raw = str(value).strip()
        if raw == "":
            return None

        lowered = raw.lower()
        mapped = {
            "eligible": "1",
            "ineligible": "5",
            "pending": "6",
        }.get(lowered, raw)

        mapped_str = str(mapped).strip()
        if mapped_str in {"1", "2", "5", "6"}:
            return mapped_str

        raise HTTPException(status_code=400, detail="invalid_osm_showbbody")

    async def find_all_osm(filter: OsmQueryParams):
        """
        ค้นหา OSM ทั้งหมดพร้อม filter และ pagination
        """
        try:
            result = await OSMProfileRepository.find_all_osm(filter)
            response = []
            for osm in result:
                response.append(osm_to_list_response(osm))
            return response
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการค้นหา OSM: {str(e)}"
            )

    async def create_osm(
        osm_data: OsmCreateSchema,
        current_user: Optional[dict] = None,
    ):
        """
        สร้าง OSM Profile ใหม่พร้อมตรวจสอบข้อมูลซ้ำ
        """
        try:
            # ตรวจสอบว่าเลขบัตรประชาชนซ้ำหรือไม่
            existing_osm = await OSMProfileRepository.find_osm_by_citizen_id(osm_data.citizen_id)
            if existing_osm:
                # ถ้าพ้นสภาพ (เสียชีวิต/ลาออก/พ้นสภาพ) → อนุญาตให้ลงทะเบียนใหม่ (re-register)
                _retired_statuses = {"0", "1", "2"}
                current_status = str(getattr(existing_osm, "osm_status", "") or "")
                if current_status in _retired_statuses:
                    return await OsmService._re_register_retired_osm(
                        existing_osm=existing_osm,
                        osm_data=osm_data,
                        current_user=current_user,
                    )
                raise HTTPException(
                    status_code=400,
                    detail="เลขบัตรประชาชนนี้มีอยู่ในระบบแล้ว"
                )
            creator_id: Optional[str] = None
            auto_approve = False
            approval_by: Optional[str] = None
            approval_date: Optional[date] = None

            if current_user:
                raw_user_id = current_user.get("user_id")
                creator_id = str(raw_user_id) if raw_user_id else None

                if current_user.get("user_type") == "officer":
                    _, officer_scope = await PermissionService.resolve_officer_context(current_user)
                    if (
                        officer_scope
                        and creator_id
                        and await OsmService._officer_can_auto_approve(officer_scope, osm_data)
                    ):
                        auto_approve = True
                        approval_by = creator_id
                        approval_date = datetime.utcnow().date()

            # สร้าง OSM Profile
            result = await OSMProfileRepository.create_osm(
                osm_data,
                creator_id,
                auto_approve=auto_approve,
                approval_by=approval_by,
                approval_date=approval_date,
            )

            detailed_profile = None
            try:
                created_profile = await OSMProfileRepository.find_osm_by_id(result.get("id"))
                if created_profile and created_profile.get("osm_profile"):
                    profile_obj = created_profile["osm_profile"]
                    # ใช้ตัวเดียวกับ GET detail เพื่อให้ field ที่เติมเอง (village_code/showbody/etc.) สอดคล้องกัน
                    detailed_profile = await OsmService.get_osm_by_id(str(profile_obj.id))

                    # --- Notification ---
                    await NotificationService.create_notification_from_osm_profile(
                        actor_id=creator_id,
                        action_type="create",
                        osm_profile=profile_obj,
                    )
            except Exception:
                # If enrichment fails we still return a success response without detailed payload.
                detailed_profile = None

            await cache_delete_pattern("dashboard:*")
            return {
                "status": "success",
                "data": detailed_profile,
                "message": "สร้าง OSM Profile สำเร็จ"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการสร้าง OSM: {str(e)}"
            )

    @staticmethod
    async def _officer_can_auto_approve(officer_scope: OfficerScope, osm_data: OsmCreateSchema) -> bool:
        allowed_levels = {
            AdministrativeLevelEnum.PROVINCE,
            AdministrativeLevelEnum.AREA,
            AdministrativeLevelEnum.REGION,
            AdministrativeLevelEnum.COUNTRY,
        }
        if officer_scope.level not in allowed_levels:
            return False

        target_scope = await OsmService._build_target_scope(osm_data)
        if not target_scope:
            return False
        return OfficerHierarchy.can_manage(officer_scope, target_scope)

    @staticmethod
    async def _build_target_scope(osm_data: OsmCreateSchema) -> Optional[OfficerScope]:
        province_health_area: Optional[str] = None
        province_region: Optional[str] = None

        try:
            province = await Province.filter(province_code=osm_data.province_id).only("health_area_id", "region_id").first()
            if province:
                province_health_area = getattr(province, "health_area_id", None)
                province_region = getattr(province, "region_id", None)
        except Exception:
            province_health_area = None
            province_region = None

        target_level = AdministrativeLevelEnum.SUBDISTRICT
        if not osm_data.subdistrict_id:
            target_level = (
                AdministrativeLevelEnum.DISTRICT
                if osm_data.district_id
                else AdministrativeLevelEnum.PROVINCE
            )

        return OfficerScope(
            level=target_level,
            health_area_id=province_health_area,
            province_id=osm_data.province_id,
            district_id=osm_data.district_id if osm_data.district_id else None,
            subdistrict_id=osm_data.subdistrict_id if osm_data.subdistrict_id else None,
            region_code=province_region,
        )

    @staticmethod
    async def _re_register_retired_osm(
        existing_osm: OSMProfile,
        osm_data: OsmCreateSchema,
        current_user: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        """ลงทะเบียนใหม่สำหรับ อสม. ที่พ้นสภาพแล้ว
        อัปเดต record เดิม (ไม่สร้าง row ใหม่) → reset สถานะ + เปลี่ยนที่อยู่ + เก็บ history"""

        osm_id = str(existing_osm.id)

        # --- snapshot ค่าเก่า ---
        prev_osm_status = str(getattr(existing_osm, "osm_status", None) or "")
        prev_is_active = getattr(existing_osm, "is_active", False)
        prev_approval_status = str(getattr(existing_osm, "approval_status", None) or "")

        # --- determine creator & auto-approve ---
        creator_id: Optional[str] = None
        auto_approve = False
        approval_by: Optional[str] = None
        approval_date_val: Optional[date] = None

        if current_user:
            raw_uid = current_user.get("user_id")
            creator_id = str(raw_uid) if raw_uid else None

            if current_user.get("user_type") == "officer":
                _, officer_scope = await PermissionService.resolve_officer_context(current_user)
                if (
                    officer_scope
                    and creator_id
                    and await OsmService._officer_can_auto_approve(officer_scope, osm_data)
                ):
                    auto_approve = True
                    approval_by = creator_id
                    approval_date_val = datetime.utcnow().date()

        # --- build flat update payload from registration data ---
        osm_dict = osm_data.model_dump(
            exclude={"spouse", "children", "official_positions", "special_skills",
                     "club_positions", "trainings"},
            exclude_none=True,
        )
        # ลบ citizen_id ออก (ไม่ต้องเปลี่ยน)
        osm_dict.pop("citizen_id", None)

        # showbody alias
        showbody = osm_dict.pop("showbody", None)
        if osm_dict.get("osm_showbbody") is None and showbody is not None:
            osm_dict["osm_showbbody"] = showbody

        # normalize osm_showbbody
        raw_showbbody = osm_dict.get("osm_showbbody")
        if raw_showbbody is not None:
            osm_dict["osm_showbbody"] = OsmService._normalize_osm_showbbody_input(raw_showbbody)

        # normalize new_registration_allowance_status
        raw_allowance = osm_dict.get("new_registration_allowance_status")
        if raw_allowance is not None:
            stripped = str(raw_allowance).strip()
            if stripped == "":
                osm_dict.pop("new_registration_allowance_status", None)

        # --- reset status fields ---
        osm_dict["osm_status"] = ""
        osm_dict["retirement_date"] = None
        osm_dict["retirement_reason"] = None
        osm_dict["deleted_at"] = None
        osm_dict["password_attempts"] = 0
        osm_dict["is_first_login"] = True

        # reset osm_showbbody → null ถ้า registration data ไม่ได้ส่งค่ามา
        # เพราะค่าเดิม "5" (ไม่ได้รับเงิน) จากตอนพ้นสภาพจะค้างอยู่
        # officer ต้องพิจารณาและกำหนด osm_showbbody ใหม่ตาม flow ปกติ
        if "osm_showbbody" not in osm_dict:
            osm_dict["osm_showbbody"] = None

        if auto_approve:
            osm_dict["is_active"] = True
            osm_dict["approval_status"] = ApprovalStatus.APPROVED.value
            osm_dict["approval_by"] = approval_by
            osm_dict["approval_date"] = approval_date_val

            # generate new osm_code for new area
            try:
                prefix = OSMProfileRepository._build_osm_code_prefix(osm_dict)
                run_no = await OSMProfileRepository._allocate_next_osm_code_run(prefix)
                osm_dict["osm_code"] = f"{prefix}{run_no:06d}"
                osm_dict.setdefault("village_code", prefix)
            except Exception as code_err:
                logger.warning("Could not generate osm_code on re-register for %s: %s", osm_id, code_err)

            # reset password
            cid = getattr(existing_osm, "citizen_id", None)
            if cid:
                osm_dict["password_hash"] = bcrypt_hash_password(cid)
        else:
            osm_dict["is_active"] = False
            osm_dict["approval_status"] = ApprovalStatus.PENDING.value
            osm_dict["approval_by"] = None
            osm_dict["approval_date"] = None
            osm_dict["osm_code"] = None
            osm_dict["password_hash"] = None
            # still try to set village_code
            try:
                vc_prefix = OSMProfileRepository._build_osm_code_prefix(osm_dict)
                osm_dict.setdefault("village_code", vc_prefix)
            except Exception:
                pass

        audit_user_id = creator_id or osm_id

        # --- persist flat fields ---
        try:
            await OSMProfileRepository.update_osm(osm_id, osm_dict, audit_user_id)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"ไม่สามารถลงทะเบียนใหม่ได้: {e}",
            )

        # --- replace nested relations ---
        try:
            await OSMProfileRepository.upsert_osm_spouse(
                osm_id=osm_id, spouse_data=osm_data.spouse, user_id=audit_user_id,
            )
            await OSMProfileRepository.replace_osm_children(
                osm_id=osm_id, children=osm_data.children or [], user_id=audit_user_id,
            )
            await OSMProfileRepository.replace_osm_official_positions(
                osm_id=osm_id, positions=osm_data.official_positions or [], user_id=audit_user_id,
            )
            await OSMProfileRepository.replace_osm_special_skills(
                osm_id=osm_id, skills=osm_data.special_skills or [], user_id=audit_user_id,
            )
            await OSMProfileRepository.replace_osm_club_positions(
                osm_id=osm_id, club_positions=osm_data.club_positions or [], user_id=audit_user_id,
            )
            await OSMProfileRepository.replace_osm_trainings(
                osm_id=osm_id, trainings=osm_data.trainings or [], user_id=audit_user_id,
            )
        except Exception as nested_err:
            logger.warning("Error replacing nested relations on re-register %s: %s", osm_id, nested_err)

        # --- history ---
        try:
            officer_name = ""
            if current_user:
                officer_name = f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
            changed_by_name = officer_name or "ลงทะเบียนตนเอง"

            await OsmStatusHistoryRepository.create({
                "osm_profile_id": osm_id,
                "previous_osm_status": prev_osm_status,
                "new_osm_status": "",
                "previous_is_active": prev_is_active,
                "new_is_active": osm_dict["is_active"],
                "previous_approval_status": prev_approval_status,
                "new_approval_status": osm_dict["approval_status"],
                "province_code": osm_data.province_id,
                "district_code": osm_data.district_id,
                "subdistrict_code": osm_data.subdistrict_id,
                "village_no": getattr(osm_data, "village_no", None),
                "retirement_reason": None,
                "remark": "ลงทะเบียนใหม่หลังพ้นสภาพ (re-register)",
                "changed_by": creator_id or existing_osm.id,
                "changed_by_name": changed_by_name,
            })
        except Exception:
            logger.exception("Failed to record re-register history for %s", osm_id)

        # --- notification ---
        try:
            refreshed = await OSMProfileRepository.find_osm_by_id(osm_id)
            profile_obj = refreshed.get("osm_profile") if refreshed else None
            if profile_obj:
                await NotificationService.create_notification_from_osm_profile(
                    actor_id=creator_id,
                    action_type="re_register",
                    osm_profile=profile_obj,
                )
        except Exception:
            logger.exception("Failed to send re-register notification for %s", osm_id)

        # --- response ---
        await cache_delete_pattern("dashboard:*")
        try:
            detailed_profile = await OsmService.get_osm_by_id(osm_id)
        except Exception:
            detailed_profile = None

        return {
            "status": "success",
            "data": detailed_profile,
            "message": "ลงทะเบียน อสม. ใหม่สำเร็จ (re-register)",
        }

    @staticmethod
    def _build_scope_from_existing_profile(profile: OSMProfile) -> OfficerScope:
        if not profile or not getattr(profile, "province_id", None):
            raise HTTPException(status_code=400, detail="osm_profile_missing_location")

        province = getattr(profile, "province", None)
        province_health_area = getattr(province, "health_area_id", None) if province else None
        province_region = getattr(province, "region_id", None) if province else None

        target_level = AdministrativeLevelEnum.SUBDISTRICT
        if not getattr(profile, "subdistrict_id", None):
            target_level = (
                AdministrativeLevelEnum.DISTRICT
                if getattr(profile, "district_id", None)
                else AdministrativeLevelEnum.PROVINCE
            )

        return OfficerScope(
            level=target_level,
            health_area_id=province_health_area,
            province_id=profile.province_id,
            district_id=profile.district_id,
            subdistrict_id=profile.subdistrict_id,
            region_code=province_region,
        )

    async def get_osm_by_id(osm_id: str):
        """
        ดึงข้อมูล OSM Profile ด้วย ID
        """
        try:
            def _enum_to_str(value):
                return value.value if getattr(value, "value", None) is not None else value

            result = await OSMProfileRepository.find_osm_by_id(osm_id)
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="ไม่พบ OSM Profile ที่ต้องการ"
                )
            
            osm_profile = result["osm_profile"]
            response_model = osm_to_response(
                osm_profile,
                spouses=result.get("spouses"),
                children=result.get("children"),
                official_positions=result.get("official_positions"),
                special_skills=result.get("special_skills"),
                club_positions=result.get("club_positions"),
                trainings=result.get("trainings"),
            ).model_dump()

            # เติมข้อมูลที่ response model ไม่ครอบคลุม
            response_model["osm_code"] = getattr(osm_profile, "osm_code", None)
            response_model["osmCode"] = response_model["osm_code"]
            response_model["village_code"] = getattr(osm_profile, "village_code", None)

            # สถานะเงินเยียวยา/ค่าป่วยการ (osm_showbbody) + alias ที่ frontend เรียก "showbody"
            response_model["osm_showbbody"] = _enum_to_str(getattr(osm_profile, "osm_showbbody", None))
            response_model["showbody"] = response_model["osm_showbbody"]

            # สถานะ อสม. (osm_status): '' = ปกติ, '0' = เสียชีวิต, '1' = ลาออก, '2' = พ้นสภาพ
            response_model["osm_status"] = _enum_to_str(getattr(osm_profile, "osm_status", None))

            # สถานะสิทธิ์ค่าป่วยการตอนสมัครใหม่ (new_registration_allowance_status)
            response_model["new_registration_allowance_status"] = _enum_to_str(
                getattr(osm_profile, "new_registration_allowance_status", None)
            )

            # เติมชื่อหมู่บ้านจากตาราง villages (ถ้ามี village_code แต่ไม่มี village_name)
            if response_model.get("village_code") and not response_model.get("village_name"):
                village = await Village.get_or_none(village_code=response_model["village_code"]).only(
                    "village_name_th"
                )
                if village:
                    response_model["village_name"] = getattr(village, "village_name_th", None)

            response_model["approval_by"] = getattr(osm_profile, "approval_by", None)
            response_model["approval_date"] = (
                str(osm_profile.approval_date) if getattr(osm_profile, "approval_date", None) else None
            )
            response_model["created_by"] = getattr(osm_profile, "created_by", None)
            response_model["updated_by"] = getattr(osm_profile, "updated_by", None)

            created_snapshot = await build_officer_snapshot(response_model["created_by"])
            updated_snapshot = await build_officer_snapshot(response_model["updated_by"])
            approval_snapshot = await build_officer_snapshot(response_model["approval_by"])

            response_model["created_by_name"] = created_snapshot.get("name") if created_snapshot else None
            response_model["created_by_position_name"] = created_snapshot.get("position_name") if created_snapshot else None
            response_model["created_by_scope_level"] = created_snapshot.get("scope_level") if created_snapshot else None
            response_model["created_by_scope_label"] = created_snapshot.get("scope_label") if created_snapshot else None

            response_model["updated_by_name"] = updated_snapshot.get("name") if updated_snapshot else None
            response_model["updated_by_position_name"] = updated_snapshot.get("position_name") if updated_snapshot else None
            response_model["updated_by_scope_level"] = updated_snapshot.get("scope_level") if updated_snapshot else None
            response_model["updated_by_scope_label"] = updated_snapshot.get("scope_label") if updated_snapshot else None

            response_model["approval_by_name"] = approval_snapshot.get("name") if approval_snapshot else None
            response_model["approval_by_position_name"] = approval_snapshot.get("position_name") if approval_snapshot else None
            response_model["approval_by_scope_level"] = approval_snapshot.get("scope_level") if approval_snapshot else None
            response_model["approval_by_scope_label"] = approval_snapshot.get("scope_label") if approval_snapshot else None

            return response_model
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงข้อมูล OSM: {str(e)}"
            )

    async def get_osm_summary_by_id(osm_id: str):
        """
        ดึงข้อมูล OSM Profile แบบย่อด้วย ID
        """
        try:
            osm_profile = await OSMProfileRepository.find_list_profile_by_id(osm_id)
            if not osm_profile:
                raise HTTPException(status_code=404, detail="ไม่พบ OSM Profile ที่ต้องการ")
            return osm_to_public_summary_response(osm_profile)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงข้อมูล OSM: {str(e)}"
            )

    @staticmethod
    async def get_osms_by_ids(osm_ids: List[str]):
        if not osm_ids:
            raise HTTPException(status_code=400, detail="ids_required")

        unique_ids = list(dict.fromkeys(osm_ids))
        items: List[dict] = []
        errors: List[dict] = []

        for osm_id in unique_ids:
            try:
                data = await OsmService.get_osm_by_id(osm_id)
                items.append(data)
            except HTTPException as exc:
                errors.append({"id": osm_id, "error": str(exc.detail)})

        return {"data": items, "errors": errors}

    async def get_osm_by_citizen_id(citizen_id: str):
        """
        ดึงข้อมูล OSM Profile ด้วยเลขบัตรประชาชน
        """
        try:
            osm_profile = await OSMProfileRepository.find_osm_by_citizen_id(citizen_id)
            if not osm_profile:
                raise HTTPException(
                    status_code=404,
                    detail="ไม่พบ OSM Profile ที่ต้องการ"
                )
            
            return osm_to_response(osm_profile)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงข้อมูล OSM: {str(e)}"
            )

    async def update_osm(osm_id: str, osm_data: OsmUpdateSchema, user_id: str):
        """
        อัปเดตข้อมูล OSM Profile
        """
        try:
            # ตรวจสอบว่า OSM Profile มีอยู่หรือไม่
            existing_record = await OSMProfileRepository.find_osm_by_id(osm_id)
            existing_osm = existing_record.get("osm_profile") if existing_record else None
            if not existing_osm:
                raise HTTPException(
                    status_code=404,
                    detail="ไม่พบ OSM Profile ที่ต้องการอัปเดต"
                )

            # ตรวจสอบเลขบัตรประชาชนซ้ำ (ถ้ามีการเปลี่ยนแปลง)
            if osm_data.citizen_id and osm_data.citizen_id != existing_osm.citizen_id:
                duplicate_osm = await OSMProfileRepository.find_osm_by_citizen_id(osm_data.citizen_id)
                if duplicate_osm and str(duplicate_osm.id) != str(existing_osm.id):
                    raise HTTPException(
                        status_code=400,
                        detail="เลขบัตรประชาชนนี้มีอยู่ในระบบแล้ว"
                    )

            # อัปเดตข้อมูล
            update_data = osm_data.model_dump(exclude_unset=True)

            # ── แยกข้อมูล nested relation ออกจาก flat fields ──
            # trainings เป็นข้อมูลในตารางแยก (osm_profile_trainings) ไม่ใช่ field บน OSMProfile
            trainings_payload = update_data.pop("trainings", None)
            spouse_payload = update_data.pop("spouse", None)
            children_payload = update_data.pop("children", None)
            official_positions_payload = update_data.pop("official_positions", None)
            special_skills_payload = update_data.pop("special_skills", None)
            club_positions_payload = update_data.pop("club_positions", None)

            # flag เพื่อแยก "ไม่ได้ส่ง field มาเลย" (None) กับ "ส่งมาแต่เป็น null/[]"
            spouse_sent = "spouse" in osm_data.model_fields_set
            children_sent = "children" in osm_data.model_fields_set
            official_positions_sent = "official_positions" in osm_data.model_fields_set
            special_skills_sent = "special_skills" in osm_data.model_fields_set
            club_positions_sent = "club_positions" in osm_data.model_fields_set

            # รองรับ client ที่ส่ง alias "showbody" และ map ให้ลง field จริง "osm_showbbody"
            showbody = update_data.pop("showbody", None)
            if "osm_showbbody" not in update_data and showbody is not None:
                update_data["osm_showbbody"] = showbody

            # normalize/validate osm_showbbody to avoid ORM enum errors (which become 500)
            if "osm_showbbody" in update_data:
                normalized_showbbody = OsmService._normalize_osm_showbbody_input(update_data.get("osm_showbbody"))
                if normalized_showbbody is None:
                    update_data.pop("osm_showbbody", None)
                else:
                    update_data["osm_showbbody"] = normalized_showbbody

            await OSMProfileRepository.update_osm(osm_id, update_data, user_id)

            # ถ้าส่ง trainings มา ให้ sync ตามรายการที่ส่งมา (replace semantics)
            # - ส่งมา 1 รายการ => เหลือ 1 รายการ
            # - ส่งมา [] => ลบ (soft-delete) ทั้งหมด
            # - ไม่ส่ง field trainings มาเลย => ไม่แตะ trainings เดิม
            if trainings_payload is not None:
                await OSMProfileRepository.replace_osm_trainings(
                    osm_id=osm_id,
                    trainings=osm_data.trainings or [],
                    user_id=user_id,
                )

            # ── Spouse: upsert หรือ ลบ ──
            if spouse_sent:
                await OSMProfileRepository.upsert_osm_spouse(
                    osm_id=osm_id,
                    spouse_data=osm_data.spouse,
                    user_id=user_id,
                )

            # ── Children: replace ──
            if children_sent:
                await OSMProfileRepository.replace_osm_children(
                    osm_id=osm_id,
                    children=osm_data.children or [],
                    user_id=user_id,
                )

            # ── Official Positions: replace ──
            if official_positions_sent:
                await OSMProfileRepository.replace_osm_official_positions(
                    osm_id=osm_id,
                    positions=osm_data.official_positions or [],
                    user_id=user_id,
                )

            # ── Special Skills: replace ──
            if special_skills_sent:
                await OSMProfileRepository.replace_osm_special_skills(
                    osm_id=osm_id,
                    skills=osm_data.special_skills or [],
                    user_id=user_id,
                )

            # ── Club Positions: replace ──
            if club_positions_sent:
                await OSMProfileRepository.replace_osm_club_positions(
                    osm_id=osm_id,
                    club_positions=osm_data.club_positions or [],
                    user_id=user_id,
                )

            # โหลดข้อมูลแบบเดียวกับ GET detail เพื่อให้ reverse relations ถูก resolve และ field ที่เติมเองครบ
            result = await OsmService.get_osm_by_id(osm_id)

            # --- Notification ---
            await NotificationService.create_notification(
                actor_id=user_id,
                action_type="update",
                target_type="osm",
                target_id=osm_id,
                target_name=f"{existing_osm.first_name} {existing_osm.last_name}".strip(),
                citizen_id=getattr(existing_osm, "citizen_id", None),
                province_code=getattr(existing_osm, "province_id", None),
                district_code=getattr(existing_osm, "district_id", None),
                subdistrict_code=getattr(existing_osm, "subdistrict_id", None),
            )

            await cache_delete_pattern("dashboard:*")
            return result

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการอัปเดต OSM: {str(e)}"
            )

    async def set_active_status(
        osm_id: str,
        is_active: bool,
        current_user: Mapping[str, Any] | None,
        *,
        approval_status: Optional[str] = None,
        osm_status: Optional[str] = None,
        osm_showbbody: Optional[str] = None,
        retirement_date: Optional[date] = None,
        retirement_reason: Optional[str] = None,
    ):
        """ปรับสถานะการใช้งานของ OSM profile โดยจำกัดให้เจ้าหน้าที่ระดับจังหวัดขึ้นไปทำรายการได้"""

        if current_user is None:
            raise HTTPException(status_code=403, detail="forbidden: officer access required")

        await PermissionService.require_officer_scope_at_least(
            current_user,
            minimum_level=AdministrativeLevelEnum.PROVINCE,
        )

        _, officer_scope = await PermissionService.resolve_officer_context(current_user)
        if not officer_scope:
            raise HTTPException(status_code=403, detail="forbidden: officer scope unavailable")

        try:
            profile_for_management = await OSMProfileRepository.get_profile_for_management(osm_id)
        except Exception as repo_error:
            raise HTTPException(
                status_code=500,
                detail=f"ไม่สามารถโหลดข้อมูล OSM สำหรับการปรับสถานะได้: {repo_error}",
            )

        if not profile_for_management:
            raise HTTPException(status_code=404, detail="ไม่พบ OSM Profile ที่ต้องการ")

        target_scope = OsmService._build_scope_from_existing_profile(profile_for_management)
        if target_scope and not OfficerHierarchy.can_manage(officer_scope, target_scope):
            raise HTTPException(status_code=403, detail="forbidden: insufficient_scope")

        officer_id = current_user.get("user_id")
        if not officer_id:
            raise HTTPException(status_code=400, detail="missing_user_id")

        # --- Snapshot ค่าก่อนเปลี่ยน (สำหรับ history) ---
        prev_osm_status = getattr(profile_for_management, "osm_status", None)
        if prev_osm_status is not None:
            prev_osm_status = str(prev_osm_status)
        prev_is_active = getattr(profile_for_management, "is_active", None)
        prev_approval_status = getattr(profile_for_management, "approval_status", None)
        if prev_approval_status is not None:
            prev_approval_status = str(prev_approval_status)

        # --- Cascading: เสียชีวิต/ลาออก/พ้นสภาพ → บังคับ inactive + approved + ไม่ได้รับเงิน ---
        _retire_like_statuses = {"0", "1", "2"}
        if osm_status in _retire_like_statuses:
            is_active = False
            approval_status = ApprovalStatus.APPROVED.value
            if osm_showbbody is None:
                osm_showbbody = "5"

        status_value = OsmService._normalize_approval_status(approval_status)
        if status_value is None:
            status_value = ApprovalStatus.APPROVED.value if is_active else ApprovalStatus.PENDING.value
        audit_date = datetime.utcnow().date()
        update_payload = {
            "is_active": is_active,
            "approval_status": status_value,
            "approval_by": str(officer_id),
            "approval_date": audit_date,
        }

        # อัปเดตสถานะ อสม./เงินเยียวยา หากส่งมา
        if osm_status is not None:
            update_payload["osm_status"] = osm_status
        if osm_showbbody is not None:
            update_payload["osm_showbbody"] = osm_showbbody

        # จัดการวันลาออก: เสียชีวิต/ลาออก/พ้นสภาพ ทั้ง 3 กรณี auto-set retirement_date
        if osm_status in _retire_like_statuses:
            update_payload["retirement_date"] = retirement_date or audit_date
            if retirement_reason is not None:
                update_payload["retirement_reason"] = retirement_reason
        elif retirement_date is not None:
            update_payload["retirement_date"] = retirement_date
            if retirement_reason is not None:
                update_payload["retirement_reason"] = retirement_reason
        elif retirement_reason is not None:
            update_payload["retirement_reason"] = retirement_reason

        # ถ้ากำลังอนุมัติ (is_active=True) และ profile ยังไม่มี osm_code ให้ generate ให้
        if is_active and not getattr(profile_for_management, "osm_code", None):
            try:
                profile_dict = {
                    "province_id": getattr(profile_for_management, "province_id", None),
                    "district_id": getattr(profile_for_management, "district_id", None),
                    "subdistrict_id": getattr(profile_for_management, "subdistrict_id", None),
                    "village_no": getattr(profile_for_management, "village_no", None),
                }
                prefix = OSMProfileRepository._build_osm_code_prefix(profile_dict)
                run_no = await OSMProfileRepository._allocate_next_osm_code_run(prefix)
                update_payload["osm_code"] = f"{prefix}{run_no:06d}"
                if not getattr(profile_for_management, "village_code", None):
                    update_payload["village_code"] = prefix
            except Exception as code_err:
                logger.warning(f"Could not generate osm_code on approval for {osm_id}: {code_err}")

        # สร้างรหัสผ่านเริ่มต้น (hash จาก citizen_id) เมื่ออนุมัติและยังไม่มี password_hash
        if is_active and not getattr(profile_for_management, "password_hash", None):
            citizen_id = getattr(profile_for_management, "citizen_id", None)
            if citizen_id:
                update_payload["password_hash"] = bcrypt_hash_password(citizen_id)
                update_payload["is_first_login"] = True

        try:
            await OSMProfileRepository.update_osm(osm_id, update_payload, str(officer_id))
            refreshed = await OSMProfileRepository.find_osm_by_id(osm_id)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการอัปเดตสถานะ OSM: {str(e)}",
            )

        profile_obj = refreshed.get("osm_profile") if refreshed else None
        summary = None
        if profile_obj:
            summary = {
                "id": str(profile_obj.id),
                "citizen_id": profile_obj.citizen_id,
                "is_active": profile_obj.is_active,
                "approval_status": getattr(profile_obj, "approval_status", None),
            }

            # --- Notification ---
            # เสียชีวิต/ลาออก/พ้นสภาพ นับเป็น "retire" (พ้นสภาพ) อย่างเดียว
            if osm_status in _retire_like_statuses:
                noti_action = "retire"
            elif status_value == ApprovalStatus.APPROVED.value:
                noti_action = "approve"
            elif status_value == ApprovalStatus.REJECTED.value:
                noti_action = "reject"
            else:
                noti_action = "status_change"
            await NotificationService.create_notification(
                actor_id=str(officer_id),
                action_type=noti_action,
                target_type="osm",
                target_id=osm_id,
                target_name=f"{profile_for_management.first_name} {profile_for_management.last_name}".strip(),
                citizen_id=getattr(profile_for_management, "citizen_id", None),
                province_code=getattr(profile_for_management, "province_id", None),
                district_code=getattr(profile_for_management, "district_id", None),
                subdistrict_code=getattr(profile_for_management, "subdistrict_id", None),
            )

        # --- บันทึกประวัติการเปลี่ยนสถานะ (fire-and-forget) ---
        try:
            officer_name = current_user.get("first_name", "")
            officer_last = current_user.get("last_name", "")
            changed_by_name = f"{officer_name} {officer_last}".strip() or "เจ้าหน้าที่"

            await OsmStatusHistoryRepository.create({
                "osm_profile_id": osm_id,
                "previous_osm_status": prev_osm_status,
                "new_osm_status": osm_status if osm_status is not None else prev_osm_status,
                "previous_is_active": prev_is_active,
                "new_is_active": is_active,
                "previous_approval_status": prev_approval_status,
                "new_approval_status": status_value,
                "province_code": getattr(profile_for_management, "province_id", None),
                "district_code": getattr(profile_for_management, "district_id", None),
                "subdistrict_code": getattr(profile_for_management, "subdistrict_id", None),
                "village_no": getattr(profile_for_management, "village_no", None),
                "retirement_reason": retirement_reason,
                "remark": None,
                "changed_by": officer_id,
                "changed_by_name": changed_by_name,
            })
        except Exception:
            logger.exception("Failed to record osm status history for %s", osm_id)

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(osm_id)
        except Exception:
            pass  # best-effort session invalidation
        return {
            "status": "success",
            "data": summary,
            "message": "อัปเดตสถานะการใช้งาน OSM สำเร็จ",
        }

    @staticmethod
    def _normalize_approval_status(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        keyword = str(value).strip().lower()
        if not keyword:
            return None
        if keyword in {ApprovalStatus.APPROVED.value, "approved", "อนุมัติ"}:
            return ApprovalStatus.APPROVED.value
        if keyword in {ApprovalStatus.PENDING.value, "pending", "รออนุมัติ", "รอ"}:
            return ApprovalStatus.PENDING.value
        if keyword in {ApprovalStatus.REJECTED.value, "rejected", "ปฏิเสธ", "ไม่อนุมัติ"}:
            return ApprovalStatus.REJECTED.value
        return None

    async def delete_osm(osm_id: str, current_user: Optional[dict] = None):
        """
        ลบ OSM Profile
        """
        try:
            # Load profile before deletion for notification
            profile_record = await OSMProfileRepository.find_osm_by_id(osm_id)
            profile_obj = profile_record.get("osm_profile") if profile_record else None

            result = await OSMProfileRepository.delete_osm(osm_id)

            # --- Notification ---
            if profile_obj:
                actor_id = str(current_user.get("user_id")) if current_user else None
                await NotificationService.create_notification(
                    actor_id=actor_id,
                    action_type="delete",
                    target_type="osm",
                    target_id=osm_id,
                    target_name=f"{profile_obj.first_name} {profile_obj.last_name}".strip(),
                    citizen_id=getattr(profile_obj, "citizen_id", None),
                    province_code=getattr(profile_obj, "province_id", None),
                    district_code=getattr(profile_obj, "district_id", None),
                    subdistrict_code=getattr(profile_obj, "subdistrict_id", None),
                )

            await cache_delete_pattern("dashboard:*")
            try:
                await invalidate_user_sessions(osm_id)
            except Exception:
                pass
            return result

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการลบ OSM: {str(e)}"
            )

    async def get_osm_statistics():
        """
        ดึงสถิติข้อมูล OSM
        """
        try:
            # นับจำนวน OSM ทั้งหมด
            total_count = await OSMProfileRepository.count_all_osm()
            
            # นับจำนวนตามเพศ
            male_count = await OSMProfileRepository.count_osm_by_gender("male")
            female_count = await OSMProfileRepository.count_osm_by_gender("female")
            
            # นับจำนวนตามจังหวัด
            province_stats = await OSMProfileRepository.get_osm_stats_by_province()
            
            return {
                "total_count": total_count,
                "gender_stats": {
                    "male": male_count,
                    "female": female_count
                },
                "province_stats": province_stats
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงสถิติ OSM: {str(e)}"
            )

    # Position Confirmation Methods
    async def create_or_update_position_confirmation(osm_profile_id: str, osm_position_ids: List[str], allowance_confirmation_status: str, user_id: str):
        """
        สร้างหรืออัปเดตการยืนยันตำแหน่งและสิทธิ์เงินค่าป่วยการ (upsert)
        """
        try:
            result = await OSMProfileRepository.create_or_update_position_confirmation(
                osm_profile_id, osm_position_ids, allowance_confirmation_status, user_id
            )
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการสร้างหรืออัปเดตการยืนยันตำแหน่ง: {str(e)}"
            )

    async def get_position_confirmation_by_osm_id(osm_profile_id: str):
        """
        ดึงการยืนยันตำแหน่งของ OSM Profile
        """
        try:
            result = await OSMProfileRepository.get_position_confirmation_by_osm_id(osm_profile_id)
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงการยืนยันตำแหน่ง: {str(e)}"
            )

    async def delete_position_confirmation(confirmation_id: str, user_id: str):
        """
        ลบการยืนยันตำแหน่ง (Soft Delete)
        """
        try:
            result = await OSMProfileRepository.delete_position_confirmation(confirmation_id, user_id)
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการลบการยืนยันตำแหน่ง: {str(e)}"
            )

    async def get_all_osm_positions():
        """
        ดึงตำแหน่ง OSM ทั้งหมด
        """
        try:
            result = await OSMProfileRepository.get_all_osm_positions()
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงตำแหน่ง OSM: {str(e)}"
            )