from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from app.models.audit_model import AdminAuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    async def log_action(
        *,
        user_id: Optional[str] = None,
        action_type: str,
        target_type: str,
        description: Optional[str] = None,
        new_data: Optional[Dict[str, Any]] = None,
        old_data: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        try:
            user_uuid = UUID(str(user_id)) if user_id else None
        except (TypeError, ValueError):
            user_uuid = None

        try:
            await AdminAuditLog.create(
                user_id=user_uuid,
                action_type=action_type,
                target_type=target_type,
                description=description,
                old_data=old_data,
                new_data=new_data,
                ip_address=ip,
                user_agent=user_agent,
                success=success,
                error_message=error_message,
            )
        except Exception:
            logger.exception(
                "Failed to persist audit log",
                extra={
                    "action_type": action_type,
                    "target_type": target_type,
                    "user_id": user_id,
                    "success": success,
                },
            )
