from typing import Optional, List

from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, status, File, UploadFile, HTTPException

from app.api.middleware.middleware import require_scopes
from app.api.v1.controllers.officer_controller import OfficerController
from app.api.v1.schemas.officer_schema import (
    OfficerActiveStatusSchema,
    OfficerCreateSchema,
    OfficerApprovalActionSchema,
    OfficerRegistrationMetaSchema,
    OfficerRegistrationResponseSchema,
    LookupResponseSchema,
    OfficerQueryParams,
    OfficerBatchIdsSchema,
    OfficerTransferSchema,
    OfficerUpdateSchema,
)
from app.api.v1.schemas.response_schema import OfficerListPaginatedResponse
from app.api.v1.schemas.upload_schema import ProfileImageUploadResponse
from app.services.permission_service import PermissionService
from app.services.profile_image_service import ProfileImageService
from app.repositories.officer_profile_repository import OfficerProfileRepository

officer_router = APIRouter(prefix="/officer", tags=["officer"])


async def _ensure_officer(current_user: dict):
    await PermissionService.require_officer(current_user)


@officer_router.get("", response_model=OfficerListPaginatedResponse)
async def list_officers(
    filter_params: OfficerQueryParams = Depends(),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.list_officers(filter_params, current_user)


@officer_router.post("", status_code=status.HTTP_201_CREATED)
async def create_officer(
    officer: OfficerCreateSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.create_officer(officer, current_user)


@officer_router.post("/register", status_code=status.HTTP_201_CREATED, response_model=OfficerRegistrationResponseSchema)
async def register_officer(officer: OfficerCreateSchema):
    return await OfficerController.register_officer(officer)


@officer_router.post("/new", status_code=status.HTTP_201_CREATED)
async def create_officer_legacy(
    officer: OfficerCreateSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.create_officer(officer, current_user)


@officer_router.get("/register/meta", response_model=OfficerRegistrationMetaSchema)
async def get_registration_meta():
    return await OfficerController.get_registration_meta()


@officer_router.get("/register/genders", response_model=LookupResponseSchema)
async def get_registration_genders():
    return await OfficerController.get_registration_genders()


@officer_router.get("/register/prefixes", response_model=LookupResponseSchema)
async def get_registration_prefixes(
    keyword: Optional[str] = Query(None, description="ค้นหาคำนำหน้า"),
    limit: int = Query(200, ge=1, le=500),
):
    return await OfficerController.get_registration_prefixes(keyword, limit)


@officer_router.get("/register/positions", response_model=LookupResponseSchema)
async def get_registration_positions(
    keyword: Optional[str] = Query(None, description="ค้นหาตำแหน่ง"),
    limit: int = Query(500, ge=1, le=1000),
):
    return await OfficerController.get_registration_positions(keyword, limit)


@officer_router.get("/register/provinces", response_model=LookupResponseSchema)
async def get_registration_provinces(
    keyword: Optional[str] = Query(None, description="ค้นหาจังหวัด"),
    limit: int = Query(1000, ge=1, le=2000),
):
    return await OfficerController.get_registration_provinces(keyword, limit)


@officer_router.get("/register/districts", response_model=LookupResponseSchema)
async def get_registration_districts(
    province_code: str = Query(..., description="รหัสจังหวัด"),
    keyword: Optional[str] = Query(None, description="ค้นหาชื่ออำเภอ"),
):
    return await OfficerController.get_registration_districts(province_code, keyword)


@officer_router.get("/register/subdistricts", response_model=LookupResponseSchema)
async def get_registration_subdistricts(
    district_code: str = Query(..., description="รหัสอำเภอ"),
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อตำบล"),
):
    return await OfficerController.get_registration_subdistricts(district_code, keyword)


@officer_router.get("/register/municipalities", response_model=LookupResponseSchema)
async def get_registration_municipalities(
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อเทศบาล"),
):
    return await OfficerController.get_registration_municipalities(
        province_code=province_code,
        district_code=district_code,
        subdistrict_code=subdistrict_code,
        keyword=keyword,
    )


@officer_router.get("/register/health-services", response_model=LookupResponseSchema)
async def get_registration_health_services(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อหน่วยบริการสุขภาพ"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    health_service_type_ids: Optional[List[str]] = Query(
        None,
        description="กรองเฉพาะประเภทหน่วยบริการ (ใส่ key ซ้ำได้หลายค่า)",
    ),
    health_service_type_ids_exclude: Optional[List[str]] = Query(
        None,
        description="ตัดประเภทหน่วยบริการที่ไม่ต้องการ (ใส่ key ซ้ำได้หลายค่า)",
    ),
    limit: int = Query(100, ge=1, le=500),
):
    return await OfficerController.get_registration_health_services(
        keyword=keyword,
        province_code=province_code,
        district_code=district_code,
        subdistrict_code=subdistrict_code,
        health_service_type_ids=health_service_type_ids,
        health_service_type_ids_exclude=health_service_type_ids_exclude,
        limit=limit,
    )


@officer_router.post("/batch")
async def get_officers_batch(
    payload: OfficerBatchIdsSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """ดึงข้อมูล Officer หลายรายการพร้อมกันด้วยรายการ ID"""
    await _ensure_officer(current_user)
    return await OfficerController.get_officers_by_ids(payload.ids, current_user)


@officer_router.get("/{officer_id}")
async def get_officer(
    officer_id: str = Path(..., description="Officer profile ID"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.get_officer(officer_id, current_user)


@officer_router.put("/{officer_id}")
async def update_officer(
    officer_id: str,
    officer_data: OfficerUpdateSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.update_officer(officer_id, officer_data, current_user)


@officer_router.post("/{officer_id}/profile-image", response_model=ProfileImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_officer_profile_image(
    officer_id: str,
    image: UploadFile = File(..., description="Profile image file"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    existing = await OfficerProfileRepository.get_officer_by_id(officer_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")
    stored_path = await ProfileImageService.upload_profile_image(file=image, context="officer")
    updated = await OfficerProfileRepository.update_officer(
        officer_id,
        {"profile_image": stored_path, "updated_at": datetime.utcnow()},
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="update_failed")
    return ProfileImageUploadResponse(image_url=stored_path)


@officer_router.post("/{officer_id}/transfer")
async def transfer_officer(
    officer_id: str,
    payload: OfficerTransferSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.transfer_officer(officer_id, payload, current_user)


@officer_router.get("/{officer_id}/transfer-history")
async def get_transfer_history(
    officer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.get_transfer_history(officer_id, page, page_size, current_user)


@officer_router.patch("/{officer_id}/status")
async def set_officer_status(
    officer_id: str,
    payload: OfficerActiveStatusSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.set_active_status(officer_id, payload, current_user)


@officer_router.delete("/{officer_id}", status_code=status.HTTP_200_OK)
async def delete_officer(
    officer_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.delete_officer(officer_id, current_user)


@officer_router.post("/{officer_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_officer_password(
    officer_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.reset_password(officer_id, current_user)


@officer_router.post("/community/osm/{osm_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_osm_password(
    osm_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.reset_osm_password(osm_id, current_user)


@officer_router.patch("/community/osm/{osm_id}/status", status_code=status.HTTP_200_OK)
async def set_osm_active_status(
    osm_id: str,
    payload: OfficerActiveStatusSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.set_osm_active_status(osm_id, payload, current_user)


@officer_router.post("/community/yuwa-osm/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_yuwa_password(
    user_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.reset_yuwa_password(user_id, current_user)


@officer_router.patch("/community/yuwa-osm/{user_id}/status", status_code=status.HTTP_200_OK)
async def set_yuwa_active_status(
    user_id: str,
    payload: OfficerActiveStatusSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.set_yuwa_active_status(user_id, payload, current_user)


@officer_router.post("/community/people/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_people_password(
    user_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.reset_people_password(user_id, current_user)


@officer_router.patch("/community/people/{user_id}/status", status_code=status.HTTP_200_OK)
async def set_people_active_status(
    user_id: str,
    payload: OfficerActiveStatusSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.set_people_active_status(user_id, payload, current_user)


@officer_router.post("/community/gen-h/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_gen_h_password(
    user_id: str,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.reset_gen_h_password(user_id, current_user)


@officer_router.patch("/community/gen-h/{user_id}/status", status_code=status.HTTP_200_OK)
async def set_gen_h_active_status(
    user_id: str,
    payload: OfficerActiveStatusSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.set_gen_h_active_status(user_id, payload, current_user)


@officer_router.post("/{officer_id}/approve")
async def approve_officer(
    officer_id: str,
    payload: OfficerApprovalActionSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.approve_officer(officer_id, payload, current_user)


@officer_router.post("/{officer_id}/reject")
async def reject_officer(
    officer_id: str,
    payload: OfficerApprovalActionSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await _ensure_officer(current_user)
    return await OfficerController.reject_officer(officer_id, payload, current_user)