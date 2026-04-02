from __future__ import annotations

from uuid import uuid4

from tortoise import fields, models


class AdminAuditLog(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    user_id = fields.UUIDField(null=True, index=True)
    action_type = fields.CharField(max_length=255)
    target_type = fields.CharField(max_length=255)
    description = fields.CharField(max_length=500, null=True)
    old_data = fields.JSONField(null=True)
    new_data = fields.JSONField(null=True)
    ip_address = fields.CharField(max_length=100, null=True)
    user_agent = fields.CharField(max_length=500, null=True)
    success = fields.BooleanField(default=True)
    error_message = fields.CharField(max_length=1000, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "admin_audit_logs"
        ordering = ["-created_at"]
