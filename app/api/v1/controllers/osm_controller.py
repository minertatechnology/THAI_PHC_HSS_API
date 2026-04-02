from fastapi import Request, HTTPException
from app.api.v1.schemas.query_schema import OsmQueryParams
from app.services.osm_service import OsmService
from app.api.v1.schemas.osm_schema import (
    OsmActiveStatusSchema,
    OsmCreateSchema,
    OsmPositionConfirmationCreateSchema,
    OsmPositionConfirmationUpdateSchema,
    OsmUpdateSchema,
)
from app.api.middleware.middleware import get_current_user
from fastapi import Depends
from typing import Dict, Any, Optional, List

class OsmController:
    async def find_all_osm(request: Request, filter: OsmQueryParams, current_user: dict = Depends(get_current_user)):
        """
        ค้นหา OSM ทั้งหมดพร้อม filter และ pagination
        """
        try:
            result = await OsmService.find_all_osm(filter)
            return  result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการค้นหา OSM: {str(e)}"
            )

    async def create_osm(osm: OsmCreateSchema, current_user: Optional[dict] = None):
        """
        สร้าง OSM Profile ใหม่
        """
        try:
            result = await OsmService.create_osm(osm, current_user=current_user)
            # Return the result directly since service already formats it
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการสร้าง OSM: {str(e)}"
            )

    async def get_osm_by_id(osm_id: str, current_user: dict = Depends(get_current_user)):
        """
        ดึงข้อมูล OSM Profile ด้วย ID
        """
        try:
            result = await OsmService.get_osm_by_id(osm_id)
            return {
                "status": "success",
                "data": result,
                "message": "ดึงข้อมูล OSM สำเร็จ"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงข้อมูล OSM: {str(e)}"
            )

    async def get_osm_summary_by_id(osm_id: str, current_user: dict = Depends(get_current_user)):
        """
        ดึงข้อมูล OSM Profile แบบย่อด้วย ID
        """
        try:
            result = await OsmService.get_osm_summary_by_id(osm_id)
            return {
                "status": "success",
                "data": result,
                "message": "ดึงข้อมูล OSM สำเร็จ",
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงข้อมูล OSM: {str(e)}"
            )

    async def get_osms_by_ids(osm_ids: List[str], current_user: dict = Depends(get_current_user)):
        """
        ดึงข้อมูล OSM หลายรายการด้วยรายการ ID
        """
        try:
            result = await OsmService.get_osms_by_ids(osm_ids)
            return {
                "status": "success",
                "data": result.get("data", []),
                "errors": result.get("errors", []),
                "message": "ดึงข้อมูล OSM สำเร็จ",
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงข้อมูล OSM: {str(e)}"
            )

    async def get_osm_by_citizen_id(citizen_id: str, current_user: dict = Depends(get_current_user)):
        """
        ดึงข้อมูล OSM Profile ด้วยเลขบัตรประชาชน
        """
        try:
            result = await OsmService.get_osm_by_citizen_id(citizen_id)
            return {
                "status": "success",
                "data": result,
                "message": "ดึงข้อมูล OSM สำเร็จ"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงข้อมูล OSM: {str(e)}"
            )

    async def update_osm(osm_id: str, osm_data: OsmUpdateSchema, current_user: dict = Depends(get_current_user)):
        """
        อัปเดตข้อมูล OSM Profile
        """
        try:
            user_id = current_user["user_id"]
            result = await OsmService.update_osm(osm_id, osm_data, user_id)
            return {
                "status": "success",
                "data": result,
                "message": "อัปเดตข้อมูล OSM สำเร็จ"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการอัปเดต OSM: {str(e)}"
            )

    async def delete_osm(osm_id: str, current_user: dict = Depends(get_current_user)):
        """
        ลบ OSM Profile
        """
        try:
            result = await OsmService.delete_osm(osm_id, current_user=current_user)
            return {
                "status": "success",
                "data": result,
                "message": "ลบ OSM Profile สำเร็จ"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการลบ OSM: {str(e)}"
            )

    async def set_active_status(
        osm_id: str,
        payload: OsmActiveStatusSchema,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OsmService.set_active_status(
                osm_id,
                payload.is_active,
                current_user,
                approval_status=payload.approval_status,
                osm_status=payload.osm_status,
                osm_showbbody=payload.osm_showbbody,
                retirement_date=payload.retirement_date,
                retirement_reason=payload.retirement_reason,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการอัปเดตสถานะ OSM: {str(e)}"
            )


    async def activate_osm(
        osm_id: str,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return await OsmService.set_active_status(osm_id, True, current_user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการอนุมัติ OSM: {str(e)}",
            )

    async def reject_osm(
        osm_id: str,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            # Set is_active to False and approval_status to 'rejected'
            from app.models.enum_models import ApprovalStatus
            return await OsmService.set_active_status(
                osm_id,
                False,
                current_user,
                approval_status=ApprovalStatus.REJECTED.value
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการปฏิเสธ OSM: {str(e)}",
            )



    # Position Confirmation Methods
    async def create_or_update_position_confirmation(position_data: OsmPositionConfirmationCreateSchema, current_user: dict = Depends(get_current_user)):
        """
        สร้างหรืออัปเดตการยืนยันตำแหน่งและสิทธิ์เงินค่าป่วยการ (upsert)
        """
        try:
            user_id = current_user["user_id"]
            await OsmService.create_or_update_position_confirmation(
                position_data.osm_profile_id,
                position_data.osm_position_ids,
                position_data.allowance_confirmation_status,
                user_id
            )
            return {
                "status": "success",
                "message": "สร้างหรืออัปเดตการยืนยันตำแหน่งสำเร็จ"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการสร้างหรืออัปเดตการยืนยันตำแหน่ง: {str(e)}"
            )

    async def get_position_confirmation_by_osm_id(osm_profile_id: str, current_user: dict = Depends(get_current_user)):
        """
        ดึงการยืนยันตำแหน่งของ OSM Profile
        """
        try:
            result = await OsmService.get_position_confirmation_by_osm_id(osm_profile_id)
            if result:
                return {
                    "status": "success",
                    "data": result,
                    "message": "ดึงการยืนยันตำแหน่งสำเร็จ"
                }
            else:
                return {
                    "status": "success",
                    "data": None,
                    "message": "ไม่พบการยืนยันตำแหน่ง"
                }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงการยืนยันตำแหน่ง: {str(e)}"
            )

    async def delete_position_confirmation(confirmation_id: str, current_user: dict = Depends(get_current_user)):
        """
        ลบการยืนยันตำแหน่ง (Soft Delete)
        """
        try:
            user_id = current_user["user_id"]
            await OsmService.delete_position_confirmation(confirmation_id, user_id)
            return {
                "status": "success",
                "message": "ลบการยืนยันตำแหน่งสำเร็จ"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการลบการยืนยันตำแหน่ง: {str(e)}"
            )

    async def get_all_osm_positions(current_user: dict = Depends(get_current_user)):
        """
        ดึงตำแหน่ง OSM ทั้งหมด
        """
        try:
            result = await OsmService.get_all_osm_positions()
            return {
                "status": "success",
                "data": result,
                "message": "ดึงตำแหน่ง OSM สำเร็จ"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"เกิดข้อผิดพลาดในการดึงตำแหน่ง OSM: {str(e)}"
            )
