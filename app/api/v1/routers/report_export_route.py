from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from app.api.middleware.middleware import require_scopes
from app.api.v1.schemas.report_export_schema import (
    ReportExportCreateRequest,
    ReportExportCreateResponse,
    ReportExportStatusResponse,
)
from app.services.report_export_job_service import (
    create_report_export_job,
    get_report_export_job,
    get_report_job_file_path,
)

report_export_router = APIRouter(prefix="/reports/export", tags=["reports-export"])


def _require_scope(current_user=Depends(require_scopes({"profile"}))):
    return current_user


@report_export_router.post("", status_code=202, response_model=ReportExportCreateResponse)
async def create_report_export_endpoint(
    payload: ReportExportCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(_require_scope),
) -> ReportExportCreateResponse:
    """สั่งสร้างไฟล์ export รายงานเป็น background job → คืน jobId ทันที."""
    result = await create_report_export_job(
        current_user, payload.reportType, payload.filters, background_tasks
    )
    return ReportExportCreateResponse(**result)


@report_export_router.get("/{job_id}", response_model=ReportExportStatusResponse)
async def get_report_export_status_endpoint(
    job_id: str,
    current_user: dict = Depends(_require_scope),
) -> ReportExportStatusResponse:
    """อ่านสถานะ job (progress/total/downloadUrl)."""
    data = await get_report_export_job(job_id, current_user)
    return ReportExportStatusResponse(**data)


@report_export_router.get("/{job_id}/download")
async def download_report_export_endpoint(
    job_id: str,
    current_user: dict = Depends(_require_scope),
):
    """ดาวน์โหลดไฟล์ .xlsx (ตรวจ ownership + ready)."""
    path = await get_report_job_file_path(job_id, current_user)
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"report_export_{date_stamp}.xlsx"
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )
