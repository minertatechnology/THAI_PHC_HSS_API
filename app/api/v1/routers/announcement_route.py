from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.middleware.mock_auth import get_mock_current_user
from app.services.mock_data_store import MockDataStore


announcement_router = APIRouter(prefix="/announcements", tags=["announcements"])


@announcement_router.get("")
async def list_announcements(
    page: int = 1,
    perPage: int = 10,
    current_user=Depends(get_mock_current_user),
):
    user_id = current_user["user"]["id"]
    result = MockDataStore.list_announcements(page, perPage, user_id)
    total_pages = (result["total"] + perPage - 1) // perPage if perPage else 1
    return {
        "success": True,
        "message": "Success",
        "items": result["items"],
        "page": page,
        "perPage": perPage,
        "total": result["total"],
        "totalPages": total_pages,
    }


@announcement_router.post("/{announcement_id}/read")
async def mark_read(announcement_id: str, current_user=Depends(get_mock_current_user)):
    user_id = current_user["user"]["id"]
    result = MockDataStore.mark_announcement_read(announcement_id, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=result.get("status_code", status.HTTP_400_BAD_REQUEST), detail=result.get("message"))
    return result


@announcement_router.post("/read-all")
async def mark_all_read(current_user=Depends(get_mock_current_user)):
    user_id = current_user["user"]["id"]
    result = MockDataStore.mark_all_announcements_read(user_id)
    if not result.get("success"):
        raise HTTPException(status_code=result.get("status_code", status.HTTP_400_BAD_REQUEST), detail=result.get("message"))
    return result
