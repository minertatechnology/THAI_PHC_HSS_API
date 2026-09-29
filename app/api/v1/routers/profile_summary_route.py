from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.middleware.middleware import require_scopes
from app.services.permission_service import PermissionService
from app.services.profile_summary_service import ProfileSummaryService

profile_summary_router = APIRouter(prefix="/profile-summary", tags=["profile-summary"])


class ProfileSummaryBatchSchema(BaseModel):
    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="OSM / Officer profile IDs (external_user_id)",
    )


@profile_summary_router.post("/batch")
async def get_profile_summary_batch(
    payload: ProfileSummaryBatchSchema,
    current_user: dict = Depends(require_scopes({"profile"})),
):
    """
    ดึงข้อมูลแบบย่อ (ชื่อ/เลขบัตร/พื้นที่/หน่วยบริการ) ของ OSM และ Officer หลายรายการในครั้งเดียว
    สำหรับหน้ารายชื่อผู้ใช้งานจำนวนมาก (เฉพาะเจ้าหน้าที่)
    - query ครั้งเดียวต่อประเภท ไม่ดึง relation ย่อย จึงเร็วกว่า /osm/batch มาก
    - แต่ละรายการมี user_type = "osm" | "officer"
    """
    await PermissionService.require_officer(current_user)
    return await ProfileSummaryService.get_summaries_by_ids(payload.ids)
