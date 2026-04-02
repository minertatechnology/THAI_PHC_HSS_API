from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enum_models import AdministrativeLevelEnum


class PermissionPageBase(BaseModel):
    system_name: str = Field(default="thai_phc_web", max_length=100)
    main_menu: str = Field(..., max_length=255)
    sub_main_menu: Optional[str] = Field(default=None, max_length=255)
    allowed_levels: list[AdministrativeLevelEnum] = Field(default_factory=list)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True
    metadata: Optional[dict[str, Any]] = None


class PermissionPageCreate(PermissionPageBase):
    pass


class PermissionPageUpdate(BaseModel):
    main_menu: Optional[str] = Field(default=None, max_length=255)
    sub_main_menu: Optional[str] = Field(default=None, max_length=255)
    allowed_levels: Optional[list[AdministrativeLevelEnum]] = None
    display_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class PermissionPageResponse(PermissionPageBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
