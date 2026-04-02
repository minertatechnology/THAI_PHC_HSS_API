from typing import Any, Mapping, Tuple, Optional

from fastapi import HTTPException, status

from app.repositories.officer_profile_repository import OfficerProfileRepository
from app.utils.logging_utils import get_logger, log_error
from app.models.enum_models import AdministrativeLevelEnum
from app.utils.officer_hierarchy import OfficerHierarchy, OfficerScope, OfficerScopeError


logger = get_logger(__name__)


class PermissionService:
    """Utility helpers for evaluating role-based permissions."""

    @staticmethod
    async def is_officer(current_user: Mapping[str, Any] | None) -> bool:
        if not current_user:
            return False
        user_type = current_user.get("user_type")
        if user_type != "officer":
            return False

        user_id = current_user.get("user_id")
        if not user_id:
            return False

        try:
            return await OfficerProfileRepository.exists_officer_by_identifier(str(user_id))
        except Exception as repo_error:
            log_error(logger, "Failed to verify officer permissions", exc=repo_error)
            return False

    @staticmethod
    async def require_officer(current_user: Mapping[str, Any] | None) -> None:
        if not await PermissionService.is_officer(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden: officer access required")

    @staticmethod
    async def resolve_officer_context(
        current_user: Mapping[str, Any] | None,
    ) -> Tuple[Optional[Any], Optional[OfficerScope]]:
        if not await PermissionService.is_officer(current_user):
            return None, None
        return await PermissionService._resolve_officer_scope(current_user)

    @staticmethod
    async def _resolve_officer_scope(
        current_user: Mapping[str, Any] | None,
    ) -> Tuple[Any, OfficerScope]:
        if not await PermissionService.is_officer(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden: officer access required")

        user_id = current_user.get("user_id") if current_user else None
        if not user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden: officer profile missing")

        try:
            profile = await OfficerProfileRepository.get_officer_by_id(str(user_id))
        except Exception as repo_error:
            log_error(logger, "Failed to load officer profile for scope check", exc=repo_error)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="officer_scope_lookup_failed")

        if not profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden: officer profile missing")

        try:
            scope = OfficerHierarchy.scope_from_profile(profile)
        except OfficerScopeError as scope_error:
            log_error(logger, "Unable to resolve officer scope", exc=scope_error)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden: officer scope unavailable")

        return profile, scope

    @staticmethod
    async def require_officer_scope_at_least(
        current_user: Mapping[str, Any] | None,
        *,
        minimum_level: AdministrativeLevelEnum,
    ) -> None:
        _, scope = await PermissionService._resolve_officer_scope(current_user)
        required_scope = OfficerScope(level=minimum_level)
        if scope.rank < required_scope.rank:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden: insufficient_scope")
