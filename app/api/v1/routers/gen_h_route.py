from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status  # noqa: F401
from typing import Optional

from app.api.middleware.middleware import require_scopes
from app.api.v1.controllers.gen_h_controller import GenHController
from app.api.v1.schemas.gen_h_schema import (
    GenHBatchIdsSchema,
    GenHCreateSchema,
    GenHQueryParams,
    GenHSelfUpdateSchema,
    GenHTransferToPeopleRequest,
    GenHUpdateSchema,
    GenHUpgradeToYuwaOSMRequest,
)
from app.api.v1.schemas.upload_schema import ProfileImageUploadResponse
from app.services.permission_service import PermissionService
from app.services.profile_image_service import ProfileImageService
from app.repositories.gen_h_user_repository import GenHUserRepository
from app.configs.config import settings

gen_h_router = APIRouter(prefix="/gen-h", tags=["gen-h"])


@gen_h_router.get("")
async def list_gen_h_users(
    search: str | None = Query(None),
    province_code: str | None = Query(None),
    district_code: str | None = Query(None),
    gender: str | None = Query(None),
    school: str | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """List Gen H users with filtering and pagination."""
    await PermissionService.require_officer(current_user)
    params = {
        "search": search,
        "province_code": province_code,
        "district_code": district_code,
        "gender": gender,
        "school": school,
        "is_active": is_active,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "per_page": per_page,
    }
    return await GenHController.list_users(params)


@gen_h_router.get("/summary")
async def gen_h_summary(
    province_code: str | None = Query(None),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Summary statistics for Gen H dashboard."""
    await PermissionService.require_officer(current_user)
    return await GenHController.summary(province_code=province_code)


@gen_h_router.post("", status_code=status.HTTP_201_CREATED)
async def register_gen_h_user(
    data: str = Form(..., description="JSON string of registration data"),
    profile_image: Optional[UploadFile] = File(None, description="Profile image file (optional)"),
):
    """Register a new Gen H user.

    Public when GEN_H_SELF_REGISTER_ENABLED=True (migration period).
    Set GEN_H_SELF_REGISTER_ENABLED=False in .env to close self-registration post-migration.
    Accepts multipart/form-data: send `data` as JSON string + optional `profile_image` file.
    """
    if not settings.GEN_H_SELF_REGISTER_ENABLED:
        raise HTTPException(status_code=403, detail="gen_h_self_register_disabled")
    try:
        payload = GenHCreateSchema.model_validate_json(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid registration data: {e}")
    return await GenHController.register(payload, current_user=None, profile_image=profile_image)


@gen_h_router.get("/{user_id}")
async def get_gen_h_user(
    user_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Get a Gen H user by UUID or gen_h_code."""
    # Officer: any level can view. Gen H user: can view themselves.
    user_type = current_user.get("user_type")
    if user_type == "gen_h":
        own_id = str(current_user.get("user_id", ""))
        if own_id != user_id:
            raise HTTPException(status_code=403, detail="forbidden: can only view own profile")
    elif not await PermissionService.is_officer(current_user):
        raise HTTPException(status_code=403, detail="forbidden: officer access required")
    return await GenHController.get_user(user_id)


@gen_h_router.patch("/{user_id}")
async def update_gen_h_user(
    user_id: str,
    payload: GenHUpdateSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Update a Gen H user. Gen H user can update own profile (restricted fields). Officer can update any user."""
    user_type = current_user.get("user_type")
    if user_type == "gen_h":
        own_id = str(current_user.get("user_id", ""))
        if own_id != user_id:
            raise HTTPException(status_code=403, detail="forbidden: can only update own profile")
        self_payload = GenHSelfUpdateSchema(**payload.model_dump(exclude_unset=True, exclude={"points", "is_active", "profile_image_url", "member_card_url"}))
        return await GenHController.update_user(user_id, self_payload, current_user)
    await PermissionService.require_officer(current_user)
    return await GenHController.update_user(user_id, payload, current_user)


@gen_h_router.post("/{user_id}/transfer-to-people")
async def transfer_gen_h_to_people(
    user_id: str,
    payload: GenHTransferToPeopleRequest,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Transfer a Gen H user to people_user (officer only, scope checked in service)."""
    await PermissionService.require_officer(current_user)
    actor_id = str(current_user.get("user_id", ""))
    return await GenHController.transfer_to_people(user_id, payload, actor_id, current_user)


@gen_h_router.post("/{user_id}/upgrade-to-yuwa-osm", status_code=status.HTTP_200_OK)
async def upgrade_gen_h_to_yuwa_osm(
    user_id: str,
    payload: GenHUpgradeToYuwaOSMRequest,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Self-service: gen_h user กรอก citizen_id เพื่อ upgrade เป็น yuwa_osm.

    - เรียกได้โดย gen_h user เอง (เพื่อ upgrade ตัวเอง)
    - หลัง upgrade: gen_h จะถูกปิด, login ด้วย gen_h_code หรือ citizen_id ที่ yuwa_osm ได้เลย
    """
    user_type = current_user.get("user_type")
    if user_type == "gen_h":
        if str(current_user.get("user_id", "")) != user_id:
            raise HTTPException(status_code=403, detail="forbidden: can only upgrade own account")
    elif not await PermissionService.is_officer(current_user):
        raise HTTPException(status_code=403, detail="forbidden: gen_h or officer access required")
    return await GenHController.upgrade_to_yuwa_osm(user_id, payload, current_user)


@gen_h_router.post("/batch")
async def get_gen_h_batch(
    payload: GenHBatchIdsSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """ดึงข้อมูล Gen H หลายรายการพร้อมกันด้วยรายการ ID (เฉพาะเจ้าหน้าที่)"""
    await PermissionService.require_officer(current_user)
    return await GenHController.get_gen_h_by_ids(payload.ids)


@gen_h_router.post("/{user_id}/profile-image", response_model=ProfileImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_gen_h_profile_image(
    request: Request,
    user_id: str,
    image: UploadFile = File(..., description="Profile image file"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Upload profile image for a Gen H user (officer or gen_h owner)."""
    user_type = current_user.get("user_type")
    if user_type == "gen_h":
        if str(current_user.get("user_id", "")) != user_id:
            raise HTTPException(status_code=403, detail="forbidden: can only update own profile")
    elif not await PermissionService.is_officer(current_user):
        raise HTTPException(status_code=403, detail="forbidden: officer access required")
    existing = await GenHUserRepository.get_by_id(UUID(user_id))
    if not existing:
        raise HTTPException(status_code=404, detail="gen_h_user_not_found")
    stored_path = await ProfileImageService.upload_profile_image(file=image, context="gen_h")
    await GenHUserRepository.update_user(existing, profile_image_url=stored_path)
    base_url = str(request.base_url).rstrip("/")
    return ProfileImageUploadResponse(image_url=f"{base_url}/{stored_path}")


@gen_h_router.post("/{user_id}/photo-1inch", response_model=ProfileImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_gen_h_photo_1inch(
    request: Request,
    user_id: str,
    image: UploadFile = File(..., description="1-inch photo file"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Upload 1-inch photo for a Gen H user (officer or gen_h owner)."""
    user_type = current_user.get("user_type")
    if user_type == "gen_h":
        if str(current_user.get("user_id", "")) != user_id:
            raise HTTPException(status_code=403, detail="forbidden: can only update own profile")
    elif not await PermissionService.is_officer(current_user):
        raise HTTPException(status_code=403, detail="forbidden: officer access required")
    existing = await GenHUserRepository.get_by_id(UUID(user_id))
    if not existing:
        raise HTTPException(status_code=404, detail="gen_h_user_not_found")
    stored_path = await ProfileImageService.upload_profile_image(file=image, context="gen_h")
    await GenHUserRepository.update_user(existing, photo_1inch=stored_path)
    base_url = str(request.base_url).rstrip("/")
    return ProfileImageUploadResponse(image_url=f"{base_url}/{stored_path}")


@gen_h_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gen_h_user(
    user_id: UUID,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Delete a Gen H user (officer only, scope checked in service)."""
    await PermissionService.require_officer(current_user)
    await GenHController.delete_user(user_id, current_user)
