"""Generic background-job Excel export สำหรับรายงาน อสม. (/reports/*)

Dispatch ตาม ``reportType`` → reuse ``StandardReportService.<method>`` (page loop)
→ xlsxwriter constant_memory → download. รองรับข้อมูลเป็นล้านแถว ทุกสิทธิ์

**ไม่แต้ม export_job_service.py (assignments)** — import เฉพาะ pure helpers
(masking/hash/lock/meta/file-path) และใช้ Redis namespace แยก ``report:export:*``
เพื่อ sweeper ของแต่ละฝั่ง resume job ของตัวเอง ไม่ปนกัน
"""

from __future__ import annotations

import asyncio
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import BackgroundTasks, HTTPException

from app.api.v1.schemas.report_standard_schema import (
    AverageAgeReportQuery,
    AwardByAreaQuery,
    BenefitClaimQuery,
    FamilyAddressReportQuery,
    NewVolunteerByYearQuery,
    PositionsByVillageQuery,
    PresidentByLevelQuery,
    PresidentListQuery,
    QualifiedBenefitQuery,
    ResignedReportQuery,
    ResignedVolunteerQuery,
    SpecialtyByAreaQuery,
    StandardGenderReportQuery,
    TrainingByAreaQuery,
    VolunteerTenureQuery,
)
from app.cache.redis_client import cache_delete, cache_get, cache_set, get_redis
from app.configs.config import settings
from app.services.export_job_service import (
    UNMASK_LEVELS,
    _acquire_lock,
    _compute_params_hash,
    _job_file_path,
    _rkey,
    _release_lock,
    _write_meta_sidecar,
    format_citizen_id_export,
)
from app.services.standard_report_service import StandardReportService
from app.utils.logging_utils import get_logger
from app.utils.scope_enforcement import apply_scope_to_query, enforce_scope_on_filters

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants — namespace แยกจาก assignments (export:job:*) เพื่อ sweeper ไม่ปน
# ---------------------------------------------------------------------------

REPORT_JOB_KEY = "report:export:job:{job_id}"
REPORT_LOOKUP_KEY = "report:export:lookup:{officer_id}:{params_hash}"

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

_report_scheduler: Optional[AsyncIOScheduler] = None


# ---------------------------------------------------------------------------
# Column resolvers (computed/virtual)
# ---------------------------------------------------------------------------


