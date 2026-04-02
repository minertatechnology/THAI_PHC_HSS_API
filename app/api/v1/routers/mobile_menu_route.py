from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.middleware.middleware import get_current_user
from app.api.v1.schemas.mobile_menu_schema import (
    MobileMenuCreate,
    MobileMenuResponse,
    MobileMenuUpdate,
)
from app.services.mobile_menu_service import MobileMenuService
from app.services.permission_service import PermissionService
from app.cache.redis_client import cache_get, cache_set


mobile_menu_router = APIRouter(prefix="/mobile/menus", tags=["mobile-menus"])


@mobile_menu_router.get("", response_model=List[MobileMenuResponse])
async def list_mobile_menus(
    include_inactive: bool = Query(default=False, description="Include menus that are currently disabled."),
    current_user: dict = Depends(get_current_user),
) -> List[MobileMenuResponse]:
    await PermissionService.require_officer(current_user)
    items = await MobileMenuService.list_menus(include_inactive=include_inactive)
    return [MobileMenuResponse(**item) for item in items]


@mobile_menu_router.get("/current", response_model=List[MobileMenuResponse])
async def list_current_mobile_menus(
    platform: Optional[str] = Query(default=None, description="Filter menus for a platform (android/ios/web)."),
    current_user: dict = Depends(get_current_user),
) -> List[MobileMenuResponse]:
    user_type = current_user.get("user_type")
    cache_key = f"mobile:menus:current:{user_type}:{platform}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return [MobileMenuResponse(**item) for item in cached]
    items = await MobileMenuService.list_visible_menus(
        user_type=user_type, platform=platform,
    )
    await cache_set(cache_key, items, 21600)  # 6 hours
    return [MobileMenuResponse(**item) for item in items]


@mobile_menu_router.post("", response_model=MobileMenuResponse, status_code=status.HTTP_201_CREATED)
async def create_mobile_menu(
    payload: MobileMenuCreate,
    current_user: dict = Depends(get_current_user),
) -> MobileMenuResponse:
    await PermissionService.require_officer(current_user)
    actor_id = current_user.get("user_id")
    item = await MobileMenuService.create_menu(payload=payload.dict(), actor_id=actor_id)
    return MobileMenuResponse(**item)


@mobile_menu_router.put("/{menu_id}", response_model=MobileMenuResponse)
async def update_mobile_menu(
    payload: MobileMenuUpdate,
    menu_id: str = Path(..., description="Mobile menu ID"),
    current_user: dict = Depends(get_current_user),
) -> MobileMenuResponse:
    await PermissionService.require_officer(current_user)
    actor_id = current_user.get("user_id")
    item = await MobileMenuService.update_menu(
        menu_id=menu_id,
        payload=payload.dict(exclude_unset=True),
        actor_id=actor_id,
    )
    return MobileMenuResponse(**item)


@mobile_menu_router.delete("/{menu_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_mobile_menu(
    menu_id: str = Path(..., description="Mobile menu ID"),
    current_user: dict = Depends(get_current_user),
) -> Response:
    await PermissionService.require_officer(current_user)
    await MobileMenuService.delete_menu(menu_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
