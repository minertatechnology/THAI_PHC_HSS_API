from __future__ import annotations

from uuid import uuid4

from tortoise import fields, models


class MobileMenuItem(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    menu_key = fields.CharField(max_length=100, unique=True, index=True)
    menu_name = fields.CharField(max_length=255)
    menu_description = fields.TextField(null=True)
    icon_name = fields.CharField(max_length=255, null=True)
    open_type = fields.CharField(max_length=50, default="webview", index=True)
    webview_title = fields.CharField(max_length=255, null=True)
    webview_url = fields.CharField(max_length=512, null=True)
    redirect_url = fields.CharField(max_length=512, null=True)
    deeplink_url = fields.CharField(max_length=512, null=True)
    allowed_user_types = fields.JSONField(default=list)
    platforms = fields.JSONField(default=list)
    metadata = fields.JSONField(null=True)
    display_order = fields.IntField(default=0, index=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.UUIDField(null=True, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "mobile_menu_items"
        ordering = ("display_order", "menu_name")
