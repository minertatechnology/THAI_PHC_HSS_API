"""Service สำหรับ CRUD ข้อมูลดีเด่น + รูปภาพแนบ (ใบประกาศนียบัตร)"""

from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.repositories.osm_outstanding_repository import OsmOutstandingRepository
from app.models.osm_model import OsmOutstanding, OsmOutstandingImage
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OsmOutstandingService:
    _UPLOAD_ROOT = Path("uploads") / "outstanding-certificates"
    _MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB per image
    _MAX_IMAGES = 10

    # ────────────────── Permission helpers ──────────────────

    @classmethod
    def _assert_can_manage(
        cls,
        current_user: dict,
        target_osm_profile_id: str,
    ) -> None:
        """OSM จัดการได้เฉพาะข้อมูลตัวเอง / officer จัดการได้ทุกคน"""
        user_type = current_user.get("user_type")
        user_id = current_user.get("user_id")
        if user_type == "officer":
            return  # officer สามารถจัดการข้อมูลดีเด่นของทุกคนได้
        if user_type == "osm" and str(user_id) == str(target_osm_profile_id):
            return  # osm จัดการข้อมูลตัวเอง
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden_not_owner",
        )

    # ────────────────── LIST ──────────────────

    @classmethod
    async def list_by_osm(cls, osm_profile_id: str) -> List[Dict[str, Any]]:
        records = await OsmOutstandingRepository.list_by_osm_profile(osm_profile_id)
        return [cls._serialize(r) for r in records]

    # ────────────────── GET ──────────────────

    @classmethod
    async def get(cls, outstanding_id: str) -> Dict[str, Any]:
        record = await OsmOutstandingRepository.get_by_id(outstanding_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outstanding_not_found")
        return cls._serialize(record)

    # ────────────────── CREATE ──────────────────

    @classmethod
    async def create(
        cls,
        current_user: dict,
        osm_profile_id: str,
        award_year: int,
        *,
        award_level_id: Optional[str] = None,
        award_category_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        images: Optional[List[UploadFile]] = None,
    ) -> Dict[str, Any]:
        cls._assert_can_manage(current_user, osm_profile_id)
        actor_id = current_user.get("user_id")

        record = await OsmOutstandingRepository.create(
            osm_profile_id=osm_profile_id,
            award_year=award_year,
            created_by=actor_id,
            award_level_id=award_level_id,
            award_category_id=award_category_id,
            title=title,
            description=description,
        )

        # Upload images
        if images:
            image_entries = await cls._store_images(images)
            await OsmOutstandingRepository.add_images(str(record.id), image_entries)

        # Re-fetch with relations
        return await cls.get(str(record.id))

    # ────────────────── UPDATE ──────────────────

    @classmethod
    async def update(
        cls,
        current_user: dict,
        outstanding_id: str,
        *,
        award_year: Optional[int] = None,
        award_level_id: Optional[str] = None,
        award_category_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        record = await OsmOutstandingRepository.get_by_id_simple(outstanding_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outstanding_not_found")

        cls._assert_can_manage(current_user, str(record.osm_profile_id))
        actor_id = current_user.get("user_id")

        update_fields: Dict[str, Any] = {}
        if award_year is not None:
            update_fields["award_year"] = award_year
        if award_level_id is not None:
            update_fields["award_level_id"] = award_level_id
        if award_category_id is not None:
            update_fields["award_category_id"] = award_category_id
        if title is not None:
            update_fields["title"] = title
        if description is not None:
            update_fields["description"] = description

        if update_fields:
            await OsmOutstandingRepository.update(outstanding_id, actor_id, **update_fields)

        return await cls.get(outstanding_id)

    # ────────────────── DELETE ──────────────────

    @classmethod
    async def delete(
        cls,
        current_user: dict,
        outstanding_id: str,
    ) -> bool:
        record = await OsmOutstandingRepository.get_by_id_simple(outstanding_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outstanding_not_found")

        cls._assert_can_manage(current_user, str(record.osm_profile_id))
        actor_id = current_user.get("user_id")
        return await OsmOutstandingRepository.soft_delete(outstanding_id, actor_id)

    # ────────────────── IMAGES ──────────────────

    @classmethod
    async def add_images(
        cls,
        current_user: dict,
        outstanding_id: str,
        images: List[UploadFile],
    ) -> Dict[str, Any]:
        record = await OsmOutstandingRepository.get_by_id_simple(outstanding_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outstanding_not_found")

        cls._assert_can_manage(current_user, str(record.osm_profile_id))

        # Check total images
        existing = await OsmOutstandingRepository.get_images(outstanding_id)
        if len(existing) + len(images) > cls._MAX_IMAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"max_images_exceeded (max {cls._MAX_IMAGES})",
            )

        image_entries = await cls._store_images(images, start_sort=len(existing))
        await OsmOutstandingRepository.add_images(outstanding_id, image_entries)
        return await cls.get(outstanding_id)

    @classmethod
    async def delete_image(
        cls,
        current_user: dict,
        outstanding_id: str,
        image_id: str,
    ) -> Dict[str, Any]:
        record = await OsmOutstandingRepository.get_by_id_simple(outstanding_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outstanding_not_found")

        cls._assert_can_manage(current_user, str(record.osm_profile_id))
        deleted = await OsmOutstandingRepository.delete_image(image_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="image_not_found")
        return await cls.get(outstanding_id)

    # ────────────────── Image storage helpers ──────────────────

    @classmethod
    async def _store_images(
        cls,
        uploads: List[UploadFile],
        start_sort: int = 0,
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for idx, upload in enumerate(uploads):
            stored_path = await cls._store_image(upload)
            entries.append({
                "image_url": stored_path,
                "sort_order": start_sort + idx,
            })
        return entries

    @classmethod
    async def _store_image(cls, upload: UploadFile) -> str:
        if upload is None or not getattr(upload, "filename", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image")
        content_type = (upload.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image_type")

        raw_bytes = await upload.read()
        if len(raw_bytes) > cls._MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="image_too_large",
            )
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

    # ────────────────── Serialization ──────────────────

    @classmethod
    def _serialize(cls, record: OsmOutstanding) -> Dict[str, Any]:
        images_list = []
        if hasattr(record, "images") and record.images:
            for img in record.images:
                images_list.append({
                    "id": str(img.id),
                    "image_url": img.image_url,
                    "sort_order": img.sort_order,
                    "caption": img.caption,
                })

        result: Dict[str, Any] = {
            "id": str(record.id),
            "osm_profile_id": str(record.osm_profile_id),
            "award_year": record.award_year,
            "award_level_id": str(record.award_level_id) if record.award_level_id else None,
            "award_level_name": None,
            "award_category_id": str(record.award_category_id) if record.award_category_id else None,
            "award_category_name": None,
            "title": record.title,
            "description": record.description,
            "images": images_list,
            "created_by": str(record.created_by) if record.created_by else None,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

        # Resolve relation names when prefetched
        try:
            if record.award_level:
                result["award_level_name"] = getattr(record.award_level, "name", None)
        except Exception:
            pass
        try:
            if record.award_category:
                result["award_category_name"] = getattr(record.award_category, "name", None)
        except Exception:
            pass

        return result
