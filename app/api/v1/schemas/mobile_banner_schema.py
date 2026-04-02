from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.v1.schemas.response_schema import PaginationMeta


class MobileBannerBase(BaseModel):
    title: str = Field(..., max_length=255, description="Main text shown on the banner.")
    subtitle: Optional[str] = Field(default=None, description="Optional supporting text displayed under the title.")
    image_url: str = Field(..., max_length=1024, description="Absolute or relative URL pointing to the banner image.")
    target_url: Optional[str] = Field(default=None, max_length=1024, description="Optional URL to open when the banner is tapped.")
    order_index: int = Field(default=0, ge=0, description="Display order; lower numbers render first.")
    platforms: List[str] = Field(default_factory=list, description="Limit visibility to specific platforms (android/ios/web). Empty = all.")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Arbitrary JSON metadata for clients.")
    starts_at: Optional[datetime] = Field(default=None, description="Optional start timestamp for displaying the banner.")
    ends_at: Optional[datetime] = Field(default=None, description="Optional end timestamp for displaying the banner.")
    is_active: bool = Field(default=True, description="Set false to hide the banner without deleting it.")


class MobileBannerCreate(MobileBannerBase):
    pass


class MobileBannerUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    subtitle: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None, max_length=1024)
    target_url: Optional[str] = Field(default=None, max_length=1024)
    order_index: Optional[int] = Field(default=None, ge=0)
    platforms: Optional[List[str]] = None
    metadata: Optional[dict[str, Any]] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class MobileBannerResponse(MobileBannerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class MobileBannerListResponse(BaseModel):
    items: List[MobileBannerResponse]
    pagination: PaginationMeta


class MobileBannerUploadResponse(BaseModel):
    image_url: str = Field(
        ...,
        max_length=1024,
        description="Relative or absolute URL of the stored banner image.",
    )
