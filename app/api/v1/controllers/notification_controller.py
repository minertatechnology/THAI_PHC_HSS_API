from __future__ import annotations

from typing import Any, Dict, Mapping, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.models.notification_model import OsmNotificationRead
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService
from app.services.permission_service import PermissionService


class NotificationController:

    @staticmethod
    async def list_notifications(
        current_user: Mapping[str, Any],
        page: int = 1,
        limit: int = 20,
        is_read: Optional[bool] = None,
        target_type: str = "osm",
    ) -> Dict[str, Any]:
        await PermissionService.require_officer(current_user)
        _, officer_scope = await PermissionService.resolve_officer_context(current_user)
        if not officer_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="forbidden: officer scope unavailable",
            )
        officer_id = current_user.get("user_id")
        return await NotificationService.get_notifications(
            officer_scope=officer_scope,
            officer_id=str(officer_id),
            page=page,
            limit=limit,
            is_read=is_read,
            target_type=target_type,
        )

    @staticmethod
    async def get_unread_count(
        current_user: Mapping[str, Any],
        target_type: str = "osm",
    ) -> Dict[str, int]:
        await PermissionService.require_officer(current_user)
        _, officer_scope = await PermissionService.resolve_officer_context(current_user)
        if not officer_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="forbidden: officer scope unavailable",
            )
        officer_id = current_user.get("user_id")
        count = await NotificationService.get_unread_count(
            officer_scope, str(officer_id), target_type=target_type,
        )
        return {"count": count}

    @staticmethod
    async def get_notification(
        notification_id: str,
        current_user: Mapping[str, Any],
    ) -> Dict[str, Any]:
        await PermissionService.require_officer(current_user)
        _, officer_scope = await PermissionService.resolve_officer_context(current_user)
        if not officer_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="forbidden: officer scope unavailable",
            )

        officer_id = str(current_user.get("user_id"))

        notification = await NotificationRepository.find_by_id(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="notification_not_found",
            )

        is_read = await OsmNotificationRead.filter(
            notification_id=notification.id,
            officer_id=UUID(officer_id),
        ).exists()

        return {
            "id": str(notification.id),
            "actor_name": notification.actor_name,
            "action_type": notification.action_type,
            "target_type": notification.target_type,
            "target_id": str(notification.target_id),
            "target_name": notification.target_name,
            "message": notification.message,
            "is_read": is_read,
            "created_at": notification.created_at,
        }

    @staticmethod
    async def mark_as_read(
        notification_id: str,
        current_user: Mapping[str, Any],
    ) -> Dict[str, str]:
        await PermissionService.require_officer(current_user)
        officer_id = current_user.get("user_id")
        success = await NotificationService.mark_as_read(notification_id, str(officer_id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mark_read_failed",
            )
        return {"status": "success"}

    @staticmethod
    async def mark_all_as_read(
        current_user: Mapping[str, Any],
        target_type: str = "osm",
    ) -> Dict[str, Any]:
        await PermissionService.require_officer(current_user)
        _, officer_scope = await PermissionService.resolve_officer_context(current_user)
        if not officer_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="forbidden: officer scope unavailable",
            )
        officer_id = current_user.get("user_id")
        marked = await NotificationService.mark_all_as_read(
            officer_scope, str(officer_id), target_type=target_type,
        )
        return {"status": "success", "marked_count": marked}
