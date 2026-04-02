from typing import Optional, List

from fastapi import Depends, HTTPException, status

from app.api.middleware.middleware import get_current_user
from app.api.v1.schemas.officer_schema import (
    OfficerActiveStatusSchema,
    OfficerCreateSchema,
    OfficerApprovalActionSchema,
    OfficerQueryParams,
    OfficerTransferSchema,
    OfficerUpdateSchema,
)
from app.services.officer_service import OfficerService

class OfficerController:
    async def list_officers(filter: OfficerQueryParams, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.list_officers(filter, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def create_officer(officer: OfficerCreateSchema, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.create_officer(officer, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_officer(officer_id: str, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.get_officer_by_id(officer_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_officers_by_ids(officer_ids: List[str], current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.get_officers_by_ids(officer_ids, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def update_officer(officer_id: str, officer_data: OfficerUpdateSchema, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.update_officer(officer_id, officer_data, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def transfer_officer(officer_id: str, payload: OfficerTransferSchema, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.transfer_officer(officer_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_transfer_history(
        officer_id: str,
        page: int = 1,
        page_size: int = 20,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.get_transfer_history(officer_id, page, page_size, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def delete_officer(officer_id: str, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.soft_delete_officer(officer_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def set_active_status(
        officer_id: str,
        payload: OfficerActiveStatusSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.set_active_status(officer_id, payload.is_active, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def reset_password(officer_id: str, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.reset_password(officer_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def reset_osm_password(osm_id: str, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.reset_osm_password(osm_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def reset_yuwa_password(user_id: str, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.reset_yuwa_password(user_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def reset_people_password(user_id: str, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.reset_people_password(user_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def set_osm_active_status(
        osm_id: str,
        payload: OfficerActiveStatusSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.set_osm_active_status(osm_id, payload.is_active, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def set_yuwa_active_status(
        user_id: str,
        payload: OfficerActiveStatusSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.set_yuwa_active_status(user_id, payload.is_active, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def set_people_active_status(
        user_id: str,
        payload: OfficerActiveStatusSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.set_people_active_status(user_id, payload.is_active, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def reset_gen_h_password(user_id: str, current_user: dict = Depends(get_current_user)):
        try:
            return await OfficerService.reset_gen_h_password(user_id, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def set_gen_h_active_status(
        user_id: str,
        payload: OfficerActiveStatusSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.set_gen_h_active_status(user_id, payload.is_active, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def register_officer(officer: OfficerCreateSchema):
        try:
            return await OfficerService.register_officer(officer)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def approve_officer(
        officer_id: str,
        payload: OfficerApprovalActionSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.approve_officer(officer_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def reject_officer(
        officer_id: str,
        payload: OfficerApprovalActionSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OfficerService.reject_officer(officer_id, payload, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_meta():
        try:
            return await OfficerService.get_registration_meta()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_genders():
        try:
            return await OfficerService.get_registration_genders()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_prefixes(keyword: Optional[str] = None, limit: int = 200):
        try:
            return await OfficerService.get_registration_prefixes(keyword, limit)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_positions(keyword: Optional[str] = None, limit: int = 500):
        try:
            return await OfficerService.get_registration_positions(keyword, limit)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_provinces(keyword: Optional[str] = None, limit: int = 1000):
        try:
            return await OfficerService.get_registration_provinces(keyword, limit)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_districts(province_code: str, keyword: Optional[str] = None):
        try:
            return await OfficerService.get_registration_districts(province_code, keyword)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_subdistricts(district_code: str, keyword: Optional[str] = None):
        try:
            return await OfficerService.get_registration_subdistricts(district_code, keyword)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_municipalities(
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        keyword: Optional[str] = None,
    ):
        try:
            return await OfficerService.get_registration_municipalities(
                province_code=province_code,
                district_code=district_code,
                subdistrict_code=subdistrict_code,
                keyword=keyword,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_registration_health_services(
        keyword: Optional[str] = None,
        province_code: Optional[str] = None,
        district_code: Optional[str] = None,
        subdistrict_code: Optional[str] = None,
        health_service_type_ids: Optional[List[str]] = None,
        health_service_type_ids_exclude: Optional[List[str]] = None,
        limit: int = 100,
    ):
        try:
            return await OfficerService.get_registration_health_services(
                keyword=keyword,
                province_code=province_code,
                district_code=district_code,
                subdistrict_code=subdistrict_code,
                health_service_type_ids=health_service_type_ids,
                health_service_type_ids_exclude=health_service_type_ids_exclude,
                limit=limit,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))