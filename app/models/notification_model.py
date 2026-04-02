from __future__ import annotations

from uuid import uuid4

from tortoise import fields, models


class OsmNotification(models.Model):
    """Notification record created when OSM/Yuwa-OSM data is modified."""

    id = fields.UUIDField(pk=True, default=uuid4)
    actor_id = fields.UUIDField(index=True)
    actor_name = fields.CharField(max_length=100)
    action_type = fields.CharField(max_length=20, index=True)
    target_type = fields.CharField(max_length=20, index=True)
    target_id = fields.UUIDField(index=True)
    target_name = fields.CharField(max_length=100)
    citizen_id = fields.CharField(max_length=13, null=True, index=True)
    message = fields.CharField(max_length=300)
    province_code = fields.CharField(max_length=6, null=True, index=True)
    district_code = fields.CharField(max_length=8, null=True, index=True)
    subdistrict_code = fields.CharField(max_length=10, null=True, index=True)
    health_area_id = fields.CharField(max_length=10, null=True, index=True)
    region_code = fields.CharField(max_length=10, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "osm_notifications"
        ordering = ["-created_at"]


class OsmNotificationRead(models.Model):
    """Tracks which officer has read which notification (fan-out on read)."""

    id = fields.UUIDField(pk=True, default=uuid4)
    notification = fields.ForeignKeyField(
        "models.OsmNotification",
        related_name="reads",
        on_delete=fields.CASCADE,
    )
    officer_id = fields.UUIDField(index=True)
    read_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "osm_notification_reads"
        unique_together = (("notification", "officer_id"),)
