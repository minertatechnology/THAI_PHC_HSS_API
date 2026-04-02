from fastapi import APIRouter, Request, Depends, Path, Query, HTTPException, status, Body, File, UploadFile
from app.api.v1.schemas.query_schema import OsmQueryParams
from app.api.v1.controllers.osm_controller import OsmController
from app.api.v1.schemas.osm_schema import (
    OsmActiveStatusSchema,
    OsmCreateSchema,
    OsmPositionConfirmationCreateSchema,
    OsmPositionConfirmationResponse,
    OsmPositionConfirmationUpdateSchema,
    OsmPositionResponse,
    OsmBatchIdsSchema,
    OsmUpdateSchema,
)
from app.api.v1.schemas.response_schema import (
    OsmProfileListResponse,
    OsmProfileSummaryResponse,
    OsmCreateResponse,
)
from app.api.v1.schemas.upload_schema import ProfileImageUploadResponse
from app.api.middleware.middleware import (
    get_current_user,
    get_current_user_optional,
    require_scopes,
)
from app.services.permission_service import PermissionService
from app.services.profile_image_service import ProfileImageService
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.models.enum_models import AdministrativeLevelEnum
from typing import List

osm_router = APIRouter(prefix="/osm", tags=["osm"])

@osm_router.get("/", response_model=List[OsmProfileListResponse])
async def find_all_osm(
    request: Request, 
    filter: OsmQueryParams = Depends(), 
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ค้นหา OSM ทั้งหมดพร้อม filter และ pagination
    หมายเหตุ: จำกัดสิทธิ์การเข้าถึง
      - Super admin: ดูได้ทั้งหมด
      - OSM: เห็นได้เฉพาะข้อมูลของตัวเองเท่านั้น (จะถูกบังคับ filter ด้วย citizen_id ตาม token)
      - Officer: เห็นได้เฉพาะพื้นที่ตัวเอง (filter ด้วย province/district/subdistrict หากไม่ได้ส่งมา จะไม่คืนทั้งหมด)
    """
    is_officer_user = await PermissionService.is_officer(current_user)
    user_type = current_user.get("user_type")

    if not is_officer_user:
        from app.repositories.osm_profile_repository import OSMProfileRepository
        if user_type == "osm":
            profile = await OSMProfileRepository.find_osm_by_id(current_user.get("user_id"))
            if profile and profile.get("osm_profile"):
                filter.citizen_id = profile["osm_profile"].citizen_id
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    result = await OsmController.find_all_osm(request, filter, current_user)
    return result

@osm_router.get("/me")
async def get_my_osm_profile(current_user: dict = Depends(require_scopes({"openid", "profile"}))):
    """
    คืนข้อมูล OSM ของผู้ใช้ที่ login อยู่ (เฉพาะ user_type=osm)
    """
    if current_user.get("user_type") != "osm":
        return {"status": "success", "data": None, "message": "not_osm_user"}
    # ใช้ controller เดิมในการคืนข้อมูลแบบ detail ที่รวม spouse/children
    from app.api.v1.controllers.osm_controller import OsmController
    return await OsmController.get_osm_by_id(current_user["user_id"], current_user)


@osm_router.post("/batch")
async def get_osm_batch(
    payload: OsmBatchIdsSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """ดึงข้อมูล OSM หลายรายการพร้อมกันด้วยรายการ ID (เฉพาะเจ้าหน้าที่)"""
    await PermissionService.require_officer(current_user)
    return await OsmController.get_osms_by_ids(payload.ids, current_user)

@osm_router.post("/new", status_code=status.HTTP_201_CREATED, response_model=OsmCreateResponse)
async def create_osm(
    osm: OsmCreateSchema,
    current_user: dict | None = Depends(get_current_user_optional),
):
    """
    สร้าง OSM Profile ใหม่ (เปิดให้ประชาชนสมัครเองได้ และรองรับการสร้างโดยเจ้าหน้าที่)
    """
    result = await OsmController.create_osm(osm, current_user)
    return result

@osm_router.get("/summary/{osm_id}", response_model=OsmProfileSummaryResponse)
async def get_osm_summary_by_id(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """
    ดึงข้อมูล OSM แบบย่อ (prefix/ชื่อ/จังหวัด/อำเภอ/ตำบล)
    รองรับเฉพาะผู้ใช้ role osm หรือ yuwa_osm
    """
    user_type = current_user.get("user_type")
    if user_type not in {"osm", "yuwa_osm"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return await OsmController.get_osm_summary_by_id(osm_id, current_user)

@osm_router.get("/{osm_id}")
async def get_osm_by_id(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ดึงข้อมูล OSM Profile ด้วย ID
    """
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "osm" or current_user.get("user_id") != osm_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    result = await OsmController.get_osm_by_id(osm_id, current_user)
    return result

@osm_router.get("/citizen/{citizen_id}")
async def get_osm_by_citizen_id(
    citizen_id: str = Path(..., description="เลขบัตรประชาชน"),
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ดึงข้อมูล OSM Profile ด้วยเลขบัตรประชาชน
    """
    await PermissionService.require_officer(current_user)
    result = await OsmController.get_osm_by_citizen_id(citizen_id, current_user)
    return result

@osm_router.put("/{osm_id}")
async def update_osm(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    osm_data: OsmUpdateSchema = None,
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    อัปเดตข้อมูล OSM Profile
    """
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "osm" or current_user.get("user_id") != osm_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    result = await OsmController.update_osm(osm_id, osm_data, current_user)
    return result


@osm_router.post("/{osm_id}/profile-image", response_model=ProfileImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_osm_profile_image(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    image: UploadFile = File(..., description="Profile image file"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    if not await PermissionService.is_officer(current_user):
        if current_user.get("user_type") != "osm" or current_user.get("user_id") != osm_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    existing = await OSMProfileRepository.get_profile_for_management(osm_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบ OSM Profile ที่ต้องการอัปเดตรูปโปรไฟล์")
    stored_path = await ProfileImageService.upload_profile_image(file=image, context="osm")
    actor_id = str(current_user.get("user_id") or osm_id)
    await OSMProfileRepository.update_osm(osm_id, {"profile_image": stored_path}, actor_id)
    return ProfileImageUploadResponse(image_url=stored_path)


@osm_router.patch("/{osm_id}/status")
async def set_osm_status(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    payload: OsmActiveStatusSchema = Body(...),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.PROVINCE,
    )
    return await OsmController.set_active_status(osm_id, payload, current_user)


@osm_router.post("/{osm_id}/activate", status_code=status.HTTP_200_OK)
async def activate_osm(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """อนุมัติและเปิดใช้งาน OSM (เฉพาะเจ้าหน้าที่ระดับจังหวัดขึ้นไป)"""
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.PROVINCE,
    )
    return await OsmController.activate_osm(osm_id, current_user)


# New endpoint: Reject OSM profile
@osm_router.post("/{osm_id}/reject", status_code=status.HTTP_200_OK)
async def reject_osm(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """ปฏิเสธ OSM (เฉพาะเจ้าหน้าที่ระดับจังหวัดขึ้นไป)"""
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.PROVINCE,
    )
    return await OsmController.reject_osm(osm_id, current_user)

@osm_router.delete("/{osm_id}")
async def delete_osm(
    osm_id: str = Path(..., description="ID ของ OSM Profile"),
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ลบ OSM Profile
    """
    await PermissionService.require_officer(current_user)
    result = await OsmController.delete_osm(osm_id, current_user)
    return result

@osm_router.get("/statistics/overview")
async def get_osm_statistics(
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ดึงสถิติข้อมูล OSM
    """
    await PermissionService.require_officer(current_user)
    result = await OsmController.get_osm_statistics(current_user)
    return result

# Position Confirmation Endpoints
@osm_router.post("/position-confirmation")
async def create_or_update_position_confirmation(
    position_data: OsmPositionConfirmationCreateSchema,
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    สร้างหรืออัปเดตการยืนยันตำแหน่งและสิทธิ์เงินค่าป่วยการ (upsert)
    """
    result = await OsmController.create_or_update_position_confirmation(position_data, current_user)
    return result

@osm_router.get("/position-confirmation/{osm_profile_id}")
async def get_position_confirmation_by_osm_id(
    osm_profile_id: str = Path(..., description="ID ของ OSM Profile"),
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ดึงการยืนยันตำแหน่งของ OSM Profile
    """
    result = await OsmController.get_position_confirmation_by_osm_id(osm_profile_id, current_user)
    return result

@osm_router.delete("/position-confirmation/{confirmation_id}")
async def delete_position_confirmation(
    confirmation_id: str = Path(..., description="ID ของการยืนยันตำแหน่ง"),
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ลบการยืนยันตำแหน่ง (Soft Delete)
    """
    result = await OsmController.delete_position_confirmation(confirmation_id, current_user)
    return result

@osm_router.get("/positions")
async def get_all_osm_positions(
    current_user: dict = Depends(require_scopes({"profile"}))
):
    """
    ดึงตำแหน่ง OSM ทั้งหมด
    """
    result = await OsmController.get_all_osm_positions(current_user)
    return result