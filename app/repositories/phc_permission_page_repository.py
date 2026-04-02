from __future__ import annotations

from typing import Iterable, Optional

from tortoise.exceptions import DoesNotExist

from app.models.phc_permission_model import PhcPermissionPage


class PhcPermissionPageRepository:
    """Data access helpers for PHC permission pages."""

    @staticmethod
    async def list_pages(
        *,
        system_name: Optional[str] = None,
        include_inactive: bool = False,
    ) -> list[PhcPermissionPage]:
        query = PhcPermissionPage.all()
        if system_name:
            query = query.filter(system_name=system_name)
        if not include_inactive:
            query = query.filter(is_active=True)
        return await query.order_by("display_order", "main_menu", "sub_main_menu")

    @staticmethod
    async def get_page(page_id: str) -> PhcPermissionPage:
        return await PhcPermissionPage.get(id=page_id)

    @staticmethod
    async def get_page_or_none(page_id: str) -> Optional[PhcPermissionPage]:
        try:
            return await PhcPermissionPage.get(id=page_id)
        except DoesNotExist:
            return None

    @staticmethod
    async def create_page(
        *,
        system_name: str,
        main_menu: str,
        sub_main_menu: Optional[str],
        allowed_levels: Iterable[str],
        display_order: int,
        is_active: bool,
        metadata: Optional[dict] = None,
    ) -> PhcPermissionPage:
        return await PhcPermissionPage.create(
            system_name=system_name,
            main_menu=main_menu,
            sub_main_menu=sub_main_menu,
            allowed_levels=list(allowed_levels),
            display_order=display_order,
            is_active=is_active,
            metadata=metadata,
        )

    @staticmethod
    async def update_page(
        page: PhcPermissionPage,
        *,
        main_menu: Optional[str] = None,
        sub_main_menu: Optional[str] = None,
        allowed_levels: Optional[Iterable[str]] = None,
        display_order: Optional[int] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[dict] = None,
    ) -> PhcPermissionPage:
        if main_menu is not None:
            page.main_menu = main_menu
        if sub_main_menu is not None:
            page.sub_main_menu = sub_main_menu
        if allowed_levels is not None:
            page.allowed_levels = list(allowed_levels)
        if display_order is not None:
            page.display_order = display_order
        if is_active is not None:
            page.is_active = is_active
        if metadata is not None:
            page.metadata = metadata
        await page.save()
        return page

    @staticmethod
    async def delete_page(page: PhcPermissionPage) -> None:
        await page.delete()
