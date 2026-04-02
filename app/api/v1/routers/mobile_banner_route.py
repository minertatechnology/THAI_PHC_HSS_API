from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Path, Query, Response, UploadFile, status

from app.api.middleware.middleware import get_current_user
from app.api.v1.schemas.mobile_banner_schema import (
    MobileBannerCreate,
    MobileBannerListResponse,
    MobileBannerResponse,
    MobileBannerUploadResponse,
    MobileBannerUpdate,
)
from app.models.enum_models import AdministrativeLevelEnum
from app.services.mobile_banner_service import MobileBannerService
from app.services.permission_service import PermissionService
from app.cache.redis_client import cache_get, cache_set

mobile_banner_router = APIRouter(prefix="/mobile/banners", tags=["mobile-banners"])


@mobile_banner_router.get("", response_model=MobileBannerListResponse)
async def list_mobile_banners(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive banners"),
    platform: Optional[str] = Query(default=None, description="Filter by platform (android/ios/web)."),
    current_user: dict = Depends(get_current_user),
) -> MobileBannerListResponse:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.AREA,
    )
    result = await MobileBannerService.list_banners(
        page=page,
        limit=limit,
        include_inactive=include_inactive,
        platform=platform,
    )
    return MobileBannerListResponse(**result)


@mobile_banner_router.get("/current", response_model=List[MobileBannerResponse])
async def list_visible_mobile_banners(
    platform: Optional[str] = Query(default=None, description="Filter for platform (android/ios/web)."),
    current_user: dict = Depends(get_current_user),
) -> List[MobileBannerResponse]:
    cache_key = f"mobile:banners:current:{platform}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return [MobileBannerResponse(**item) for item in cached]
    banners = await MobileBannerService.list_visible_banners(platform=platform)
    await cache_set(cache_key, banners, 3600)  # 1 hour
    return [MobileBannerResponse(**item) for item in banners]


@mobile_banner_router.get("/{banner_id}", response_model=MobileBannerResponse)
async def get_mobile_banner(
    banner_id: str = Path(..., description="Banner ID"),
    current_user: dict = Depends(get_current_user),
) -> MobileBannerResponse:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.AREA,
    )
    item = await MobileBannerService.get_banner(banner_id)
    return MobileBannerResponse(**item)


@mobile_banner_router.post("", response_model=MobileBannerResponse, status_code=status.HTTP_201_CREATED)
async def create_mobile_banner(
    payload: MobileBannerCreate,
    current_user: dict = Depends(get_current_user),
) -> MobileBannerResponse:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.AREA,
    )
    actor_id = current_user.get("user_id")
    item = await MobileBannerService.create_banner(payload=payload.dict(), actor_id=actor_id)
    return MobileBannerResponse(**item)


@mobile_banner_router.post("/upload", response_model=MobileBannerUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_mobile_banner_image(
    image: UploadFile = File(..., description="Banner image file"),
    current_user: dict = Depends(get_current_user),
) -> MobileBannerUploadResponse:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.AREA,
    )
    stored_path = await MobileBannerService.upload_banner_image(file=image)
    return MobileBannerUploadResponse(image_url=stored_path)


@mobile_banner_router.put("/{banner_id}", response_model=MobileBannerResponse)
async def update_mobile_banner(
    payload: MobileBannerUpdate,
    banner_id: str = Path(..., description="Banner ID"),
    current_user: dict = Depends(get_current_user),
) -> MobileBannerResponse:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.AREA,
    )
    actor_id = current_user.get("user_id")
    item = await MobileBannerService.update_banner(
        banner_id=banner_id,
        payload=payload.dict(exclude_unset=True),
        actor_id=actor_id,
    )
    return MobileBannerResponse(**item)


@mobile_banner_router.delete("/{banner_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_mobile_banner(
    banner_id: str = Path(..., description="Banner ID"),
    current_user: dict = Depends(get_current_user),
) -> Response:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.AREA,
    )
    await MobileBannerService.delete_banner(banner_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
