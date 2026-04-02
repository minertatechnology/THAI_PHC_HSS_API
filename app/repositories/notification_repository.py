from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from tortoise.expressions import Q

from app.models.notification_model import OsmNotification, OsmNotificationRead
from app.utils.officer_hierarchy import OfficerScope
from app.models.enum_models import AdministrativeLevelEnum

logger = logging.getLogger(__name__)


class NotificationRepository:

    @staticmethod
    def _build_scope_filter(scope: OfficerScope) -> Q:
        """Build a Q filter so an officer only sees notifications within their scope."""
        level = scope.level
        if level == AdministrativeLevelEnum.COUNTRY:
            return Q()  # sees everything
        if level == AdministrativeLevelEnum.REGION:
            if scope.region_code:
                return Q(region_code=scope.region_code)
            return Q(id=None)  # no match
        if level == AdministrativeLevelEnum.AREA:
            if scope.health_area_id:
                return Q(health_area_id=scope.health_area_id)
            return Q(id=None)
        if level == AdministrativeLevelEnum.PROVINCE:
            if scope.province_id:
                return Q(province_code=scope.province_id)
            return Q(id=None)
        if level == AdministrativeLevelEnum.DISTRICT:
            if scope.district_id:
                return Q(district_code=scope.district_id)
            return Q(id=None)
        if level == AdministrativeLevelEnum.SUBDISTRICT:
            if scope.subdistrict_id:
                return Q(subdistrict_code=scope.subdistrict_id)
            return Q(id=None)
        if level == AdministrativeLevelEnum.VILLAGE:
            if scope.subdistrict_id:
                return Q(subdistrict_code=scope.subdistrict_id)
            return Q(id=None)
        return Q(id=None)

    @staticmethod
    async def _get_read_ids(officer_id: UUID) -> set:
        """Materialize the set of notification IDs that an officer has read."""
        read_list = await OsmNotificationRead.filter(
            officer_id=officer_id
        ).values_list("notification_id", flat=True)
        return set(read_list)

    @staticmethod
    async def create(data: Dict[str, Any]) -> OsmNotification:
        return await OsmNotification.create(**data)

    @staticmethod
    async def find_by_id(notification_id: str) -> Optional[OsmNotification]:
        try:
            return await OsmNotification.get(id=notification_id)
        except Exception:
            return None

    @staticmethod
    async def find_for_officer(
        scope: OfficerScope,
        officer_id: str,
        page: int = 1,
        limit: int = 20,
        is_read: Optional[bool] = None,
        target_type: str = "osm",
    ) -> Dict[str, Any]:
        scope_filter = NotificationRepository._build_scope_filter(scope)
        officer_uuid = UUID(str(officer_id))
        qs = OsmNotification.filter(scope_filter).filter(target_type=target_type)

        if is_read is not None:
            read_ids = await NotificationRepository._get_read_ids(officer_uuid)
            if is_read is True:
                if read_ids:
                    qs = qs.filter(id__in=list(read_ids))
                else:
                    # No reads → no read items to show
                    return {
                        "items": [],
                        "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0},
                    }
            else:
                if read_ids:
                    qs = qs.exclude(id__in=list(read_ids))

        total = await qs.count()
        offset = (page - 1) * limit
        items = await qs.offset(offset).limit(limit).order_by("-created_at")

        # Determine read status for returned items
        item_ids = [n.id for n in items]
        read_notification_ids = set()
        if item_ids:
            read_records = await OsmNotificationRead.filter(
                officer_id=officer_uuid,
                notification_id__in=item_ids,
            ).values_list("notification_id", flat=True)
            read_notification_ids = set(read_records)

        results = []
        for n in items:
            results.append({
                "id": str(n.id),
                "actor_id": str(n.actor_id),
                "actor_name": n.actor_name,
                "action_type": n.action_type,
                "target_type": n.target_type,
                "target_id": str(n.target_id),
                "target_name": n.target_name,
                "citizen_id": n.citizen_id,
                "message": n.message,
                "is_read": n.id in read_notification_ids,
                "created_at": n.created_at,
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

    @staticmethod
    async def count_unread(
        scope: OfficerScope,
        officer_id: str,
        target_type: str = "osm",
    ) -> int:
        scope_filter = NotificationRepository._build_scope_filter(scope)
        officer_uuid = UUID(str(officer_id))

        # Materialize read IDs first, then exclude
        read_ids = await NotificationRepository._get_read_ids(officer_uuid)

        qs = OsmNotification.filter(scope_filter).filter(target_type=target_type)
        if read_ids:
            qs = qs.exclude(id__in=list(read_ids))

        return await qs.count()

    @staticmethod
    async def mark_read(notification_id: str, officer_id: str) -> bool:
        try:
            await OsmNotificationRead.get_or_create(
                notification_id=UUID(str(notification_id)),
                officer_id=UUID(str(officer_id)),
            )
            return True
        except Exception:
            logger.exception("Failed to mark notification %s as read", notification_id)
            return False

    @staticmethod
    async def mark_all_read(
        scope: OfficerScope,
        officer_id: str,
        target_type: str = "osm",
    ) -> int:
        scope_filter = NotificationRepository._build_scope_filter(scope)
        officer_uuid = UUID(str(officer_id))

        # Materialize read IDs first
        read_ids = await NotificationRepository._get_read_ids(officer_uuid)

        qs = OsmNotification.filter(scope_filter).filter(target_type=target_type)
        if read_ids:
            qs = qs.exclude(id__in=list(read_ids))

        unread = await qs.values_list("id", flat=True)

        count = 0
        for nid in unread:
            try:
                await OsmNotificationRead.get_or_create(
                    notification_id=nid,
                    officer_id=officer_uuid,
                )
                count += 1
            except Exception:
                pass
        return count
