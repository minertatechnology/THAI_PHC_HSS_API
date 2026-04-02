from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Dict, List

from fastapi import HTTPException, status

from app.api.v1.schemas.people_schema import PeopleCreateSchema, PeopleUpdateSchema
from app.models.people_model import PeopleUser
from app.repositories.people_user_repository import PeopleUserRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.services.oauth2_service import bcrypt_hash_password
from app.services.officer_snapshot_helper import build_officer_snapshot


class PeopleService:
    """Business logic for managing People accounts."""

    @staticmethod
    def _normalize_optional_text(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        return value

    @staticmethod
    def _serialize_user(user: PeopleUser) -> Dict[str, Any]:
        return {
            "id": str(user.id),
            "citizen_id": user.citizen_id,
            "yuwa_osm_code": user.yuwa_osm_code,
            "prefix": getattr(user, "prefix", None),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "gender": user.gender,
            "phone_number": user.phone_number,
            "email": user.email,
            "line_id": getattr(user, "line_id", None),
            "school": getattr(user, "school", None),
            "organization": getattr(user, "organization", None),
            "profile_image": getattr(user, "profile_image", None),
            "registration_reason": getattr(user, "registration_reason", None),
            "photo_1inch": getattr(user, "photo_1inch", None),
            "attachments": getattr(user, "attachments", None),
            "province_code": user.province_code,
            "province_name": user.province_name,
            "district_code": user.district_code,
            "district_name": user.district_name,
            "subdistrict_code": user.subdistrict_code,
            "subdistrict_name": user.subdistrict_name,
            "birthday": user.birthday,
            "is_active": bool(user.is_active),
            "is_first_login": bool(user.is_first_login),
            "is_transferred": bool(getattr(user, "is_transferred", False)),
            "transferred_at": str(user.transferred_at) if user.transferred_at else None,
            "transferred_by": str(user.transferred_by) if user.transferred_by else None,
            "transferred_by_name": None,
            "yuwa_osm_id": str(user.yuwa_osm_id) if user.yuwa_osm_id else None,
            "created_at": str(user.created_at) if user.created_at else None,
            "updated_at": str(user.updated_at) if user.updated_at else None,
        }

    @staticmethod
    async def _attach_transfer_actor(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return payload
        snapshot = await build_officer_snapshot(payload.get("transferred_by"))
        payload["transferred_by_name"] = snapshot.get("name") if snapshot else None
        return payload

    @staticmethod
    async def _hydrate_transfer_from_yuwa(user: PeopleUser) -> None:
        if getattr(user, "is_transferred", False) and getattr(user, "yuwa_osm_id", None):
            return
        yuwa = None
        if getattr(user, "id", None):
            yuwa = await YuwaOSMUserRepository.get_user_by_source_people_id(str(user.id))
        if not yuwa and getattr(user, "citizen_id", None):
            yuwa = await YuwaOSMUserRepository.get_user_by_citizen_id(user.citizen_id)
        if not yuwa:
            return
        user.is_transferred = True
        user.yuwa_osm_id = yuwa.id
        user.yuwa_osm_code = getattr(yuwa, "yuwa_osm_code", None) or user.yuwa_osm_code
        user.transferred_at = getattr(yuwa, "transferred_at", None)
        user.transferred_by = getattr(yuwa, "transferred_by", None)

    @staticmethod
    def _get_thai_year_prefix(now: datetime) -> str:
        thai_year = now.year + 543
        return f"{thai_year % 100:02d}"

    @staticmethod
    async def _generate_yuwa_osm_code() -> str:
        prefix = PeopleService._get_thai_year_prefix(datetime.utcnow())
        latest_people = await PeopleUserRepository.get_latest_yuwa_osm_code(prefix)
        latest_yuwa = await YuwaOSMUserRepository.get_latest_yuwa_osm_code(prefix)

        def _to_int(value: str | None) -> int:
            if not value:
                return 0
            try:
                return int(value)
            except ValueError:
                return 0

        max_code_value = max(_to_int(latest_people), _to_int(latest_yuwa))
        next_running = (max_code_value % 10**7) + 1 if max_code_value else 1

        for _ in range(20):
            code = f"{prefix}{next_running:07d}"
            if not await PeopleUserRepository.exists_by_yuwa_osm_code(code) and not await YuwaOSMUserRepository.exists_by_yuwa_osm_code(code):
                return code
            next_running += 1

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="yuwa_osm_code_generation_failed")

    @staticmethod
    async def register_user(payload: PeopleCreateSchema, actor_id: str | None = None):
        exists = await PeopleUserRepository.exists_by_citizen_id(payload.citizen_id)
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="citizen_id_exists")

        if await YuwaOSMUserRepository.exists_by_citizen_id(payload.citizen_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="citizen_id_already_in_yuwa_osm")

        password_hash = bcrypt_hash_password(payload.password)
        yuwa_osm_code = await PeopleService._generate_yuwa_osm_code()

        user = await PeopleUser.create(
            citizen_id=payload.citizen_id,
            prefix=PeopleService._normalize_optional_text(payload.prefix),
            first_name=payload.first_name,
            last_name=payload.last_name,
            gender=PeopleService._normalize_optional_text(payload.gender),
            phone_number=PeopleService._normalize_optional_text(payload.phone_number),
            email=PeopleService._normalize_optional_text(payload.email),
            line_id=PeopleService._normalize_optional_text(payload.line_id),
            school=PeopleService._normalize_optional_text(payload.school),
            organization=PeopleService._normalize_optional_text(payload.organization),
            profile_image=PeopleService._normalize_optional_text(payload.profile_image),
            registration_reason=PeopleService._normalize_optional_text(getattr(payload, "registration_reason", None)),
            photo_1inch=PeopleService._normalize_optional_text(getattr(payload, "photo_1inch", None)),
            attachments=getattr(payload, "attachments", None),
            province_code=PeopleService._normalize_optional_text(payload.province_code),
            province_name=PeopleService._normalize_optional_text(payload.province_name),
            district_code=PeopleService._normalize_optional_text(payload.district_code),
            district_name=PeopleService._normalize_optional_text(payload.district_name),
            subdistrict_code=PeopleService._normalize_optional_text(payload.subdistrict_code),
            subdistrict_name=PeopleService._normalize_optional_text(payload.subdistrict_name),
            birthday=payload.birthday,
            yuwa_osm_code=yuwa_osm_code,
            password_hash=password_hash,
            is_active=True,
            is_first_login=False,
        )

        return {
            "success": True,
            "message": "People user registered",
            "data": await PeopleService._attach_transfer_actor(PeopleService._serialize_user(user)),
        }

    @staticmethod
    async def get_user(user_id: str, current_user: dict) -> Dict[str, Any]:
        user = None
        try:
            UUID(str(user_id))
            user = await PeopleUserRepository.get_user_for_management(user_id)
        except (ValueError, TypeError):
            user = None

        if not user:
            if user_id and user_id.isdigit() and len(user_id) == 13:
                user = await PeopleUserRepository.get_user_by_citizen_id(user_id)
            else:
                user = await PeopleUserRepository.get_user_by_yuwa_osm_code(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="people_user_not_found")
        await PeopleService._hydrate_transfer_from_yuwa(user)
        payload = PeopleService._serialize_user(user)
        payload = await PeopleService._attach_transfer_actor(payload)
        return {
            "success": True,
            "message": "People user fetched",
            "data": payload,
        }

    @staticmethod
    async def update_user(user_id: str, payload: PeopleUpdateSchema, current_user: dict) -> Dict[str, Any]:
        user = await PeopleUserRepository.get_user_for_management(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="people_user_not_found")

        updates = payload.dict(exclude_unset=True)
        for field, value in updates.items():
            if isinstance(value, str):
                value = PeopleService._normalize_optional_text(value)
            setattr(user, field, value)
        user.updated_at = datetime.utcnow()
        await user.save()

        payload = PeopleService._serialize_user(user)
        payload = await PeopleService._attach_transfer_actor(payload)
        return {
            "success": True,
            "message": "People user updated",
            "data": payload,
        }

    @staticmethod
    async def get_people_by_ids(user_ids: List[str], current_user: dict):
        """Batch fetch People users by IDs (UUID or citizen_id)."""
        if not user_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids_required")

        unique_ids = list(dict.fromkeys(user_ids))
        items: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        for user_id in unique_ids:
            try:
                result = await PeopleService.get_user(user_id, current_user)
                items.append(result.get("data"))
            except HTTPException as exc:
                errors.append({"id": user_id, "error": str(exc.detail)})

        return {
            "status": "success",
            "data": items,
            "errors": errors,
            "message": "ดึงข้อมูล People Users สำเร็จ",
        }
