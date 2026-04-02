from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.middleware.mock_auth import get_mock_current_user
from app.services.mock_data_store import MockDataStore


admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _ensure_success(result: Dict[str, object]):
    if result.get("success"):
        return result
    raise HTTPException(status_code=result.get("status_code", status.HTTP_400_BAD_REQUEST), detail=result.get("message"))


# Groups -----------------------------------------------------------------
@admin_router.get("/groups")
async def list_groups(current_user=Depends(get_mock_current_user)):
    items = MockDataStore.list_groups()
    return {"success": True, "message": "Success", "items": items}


@admin_router.post("/groups")
async def create_group(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.create_group(payload))


@admin_router.put("/groups/{group_id}")
async def update_group(group_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.update_group(group_id, payload))


@admin_router.delete("/groups/{group_id}")
async def delete_group(group_id: str, current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.delete_group(group_id))


# Main menus --------------------------------------------------------------
@admin_router.get("/menus/main")
async def list_main_menus(current_user=Depends(get_mock_current_user)):
    items = MockDataStore.list_main_menus()
    return {"success": True, "message": "Success", "items": items}


@admin_router.post("/menus/main")
async def create_main_menu(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.create_main_menu(payload))


@admin_router.put("/menus/main/{menu_id}")
async def update_main_menu(menu_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.update_main_menu(menu_id, payload))


@admin_router.delete("/menus/main/{menu_id}")
async def delete_main_menu(menu_id: str, current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.delete_main_menu(menu_id))


# Sub menus ---------------------------------------------------------------
@admin_router.get("/menus/sub")
async def list_sub_menus(mainMenuId: Optional[str] = None, current_user=Depends(get_mock_current_user)):
    items = MockDataStore.list_sub_menus(mainMenuId)
    return {"success": True, "message": "Success", "items": items}


@admin_router.post("/menus/sub")
async def create_sub_menu(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.create_sub_menu(payload))


@admin_router.put("/menus/sub/{sub_menu_id}")
async def update_sub_menu(sub_menu_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.update_sub_menu(sub_menu_id, payload))


@admin_router.delete("/menus/sub/{sub_menu_id}")
async def delete_sub_menu(sub_menu_id: str, current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.delete_sub_menu(sub_menu_id))


# Menu assignees ---------------------------------------------------------
@admin_router.get("/menu-assignees")
async def list_menu_assignees(menuId: str = Query(...), current_user=Depends(get_mock_current_user)):
    items = MockDataStore.list_menu_assignees(menuId)
    return {"success": True, "message": "Success", "items": items}


@admin_router.post("/menu-assignees")
async def add_menu_assignee(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    menu_id = payload.get("menuId")
    username = payload.get("username")
    if not menu_id or not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="menuId_and_username_required")
    return _ensure_success(MockDataStore.add_menu_assignee(menu_id, username))


@admin_router.delete("/menu-assignees")
async def remove_menu_assignee(menuId: str = Query(...), username: str = Query(...), current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.remove_menu_assignee(menuId, username))


# Roles & permissions -----------------------------------------------------
@admin_router.get("/roles")
async def list_roles(current_user=Depends(get_mock_current_user)):
    items = MockDataStore.list_roles()
    return {"success": True, "message": "Success", "items": items}


@admin_router.get("/roles/{role_id}/permissions")
async def role_permissions(role_id: str, current_user=Depends(get_mock_current_user)):
    result = MockDataStore.get_role_permissions(role_id)
    return _ensure_success(result)


@admin_router.put("/roles/{role_id}/permissions")
async def update_role_permissions(role_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    permissions = payload.get("permissions", [])
    return _ensure_success(MockDataStore.update_role_permissions(role_id, permissions))


# System users ------------------------------------------------------------
@admin_router.get("/users")
async def list_users(page: int = 1, pageSize: int = 20, current_user=Depends(get_mock_current_user)):
    return MockDataStore.list_users(page, pageSize)


@admin_router.post("/users")
async def create_user(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    return _ensure_success(MockDataStore.create_user(payload))


@admin_router.put("/users/{user_id}")
async def update_user(user_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.update_user(user_id, payload)
    return _ensure_success(result)


@admin_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user=Depends(get_mock_current_user)):
    result = MockDataStore.delete_user(user_id)
    return _ensure_success(result)
