"""
Scope enforcement utility for report / dashboard endpoints.

Resolves the calling officer's administrative scope and **clamps** the
geographic query-parameters so they never exceed the officer's visibility.

Scope levels and behaviour
--------------------------
- COUNTRY / REGION / AREA  →  no restriction (pass filters through)
- PROVINCE                 →  province_code locked to officer's province
- DISTRICT                 →  province_code + district_code locked
- SUBDISTRICT              →  province + district + subdistrict locked
- VILLAGE                  →  all geo codes locked

If a caller supplies a filter that conflicts with their scope the officer's
own value takes precedence (silent override + warning log).
Non-officer users receive HTTP 403.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from fastapi import HTTPException, status

from app.models.enum_models import AdministrativeLevelEnum
from app.services.permission_service import PermissionService
from app.utils.logging_utils import get_logger
from app.utils.officer_hierarchy import OfficerScope

logger = get_logger(__name__)


@dataclass
class ScopeOverride:
    """Clamped geographic filter values after scope enforcement."""

    province_code: Optional[str] = None
    district_code: Optional[str] = None
    subdistrict_code: Optional[str] = None
    village_code: Optional[str] = None
    scope: Optional[OfficerScope] = None
    enforced: bool = False  # True when at least one value was overridden


# ── public helpers ──────────────────────────────────────────────────────

async def enforce_scope_on_filters(
    current_user: Mapping[str, Any] | None,
    *,
    province_code: Optional[str] = None,
    district_code: Optional[str] = None,
    subdistrict_code: Optional[str] = None,
    village_code: Optional[str] = None,
) -> ScopeOverride:
    """Clamp geographic params to the officer's scope.

    Returns a ``ScopeOverride`` whose fields should replace the original
    query-filter values before passing them to the service layer.
    """

    profile, scope = await PermissionService.resolve_officer_context(current_user)

    if profile is None or scope is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden: officer access required for reports",
        )

    # Broad scopes → no geo restriction
    if scope.level in (
        AdministrativeLevelEnum.COUNTRY,
        AdministrativeLevelEnum.REGION,
        AdministrativeLevelEnum.AREA,
    ):
        return ScopeOverride(
            province_code=province_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
            village_code=village_code,
            scope=scope,
            enforced=False,
        )

    enforced = False

    if scope.level == AdministrativeLevelEnum.PROVINCE:
        if province_code and province_code != scope.province_id:
            logger.warning(
                "Scope override: officer province=%s, requested=%s",
                scope.province_id,
                province_code,
            )
        province_code = scope.province_id
        enforced = True

    elif scope.level == AdministrativeLevelEnum.DISTRICT:
        province_code = scope.province_id
        if district_code and district_code != scope.district_id:
            logger.warning(
                "Scope override: officer district=%s, requested=%s",
                scope.district_id,
                district_code,
            )
        district_code = scope.district_id
        enforced = True

    elif scope.level == AdministrativeLevelEnum.SUBDISTRICT:
        province_code = scope.province_id
        district_code = scope.district_id
        if subdistrict_code and subdistrict_code != scope.subdistrict_id:
            logger.warning(
                "Scope override: officer subdistrict=%s, requested=%s",
                scope.subdistrict_id,
                subdistrict_code,
            )
        subdistrict_code = scope.subdistrict_id
        enforced = True

    elif scope.level == AdministrativeLevelEnum.VILLAGE:
        province_code = scope.province_id
        district_code = scope.district_id
        subdistrict_code = scope.subdistrict_id
        village_code = scope.village_code
        enforced = True

    return ScopeOverride(
        province_code=province_code,
        district_code=district_code,
        subdistrict_code=subdistrict_code,
        village_code=village_code,
        scope=scope,
        enforced=enforced,
    )


def apply_scope_to_query(filters: Any, override: ScopeOverride) -> None:
    """Mutate a Pydantic query-schema in-place with the clamped geo values.

    Works with any schema that exposes ``province_code``, ``district_code``,
    ``subdistrict_code`` and/or ``village_code`` attributes.
    """
    if hasattr(filters, "province_code"):
        filters.province_code = override.province_code
    if hasattr(filters, "district_code"):
        filters.district_code = override.district_code
    if hasattr(filters, "subdistrict_code"):
        filters.subdistrict_code = override.subdistrict_code
    if hasattr(filters, "village_code"):
        filters.village_code = override.village_code
