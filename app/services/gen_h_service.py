from __future__ import annotations

import logging
import re
from typing import Optional, List
from uuid import UUID, uuid4

import bcrypt as _bcrypt

from fastapi import HTTPException, UploadFile
from tortoise.transactions import in_transaction

from app.api.v1.schemas.gen_h_schema import (
    GenHCreateSchema,
    GenHResponseSchema,
    GenHTransferToPeopleRequest,
    GenHUpdateSchema,
    GenHUpgradeToYuwaOSMRequest,
)
from app.models.gen_h_model import GenHUser
from app.models.people_model import PeopleUser
from app.models.yuwa_osm_model import YuwaOSMUser
from app.models.enum_models import ApprovalStatus
from app.repositories.gen_h_user_repository import GenHUserRepository
from app.repositories.people_user_repository import PeopleUserRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.services.officer_service import OfficerService
from app.services.profile_image_service import ProfileImageService

logger = logging.getLogger(__name__)


class GenHService:

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _clean_str(v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        # remove zero-width spaces
        s = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", s)
        return s or None

    @staticmethod
    def _build_public_url(relative_path: str | None) -> str | None:
        """Convert a relative image path to a full URL if it looks like a local path."""
        if not relative_path:
            return None
        if relative_path.startswith("http://") or relative_path.startswith("https://"):
            return relative_path
        from app.configs.config import settings
        base = settings.PUBLIC_BASE_URL
        if not base:
            return relative_path
        base = base.rstrip("/")
        return f"{base}/{relative_path}"

    @staticmethod
    def _serialize_user(user: GenHUser) -> dict:
        data = GenHResponseSchema.model_validate(user).model_dump(mode="json")
        _url = GenHService._build_public_url
        if data.get("profile_image_url"):
            data["profile_image_url"] = _url(data["profile_image_url"])
        if data.get("photo_1inch"):
            data["photo_1inch"] = _url(data["photo_1inch"])
        if data.get("member_card_url"):
            data["member_card_url"] = _url(data["member_card_url"])
        return data

    @staticmethod
    async def _generate_gen_h_code() -> str:
        """Generate next Gen H code atomically using osm_code_counters table.

        Format: {2-digit-thai-year}{6-digit-running-number}
        Example: 690001234 (year 2569, number 1234)
        Counter key: GH{year2} e.g. 'GH69'
        """
        from datetime import datetime
        from tortoise import connections

        thai_year = datetime.now().year + 543
        year2 = str(thai_year)[-2:]  # e.g. "69"
        counter_key = f"GH{year2}"

        db = connections.get("default")
        # Upsert + increment atomically — returns the new last_number
        rows = await db.execute_query_dict(
            """
            INSERT INTO osm_code_counters (prefix, last_number, updated_at)
            VALUES ($1, 1, NOW())
            ON CONFLICT (prefix) DO UPDATE
                SET last_number = osm_code_counters.last_number + 1,
                    updated_at  = NOW()
            RETURNING last_number
            """,
            [counter_key],
        )
        next_num = rows[0]["last_number"]
        return f"{year2}{next_num:06d}"

    @staticmethod
    async def _check_scope_for_gen_h(gen_h_user, current_user: Optional[dict]) -> None:
        """Verify the officer has jurisdiction over the gen_h user's area."""
        if not current_user:
            return
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(
            current_user, require_active=True,
        )
        if viewer_scope is None:
            raise HTTPException(status_code=403, detail="forbidden")
        target_scope, _ctx = await OfficerService._resolve_gen_h_management_context(gen_h_user)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope)

    @staticmethod
    async def _check_scope_for_payload(payload_province_code: Optional[str], current_user: Optional[dict]) -> None:
        """Verify the officer has jurisdiction over the target province (for register)."""
        if not current_user or not payload_province_code:
            return
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(
            current_user, require_active=True,
        )
        if viewer_scope is None:
            raise HTTPException(status_code=403, detail="forbidden")

        # Build a minimal scope from payload province
        from app.models.geography_model import Province, District
        province = await Province.filter(province_code=payload_province_code).first()
        health_area_id = OfficerService._normalize_code(getattr(province, "health_area_id", None)) if province else None
        region_code = OfficerService._normalize_code(getattr(province, "region_id", None)) if province else None
        target_scope = OfficerService._build_scope_from_geography(
            region_code=region_code,
            health_area_id=health_area_id,
            province_id=payload_province_code,
        )
        OfficerService._ensure_scope_permission(viewer_scope, target_scope)

    # ── CRUD ─────────────────────────────────────────────────────────────

    @staticmethod
    async def register(payload: GenHCreateSchema, current_user: Optional[dict] = None, profile_image: Optional[UploadFile] = None) -> dict:
        """Register a new Gen H user."""
        # Scope check: officer can only register in their jurisdiction
        await GenHService._check_scope_for_payload(
            GenHService._clean_str(payload.province_code), current_user,
        )

        code = GenHService._clean_str(payload.gen_h_code) if payload.gen_h_code else None
        if code:
            if await GenHUserRepository.exists_by_gen_h_code(code):
                raise HTTPException(status_code=409, detail=f"Gen H code {code} already exists")
        else:
            code = await GenHService._generate_gen_h_code()

        # self_register: password required, never fallback to gen_h_code
        # (gen_h_code default password is for migration data only, set directly in DB)
        password_hash = _bcrypt.hashpw(payload.password.encode(), _bcrypt.gensalt()).decode()
        is_first_login = False

        # Upload profile image if provided
        profile_image_url = GenHService._clean_str(payload.profile_image_url)
        if profile_image is not None and getattr(profile_image, "filename", None):
            stored_path = await ProfileImageService.upload_profile_image(file=profile_image, context="gen_h")
            profile_image_url = stored_path

        user = await GenHUserRepository.create_user(
            id=uuid4(),
            gen_h_code=code,
            citizen_id=GenHService._clean_str(payload.citizen_id),
            prefix=GenHService._clean_str(payload.prefix),
            first_name=GenHService._clean_str(payload.first_name) or "ไม่ระบุชื่อ",
            last_name=GenHService._clean_str(payload.last_name) or "ไม่ระบุนามสกุล",
            gender=GenHService._clean_str(payload.gender),
            birthday=payload.birthday,
            phone_number=GenHService._clean_str(payload.phone_number),
            email=GenHService._clean_str(payload.email),
            line_id=GenHService._clean_str(payload.line_id),
            school=GenHService._clean_str(payload.school),
            organization=GenHService._clean_str(payload.organization),
            registration_reason=GenHService._clean_str(payload.registration_reason),
            province_code=GenHService._clean_str(payload.province_code),
            province_name=GenHService._clean_str(payload.province_name),
            district_code=GenHService._clean_str(payload.district_code),
            district_name=GenHService._clean_str(payload.district_name),
            subdistrict_code=GenHService._clean_str(payload.subdistrict_code),
            subdistrict_name=GenHService._clean_str(payload.subdistrict_name),
            profile_image_url=profile_image_url,
            photo_1inch=GenHService._clean_str(payload.photo_1inch),
            member_card_url=GenHService._clean_str(payload.member_card_url),
            attachments=payload.attachments,
            password_hash=password_hash,
            is_first_login=is_first_login,
            source_type="self_register",
        )
        return GenHService._serialize_user(user)

    @staticmethod
    async def get_user(user_id: str) -> dict:
        """Get a Gen H user by UUID, citizen_id or gen_h_code."""
        user = None
        is_uuid = False

        try:
            uid = UUID(user_id)
            is_uuid = True
            user = await GenHUserRepository.get_by_id(uid)
        except (ValueError, AttributeError):
            pass

        if user is None:
            if user_id and user_id.isdigit() and len(user_id) == 13:
                user = await GenHUserRepository.get_by_citizen_id(user_id)

        if user is None and not is_uuid:
            user = await GenHUserRepository.get_by_gen_h_code(user_id)

        if user is None:
            raise HTTPException(status_code=404, detail="Gen H user not found")

        return GenHService._serialize_user(user)

    @staticmethod
    async def update_user(user_id: str, payload: GenHUpdateSchema, current_user: Optional[dict] = None) -> dict:
        """Update a Gen H user."""
        user = None
        try:
            uid = UUID(user_id)
            user = await GenHUserRepository.get_by_id(uid)
        except (ValueError, AttributeError):
            pass
        if user is None and len(user_id) <= 20:
            user = await GenHUserRepository.get_by_gen_h_code(user_id)

        if user is None:
            raise HTTPException(status_code=404, detail="Gen H user not found")

        # Scope check: officer can only update users in their jurisdiction
        # Skip scope check if gen_h user is updating their own profile
        if not (current_user and current_user.get("user_type") == "gen_h" and str(current_user.get("user_id", "")) == user_id):
            await GenHService._check_scope_for_gen_h(user, current_user)

        updates = payload.model_dump(exclude_unset=True)
        # clean string fields
        for k, v in updates.items():
            if isinstance(v, str):
                updates[k] = GenHService._clean_str(v)

        user = await GenHUserRepository.update_user(user, **updates)
        return GenHService._serialize_user(user)

    @staticmethod
    async def delete_user(user_id: UUID, current_user: Optional[dict] = None) -> None:
        user = await GenHUserRepository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Gen H user not found")
        # Scope check: officer can only delete users in their jurisdiction
        await GenHService._check_scope_for_gen_h(user, current_user)
        await GenHUserRepository.delete_user(user)

    @staticmethod
    async def list_users(params: dict) -> dict:
        users, total = await GenHUserRepository.list_users(**params)
        page = params.get("page", 1)
        per_page = params.get("per_page", 20)
        return {
            "items": [GenHService._serialize_user(u) for u in users],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    @staticmethod
    async def summary(province_code: Optional[str] = None) -> dict:
        return await GenHUserRepository.summary(province_code=province_code)

    # ── Transfer ──────────────────────────────────────────────────────────

    @staticmethod
    async def transfer_to_people(
        gen_h_id: str,
        payload: GenHTransferToPeopleRequest,
        actor_id: Optional[str] = None,
        current_user: Optional[dict] = None,
    ) -> dict:
        """Transfer a Gen H user to people_user.

        Steps:
        1. Validate gen_h user exists and is active
        2. Verify officer scope covers the gen_h user's province
        3. Check citizen_id not already in people_user
        4. Create people_user with data from gen_h + citizen_id
        5. Deactivate gen_h: is_active=False, clear password_hash
        6. Link gen_h.people_user_id to the new people_user
        """
        from datetime import datetime

        # Resolve gen_h user — ลอง UUID ก่อน, fallback เป็น gen_h_code
        gen_h = None
        try:
            uid = UUID(gen_h_id)
            gen_h = await GenHUserRepository.get_by_id(uid)
        except (ValueError, AttributeError):
            pass
        if gen_h is None and len(gen_h_id) <= 20:
            gen_h = await GenHUserRepository.get_by_gen_h_code(gen_h_id)
        if gen_h is None:
            raise HTTPException(status_code=404, detail="gen_h_user_not_found")
        if not gen_h.is_active:
            raise HTTPException(status_code=400, detail="gen_h_user_already_inactive")
        if gen_h.people_user_id:
            raise HTTPException(status_code=400, detail="gen_h_already_transferred")

        # Scope check: officer must have jurisdiction over this gen_h user's area
        if current_user:
            _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(
                current_user, require_active=True,
            )
            if viewer_scope is None:
                raise HTTPException(status_code=403, detail="forbidden")
            target_scope, _ctx = await OfficerService._resolve_gen_h_management_context(gen_h)
            OfficerService._ensure_scope_permission(viewer_scope, target_scope)

        citizen_id = payload.citizen_id.strip()
        if await PeopleUserRepository.exists_by_citizen_id(citizen_id):
            raise HTTPException(status_code=409, detail="citizen_id_already_exists_in_people")

        now = datetime.utcnow()
        birthday = None
        if payload.birthday:
            from datetime import date as date_type
            try:
                birthday = date_type.fromisoformat(payload.birthday)
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid_birthday_format")

        async with in_transaction():
            # Create people_user
            people = await PeopleUser.create(
                id=uuid4(),
                citizen_id=citizen_id,
                prefix=gen_h.prefix,
                first_name=gen_h.first_name,
                last_name=gen_h.last_name,
                gender=gen_h.gender,
                phone_number=gen_h.phone_number,
                email=gen_h.email,
                line_id=gen_h.line_id,
                school=gen_h.school,
                organization=payload.organization,
                registration_reason=payload.registration_reason,
                province_code=gen_h.province_code,
                province_name=gen_h.province_name,
                district_code=gen_h.district_code,
                district_name=gen_h.district_name,
                subdistrict_code=gen_h.subdistrict_code,
                subdistrict_name=gen_h.subdistrict_name,
                profile_image=gen_h.profile_image_url,
                birthday=birthday,
                password_hash=None,  # force new password setup
                is_first_login=True,
                is_active=True,
            )

            # Deactivate gen_h + link
            gen_h.is_active = False
            gen_h.password_hash = None  # invalidate old login
            gen_h.people_user_id = people.id
            gen_h.transferred_at = now
            await gen_h.save()

        return {
            "success": True,
            "gen_h_id": str(gen_h.id),
            "gen_h_code": gen_h.gen_h_code,
            "people_user_id": str(people.id),
            "citizen_id": citizen_id,
            "message": "transferred_to_people_user",
        }

    # ── Upgrade to YuwaOSM (self-service migration) ───────────────────────

    @staticmethod
    async def upgrade_to_yuwa_osm(
        gen_h_id: str,
        payload: GenHUpgradeToYuwaOSMRequest,
        current_user: dict,
    ) -> dict:
        """Self-service: gen_h user กรอก citizen_id เพื่อ upgrade เป็น yuwa_osm โดยตรง.

        Steps:
        1. ตรวจสอบ gen_h user มีอยู่จริง และ is_active
        2. ตรวจสอบว่า current_user เป็นเจ้าของ gen_h record นั้น
        3. ตรวจสอบ citizen_id ไม่ซ้ำใน yuwa_osm หรือ people
        4. สร้าง YuwaOSMUser (source_type='migration', approval_status=APPROVED)
        5. ปิด gen_h (is_active=False) + link yuwa_osm_user_id
        6. Return yuwa_osm data พร้อม new session info
        """
        from datetime import datetime as dt

        # Resolve gen_h user — ลอง UUID ก่อน, fallback เป็น gen_h_code
        gen_h = None
        try:
            uid = UUID(gen_h_id)
            gen_h = await GenHUserRepository.get_by_id(uid)
        except (ValueError, AttributeError):
            pass
        if gen_h is None and len(gen_h_id) <= 20:
            gen_h = await GenHUserRepository.get_by_gen_h_code(gen_h_id)
        if gen_h is None:
            raise HTTPException(status_code=404, detail="gen_h_user_not_found")
        if not gen_h.is_active:
            raise HTTPException(status_code=400, detail="gen_h_user_already_inactive")
        if gen_h.yuwa_osm_user_id:
            raise HTTPException(status_code=400, detail="gen_h_already_upgraded_to_yuwa_osm")

        # ตรวจสอบ: gen_h user ต้องเป็น self (ไม่ใช่ officer ทำแทน)
        caller_type = current_user.get("user_type")
        caller_id = str(current_user.get("user_id", ""))
        if caller_type == "gen_h" and caller_id != str(gen_h.id):
            raise HTTPException(status_code=403, detail="forbidden: can only upgrade own account")

        citizen_id = payload.citizen_id.strip()

        # ตรวจ citizen_id ไม่ซ้ำ
        if await YuwaOSMUserRepository.exists_by_citizen_id(citizen_id):
            raise HTTPException(status_code=409, detail="citizen_id_already_exists_in_yuwa_osm")
        if await PeopleUserRepository.exists_by_citizen_id(citizen_id):
            raise HTTPException(status_code=409, detail="citizen_id_already_exists_in_people")

        birthday = None
        if payload.birthday:
            from datetime import date as date_type
            try:
                birthday = date_type.fromisoformat(payload.birthday)
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid_birthday_format")

        # Generate yuwa_osm_code ด้วย atomic counter
        from app.services.people_service import PeopleService
        yuwa_osm_code = await PeopleService._generate_yuwa_osm_code()

        # phone_number เป็น UNIQUE ใน yuwa_osm → ต้องตรวจก่อน
        # ถ้า payload ส่ง phone มาใหม่ ใช้ตัวใหม่, ไม่งั้นใช้จาก gen_h
        phone_number = GenHService._clean_str(payload.phone_number) or gen_h.phone_number
        if phone_number and await YuwaOSMUserRepository.exists_by_phone(phone_number):
            # phone ซ้ำ → ไม่บังคับ error, เซ็ตเป็น null ให้ user update ทีหลัง
            phone_number = None

        now = dt.utcnow()

        async with in_transaction():
            yuwa = await YuwaOSMUser.create(
                id=uuid4(),
                prefix=gen_h.prefix,
                first_name=gen_h.first_name,
                last_name=gen_h.last_name,
                citizen_id=citizen_id,
                gender=gen_h.gender,
                phone_number=phone_number,
                email=gen_h.email,
                line_id=gen_h.line_id,
                school=gen_h.school,
                organization=GenHService._clean_str(payload.organization),
                registration_reason=GenHService._clean_str(payload.registration_reason),
                province_code=gen_h.province_code,
                province_name=gen_h.province_name,
                district_code=gen_h.district_code,
                district_name=gen_h.district_name,
                subdistrict_code=gen_h.subdistrict_code,
                subdistrict_name=gen_h.subdistrict_name,
                profile_image=gen_h.profile_image_url,
                birthday=birthday,
                yuwa_osm_code=yuwa_osm_code,
                password_hash=gen_h.password_hash,  # ใช้ password เดิม ไม่ต้อง set ใหม่
                is_first_login=False,
                is_active=True,
                approval_status=ApprovalStatus.APPROVED,
                approved_at=now,
                # Gen-H link
                gen_h_code=gen_h.gen_h_code,
                gen_h_id=gen_h.id,
                source_type="migration",
                transferred_at=now,
            )

            # Deactivate gen_h + link
            gen_h.is_active = False
            gen_h.password_hash = None  # invalidate gen_h login
            gen_h.yuwa_osm_user_id = yuwa.id
            gen_h.transferred_at = now
            await gen_h.save()

        return {
            "success": True,
            "message": "upgraded_to_yuwa_osm",
            "gen_h_id": str(gen_h.id),
            "gen_h_code": gen_h.gen_h_code,
            "yuwa_osm_user_id": str(yuwa.id),
            "yuwa_osm_code": yuwa_osm_code,
            "citizen_id": citizen_id,
            "phone_number": yuwa.phone_number,
            # phone_number=None หมายความว่า phone เดิมซ้ำกับ yuwa_osm อื่น → ต้องให้ user กรอกใหม่
            "phone_number_conflict": yuwa.phone_number is None and bool(gen_h.phone_number),
            # Frontend ใช้ข้อมูลนี้เพื่อ re-login เป็น yuwa_osm
            "user_type": "yuwa_osm",
        }

    @staticmethod
    async def get_gen_h_by_ids(user_ids: List[str]):
        """Batch fetch Gen H users by IDs (UUID or gen_h_code)."""
        if not user_ids:
            raise HTTPException(status_code=400, detail="ids_required")

        unique_ids = list(dict.fromkeys(user_ids))
        items: List[dict] = []
        errors: List[dict] = []

        for user_id in unique_ids:
            try:
                data = await GenHService.get_user(user_id)
                items.append(data)
            except HTTPException as exc:
                errors.append({"id": user_id, "error": str(exc.detail)})

        return {"data": items, "errors": errors}
