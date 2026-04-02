from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.middleware.middleware import get_current_user
from app.api.v1.schemas.user_lookup_schema import (
    UserLookupDetailResponse,
    UserLookupListResponse,
)
from app.services.permission_service import PermissionService
from app.services.user_lookup_service import UserLookupService

user_lookup_router = APIRouter(prefix="/auth/officer/lookups", tags=["auth", "officer-lookups"])


async def _require_officer(current_user: dict = Depends(get_current_user)) -> dict:
    await PermissionService.require_officer(current_user)
    return current_user


@user_lookup_router.get("/user-id", response_model=UserLookupListResponse)
async def lookup_by_user_id(
    user_id: Optional[str] = Query(None, description="UUID ของผู้ใช้ หากไม่ระบุจะคืนรายการทั้งหมด"),
    user_type: Optional[str] = Query(None, description="จำกัดการค้นหาเฉพาะประเภทผู้ใช้"),
    limit: int = Query(50, ge=1, le=200, description="จำนวนผลลัพธ์ต่อหน้าเมื่อไม่ระบุ user_id"),
    offset: int = Query(0, ge=0, description="จำนวนรายการที่ต้องข้ามก่อนแสดงผล"),
    _: dict = Depends(_require_officer),
):
    if user_id:
        items = await UserLookupService.find_users_by_uuid(user_id, user_type=user_type)
        count = len(items)
        return {"items": items, "count": count, "total": count, "limit": limit, "offset": 0}

    return await UserLookupService.list_users(limit=limit, offset=offset, user_type=user_type)


@user_lookup_router.get("/user-id/{user_id}", response_model=UserLookupDetailResponse)
async def lookup_detail_by_user_id(
    user_id: str,
    user_type: Optional[str] = Query(None, description="ประเภทผู้ใช้หากทราบ"),
    _: dict = Depends(_require_officer),
):
    data = await UserLookupService.get_user_detail_by_uuid(user_id, user_type)
    return {"success": True, "data": data}


@user_lookup_router.get("/citizen-id", response_model=UserLookupListResponse)
async def lookup_by_citizen_id(
    citizen_id: str = Query(..., description="เลขประจำตัวประชาชน"),
    user_type: Optional[str] = Query(None, description="จำกัดการค้นหาเฉพาะประเภทผู้ใช้"),
    _: dict = Depends(_require_officer),
):
    items = await UserLookupService.find_users_by_citizen_id(citizen_id, user_type=user_type)
    count = len(items)
    return {"items": items, "count": count, "total": count, "limit": count, "offset": 0}


@user_lookup_router.get("/citizen-id/{citizen_id}", response_model=UserLookupDetailResponse)
async def lookup_detail_by_citizen_id(
    citizen_id: str,
    user_type: Optional[str] = Query(None, description="ประเภทผู้ใช้หากทราบ"),
    _: dict = Depends(_require_officer),
):
    data = await UserLookupService.get_user_detail_by_citizen_id(citizen_id, user_type)
    return {"success": True, "data": data}


@user_lookup_router.get("/age", response_model=UserLookupListResponse)
async def lookup_by_age(
    min_age: Optional[int] = Query(None, ge=0, description="อายุต่ำสุด"),
    max_age: Optional[int] = Query(None, ge=0, description="อายุสูงสุด"),
    limit: int = Query(50, ge=1, le=200, description="จำนวนผลลัพธ์ต่อหน้า"),
    offset: int = Query(0, ge=0, description="จำนวนรายการที่ต้องข้ามก่อนแสดงผล"),
    user_type: Optional[str] = Query(None, description="จำกัดการค้นหาเฉพาะประเภทผู้ใช้"),
    _: dict = Depends(_require_officer),
):
    if min_age is not None and max_age is not None and min_age > max_age:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_age_range")
    return await UserLookupService.find_users_by_age(
        min_age=min_age,
        max_age=max_age,
        limit=limit,
        offset=offset,
        user_type=user_type,
    )


@user_lookup_router.get("/gender", response_model=UserLookupListResponse)
async def lookup_by_gender(
    gender: str = Query(..., description="เพศที่ต้องการค้นหา"),
    limit: int = Query(50, ge=1, le=200, description="จำนวนผลลัพธ์ต่อหน้า"),
    offset: int = Query(0, ge=0, description="จำนวนรายการที่ต้องข้ามก่อนแสดงผล"),
    user_type: Optional[str] = Query(None, description="จำกัดการค้นหาเฉพาะประเภทผู้ใช้"),
    _: dict = Depends(_require_officer),
):
    return await UserLookupService.find_users_by_gender(
        gender,
        limit=limit,
        offset=offset,
        user_type=user_type,
    )


@user_lookup_router.get("/users/{user_id}", response_model=UserLookupDetailResponse)
async def get_user_detail(
    user_id: str,
    user_type: Optional[str] = Query(None, description="ประเภทผู้ใช้หากทราบ"),
    _: dict = Depends(_require_officer),
):
    data = await UserLookupService.get_user_detail(user_id, user_type)
    return {"success": True, "data": data}