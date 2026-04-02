from __future__ import annotations

from uuid import uuid4

from tortoise import fields, models

from app.models.enum_models import AdministrativeLevelEnum
from app.models.position_model import Position


_ENUM_ORDER = [level.value for level in AdministrativeLevelEnum]


class PhcPermissionPage(models.Model):
    """Menu access mapping for Thai PHC web dashboards."""

    id = fields.UUIDField(pk=True, default=uuid4)
    system_name = fields.CharField(max_length=100, index=True)
    main_menu = fields.CharField(max_length=255)
    sub_main_menu = fields.CharField(max_length=255, null=True)
    allowed_levels = fields.JSONField(default=list)
    is_active = fields.BooleanField(default=True)
    display_order = fields.IntField(default=0)
    metadata = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "phc_permission_page"
        unique_together = ("system_name", "main_menu", "sub_main_menu")
        ordering = ("display_order", "main_menu", "sub_main_menu")

    def __str__(self) -> str:
        label = self.sub_main_menu or self.main_menu
        return f"{self.system_name}:{label}"

    async def _normalize_allowed_levels(self) -> None:
        raw_levels = self.allowed_levels or []
        cleaned: list[str] = []
        for entry in raw_levels:
            if not entry:
                continue
            value = str(entry).strip().lower()
            if not value:
                continue
            cleaned.append(value)

        if not cleaned:
            self.allowed_levels = []
            return

        db_levels = await (
            Position.filter(scope_level__isnull=False)
            .distinct()
            .values_list("scope_level", flat=True)
        )
        valid_set = {str(item).strip().lower() for item in db_levels if item}
        enum_set = set(_ENUM_ORDER)
        if valid_set:
            valid_set = valid_set | enum_set
        else:
            valid_set = enum_set

        for value in cleaned:
            if value not in valid_set:
                raise ValueError(f"invalid_allowed_level:{value}")

        ordered_unique: list[str] = []
        seen: set[str] = set()
        for level in _ENUM_ORDER:
            if level not in valid_set:
                continue
            if level in cleaned and level not in seen:
                ordered_unique.append(level)
                seen.add(level)
        for level in cleaned:
            if level in valid_set and level not in seen:
                ordered_unique.append(level)
                seen.add(level)

        self.allowed_levels = ordered_unique

    async def save(self, *args, **kwargs):
        await self._normalize_allowed_levels()
        await super().save(*args, **kwargs)
