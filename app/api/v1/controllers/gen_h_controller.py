from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException

from app.api.v1.schemas.gen_h_schema import (
    GenHCreateSchema,
    GenHTransferToPeopleRequest,
    GenHUpdateSchema,
    GenHUpgradeToYuwaOSMRequest,
)
from app.services.gen_h_service import GenHService

logger = logging.getLogger(__name__)


class GenHController:

    @staticmethod
    async def register(payload: GenHCreateSchema, current_user: dict | None = None) -> dict:
        try:
            return await GenHService.register(payload, current_user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H register error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def get_user(user_id: str) -> dict:
        try:
            return await GenHService.get_user(user_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H get_user error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def update_user(user_id: str, payload: GenHUpdateSchema, current_user: dict | None = None) -> dict:
        try:
            return await GenHService.update_user(user_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H update_user error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def delete_user(user_id: UUID, current_user: dict | None = None) -> None:
        try:
            await GenHService.delete_user(user_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H delete_user error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def list_users(params: dict) -> dict:
        try:
            return await GenHService.list_users(params)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H list_users error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def summary(province_code: str | None = None) -> dict:
        try:
            return await GenHService.summary(province_code=province_code)
        except Exception as e:
            logger.error("Gen H summary error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def transfer_to_people(
        gen_h_id: str,
        payload: GenHTransferToPeopleRequest,
        actor_id: str | None = None,
        current_user: dict | None = None,
    ) -> dict:
        try:
            return await GenHService.transfer_to_people(gen_h_id, payload, actor_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H transfer error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def upgrade_to_yuwa_osm(
        gen_h_id: str,
        payload: GenHUpgradeToYuwaOSMRequest,
        current_user: dict,
    ) -> dict:
        try:
            return await GenHService.upgrade_to_yuwa_osm(gen_h_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H upgrade_to_yuwa_osm error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def get_gen_h_by_ids(user_ids: list[str]) -> dict:
        try:
            result = await GenHService.get_gen_h_by_ids(user_ids)
            return {
                "status": "success",
                "data": result.get("data", []),
                "errors": result.get("errors", []),
                "message": "ดึงข้อมูล Gen H Users สำเร็จ",
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gen H get_gen_h_by_ids error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
