from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.models.people_model import PeopleUser
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class UserSyncService:
    """บริการ sync ข้อมูล user จาก mobile app → people_user table."""

    # ------------------------------------------------------------------ #
    #  Field mapping: frontend field name → PeopleUser model field name  #
    # ------------------------------------------------------------------ #
    _FIELD_MAP: Dict[str, str] = {
        "province_id": "province_code",
        "district_id": "district_code",
        "sub_district_id": "subdistrict_code",
        "sub_district_name": "subdistrict_name",
        "profile_image_url": "profile_image",
        "reason": "registration_reason",
    }

    # Fields ที่ frontend ส่งมาแต่ไม่มีใน PeopleUser → ข้าม
    _SKIP_FIELDS: set = {
        "username",
        "thai_id",
        "full_name",
        "is_approved",
        "is_superuser",
    }

    @staticmethod
    def _normalize(value: Any) -> Any:
        """Normalize ค่าว่างเป็น None."""
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        return value

    @staticmethod
    def _map_frontend_to_model(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        แปลง field names จาก frontend format → PeopleUser model fields.

        frontend ส่ง: province_id, district_id, sub_district_id, profile_image_url
        backend ต้องการ: province_code, district_code, subdistrict_code, profile_image
        """
        mapped: Dict[str, Any] = {}

        for key, value in data.items():
            # ข้าม fields ที่ไม่มีใน model
            if key in UserSyncService._SKIP_FIELDS:
                continue

            # map field name ถ้าต่างกัน
            model_field = UserSyncService._FIELD_MAP.get(key, key)

            # ข้าม fields ที่ map แล้วยังไม่อยู่ใน model
            if model_field not in PeopleUser._meta.fields_map:
                logger.debug("Skipping unknown field: %s → %s", key, model_field)
                continue

            mapped[model_field] = UserSyncService._normalize(value)

        # สร้าง first_name / last_name จาก full_name ถ้าไม่มี
            if "full_name" in data and data["full_name"]:
                parts = data["full_name"].strip().split(maxsplit=1)
                if not mapped.get("first_name") and len(parts) >= 1:
                    mapped["first_name"] = UserSyncService._normalize(parts[0])
                if not mapped.get("last_name") and len(parts) >= 2:
                    mapped["last_name"] = UserSyncService._normalize(parts[1])

        return mapped

    @staticmethod
    def _serialize_user(user: PeopleUser) -> Dict[str, Any]:
        """แปลง PeopleUser object → dict สำหรับ response."""
        return {
            "id": str(user.id),
            "citizen_id": user.citizen_id,
            "prefix": user.prefix,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "gender": user.gender,
            "phone_number": user.phone_number,
            "email": user.email,
            "line_id": user.line_id,
            "school": user.school,
            "organization": user.organization,
            "profile_image": user.profile_image,
            "province_code": user.province_code,
            "province_name": user.province_name,
            "district_code": user.district_code,
            "district_name": user.district_name,
            "subdistrict_code": user.subdistrict_code,
            "subdistrict_name": user.subdistrict_name,
            "is_active": bool(user.is_active),
            "created_at": str(user.created_at) if user.created_at else None,
            "updated_at": str(user.updated_at) if user.updated_at else None,
        }

    @staticmethod
    async def find_by_uuid(uuid: str) -> Optional[PeopleUser]:
        """ค้นหา PeopleUser จาก id (UUID)."""
        try:
            return await PeopleUser.filter(id=uuid).first()
        except Exception as exc:
            logger.error("Failed to find PeopleUser by uuid=%s", uuid, exc_info=exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"database_error: {str(exc)}",
            ) from exc

    @staticmethod
    async def sync_update(uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update ข้อมูล PeopleUser จาก frontend sync payload.

        Returns 404 ถ้าไม่เจอ user (ให้ frontend fallback ไป POST create).
        """
        user = await UserSyncService.find_by_uuid(uuid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user_not_found",
            )

        mapped = UserSyncService._map_frontend_to_model(data)

        for field, value in mapped.items():
            if hasattr(user, field):
                setattr(user, field, value)

        await user.save()

        logger.info("Synced update for PeopleUser uuid=%s", uuid)
        return {
            "success": True,
            "message": "user_synced",
            "data": UserSyncService._serialize_user(user),
        }

    @staticmethod
    async def sync_create(uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        สร้าง PeopleUser ใหม่จาก frontend sync payload.

        ใช้ citizen_id จาก username หรือ thai_id เป็น required field.
        """
        from datetime import datetime

        citizen_id = data.get("username") or data.get("thai_id") or ""
        citizen_id = citizen_id.strip() if isinstance(citizen_id, str) else ""

        if not citizen_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="citizen_id_required",
            )

        # ตรวจซ้ำ
        existing = await PeopleUser.filter(citizen_id=citizen_id).first()
        if existing:
            logger.warning(
                "Sync create: citizen_id=%s already exists (id=%s), updating instead",
                citizen_id,
                existing.id,
            )
            return await UserSyncService.sync_update(str(existing.id), data)

        mapped = UserSyncService._map_frontend_to_model(data)
        mapped["citizen_id"] = citizen_id

        # Validate required fields
        if not mapped.get("first_name"):
            mapped["first_name"] = "Unknown"
        if not mapped.get("last_name"):
            mapped["last_name"] = ""

        # Default is_active
        if mapped.get("is_active") is None:
            mapped["is_active"] = True

        try:
            user = await PeopleUser.create(
                id=UUID(uuid),
                **mapped,
            )
        except Exception as exc:
            logger.error("Failed to create PeopleUser from sync: %s", exc, exc_info=exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"create_failed: {str(exc)}",
            ) from exc

        logger.info("Synced create PeopleUser uuid=%s citizen_id=%s", uuid, citizen_id)
        return {
            "success": True,
            "message": "user_created",
            "data": UserSyncService._serialize_user(user),
        }
