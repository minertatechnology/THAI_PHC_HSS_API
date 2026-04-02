from __future__ import annotations

from uuid import uuid4

from tortoise import fields, models


class MobileBanner(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    title = fields.CharField(max_length=255)
    subtitle = fields.TextField(null=True)
    image_url = fields.CharField(max_length=1024)
    target_url = fields.CharField(max_length=1024, null=True)
    order_index = fields.IntField(default=0, index=True)
    platforms = fields.JSONField(default=list)
    metadata = fields.JSONField(null=True)
    starts_at = fields.DatetimeField(null=True, index=True)
    ends_at = fields.DatetimeField(null=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.UUIDField(null=True, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "mobile_banners"
        ordering = ("order_index", "created_at")
