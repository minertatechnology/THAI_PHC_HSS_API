from __future__ import annotations

import re
from typing import Mapping, MutableMapping, Sequence

from fastapi import HTTPException, status

from app.models.mobile_menu_model import MobileMenuItem
from app.cache.redis_client import cache_delete_pattern


class MobileMenuService:
    VALID_USER_TYPES = {"officer", "osm", "yuwa_osm", "people"}
    VALID_PLATFORMS = {"android", "ios", "web"}
    USER_TYPE_ORDER = ("officer", "osm", "yuwa_osm", "people")
    PLATFORM_ORDER = ("android", "ios", "web")
    VALID_OPEN_TYPES = {"webview", "external", "deeplink", "native"}

    @classmethod
    async def list_menus(
        cls,
        *,
        include_inactive: bool = False,
    ) -> list[dict]:
        query = MobileMenuItem.all()
        if not include_inactive:
            query = query.filter(is_active=True)
        rows = await query.order_by("display_order", "menu_name", "id")
        return [cls._serialize(row) for row in rows]

    @classmethod
    async def list_visible_menus(
        cls,
        *,
        user_type: str | None,
        platform: str | None = None,
    ) -> list[dict]:
        normalized_user_type = cls._normalize_user_type_token(user_type)
        normalized_platform = cls._normalize_platform_token(platform)
        rows = await MobileMenuItem.filter(is_active=True).order_by("display_order", "menu_name", "id")
        visible: list[dict] = []
        for row in rows:
            allowed_types = {str(item).strip().lower() for item in row.allowed_user_types or [] if item}
            if allowed_types and normalized_user_type not in allowed_types:
                continue
            allowed_platforms = {str(item).strip().lower() for item in row.platforms or [] if item}
            if normalized_platform and allowed_platforms and normalized_platform not in allowed_platforms:
                continue
            visible.append(cls._serialize(row))
        return visible

    @classmethod
    async def create_menu(cls, *, payload: Mapping[str, object], actor_id: str | None) -> dict:
        actor_clean = cls._normalize_actor(actor_id)
        fields = cls._normalize_payload(payload, partial=False)
        await cls._assert_unique_menu_key(fields["menu_key"])
        await cls._shift_display_orders(fields["display_order"])
        row = await MobileMenuItem.create(
            **fields,
            created_by=actor_clean,
            updated_by=actor_clean,
        )
        await cache_delete_pattern("mobile:menus:current:*")
        return cls._serialize(row)

    @classmethod
    async def update_menu(
        cls,
        menu_id: str,
        *,
        payload: Mapping[str, object],
        actor_id: str | None,
    ) -> dict:
        target = await cls._get_existing(menu_id)
        actor_clean = cls._normalize_actor(actor_id)
        updates = cls._normalize_payload(payload, partial=True, existing=target)
        if "menu_key" in updates and updates["menu_key"] != target.menu_key:
            await cls._assert_unique_menu_key(updates["menu_key"], exclude_id=str(target.id))
        if "display_order" in updates and updates["display_order"] != target.display_order:
            await cls._shift_display_orders(updates["display_order"], exclude_id=str(target.id))
        for field, value in updates.items():
            setattr(target, field, value)
        target.updated_by = actor_clean
        await target.save()
        await cache_delete_pattern("mobile:menus:current:*")
        await target.refresh_from_db()
        return cls._serialize(target)

    @classmethod
    async def delete_menu(cls, menu_id: str) -> None:
        target = await cls._get_existing(menu_id)
        await target.delete()
        await cache_delete_pattern("mobile:menus:current:*")

    # ---------------------------- helpers ----------------------------

    @classmethod
    async def _shift_display_orders(
        cls,
        target_order: int,
        *,
        exclude_id: str | None = None,
    ) -> None:
        """Ensure *target_order* is free by cascading colliding items forward.

        Walks every row with display_order >= target_order (sorted ASC)
        and pushes any that would collide to the next available slot.
        The cascade continues until a gap is found (no more conflicts).

        Example: orders [8, 9, 10, 15], insert at 8
          → 8→9, 9→10, 10→11, 15 stays  →  result [9, 10, 11, 15]

        Also handles pre-existing duplicates, e.g. [8, 8, 9]
          → first 8→9, second 8→10, 9→11  →  result [9, 10, 11]
        """
        query = MobileMenuItem.filter(display_order__gte=target_order)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        rows = await query.order_by("display_order")

        if not rows:
            return

        next_available = target_order + 1
        for row in rows:
            if row.display_order > next_available:
                break
            if row.display_order < next_available:
                row.display_order = next_available
                await row.save(update_fields=["display_order"])
            next_available = row.display_order + 1

    @classmethod
    async def _get_existing(cls, menu_id: str) -> MobileMenuItem:
        item = await MobileMenuItem.filter(id=menu_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mobile_menu_not_found")
        return item

    @classmethod
    async def _assert_unique_menu_key(cls, menu_key: str, exclude_id: str | None = None) -> None:
        query = MobileMenuItem.filter(menu_key=menu_key)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        exists = await query.exists()
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="menu_key_exists")

    @classmethod
    def _normalize_payload(
        cls,
        payload: Mapping[str, object],
        *,
        partial: bool,
        existing: MobileMenuItem | None = None,
    ) -> MutableMapping[str, object]:
        normalized: MutableMapping[str, object] = {}
        if not partial or "menu_key" in payload:
            normalized["menu_key"] = cls._normalize_menu_key(payload.get("menu_key"))
        if not partial or "menu_name" in payload:
            normalized["menu_name"] = cls._normalize_menu_name(payload.get("menu_name"))
        if not partial or "menu_description" in payload:
            normalized["menu_description"] = cls._normalize_optional_text(payload.get("menu_description"))
        if not partial or "icon_name" in payload:
            normalized["icon_name"] = cls._normalize_optional_text(payload.get("icon_name"), max_length=255)
        if not partial or "open_type" in payload:
            normalized["open_type"] = cls._normalize_open_type(payload.get("open_type"), existing)
        if not partial or "webview_title" in payload:
            normalized["webview_title"] = cls._normalize_optional_text(payload.get("webview_title"))
        if not partial or "webview_url" in payload:
            normalized["webview_url"] = cls._normalize_optional_url(payload.get("webview_url"))
        if not partial or "redirect_url" in payload:
            normalized["redirect_url"] = cls._normalize_optional_url(payload.get("redirect_url"))
        if not partial or "deeplink_url" in payload:
            normalized["deeplink_url"] = cls._normalize_optional_text(payload.get("deeplink_url"), max_length=512)
        if not partial or "allowed_user_types" in payload:
            normalized["allowed_user_types"] = cls._normalize_list_field(
                payload.get("allowed_user_types"),
                allowed=cls.VALID_USER_TYPES,
                ordered=cls.USER_TYPE_ORDER,
                field_name="allowed_user_types",
            )
        if not partial or "platforms" in payload:
            normalized["platforms"] = cls._normalize_list_field(
                payload.get("platforms"),
                allowed=cls.VALID_PLATFORMS,
                ordered=cls.PLATFORM_ORDER,
                field_name="platforms",
            )
        if not partial or "metadata" in payload:
            normalized["metadata"] = cls._normalize_metadata(payload.get("metadata"))
        if not partial or "display_order" in payload:
            normalized["display_order"] = cls._normalize_display_order(payload.get("display_order"))
        if not partial or "is_active" in payload:
            normalized["is_active"] = bool(payload.get("is_active", True))

        effective_open_type = normalized.get("open_type")
        if effective_open_type is None:
            effective_open_type = existing.open_type if existing else "webview"
        effective_webview = normalized.get("webview_url")
        if effective_webview is None and existing:
            effective_webview = existing.webview_url
        effective_redirect = normalized.get("redirect_url")
        if effective_redirect is None and existing:
            effective_redirect = existing.redirect_url
        effective_deeplink = normalized.get("deeplink_url")
        if effective_deeplink is None and existing:
            effective_deeplink = existing.deeplink_url
        cls._enforce_open_requirements(
            open_type=effective_open_type,
            webview_url=effective_webview,
            redirect_url=effective_redirect,
            deeplink_url=effective_deeplink,
        )
        return normalized

    @classmethod
    def _normalize_menu_key(cls, value: object) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="menu_key_required")
        if len(raw) > 100:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="menu_key_too_long")
        if not re.fullmatch(r"[a-z0-9_-]+", raw):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="menu_key_invalid")
        return raw

    @classmethod
    def _normalize_menu_name(cls, value: object) -> str:
        cleaned = str(value or "").strip()
        if not cleaned:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="menu_name_required")
        if len(cleaned) > 255:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="menu_name_too_long")
        return cleaned

    @staticmethod
    def _normalize_optional_text(value: object, max_length: int | None = None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        if max_length and len(cleaned) > max_length:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="text_too_long")
        return cleaned

    @classmethod
    def _normalize_open_type(cls, value: object, existing: MobileMenuItem | None) -> str:
        cleaned = str(value or "").strip().lower()
        if not cleaned:
            if existing:
                return existing.open_type
            return "webview"
        if cleaned not in cls.VALID_OPEN_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_open_type")
        return cleaned

    @classmethod
    def _normalize_optional_url(cls, value: object) -> str | None:
        text = cls._normalize_optional_text(value, max_length=512)
        if text and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
            # Allow relative URLs for internal routes (beginning with /)
            if not text.startswith("/"):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_url")
        return text

    @classmethod
    def _normalize_list_field(
        cls,
        values: object,
        *,
        allowed: set[str],
        ordered: Sequence[str],
        field_name: str,
    ) -> list[str]:
        if values is None:
            return []
        if not isinstance(values, (list, tuple, set)):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name}_must_be_list")
        normalized: list[str] = []
        seen: set[str] = set()
        for entry in values:
            token = str(entry or "").strip().lower()
            if not token:
                continue
            if token not in allowed:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"invalid_{field_name}:{token}")
            if token not in seen:
                normalized.append(token)
                seen.add(token)
        if not normalized:
            return []
        ordered_result: list[str] = [value for value in ordered if value in seen]
        for token in normalized:
            if token not in ordered_result:
                ordered_result.append(token)
        return ordered_result

    @staticmethod
    def _normalize_metadata(value: object) -> dict | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="metadata_must_be_object")
        return value

    @staticmethod
    def _normalize_display_order(value: object) -> int:
        try:
            number = int(value or 0)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_display_order") from exc
        if number < 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="display_order_must_be_positive")
        return number

    @staticmethod
    def _normalize_actor(actor_id: str | None) -> str:
        actor_clean = str(actor_id or "").strip()
        if not actor_clean:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="actor_required")
        return actor_clean

    @classmethod
    def _enforce_open_requirements(
        cls,
        *,
        open_type: str,
        webview_url: str | None,
        redirect_url: str | None,
        deeplink_url: str | None,
    ) -> None:
        if open_type == "webview" and not webview_url:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="webview_url_required")
        if open_type == "external" and not redirect_url:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="redirect_url_required")
        if open_type == "deeplink" and not deeplink_url:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="deeplink_url_required")

    @staticmethod
    def _normalize_user_type_token(user_type: str | None) -> str | None:
        if not user_type:
            return None
        value = str(user_type).strip().lower()
        if not value:
            return None
        if value in MobileMenuService.VALID_USER_TYPES:
            return value
        return None

    @staticmethod
    def _normalize_platform_token(platform: str | None) -> str | None:
        if not platform:
            return None
        value = str(platform).strip().lower()
        if not value:
            return None
        if value in MobileMenuService.VALID_PLATFORMS:
            return value
        return None

    @staticmethod
    def _serialize(row: MobileMenuItem) -> dict:
        return {
            "id": str(row.id),
            "menu_key": row.menu_key,
            "menu_name": row.menu_name,
            "menu_description": row.menu_description,
            "icon_name": row.icon_name,
            "open_type": row.open_type,
            "webview_title": row.webview_title,
            "webview_url": row.webview_url,
            "redirect_url": row.redirect_url,
            "deeplink_url": row.deeplink_url,
            "allowed_user_types": list(row.allowed_user_types or []),
            "platforms": list(row.platforms or []),
            "metadata": row.metadata or None,
            "display_order": row.display_order,
            "is_active": bool(row.is_active),
            "created_by": str(row.created_by) if row.created_by else None,
            "updated_by": str(row.updated_by) if row.updated_by else None,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
