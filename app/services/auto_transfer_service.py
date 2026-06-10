"""Server-side auto-transfer scheduler: ตรวจสอบ Gen-H users ที่ผ่านเกณฑ์หลักสูตรครบ
และ upgrade เป็น YUWA-OSM อัตโนมัติ ทุกๆ N ชั่วโมง

Flow (เหมือน frontend MembersComp.fetchCompletedMembers + autoTransferEligible):
  1. GET course-criteria จาก api-genh
  2. Login เข้า e-learning API → GET completed-members
  3. Matching: ใครผ่านหลักสูตรครบทุกเกณฑ์
  4. Upgrade ผ่าน GenHService.upgrade_to_yuwa_osm()
"""

import asyncio
import logging
from uuid import UUID

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import HTTPException

from app.configs.config import settings
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

# System user context สำหรับเรียก upgrade_to_yuwa_osm (bypass ownership check)
SYSTEM_USER = {"user_type": "officer", "user_id": "auto-transfer-scheduler"}

_scheduler: AsyncIOScheduler | None = None


# ---------------------------------------------------------------------------
# Scheduler lifecycle (เรียกจาก main.py lifespan)
# ---------------------------------------------------------------------------

async def start_scheduler():
    """เริ่มต้น APScheduler ถ้า AUTO_TRANSFER_ENABLED=True."""
    global _scheduler
    if not settings.AUTO_TRANSFER_ENABLED:
        logger.info("auto_transfer: scheduler disabled (AUTO_TRANSFER_ENABLED=%s)", settings.AUTO_TRANSFER_ENABLED)
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_auto_transfer,
        trigger=IntervalTrigger(hours=settings.AUTO_TRANSFER_INTERVAL_HOURS),
        id="auto_transfer_job",
        name="Auto-transfer Gen-H to Yuwa OSM",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 ชม. catch-up ถ้า server ล่ม
    )
    _scheduler.start()
    logger.info(
        "auto_transfer: scheduler started (interval=%dh)",
        settings.AUTO_TRANSFER_INTERVAL_HOURS,
    )


