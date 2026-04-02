from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from tortoise.expressions import Q
from tortoise.functions import Count

from app.models.gen_h_model import GenHUser

logger = logging.getLogger(__name__)

_SORTABLE_FIELDS = {
    "gen_h_code", "first_name", "last_name", "province_name",
    "school", "points", "created_at", "updated_at",
}


class GenHUserRepository:

    @staticmethod
    async def get_by_id(user_id: UUID) -> Optional[GenHUser]:
        return await GenHUser.get_or_none(id=user_id)

    @staticmethod
    async def get_by_gen_h_code(code: str) -> Optional[GenHUser]:
        return await GenHUser.get_or_none(gen_h_code=code)

    @staticmethod
    async def get_by_citizen_id(citizen_id: str) -> Optional[GenHUser]:
        return await GenHUser.get_or_none(citizen_id=citizen_id)

    @staticmethod
    async def exists_by_gen_h_code(code: str) -> bool:
        return await GenHUser.exists(gen_h_code=code)

    @staticmethod
    async def create_user(**kwargs) -> GenHUser:
        return await GenHUser.create(**kwargs)

    @staticmethod
    async def update_user(user: GenHUser, **kwargs) -> GenHUser:
        for k, v in kwargs.items():
            setattr(user, k, v)
        await user.save()
        return user

    @staticmethod
    async def delete_user(user: GenHUser) -> None:
        await user.delete()

    @staticmethod
    async def list_users(
        *,
        search: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        gender: Optional[str] = None,
        school: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[GenHUser], int]:
        qs = GenHUser.all()

        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(gen_h_code__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(school__icontains=search)
            )

        if province_code:
            qs = qs.filter(province_code=province_code)
        if district_code:
            qs = qs.filter(district_code=district_code)
        if gender:
            qs = qs.filter(gender=gender)
        if school:
            qs = qs.filter(school__icontains=school)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        total = await qs.count()

        field = sort_by if sort_by in _SORTABLE_FIELDS else "created_at"
        order = f"-{field}" if sort_order == "desc" else field
        offset = (page - 1) * per_page

        users = await qs.order_by(order).offset(offset).limit(per_page)
        return users, total

    # ── Auth methods ────────────────────────────────────────────────────

    @staticmethod
    async def is_gen_h_code_exist_and_is_first_login(gen_h_code: str) -> Optional[dict]:
        user = await GenHUser.get_or_none(gen_h_code=gen_h_code, is_active=True)
        if not user:
            return None
        return {
            "is_first_login": user.is_first_login,
            "password_hash": user.password_hash,
        }

    @staticmethod
    async def find_basic_profile_by_gen_h_code(gen_h_code: str) -> Optional[GenHUser]:
        return await GenHUser.get_or_none(gen_h_code=gen_h_code, is_active=True)

    @staticmethod
    async def find_basic_profile_by_citizen_id(citizen_id: str) -> Optional[GenHUser]:
        return await GenHUser.get_or_none(citizen_id=citizen_id, is_active=True)

    @staticmethod
    async def find_basic_profile_by_id(user_id: UUID) -> Optional[GenHUser]:
        return await GenHUser.get_or_none(id=user_id, is_active=True)

    @staticmethod
    async def set_password(gen_h_code: str, hashed_password: str) -> None:
        await GenHUser.filter(gen_h_code=gen_h_code).update(
            password_hash=hashed_password,
            is_first_login=False,
            password_attempts=0,
        )

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
        update_payload: Dict[str, Any] = {
            "password_hash": hashed_password,
            "updated_at": datetime.utcnow(),
            "is_first_login": bool(mark_first_login),
        }
        if reset_attempts:
            update_payload["password_attempts"] = 0
        if reactivate:
            update_payload["is_active"] = True
        updated = await GenHUser.filter(id=user_id).update(**update_payload)
        return bool(updated)

    @staticmethod
    async def get_password_state(user_id: str) -> Optional[GenHUser]:
        return (
            await GenHUser
            .filter(id=user_id)
            .only("id", "password_hash", "password_attempts", "is_active")
            .first()
        )

    @staticmethod
    async def update_password_attempts(user_id: str, attempts: int, *, deactivate: bool = False) -> None:
        update_payload: Dict[str, Any] = {"password_attempts": attempts, "updated_at": datetime.utcnow()}
        if deactivate:
            update_payload["is_active"] = False
        await GenHUser.filter(id=user_id).update(**update_payload)

    @staticmethod
    async def increment_password_attempts(gen_h_code: str) -> None:
        from tortoise.expressions import F
        await GenHUser.filter(gen_h_code=gen_h_code).update(
            password_attempts=F("password_attempts") + 1
        )

    @staticmethod
    async def reset_password_attempts(gen_h_code: str) -> None:
        await GenHUser.filter(gen_h_code=gen_h_code).update(password_attempts=0)

    @staticmethod
    async def search_active_users(term: str, limit: int = 10, *, active_only: bool = True, offset: int = 0):
        if not term:
            return [], 0
        base_qs = GenHUser.all().filter(
            Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(gen_h_code__icontains=term)
            | Q(phone_number__icontains=term)
        )
        if active_only:
            base_qs = base_qs.filter(is_active=True)
        total = await base_qs.count()
        records = await base_qs.order_by("-created_at").offset(offset).limit(limit)
        return records, total

    @staticmethod
    async def summary(
        province_code: Optional[str] = None,
    ) -> dict:
        qs = GenHUser.all()
        if province_code:
            qs = qs.filter(province_code=province_code)

        total = await qs.count()
        active = await qs.filter(is_active=True).count()
        male = await qs.filter(gender="male").count()
        female = await qs.filter(gender="female").count()
        lgbtq_plus = await qs.filter(gender="lgbtq+").count()
        transferred = await qs.exclude(yuwa_osm_user_id=None).count()

        by_province_raw = (
            await qs.annotate(cnt=Count("id"))
            .group_by("province_name", "province_code")
            .values("province_name", "province_code", "cnt")
        )
        by_province = sorted(by_province_raw, key=lambda x: -(x.get("cnt") or 0))

        return {
            "total": total,
            "active": active,
            "male": male,
            "female": female,
            "lgbtq_plus": lgbtq_plus,
            "transferred_to_yuwa": transferred,
            "by_province": by_province,
        }
