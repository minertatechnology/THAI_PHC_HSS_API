from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response, status, File, UploadFile, HTTPException

from app.api.middleware.middleware import require_scopes
from app.api.v1.controllers.yuwa_osm_controller import YuwaOsmController
from app.api.v1.schemas.yuwa_osm_schema import (
    YuwaOSMBatchIdsSchema,
    YuwaOSMDecisionPayload,
    YuwaOSMQueryParams,
    YuwaOSMRejectPayload,
    YuwaOSMSummaryQueryParams,
    YuwaOSMTransferRequest,
    YuwaOSMUpdateSchema,
)
from app.api.v1.schemas.upload_schema import ProfileImageUploadResponse
from app.services.permission_service import PermissionService
from app.services.profile_image_service import ProfileImageService
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository


yuwa_osm_router = APIRouter(prefix="/yuwa-osm", tags=["yuwa-osm"])


@yuwa_osm_router.get("")
async def list_yuwa_osm_users(
    filter_params: YuwaOSMQueryParams = Depends(),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    return await YuwaOsmController.list_users(filter_params, current_user)


@yuwa_osm_router.get("/summary")
async def summary_yuwa_osm_users(
    response: Response,
    filter_params: YuwaOSMSummaryQueryParams = Depends(),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    response.headers["Cache-Control"] = "private, max-age=600"
    response.headers["Expires"] = expires_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
    response.headers["Vary"] = "Authorization"
    return await YuwaOsmController.summary(filter_params, current_user)


# NOTE: Direct Yuwa OSM registration disabled. Use transfer from People instead.
# @yuwa_osm_router.post("", status_code=status.HTTP_201_CREATED)
# async def register_yuwa_osm_user(payload: YuwaOSMCreateSchema):
#     return await YuwaOsmController.register_user(payload)


@yuwa_osm_router.get("/{user_id}")
async def get_yuwa_osm_user(
    user_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    # Allow the yuwa_osm user themselves OR an officer
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "yuwa_osm" or str(current_user.get("user_id")) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return await YuwaOsmController.get_user(user_id, current_user)


@yuwa_osm_router.patch("/{user_id}")
async def update_yuwa_osm_user(
    user_id: str,
    payload: YuwaOSMUpdateSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    # Allow the yuwa_osm user themselves OR an officer
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "yuwa_osm" or str(current_user.get("user_id")) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return await YuwaOsmController.update_user(user_id, payload, current_user)


@yuwa_osm_router.post("/{user_id}/profile-image", response_model=ProfileImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_yuwa_osm_profile_image(
    request: Request,
    user_id: str,
    image: UploadFile = File(..., description="Profile image file"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "yuwa_osm" or str(current_user.get("user_id")) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    existing = await YuwaOSMUserRepository.get_user_for_management(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")
    stored_path = await ProfileImageService.upload_profile_image(file=image, context="yuwa_osm")
    updated = await YuwaOSMUserRepository.update_user(user_id, {"profile_image": stored_path})
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="yuwa_osm_update_failed")
    base_url = str(request.base_url).rstrip("/")
    return ProfileImageUploadResponse(image_url=f"{base_url}/{stored_path}")


@yuwa_osm_router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_yuwa_osm_user(
    user_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    return await YuwaOsmController.delete_user(user_id, current_user)


@yuwa_osm_router.post("/{user_id}/approve")
async def approve_yuwa_osm_user(
    user_id: str,
    payload: YuwaOSMDecisionPayload,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    return await YuwaOsmController.approve_user(user_id, payload, current_user)


@yuwa_osm_router.post("/{user_id}/reject")
async def reject_yuwa_osm_user(
    user_id: str,
    payload: YuwaOSMRejectPayload,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    return await YuwaOsmController.reject_user(user_id, payload, current_user)


@yuwa_osm_router.post("/{user_id}/retire")
async def retire_yuwa_osm_user(
    user_id: str,
    payload: YuwaOSMDecisionPayload,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    return await YuwaOsmController.retire_user(user_id, payload, current_user)


@yuwa_osm_router.post("/batch")
async def get_yuwa_osm_batch(
    payload: YuwaOSMBatchIdsSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """ดึงข้อมูล Yuwa OSM หลายรายการพร้อมกันด้วยรายการ ID (เฉพาะเจ้าหน้าที่)"""
    await PermissionService.require_officer(current_user)
    return await YuwaOsmController.get_yuwa_osm_by_ids(payload.ids, current_user)


@yuwa_osm_router.post("/transfer", status_code=status.HTTP_201_CREATED)
async def transfer_people_to_yuwa_osm(
    payload: YuwaOSMTransferRequest,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer(current_user)
    return await YuwaOsmController.transfer_from_people(payload, current_user)
