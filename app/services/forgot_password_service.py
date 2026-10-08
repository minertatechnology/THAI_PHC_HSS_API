"""
ลืมรหัสผ่าน (อสม.) แบบ self-service: ยืนยันตัวตนด้วยเลขบัตร + วันเกิด แล้วตั้งรหัสผ่านใหม่

เลขบัตร + วันเกิด เดาได้ง่ายกว่ารหัสผ่าน จึงต้องมี:
- จำกัดจำนวนครั้งต่อเลขบัตร/ต่อ IP ผ่าน Redis (ถ้า Redis ใช้ไม่ได้ ให้ปิดฟีเจอร์นี้ ไม่ปล่อยให้เดาได้ไม่จำกัด)
- reset token อายุสั้น ใช้ได้ครั้งเดียว และ purpose ต่างจาก token ของ /auth/set-password
- ตอบ error แบบเดียวกันทุกกรณี (ไม่บอกว่าเลขบัตรมีในระบบหรือไม่)
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List

import jwt
from fastapi import HTTPException, status
from tortoise.expressions import Q

from app.api.middleware.middleware import invalidate_user_sessions
from app.api.v1.exceptions.http_exceptions import BadRequestException
from app.cache.redis_client import _key, get_redis
from app.configs.config import settings
from app.models.enum_models import ApprovalStatus
from app.models.osm_model import OSMProfile
from app.repositories.client_repository import RefreshTokenRepository
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.services.audit_service import AuditService
from app.services.oauth2_service import bcrypt_hash_password
from app.utils.logging_utils import get_logger, log_error

logger = get_logger(__name__)

TOKEN_PURPOSE = "forgot-password"
TOKEN_TTL_SECONDS = 10 * 60

WINDOW_SECONDS = 30 * 60
MAX_FAILS_PER_CITIZEN = 5
MAX_ATTEMPTS_PER_IP = 30


def _too_many() -> HTTPException:
    return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too_many_attempts")


def _unavailable() -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="forgot_password_unavailable")


def _eligible_osm_filter(citizen_id: str) -> Q:
    # เฉพาะ อสม. ที่อนุมัติแล้วและยังมีสถานะปกติ ไม่ให้ใช้ช่องทางนี้เปิดบัญชีที่รออนุมัติ/พ้นสภาพ
    return (
        Q(citizen_id=citizen_id)
        & Q(deleted_at__isnull=True)
        & Q(approval_status=ApprovalStatus.APPROVED.value)
        & (Q(osm_status__isnull=True) | Q(osm_status=""))
    )


class ForgotPasswordService:
    @staticmethod
    async def _hit(redis, key: str, limit: int) -> bool:
        """เพิ่ม counter แล้วคืน True ถ้ายังไม่เกิน limit"""
        full_key = _key(key)
        count = await redis.incr(full_key)
        if count == 1:
            await redis.expire(full_key, WINDOW_SECONDS)
        return count <= limit

    @staticmethod
    async def verify(citizen_id: str, birth_date: date, ip: str | None) -> dict:
        redis = get_redis()
        if redis is None:
            raise _unavailable()

        fail_key = f"forgot_pw:fail:{citizen_id}"
        try:
            if ip and not await ForgotPasswordService._hit(redis, f"forgot_pw:ip:{ip}", MAX_ATTEMPTS_PER_IP):
                raise _too_many()
            fails = int(await redis.get(_key(fail_key)) or 0)
            if fails >= MAX_FAILS_PER_CITIZEN:
                raise _too_many()
        except HTTPException:
            raise
        except Exception as exc:
            log_error(logger, "forgot_password rate limit check failed", exc=exc)
            raise _unavailable()

        profiles = await OSMProfile.filter(_eligible_osm_filter(citizen_id)).only("id", "birth_date")
        accepted_dates = {birth_date}
        try:
            # ข้อมูลเก่าบางส่วนอาจเก็บปีเป็น พ.ศ.
            accepted_dates.add(birth_date.replace(year=birth_date.year + 543))
        except ValueError:
            pass  # 29 ก.พ. ที่ปี +543 ไม่ใช่ปีอธิกสุรทิน
        osm_ids: List[str] = [str(p.id) for p in profiles if p.birth_date in accepted_dates]

        if not osm_ids:
            try:
                await ForgotPasswordService._hit(redis, fail_key, MAX_FAILS_PER_CITIZEN)
            except Exception as exc:
                log_error(logger, "forgot_password fail counter update failed", exc=exc)
            await AuditService.log_action(
                action_type="forgot_password_verify",
                target_type="osm",
                description="Forgot password identity check failed",
                ip=ip,
                success=False,
                error_message="identity_mismatch",
            )
            raise BadRequestException(detail="identity_mismatch")

        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": citizen_id,
                "ids": osm_ids,
                "purpose": TOKEN_PURPOSE,
                "jti": uuid.uuid4().hex,
                "iat": now,
                "exp": now + timedelta(seconds=TOKEN_TTL_SECONDS),
            },
            settings.JWT_FIRST_LOGIN_TOKEN_SECRET_KEY,
            algorithm=settings.JWT_FIRST_LOGIN_TOKEN_ALGORITHM,
        )
        return {"reset_token": token, "expires_in": TOKEN_TTL_SECONDS}

    @staticmethod
    async def reset(reset_token: str, new_password: str, ip: str | None) -> dict:
        try:
            payload = jwt.decode(
                reset_token,
                settings.JWT_FIRST_LOGIN_TOKEN_SECRET_KEY,
                algorithms=[settings.JWT_FIRST_LOGIN_TOKEN_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise BadRequestException(detail="reset_token_expired")
        except jwt.InvalidTokenError:
            raise BadRequestException(detail="reset_token_invalid")

        citizen_id = payload.get("sub")
        osm_ids = payload.get("ids") or []
        jti = payload.get("jti")
        if payload.get("purpose") != TOKEN_PURPOSE or not citizen_id or not osm_ids or not jti:
            raise BadRequestException(detail="reset_token_invalid")

        redis = get_redis()
        if redis is None:
            raise _unavailable()
        try:
            # ใช้ token ได้ครั้งเดียว
            first_use = await redis.set(_key(f"forgot_pw:used:{jti}"), "1", nx=True, ex=TOKEN_TTL_SECONDS + 60)
        except Exception as exc:
            log_error(logger, "forgot_password token single-use check failed", exc=exc)
            raise _unavailable()
        if not first_use:
            raise BadRequestException(detail="reset_token_used")

        # ตรวจซ้ำว่ายังมีสิทธิ์อยู่ (เผื่อสถานะเปลี่ยนระหว่างที่ token ยังไม่หมดอายุ)
        eligible = await OSMProfile.filter(_eligible_osm_filter(citizen_id) & Q(id__in=osm_ids)).values_list("id", flat=True)
        eligible_ids = [str(i) for i in eligible]
        if not eligible_ids:
            raise BadRequestException(detail="reset_token_invalid")

        hashed_password = bcrypt_hash_password(new_password)
        for osm_id in eligible_ids:
            await OSMProfileRepository.set_password_by_id(
                osm_id,
                hashed_password,
                mark_first_login=False,
                reset_attempts=True,
                reactivate=True,  # ปลดล็อกบัญชีที่ถูกปิดเพราะกรอกรหัสผิดเกินกำหนด
                updated_by="forgot-password",
            )
            try:
                await RefreshTokenRepository.revoke_all_user_refresh_tokens(osm_id, None, "osm")
            except Exception as exc:
                log_error(logger, "forgot_password revoke tokens failed", exc=exc)
            try:
                await invalidate_user_sessions(osm_id)
            except Exception:
                pass

            await AuditService.log_action(
                user_id=osm_id,
                action_type="reset_password",
                target_type="osm",
                description=f"Self-service forgot password for OSM profile {osm_id}",
                new_data={"osmProfileId": osm_id, "channel": "forgot-password"},
                ip=ip,
            )

        try:
            await redis.delete(_key(f"forgot_pw:fail:{citizen_id}"))
        except Exception:
            pass

        return {"success": True, "message": "password_reset_success"}
