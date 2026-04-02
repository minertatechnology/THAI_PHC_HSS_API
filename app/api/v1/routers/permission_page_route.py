from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.middleware.middleware import get_current_user
from app.api.v1.schemas.permission_page_schema import (
    PermissionPageCreate,
    PermissionPageResponse,
    PermissionPageUpdate,
)
from app.services.permission_page_service import PermissionPageService
from app.services.permission_service import PermissionService


permission_page_router = APIRouter(prefix="/auth/permission-pages", tags=["permission-pages"])


@permission_page_router.get("", response_model=List[PermissionPageResponse])
async def list_permission_pages(
    system_name: Optional[str] = Query(default=None, description="ชื่อระบบ เช่น thai_phc_web"),
    include_inactive: bool = Query(default=False, description="ดึงข้อมูลที่ปิดการใช้งานด้วยหรือไม่"),
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    pages = await PermissionPageService.list_pages(
        system_name=system_name,
        include_inactive=include_inactive,
    )
    return pages


@permission_page_router.post("", response_model=PermissionPageResponse, status_code=201)
async def create_permission_page(
    payload: PermissionPageCreate,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    created = await PermissionPageService.create_page(payload=payload.dict())
    return created


@permission_page_router.put("/{page_id}", response_model=PermissionPageResponse)
async def update_permission_page(
    page_id: str,
    payload: PermissionPageUpdate,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    updated = await PermissionPageService.update_page(page_id, payload=payload.dict(exclude_unset=True))
    return updated


@permission_page_router.delete("/{page_id}", status_code=204)
async def delete_permission_page(
    page_id: str,
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer(current_user)
    await PermissionPageService.delete_page(page_id)
    return None
