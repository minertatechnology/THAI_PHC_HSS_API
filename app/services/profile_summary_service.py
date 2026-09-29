"""
Profile summary (batch) สำหรับระบบภายนอกที่ต้องการแค่ชื่อ/พื้นที่ของผู้ใช้จำนวนมาก

ต่างจาก /osm/batch และ /officer/batch ที่วนดึงข้อมูลเต็ม (คู่สมรส/บุตร/การอบรม ฯลฯ) ทีละคน
เส้นนี้ query ครั้งเดียวต่อประเภทผู้ใช้ด้วย id IN (...) และคืนเฉพาะฟิลด์ที่ใช้แสดงรายชื่อ
"""
from typing import Any, Dict, List

from app.models.osm_model import OSMProfile
from app.models.officer_model import OfficerProfile


# ฟิลด์ที่เหมือนกันทั้ง OSM และ Officer
_COMMON_FIELDS = dict(
    prefix_name_th="prefix__prefix_name_th",
    province_name_th="province__province_name_th",
    district_name_th="district__district_name_th",
    subdistrict_name_th="subdistrict__subdistrict_name_th",
    health_service_name_th="health_service__health_service_name_th",
)
_COMMON_COLUMNS = (
    "id",
    "citizen_id",
    "first_name",
    "last_name",
    "gender",
    "phone",
    "is_active",
    "province_id",
    "district_id",
    "subdistrict_id",
    "health_service_id",
)


def _normalize(row: Dict[str, Any], user_type: str) -> Dict[str, Any]:
    gender = row.get("gender")
    return {
        **row,
        "id": str(row["id"]),
        "gender": getattr(gender, "value", gender),
        "user_type": user_type,
    }


class ProfileSummaryService:
    @staticmethod
    async def get_summaries_by_ids(ids: List[str]) -> Dict[str, Any]:
        unique_ids = list(dict.fromkeys(ids))

        osm_rows = await (
            OSMProfile.filter(id__in=unique_ids, deleted_at__isnull=True)
            .values(
                *_COMMON_COLUMNS,
                "osm_code",
                "village_code",
                "village_name",
                health_area_id="province__health_area__code",
                **_COMMON_FIELDS,
            )
        )
        items = [_normalize(row, "osm") for row in osm_rows]

        found = {item["id"] for item in items}
        remaining = [i for i in unique_ids if i not in found]

        if remaining:
            officer_rows = await (
                OfficerProfile.filter(id__in=remaining, deleted_at__isnull=True)
                .values(
                    *_COMMON_COLUMNS,
                    position_name_th="position__position_name_th",
                    health_area_id="health_area__code",
                    **_COMMON_FIELDS,
                )
            )
            items.extend(_normalize(row, "officer") for row in officer_rows)
            found.update(item["id"] for item in items)

        return {
            "data": items,
            "not_found": [i for i in unique_ids if i not in found],
        }
