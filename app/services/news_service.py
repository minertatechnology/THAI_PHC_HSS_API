from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Iterable, List, Sequence
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.models.news_model import NewsArticle
from app.cache.redis_client import cache_delete_pattern


class NewsService:
    @classmethod
    async def delete_news(cls, *, news_id: str, actor_id: str) -> None:
        from datetime import datetime
        target = await NewsArticle.filter(id=news_id, deleted_at__isnull=True).first()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="news_not_found")
        if not actor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")
        target.deleted_at = datetime.utcnow()
        target.updated_by = actor_id
        await target.save()
        await cache_delete_pattern("news:list:*")
    _UPLOAD_ROOT = Path("uploads") / "news"
    _MAX_IMAGES = 5
    _MAX_FILE_BYTES = 20 * 1024 * 1024
    _DEFAULT_LIST_LIMIT = 20

    @classmethod
    async def create_news(
        cls,
        *,
        title: str,
        department: str,
        content_html: str,
        actor_id: str,
        images: Sequence[UploadFile] | None = None,
        platforms: List[str] | None = None,
    ) -> dict:
        title_clean = (title or "").strip()
        department_clean = (department or "").strip()
        content_clean = (content_html or "").strip()
        actor_clean = (actor_id or "").strip()

        if not actor_clean:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")
        if not title_clean:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="title_required")
        if not department_clean:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="department_required")
        if not content_clean:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="content_required")

        stored_paths: List[str] = []
        upload_items: Iterable[UploadFile] = images or []
        upload_list = [
            item
            for item in upload_items
            if item and getattr(item, "filename", None)
        ]
        if len(upload_list) > cls._MAX_IMAGES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="too_many_images")

        try:
            for upload in upload_list:
                stored_path = await cls._store_image(upload)
                stored_paths.append(stored_path)
        except HTTPException:
            await cls._cleanup_files(stored_paths)
            raise

        platforms_clean = platforms or []
        row = await NewsArticle.create(
            title=title_clean,
            department=department_clean,
            content_html=content_clean,
            image_urls=stored_paths,
            platforms=platforms_clean,
            created_by=actor_clean,
            updated_by=actor_clean,
        )
        await cache_delete_pattern("news:list:*")
        return cls._serialize(row)

    @classmethod
    async def update_news(
        cls,
        *,
        news_id: str,
        title: str,
        department: str,
        content_html: str,
        actor_id: str,
        images: Sequence[UploadFile] | None = None,
        existing_image_urls: Sequence[str] | None = None,
        platforms: List[str] | None = None,
    ) -> dict:
        target = await NewsArticle.filter(id=news_id, deleted_at__isnull=True).first()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="news_not_found")

        title_clean = (title or "").strip()
        department_clean = (department or "").strip()
        content_clean = (content_html or "").strip()
        actor_clean = (actor_id or "").strip()

        if not actor_clean:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")
        if not title_clean:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="title_required")
        if not department_clean:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="department_required")
        if not content_clean:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="content_required")

        current_images: List[str] = list(target.image_urls or [])
        retained_images = cls._normalize_existing_image_urls(existing_image_urls, current=current_images)

        uploaded_items: Iterable[UploadFile] | None = images
        upload_list: List[UploadFile] = []
        if uploaded_items is not None:
            upload_list = [item for item in uploaded_items if item and getattr(item, "filename", None)]

        if len(retained_images) + len(upload_list) > cls._MAX_IMAGES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="too_many_images")

        new_image_paths: List[str] = []
        if upload_list:
            try:
                for upload in upload_list:
                    stored = await cls._store_image(upload)
                    new_image_paths.append(stored)
            except HTTPException:
                await cls._cleanup_files(new_image_paths)
                raise

        final_images = retained_images + new_image_paths
        target.image_urls = final_images

        platforms_clean = platforms or []
        target.title = title_clean
        target.department = department_clean
        target.content_html = content_clean
        target.platforms = platforms_clean
        target.updated_by = actor_clean
        await target.save()
        await cache_delete_pattern("news:list:*")

        removed_images = [path for path in current_images if path not in retained_images]
        if removed_images:
            await cls._cleanup_files(removed_images)

        return cls._serialize(target)

    @classmethod
    async def list_news(
        cls,
        *,
        limit: int | None = None,
        offset: int = 0,
        platform: str | None = None,
    ) -> List[dict]:
        applied_limit = limit or cls._DEFAULT_LIST_LIMIT
        query = (
            NewsArticle
            .filter(deleted_at__isnull=True)
            .order_by("-created_at", "-id")
        )
        if platform:
            query = query.filter(platforms__contains=[platform])
        if offset:
            query = query.offset(offset)
        if applied_limit:
            query = query.limit(applied_limit)
        rows = await query
        return [cls._serialize(row) for row in rows]

    @classmethod
    async def _store_image(cls, upload: UploadFile) -> str:
        if upload is None or not getattr(upload, "filename", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image")
        content_type = (upload.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image_type")

        raw_bytes = await upload.read()
        if len(raw_bytes) > cls._MAX_FILE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="image_too_large")
        if not raw_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_image")

        suffix = cls._resolve_suffix(upload.filename, content_type)
        filename = f"{uuid4()}{suffix}"
        cls._ensure_upload_path()
        destination = cls._UPLOAD_ROOT / filename
        await asyncio.to_thread(destination.write_bytes, raw_bytes)
        await upload.close()
        return str(destination.as_posix())

    @staticmethod
    def _resolve_suffix(original_name: str | None, content_type: str) -> str:
        if original_name:
            suffix = Path(original_name).suffix.lower()
            if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
                return suffix
        guessed = mimetypes.guess_extension(content_type) or ".jpg"
        normalized = guessed.lower()
        if normalized == ".jpe":
            normalized = ".jpg"
        return normalized

    @classmethod
    def _ensure_upload_path(cls) -> None:
        cls._UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    @classmethod
    async def _cleanup_files(cls, stored_paths: Sequence[str]) -> None:
        for stored in stored_paths:
            if not stored:
                continue
            path = Path(stored)
            try:
                await asyncio.to_thread(path.unlink)
            except FileNotFoundError:
                pass
            except OSError:
                pass

    @classmethod
    def _normalize_existing_image_urls(
        cls,
        requested: Sequence[str] | None,
        *,
        current: Sequence[str],
    ) -> List[str]:
        current_list = [str(item) for item in current if item]
        current_set = set(current_list)
        if requested is None:
            return list(current_list)

        normalized: List[str] = []
        seen: set[str] = set()
        for raw in requested:
            token = str(raw or "").strip()
            if not token:
                continue
            if token not in current_set:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_existing_image")
            if token in seen:
                continue
            normalized.append(token)
            seen.add(token)
        return normalized

    @staticmethod
    def _serialize(row: NewsArticle) -> dict:
        return {
            "id": str(row.id),
            "title": row.title,
            "department": row.department,
            "content_html": row.content_html,
            "image_urls": list(row.image_urls or []),
            "platforms": list(row.platforms or []),
            "created_by": str(row.created_by) if row.created_by else None,
            "updated_by": str(row.updated_by) if row.updated_by else None,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
