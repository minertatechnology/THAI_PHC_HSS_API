from __future__ import annotations

from fastapi import HTTPException

from app.services.user_sync_service import UserSyncService


class UserSyncController:
    """Controller สำหรับ sync endpoints — รับข้อมูลจาก mobile app."""

    @staticmethod
    async def sync_update(uuid: str, payload: dict):
        """PUT /user/sync/users/{uuid} — update ข้อมูล user จาก sync."""
        try:
            return await UserSyncService.sync_update(uuid, payload)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def sync_create(payload: dict):
        """POST /user/sync/users — สร้าง user ใหม่จาก sync."""
        try:
            user_id = payload.get("id")
            if not user_id:
                raise HTTPException(status_code=400, detail="id_required")
            return await UserSyncService.sync_create(user_id, payload)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
