from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.middleware.middleware import get_current_user
from app.api.v1.exceptions.http_exceptions import UnauthorizedException
from app.api.v1.schemas.osm_schema import OsmCreateSchema, OsmUpdateSchema
from app.api.v1.schemas.query_schema import OsmQueryParams
from app.services.mock_auth_service import MockAuthService
from app.services.volunteer_service import VolunteerService


volunteer_router = APIRouter(prefix="/volunteers", tags=["volunteers"])
auth_scheme = HTTPBearer(auto_error=False)


async def _resolve_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await get_current_user(credentials)
    except UnauthorizedException:
        pass
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
    try:
        mock_payload = MockAuthService.decode_access_token(credentials.credentials)
        user = mock_payload.get("user") or {}
        return {
            "user_id": user.get("id"),
            "client_id": "mock-client",
            "user_type": user.get("user_type"),
            "scopes": mock_payload.get("scopes", []),
        }
    except HTTPException as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed") from exc


@volunteer_router.get("")
async def list_volunteers(
    firstName: Optional[str] = None,
    lastName: Optional[str] = None,
    status_param: Optional[str] = Query(None, alias="status"),
    hospitalCode: Optional[str] = None,
    province: Optional[str] = None,
    provinceCode: Optional[str] = None,
    district: Optional[str] = None,
    subDistrict: Optional[str] = None,
    page: int = 1,
    pageSize: int = 10,
    current_user=Depends(_resolve_current_user),
):
    page = max(page, 1)
    pageSize = max(pageSize, 1)

    filter_params = OsmQueryParams(
        citizen_id=None,
        first_name=firstName,
        last_name=lastName,
        status=status_param,
        health_service_code=hospitalCode,
        province_code=provinceCode or province,
        district_code=district,
        subdistrict_code=subDistrict,
        page=page,
        limit=pageSize,
        order_by="created_at",
        sort_dir="desc",
    )

    return await VolunteerService.list_volunteers(filter_params)


@volunteer_router.get("/{volunteer_id}")
async def get_volunteer(volunteer_id: str, current_user=Depends(_resolve_current_user)):
    return await VolunteerService.get_volunteer(volunteer_id)


@volunteer_router.post("", status_code=status.HTTP_201_CREATED)
async def create_volunteer(payload: OsmCreateSchema, current_user=Depends(_resolve_current_user)):
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_user")
    return await VolunteerService.create_volunteer(payload, current_user)


@volunteer_router.put("/{volunteer_id}")
async def update_volunteer(volunteer_id: str, payload: OsmUpdateSchema, current_user=Depends(_resolve_current_user)):
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_user")
    return await VolunteerService.update_volunteer(volunteer_id, payload, user_id)


@volunteer_router.patch("/{volunteer_id}/training")
async def update_training(volunteer_id: str, current_user=Depends(_resolve_current_user)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Volunteer training management is not yet implemented",
    )


@volunteer_router.patch("/{volunteer_id}/outstanding")
async def update_outstanding(volunteer_id: str, current_user=Depends(_resolve_current_user)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Volunteer outstanding management is not yet implemented",
    )


@volunteer_router.patch("/{volunteer_id}/personal")
async def update_personal(volunteer_id: str, payload: OsmUpdateSchema, current_user=Depends(_resolve_current_user)):
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_user")
    return await VolunteerService.update_volunteer(volunteer_id, payload, user_id)


@volunteer_router.post("/{volunteer_id}/activity-photos")
async def upload_activity_photo(volunteer_id: str, current_user=Depends(_resolve_current_user)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Volunteer activity photos storage is not yet implemented",
    )


@volunteer_router.delete("/{volunteer_id}")
async def delete_volunteer(volunteer_id: str, current_user=Depends(_resolve_current_user)):
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_user")
    return await VolunteerService.delete_volunteer(volunteer_id, user_id)


@volunteer_router.get("/{volunteer_id}/history")
async def volunteer_history(
    volunteer_id: str,
    page: int = 1,
    pageSize: int = 10,
    current_user=Depends(_resolve_current_user),
):
    return await VolunteerService.get_history(volunteer_id, page, pageSize)
