from __future__ import annotations

from fastapi import HTTPException

from app.api.v1.schemas.people_schema import PeopleCreateSchema, PeopleUpdateSchema
from app.services.people_service import PeopleService


class PeopleController:
    @staticmethod
    async def register_user(payload: PeopleCreateSchema, actor_id: str | None = None):
        try:
            return await PeopleService.register_user(payload, actor_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def get_user(user_id: str, current_user: dict):
        try:
            return await PeopleService.get_user(user_id, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def update_user(user_id: str, payload: PeopleUpdateSchema, current_user: dict):
        try:
            return await PeopleService.update_user(user_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @staticmethod
    async def get_people_by_ids(user_ids: list[str], current_user: dict) -> dict:
        try:
            result = await PeopleService.get_people_by_ids(user_ids, current_user)
            return result
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
