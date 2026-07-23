from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from app.api.middleware.middleware import require_scopes
from app.api.v1.schemas.export_schema import (
    ExportJobCreateRequest,
    ExportJobCreateResponse,
    ExportJobStatusResponse,
)
from app.services.export_job_service import (
    create_export_job,
    get_export_job,
    get_job_file_path,
)

export_router = APIRouter(prefix="/dashboard/assignments/export", tags=["dashboard-export"])


def _require_scope(current_user=Depends(require_scopes({"profile"}))):
    return current_user


def _payload_to_filters(payload: ExportJobCreateRequest) -> dict:
    """แปลง request body → filters dict (camelCase keys ที่ service อ่าน)."""
    return {
        "provinceCode": payload.provinceCode,
        "districtCode": payload.districtCode,
        "subdistrictCode": payload.subdistrictCode,
        "villageNo": payload.villageNo,
        "status": payload.status,
        "is_active": payload.isActive,
        "osmStatus": payload.osmStatus,
        "approval_status": payload.approvalStatus,
        "search": payload.search,
        "orderBy": payload.orderBy,
        "sortDir": payload.sortDir,
    }


@export_router.post("", status_code=202, response_model=ExportJobCreateResponse)
async def create_export_job_endpoint(
    payload: ExportJobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(_require_scope),
) -> ExportJobCreateResponse:
    """สั่งสร้างไฟล์ export เป็น background job → คืน jobId ทันที."""
    filters = _payload_to_filters(payload)
    result = await create_export_job(current_user, filters, background_tasks)
    return ExportJobCreateResponse(**result)


@export_router.get("/{job_id}", response_model=ExportJobStatusResponse)
async def get_export_job_status_endpoint(
    job_id: str,
    current_user: dict = Depends(_require_scope),
) -> ExportJobStatusResponse:
    """อ่านสถานะ job (progress/total/downloadUrl)."""
    data = await get_export_job(job_id, current_user)
    return ExportJobStatusResponse(**data)


@export_router.get("/{job_id}/download")
async def download_export_job_endpoint(
    job_id: str,
    current_user: dict = Depends(_require_scope),
):
    """ดาวน์โหลดไฟล์ .xlsx (ตรวจ ownership + ready)."""
    path = await get_job_file_path(job_id, current_user)
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"healthofficer_list_{date_stamp}.xlsx"
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )
