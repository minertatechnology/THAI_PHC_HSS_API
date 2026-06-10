from pydantic import BaseModel, Field
from typing import Optional


class AutoTransferResultSchema(BaseModel):
    """Response schema สำหรับ auto-transfer result."""

    enabled: bool = False
    criteria_count: int = 0
    total_completed_users: int = 0
    eligible_count: int = 0
    upgraded_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    message: str = ""
    details: list[dict] = Field(default_factory=list)
