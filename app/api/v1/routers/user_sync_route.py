from __future__ import annotations

from fastapi import APIRouter, status

from app.api.v1.controllers.user_sync_controller import UserSyncController
from app.api.v1.schemas.user_sync_schema import (
    UserSyncCreateSchema,
    UserSyncResponseSchema,
    UserSyncUpdateSchema,
)

user_sync_router = APIRouter(prefix="/user/sync", tags=["user-sync"])


@user_sync_router.put(
    "/users/{uuid}",
    response_model=UserSyncResponseSchema,
    summary="Sync update user จาก mobile app",
    description="อัปเดตข้อมูล people_user จาก frontend sync payload — ใช้ uuid จาก Keycloak (sub)",
)
async def sync_update_user(uuid: str, payload: UserSyncUpdateSchema):
    return await UserSyncController.sync_update(uuid, payload.dict(exclude_unset=True))


@user_sync_router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=UserSyncResponseSchema,
    summary="Sync create user จาก mobile app",
    description="สร้าง people_user ใหม่จาก frontend sync payload — ต้องมี id (UUID)",
)
async def sync_create_user(payload: UserSyncCreateSchema):
    return await UserSyncController.sync_create(payload.dict(exclude_unset=True))


@user_sync_router.get(
    "/health",
    summary="Health check สำหรับ user sync endpoints",
)
async def sync_health():
    return {"status": "ok", "service": "user_sync"}
