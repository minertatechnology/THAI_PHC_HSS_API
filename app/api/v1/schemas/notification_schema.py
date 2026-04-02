from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.api.v1.schemas.response_schema import PaginationMeta


class NotificationResponse(BaseModel):
    id: str
    actor_name: str
    action_type: str
    target_type: str
    target_id: str
    target_name: str
    citizen_id: Optional[str] = None
    message: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    pagination: PaginationMeta


class UnreadCountResponse(BaseModel):
    count: int
