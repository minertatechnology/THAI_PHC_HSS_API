from __future__ import annotations
from datetime import datetime
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status

from app.api.middleware.middleware import get_current_user
from app.api.v1.schemas.news_schema import NewsResponse
from app.services.news_service import NewsService
from app.services.permission_service import PermissionService
from app.models.enum_models import AdministrativeLevelEnum
from app.cache.redis_client import cache_get, cache_set

news_router = APIRouter(prefix="/news", tags=["news"])


def _coerce_existing_image_urls_field(values: Optional[List[str]]) -> Optional[List[str]]:
    """Normalize existing_image_urls coming from multipart (JSON string or repeated fields)."""
    if values is None:
        return None
    if not values:
        return []

    def _normalize(seq: List[str]) -> List[str]:
        normalized: List[str] = []
        for raw in seq:
            token = str(raw or "").strip()
            if token:
                normalized.append(token)
        return normalized

    if len(values) == 1:
        candidate = (values[0] or "").strip()
        if not candidate:
            return []
        if candidate.startswith("["):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_existing_image_format") from exc
            if parsed is None:
                return []
            if not isinstance(parsed, list):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_existing_image_format")
            return _normalize([str(item) for item in parsed])

    return _normalize(values)

async def _list_news_impl(
    limit: int = Query(20, ge=1, le=100, description="จำนวนรายการสูงสุดที่ต้องการ"),
    offset: int = Query(0, ge=0, description="จำนวนรายการที่ข้ามไปก่อนหน้า"),
    platform: str | None = Query(None, description="กรองตามแพลตฟอร์ม เช่น ThaiPHC, SmartOSM"),
    current_user: dict = Depends(get_current_user),
) -> List[NewsResponse]:
    # Dependency ensures requester already authenticated; news is globally visible for signed-in users.
    _ = current_user
    cache_key = f"news:list:{limit}:{offset}:{platform}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return [NewsResponse(**item) for item in cached]
    items = await NewsService.list_news(limit=limit, offset=offset, platform=platform)
    await cache_set(cache_key, items, 300)  # 5 minutes
    return [NewsResponse(**item) for item in items]


@news_router.get("/", response_model=List[NewsResponse])
async def list_news_slash(
    limit: int = Query(20, ge=1, le=100, description="จำนวนรายการสูงสุดที่ต้องการ"),
    offset: int = Query(0, ge=0, description="จำนวนรายการที่ข้ามไปก่อนหน้า"),
    platform: str | None = Query(None, description="กรองตามแพลตฟอร์ม เช่น ThaiPHC, SmartOSM"),
    current_user: dict = Depends(get_current_user),
) -> List[NewsResponse]:
    return await _list_news_impl(limit=limit, offset=offset, platform=platform, current_user=current_user)


@news_router.get("", response_model=List[NewsResponse], include_in_schema=False)
async def list_news(
    limit: int = Query(20, ge=1, le=100, description="จำนวนรายการสูงสุดที่ต้องการ"),
    offset: int = Query(0, ge=0, description="จำนวนรายการที่ข้ามไปก่อนหน้า"),
    platform: str | None = Query(None, description="กรองตามแพลตฟอร์ม เช่น ThaiPHC, SmartOSM"),
    current_user: dict = Depends(get_current_user),
) -> List[NewsResponse]:
    """Allow /api/v1/news without trailing slash to avoid proxy redirects."""
    return await _list_news_impl(limit=limit, offset=offset, platform=platform, current_user=current_user)


@news_router.post("/", response_model=NewsResponse, status_code=status.HTTP_201_CREATED)
async def create_news(
    title: str = Form(..., description="หัวข้อข่าวสาร"),
    department: str = Form(..., description="หน่วยงานหรือแผนกผู้ประกาศ"),
    content: str = Form(..., description="เนื้อหาข่าวสาร (รองรับ HTML)"),
    platforms: Optional[List[str]] = Form(default=None, description="แพลตฟอร์มที่แสดงข่าว (SmartOSM, ThaiPHC)"),
    images: Optional[List[UploadFile]] = File(default=None, description="รูปภาพแนบ (สูงสุด 5 รูป รูปละไม่เกิน 20MB)"),
    current_user: dict = Depends(get_current_user),
) -> NewsResponse:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.COUNTRY,
    )
    actor_id = current_user.get("user_id")
    item = await NewsService.create_news(
        title=title,
        department=department,
        content_html=content,
        actor_id=actor_id,
        images=images,
        platforms=platforms,
    )
    return NewsResponse(**item)


@news_router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: str = Path(..., description="ID ของข่าวสาร"),
    title: str = Form(..., description="หัวข้อข่าวสาร"),
    department: str = Form(..., description="หน่วยงานหรือแผนกผู้ประกาศ"),
    content: str = Form(..., description="เนื้อหาข่าวสาร (รองรับ HTML)"),
    platforms: Optional[List[str]] = Form(default=None, description="แพลตฟอร์มที่แสดงข่าว (SmartOSM, ThaiPHC)"),
    images: Optional[List[UploadFile]] = File(default=None, description="รูปภาพแนบ (สูงสุด 5 รูป รูปละไม่เกิน 20MB)"),
    existing_image_urls: Optional[List[str]] = Form(
        default=None,
        description="ระบุ URL รูปเดิมที่ต้องการเก็บไว้ สามารถส่งเป็น JSON array หรือส่งซ้ำหลายฟิลด์ได้",
    ),
    current_user: dict = Depends(get_current_user),
) -> NewsResponse:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.COUNTRY,
    )
    actor_id = current_user.get("user_id")
    normalized_existing = _coerce_existing_image_urls_field(existing_image_urls)
    item = await NewsService.update_news(
        news_id=news_id,
        title=title,
        department=department,
        content_html=content,
        actor_id=actor_id,
        images=images,
        existing_image_urls=normalized_existing,
        platforms=platforms,
    )
    return NewsResponse(**item)


# DELETE /api/v1/news/{news_id}
@news_router.delete("/{news_id}", status_code=204)
async def delete_news(
    news_id: str = Path(..., description="ID ของข่าวสาร"),
    current_user: dict = Depends(get_current_user),
):
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.COUNTRY,
    )
    actor_id = current_user.get("user_id")
    await NewsService.delete_news(news_id=news_id, actor_id=actor_id)
    return None