def _item_val(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _full_name(item: Any) -> str:
    """ชื่อ-นามสกุล: ใช้ full_name field ถ้ามี ไม่งั้นรวม first+last."""
    explicit = _item_val(item, "full_name")
    if explicit:
        return str(explicit)
    first = str(_item_val(item, "first_name") or "").strip()
    last = str(_item_val(item, "last_name") or "").strip()
    return f"{first} {last}".strip()


VIRTUAL_RESOLVERS: Dict[str, Callable[[Any], Any]] = {
    "full_name": _full_name,
}


def _resolve_cell(item: Any, key: str, index: int) -> Any:
    if key == "__index__":
        return index
    resolver = VIRTUAL_RESOLVERS.get(key)
    if resolver is not None:
        value = resolver(item)
    else:
        value = _item_val(item, key)
    if value is None:
        return ""
    # xlsxwriter รับเฉพาะ str/int/float/datetime/None/bool — coerce ค่าอื่น (enum/date/Decimal/list/dict) เป็น str
    if isinstance(value, (str, int, float)):
        return value
    if isinstance(value, bool):
        return "ใช่" if value else ""
    return str(value)


def _project_report_row(item: Any, spec: "ReportExportSpec", unmask: bool, index: int) -> list:
    values: list = []
    for key, _label in spec.columns:
        if spec.mask_citizen_id and key == "citizen_id":
            raw = _resolve_cell(item, key, index)
            values.append(format_citizen_id_export(raw, unmask=unmask))
        else:
            values.append(_resolve_cell(item, key, index))
    return values


# ---------------------------------------------------------------------------
# Report registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReportExportSpec:
    report_type: str
    service_method: Callable
    filter_schema: type
    columns: List[Tuple[str, str]]  # (item_attr_or_virtual_key, หัวคอลัมน์)
    title: str
    file_slug: str
    mask_citizen_id: bool = False
    page_size: int = 200
    default_filters: Dict[str, Any] = field(default_factory=dict)


# columns: ("__index__", "ลำดับ") เป็นคอลัมน์ลำดับอัตโนมัติ
# field key ใช้ snake_case field name ของ Item schema (attr access)
REPORT_REGISTRY: Dict[str, ReportExportSpec] = {
    "training-by-area": ReportExportSpec(
        report_type="training-by-area",
        service_method=StandardReportService.training_by_area,
        filter_schema=TrainingByAreaQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("course_name", "หลักสูตรอบรม"),
            ("trained_year", "ปีที่อบรม (พ.ศ.)"),
            ("count", "จำนวน (คน)"),
        ],
        title="รายงานจำนวน อสม. ที่ได้รับการอบรม อสม.ช. ในแต่ละพื้นที่",
        file_slug="report_training_by_area",
    ),
    "awards-by-area": ReportExportSpec(
        report_type="awards-by-area",
        service_method=StandardReportService.awards_by_area,
        filter_schema=AwardByAreaQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("award_type", "ประเภทรางวัล"),
            ("award_name", "ชื่อรางวัล/เข็ม"),
            ("awarded_date", "วันที่ได้รับ"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
        ],
        title="รายงานแสดงรายชื่อ อสม. ที่ได้รับเข็ม จำแนกตามตำบล และอำเภอ",
        file_slug="report_standard_confirmed_by_area",
    ),
    "specialty-by-area": ReportExportSpec(
        report_type="specialty-by-area",
        service_method=StandardReportService.specialty_by_area,
        filter_schema=SpecialtyByAreaQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("skill_name", "ความชำนาญ"),
            ("count", "จำนวน (คน)"),
        ],
        title="รายงานตารางรายชื่อ อสม. ตามความชำนาญ จำแนกตามตำบล และอำเภอ",
        file_slug="report_standard_by_area_need",
    ),
    "volunteer-gender": ReportExportSpec(
        report_type="volunteer-gender",
        service_method=StandardReportService.volunteer_gender,
        filter_schema=StandardGenderReportQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("village_no", "หมู่"),
            ("village_name", "ชื่อหมู่บ้าน"),
            ("male", "เพศชาย"),
            ("female", "เพศหญิง"),
            ("total", "รวม"),
        ],
        title="รายงานมาตราฐาน อสม. จำแนกตามเพศ",
        file_slug="report_standard_by_gender",
    ),
    "volunteer-family": ReportExportSpec(
        report_type="volunteer-family",
        service_method=StandardReportService.volunteer_family_report,
        filter_schema=FamilyAddressReportQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("osm_code", "เลขบัตร อสม."),
            ("citizen_id", "เลขบัตรประชาชน"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("gender", "เพศ"),
            ("status_label", "สถานะ"),
            ("address", "ที่อยู่"),
            ("village_no", "หมู่ที่"),
            ("village_name", "หมู่บ้าน"),
            ("subdistrict_name", "ตำบล"),
            ("district_name", "อำเภอ"),
            ("province_name", "จังหวัด"),
        ],
        title="รายงานตารางรายชื่อและที่อยู่ อสม. และสมาชิกครอบครัวทั้งหมด",
        file_slug="report_standard_by_address",
        mask_citizen_id=True,
    ),
    "resigned-volunteers": ReportExportSpec(
        report_type="resigned-volunteers",
        service_method=StandardReportService.resigned_volunteers,
        filter_schema=ResignedVolunteerQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("citizen_id", "เลขบัตรประชาชน"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("village_no", "หมู่ที่"),
            ("village_name", "หมู่บ้าน"),
            ("subdistrict_name", "ตำบล"),
            ("district_name", "อำเภอ"),
            ("province_name", "จังหวัด"),
            ("retirement_date", "วันที่พ้นสภาพ"),
            ("retirement_reason", "สาเหตุพ้นสภาพ"),
            ("osm_status", "สถานะ อสม."),
        ],
        title="รายงานแสดงรายชื่อ อสม. ที่พ้นสภาพ",
        file_slug="report_resigned_list",
        mask_citizen_id=True,
    ),
    "resigned-report": ReportExportSpec(
        report_type="resigned-report",
        service_method=StandardReportService.resigned_report,
        filter_schema=ResignedReportQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("retirement_reason", "สาเหตุพ้นสภาพ"),
            ("total_resigned", "จำนวน (คน)"),
        ],
        title="รายงาน รายชื่อ อสม. พ้นสภาพ",
        file_slug="report_resigned_report",
    ),
    "qualified-benefit": ReportExportSpec(
        report_type="qualified-benefit",
        service_method=StandardReportService.qualified_benefit,
        filter_schema=QualifiedBenefitQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("citizen_id", "เลขบัตรประชาชน"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("village_no", "หมู่ที่"),
            ("village_name", "หมู่บ้าน"),
            ("allowance_status", "สถานะสิทธิ์"),
            ("allowance_year", "ปีงบประมาณ"),
            ("showbbody_status", "สถานะสิทธิ์ค่าป่วยการ"),
        ],
        title="รายงานแสดงรายชื่อ อสม. ที่ร้องสิทธิรักษาป่วยการ 2,000 บาท",
        file_slug="report_qualified_for_benefit",
        mask_citizen_id=True,
    ),
    "benefit-claims": ReportExportSpec(
        report_type="benefit-claims",
        service_method=StandardReportService.benefit_claim_list,
        filter_schema=BenefitClaimQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("osm_code", "เลขบัตร อสม."),
            ("citizen_id", "เลขบัตรประชาชน"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("village_no", "หมู่ที่"),
            ("village_name", "หมู่บ้าน"),
            ("approval_date", "วันที่อนุมัติ"),
            ("allowance_year", "ปีงบประมาณ"),
            ("osm_showbbody", "สถานะสิทธิ์ค่าป่วยการ"),
            ("claim_date", "วันที่ยื่นเรื่อง"),
            ("amount", "จำนวนเงิน"),
            ("status", "สถานะการเบิกจ่าย"),
        ],
        title="รายชื่อ อสม. ที่มีสิทธิรับค่าป่วยการ",
        file_slug="report_benefit_claim_list",
        mask_citizen_id=True,
        default_filters={"claim_type": "2000", "active_only": True},
    ),
    "volunteer-tenure": ReportExportSpec(
        report_type="volunteer-tenure",
        service_method=StandardReportService.volunteer_tenure,
        filter_schema=VolunteerTenureQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("osm_code", "เลขบัตร อสม."),
            ("citizen_id", "เลขบัตรประชาชน"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("village_name", "หมู่บ้าน"),
            ("start_year", "ปีที่เริ่มเป็น อสม."),
            ("tenure_years", "อายุการเป็น อสม. (ปี)"),
            ("approval_date", "วันที่อนุมัติ"),
            ("retirement_date", "วันที่พ้นสภาพ"),
            ("osm_status", "สถานะ"),
        ],
        title="รายชื่อ อสม. ทุกคน และระยะเวลาการเป็นอสม.",
        file_slug="report_all_and_duration",
        mask_citizen_id=True,
    ),
    "new-volunteers": ReportExportSpec(
        report_type="new-volunteers",
        service_method=StandardReportService.new_volunteers_by_year,
        filter_schema=NewVolunteerByYearQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("osm_code", "เลขบัตร อสม."),
            ("citizen_id", "เลขบัตรประชาชน"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("gender", "เพศ"),
            ("village_no", "หมู่ที่"),
            ("village_name", "หมู่บ้าน"),
            ("subdistrict_name", "ตำบล"),
            ("district_name", "อำเภอ"),
            ("province_name", "จังหวัด"),
            ("start_year", "ปีที่เริ่มเป็นอสม. (พ.ศ.)"),
            ("tenure_years", "อายุการทำงาน (ปี)"),
            ("created_at", "วันที่สร้างรายการ"),
            ("approval_date", "วันที่อนุมัติ"),
            ("approval_status", "สถานะ"),
        ],
        title="รายงานแสดงรายชื่อ อสม. ใหม่ ที่มีอายุการทำงานแบ่งตามปี",
        file_slug="report_new_by_year_list",
        mask_citizen_id=True,
    ),
    "positions-by-village": ReportExportSpec(
        report_type="positions-by-village",
        service_method=StandardReportService.positions_by_village,
        filter_schema=PositionsByVillageQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("village_no", "หมู่ที่"),
            ("village_name", "หมู่บ้าน"),
            ("position_name", "ตำแหน่ง"),
            ("count", "จำนวน (คน)"),
        ],
        title="ข้อมูล อสม. ที่ดำรงตำแหน่งอื่น เพื่อยืนยันการรับเงินค่าป่วยการ อสม",
        file_slug="report_positions_by_village",
    ),
    "president-by-level": ReportExportSpec(
        report_type="president-by-level",
        service_method=StandardReportService.president_by_level,
        filter_schema=PresidentByLevelQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("position_name", "ตำแหน่ง"),
            ("position_level", "ระดับตำแหน่ง"),
            ("area_name", "พื้นที่"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
        ],
        title="รายงาน รายชื่อ อสม. ที่มีตำแหน่งประธานชมรมอสม. ในระดับต่างๆ ตามพื้นที่แต่ละจังหวัด",
        file_slug="report_president_by_level",
    ),
    "president-list": ReportExportSpec(
        report_type="president-list",
        service_method=StandardReportService.president_list,
        filter_schema=PresidentListQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("full_name", "ชื่อ-นามสกุล"),
            ("position_name", "ตำแหน่ง"),
            ("position_level", "ระดับตำแหน่ง"),
            ("area_name", "พื้นที่"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
        ],
        title="รายงานแสดงรายชื่อประธาน อสม.",
        file_slug="report_president_list",
    ),
    "average-age": ReportExportSpec(
        report_type="average-age",
        service_method=StandardReportService.average_age_report,
        filter_schema=AverageAgeReportQuery,
        columns=[
            ("__index__", "ลำดับ"),
            ("province_name", "จังหวัด"),
            ("district_name", "อำเภอ"),
            ("subdistrict_name", "ตำบล"),
            ("total", "จำนวน"),
            ("average_age", "อายุเฉลี่ย"),
            ("min_age", "อายุต่ำสุด"),
            ("max_age", "อายุสูงสุด"),
        ],
        title="รายงานแสดงอายุเฉลี่ยของ อสม.",
        file_slug="report_average_age",
        page_size=500,
    ),
}