async def stop_scheduler():
    """หยุด APScheduler เมื่อ app shutdown."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("auto_transfer: scheduler stopped")


# ---------------------------------------------------------------------------
# Core business logic
# ---------------------------------------------------------------------------

async def run_auto_transfer() -> dict:
    """Main orchestrator — รันทั้ง flow auto-transfer ครั้งเดียว.

    Returns:
        dict สรุปผลลัพธ์ {enabled, criteria_count, eligible, upgraded, skipped, errors, ...}
    """
    result = {
        "enabled": False,
        "criteria_count": 0,
        "total_completed_users": 0,
        "eligible_count": 0,
        "upgraded_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "message": "",
        "details": [],
    }

    if not settings.AUTO_TRANSFER_ENABLED:
        result["message"] = "auto_transfer disabled"
        return result

    # Redis lock — ป้องกัน concurrent run
    from app.cache.redis_client import cache_get, cache_set, cache_delete
    lock = await cache_get("auto_transfer:lock")
    if lock:
        msg = "auto_transfer: another run is in progress, skipping"
        logger.warning(msg)
        result["message"] = msg
        return result

    await cache_set("auto_transfer:lock", "1", ttl=300)  # 5 นาที

    try:
        result["enabled"] = True
        logger.info("auto_transfer: starting scheduled run")

        # --- Step 1: สร้าง AUTH access token (self-signed JWT) ---
        auth_token = await _create_auth_token()
        if not auth_token:
            msg = "auto_transfer: failed to create auth token"
            logger.error(msg)
            result["message"] = msg
            return result

        # --- Step 2: GET course criteria ---
        criteria = await _fetch_course_criteria(auth_token)
        if not criteria:
            msg = "auto_transfer: no course criteria configured or fetch failed"
            logger.warning(msg)
            result["message"] = msg
            return result
        result["criteria_count"] = len(criteria)

        # --- Step 3: Login to e-learning → GET completed members ---
        el_token = await _fetch_elearning_token(auth_token)
        if not el_token:
            msg = "auto_transfer: failed to login to e-learning API"
            logger.error(msg)
            result["message"] = msg
            return result

        completed_data = await _fetch_completed_members(el_token)
        if not completed_data:
            msg = "auto_transfer: failed to fetch completed members"
            logger.error(msg)
            result["message"] = msg
            return result

        # --- Step 4: สร้าง completion map ---
        completed_map: dict[str, set[str]] = _build_completion_map(completed_data)
        result["total_completed_users"] = len(completed_map)
        logger.info(
            "auto_transfer: %d users with completions, %d criteria courses",
            len(completed_map),
            len(criteria),
        )

        # --- Step 5: หา eligible users ---
        eligible_uuids = _find_eligible_uuids(criteria, completed_map)
        result["eligible_count"] = len(eligible_uuids)
        logger.info("auto_transfer: %d eligible users", len(eligible_uuids))

        if not eligible_uuids:
            result["message"] = "no eligible users"
            return result

        # --- Step 6: Upgrade แต่ละคน ---
        result["details"] = []
        for uuid_str in eligible_uuids:
            detail = await _process_single_user(uuid_str)
            result["details"].append(detail)
            if detail["status"] == "upgraded":
                result["upgraded_count"] += 1
            elif detail["status"] == "skipped":
                result["skipped_count"] += 1
            else:
                result["error_count"] += 1

        result["message"] = (
            f"completed: {result['upgraded_count']} upgraded, "
            f"{result['skipped_count']} skipped, "
            f"{result['error_count']} errors"
        )
        logger.info("auto_transfer: %s", result["message"])
        return result

    except Exception as exc:
        msg = f"auto_transfer: unexpected error: {exc}"
        logger.exception(msg)
        result["message"] = msg
        result["error_count"] += 1
        return result
    finally:
        await cache_delete("auto_transfer:lock")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _create_auth_token() -> str | None:
    """สร้าง JWT access token แบบ self-signed (เพราะเราคือ AUTH server)."""
    try:
        from app.utils.security import create_access_token

        client_id = "auto-transfer-service"
        token = create_access_token(
            user_id="auto-transfer-scheduler",
            client_id=client_id,
            user_type="officer",
            scopes=["profile"],
        )
        return token
    except Exception as exc:
        logger.error("auto_transfer: failed to create service token", exc_info=True)
        return None


async def _fetch_course_criteria(auth_token: str) -> list[dict]:
    """GET course-criteria จาก api-genh."""
    url = f"{settings.GENH_API_URL}/course-criteria/"
    headers = {"Authorization": f"Bearer {auth_token}"}
    try:
        resp = await asyncio.to_thread(
            requests.get, url, headers=headers, timeout=15,
        )
        if resp.status_code == 404:
            logger.info("auto_transfer: course-criteria endpoint returned 404 (no criteria set)")
            return []
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            logger.info("auto_transfer: no course criteria items configured")
            return []
        return items
    except Exception as exc:
        logger.error("auto_transfer: failed to fetch course criteria from %s: %s", url, exc)
        return []


async def _fetch_elearning_token(auth_token: str) -> str | None:
    """POST login เข้า e-learning API → รับ e-learning access token."""
    if not settings.ELEARNING_SERVICE_UUID:
        logger.error("auto_transfer: ELEARNING_SERVICE_UUID not configured")
        return None
    url = f"{settings.ELEARNING_API_URL}/auth/login"
    payload = {
        "uuid": settings.ELEARNING_SERVICE_UUID,
        "access_token": auth_token,
    }
    try:
        resp = await asyncio.to_thread(
            requests.post, url, json=payload, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        el_token = data.get("data", {}).get("access_token") or data.get("access_token")
        if not el_token:
            logger.error("auto_transfer: e-learning login response missing access_token")
            return None
        logger.info("auto_transfer: e-learning login successful")
        return el_token
    except Exception as exc:
        logger.error("auto_transfer: failed to login to e-learning API: %s", exc)
        return None


async def _fetch_completed_members(el_token: str) -> dict | None:
    """GET completed-members จาก e-learning API (group 12 = GEN-H)."""
    url = f"{settings.ELEARNING_API_URL}/groups/12/completed-members"
    headers = {"Authorization": f"Bearer {el_token}"}
    try:
        resp = await asyncio.to_thread(
            requests.get, url, headers=headers, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("auto_transfer: failed to fetch completed members: %s", exc)
        return None


def _build_completion_map(data: dict) -> dict[str, set[str]]:
    """สร้าง map: uuid -> Set<curriculum_id> จาก e-learning response.

    Response format:
    {
        "curriculums": [
            {"curriculum_id": "abc", "completed_members": [{"uuid": "..."}]},
            ...
        ]
    }
    """
    completed_map: dict[str, set[str]] = {}
    curriculums = data.get("curriculums", [])
    for curriculum in curriculums:
        curriculum_id = str(curriculum.get("curriculum_id", ""))
        members = curriculum.get("completed_members", [])
        for member in members:
            uuid = str(member.get("uuid", ""))
            if uuid and curriculum_id:
                if uuid not in completed_map:
                    completed_map[uuid] = set()
                completed_map[uuid].add(curriculum_id)
    return completed_map


def _find_eligible_uuids(
    criteria: list[dict],
    completed_map: dict[str, set[str]],
) -> list[str]:
    """หา UUID ที่ผ่านหลักสูตรครบทุกเกณฑ์.

    เหมือน frontend:
        criteria.every(c => completedSet.has(String(c.course_id || c.id)))
    """
    if not criteria:
        return []

    eligible: list[str] = []
    for uuid, completed_set in completed_map.items():
        all_passed = all(
            str(c.get("course_id") or c.get("id")) in completed_set
            for c in criteria
        )
        if all_passed:
            eligible.append(uuid)
    return eligible


async def _process_single_user(uuid_str: str) -> dict:
    """ตรวจสอบ + upgrade Gen-H user คนเดียว.

    Returns dict with status: "upgraded" | "skipped" | "error"
    """
    from app.repositories.gen_h_user_repository import GenHUserRepository
    from app.services.gen_h_service import GenHService
    from app.api.v1.schemas.gen_h_schema import GenHUpgradeToYuwaOSMRequest

    try:
        # --- เช็ค Gen-H user ใน local DB ---
        gen_h = await GenHUserRepository.get_by_id(UUID(uuid_str))
        if not gen_h:
            return {"gen_h_id": uuid_str, "status": "skipped", "reason": "not_found_in_db"}
        if not gen_h.is_active:
            return {"gen_h_id": uuid_str, "status": "skipped", "reason": "already_inactive"}
        if gen_h.yuwa_osm_user_id:
            return {"gen_h_id": uuid_str, "status": "skipped", "reason": "already_upgraded"}

        citizen_id = gen_h.citizen_id
        if not citizen_id:
            return {"gen_h_id": uuid_str, "status": "skipped", "reason": "no_citizen_id"}

        # --- Upgrade ---
        payload = GenHUpgradeToYuwaOSMRequest(citizen_id=citizen_id)
        result = await GenHService.upgrade_to_yuwa_osm(
            gen_h_id=uuid_str,
            payload=payload,
            current_user=SYSTEM_USER,
        )
        logger.info(
            "auto_transfer: upgraded %s → yuwa_osm %s",
            uuid_str,
            result.get("yuwa_osm_user_id"),
        )
        return {
            "gen_h_id": uuid_str,
            "status": "upgraded",
            "yuwa_osm_user_id": str(result.get("yuwa_osm_user_id", "")),
        }

    except HTTPException as exc:
        reason = exc.detail if hasattr(exc, "detail") else str(exc)
        logger.warning("auto_transfer: skipped %s — %s", uuid_str, reason)
        return {"gen_h_id": uuid_str, "status": "skipped", "reason": reason}

    except Exception as exc:
        logger.error("auto_transfer: error processing %s: %s", uuid_str, exc, exc_info=True)
        return {"gen_h_id": uuid_str, "status": "error", "error": str(exc)}
