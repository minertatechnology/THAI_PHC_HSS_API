from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from tortoise.expressions import Q

from app.models.people_model import PeopleUser
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PeopleUserRepository:
    """Data access helpers for People users participating in SSO."""

    @staticmethod
    async def find_basic_profile_by_citizen_id(citizen_id: str) -> Optional[PeopleUser]:
        if not citizen_id:
            return None
        try:
            return (
                await PeopleUser
                .filter(citizen_id=citizen_id, is_active=True)
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "province_code",
                    "district_code",
                    "subdistrict_code",
                    "password_hash",
                    "is_first_login",
                    "is_active",
                )
                .first()
            )
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to load People profile for citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def find_profile_by_id(user_id: str) -> Optional[PeopleUser]:
        try:
            return await PeopleUser.filter(id=user_id, is_active=True).first()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to load People profile for id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def find_basic_profile_by_id(user_id: str) -> Optional[PeopleUser]:
        if not user_id:
            return None
        try:
            return (
                await PeopleUser
                .filter(id=user_id)
                .only("id", "first_name", "last_name", "citizen_id", "is_active")
                .first()
            )
        except Exception as exc:
            logger.error("Failed to load basic People profile for id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def get_citizen_id_by_id(user_id: str) -> Optional[str]:
        if not user_id:
            return None
        try:
            row = await PeopleUser.filter(id=user_id).values("citizen_id").first()
            return row.get("citizen_id") if row else None
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to load People citizen_id for id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def is_citizen_id_exist_and_is_first_login(citizen_id: str) -> Optional[Dict[str, Any]]:
        if not citizen_id:
            return None
        try:
            result = (
                await PeopleUser
                .filter(citizen_id=citizen_id, is_active=True)
                .values("citizen_id", "is_first_login", "password_hash")
            )
            return result[0] if result else None
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to inspect People profile citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def set_password(citizen_id: str, hashed_password: str) -> None:
        try:
            user = await PeopleUser.get(citizen_id=citizen_id, is_first_login=True, is_active=True)
            user.password_hash = hashed_password
            user.is_first_login = False
            await user.save()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to set password for People citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def get_user_for_management(user_id: str) -> Optional[PeopleUser]:
        if not user_id:
            return None
        try:
            return await PeopleUser.filter(id=user_id).first()
        except Exception as exc:
            logger.error("Failed to load People profile for management id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def get_user_by_citizen_id(citizen_id: str) -> Optional[PeopleUser]:
        if not citizen_id:
            return None
        try:
            return await PeopleUser.filter(citizen_id=citizen_id).first()
        except Exception as exc:
            logger.error("Failed to load People profile for citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def get_user_by_yuwa_osm_code(code: str) -> Optional[PeopleUser]:
        if not code:
            return None
        try:
            return await PeopleUser.filter(yuwa_osm_code=code).first()
        except Exception as exc:
            logger.error("Failed to load People profile for yuwa_osm_code=%s", code, exc_info=exc)
            raise

    @staticmethod
    async def set_password_by_id(
        user_id: str,
        hashed_password: str,
        *,
        mark_first_login: bool = False,
        reset_attempts: bool = True,
        reactivate: bool = True,
    ) -> bool:
        if not user_id:
            return False
        try:
            update_payload: Dict[str, Any] = {
                "password_hash": hashed_password,
                "updated_at": datetime.utcnow(),
                "is_first_login": bool(mark_first_login),
            }
            if reset_attempts:
                update_payload["password_attempts"] = 0
            if reactivate:
                update_payload["is_active"] = True
            updated = await PeopleUser.filter(id=user_id).update(**update_payload)
            return bool(updated)
        except Exception as exc:
            logger.error("Failed to update password for People id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def get_password_state(user_id: str):
        try:
            return (
                await PeopleUser
                .filter(id=user_id)
                .only("id", "password_hash", "password_attempts", "is_active")
                .first()
            )
        except Exception as exc:
            logger.error("Error retrieving password state for People %s: %s", user_id, exc)
            raise

    @staticmethod
    async def update_password_attempts(user_id: str, attempts: int, *, deactivate: bool = False) -> None:
        try:
            update_payload: Dict[str, Any] = {"password_attempts": attempts, "updated_at": datetime.utcnow()}
            if deactivate:
                update_payload["is_active"] = False
            await PeopleUser.filter(id=user_id).update(**update_payload)
        except Exception as exc:
            logger.error("Error updating password attempts for People %s: %s", user_id, exc)
            raise

    @staticmethod
    async def search_active_users(term: str, limit: int = 10, *, active_only: bool = True, offset: int = 0):
        if not term:
            return [], 0
        try:
            base_qs = (
                PeopleUser
                .all()
                .filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(citizen_id__icontains=term)
                    | Q(phone_number__icontains=term)
                )
            )
            if active_only:
                base_qs = base_qs.filter(is_active=True)
            total = await base_qs.count()
            query = (
                base_qs
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "phone_number",
                    "email",
                    "is_active",
                    "is_transferred",
                    "transferred_at",
                    "transferred_by",
                    "yuwa_osm_id",
                    "yuwa_osm_code",
                    "province_name",
                    "district_name",
                    "subdistrict_name",
                )
                .order_by("first_name")
                .offset(offset)
                .limit(limit)
            )
            items = await query
            return items, total
        except Exception as exc:
            logger.error("Failed to search People profiles", exc_info=exc)
            raise

    @staticmethod
    async def set_active_status(user_id: str, is_active: bool) -> bool:
        if not user_id:
            return False
        try:
            updated = await PeopleUser.filter(id=user_id).update(
                is_active=is_active,
                updated_at=datetime.utcnow(),
            )
            return bool(updated)
        except Exception as exc:
            logger.error("Failed to update active status for People user %s", user_id, exc_info=exc)
            raise

        @staticmethod
        async def update_user(user_id: str, payload: Dict[str, Any]) -> bool:
            if not user_id:
                return False
            if not payload:
                return True
            try:
                payload = dict(payload)
                payload.setdefault("updated_at", datetime.utcnow())
                updated = await PeopleUser.filter(id=user_id).update(**payload)
                return bool(updated)
            except Exception as exc:  # pragma: no cover - logging only
                logger.error("Failed to update People profile id=%s", user_id, exc_info=exc)
                raise

    @staticmethod
    async def exists_by_citizen_id(citizen_id: Optional[str], exclude_id: Optional[str] = None) -> bool:
        if not citizen_id:
            return False
        try:
            query = PeopleUser.filter(citizen_id=citizen_id)
            if exclude_id:
                query = query.exclude(id=exclude_id)
            return await query.exists()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to verify People citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def exists_by_yuwa_osm_code(code: Optional[str], exclude_id: Optional[str] = None) -> bool:
        if not code:
            return False
        try:
            query = PeopleUser.filter(yuwa_osm_code=code)
            if exclude_id:
                query = query.exclude(id=exclude_id)
            return await query.exists()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to verify People yuwa_osm_code=%s", code, exc_info=exc)
            raise

    @staticmethod
    async def get_latest_yuwa_osm_code(prefix: str) -> Optional[str]:
        if not prefix:
            return None
        try:
            record = (
                await PeopleUser
                .filter(yuwa_osm_code__startswith=prefix)
                .only("yuwa_osm_code")
                .order_by("-yuwa_osm_code")
                .first()
            )
            return record.yuwa_osm_code if record else None
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to load latest People yuwa_osm_code for prefix=%s", prefix, exc_info=exc)
            raise