# ---------------------------------------------------------------------------
# Redis helpers (report namespace)
# ---------------------------------------------------------------------------


async def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return await cache_get(REPORT_JOB_KEY.format(job_id=job_id))


async def _set_job(job_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
    ttl = ttl if ttl is not None else settings.EXPORT_JOB_TTL_HOURS * 3600
    await cache_set(REPORT_JOB_KEY.format(job_id=job_id), data, ttl=ttl)


async def _update_job(job_id: str, patch: Dict[str, Any], ttl: Optional[int] = None) -> Dict[str, Any]:
    job = await _get_job(job_id) or {}
    job.update(patch)
    await _set_job(job_id, job, ttl=ttl)
    return job


async def _heartbeat(job_id: str, rows_written: int, total: int) -> None:
    progress = int((rows_written / total) * 100) if total else 0
    now_iso = datetime.now(timezone.utc).isoformat()
    await _update_job(
        job_id,
        {
            "status": JOB_STATUS_RUNNING,
            "rowsWritten": rows_written,
            "totalRows": total,
            "progress": progress,
            "heartbeatTs": now_iso,
        },
    )


async def _delete_job_and_file(job: Dict[str, Any]) -> None:
    import os

    job_id = job.get("jobId")
    path = job.get("filePath")
    if path:
        for candidate in (path, path + ".meta.json"):
            try:
                if candidate and os.path.exists(candidate):
                    os.remove(candidate)
            except Exception:
                pass
    if job_id:
        await cache_delete(REPORT_JOB_KEY.format(job_id=job_id))


# ---------------------------------------------------------------------------
# Job lifecycle
# ---------------------------------------------------------------------------


async def create_report_export_job(
    current_user: dict,
    report_type: str,
    filters: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    spec = REPORT_REGISTRY.get(report_type)
    if not spec:
        raise HTTPException(status_code=400, detail="unknown_report_type")

    officer_id = str(current_user.get("user_id"))
    payload_hash = _compute_params_hash(
        officer_id, {"r": report_type, "f": filters}
    )
    lookup_key = REPORT_LOOKUP_KEY.format(officer_id=officer_id, params_hash=payload_hash)

    # Idempotent: คืน job เดิมถ้ายังไม่ failed
    existing_job_id = await cache_get(lookup_key)
    if existing_job_id:
        job = await _get_job(existing_job_id)
        if job and job.get("status") in (
            JOB_STATUS_PENDING,
            JOB_STATUS_RUNNING,
            JOB_STATUS_COMPLETED,
        ):
            return {"jobId": existing_job_id, "status": job.get("status")}

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "jobId": job_id,
        "officerId": officer_id,
        "reportType": report_type,
        "paramsHash": payload_hash,
        "filters": filters,
        "status": JOB_STATUS_PENDING,
        "rowsWritten": 0,
        "totalRows": 0,
        "progress": 0,
        "createdAt": now.isoformat(),
        "heartbeatTs": now.isoformat(),
        "expiresAt": None,
        "filePath": None,
        "error": None,
    }
    await _set_job(job_id, job)
    await cache_set(lookup_key, job_id, ttl=settings.EXPORT_JOB_TTL_HOURS * 3600)

    background_tasks.add_task(
        _run_report_export_job_safe, job_id, dict(current_user), report_type, filters
    )
    return {"jobId": job_id, "status": JOB_STATUS_PENDING}


async def get_report_export_job(job_id: str, current_user: dict) -> Dict[str, Any]:
    job = await _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="export_job_not_found")
    if str(job.get("officerId")) != str(current_user.get("user_id")):
        raise HTTPException(status_code=403, detail="export_job_forbidden")

    status = job.get("status", JOB_STATUS_PENDING)
    total = int(job.get("totalRows") or 0)
    written = int(job.get("rowsWritten") or 0)
    progress = int(job.get("progress") or 0)
    if status == JOB_STATUS_COMPLETED and total:
        progress = 100

    download_url = None
    if status == JOB_STATUS_COMPLETED:
        download_url = f"{settings.API_V1_PREFIX}/reports/export/{job_id}/download"

    return {
        "status": status,
        "rowsWritten": written,
        "totalRows": total,
        "progress": progress,
        "expiresAt": job.get("expiresAt"),
        "downloadUrl": download_url,
        "reportType": job.get("reportType"),
        "error": job.get("error"),
    }


