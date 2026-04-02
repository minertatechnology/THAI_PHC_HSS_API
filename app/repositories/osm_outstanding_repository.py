from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from app.models.osm_model import OsmOutstanding, OsmOutstandingImage
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OsmOutstandingRepository:
    """Repository สำหรับ CRUD ข้อมูลดีเด่น (OsmOutstanding) + รูปภาพแนบ (OsmOutstandingImage)"""

    # ──────────────────────────  READ  ──────────────────────────

    @staticmethod
    async def list_by_osm_profile(osm_profile_id: str) -> List[OsmOutstanding]:
        """ดึงข้อมูลดีเด่นทั้งหมดของ OSM profile (ไม่รวม soft-deleted)"""
        try:
            return await (
                OsmOutstanding
                .filter(osm_profile_id=osm_profile_id, deleted_at__isnull=True)
                .prefetch_related("award_level", "award_category", "images")
                .order_by("-award_year", "-created_at")
            )
        except Exception as exc:
            logger.error("Error listing outstandings for osm %s: %s", osm_profile_id, exc)
            raise

    @staticmethod
    async def get_by_id(outstanding_id: str) -> Optional[OsmOutstanding]:
        """ดึงข้อมูลดีเด่นตาม ID พร้อม images"""
        try:
            return await (
                OsmOutstanding
                .filter(id=outstanding_id, deleted_at__isnull=True)
                .prefetch_related("award_level", "award_category", "images")
                .first()
            )
        except Exception as exc:
            logger.error("Error retrieving outstanding %s: %s", outstanding_id, exc)
            raise

    @staticmethod
    async def get_by_id_simple(outstanding_id: str) -> Optional[OsmOutstanding]:
        """ดึงข้อมูลดีเด่นตาม ID ไม่ prefetch"""
        try:
            return await (
                OsmOutstanding
                .filter(id=outstanding_id, deleted_at__isnull=True)
                .first()
            )
        except Exception as exc:
            logger.error("Error retrieving outstanding (simple) %s: %s", outstanding_id, exc)
            raise

    # ──────────────────────────  CREATE  ──────────────────────────

    @staticmethod
    async def create(
        osm_profile_id: str,
        award_year: int,
        created_by: str,
        *,
        award_level_id: Optional[str] = None,
        award_category_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> OsmOutstanding:
        try:
            payload: Dict[str, Any] = {
                "osm_profile_id": osm_profile_id,
                "award_year": award_year,
                "created_by": created_by,
            }
            if award_level_id:
                payload["award_level_id"] = award_level_id
            if award_category_id:
                payload["award_category_id"] = award_category_id
            if title is not None:
                payload["title"] = title
            if description is not None:
                payload["description"] = description

            record = await OsmOutstanding.create(**payload)
            return record
        except Exception as exc:
            logger.error("Error creating outstanding for osm %s: %s", osm_profile_id, exc)
            raise

    # ──────────────────────────  UPDATE  ──────────────────────────

    @staticmethod
    async def update(
        outstanding_id: str,
        updated_by: str,
        **fields: Any,
    ) -> bool:
        """อัปเดตฟิลด์ที่ส่งมา (ไม่รวม images)"""
        try:
            allowed = {"award_level_id", "award_category_id", "award_year", "title", "description"}
            update_payload: Dict[str, Any] = {
                k: v for k, v in fields.items() if k in allowed and v is not None
            }
            update_payload["updated_by"] = updated_by
            update_payload["updated_at"] = datetime.datetime.utcnow()
            updated = await (
                OsmOutstanding
                .filter(id=outstanding_id, deleted_at__isnull=True)
                .update(**update_payload)
            )
            return bool(updated)
        except Exception as exc:
            logger.error("Error updating outstanding %s: %s", outstanding_id, exc)
            raise

    # ──────────────────────────  DELETE (soft)  ──────────────────────────

    @staticmethod
    async def soft_delete(outstanding_id: str, deleted_by: str) -> bool:
        try:
            updated = await (
                OsmOutstanding
                .filter(id=outstanding_id, deleted_at__isnull=True)
                .update(
                    deleted_at=datetime.datetime.utcnow(),
                    updated_by=deleted_by,
                    updated_at=datetime.datetime.utcnow(),
                )
            )
            return bool(updated)
        except Exception as exc:
            logger.error("Error soft-deleting outstanding %s: %s", outstanding_id, exc)
            raise

    # ──────────────────────────  IMAGES  ──────────────────────────

    @staticmethod
    async def add_images(
        outstanding_id: str,
        image_entries: List[Dict[str, Any]],
    ) -> List[OsmOutstandingImage]:
        """เพิ่มรูปภาพแนบให้ outstanding record"""
        created: List[OsmOutstandingImage] = []
        try:
            for idx, entry in enumerate(image_entries):
                img = await OsmOutstandingImage.create(
                    id=uuid4(),
                    outstanding_id=outstanding_id,
                    image_url=entry["image_url"],
                    sort_order=entry.get("sort_order", idx),
                    caption=entry.get("caption"),
                )
                created.append(img)
            return created
        except Exception as exc:
            logger.error("Error adding images to outstanding %s: %s", outstanding_id, exc)
            raise

    @staticmethod
    async def replace_images(
        outstanding_id: str,
        image_entries: List[Dict[str, Any]],
    ) -> List[OsmOutstandingImage]:
        """ลบรูปเดิมทั้งหมดแล้วแทนที่ด้วยรูปใหม่"""
        try:
            await OsmOutstandingImage.filter(outstanding_id=outstanding_id).delete()
            return await OsmOutstandingRepository.add_images(outstanding_id, image_entries)
        except Exception as exc:
            logger.error("Error replacing images for outstanding %s: %s", outstanding_id, exc)
            raise

    @staticmethod
    async def delete_image(image_id: str) -> bool:
        try:
            deleted = await OsmOutstandingImage.filter(id=image_id).delete()
            return bool(deleted)
        except Exception as exc:
            logger.error("Error deleting outstanding image %s: %s", image_id, exc)
            raise

    @staticmethod
    async def get_images(outstanding_id: str) -> List[OsmOutstandingImage]:
        try:
            return await (
                OsmOutstandingImage
                .filter(outstanding_id=outstanding_id)
                .order_by("sort_order", "created_at")
            )
        except Exception as exc:
            logger.error("Error retrieving images for outstanding %s: %s", outstanding_id, exc)
            raise
