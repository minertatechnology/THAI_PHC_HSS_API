"""Legacy OfficerRepository wrapper for backward compatibility.

Prefer importing :mod:`app.repositories.officer_profile_repository` directly.
"""

from app.api.v1.schemas.officer_schema import OfficerCreateSchema
from app.repositories.officer_profile_repository import OfficerProfileRepository


class OfficerRepository:
    @staticmethod
    async def create_officer(officer: OfficerCreateSchema, user_id: str):
        payload = officer.model_dump()
        payload["approval_by"] = user_id
        return await OfficerProfileRepository.create_officer(payload)