async def get_report_job_file_path(job_id: str, current_user: dict) -> str:
    job = await _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="export_job_not_found")
    if str(job.get("officerId")) != str(current_user.get("user_id")):
        raise HTTPException(status_code=403, detail="export_job_forbidden")
    if job.get("status") != JOB_STATUS_COMPLETED:
        raise HTTPException(status_code=409, detail="export_job_not_ready")

    path = job.get("filePath")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="export_file_missing")
    return path


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def _run_report_export_job_safe(
    job_id: str, current_user: dict, report_type: str, filters: Dict[str, Any]
) -> None:
    try:
        await run_report_export_job(job_id, current_user, report_type, filters)
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        logger.exception("report export job %s crashed", job_id)
        # เก็บ stack trace ท้ายๆ ใน error field เพื่อ frontend เห็นจุดพังจริง
        short_tb = tb[-1500:] if len(tb) > 1500 else tb
        await _update_job(
            job_id,
            {"status": JOB_STATUS_FAILED, "error": f"{type(exc).__name__}: {exc}\n{short_tb}"},
        )


async def run_report_export_job(
    job_id: str, current_user: dict, report_type: str, filters: Dict[str, Any]
) -> None:
    spec = REPORT_REGISTRY.get(report_type)
    if not spec:
        await _update_job(job_id, {"status": JOB_STATUS_FAILED, "error": "unknown_report_type"})
        return

    await _update_job(job_id, {"status": JOB_STATUS_RUNNING, "error": None})

    # 1) build filter schema (default + payload) — schema รับ camelCase/snake_case
    merged = {**spec.default_filters, **(filters or {})}
    try:
        filter_obj = spec.filter_schema(**merged)
    except Exception as exc:  # pydantic ValidationError
        await _update_job(job_id, {"status": JOB_STATUS_FAILED, "error": f"invalid_filters: {exc}"})
        return

    # 2) enforce scope (mirror reports_router) + ได้ level จาก override.scope
    override = await enforce_scope_on_filters(
        current_user,
        province_code=getattr(filter_obj, "province_code", None),
        district_code=getattr(filter_obj, "district_code", None),
        subdistrict_code=getattr(filter_obj, "subdistrict_code", None),
        village_code=getattr(filter_obj, "village_code", None),
    )
    apply_scope_to_query(filter_obj, override)
    # เปิดเลขบัตรประชาชนเต็มทุกสิทธิ์ (ยกเลิกการ masking ตาม level)
    unmask = True

    officer_id = str(current_user.get("user_id"))
    file_path = _job_file_path(officer_id, job_id)
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    page_size = max(1, spec.page_size)

    # 3) lazy import xlsxwriter (defensive — ไม่ทำให้ app start ไม่ได้)
    try:
        import xlsxwriter  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("XlsxWriter ไม่ได้ติดตั้ง กรุณา pip install -r requirements.txt") from exc

    workbook = xlsxwriter.Workbook(file_path, {"constant_memory": True, "use_zip64": True})
    worksheet = workbook.add_worksheet("Report")
    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#212584",
            "font_color": "#FFFFFF",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        }
    )
    cell_format = workbook.add_format({"border": 1, "valign": "vcenter"})
    for col, (_key, label) in enumerate(spec.columns):
        worksheet.write(0, col, label, header_format)
        worksheet.set_column(col, col, 18)

    try:
        total: Optional[int] = None
        rows_written = 0
        page = 1
        while True:
            filter_obj.page = page
            filter_obj.page_size = page_size
            response = await spec.service_method(filter_obj)

            items = list(getattr(response, "items", []) or [])
            if total is None:
                total = int(getattr(response, "total", 0) or 0)
                if total > settings.EXPORT_MAX_ROWS:
                    total = settings.EXPORT_MAX_ROWS
                await _update_job(job_id, {"totalRows": total})

            if not items:
                break

            for item in items:
                if rows_written >= (total or 0):
                    break
                rows_written += 1
                try:
                    values = _project_report_row(item, spec, unmask=unmask, index=rows_written)
                    worksheet.write_row(rows_written, 0, values, cell_format)
                except Exception as row_exc:  # noqa: BLE001
                    # skip แถวที่มีค่าแปลก แทน crash ทั้ง job
                    logger.warning(
                        "report export %s (%s): skip row %d — %s",
                        job_id, report_type, rows_written, row_exc,
                    )

            await _heartbeat(job_id, rows_written, total or rows_written)

            if rows_written >= (total or 0):
                break
            if len(items) < page_size:
                break
            page += 1

        workbook.close()
    except Exception:
        try:
            workbook.close()
        except Exception:
            pass
        raise

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.EXPORT_FILE_TTL_HOURS)
    await _update_job(
        job_id,
        {
            "status": JOB_STATUS_COMPLETED,
            "rowsWritten": rows_written,
            "totalRows": total or rows_written,
            "progress": 100,
            "filePath": file_path,
            "expiresAt": expires_at.isoformat(),
        },
    )
    latest = await _get_job(job_id)
    if latest:
        _write_meta_sidecar(latest)
    logger.info(
        "report export job %s (%s) completed: %d rows → %s",
        job_id, report_type, rows_written, file_path,
    )


