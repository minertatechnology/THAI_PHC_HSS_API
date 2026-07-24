from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ReportExportCreateRequest(BaseModel):
    """สั่งสร้าง job export สำหรับรายงาน — dispatch ตาม reportType."""

    reportType: str = Field(..., description="slug รายงาน เช่น new-volunteers, resigned-volunteers")
    filters: Dict[str, Any] = Field(default_factory=dict, description="พารามิเตอร์กรอง (camelCase หรือ snake_case ตามที่ตารางใช้)")


class ReportExportCreateResponse(BaseModel):
    jobId: str
    status: str = "pending"


class ReportExportStatusResponse(BaseModel):
    status: str
    rowsWritten: int = 0
    totalRows: int = 0
    progress: int = 0
    expiresAt: Optional[str] = None
    downloadUrl: Optional[str] = None
    reportType: Optional[str] = None
    error: Optional[str] = None
