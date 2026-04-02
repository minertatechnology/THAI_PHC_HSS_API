from __future__ import annotations

from fastapi import HTTPException

from app.api.v1.schemas.yuwa_osm_schema import (
    YuwaOSMCreateSchema,
    YuwaOSMDecisionPayload,
    YuwaOSMQueryParams,
    YuwaOSMRejectPayload,
    YuwaOSMSummaryQueryParams,
    YuwaOSMUpdateSchema,
    YuwaOSMTransferRequest,
)
from app.services.yuwa_osm_service import YuwaOsmService


class YuwaOsmController:
    @staticmethod
    async def register_user(
        payload: YuwaOSMCreateSchema,
        actor_id: str | None = None,
    ):
        try:
            return await YuwaOsmService.register_user(payload, actor_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def list_users(filter_params: YuwaOSMQueryParams, current_user: dict):
        try:
            return await YuwaOsmService.list_users(filter_params, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def summary(filter_params: YuwaOSMSummaryQueryParams, current_user: dict):
        try:
            return await YuwaOsmService.summary(filter_params, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def get_user(user_id: str, current_user: dict):
        try:
            return await YuwaOsmService.get_user(user_id, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def update_user(user_id: str, payload: YuwaOSMUpdateSchema, current_user: dict):
        try:
            return await YuwaOsmService.update_user(user_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def delete_user(user_id: str, current_user: dict):
        try:
            return await YuwaOsmService.delete_user(user_id, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def approve_user(user_id: str, payload: YuwaOSMDecisionPayload, current_user: dict):
        try:
            return await YuwaOsmService.approve_user(user_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def reject_user(user_id: str, payload: YuwaOSMRejectPayload, current_user: dict):
        try:
            return await YuwaOsmService.reject_user(user_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def retire_user(user_id: str, payload: YuwaOSMDecisionPayload, current_user: dict):
        try:
            return await YuwaOsmService.retire_user(user_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def transfer_from_people(payload: YuwaOSMTransferRequest, current_user: dict):
        try:
            return await YuwaOsmService.transfer_from_people(str(payload.people_id), current_user, payload.note)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def get_yuwa_osm_by_ids(user_ids: list[str], current_user: dict) -> dict:
        try:
            result = await YuwaOsmService.get_yuwa_osm_by_ids(user_ids, current_user)
            return result
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
