from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from collections import Counter
from datetime import date, datetime

from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.functions import Count

from app.models.enum_models import ApprovalStatus
from app.models.yuwa_osm_model import YuwaOSMUser
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class YuwaOSMUserRepository:
    """Data access helpers for Yuwa OSM users participating in SSO."""

    @staticmethod
    async def find_basic_profile_by_gen_h_code(gen_h_code: str) -> Optional[YuwaOSMUser]:
        """Login lookup: find active yuwa_osm user by their original gen_h_code."""
        if not gen_h_code:
            return None
        try:
            return (
                await YuwaOSMUser
                .filter(gen_h_code=gen_h_code, is_active=True)
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "gen_h_code",
                    "province_code",
                    "district_code",
                    "subdistrict_code",
                    "password_hash",
                    "is_first_login",
                    "is_active",
                )
                .first()
            )
        except Exception as exc:
            logger.error("Failed to load Yuwa profile for gen_h_code=%s", gen_h_code, exc_info=exc)
            raise

    @staticmethod
    async def find_basic_profile_by_citizen_id(citizen_id: str) -> Optional[YuwaOSMUser]:
        if not citizen_id:
            return None
        try:
            return (
                await YuwaOSMUser
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
            logger.error("Failed to load Yuwa profile for citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def find_profile_by_id(user_id: str) -> Optional[YuwaOSMUser]:
        try:
            return await YuwaOSMUser.filter(id=user_id, is_active=True).first()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to load Yuwa profile for id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def find_basic_profile_by_id(user_id: str) -> Optional[YuwaOSMUser]:
        if not user_id:
            return None
        try:
            return (
                await YuwaOSMUser
                .filter(id=user_id)
                .only("id", "first_name", "last_name", "citizen_id", "is_active")
                .first()
            )
        except Exception as exc:
            logger.error("Failed to load basic Yuwa profile for id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def is_citizen_id_exist_and_is_first_login(citizen_id: str) -> Optional[Dict[str, Any]]:
        if not citizen_id:
            return None
        try:
            result = (
                await YuwaOSMUser
                .filter(citizen_id=citizen_id, is_active=True)
                .values("citizen_id", "is_first_login", "password_hash")
            )
            return result[0] if result else None
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to inspect Yuwa profile citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def set_password(citizen_id: str, hashed_password: str) -> None:
        try:
            user = await YuwaOSMUser.get(citizen_id=citizen_id, is_first_login=True, is_active=True)
            user.password_hash = hashed_password
            user.is_first_login = False
            await user.save()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to set password for Yuwa citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def get_user_for_management(user_id: str) -> Optional[YuwaOSMUser]:
        if not user_id:
            return None
        try:
            return await (
                YuwaOSMUser
                .filter(id=user_id)
                .first()
            )
        except Exception as exc:
            logger.error("Failed to load Yuwa profile for management id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def get_user_by_citizen_id(citizen_id: str) -> Optional[YuwaOSMUser]:
        if not citizen_id:
            return None
        try:
            return await YuwaOSMUser.filter(citizen_id=citizen_id).first()
        except Exception as exc:
            logger.error("Failed to load Yuwa profile for citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def get_user_by_source_people_id(people_id: str) -> Optional[YuwaOSMUser]:
        if not people_id:
            return None
        try:
            return await YuwaOSMUser.filter(source_people_id=people_id).first()
        except Exception as exc:
            logger.error("Failed to load Yuwa profile for source_people_id=%s", people_id, exc_info=exc)
            raise

    @staticmethod
    async def get_user_by_yuwa_osm_code(code: str) -> Optional[YuwaOSMUser]:
        if not code:
            return None
        try:
            return await YuwaOSMUser.filter(yuwa_osm_code=code).first()
        except Exception as exc:
            logger.error("Failed to load Yuwa profile for yuwa_osm_code=%s", code, exc_info=exc)
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
            }
            update_payload["is_first_login"] = bool(mark_first_login)
            if reset_attempts:
                update_payload["password_attempts"] = 0
            if reactivate:
                update_payload["is_active"] = True
            updated = await YuwaOSMUser.filter(id=user_id).update(**update_payload)
            return bool(updated)
        except Exception as exc:
            logger.error("Failed to update password for Yuwa id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def get_password_state(user_id: str):
        try:
            return (
                await YuwaOSMUser
                .filter(id=user_id)
                .only("id", "password_hash", "password_attempts", "is_active")
                .first()
            )
        except Exception as exc:
            logger.error("Error retrieving password state for Yuwa %s: %s", user_id, exc)
            raise

    @staticmethod
    async def update_password_attempts(user_id: str, attempts: int, *, deactivate: bool = False) -> None:
        try:
            update_payload: Dict[str, Any] = {"password_attempts": attempts, "updated_at": datetime.utcnow()}
            if deactivate:
                update_payload["is_active"] = False
            await YuwaOSMUser.filter(id=user_id).update(**update_payload)
        except Exception as exc:
            logger.error("Error updating password attempts for Yuwa %s: %s", user_id, exc)
            raise

    @staticmethod
    async def get_citizen_id_by_id(user_id: str) -> Optional[str]:
        try:
            record = await YuwaOSMUser.filter(id=user_id).only("citizen_id").first()
            return record.citizen_id if record else None
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to resolve Yuwa citizen id for user=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def exists_by_phone(phone_number: str, exclude_id: Optional[str] = None) -> bool:
        if not phone_number:
            return False
        try:
            query = YuwaOSMUser.filter(phone_number=phone_number)
            if exclude_id:
                query = query.exclude(id=exclude_id)
            return await query.exists()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to verify Yuwa phone_number=%s", phone_number, exc_info=exc)
            raise

    @staticmethod
    async def exists_by_citizen_id(citizen_id: Optional[str], exclude_id: Optional[str] = None) -> bool:
        if not citizen_id:
            return False
        try:
            query = YuwaOSMUser.filter(citizen_id=citizen_id)
            if exclude_id:
                query = query.exclude(id=exclude_id)
            return await query.exists()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to verify Yuwa citizen_id=%s", citizen_id, exc_info=exc)
            raise

    @staticmethod
    async def exists_by_yuwa_osm_code(code: Optional[str], exclude_id: Optional[str] = None) -> bool:
        if not code:
            return False
        try:
            query = YuwaOSMUser.filter(yuwa_osm_code=code)
            if exclude_id:
                query = query.exclude(id=exclude_id)
            return await query.exists()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to verify Yuwa yuwa_osm_code=%s", code, exc_info=exc)
            raise

    @staticmethod
    async def get_latest_yuwa_osm_code(prefix: str) -> Optional[str]:
        if not prefix:
            return None
        try:
            record = (
                await YuwaOSMUser
                .filter(yuwa_osm_code__startswith=prefix)
                .only("yuwa_osm_code")
                .order_by("-yuwa_osm_code")
                .first()
            )
            return record.yuwa_osm_code if record else None
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to load latest Yuwa yuwa_osm_code for prefix=%s", prefix, exc_info=exc)
            raise

    @staticmethod
    async def search_active_users(term: str, limit: int = 10, *, active_only: bool = True, offset: int = 0):
        if not term:
            return [], 0
        try:
            base_qs = (
                YuwaOSMUser
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
                    "province_name",
                    "district_name",
                    "subdistrict_name",
                    "school",
                    "organization",
                )
                .order_by("first_name")
                .offset(offset)
                .limit(limit)
            )
            items = await query
            return items, total
        except Exception as exc:
            logger.error("Failed to search Yuwa profiles", exc_info=exc)
            raise

    @staticmethod
    async def set_active_status(user_id: str, is_active: bool) -> bool:
        if not user_id:
            return False
        try:
            updated = await YuwaOSMUser.filter(id=user_id).update(
                is_active=is_active,
                updated_at=datetime.utcnow(),
            )
            return bool(updated)
        except Exception as exc:
            logger.error("Failed to update active status for Yuwa user %s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def create_user(payload: Dict[str, Any]) -> YuwaOSMUser:
        try:
            return await YuwaOSMUser.create(**payload)
        except IntegrityError as exc:
            logger.error("Integrity error when creating Yuwa profile", exc_info=exc)
            raise
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to create Yuwa profile", exc_info=exc)
            raise

    @staticmethod
    async def list_users(
        *,
        page: int,
        limit: int,
        search: Optional[str] = None,
        approval_status: Optional[str] = None,
        is_active: Optional[bool] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        order_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[YuwaOSMUser], int]:
        try:
            query = YuwaOSMUser.all()

            if search:
                term = search.strip()
                if term:
                    status_bool, status_approval = YuwaOSMUserRepository._map_status_search(term)
                    if status_bool is not None or status_approval is not None:
                        if status_bool is not None:
                            query = query.filter(is_active=status_bool)
                        if status_approval is not None:
                            query = query.filter(approval_status=status_approval)
                    else:
                        query = query.filter(
                            Q(first_name__icontains=term)
                            | Q(last_name__icontains=term)
                            | Q(phone_number__icontains=term)
                            | Q(citizen_id__icontains=term)
                            | Q(approval_status__icontains=term.lower())
                        )

            if approval_status:
                query = query.filter(approval_status=str(approval_status).lower())

            if is_active is not None:
                query = query.filter(is_active=is_active)

            if province_code:
                query = query.filter(province_code=province_code)
            if district_code:
                query = query.filter(district_code=district_code)
            if subdistrict_code:
                query = query.filter(subdistrict_code=subdistrict_code)

            total = await query.count()

            allowed_order_fields = {
                "created_at",
                "updated_at",
                "first_name",
                "last_name",
                "citizen_id",
            }
            order_field = order_by if order_by in allowed_order_fields else "created_at"
            if sort_dir.lower() == "desc":
                order_field = f"-{order_field}"

            offset = (page - 1) * limit if page > 1 else 0
            records = await query.order_by(order_field).offset(offset).limit(limit)
            return list(records), total
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to list Yuwa profiles", exc_info=exc)
            raise

    @staticmethod
    def _apply_summary_filters(
        query,
        *,
        province: Optional[str] = None,
        province_code: Optional[str] = None,
        province_name: Optional[str] = None,
        birthday: Optional[date] = None,
        school: Optional[str] = None,
        organization: Optional[str] = None,
        approval_status: Optional[str] = None,
        min_birth_date: Optional[date] = None,
        max_birth_date: Optional[date] = None,
    ):
        if province:
            candidate = province.strip()
            if candidate:
                query = query.filter(Q(province_code=candidate) | Q(province_name__iexact=candidate))

        if province_code:
            query = query.filter(province_code=province_code)

        if province_name:
            query = query.filter(province_name__iexact=province_name)

        if birthday:
            query = query.filter(birthday=birthday)

        if school:
            query = query.filter(school__icontains=school.strip())

        if organization:
            query = query.filter(organization__icontains=organization.strip())

        if approval_status:
            query = query.filter(approval_status=str(approval_status).lower())

        if min_birth_date is not None or max_birth_date is not None:
            query = query.filter(birthday__isnull=False)
            if min_birth_date is not None:
                query = query.filter(birthday__gte=min_birth_date)
            if max_birth_date is not None:
                query = query.filter(birthday__lte=max_birth_date)

        return query

    @staticmethod
    def _calculate_age(birth_date: Optional[date]) -> Optional[int]:
        if not birth_date:
            return None
        today = date.today()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return max(age, 0)

    @staticmethod
    async def summary(
        *,
        province: Optional[str] = None,
        province_code: Optional[str] = None,
        province_name: Optional[str] = None,
        birthday: Optional[date] = None,
        school: Optional[str] = None,
        organization: Optional[str] = None,
        approval_status: Optional[str] = None,
        min_birth_date: Optional[date] = None,
        max_birth_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        try:
            base_query = YuwaOSMUserRepository._apply_summary_filters(
                YuwaOSMUser.all(),
                province=province,
                province_code=province_code,
                province_name=province_name,
                birthday=birthday,
                school=school,
                organization=organization,
                approval_status=approval_status,
                min_birth_date=min_birth_date,
                max_birth_date=max_birth_date,
            )

            total = await base_query.count()
            active = await base_query.filter(is_active=True).count()
            inactive = await base_query.filter(is_active=False).count()

            now = datetime.utcnow()
            month_start = datetime(now.year, now.month, 1)
            if now.month == 12:
                next_month_start = datetime(now.year + 1, 1, 1)
            else:
                next_month_start = datetime(now.year, now.month + 1, 1)

            new_this_month = await (
                base_query
                .filter(created_at__gte=month_start, created_at__lt=next_month_start)
                .count()
            )
            existing_members = max(total - new_this_month, 0)

            approval_summary = await (
                base_query
                .annotate(total=Count("id"))
                .group_by("approval_status")
                .values("approval_status", "total")
            )

            province_summary = await (
                base_query
                .annotate(total=Count("id"))
                .group_by("province_code", "province_name")
                .values("province_code", "province_name", "total")
            )

            school_summary = await (
                base_query
                .annotate(total=Count("id"))
                .group_by("school")
                .values("school", "total")
            )

            organization_summary = await (
                base_query
                .annotate(total=Count("id"))
                .group_by("organization")
                .values("organization", "total")
            )

            birthdays = await base_query.filter(birthday__isnull=False).values_list("birthday", flat=True)
            birthday_counts = Counter(birthdays)
            birthday_summary = [
                {
                    "birthday": day.isoformat() if day else None,
                    "total": count,
                }
                for day, count in sorted(birthday_counts.items(), key=lambda item: item[0] or date.min)
            ]

            age_counts = Counter(
                age for age in (YuwaOSMUserRepository._calculate_age(day) for day in birthdays) if age is not None
            )
            age_summary = [
                {"age": age, "total": count}
                for age, count in sorted(age_counts.items(), key=lambda item: item[0])
            ]

            approval_summary = sorted(
                approval_summary,
                key=lambda row: (row.get("approval_status") or ""),
            )
            province_summary = sorted(
                province_summary,
                key=lambda row: (row.get("province_code") or "", row.get("province_name") or ""),
            )
            school_summary = sorted(
                school_summary,
                key=lambda row: (row.get("school") or ""),
            )

            organization_summary = sorted(
                organization_summary,
                key=lambda row: (row.get("organization") or ""),
            )

            return {
                "total_members": total,
                "existing_members": existing_members,
                "new_members_this_month": new_this_month,
                "total": total,
                "active": active,
                "inactive": inactive,
                "approval_status": approval_summary,
                "province": province_summary,
                "school": school_summary,
                "organization": organization_summary,
                "birthday": birthday_summary,
                "age": age_summary,
            }
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to summarize Yuwa profiles", exc_info=exc)
            raise

    @staticmethod
    def _map_status_search(term: str) -> Tuple[Optional[bool], Optional[str]]:
        keyword = term.strip().lower()
        if not keyword:
            return None, None

        if keyword in {"active", "ใช้งาน", "true", "1"}:
            return True, None
        if keyword in {"inactive", "ไม่ใช้งาน", "false", "0"}:
            return False, None

        if keyword in {"approved", "อนุมัติ"}:
            return None, ApprovalStatus.APPROVED.value
        if keyword in {"pending", "รออนุมัติ", "รอ"}:
            return None, ApprovalStatus.PENDING.value
        if keyword in {"rejected", "ปฏิเสธ", "ไม่อนุมัติ"}:
            return None, ApprovalStatus.REJECTED.value
        if keyword in {"retired", "พ้นสภาพ"}:
            return None, ApprovalStatus.RETIRED.value

        return None, None

    @staticmethod
    async def update_user(user_id: str, payload: Dict[str, Any]) -> bool:
        if not payload:
            return True
        try:
            payload = dict(payload)
            payload.setdefault("updated_at", datetime.utcnow())
            updated = await YuwaOSMUser.filter(id=user_id).update(**payload)
            return bool(updated)
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to update Yuwa profile id=%s", user_id, exc_info=exc)
            raise

    @staticmethod
    async def delete_user(user_id: str) -> bool:
        try:
            deleted = await YuwaOSMUser.filter(id=user_id).delete()
            return bool(deleted)
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to delete Yuwa profile id=%s", user_id, exc_info=exc)
            raise
