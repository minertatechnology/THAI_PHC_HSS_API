from __future__ import annotations

from typing import Iterable, Mapping, Optional

from fastapi import HTTPException, status

from app.models.enum_models import AdministrativeLevelEnum
from app.models.position_model import Position
from app.repositories.phc_permission_page_repository import PhcPermissionPageRepository
from app.utils.logging_utils import get_logger, log_error

logger = get_logger(__name__)

def _coerce_level_token(raw: object) -> str:
    """Normalize any enum/string token into the canonical lower-case value."""
    if raw is None:
        return ""
    if isinstance(raw, AdministrativeLevelEnum):
        return raw.value
    value = str(raw).strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered.startswith("administrativelevelenum."):
        lowered = lowered.split(".", 1)[1]
    return lowered


async def _fetch_allowed_level_metadata() -> tuple[list[str], set[str]]:
    records = (
        await Position.filter(scope_level__isnull=False)
        .distinct()
        .values_list("scope_level", flat=True)
    )
    normalized = [_coerce_level_token(item) for item in records if _coerce_level_token(item)]
    valid_set = set(normalized)
    enum_values = [level.value for level in AdministrativeLevelEnum]
    if valid_set:
        valid_set = valid_set | set(enum_values)
    else:
        valid_set = set(enum_values)
    enum_order = [value for value in enum_values if value in valid_set]
    return enum_order, valid_set


async def _normalize_levels(raw_levels: Optional[Iterable[str]]) -> list[str]:
    if not raw_levels:
        return []

    enum_order, valid_set = await _fetch_allowed_level_metadata()
    if not valid_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_level:no_valid_scope_levels",
        )

    normalized = []
    for item in raw_levels:
        value = _coerce_level_token(item)
        if not value:
            continue
        if value not in valid_set:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"invalid_level:{value}",
            )
        normalized.append(value)

    if not normalized:
        return []

    normalized_unique: list[str] = []
    seen: set[str] = set()
    for value in enum_order:
        if value in normalized and value not in seen:
            normalized_unique.append(value)
            seen.add(value)
    for value in normalized:
        if value not in seen:
            normalized_unique.append(value)
            seen.add(value)
    return normalized_unique


def _serialize(page) -> dict:
    return {
        "id": str(page.id),
        "system_name": page.system_name,
        "main_menu": page.main_menu,
        "sub_main_menu": page.sub_main_menu,
        "allowed_levels": list(page.allowed_levels or []),
        "is_active": bool(page.is_active),
        "display_order": page.display_order,
        "metadata": page.metadata or None,
        "created_at": page.created_at,
        "updated_at": page.updated_at,
    }


class PermissionPageService:
    DEFAULT_SYSTEM_NAME = "thai_phc_web"

    @classmethod
    async def list_pages(
        cls,
        *,
        system_name: Optional[str] = None,
        include_inactive: bool = False,
    ) -> list[dict]:
        pages = await PhcPermissionPageRepository.list_pages(
            system_name=system_name or cls.DEFAULT_SYSTEM_NAME,
            include_inactive=include_inactive,
        )
        return [_serialize(page) for page in pages]

    @classmethod
    async def list_accessible_pages(
        cls,
        manageable_levels: Iterable[str] | None,
        *,
        system_name: Optional[str] = None,
    ) -> list[dict]:
        try:
            pages = await PhcPermissionPageRepository.list_pages(
                system_name=system_name or cls.DEFAULT_SYSTEM_NAME,
                include_inactive=False,
            )
        except Exception as repo_error:
            log_error(logger, "list_accessible_pages failed", exc=repo_error)
            return []

        levels = {str(level).strip().lower() for level in manageable_levels or [] if level}
        if not levels:
            return [_serialize(page) for page in pages if not page.allowed_levels]

        result: list[dict] = []
        for page in pages:
            allowed = {str(level).strip().lower() for level in page.allowed_levels or [] if level}
            if allowed and allowed.isdisjoint(levels):
                continue
            result.append(_serialize(page))
        return result

    @classmethod
    async def create_page(
        cls,
        *,
        payload: Mapping[str, object],
    ) -> dict:
        system_name = str(payload.get("system_name") or cls.DEFAULT_SYSTEM_NAME).strip()
        if not system_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="system_name_required")
        main_menu = str(payload.get("main_menu") or "").strip()
        if not main_menu:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="main_menu_required")
        sub_main_menu_raw = payload.get("sub_main_menu")
        sub_main_menu = None
        if sub_main_menu_raw is not None:
            value = str(sub_main_menu_raw).strip()
            sub_main_menu = value or None
        allowed_levels = await _normalize_levels(payload.get("allowed_levels"))
        display_order = int(payload.get("display_order") or 0)
        is_active = bool(payload.get("is_active", True))
        metadata = payload.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="metadata_must_be_object")

        try:
            page = await PhcPermissionPageRepository.create_page(
                system_name=system_name,
                main_menu=main_menu,
                sub_main_menu=sub_main_menu,
                allowed_levels=allowed_levels,
                display_order=display_order,
                is_active=is_active,
                metadata=metadata,
            )
        except ValueError as value_error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(value_error),
            ) from value_error
        except Exception as repo_error:
            log_error(logger, "create permission page failed", exc=repo_error)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="create_failed") from repo_error
        return _serialize(page)

    @classmethod
    async def update_page(
        cls,
        page_id: str,
        *,
        payload: Mapping[str, object],
    ) -> dict:
        page = await PhcPermissionPageRepository.get_page_or_none(page_id)
        if not page:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="permission_page_not_found")

        updates: dict = {}
        if "main_menu" in payload:
            main_menu = str(payload.get("main_menu") or "").strip()
            if not main_menu:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="main_menu_required")
            updates["main_menu"] = main_menu
        if "sub_main_menu" in payload:
            raw = payload.get("sub_main_menu")
            if raw is None:
                updates["sub_main_menu"] = None
            else:
                cleaned = str(raw).strip()
                updates["sub_main_menu"] = cleaned or None
        if "allowed_levels" in payload:
            updates["allowed_levels"] = await _normalize_levels(payload.get("allowed_levels"))
        if "display_order" in payload:
            updates["display_order"] = int(payload.get("display_order") or 0)
        if "is_active" in payload:
            updates["is_active"] = bool(payload.get("is_active"))
        if "metadata" in payload:
            metadata = payload.get("metadata")
            if metadata is not None and not isinstance(metadata, dict):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="metadata_must_be_object")
            updates["metadata"] = metadata

        try:
            updated = await PhcPermissionPageRepository.update_page(page, **updates)
        except ValueError as value_error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(value_error),
            ) from value_error
        except Exception as repo_error:
            log_error(logger, "update permission page failed", exc=repo_error)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="update_failed") from repo_error
        return _serialize(updated)

    @classmethod
    async def delete_page(cls, page_id: str) -> None:
        page = await PhcPermissionPageRepository.get_page_or_none(page_id)
        if not page:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="permission_page_not_found")
        await PhcPermissionPageRepository.delete_page(page)
