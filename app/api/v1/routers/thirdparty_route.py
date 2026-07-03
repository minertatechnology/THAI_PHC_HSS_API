from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import Optional

from app.configs.config import settings
from app.api.v1.schemas.thirdparty_schema import (
    ThirdPartyOsmRequest,
    ThirdPartyOsmResponse,
    ThirdPartyOsmDataSchema,
    ThirdPartyAddressSchema,
)
from app.repositories.osm_profile_repository import OSMProfileRepository

thirdparty_router = APIRouter(prefix="/thirdparty", tags=["thirdparty"])


async def verify_api_key(authorization: Optional[str] = Header(None)):
    """ตรวจสอบ API Key จาก Authorization header (Fix Key)"""
    if not settings.THIRD_PARTY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Third party API key not configured",
        )
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    # รองรับทั้งแบบ "Bearer <key>" และ "<key>" ตรงๆ
    token = authorization
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if token != settings.THIRD_PARTY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return token


@thirdparty_router.post(
    "/getDataOSMCGD",
    response_model=ThirdPartyOsmResponse,
    summary="ดึงข้อมูล อสม. สำหรับระบบ CGD (Third Party)",
)
async def get_data_osm_cgd(
    body: ThirdPartyOsmRequest,
    _: str = Depends(verify_api_key),
):
    """
    ดึงข้อมูล อสม. ด้วยเลขบัตรประชาชน สำหรับระบบ CGD
    ใช้ Fix Key จาก Authorization header
    """
    try:
        osm = await OSMProfileRepository.find_osm_by_citizen_id(body.citizen_id)

        if not osm:
            return ThirdPartyOsmResponse(
                code=404,
                message="not_found",
                message_th="ไม่พบข้อมูล",
                osm_data=[],
            )

        # ดึงชื่อ prefix
        prefix_name = ""
        try:
            prefix_obj = await osm.prefix
            if prefix_obj:
                prefix_name = prefix_obj.prefix_name_th or ""
        except Exception:
            pass

        # ดึงชื่อตำบล อำเภอ จังหวัด
        sub_district_name = ""
        district_name = ""
        province_name = ""
        post_code = osm.postal_code or ""

        try:
            subdistrict_obj = await osm.subdistrict
            if subdistrict_obj:
                sub_district_name = subdistrict_obj.subdistrict_name_th or ""
        except Exception:
            pass

        try:
            district_obj = await osm.district
            if district_obj:
                district_name = district_obj.district_name_th or ""
        except Exception:
            pass

        try:
            province_obj = await osm.province
            if province_obj:
                province_name = province_obj.province_name_th or ""
        except Exception:
            pass

        # แปลงวันเกิดเป็น ISO string
        birthday_str = ""
        if osm.birth_date:
            birthday_str = osm.birth_date.isoformat()

        # สร้างชื่อเต็ม
        full_name = f"{prefix_name}{osm.first_name} {osm.last_name}"

        # สถานะ
        osm_status = ""
        if osm.osm_status:
            osm_status = osm.osm_status.value if hasattr(osm.osm_status, "value") else str(osm.osm_status)

        osm_item = ThirdPartyOsmDataSchema(
            pid=osm.citizen_id or "",
            name=full_name,
            birthday=birthday_str,
            address=ThirdPartyAddressSchema(
                address=osm.address_number or "",
                moo=int(osm.village_no) if osm.village_no and osm.village_no.isdigit() else 0,
                sub_district_name=sub_district_name,
                district_name=district_name,
                province_name=province_name,
                post_code=post_code,
            ),
            start_date_volunteer=str(osm.osm_year) if osm.osm_year else "",
            phone_number=osm.phone or "",
            status=osm_status,
        )

        return ThirdPartyOsmResponse(
            code=200,
            message="success",
            message_th="สำเร็จ",
            osm_data=[osm_item],
        )

    except HTTPException:
        raise
    except Exception as e:
        return ThirdPartyOsmResponse(
            code=500,
            message="error",
            message_th=f"เกิดข้อผิดพลาด: {str(e)}",
            osm_data=[],
        )
