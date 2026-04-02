from __future__ import annotations

from fastapi import APIRouter, Depends, status, File, UploadFile, HTTPException

from app.api.middleware.middleware import require_scopes
from app.api.v1.controllers.people_controller import PeopleController
from app.api.v1.schemas.people_schema import PeopleCreateSchema, PeopleUpdateSchema, PeopleBatchIdsSchema
from app.api.v1.schemas.upload_schema import ProfileImageUploadResponse
from app.services.permission_service import PermissionService
from app.services.profile_image_service import ProfileImageService
from app.repositories.people_user_repository import PeopleUserRepository


people_router = APIRouter(prefix="/people", tags=["people"])


@people_router.post("", status_code=status.HTTP_201_CREATED)
async def register_people_user(payload: PeopleCreateSchema):
    return await PeopleController.register_user(payload)


@people_router.get("/{user_id}")
async def get_people_user(
    user_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    # Allow the people user themselves OR an officer
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "people" or str(current_user.get("user_id")) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return await PeopleController.get_user(user_id, current_user)


@people_router.patch("/{user_id}")
async def update_people_user(
    user_id: str,
    payload: PeopleUpdateSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    # Allow the people user themselves OR an officer
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "people" or str(current_user.get("user_id")) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return await PeopleController.update_user(user_id, payload, current_user)


@people_router.post("/batch")
async def get_people_batch(
    payload: PeopleBatchIdsSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """ดึงข้อมูล People หลายรายการพร้อมกันด้วยรายการ ID (เฉพาะเจ้าหน้าที่)"""
    await PermissionService.require_officer(current_user)
    return await PeopleController.get_people_by_ids(payload.ids, current_user)


@people_router.post("/{user_id}/profile-image", response_model=ProfileImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_people_profile_image(
    user_id: str,
    image: UploadFile = File(..., description="Profile image file"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "people" or str(current_user.get("user_id")) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    existing = await PeopleUserRepository.get_user_for_management(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="people_user_not_found")
    stored_path = await ProfileImageService.upload_profile_image(file=image, context="people")
    updated = await PeopleUserRepository.update_user(user_id, {"profile_image": stored_path})
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="people_user_update_failed")
    return ProfileImageUploadResponse(image_url=stored_path)
