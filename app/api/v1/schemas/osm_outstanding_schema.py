from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OutstandingImageResponse(BaseModel):
    id: str
    image_url: str
    sort_order: int = 0
    caption: Optional[str] = None

    class Config:
        from_attributes = True


class OsmOutstandingCreateSchema(BaseModel):
    """สร้างข้อมูลดีเด่นใหม่"""
    award_year: int = Field(..., description="ปี พ.ศ. ที่ได้รับ")
    award_level_id: Optional[str] = Field(None, description="UUID ระดับดีเด่น")
    award_category_id: Optional[str] = Field(None, description="UUID ประเภทดีเด่น")
    title: Optional[str] = Field(None, max_length=500, description="ชื่อผลงานดีเด่น")
    description: Optional[str] = Field(None, description="รายละเอียดผลงาน")


class OsmOutstandingUpdateSchema(BaseModel):
    """อัปเดตข้อมูลดีเด่น"""
    award_year: Optional[int] = Field(None, description="ปี พ.ศ. ที่ได้รับ")
    award_level_id: Optional[str] = Field(None, description="UUID ระดับดีเด่น")
    award_category_id: Optional[str] = Field(None, description="UUID ประเภทดีเด่น")
    title: Optional[str] = Field(None, max_length=500, description="ชื่อผลงานดีเด่น")
    description: Optional[str] = Field(None, description="รายละเอียดผลงาน")


class OsmOutstandingResponse(BaseModel):
    id: str
    osm_profile_id: str
    award_year: int
    award_level_id: Optional[str] = None
    award_level_name: Optional[str] = None
    award_category_id: Optional[str] = None
    award_category_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    images: List[OutstandingImageResponse] = []
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OsmOutstandingListResponse(BaseModel):
    items: List[OsmOutstandingResponse]
    total: int
