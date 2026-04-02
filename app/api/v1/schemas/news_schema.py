from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NewsResponse(BaseModel):
    id: UUID
    title: str = Field(..., max_length=255)
    department: str = Field(..., max_length=255)
    content_html: str
    image_urls: List[str]
    platforms: List[str] = Field(default_factory=list, description="แพลตฟอร์มที่แสดงข่าว: SmartOSM, ThaiPHC")
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    class Config:
        from_attributes = True
