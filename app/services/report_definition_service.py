from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from tortoise.expressions import Q

from app.models.report_model import ReportDefinition


class ReportDefinitionService:
    @staticmethod
    def _serialize(report: ReportDefinition) -> Dict[str, object]:
        return {
            "id": report.id,
            "name": report.name,
            "label": report.label,
            "description": report.description,
            "is_active": report.is_active,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
        }

    @staticmethod
    async def list_reports(
        *,
        keyword: Optional[str],
        is_active: Optional[bool],
        limit: int,
        offset: int,
    ) -> Dict[str, object]:
        query = ReportDefinition.filter(deleted_at__isnull=True)
        if keyword:
            query = query.filter(Q(name__icontains=keyword) | Q(label__icontains=keyword))
        if is_active is not None:
            query = query.filter(is_active=is_active)
        total = await query.count()
        rows: List[ReportDefinition] = (
            await query.order_by("name").offset(offset).limit(limit)
        )
        items = [ReportDefinitionService._serialize(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_report(report_id: UUID) -> Dict[str, object]:
        report = await ReportDefinition.filter(id=report_id, deleted_at__isnull=True).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report_not_found")
        return {"item": ReportDefinitionService._serialize(report)}

    @staticmethod
    async def create_report(payload: Dict[str, object], *, actor: Optional[str]) -> Dict[str, object]:
        name = str(payload.get("name", "")).strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name_required")
        existing = await ReportDefinition.filter(name=name, deleted_at__isnull=True).exists()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="report_name_in_use")
        label = str(payload.get("label", "")).strip()
        if not label:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="label_required")
        report = await ReportDefinition.create(
            name=name,
            label=label,
            description=payload.get("description"),
            is_active=bool(payload.get("is_active", True)),
            created_by=actor,
            updated_by=actor,
        )
        return {"item": ReportDefinitionService._serialize(report)}

    @staticmethod
    async def update_report(
        report_id: UUID,
        payload: Dict[str, object],
        *,
        actor: Optional[str],
    ) -> Dict[str, object]:
        report = await ReportDefinition.filter(id=report_id, deleted_at__isnull=True).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report_not_found")
        if "name" in payload and payload["name"]:
            new_name = str(payload["name"]).strip()
            if new_name and new_name != report.name:
                exists = await ReportDefinition.filter(
                    name=new_name,
                    deleted_at__isnull=True,
                ).exclude(id=report_id).exists()
                if exists:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="report_name_in_use")
                report.name = new_name
        if "label" in payload and payload["label"] is not None:
            report.label = str(payload["label"])
        if "description" in payload:
            report.description = payload.get("description")
        if "is_active" in payload and payload["is_active"] is not None:
            report.is_active = bool(payload["is_active"])
        report.updated_by = actor
        await report.save()
        return {"item": ReportDefinitionService._serialize(report)}

    @staticmethod
    async def delete_report(report_id: UUID, *, actor: Optional[str]) -> Dict[str, object]:
        report = await ReportDefinition.filter(id=report_id, deleted_at__isnull=True).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report_not_found")
        report.deleted_at = datetime.utcnow()
        report.updated_by = actor
        await report.save()
        return {"success": True}
