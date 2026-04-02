from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from tortoise.expressions import Q

from app.models.enum_models import Gender
from app.models.officer_model import OfficerProfile
from app.models.osm_model import OSMProfile
from app.models.yuwa_osm_model import YuwaOSMUser
from app.models.people_model import PeopleUser
from app.services.auth_me_service import AuthMeService
from app.services.user_service import UserService


class UserLookupService:
    """Cross-user search utilities for officer-facing lookup endpoints."""

    USER_TYPE_ALIASES = {
        "officer": "officer",
        "officers": "officer",
        "osm": "osm",
        "osms": "osm",
        "yuwa": "yuwa_osm",
        "yuwa_osm": "yuwa_osm",
        "yuwa-osm": "yuwa_osm",
        "people": "people",
        "person": "people",
        "persons": "people",
    }

    GENDER_ALIASES = {
        "male": Gender.MALE,
        "m": Gender.MALE,
        "ชาย": Gender.MALE,
        "female": Gender.FEMALE,
        "f": Gender.FEMALE,
        "หญิง": Gender.FEMALE,
        "woman": Gender.FEMALE,
        "other": Gender.OTHER,
        "o": Gender.OTHER,
        "อื่น": Gender.OTHER,
        "อื่นๆ": Gender.OTHER,
    }

    @classmethod
    def _normalize_user_type(cls, user_type: Optional[str]) -> Optional[str]:
        if user_type is None:
            return None
        value = str(user_type).strip().lower()
        if not value:
            return None
        normalized = cls.USER_TYPE_ALIASES.get(value)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_user_type")
        return normalized

    @classmethod
    def _resolve_gender(cls, gender: str) -> Tuple[Gender, str]:
        normalized = (gender or "").strip().lower()
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="gender_required")
        alias = cls.GENDER_ALIASES.get(normalized)
        if alias:
            return alias, alias.value
        try:
            enum_value = Gender(normalized)
            return enum_value, enum_value.value
        except ValueError as exc:  # pragma: no cover - validation only
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_gender") from exc

    @staticmethod
    def _page_response(
        items: List[Dict[str, Any]],
        *,
        total: int,
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:
        return {
            "items": items,
            "count": len(items),
            "total": total,
            "limit": max(limit, 0),
            "offset": max(offset, 0),
        }

    @classmethod
    def _empty_page(cls, *, limit: int, offset: int) -> Dict[str, Any]:
        return cls._page_response([], total=0, limit=limit, offset=offset)

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
    def _full_name(first_name: Optional[str], last_name: Optional[str]) -> str:
        parts = [part.strip() for part in (first_name or "", last_name or "") if part]
        return " ".join(parts)

    @classmethod
    def _summary_payload(
        cls,
        *,
        user_type: str,
        user_id: str,
        citizen_id: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        gender: Optional[Any],
        birth_date: Optional[date],
    ) -> Dict[str, Any]:
        normalized_gender = getattr(gender, "value", gender)
        age = cls._calculate_age(birth_date)
        return {
            "user_id": user_id,
            "user_type": user_type,
            "citizen_id": citizen_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": cls._full_name(first_name, last_name),
            "gender": normalized_gender,
            "birth_date": birth_date.isoformat() if birth_date else None,
            "age": age,
        }

    @classmethod
    async def _resolve_user_type_by_uuid(cls, user_uuid: str) -> Optional[str]:
        if not user_uuid:
            return None
        try:
            normalized = cls._normalize_uuid(user_uuid)
        except HTTPException:
            return None

        if await OfficerProfile.filter(id=normalized, deleted_at__isnull=True).exists():
            return "officer"
        if await OSMProfile.filter(id=normalized, deleted_at__isnull=True).exists():
            return "osm"
        if await YuwaOSMUser.filter(id=normalized, is_active=True).exists():
            return "yuwa_osm"
        if await PeopleUser.filter(id=normalized, is_active=True).exists():
            return "people"
        return None

    @classmethod
    async def _resolve_user_type_by_citizen_id(cls, citizen_id: str) -> Optional[str]:
        if not citizen_id:
            return None
        try:
            normalized = cls._normalize_citizen_id(citizen_id)
        except HTTPException:
            return None

        if await OfficerProfile.filter(citizen_id=normalized, deleted_at__isnull=True).exists():
            return "officer"
        if await OSMProfile.filter(citizen_id=normalized, deleted_at__isnull=True).exists():
            return "osm"
        if await YuwaOSMUser.filter(citizen_id=normalized, is_active=True).exists():
            return "yuwa_osm"
        if await PeopleUser.filter(citizen_id=normalized, is_active=True).exists():
            return "people"
        return None

    @classmethod
    async def find_users_by_uuid(
        cls,
        user_uuid: str,
        *,
        user_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized = cls._normalize_uuid(user_uuid)

        normalized_type = cls._normalize_user_type(user_type)
        results: List[Dict[str, Any]] = []

        if normalized_type in {None, "officer"}:
            officer = await OfficerProfile.filter(id=normalized, deleted_at__isnull=True).first()
            if officer:
                results.append(
                    cls._summary_payload(
                        user_type="officer",
                        user_id=str(officer.id),
                        citizen_id=officer.citizen_id,
                        first_name=officer.first_name,
                        last_name=officer.last_name,
                        gender=officer.gender,
                        birth_date=officer.birth_date,
                    )
                )

        if normalized_type in {None, "osm"}:
            osm = await OSMProfile.filter(id=normalized, deleted_at__isnull=True).first()
            if osm:
                results.append(
                    cls._summary_payload(
                        user_type="osm",
                        user_id=str(osm.id),
                        citizen_id=osm.citizen_id,
                        first_name=osm.first_name,
                        last_name=osm.last_name,
                        gender=osm.gender,
                        birth_date=osm.birth_date,
                    )
                )

        if normalized_type in {None, "yuwa_osm"}:
            yuwa = await YuwaOSMUser.filter(id=normalized, is_active=True).first()
            if yuwa:
                results.append(
                    cls._summary_payload(
                        user_type="yuwa_osm",
                        user_id=str(yuwa.id),
                        citizen_id=yuwa.citizen_id,
                        first_name=yuwa.first_name,
                        last_name=yuwa.last_name,
                        gender=yuwa.gender,
                        birth_date=yuwa.birthday,
                    )
                )

        if normalized_type in {None, "people"}:
            people = await PeopleUser.filter(id=normalized, is_active=True).first()
            if people:
                results.append(
                    cls._summary_payload(
                        user_type="people",
                        user_id=str(people.id),
                        citizen_id=people.citizen_id,
                        first_name=people.first_name,
                        last_name=people.last_name,
                        gender=people.gender,
                        birth_date=people.birthday,
                    )
                )

        return results

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        try:
            UUID(str(value))
            return True
        except (ValueError, TypeError, AttributeError):
            return False

    @classmethod
    def _normalize_uuid(cls, value: Optional[str]) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id_required")
        if not cls._is_valid_uuid(normalized):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_user_id")
        return normalized

    @staticmethod
    def _normalize_citizen_id(value: Optional[str]) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="citizen_id_required")
        if len(normalized) != 13 or not normalized.isdigit():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_citizen_id")
        return normalized

    @classmethod
    async def find_users_by_citizen_id(
        cls,
        citizen_id: str,
        *,
        user_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized = cls._normalize_citizen_id(citizen_id)

        normalized_type = cls._normalize_user_type(user_type)
        results: List[Dict[str, Any]] = []

        if normalized_type in {None, "officer"}:
            officer = await OfficerProfile.filter(citizen_id=normalized, deleted_at__isnull=True).first()
            if officer:
                results.append(
                    cls._summary_payload(
                        user_type="officer",
                        user_id=str(officer.id),
                        citizen_id=officer.citizen_id,
                        first_name=officer.first_name,
                        last_name=officer.last_name,
                        gender=officer.gender,
                        birth_date=officer.birth_date,
                    )
                )

        if normalized_type in {None, "osm"}:
            osm = await OSMProfile.filter(citizen_id=normalized, deleted_at__isnull=True).first()
            if osm:
                results.append(
                    cls._summary_payload(
                        user_type="osm",
                        user_id=str(osm.id),
                        citizen_id=osm.citizen_id,
                        first_name=osm.first_name,
                        last_name=osm.last_name,
                        gender=osm.gender,
                        birth_date=osm.birth_date,
                    )
                )

        if normalized_type in {None, "yuwa_osm"}:
            yuwa = await YuwaOSMUser.filter(citizen_id=normalized, is_active=True).first()
            if yuwa:
                results.append(
                    cls._summary_payload(
                        user_type="yuwa_osm",
                        user_id=str(yuwa.id),
                        citizen_id=yuwa.citizen_id,
                        first_name=yuwa.first_name,
                        last_name=yuwa.last_name,
                        gender=yuwa.gender,
                        birth_date=yuwa.birthday,
                    )
                )

        if normalized_type in {None, "people"}:
            people = await PeopleUser.filter(citizen_id=normalized, is_active=True).first()
            if people:
                results.append(
                    cls._summary_payload(
                        user_type="people",
                        user_id=str(people.id),
                        citizen_id=people.citizen_id,
                        first_name=people.first_name,
                        last_name=people.last_name,
                        gender=people.gender,
                        birth_date=people.birthday,
                    )
                )

        return results

    @classmethod
    def _base_queryset_for_type(cls, user_type: str):
        if user_type == "officer":
            return OfficerProfile.filter(deleted_at__isnull=True)
        if user_type == "osm":
            return OSMProfile.filter(deleted_at__isnull=True)
        if user_type == "yuwa_osm":
            return YuwaOSMUser.filter(is_active=True)
        return PeopleUser.filter(is_active=True)

    @classmethod
    def _summary_from_record(cls, user_type: str, record: Any) -> Dict[str, Any]:
        if user_type == "officer":
            return cls._summary_payload(
                user_type="officer",
                user_id=str(record.id),
                citizen_id=record.citizen_id,
                first_name=record.first_name,
                last_name=record.last_name,
                gender=record.gender,
                birth_date=record.birth_date,
            )
        if user_type == "osm":
            return cls._summary_payload(
                user_type="osm",
                user_id=str(record.id),
                citizen_id=record.citizen_id,
                first_name=record.first_name,
                last_name=record.last_name,
                gender=record.gender,
                birth_date=record.birth_date,
            )
        if user_type == "yuwa_osm":
            return cls._summary_payload(
                user_type="yuwa_osm",
                user_id=str(record.id),
                citizen_id=record.citizen_id,
                first_name=record.first_name,
                last_name=record.last_name,
                gender=record.gender,
                birth_date=getattr(record, "birthday", None),
            )
        return cls._summary_payload(
            user_type="people",
            user_id=str(record.id),
            citizen_id=record.citizen_id,
            first_name=record.first_name,
            last_name=record.last_name,
            gender=record.gender,
            birth_date=getattr(record, "birthday", None),
        )

    @classmethod
    def _age_filtered_queryset(
        cls,
        user_type: str,
        *,
        min_birth_date: Optional[date],
        max_birth_date: Optional[date],
    ):
        field_name = "birth_date" if user_type in {"officer", "osm"} else "birthday"
        queryset = cls._base_queryset_for_type(user_type)
        if user_type in {"officer", "osm"}:
            queryset = queryset.filter(birth_date__isnull=False)
        else:
            queryset = queryset.filter(birthday__isnull=False)
        if min_birth_date is not None:
            queryset = queryset.filter(**{f"{field_name}__gte": min_birth_date})
        if max_birth_date is not None:
            queryset = queryset.filter(**{f"{field_name}__lte": max_birth_date})
        return queryset, field_name

    @classmethod
    def _gender_filtered_queryset(
        cls,
        user_type: str,
        *,
        gender_enum: Gender,
        gender_text: str,
    ):
        if user_type in {"officer", "osm"}:
            return cls._base_queryset_for_type(user_type).filter(gender=gender_enum)
        return cls._base_queryset_for_type(user_type).filter(
            Q(gender__iexact=gender_text) | Q(gender=gender_text)
        )

    @classmethod
    async def list_users(
        cls,
        *,
        limit: int,
        offset: int,
        user_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        limit = max(limit, 0)
        offset = max(offset, 0)
        if limit == 0:
            return cls._empty_page(limit=limit, offset=offset)

        normalized_type = cls._normalize_user_type(user_type)
        type_order = [normalized_type] if normalized_type else ["officer", "osm", "yuwa_osm", "people"]

        totals: Dict[str, int] = {}
        for type_id in type_order:
            totals[type_id] = await cls._base_queryset_for_type(type_id).count()

        total = sum(totals.values())
        if total == 0:
            return cls._empty_page(limit=limit, offset=offset)

        items: List[Dict[str, Any]] = []
        remaining_offset = offset
        remaining_limit = limit

        for type_id in type_order:
            type_total = totals[type_id]
            if type_total == 0:
                continue
            if remaining_offset >= type_total:
                remaining_offset -= type_total
                continue

            type_query = cls._base_queryset_for_type(type_id).order_by("-created_at")

            select_fields = ["id", "citizen_id", "first_name", "last_name", "gender"]
            if type_id in {"officer", "osm"}:
                select_fields.append("birth_date")
            else:
                select_fields.append("birthday")

            type_query = type_query.only(*select_fields)

            if remaining_offset:
                type_query = type_query.offset(remaining_offset)

            type_query = type_query.limit(remaining_limit)
            records = await type_query
            for record in records:
                items.append(cls._summary_from_record(type_id, record))

            remaining_limit = limit - len(items)
            remaining_offset = 0
            if remaining_limit <= 0:
                break

        return cls._page_response(items, total=total, limit=limit, offset=offset)

    @classmethod
    def _birthdate_range_for_age(
        cls, *, min_age: Optional[int], max_age: Optional[int]
    ) -> Tuple[Optional[date], Optional[date]]:
        today = date.today()
        max_birth_date: Optional[date] = None  # birth_date <= max_birth_date (age >= min_age)
        min_birth_date: Optional[date] = None  # birth_date >= min_birth_date (age <= max_age)

        if min_age is not None:
            year = today.year - min_age
            try:
                max_birth_date = today.replace(year=year)
            except ValueError:
                max_birth_date = today.replace(year=year, month=2, day=28)

        if max_age is not None:
            year = today.year - max_age
            try:
                min_birth_date = today.replace(year=year)
            except ValueError:
                min_birth_date = today.replace(year=year, month=2, day=28)

        return min_birth_date, max_birth_date

    @classmethod
    def _age_within_range(
        cls,
        age: Optional[int],
        *,
        min_age: Optional[int],
        max_age: Optional[int],
    ) -> bool:
        if age is None:
            return False
        if min_age is not None and age < min_age:
            return False
        if max_age is not None and age > max_age:
            return False
        return True

    @classmethod
    async def find_users_by_age(
        cls,
        *,
        min_age: Optional[int],
        max_age: Optional[int],
        limit: int,
        offset: int,
        user_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        limit = max(limit, 0)
        offset = max(offset, 0)
        if limit == 0:
            return cls._empty_page(limit=limit, offset=offset)

        min_birth_date, max_birth_date = cls._birthdate_range_for_age(min_age=min_age, max_age=max_age)
        normalized_type = cls._normalize_user_type(user_type)
        type_order = [normalized_type] if normalized_type else ["officer", "osm", "yuwa_osm", "people"]

        totals: Dict[str, int] = {}
        for type_id in type_order:
            queryset, _ = cls._age_filtered_queryset(
                type_id,
                min_birth_date=min_birth_date,
                max_birth_date=max_birth_date,
            )
            totals[type_id] = await queryset.count()

        total = sum(totals.values())
        if total == 0:
            return cls._empty_page(limit=limit, offset=offset)

        items: List[Dict[str, Any]] = []
        remaining_offset = offset
        remaining_limit = limit

        for type_id in type_order:
            type_total = totals[type_id]
            if type_total == 0:
                continue
            if remaining_offset >= type_total:
                remaining_offset -= type_total
                continue

            queryset, birth_field = cls._age_filtered_queryset(
                type_id,
                min_birth_date=min_birth_date,
                max_birth_date=max_birth_date,
            )

            ordering_field = birth_field
            queryset = queryset.order_by(ordering_field)
            if remaining_offset:
                queryset = queryset.offset(remaining_offset)
            queryset = queryset.limit(remaining_limit).only(
                "id",
                "citizen_id",
                "first_name",
                "last_name",
                "gender",
                birth_field,
            )

            records = await queryset
            for record in records:
                items.append(cls._summary_from_record(type_id, record))

            remaining_limit = limit - len(items)
            remaining_offset = 0
            if remaining_limit <= 0:
                break

        return cls._page_response(items, total=total, limit=limit, offset=offset)

    @classmethod
    async def find_users_by_gender(
        cls,
        gender: str,
        *,
        limit: int,
        offset: int,
        user_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        limit = max(limit, 0)
        offset = max(offset, 0)
        gender_enum, gender_text = cls._resolve_gender(gender)

        if limit == 0:
            return cls._empty_page(limit=limit, offset=offset)

        normalized_type = cls._normalize_user_type(user_type)
        type_order = [normalized_type] if normalized_type else ["officer", "osm", "yuwa_osm", "people"]

        totals: Dict[str, int] = {}
        for type_id in type_order:
            queryset = cls._gender_filtered_queryset(
                type_id,
                gender_enum=gender_enum,
                gender_text=gender_text,
            )
            totals[type_id] = await queryset.count()

        total = sum(totals.values())
        if total == 0:
            return cls._empty_page(limit=limit, offset=offset)

        items: List[Dict[str, Any]] = []
        remaining_offset = offset
        remaining_limit = limit

        for type_id in type_order:
            type_total = totals[type_id]
            if type_total == 0:
                continue
            if remaining_offset >= type_total:
                remaining_offset -= type_total
                continue

            queryset = cls._gender_filtered_queryset(
                type_id,
                gender_enum=gender_enum,
                gender_text=gender_text,
            ).order_by("first_name")

            if remaining_offset:
                queryset = queryset.offset(remaining_offset)

            select_fields = ["id", "citizen_id", "first_name", "last_name", "gender"]
            if type_id in {"officer", "osm"}:
                select_fields.append("birth_date")
            else:
                select_fields.append("birthday")

            queryset = queryset.limit(remaining_limit).only(*select_fields)
            records = await queryset
            for record in records:
                items.append(cls._summary_from_record(type_id, record))

            remaining_limit = limit - len(items)
            remaining_offset = 0
            if remaining_limit <= 0:
                break

        return cls._page_response(items, total=total, limit=limit, offset=offset)

    @classmethod
    async def _build_detail_payload(
        cls,
        user_id: str,
        user_type: str,
    ) -> Dict[str, Any]:
        user_info = await UserService.get_user_info(user_id, None, user_type)
        if not user_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

        user_info.setdefault("client_id", None)
        user_info.setdefault("scopes", [])
        user_info.setdefault("token_scopes", [])
        user_info.setdefault("is_admin", user_type == "officer")

        permission_scope = await AuthMeService.build_permission_scope(user_id, user_type, user_info.copy())
        user_info["permission_scope"] = permission_scope
        user_info["client_context"] = None
        user_info.setdefault("accessible_projects", [])

        return user_info

    @classmethod
    async def get_user_detail_by_uuid(cls, user_uuid: str, user_type: Optional[str]) -> Dict[str, Any]:
        normalized_uuid = cls._normalize_uuid(user_uuid)
        effective_user_type = user_type or await cls._resolve_user_type_by_uuid(normalized_uuid)
        if not effective_user_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
        return await cls._build_detail_payload(normalized_uuid, effective_user_type)

    @classmethod
    async def get_user_detail_by_citizen_id(
        cls,
        citizen_id: str,
        user_type: Optional[str],
    ) -> Dict[str, Any]:
        normalized_citizen_id = cls._normalize_citizen_id(citizen_id)
        effective_user_type = user_type or await cls._resolve_user_type_by_citizen_id(normalized_citizen_id)
        if not effective_user_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

        lookup_map = {
            "officer": OfficerProfile,
            "osm": OSMProfile,
            "yuwa_osm": YuwaOSMUser,
            "people": PeopleUser,
        }
        model = lookup_map[effective_user_type]
        filters = {"citizen_id": normalized_citizen_id}
        if effective_user_type == "officer":
            filters["deleted_at__isnull"] = True
        elif effective_user_type == "osm":
            filters["deleted_at__isnull"] = True
        else:
            filters["is_active"] = True
        record = await model.filter(**filters).only("id").first()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
        return await cls._build_detail_payload(str(record.id), effective_user_type)

    @classmethod
    async def get_user_detail(cls, user_id: str, user_type: Optional[str]) -> Dict[str, Any]:
        if cls._is_valid_uuid(user_id):
            normalized_uuid = cls._normalize_uuid(user_id)
            effective_user_type = user_type or await cls._resolve_user_type_by_uuid(normalized_uuid)
            if not effective_user_type:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
            return await cls._build_detail_payload(normalized_uuid, effective_user_type)

        return await cls.get_user_detail_by_citizen_id(user_id, user_type)
