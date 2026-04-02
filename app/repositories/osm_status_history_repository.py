from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.osm_model import OsmStatusHistory

logger = logging.getLogger(__name__)


class OsmStatusHistoryRepository:

    @staticmethod
    async def create(data: Dict[str, Any]) -> OsmStatusHistory:
        return await OsmStatusHistory.create(**data)

    @staticmethod
    async def find_by_osm_id(
        osm_profile_id: str,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        qs = OsmStatusHistory.filter(osm_profile_id=osm_profile_id)
        total = await qs.count()
        offset = (page - 1) * limit
        items = await qs.offset(offset).limit(limit).order_by("-created_at")

        results: List[Dict[str, Any]] = []
        for h in items:
            results.append({
                "id": str(h.id),
                "previous_osm_status": h.previous_osm_status,
                "new_osm_status": h.new_osm_status,
                "previous_is_active": h.previous_is_active,
                "new_is_active": h.new_is_active,
                "previous_approval_status": h.previous_approval_status,
                "new_approval_status": h.new_approval_status,
                "province_code": h.province_code,
                "district_code": h.district_code,
                "subdistrict_code": h.subdistrict_code,
                "village_no": h.village_no,
                "retirement_reason": h.retirement_reason,
                "remark": h.remark,
                "changed_by": str(h.changed_by),
                "changed_by_name": h.changed_by_name,
                "created_at": h.created_at,
            })

        pages = (total + limit - 1) // limit if limit > 0 else 1
        return {
            "items": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": pages,
            },
        }
