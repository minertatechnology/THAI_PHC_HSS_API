"""Routes สำหรับ CRUD ข้อมูลดีเด่น (Outstanding Achievements) ของ อสม."""

from __future__ import annotations

from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    UploadFile,
    status,
)

from app.api.middleware.middleware import get_current_user
from app.api.v1.schemas.osm_outstanding_schema import (
    OsmOutstandingListResponse,
    OsmOutstandingResponse,
)
from app.services.osm_outstanding_service import OsmOutstandingService

osm_outstanding_router = APIRouter(
    prefix="/osm-outstandings",
    tags=["osm-outstandings"],
)


# ──────────────────────────  LIST  ──────────────────────────

@osm_outstanding_router.get(
    "/osm/{osm_profile_id}",
    response_model=OsmOutstandingListResponse,
    summary="ดึงข้อมูลดีเด่นทั้งหมดของ อสม.",
)
async def list_outstandings(
    osm_profile_id: str = Path(..., description="UUID ของ osm_profile"),
    current_user: dict = Depends(get_current_user),
) -> OsmOutstandingListResponse:
    items = await OsmOutstandingService.list_by_osm(osm_profile_id)
    return OsmOutstandingListResponse(items=items, total=len(items))


# ──────────────────────────  GET  ──────────────────────────

@osm_outstanding_router.get(
    "/{outstanding_id}",
    response_model=OsmOutstandingResponse,
    summary="ดึงข้อมูลดีเด่นรายการเดียว",
)
async def get_outstanding(
    outstanding_id: str = Path(..., description="UUID ของ outstanding"),
    current_user: dict = Depends(get_current_user),
) -> OsmOutstandingResponse:
    item = await OsmOutstandingService.get(outstanding_id)
    return OsmOutstandingResponse(**item)


# ──────────────────────────  CREATE  ──────────────────────────

@osm_outstanding_router.post(
    "/osm/{osm_profile_id}",
    response_model=OsmOutstandingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="เพิ่มข้อมูลดีเด่น (osm เพิ่มเอง หรือ officer เพิ่มให้)",
)
async def create_outstanding(
    osm_profile_id: str = Path(..., description="UUID ของ osm_profile"),
    award_year: int = Form(..., description="ปี พ.ศ. ที่ได้รับ"),
    award_level_id: Optional[str] = Form(default=None, description="UUID ระดับดีเด่น"),
    award_category_id: Optional[str] = Form(default=None, description="UUID ประเภทดีเด่น"),
    title: Optional[str] = Form(default=None, max_length=500, description="ชื่อผลงานดีเด่น"),
    description: Optional[str] = Form(default=None, description="รายละเอียดผลงาน"),
    images: Optional[List[UploadFile]] = File(
        default=None,
        description="รูปภาพใบประกาศนียบัตร (สูงสุด 10 รูป รูปละไม่เกิน 20MB)",
    ),
    current_user: dict = Depends(get_current_user),
) -> OsmOutstandingResponse:
    item = await OsmOutstandingService.create(
        current_user=current_user,
        osm_profile_id=osm_profile_id,
        award_year=award_year,
        award_level_id=award_level_id,
        award_category_id=award_category_id,
        title=title,
        description=description,
        images=images,
    )
    return OsmOutstandingResponse(**item)


# ──────────────────────────  UPDATE  ──────────────────────────

@osm_outstanding_router.put(
    "/{outstanding_id}",
    response_model=OsmOutstandingResponse,
    summary="แก้ไขข้อมูลดีเด่น (ไม่รวมรูปภาพ — ใช้ endpoints ด้านล่าง)",
)
async def update_outstanding(
    outstanding_id: str = Path(..., description="UUID ของ outstanding"),
    award_year: Optional[int] = Form(default=None, description="ปี พ.ศ. ที่ได้รับ"),
    award_level_id: Optional[str] = Form(default=None, description="UUID ระดับดีเด่น"),
    award_category_id: Optional[str] = Form(default=None, description="UUID ประเภทดีเด่น"),
    title: Optional[str] = Form(default=None, max_length=500, description="ชื่อผลงานดีเด่น"),
    description: Optional[str] = Form(default=None, description="รายละเอียดผลงาน"),
    current_user: dict = Depends(get_current_user),
) -> OsmOutstandingResponse:
    item = await OsmOutstandingService.update(
        current_user=current_user,
        outstanding_id=outstanding_id,
        award_year=award_year,
        award_level_id=award_level_id,
        award_category_id=award_category_id,
        title=title,
        description=description,
    )
    return OsmOutstandingResponse(**item)


# ──────────────────────────  DELETE  ──────────────────────────

@osm_outstanding_router.delete(
    "/{outstanding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="ลบข้อมูลดีเด่น (soft delete)",
)
async def delete_outstanding(
    outstanding_id: str = Path(..., description="UUID ของ outstanding"),
    current_user: dict = Depends(get_current_user),
):
    await OsmOutstandingService.delete(
        current_user=current_user,
        outstanding_id=outstanding_id,
    )
    return None


# ──────────────────────────  ADD IMAGES  ──────────────────────────

@osm_outstanding_router.post(
    "/{outstanding_id}/images",
    response_model=OsmOutstandingResponse,
    summary="เพิ่มรูปภาพใบประกาศนียบัตรเข้า outstanding ที่มีอยู่แล้ว",
)
async def add_images(
    outstanding_id: str = Path(..., description="UUID ของ outstanding"),
    images: List[UploadFile] = File(..., description="รูปภาพที่ต้องการเพิ่ม"),
    current_user: dict = Depends(get_current_user),
) -> OsmOutstandingResponse:
    item = await OsmOutstandingService.add_images(
        current_user=current_user,
        outstanding_id=outstanding_id,
        images=images,
    )
    return OsmOutstandingResponse(**item)


# ──────────────────────────  DELETE IMAGE  ──────────────────────────

@osm_outstanding_router.delete(
    "/{outstanding_id}/images/{image_id}",
    response_model=OsmOutstandingResponse,
    summary="ลบรูปภาพใบประกาศนียบัตรรูปเดียว",
)
async def delete_image(
    outstanding_id: str = Path(..., description="UUID ของ outstanding"),
    image_id: str = Path(..., description="UUID ของรูปภาพ"),
    current_user: dict = Depends(get_current_user),
) -> OsmOutstandingResponse:
    item = await OsmOutstandingService.delete_image(
        current_user=current_user,
        outstanding_id=outstanding_id,
        image_id=image_id,
    )
    return OsmOutstandingResponse(**item)