# ---------------------------------------------------------------------------
# Sweeper + cleanup (APScheduler) — namespace report:export:*
# ---------------------------------------------------------------------------


async def _scan_report_jobs():
    """คืน list ของ (job_id, job_dict) ทั้งหมดใน namespace report:export:job:*."""
    import json

    r = get_redis()
    if not r:
        return []
    out = []
    pattern = _rkey("report:export:job:*")
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
        for full_key in keys or []:
            try:
                raw = await r.get(full_key)
                job = json.loads(raw) if raw else None
            except Exception:
                job = None
            if job and job.get("jobId"):
                out.append((job["jobId"], job))
        if cursor == 0:
            break
    return out


async def sweep_stale_report_jobs() -> None:
    now = datetime.now(timezone.utc)
    stale_threshold = settings.EXPORT_HEARTBEAT_STALE_SECONDS
    for job_id, job in await _scan_report_jobs():
        if job.get("status") != JOB_STATUS_RUNNING:
            continue
        hb = job.get("heartbeatTs")
        if not hb:
            continue
        try:
            hb_dt = datetime.fromisoformat(hb)
        except Exception:
            continue
        if (now - hb_dt).total_seconds() < stale_threshold:
            continue
        if not await _acquire_lock(f"report:export:resume-lock:{job_id}", ttl=1800):
            continue
        logger.warning("report export job %s stale → resuming", job_id)
        officer_id = job.get("officerId")
        synthetic_user = {"user_type": "officer", "user_id": officer_id}
        asyncio.create_task(
            _safe_resume_report(job_id, synthetic_user, job.get("reportType"), job.get("filters") or {})
        )


