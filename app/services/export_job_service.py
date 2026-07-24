"""Background-job Excel export สำหรับรายชื่อ อสม. (/dashboard/assignments)

Design:
- POST สร้าง job → คืน jobId ทันที (HTTP 202) แล้วรัน BackgroundTasks สร้างไฟล์จริง
- รันเป็นหน้า (page_size) + xlsxwriter constant_memory → memory คงที่ รองรับ ~1M แถว
- สถานะเก็บใน Redis (cache_*) + `.meta.json` sidecar บน PVC เผื่อ Redis evict
- APScheduler sweeper resume job ที่ worker ตายกลางทาง (heartbeat stale)
- APScheduler cleanup ลบไฟล์หมดอายุ
- ดาวน์โหลดผ่าน endpoint ที่ตรวจ ownership (officer_id) — ไม่ใช้ static mount

Reuse ทุกอย่างจาก DashboardAssignmentService เพื่อให้ข้อมูลตรงตาราง 100%
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import BackgroundTasks, HTTPException

from app.cache.redis_client import (
    KEY_PREFIX,
    cache_delete,
    cache_get,
    cache_set,
    get_redis,
)
from app.configs.config import settings
from app.models.enum_models import AdministrativeLevelEnum
from app.services.dashboard_assignment_service import DashboardAssignmentService
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOB_KEY = "export:job:{job_id}"
LOOKUP_KEY = "export:lookup:{officer_id}:{params_hash}"

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

# ระดับที่เห็นเลขบัตรประชาชนเต็ม (mirror frontend UNMASK_EXPORT_LEVELS)
# country/region/area/province → เต็ม; district/subdistrict/village → mask
UNMASK_LEVELS = {
    AdministrativeLevelEnum.COUNTRY,
    AdministrativeLevelEnum.REGION,
    AdministrativeLevelEnum.AREA,
    AdministrativeLevelEnum.PROVINCE,
}

EXPORT_HEADERS = [
    "ลำดับ",
    "ชื่อ -นามสกุล",
    "เลขบัตรประชาชน",
    "เลขบัตร อสม.",
    "จังหวัด",
    "อำเภอ",
    "ตำบล",
    "หมู่ที่",
    "สถานะอสม.",
]

CITIZEN_ID_SEGMENTS = (1, 4, 5, 2, 1)

_export_scheduler: Optional[AsyncIOScheduler] = None


# ---------------------------------------------------------------------------
# Citizen-id masking (mirror frontend utils/citizenId.js)
# ---------------------------------------------------------------------------


def _sanitize_digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _mask_digits(digits: str, hidden: int = 4) -> str:
    if not digits:
        return ""
    if len(digits) <= hidden:
        return "x" * len(digits)
    threshold = len(digits) - hidden
    return "".join("x" if i >= threshold else c for i, c in enumerate(digits))


def _format_segments(text: str) -> str:
    """แบ่งตาม segments [1,4,5,2,1] คั่น '-' (ยอมรับตัว 'x')"""
    normalized = re.sub(r"[^0-9x]", "", (text or "").lower())
    if not normalized:
        return ""
    parts = []
    cursor = 0
    for seg in CITIZEN_ID_SEGMENTS:
        part = normalized[cursor : cursor + seg]
        if not part:
            break
        parts.append(part)
        cursor += seg
    return "-".join(parts)


def format_citizen_id_export(raw: Any, *, unmask: bool) -> str:
    """Format เลขบัตรประชาชนสำหรับ export — เต็มถ้า unmask มิฉะนั้น mask 4 หลักท้าย."""
    digits = _sanitize_digits(raw)
    if not digits:
        return "-"
    if unmask:
        return _format_segments(digits)
    return _format_segments(_mask_digits(digits, 4))


# ---------------------------------------------------------------------------
# Status label (mirror frontend mapOsmStatus)
# ---------------------------------------------------------------------------


def _enum_value(v: Any) -> str:
    if v is None:
        return ""
    if hasattr(v, "value"):
        return str(v.value)
    return str(v)


def _status_label(osm_status_field: Any, osm_showbbody_field: Any) -> str:
    normalized = _enum_value(osm_status_field).strip()
    if normalized != "":
        return "พ้นสภาพ"
    sb = _enum_value(osm_showbbody_field).strip()
    if sb in ("1", "2"):
        return "ได้รับสิทธิค่าป่วยการ"
    if sb == "5":
        return "ไม่ขอรับสิทธิค่าป่วยการ"
    if sb == "6":
        return "รอรับสิทธิค่าป่วยการ"
    return "ปกติ"


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------


def _rkey(key: str) -> str:
    """เติม project prefix ให้ key เมื่อใช้กับ get_redis() ตรงๆ (cache_* ทำให้เอง)."""
    return f"{KEY_PREFIX}{key}"


async def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return await cache_get(JOB_KEY.format(job_id=job_id))


async def _set_job(job_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
    ttl = ttl if ttl is not None else settings.EXPORT_JOB_TTL_HOURS * 3600
    await cache_set(JOB_KEY.format(job_id=job_id), data, ttl=ttl)


async def _update_job(job_id: str, patch: Dict[str, Any], ttl: Optional[int] = None) -> Dict[str, Any]:
    job = await _get_job(job_id) or {}
    job.update(patch)
    await _set_job(job_id, job, ttl=ttl)
    return job


async def _acquire_lock(key: str, ttl: int) -> bool:
    """Redis SETNX lock (single-pod leader). Redis ล่ม → proceed optimistically."""
    r = get_redis()
    if not r:
        return True
    try:
        return bool(await r.set(_rkey(key), "1", nx=True, ex=ttl))
    except Exception:
        return True


async def _release_lock(key: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        await r.delete(_rkey(key))
    except Exception:
        pass


def _compute_params_hash(officer_id: str, filters: Dict[str, Any]) -> str:
    payload = json.dumps({"o": officer_id, "f": filters}, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()[:16]


def _job_file_path(officer_id: str, job_id: str) -> str:
    return os.path.join(settings.EXPORT_FILES_DIR, officer_id, f"{job_id}.xlsx")


def _write_meta_sidecar(job: Dict[str, Any]) -> None:
    path = job.get("filePath")
    if not path:
        return
    try:
        meta_path = path + ".meta.json"
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(job, fh, ensure_ascii=False, default=str)
    except Exception:
        logger.warning("export: failed to write meta sidecar for %s", job.get("jobId"))


def _read_meta_sidecar(path: str) -> Optional[Dict[str, Any]]:
    try:
        meta_path = path + ".meta.json"
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


async def _delete_job_and_file(job: Dict[str, Any]) -> None:
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
        await cache_delete(JOB_KEY.format(job_id=job_id))


# ---------------------------------------------------------------------------
# Row projection
# ---------------------------------------------------------------------------


def _project_row(row: Dict[str, Any], *, unmask: bool, index: int) -> list:
    village_no = str(row.get("villageNo") or "").strip()
    village_name = str(row.get("villageName") or "").strip()
    if village_no and village_name:
        village_display = f"{village_no} - {village_name}"
    elif village_no:
        village_display = village_no
    elif village_name:
        village_display = village_name
    else:
        village_display = "-"

    return [
        index,
        str(row.get("fullName") or ""),
        format_citizen_id_export(row.get("citizenId"), unmask=unmask),
        str(row.get("osmCode") or ""),
        str(row.get("provinceNameTh") or ""),
        str(row.get("districtNameTh") or ""),
        str(row.get("subdistrictNameTh") or ""),
        village_display,
        _status_label(row.get("osmStatus"), row.get("osmShowbbody")),
    ]


# ---------------------------------------------------------------------------
# Job lifecycle
# ---------------------------------------------------------------------------


async def create_export_job(
    current_user: dict,
    filters: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """สร้าง export job (idempotent ตาม officer_id + filter hash) แล้ว enqueue runner."""
    officer_id = str(current_user.get("user_id"))
    params_hash = _compute_params_hash(officer_id, filters)
    lookup_key = LOOKUP_KEY.format(officer_id=officer_id, params_hash=params_hash)

    # Idempotent: ถ้ามี job เดิมยังไม่ failed → คืน job เดิม
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
        "paramsHash": params_hash,
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

    # Enqueue background runner (FastAPI BackgroundTasks — รันใน event loop ของ worker)
    background_tasks.add_task(_run_export_job_safe, job_id, dict(current_user), filters)

    return {"jobId": job_id, "status": JOB_STATUS_PENDING}


async def get_export_job(job_id: str, current_user: dict) -> Dict[str, Any]:
    """อ่านสถานะ job (ตรวจ ownership)."""
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
        download_url = f"{settings.API_V1_PREFIX}/dashboard/assignments/export/{job_id}/download"

    return {
        "status": status,
        "rowsWritten": written,
        "totalRows": total,
        "progress": progress,
        "expiresAt": job.get("expiresAt"),
        "downloadUrl": download_url,
        "error": job.get("error"),
    }


async def get_job_file_path(job_id: str, current_user: dict) -> str:
    """คืน path ไฟล์สำหรับดาวน์โหลด (ตรวจ ownership + ready)."""
    job = await _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="export_job_not_found")
    if str(job.get("officerId")) != str(current_user.get("user_id")):
        raise HTTPException(status_code=403, detail="export_job_forbidden")
    if job.get("status") != JOB_STATUS_COMPLETED:
        raise HTTPException(status_code=409, detail="export_job_not_ready")

    path = job.get("filePath")
    if not path or not os.path.exists(path):
        # Redis อาจรอด แต่ไฟล์ถูกลบ/ไม่เห็นข้าม pod → คืน 404 ชัด
        raise HTTPException(status_code=404, detail="export_file_missing")
    return path


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def _run_export_job_safe(job_id: str, current_user: dict, filters: Dict[str, Any]) -> None:
    """Wrapper ดัก exception เพื่อ mark failed และไม่ทำให้ worker crash."""
    try:
        await run_export_job(job_id, current_user, filters)
    except Exception as exc:  # noqa: BLE001
        logger.exception("export job %s crashed", job_id)
        await _update_job(job_id, {"status": JOB_STATUS_FAILED, "error": str(exc)})


async def run_export_job(job_id: str, current_user: dict, filters: Dict[str, Any]) -> None:
    """สร้างไฟล์ xlsx จริง: scope → queryset → count → stream rows."""
    await _update_job(job_id, {"status": JOB_STATUS_RUNNING, "error": None})

    # Resolve scope + build queryset (reuse DashboardAssignmentService)
    scope = await DashboardAssignmentService._resolve_scope(current_user)
    scope_filter = DashboardAssignmentService._build_scope_filter(scope) if scope else None
    status_bool = DashboardAssignmentService._parse_status(filters.get("status") or filters.get("is_active"))
    approval_status = DashboardAssignmentService._parse_approval_status(filters.get("approval_status"))

    base_query = DashboardAssignmentService._build_queryset(
        scope_filter=scope_filter,
        province_code=filters.get("provinceCode"),
        district_code=filters.get("districtCode"),
        subdistrict_code=filters.get("subdistrictCode"),
        village_no=filters.get("villageNo"),
        status_bool=status_bool,
        osm_status_filter=filters.get("osmStatus"),
        approval_status=approval_status,
        search=filters.get("search"),
    )

    total = await base_query.count()
    if total > settings.EXPORT_MAX_ROWS:
        total = settings.EXPORT_MAX_ROWS
    await _update_job(job_id, {"totalRows": total})
    await _heartbeat(job_id, 0, total)

    order_fields = DashboardAssignmentService._build_order_fields(
        order_by=filters.get("orderBy"),
        sort_dir=filters.get("sortDir"),
    )

    officer_id = str(current_user.get("user_id"))
    file_path = _job_file_path(officer_id, job_id)
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    # เปิดเลขบัตรประชาชนเต็มทุกสิทธิ์ (ยกเลิกการ masking ตาม level)
    unmask = True
    page_size = max(1, settings.EXPORT_PAGE_SIZE)

    # Lazy import — ถ้า XlsxWriter ยังไม่ถูกติดตั้งจะได้ไม่ทำให้ app start ไม่ได้
    try:
        import xlsxwriter  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "XlsxWriter ไม่ได้ติดตั้ง กรุณา pip install -r requirements.txt"
        ) from exc

    # xlsxwriter constant_memory: เขียนแถวแล้วทิ้งทันที → memory คงที่ตาม page_size
    workbook = xlsxwriter.Workbook(file_path, {"constant_memory": True, "use_zip64": True})
    worksheet = workbook.add_worksheet("OSM")
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

    for col, header in enumerate(EXPORT_HEADERS):
        worksheet.write(0, col, header, header_format)
        worksheet.set_column(col, col, 18)

    try:
        rows_written = 0
        page = 1
        while rows_written < total:
            offset = (page - 1) * page_size
            limit = min(page_size, total - rows_written)
            if limit <= 0:
                break
            items = (
                await base_query.prefetch_related("prefix", "province", "district", "subdistrict")
                .order_by(*order_fields)
                .offset(offset)
                .limit(limit)
            )
            if not items:
                break
            for profile in items:
                if rows_written >= total:
                    break
                row_data = DashboardAssignmentService._serialize_profile(profile)
                values = _project_row(row_data, unmask=unmask, index=rows_written + 1)
                worksheet.write_row(rows_written + 1, 0, values, cell_format)
                rows_written += 1
            await _heartbeat(job_id, rows_written, total)
            page += 1

        workbook.close()
    except Exception:
        # ปิด workbook ก่อน re-raise เพื่อไม่ทิ้ง fd
        try:
            workbook.close()
        except Exception:
            pass
        raise

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.EXPORT_FILE_TTL_HOURS)
    job_patch = {
        "status": JOB_STATUS_COMPLETED,
        "rowsWritten": rows_written,
        "totalRows": total,
        "progress": 100,
        "filePath": file_path,
        "expiresAt": expires_at.isoformat(),
    }
    await _update_job(job_id, job_patch)
    # เขียน sidecar หลัง set Redis (อ่าน job ล่าสุด)
    latest = await _get_job(job_id)
    if latest:
        _write_meta_sidecar(latest)
    logger.info("export job %s completed: %d rows → %s", job_id, rows_written, file_path)


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


# ---------------------------------------------------------------------------
# Sweeper + cleanup (APScheduler)
# ---------------------------------------------------------------------------


async def sweep_stale_jobs() -> None:
    """หา job running ที่ heartbeat stale → resume (rebuild ไฟล์ใหม่)."""
    r = get_redis()
    if not r:
        return
    now = datetime.now(timezone.utc)
    stale_threshold = settings.EXPORT_HEARTBEAT_STALE_SECONDS
    pattern = _rkey("export:job:*")
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
        for full_key in keys or []:
            try:
                raw = await r.get(full_key)
                job = json.loads(raw) if raw else None
            except Exception:
                job = None
            if not job or job.get("status") != JOB_STATUS_RUNNING:
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

            job_id = job.get("jobId")
            if not job_id:
                continue
            # resume lock → only one pod rebuilds
            if not await _acquire_lock(f"export:resume-lock:{job_id}", ttl=1800):
                continue
            officer_id = job.get("officerId")
            logger.warning("export job %s stale → resuming", job_id)
            synthetic_user = {"user_type": "officer", "user_id": officer_id}
            asyncio.create_task(
                _safe_resume(job_id, synthetic_user, job.get("filters") or {})
            )
        if cursor == 0:
            break


async def _safe_resume(job_id: str, current_user: dict, filters: Dict[str, Any]) -> None:
    """Resume = rebuild ไฟล์ใหม่ตั้งแต่ต้น (deterministic) เพราะ xlsxwriter ไม่ append."""
    try:
        await _update_job(
            job_id,
            {"status": JOB_STATUS_RUNNING, "rowsWritten": 0, "progress": 0, "error": None},
        )
        await run_export_job(job_id, current_user, filters)
    except Exception as exc:  # noqa: BLE001
        logger.exception("export job %s resume failed", job_id)
        await _update_job(job_id, {"status": JOB_STATUS_FAILED, "error": str(exc)})
    finally:
        await _release_lock(f"export:resume-lock:{job_id}")


async def cleanup_expired_jobs() -> None:
    """ลบไฟล์ + Redis key ที่หมดอายุ."""
    r = get_redis()
    if not r:
        return
    now = datetime.now(timezone.utc)
    pattern = _rkey("export:job:*")
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
        for full_key in keys or []:
            try:
                raw = await r.get(full_key)
                job = json.loads(raw) if raw else None
            except Exception:
                job = None
            if not job:
                continue

            expires = job.get("expiresAt")
            if expires:
                try:
                    exp_dt = datetime.fromisoformat(expires)
                except Exception:
                    continue
                if now > exp_dt:
                    await _delete_job_and_file(job)
                continue

            # pending/running ที่ไม่มี expiresAt → ตัดทิ้งถ้าเก่าเกิน 2x job TTL
            created = job.get("createdAt")
            if not created:
                continue
            try:
                c_dt = datetime.fromisoformat(created)
            except Exception:
                continue
            if (now - c_dt).total_seconds() > settings.EXPORT_JOB_TTL_HOURS * 3600 * 2:
                await _delete_job_and_file(job)
        if cursor == 0:
            break


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


async def _safe_sweep() -> None:
    """Sweeper tick — lock เพื่อให้ทำงานทีละ pod."""
    if not await _acquire_lock("export:sweep-lock", ttl=55):
        return
    try:
        await sweep_stale_jobs()
    except Exception:  # noqa: BLE001
        logger.exception("export sweep tick failed")


async def _safe_cleanup() -> None:
    if not await _acquire_lock("export:cleanup-lock", ttl=14 * 60):
        return
    try:
        await cleanup_expired_jobs()
    except Exception:  # noqa: BLE001
        logger.exception("export cleanup tick failed")


async def start_export_scheduler() -> None:
    global _export_scheduler
    if not settings.EXPORT_SCHEDULER_ENABLED:
        logger.info("export: scheduler disabled")
        return
    _export_scheduler = AsyncIOScheduler()
    _export_scheduler.add_job(
        _safe_sweep,
        trigger=IntervalTrigger(seconds=60),
        id="export_sweep_job",
        name="Export stale-job sweeper",
        replace_existing=True,
        misfire_grace_time=120,
    )
    _export_scheduler.add_job(
        _safe_cleanup,
        trigger=IntervalTrigger(minutes=15),
        id="export_cleanup_job",
        name="Export expired-file cleanup",
        replace_existing=True,
        misfire_grace_time=600,
    )
    _export_scheduler.start()
    logger.info("export: scheduler started (sweep=60s, cleanup=15m)")


async def stop_export_scheduler() -> None:
    global _export_scheduler
    if _export_scheduler:
        _export_scheduler.shutdown(wait=False)
        _export_scheduler = None
        logger.info("export: scheduler stopped")
