from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExportJobCreateRequest(BaseModel):
    """พารามิเตอร์กรองสำหรับสร้าง job export (mirror GET /dashboard/assignments)."""

    provinceCode: Optional[str] = Field(None, max_length=10)
    districtCode: Optional[str] = Field(None, max_length=10)
    subdistrictCode: Optional[str] = Field(None, max_length=10)
    villageNo: Optional[str] = None
    status: Optional[str] = None
    isActive: Optional[str] = Field(None, alias="is_active")
    osmStatus: Optional[str] = Field(None, alias="osm_status")
    approvalStatus: Optional[str] = Field(None, alias="approval_status")
    search: Optional[str] = None
    orderBy: Optional[str] = Field(None, alias="order_by")
    sortDir: Optional[str] = Field(None, alias="sort_dir")
    format: str = Field("xlsx", description="รูปแบบไฟล์ (v1 รองรับ xlsx เท่านั้น)")

    model_config = {"populate_by_name": True}


class ExportJobCreateResponse(BaseModel):
    jobId: str
    status: str = "pending"


class ExportJobStatusResponse(BaseModel):
    status: str
    rowsWritten: int = 0
    totalRows: int = 0
    progress: int = 0
    expiresAt: Optional[str] = None
    downloadUrl: Optional[str] = None
    error: Optional[str] = None
