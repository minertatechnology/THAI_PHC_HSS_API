from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enum_models import AdministrativeLevelEnum


class PositionBase(BaseModel):
    position_name_th: str = Field(..., max_length=255)
    position_name_en: Optional[str] = Field(default=None, max_length=255)
    position_code: str = Field(..., max_length=255)
    scope_level: Optional[AdministrativeLevelEnum] = None


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    position_name_th: Optional[str] = Field(default=None, max_length=255)
    position_name_en: Optional[str] = Field(default=None, max_length=255)
    position_code: Optional[str] = Field(default=None, max_length=255)
    scope_level: Optional[AdministrativeLevelEnum] = None


class PositionResponse(PositionBase):
    id: UUID
    label: Optional[str] = None
    name_th: Optional[str] = None
    name_en: Optional[str] = None
    code: Optional[str] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
