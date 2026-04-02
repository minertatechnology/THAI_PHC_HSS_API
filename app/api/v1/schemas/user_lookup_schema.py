from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserLookupSummary(BaseModel):
    user_id: str = Field(..., description="UUID ของผู้ใช้")
    user_type: str = Field(..., description="ประเภทผู้ใช้เช่น officer, osm, yuwa_osm, people")
    citizen_id: Optional[str] = Field(None, description="เลขประจำตัวประชาชนถ้ามี")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = Field(None, description="เพศของผู้ใช้")
    birth_date: Optional[str] = Field(None, description="วันเกิดในรูปแบบ ISO 8601")
    age: Optional[int] = Field(None, description="อายุคำนวณจากวันเกิด")


class UserLookupListResponse(BaseModel):
    items: List[UserLookupSummary]
    count: int = Field(..., description="จำนวนรายการในหน้านี้")
    total: int = Field(..., description="จำนวนรายการทั้งหมดตามเงื่อนไข")
    limit: int = Field(..., description="จำนวนสูงสุดของรายการต่อหน้า")
    offset: int = Field(..., description="จำนวนรายการที่ถูกข้ามก่อนเริ่มหน้า")


class UserLookupDetailResponse(BaseModel):
    success: bool
    data: Dict[str, Any]