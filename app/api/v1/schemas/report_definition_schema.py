from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportDefinitionBase(BaseModel):
    name: str = Field(..., max_length=100)
    label: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: bool = True


class ReportDefinitionCreate(ReportDefinitionBase):
    model_config = ConfigDict(extra="forbid")


class ReportDefinitionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, max_length=100)
    label: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None


class ReportDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    label: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReportDefinitionListResponse(BaseModel):
    items: List[ReportDefinitionResponse]
    total: int
    limit: int
    offset: int
