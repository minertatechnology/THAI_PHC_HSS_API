from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from app.api.middleware.middleware import get_current_user
from app.api.v1.controllers.notification_controller import NotificationController
from app.api.v1.schemas.notification_schema import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)

notification_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notification_router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="จำนวน notification ที่ยังไม่อ่าน",
)
async def get_unread_count(
    target_type: str = Query("osm", description="ระบบ: osm, yuwa_osm หรือ officer"),
    current_user: dict = Depends(get_current_user),
):
    return await NotificationController.get_unread_count(current_user, target_type=target_type)


@notification_router.get(
    "",
    response_model=NotificationListResponse,
    summary="รายการ notification",
)
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = Query(None, description="กรอง: true=อ่านแล้ว, false=ยังไม่อ่าน, null=ทั้งหมด"),
    target_type: str = Query("osm", description="ระบบ: osm, yuwa_osm หรือ officer"),
    current_user: dict = Depends(get_current_user),
):
    return await NotificationController.list_notifications(
        current_user=current_user,
        page=page,
        limit=limit,
        is_read=is_read,
        target_type=target_type,
    )


# IMPORTANT: /read-all must be defined BEFORE /{notification_id}/read
# to avoid "read-all" matching as a notification_id parameter.
@notification_router.patch(
    "/read-all",
    summary="mark ทั้งหมดว่าอ่านแล้ว",
)
async def mark_all_as_read(
    target_type: str = Query("osm", description="ระบบ: osm, yuwa_osm หรือ officer"),
    current_user: dict = Depends(get_current_user),
):
    return await NotificationController.mark_all_as_read(current_user, target_type=target_type)


@notification_router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="รายละเอียด notification",
)
async def get_notification(
    notification_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
):
    return await NotificationController.get_notification(notification_id, current_user)


@notification_router.patch(
    "/{notification_id}/read",
    summary="mark notification ว่าอ่านแล้ว",
)
async def mark_as_read(
    notification_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
):
    return await NotificationController.mark_as_read(notification_id, current_user)
