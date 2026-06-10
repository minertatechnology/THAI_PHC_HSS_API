"""POST /api/v1/auto-transfer/run — manual trigger สำหรับ officer
(เทียบเท่ากับปุ่ม "เช็คและเลื่อนขั้น" ฝั่ง frontend)"""

from fastapi import APIRouter, Depends

from app.api.middleware.middleware import require_scopes
from app.services.permission_service import PermissionService
from app.services.auto_transfer_service import run_auto_transfer

auto_transfer_router = APIRouter(
    prefix="/auto-transfer",
    tags=["auto-transfer"],
)


@auto_transfer_router.post("/run")
async def trigger_auto_transfer(
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """Manual trigger: ตรวจสอบ + เลื่อนขั้น Gen-H → YUWA-OSM อัตโนมัติ (officer only).

    Endpoint นี้ทำงานเหมือน scheduled job ทุกชม. แต่เรียกได้ตอนไหนก็ได้
    เพื่อให้ officer สามารถ trigger เองได้โดยไม่ต้องรอรอบถัดไป
    """
    await PermissionService.require_officer(current_user)
    result = await run_auto_transfer()
    return {
        "success": True,
        "message": "auto_transfer_completed",
        "data": result,
    }