async def _safe_resume_report(job_id, current_user, report_type, filters) -> None:
    try:
        await _update_job(
            job_id, {"status": JOB_STATUS_RUNNING, "rowsWritten": 0, "progress": 0, "error": None}
        )
        await run_report_export_job(job_id, current_user, report_type, filters)
    except Exception as exc:  # noqa: BLE001
        logger.exception("report export job %s resume failed", job_id)
        await _update_job(job_id, {"status": JOB_STATUS_FAILED, "error": str(exc)})
    finally:
        await _release_lock(f"report:export:resume-lock:{job_id}")


async def cleanup_expired_report_jobs() -> None:
    now = datetime.now(timezone.utc)
    for _job_id, job in await _scan_report_jobs():
        expires = job.get("expiresAt")
        if expires:
            try:
                exp_dt = datetime.fromisoformat(expires)
            except Exception:
                continue
            if now > exp_dt:
                await _delete_job_and_file(job)
            continue
        created = job.get("createdAt")
        if not created:
            continue
        try:
            c_dt = datetime.fromisoformat(created)
        except Exception:
            continue
        if (now - c_dt).total_seconds() > settings.EXPORT_JOB_TTL_HOURS * 3600 * 2:
            await _delete_job_and_file(job)


# ---------------------------------------------------------------------------
# Scheduler lifecycle (instance ที่ 2 — คู่กับ assignments scheduler)
# ---------------------------------------------------------------------------


