from pydantic import BaseModel, Field


class ThirdPartyOsmRequest(BaseModel):
    """Request schema for thirdparty getDataOSMCGD endpoint"""
    citizen_id: str = Field(
        ...,
        min_length=13,
        max_length=13,
        description="เลขบัตรประชาชน 13 หลัก",
        examples=["3501500299499"],
    )


class ThirdPartyAddressSchema(BaseModel):
    """Address sub-schema for thirdparty response"""
    address: str = ""
    moo: int = 0
    sub_district_name: str = ""
    district_name: str = ""
    province_name: str = ""
    post_code: str = ""


class ThirdPartyOsmDataSchema(BaseModel):
    """OSM data sub-schema for thirdparty response"""
    pid: str = ""
    name: str = ""
    birthday: str = ""
    address: ThirdPartyAddressSchema = ThirdPartyAddressSchema()
    start_date_volunteer: str = ""
    phone_number: str = ""
    status: str = ""


class ThirdPartyOsmResponse(BaseModel):
    """Response schema for thirdparty getDataOSMCGD endpoint"""
    code: int = 200
    message: str = "success"
    message_th: str = "สำเร็จ"
    osm_data: list[ThirdPartyOsmDataSchema] = []
