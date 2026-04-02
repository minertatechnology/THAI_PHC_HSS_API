from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from app.models.geography_model import Province
from app.models.notification_model import OsmNotification
from app.models.officer_model import OfficerProfile
from app.models.osm_model import OSMProfile
from app.repositories.notification_repository import NotificationRepository
from app.utils.officer_hierarchy import OfficerScope

logger = logging.getLogger(__name__)

_ACTION_LABELS: Dict[str, str] = {
    "create": "สร้างข้อมูล",
    "update": "แก้ไขข้อมูล",
    "delete": "ลบข้อมูล",
    "approve": "อนุมัติ",
    "reject": "ปฏิเสธ",
    "retire": "ให้พ้นสภาพ",
    "status_change": "เปลี่ยนสถานะ",
    "register": "ลงทะเบียน",
    "re_register": "ลงทะเบียนใหม่ (หลังพ้นสภาพ)",
}

_TARGET_TYPE_LABELS: Dict[str, str] = {
    "osm": "อสม.",
    "yuwa_osm": "อสม.น้อย",
    "officer": "เจ้าหน้าที่",
}


class NotificationService:

    @staticmethod
    async def _resolve_actor_name(actor_id: Optional[str]) -> str:
        if not actor_id:
            return "ระบบ"
        try:
            officer = await OfficerProfile.filter(id=actor_id).only(
                "first_name", "last_name"
            ).first()
            if officer:
                return f"{officer.first_name} {officer.last_name}".strip()
        except Exception:
            pass
        return "เจ้าหน้าที่"

    @staticmethod
    async def _resolve_geo_codes(
        province_code: Optional[str],
        district_code: Optional[str],
        subdistrict_code: Optional[str],
    ) -> Dict[str, Optional[str]]:
        health_area_id = None
        region_code = None
        if province_code:
            try:
                province = await Province.filter(
                    province_code=province_code
                ).only("health_area_id", "region_id").first()
                if province:
                    health_area_id = getattr(province, "health_area_id", None)
                    region_code = getattr(province, "region_id", None)
            except Exception:
                pass
        return {
            "province_code": province_code,
            "district_code": district_code,
            "subdistrict_code": subdistrict_code,
            "health_area_id": health_area_id,
            "region_code": region_code,
        }

    @staticmethod
    def _build_message(
        actor_name: str,
        action_type: str,
        target_type: str,
        target_name: str,
    ) -> str:
        action_label = _ACTION_LABELS.get(action_type, action_type)
        type_label = _TARGET_TYPE_LABELS.get(target_type, target_type)
        return f"{actor_name} {action_label} {type_label} {target_name}"

    @staticmethod
    async def create_notification(
        *,
        actor_id: Optional[str],
        action_type: str,
        target_type: str,
        target_id: str,
        target_name: str,
        citizen_id: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
    ) -> None:
        """Fire-and-forget notification creation. Errors are logged, never raised."""
        try:
            actor_name = await NotificationService._resolve_actor_name(actor_id)
            geo = await NotificationService._resolve_geo_codes(
                province_code, district_code, subdistrict_code
            )
            message = NotificationService._build_message(
                actor_name, action_type, target_type, target_name
            )

            await NotificationRepository.create({
                "actor_id": UUID(str(actor_id)) if actor_id else UUID(int=0),
                "actor_name": actor_name,
                "action_type": action_type,
                "target_type": target_type,
                "target_id": UUID(str(target_id)),
                "target_name": target_name,
                "citizen_id": citizen_id,
                "message": message,
                **geo,
            })
        except Exception:
            logger.exception(
                "Failed to create notification for %s %s/%s",
                action_type, target_type, target_id,
            )

    @staticmethod
    async def create_notification_from_osm_profile(
        *,
        actor_id: Optional[str],
        action_type: str,
        osm_profile: OSMProfile,
        target_type: str = "osm",
    ) -> None:
        target_name = f"{osm_profile.first_name} {osm_profile.last_name}".strip()
        await NotificationService.create_notification(
            actor_id=actor_id,
            action_type=action_type,
            target_type=target_type,
            target_id=str(osm_profile.id),
            target_name=target_name,
            citizen_id=getattr(osm_profile, "citizen_id", None),
            province_code=getattr(osm_profile, "province_id", None),
            district_code=getattr(osm_profile, "district_id", None),
            subdistrict_code=getattr(osm_profile, "subdistrict_id", None),
        )

    @staticmethod
    async def create_notification_from_officer_profile(
        *,
        actor_id: Optional[str],
        action_type: str,
        officer_profile,
    ) -> None:
        """Create a notification for officer-related actions (register, create, approve, reject)."""
        target_name = f"{getattr(officer_profile, 'first_name', '')} {getattr(officer_profile, 'last_name', '')}".strip()
        await NotificationService.create_notification(
            actor_id=actor_id,
            action_type=action_type,
            target_type="officer",
            target_id=str(officer_profile.id),
            target_name=target_name,
            citizen_id=getattr(officer_profile, "citizen_id", None),
            province_code=getattr(officer_profile, "province_id", None),
            district_code=getattr(officer_profile, "district_id", None),
            subdistrict_code=getattr(officer_profile, "subdistrict_id", None),
        )

    @staticmethod
    async def get_notifications(
        officer_scope: OfficerScope,
        officer_id: str,
        page: int = 1,
        limit: int = 20,
        is_read: Optional[bool] = None,
        target_type: str = "osm",
    ) -> Dict[str, Any]:
        return await NotificationRepository.find_for_officer(
            scope=officer_scope,
            officer_id=officer_id,
            page=page,
            limit=limit,
            is_read=is_read,
            target_type=target_type,
        )

    @staticmethod
    async def get_unread_count(
        officer_scope: OfficerScope,
        officer_id: str,
        target_type: str = "osm",
    ) -> int:
        return await NotificationRepository.count_unread(
            officer_scope, officer_id, target_type=target_type,
        )

    @staticmethod
    async def mark_as_read(notification_id: str, officer_id: str) -> bool:
        return await NotificationRepository.mark_read(notification_id, officer_id)

    @staticmethod
    async def mark_all_as_read(
        officer_scope: OfficerScope,
        officer_id: str,
        target_type: str = "osm",
    ) -> int:
        return await NotificationRepository.mark_all_read(
            officer_scope, officer_id, target_type=target_type,
        )
