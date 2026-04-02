from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple
from uuid import UUID

from tortoise.expressions import Q

from app.models.officer_model import OfficerProfile
from app.models.enum_models import ApprovalStatus
from app.utils.constant import ALLOWED_SORT_FIELDS
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

class OfficerProfileRepository:
    _RELATED_FIELDS: Iterable[str] = (
        "prefix",
        "position",
        "province",
        "district",
        "district__province",
        "subdistrict",
        "subdistrict__district",
        "subdistrict__district__province",
        "municipality",
        "health_area",
        "health_service",
    )

    @classmethod
    def _with_related(cls, queryset):
        return queryset.prefetch_related(*cls._RELATED_FIELDS)

    @staticmethod
    async def find_officer_basic_profile_by_citizen_id(citizen_id: str):
        """Return minimal officer profile data for authentication."""
        if not citizen_id:
            return None
        try:
            return (
                await OfficerProfile
                .filter(
                    citizen_id=citizen_id,
                    is_active=True,
                    approval_status=ApprovalStatus.APPROVED.value,
                    deleted_at__isnull=True,
                )
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "province_id",
                    "district_id",
                    "subdistrict_id",
                    "password_hash",
                    "is_first_login",
                    "is_active",
                    "approval_status",
                )
                .first()
            )
        except Exception as exc:
            logger.error("Error finding Officer profile by citizen id: %s", exc)
            raise
    
    async def find_officer_profile_by_credential_user_id(user_credential_id: str):
        """
        ดึง Officer Profile เฉพาะ basic fields สำหรับ login validation
        """
        logger.info(f"Looking for Officer profile with user_id: {user_credential_id}")
        
        try:
            # ใช้ .only() สำหรับ basic fields เท่านั้น และหลีกเลี่ยง exception กรณีไม่พบ
            officer_profile = (
                await OfficerProfile
                .filter(id=user_credential_id, deleted_at__isnull=True)
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "phone",
                    "email",
                    "gender",
                    "birth_date",
                    "province_id",
                    "district_id",
                    "subdistrict_id",
                )
                .first()
            )
            logger.info(f"Found Officer profile: {officer_profile}")
            return officer_profile
        except Exception as e:
            logger.error(f"Error finding Officer profile: {e}")
            raise e

    @staticmethod
    async def get_citizen_id_by_id(user_id: str) -> str | None:
        try:
            profile = (
                await OfficerProfile
                .filter(id=user_id, deleted_at__isnull=True)
                .only("citizen_id")
                .first()
            )
            return profile.citizen_id if profile else None
        except Exception as e:
            logger.error(f"Error retrieving citizen_id for Officer user {user_id}: {e}")
            raise e

    @staticmethod
    async def get_display_name_by_id(user_id: str) -> Optional[str]:
        snapshot = await OfficerProfileRepository.get_display_snapshot_by_id(user_id)
        if snapshot:
            return snapshot.get("name")
        return None

    @staticmethod
    async def get_display_snapshot_by_id(user_id: str) -> Optional[Dict[str, Optional[str]]]:
        if not user_id:
            return None
        try:
            profile = (
                await OfficerProfile
                .filter(id=user_id, deleted_at__isnull=True)
                .select_related("prefix", "position")
                .only("first_name", "last_name", "prefix_id", "position_id", "area_type")
                .first()
            )
            if not profile:
                return None

            prefix_name = getattr(getattr(profile, "prefix", None), "prefix_name_th", None)
            position = getattr(profile, "position", None)
            position_name = getattr(position, "position_name_th", None) if position else None
            scope_level = None
            if position and getattr(position, "scope_level", None):
                scope_level = getattr(position.scope_level, "value", None) or getattr(position.scope_level, "name", None)
            elif getattr(profile, "area_type", None):
                scope_level = getattr(profile.area_type, "value", None) or getattr(profile.area_type, "name", None)

            parts = [prefix_name, profile.first_name, profile.last_name]
            name = " ".join(part for part in parts if part)

            return {
                "name": name or None,
                "position_name": position_name,
                "scope_level": scope_level,
            }
        except Exception as exc:
            logger.error("Error retrieving officer display snapshot for %s: %s", user_id, exc)
            return None

    @staticmethod
    async def is_citizen_id_exist_and_is_first_login(citizen_id: str) -> Optional[Dict[str, Any]]:
        if not citizen_id:
            return None
        try:
            result = (
                await OfficerProfile
                .filter(
                    citizen_id=citizen_id,
                    is_active=True,
                    approval_status=ApprovalStatus.APPROVED.value,
                    deleted_at__isnull=True,
                )
                .values("citizen_id", "is_first_login", "password_hash")
            )
            return result[0] if result else None
        except Exception as exc:
            logger.error("Error checking officer login state: %s", exc)
            raise

    @staticmethod
    async def set_password(citizen_id: str, hashed_password: str) -> None:
        try:
            officer = await OfficerProfile.get(citizen_id=citizen_id, deleted_at__isnull=True)
            officer.password_hash = hashed_password
            officer.is_first_login = False
            officer.password_attempts = 0
            officer.is_active = True
            await officer.save()
        except Exception as exc:
            logger.error("Error setting officer password for %s: %s", citizen_id, exc)
            raise

    @staticmethod
    async def set_password_by_id(
        officer_id: str,
        hashed_password: str,
        *,
        mark_first_login: bool = False,
        reset_attempts: bool = True,
        reactivate: bool = True,
    ) -> bool:
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
            updated = (
                await OfficerProfile
                .filter(id=officer_id, deleted_at__isnull=True)
                .update(**update_payload)
            )
            return bool(updated)
        except Exception as exc:
            logger.error("Error setting officer password by id %s: %s", officer_id, exc)
            raise

    @staticmethod
    async def get_password_state(officer_id: str):
        try:
            return (
                await OfficerProfile
                .filter(id=officer_id, deleted_at__isnull=True)
                .only("id", "password_hash", "password_attempts", "is_active")
                .first()
            )
        except Exception as exc:
            logger.error("Error retrieving password state for officer %s: %s", officer_id, exc)
            raise

    @staticmethod
    async def update_password_attempts(officer_id: str, attempts: int, *, deactivate: bool = False) -> None:
        try:
            update_payload: Dict[str, Any] = {"password_attempts": attempts, "updated_at": datetime.utcnow()}
            if deactivate:
                update_payload["is_active"] = False
            await OfficerProfile.filter(id=officer_id, deleted_at__isnull=True).update(**update_payload)
        except Exception as exc:
            logger.error("Error updating password attempts for officer %s: %s", officer_id, exc)
            raise

    @staticmethod
    async def find_any_officer_by_citizen_id(citizen_id: str):
        if not citizen_id:
            return None
        try:
            return (
                await OfficerProfile
                .filter(citizen_id=citizen_id, deleted_at__isnull=True)
                .prefetch_related("province", "district", "subdistrict", "health_area", "position")
                .first()
            )
        except Exception as exc:
            logger.error("Error looking up officer by citizen id: %s", exc)
            raise

    async def find_officer_profile_by_citizen_id(citizen_id: str):
        """Return officer profile by citizen id for authentication and permission checks."""
        if not citizen_id:
            return None
        logger.info(f"Looking for Officer profile with citizen_id: {citizen_id}")
        try:
            officer_profile = (
                await OfficerProfile
                .filter(citizen_id=citizen_id, deleted_at__isnull=True)
                .prefetch_related("province", "district", "subdistrict")
                .first()
            )
            logger.info(f"Found Officer profile by citizen_id: {officer_profile}")
            return officer_profile
        except Exception as e:
            logger.error(f"Error finding Officer profile by citizen id: {e}")
            raise e

    async def find_officer_profile_with_related_fields(user_credential_id: str):
        """
        ดึง Officer Profile พร้อม related fields สำหรับ UserInfo endpoint
        """
        logger.info(f"Looking for Officer profile with related fields: {user_credential_id}")
        
        try:
            # รวม prefetch related fields และหลีกเลี่ยง exception กรณีไม่พบ
            officer_profile = (
                await OfficerProfile
                .filter(id=user_credential_id, deleted_at__isnull=True)
                .prefetch_related(
                    "province", "province__region", "province__health_area",
                    "district", "subdistrict", "position", "prefix",
                    "health_area", "health_service",
                )
                .first()
            )
            logger.info(f"Found Officer profile with related fields: {officer_profile}")
            return officer_profile
        except Exception as e:
            logger.error(f"Error finding Officer profile with related fields: {e}")
            raise e

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        try:
            UUID(str(value))
            return True
        except (ValueError, TypeError, AttributeError):
            return False

    async def exists_officer_by_identifier(identifier: str) -> bool:
        """Check whether the given identifier (UUID or citizen id) belongs to an officer profile."""
        if not identifier:
            return False
        try:
            conditions = Q(citizen_id=str(identifier))
            if OfficerProfileRepository._is_valid_uuid(identifier):
                conditions |= Q(id=str(identifier))

            query = OfficerProfile.filter(conditions).filter(is_active=True, deleted_at__isnull=True)
            return await query.exists()
        except Exception as e:
            logger.error(f"Error checking Officer profile existence for identifier {identifier}: {e}")
            raise e

    @staticmethod
    async def search_active_officers(term: str, limit: int = 10, *, active_only: bool = True, offset: int = 0):
        if not term:
            return [], 0
        try:
            base_qs = (
                OfficerProfile
                .filter(deleted_at__isnull=True)
                .filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(citizen_id__icontains=term)
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
                    "phone",
                    "email",
                    "is_active",
                    "prefix_id",
                    "position_id",
                    "province_id",
                    "district_id",
                    "subdistrict_id",
                    "municipality_id",
                    "health_area_id",
                )
                .order_by("first_name")
                .offset(offset)
                .limit(limit)
            )
            query = OfficerProfileRepository._with_related(query)
            items = await query
            return items, total
        except Exception as e:
            logger.error(f"Error searching officer profiles: {e}")
            raise e

    @staticmethod
    async def get_basic_officer_by_id(officer_id: str):
        if not officer_id:
            return None
        try:
            return (
                await OfficerProfile
                .filter(id=officer_id, deleted_at__isnull=True)
                .only(
                    "id",
                    "first_name",
                    "last_name",
                    "citizen_id",
                    "is_active",
                    "approval_status",
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error retrieving officer basic profile {officer_id}: {e}")
            raise e

    async def list_officers(
        filter_params,
        visibility_filter=None,
        manageable_levels: Optional[Sequence[str]] = None,
        exclude_ids: Optional[Sequence[str]] = None,
    ) -> Tuple[list, int]:
        logger.info("Listing officer profiles with filters: %s", filter_params)
        try:
            query = OfficerProfile.filter(deleted_at__isnull=True)

            if visibility_filter is not None:
                query = query.filter(visibility_filter)

            if filter_params.search:
                search_term = filter_params.search.strip()
                if search_term:
                    query = query.filter(
                        Q(first_name__icontains=search_term)
                        | Q(last_name__icontains=search_term)
                        | Q(citizen_id__icontains=search_term)
                        | Q(health_service__health_service_name_th__icontains=search_term)
                        | Q(health_service__health_service_code__icontains=search_term)
                    )

            if manageable_levels:
                level_values = [level.value if hasattr(level, "value") else level for level in manageable_levels]
                query = query.filter(Q(area_type__in=level_values))
                query = query.filter(Q(position__scope_level__in=level_values) | Q(position__scope_level__isnull=True))

            if filter_params.area_code:
                query = query.filter(area_code__icontains=filter_params.area_code)
            if filter_params.health_service_id:
                query = query.filter(health_service_id__icontains=filter_params.health_service_id)
            if getattr(filter_params, "position_id", None):
                query = query.filter(position_id=filter_params.position_id)
            if filter_params.province_id:
                query = query.filter(province_id=filter_params.province_id)
            if filter_params.district_id:
                query = query.filter(district_id=filter_params.district_id)
            if filter_params.subdistrict_id:
                query = query.filter(subdistrict_id=filter_params.subdistrict_id)
            if filter_params.is_active is not None:
                query = query.filter(is_active=filter_params.is_active)
            if filter_params.approval_status:
                query = query.filter(approval_status=filter_params.approval_status)

            if exclude_ids:
                query = query.filter(~Q(id__in=exclude_ids))

            total_count = await query.count()

            order_field = filter_params.order_by or "created_at"
            if order_field not in ALLOWED_SORT_FIELDS:
                order_field = "created_at"
            sort_dir = (filter_params.sort_dir or "").lower()
            order_expression = f"{'-' if sort_dir == 'desc' else ''}{order_field}"
            query = query.order_by(order_expression)

            offset = (filter_params.page - 1) * filter_params.limit
            query = query.offset(offset).limit(filter_params.limit)
            query = OfficerProfileRepository._with_related(query)
            result = await query
            logger.info("Found %d officer profiles", len(result))
            return result, total_count
        except Exception as e:
            logger.error("Error listing officer profiles: %s", e)
            raise e

    async def get_officer_by_id(officer_id: str):
        try:
            return await OfficerProfileRepository._with_related(
                OfficerProfile.filter(id=officer_id, deleted_at__isnull=True)
            ).first()
        except Exception as e:
            logger.error(f"Error retrieving officer profile {officer_id}: {e}")
            raise e

    @staticmethod
    async def is_officer_visible(officer_id: str, visibility_filter: Optional[Q]) -> bool:
        try:
            query = OfficerProfile.filter(id=officer_id, deleted_at__isnull=True)
            if visibility_filter is not None:
                query = query.filter(visibility_filter)
            return await query.exists()
        except Exception as e:
            logger.error(f"Error checking officer visibility {officer_id}: {e}")
            raise e

    async def create_officer(payload: dict):
        try:
            officer = await OfficerProfile.create(**payload)
            await officer.fetch_related(*OfficerProfileRepository._RELATED_FIELDS)
            return officer
        except Exception as e:
            logger.error(f"Error creating officer profile: {e}")
            raise e

    async def update_officer(officer_id: str, payload: dict) -> bool:
        if not payload:
            return False
        try:
            updated = await OfficerProfile.filter(id=officer_id, deleted_at__isnull=True).update(**payload)
            logger.info("Updated officer %s: %s", officer_id, bool(updated))
            return bool(updated)
        except Exception as e:
            logger.error(f"Error updating officer profile {officer_id}: {e}")
            raise e

    async def soft_delete_officer(officer_id: str) -> bool:
        try:
            deleted = await OfficerProfile.filter(id=officer_id, deleted_at__isnull=True).update(
                deleted_at=datetime.utcnow(),
                is_active=False,
            )
            logger.info("Soft deleted officer %s: %s", officer_id, bool(deleted))
            return bool(deleted)
        except Exception as e:
            logger.error(f"Error soft deleting officer profile {officer_id}: {e}")
            raise e