async def _safe_sweep() -> None:
    if not await _acquire_lock("report:export:sweep-lock", ttl=55):
        return
    try:
        await sweep_stale_report_jobs()
    except Exception:  # noqa: BLE001
        logger.exception("report export sweep tick failed")


async def _safe_cleanup() -> None:
    if not await _acquire_lock("report:export:cleanup-lock", ttl=14 * 60):
        return
    try:
        await cleanup_expired_report_jobs()
    except Exception:  # noqa: BLE001
        logger.exception("report export cleanup tick failed")


async def start_report_export_scheduler() -> None:
    global _report_scheduler
    if not settings.EXPORT_SCHEDULER_ENABLED:
        logger.info("report export: scheduler disabled")
        return
    _report_scheduler = AsyncIOScheduler()
    _report_scheduler.add_job(
        _safe_sweep,
        trigger=IntervalTrigger(seconds=60),
        id="report_export_sweep_job",
        name="Report export stale-job sweeper",
        replace_existing=True,
        misfire_grace_time=120,
    )
    _report_scheduler.add_job(
        _safe_cleanup,
        trigger=IntervalTrigger(minutes=15),
        id="report_export_cleanup_job",
        name="Report export expired-file cleanup",
        replace_existing=True,
        misfire_grace_time=600,
    )
    _report_scheduler.start()
    logger.info("report export: scheduler started (sweep=60s, cleanup=15m)")


async def stop_report_export_scheduler() -> None:
    global _report_scheduler
    if _report_scheduler:
        _report_scheduler.shutdown(wait=False)
        _report_scheduler = None
        logger.info("report export: scheduler stopped")
