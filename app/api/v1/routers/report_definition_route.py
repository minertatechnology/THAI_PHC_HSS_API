from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.middleware.middleware import require_scopes
from app.api.v1.schemas.report_definition_schema import (
    ReportDefinitionCreate,
    ReportDefinitionListResponse,
    ReportDefinitionResponse,
    ReportDefinitionUpdate,
)
from app.models.enum_models import AdministrativeLevelEnum
from app.services.permission_service import PermissionService
from app.services.report_definition_service import ReportDefinitionService

report_definition_router = APIRouter(prefix="/report-definitions", tags=["report-definitions"])


async def _require_officer(current_user: dict = Depends(require_scopes({"profile"}))) -> dict:
    await PermissionService.require_officer(current_user)
    return current_user


async def _require_central_officer(current_user: dict = Depends(require_scopes({"profile"}))) -> dict:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.COUNTRY,
    )
    return current_user


@report_definition_router.get("", response_model=ReportDefinitionListResponse)
async def list_report_definitions(
    keyword: Optional[str] = Query(None, description="ค้นหาจาก name หรือ label"),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    return await ReportDefinitionService.list_reports(
        keyword=keyword,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@report_definition_router.get(
    "/{report_id}",
    response_model=ReportDefinitionResponse,
)
async def get_report_definition(
    report_id: UUID = Path(..., description="รหัสรายงาน"),
    _: dict = Depends(_require_officer),
):
    result = await ReportDefinitionService.get_report(report_id)
    return result["item"]


@report_definition_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ReportDefinitionResponse,
)
async def create_report_definition(
    payload: ReportDefinitionCreate,
    current_user: dict = Depends(_require_central_officer),
):
    actor = current_user.get("user_id") if current_user else None
    result = await ReportDefinitionService.create_report(payload.model_dump(), actor=str(actor) if actor else None)
    return result["item"]


@report_definition_router.patch(
    "/{report_id}",
    response_model=ReportDefinitionResponse,
)
async def update_report_definition(
    report_id: UUID = Path(..., description="รหัสรายงาน"),
    payload: ReportDefinitionUpdate | None = None,
    current_user: dict = Depends(_require_central_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    actor = current_user.get("user_id") if current_user else None
    result = await ReportDefinitionService.update_report(
        report_id,
        data,
        actor=str(actor) if actor else None,
    )
    return result["item"]


@report_definition_router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report_definition(
    report_id: UUID = Path(..., description="รหัสรายงาน"),
    current_user: dict = Depends(_require_central_officer),
):
    actor = current_user.get("user_id") if current_user else None
    await ReportDefinitionService.delete_report(
        report_id,
        actor=str(actor) if actor else None,
    )
    return None
