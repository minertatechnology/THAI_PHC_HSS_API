from __future__ import annotations

import asyncio
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.models.mobile_banner_model import MobileBanner
from app.cache.redis_client import cache_delete_pattern


class MobileBannerService:
    VALID_PLATFORMS = {"android", "ios", "web"}
    DEFAULT_PAGE_LIMIT = 20
    MAX_PAGE_LIMIT = 100
    _UPLOAD_ROOT = Path("uploads") / "mobile-banners"
    _MAX_FILE_BYTES = 10 * 1024 * 1024

    # ---------------------------- public APIs ----------------------------

    @classmethod
    async def list_banners(
        cls,
        *,
        page: int = 1,
        limit: int = DEFAULT_PAGE_LIMIT,
        include_inactive: bool = False,
        platform: str | None = None,
    ) -> dict[str, Any]:
        valid_page = max(1, page)
        clean_limit = min(max(1, limit), cls.MAX_PAGE_LIMIT)
        normalized_platform = cls._normalize_platform(platform) if platform else None

        query = MobileBanner.all()
        if not include_inactive:
            query = query.filter(is_active=True)
        rows = await query.order_by("order_index", "created_at").all()
        filtered = [row for row in rows if cls._match_platform(row, normalized_platform)]
        total = len(filtered)
        offset = (valid_page - 1) * clean_limit
        paginated = filtered[offset : offset + clean_limit]
        total_pages = (total + clean_limit - 1) // clean_limit if total and clean_limit else 0

        return {
            "items": [cls._serialize(row) for row in paginated],
            "pagination": {
                "page": valid_page,
                "limit": clean_limit,
                "total": total,
                "pages": total_pages,
            },
        }

    @classmethod
    async def list_visible_banners(
        cls,
        *,
        platform: str | None = None,
        only_active_window: bool = True,
    ) -> list[dict[str, Any]]:
        normalized_platform = cls._normalize_platform(platform) if platform else None
        query = MobileBanner.filter(is_active=True)
        rows = await query.order_by("order_index", "created_at")
        now = datetime.now(timezone.utc)
        visible: list[dict[str, Any]] = []
        for row in rows:
            if normalized_platform and not cls._match_platform(row, normalized_platform):
                continue
            if only_active_window and not cls._is_within_schedule(row, now):
                continue
            visible.append(cls._serialize(row))
        return visible

    @classmethod
    async def get_banner(cls, banner_id: str) -> dict[str, Any]:
        row = await cls._get_existing(banner_id)
        return cls._serialize(row)

    @classmethod
    async def create_banner(
        cls,
        *,
        payload: Mapping[str, Any],
        actor_id: str | None,
    ) -> dict[str, Any]:
        actor_clean = cls._normalize_actor(actor_id)
        normalized_payload = cls._normalize_payload(payload, partial=False)
        row = await MobileBanner.create(
            **normalized_payload,
            created_by=actor_clean,
            updated_by=actor_clean,
        )
        await cache_delete_pattern("mobile:banners:current:*")
        return cls._serialize(row)

    @classmethod
    async def update_banner(
        cls,
        banner_id: str,
        *,
        payload: Mapping[str, Any],
        actor_id: str | None,
    ) -> dict[str, Any]:
        row = await cls._get_existing(banner_id)
        actor_clean = cls._normalize_actor(actor_id)
        updates = cls._normalize_payload(payload, partial=True, existing=row)
        for field, value in updates.items():
            setattr(row, field, value)
        row.updated_by = actor_clean
        await row.save()
        await cache_delete_pattern("mobile:banners:current:*")
        await row.refresh_from_db()
        return cls._serialize(row)

    @classmethod
    async def delete_banner(cls, banner_id: str) -> None:
        row = await cls._get_existing(banner_id)
        await row.delete()
        await cache_delete_pattern("mobile:banners:current:*")

    @classmethod
    async def upload_banner_image(cls, *, file: UploadFile) -> str:
        stored_path = await cls._store_image(file)
        return stored_path

    # ---------------------------- helpers ----------------------------

    @classmethod
    async def _get_existing(cls, banner_id: str) -> MobileBanner:
        row = await MobileBanner.filter(id=banner_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mobile_banner_not_found")
        return row

    @classmethod
    def _normalize_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        partial: bool,
        existing: MobileBanner | None = None,
    ) -> MutableMapping[str, Any]:
        normalized: MutableMapping[str, Any] = {}
        if not partial or "title" in payload:
            normalized["title"] = cls._normalize_required_text(payload.get("title"), field="title", max_length=255)
        if not partial or "subtitle" in payload:
            normalized["subtitle"] = cls._normalize_optional_text(payload.get("subtitle"))
        if not partial or "image_url" in payload:
            normalized["image_url"] = cls._normalize_required_text(payload.get("image_url"), field="image_url", max_length=1024)
        if not partial or "target_url" in payload:
            normalized["target_url"] = cls._normalize_optional_text(payload.get("target_url"), max_length=1024)
        if not partial or "order_index" in payload:
            normalized["order_index"] = cls._normalize_order_index(payload.get("order_index"))
        if not partial or "platforms" in payload:
            normalized["platforms"] = cls._normalize_platforms(payload.get("platforms"))
        if not partial or "metadata" in payload:
            normalized["metadata"] = cls._normalize_metadata(payload.get("metadata"))
        if not partial or "starts_at" in payload:
            normalized["starts_at"] = cls._normalize_datetime(payload.get("starts_at"))
        if not partial or "ends_at" in payload:
            normalized["ends_at"] = cls._normalize_datetime(payload.get("ends_at"))
        if not partial or "is_active" in payload:
            normalized["is_active"] = bool(payload.get("is_active", True))

        effective_starts = normalized.get("starts_at")
        if effective_starts is None and existing is not None:
            effective_starts = existing.starts_at
        effective_ends = normalized.get("ends_at")
        if effective_ends is None and existing is not None:
            effective_ends = existing.ends_at
        cls._validate_schedule(effective_starts, effective_ends)
        return normalized

    @staticmethod
    def _normalize_required_text(value: Any, *, field: str, max_length: int | None = None) -> str:
        text = str(value or "").strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field}_required")
        if max_length is not None and len(text) > max_length:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field}_too_long")
        return text

    @staticmethod
    def _normalize_optional_text(value: Any, *, max_length: int | None = None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if max_length is not None and len(text) > max_length:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="text_too_long")
        return text

    @staticmethod
    def _normalize_order_index(value: Any) -> int:
        if value is None:
            return 0
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="order_index_invalid") from exc
        if number < 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="order_index_must_be_positive")
        return number

    @classmethod
    def _normalize_platforms(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="platforms_must_be_list")
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            token = str(raw or "").strip().lower()
            if not token:
                continue
            if token not in cls.VALID_PLATFORMS:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"invalid_platform:{token}")
            if token not in seen:
                normalized.append(token)
                seen.add(token)
        return normalized

    @staticmethod
    def _normalize_metadata(value: Any) -> dict | None:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="metadata_must_be_object")
        return dict(value)

    @staticmethod
    def _normalize_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_datetime")

    @staticmethod
    def _validate_schedule(start: datetime | None, end: datetime | None) -> None:
        if start and end and end <= start:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_schedule_range")

    @staticmethod
    def _normalize_actor(actor_id: str | None) -> str:
        token = str(actor_id or "").strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")
        return token

    @classmethod
    def _match_platform(cls, row: MobileBanner, platform: str | None) -> bool:
        if not platform:
            return True
        allowed = [str(item).strip().lower() for item in (row.platforms or []) if item]
        if not allowed:
            return True
        return platform in allowed

    @staticmethod
    def _is_within_schedule(row: MobileBanner, now: datetime) -> bool:
        starts_at = row.starts_at
        ends_at = row.ends_at
        if starts_at and starts_at > now:
            return False
        if ends_at and ends_at < now:
            return False
        return True

    @classmethod
    def _serialize(cls, row: MobileBanner) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "title": row.title,
            "subtitle": row.subtitle,
            "image_url": row.image_url,
            "target_url": row.target_url,
            "order_index": row.order_index,
            "platforms": list(row.platforms or []),
            "metadata": row.metadata or None,
            "starts_at": row.starts_at,
            "ends_at": row.ends_at,
            "is_active": bool(row.is_active),
            "created_by": str(row.created_by) if row.created_by else None,
            "updated_by": str(row.updated_by) if row.updated_by else None,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    def _normalize_platform(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = str(value).strip().lower()
        if not token:
            return None
        if token not in cls.VALID_PLATFORMS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"invalid_platform:{token}")
        return token

    @classmethod
    async def _store_image(cls, upload: UploadFile) -> str:
        if upload is None or not getattr(upload, "filename", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image")
        content_type = (upload.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image_type")

        raw_bytes = await upload.read()
        if not raw_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_image")
        if len(raw_bytes) > cls._MAX_FILE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="image_too_large")

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
