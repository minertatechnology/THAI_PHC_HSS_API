from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.middleware.middleware import require_scopes
from app.api.v1.schemas.geography_schema import (
    DistrictCreateRequest,
    DistrictUpdateRequest,
    HealthAreaCreateRequest,
    HealthAreaUpdateRequest,
    HealthServiceCreateRequest,
    HealthServiceUpdateRequest,
    MunicipalityCreateRequest,
    MunicipalityUpdateRequest,
    ProvinceCreateRequest,
    ProvinceQuotaUpdateRequest,
    ProvinceUpdateRequest,
    SubdistrictCreateRequest,
    SubdistrictUpdateRequest,
    VillageCreateRequest,
    VillageUpdateRequest,
)
from app.services.geography_management_service import GeographyManagementService
from app.services.permission_service import PermissionService
from app.models.enum_models import AdministrativeLevelEnum


geo_management_router = APIRouter(prefix="/geo-management", tags=["geo-management"])


async def _require_officer(current_user: dict = Depends(require_scopes({"profile"}))) -> dict:
    await PermissionService.require_officer(current_user)
    return current_user


async def _require_department_officer(current_user: dict = Depends(require_scopes({"profile"}))) -> dict:
    await PermissionService.require_officer_scope_at_least(
        current_user,
        minimum_level=AdministrativeLevelEnum.COUNTRY,
    )
    return current_user


# Provinces -----------------------------------------------------------------


@geo_management_router.get("/provinces")
async def list_provinces(
    keyword: Optional[str] = Query(None, description="ค้นหาจังหวัด"),
    area_code: Optional[str] = Query(None, description="รหัสเขต"),
    region_code: Optional[str] = Query(None, description="รหัสภูมิภาค"),
    health_area_code: Optional[str] = Query(None, description="รหัสเขตสุขภาพ"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.list_provinces(
        keyword=keyword,
        area_code=area_code,
        region_code=region_code,
        health_area_code=health_area_code,
        limit=limit,
        offset=offset,
    )


@geo_management_router.get("/provinces/{province_code}")
async def get_province(
    province_code: str = Path(..., description="รหัสจังหวัด"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.get_province(province_code)


@geo_management_router.post("/provinces", status_code=status.HTTP_201_CREATED)
async def create_province(
    payload: ProvinceCreateRequest,
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.create_province(payload.model_dump())


@geo_management_router.patch("/provinces/{province_code}")
async def update_province(
    province_code: str = Path(..., description="รหัสจังหวัด"),
    payload: ProvinceUpdateRequest = None,
    _: dict = Depends(_require_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    return await GeographyManagementService.update_province(province_code, data)


@geo_management_router.patch("/provinces/{province_code}/quota")
async def update_province_quota(
    province_code: str = Path(..., description="รหัสจังหวัด"),
    payload: ProvinceQuotaUpdateRequest = None,
    _: dict = Depends(_require_department_officer),
):
    quota_value = payload.quota if payload else 0
    return await GeographyManagementService.update_province_quota(
        province_code,
        quota_value,
    )


@geo_management_router.delete("/provinces/{province_code}")
async def delete_province(
    province_code: str = Path(..., description="รหัสจังหวัด"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.delete_province(province_code)


# Districts ------------------------------------------------------------------


@geo_management_router.get("/districts")
async def list_districts(
    keyword: Optional[str] = Query(None, description="ค้นหาอำเภอ"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.list_districts(
        keyword=keyword,
        province_code=province_code,
        limit=limit,
        offset=offset,
    )


@geo_management_router.get("/districts/{district_code}")
async def get_district(
    district_code: str = Path(..., description="รหัสอำเภอ"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.get_district(district_code)


@geo_management_router.post("/districts", status_code=status.HTTP_201_CREATED)
async def create_district(
    payload: DistrictCreateRequest,
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.create_district(payload.model_dump())


@geo_management_router.patch("/districts/{district_code}")
async def update_district(
    district_code: str = Path(..., description="รหัสอำเภอ"),
    payload: DistrictUpdateRequest = None,
    _: dict = Depends(_require_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    return await GeographyManagementService.update_district(district_code, data)


@geo_management_router.delete("/districts/{district_code}")
async def delete_district(
    district_code: str = Path(..., description="รหัสอำเภอ"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.delete_district(district_code)


# Subdistricts ----------------------------------------------------------------


@geo_management_router.get("/subdistricts")
async def list_subdistricts(
    keyword: Optional[str] = Query(None, description="ค้นหาตำบล"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    limit: int = Query(150, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.list_subdistricts(
        keyword=keyword,
        province_code=province_code,
        district_code=district_code,
        limit=limit,
        offset=offset,
    )


@geo_management_router.get("/subdistricts/{subdistrict_code}")
async def get_subdistrict(
    subdistrict_code: str = Path(..., description="รหัสตำบล"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.get_subdistrict(subdistrict_code)


@geo_management_router.post("/subdistricts", status_code=status.HTTP_201_CREATED)
async def create_subdistrict(
    payload: SubdistrictCreateRequest,
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.create_subdistrict(payload.model_dump())


@geo_management_router.patch("/subdistricts/{subdistrict_code}")
async def update_subdistrict(
    subdistrict_code: str = Path(..., description="รหัสตำบล"),
    payload: SubdistrictUpdateRequest = None,
    _: dict = Depends(_require_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    return await GeographyManagementService.update_subdistrict(subdistrict_code, data)


@geo_management_router.delete("/subdistricts/{subdistrict_code}")
async def delete_subdistrict(
    subdistrict_code: str = Path(..., description="รหัสตำบล"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.delete_subdistrict(subdistrict_code)


# Villages -------------------------------------------------------------------


@geo_management_router.get("/villages")
async def list_villages(
    keyword: Optional[str] = Query(None, description="ค้นหาหมู่บ้าน"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    health_service_code: Optional[str] = Query(None, description="รหัสหน่วยบริการ"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.list_villages(
        keyword=keyword,
        province_code=province_code,
        district_code=district_code,
        subdistrict_code=subdistrict_code,
        health_service_code=health_service_code,
        limit=limit,
        offset=offset,
    )


@geo_management_router.get("/villages/{village_code}")
async def get_village(
    village_code: str = Path(..., description="รหัสหมู่บ้าน"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.get_village(village_code)


@geo_management_router.post("/villages", status_code=status.HTTP_201_CREATED)
async def create_village(
    payload: VillageCreateRequest,
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.create_village(payload.model_dump())


@geo_management_router.patch("/villages/{village_code}")
async def update_village(
    village_code: str = Path(..., description="รหัสหมู่บ้าน"),
    payload: VillageUpdateRequest = None,
    _: dict = Depends(_require_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    return await GeographyManagementService.update_village(village_code, data)


@geo_management_router.delete("/villages/{village_code}")
async def delete_village(
    village_code: str = Path(..., description="รหัสหมู่บ้าน"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.delete_village(village_code)


# Health services ------------------------------------------------------------


@geo_management_router.get("/health-services")
async def list_health_services(
    keyword: Optional[str] = Query(None, description="ค้นหาชื่อหน่วยบริการสุขภาพ"),
    health_service_code: Optional[str] = Query(None, description="รหัสหน่วยบริการสุขภาพ"),
    legacy_5digit_code: Optional[str] = Query(None, description="รหัสหน่วยบริการสุขภาพเดิม 5 หลัก"),
    legacy_9digit_code: Optional[str] = Query(None, description="รหัสหน่วยบริการสุขภาพเดิม 9 หลัก"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    provinceCode: Optional[str] = Query(None, include_in_schema=False),
    province: Optional[str] = Query(None, include_in_schema=False),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    districtCode: Optional[str] = Query(None, include_in_schema=False),
    district: Optional[str] = Query(None, include_in_schema=False),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    subdistrictCode: Optional[str] = Query(None, include_in_schema=False),
    subdistrict: Optional[str] = Query(None, include_in_schema=False),
    health_service_type_id: Optional[str] = Query(None, description="รหัสประเภทหน่วยบริการ"),
    health_service_type_ids_exclude: Optional[List[str]] = Query(
        None,
        description="ตัดประเภทหน่วยบริการที่ไม่ต้องการ (ใส่ key ซ้ำได้หลายค่า)",
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    resolved_province_code = province_code or provinceCode or province
    resolved_district_code = district_code or districtCode or district
    resolved_subdistrict_code = subdistrict_code or subdistrictCode or subdistrict
    return await GeographyManagementService.list_health_services(
        keyword=keyword,
        province_code=resolved_province_code,
        district_code=resolved_district_code,
        subdistrict_code=resolved_subdistrict_code,
        health_service_code=health_service_code,
        legacy_5digit_code=legacy_5digit_code,
        legacy_9digit_code=legacy_9digit_code,
        health_service_type_id=health_service_type_id,
        health_service_type_ids_exclude=health_service_type_ids_exclude,
        limit=limit,
        offset=offset,
    )


@geo_management_router.get("/health-services/{health_service_code}")
async def get_health_service(
    health_service_code: str = Path(..., description="รหัสหน่วยบริการ"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.get_health_service(health_service_code)


@geo_management_router.post("/health-services", status_code=status.HTTP_201_CREATED)
async def create_health_service(
    payload: HealthServiceCreateRequest,
    current_user: dict = Depends(_require_officer),
):
    return await GeographyManagementService.create_health_service(
        payload.model_dump(),
        actor_id=current_user.get("user_id"),
    )


@geo_management_router.patch("/health-services/{health_service_code}")
async def update_health_service(
    health_service_code: str = Path(..., description="รหัสหน่วยบริการ"),
    payload: HealthServiceUpdateRequest = None,
    current_user: dict = Depends(_require_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    return await GeographyManagementService.update_health_service(
        health_service_code,
        data,
        actor_id=current_user.get("user_id"),
    )


@geo_management_router.delete("/health-services/{health_service_code}")
async def delete_health_service(
    health_service_code: str = Path(..., description="รหัสหน่วยบริการ"),
    current_user: dict = Depends(_require_officer),
):
    return await GeographyManagementService.delete_health_service(
        health_service_code,
        actor_id=current_user.get("user_id"),
    )


# Municipalities --------------------------------------------------------------


@geo_management_router.get("/municipalities")
async def list_municipalities(
    keyword: Optional[str] = Query(None, description="ค้นหาเทศบาล"),
    municipality_type_code: Optional[str] = Query(None, description="รหัสประเภทเทศบาล"),
    province_code: Optional[str] = Query(None, description="รหัสจังหวัด"),
    district_code: Optional[str] = Query(None, description="รหัสอำเภอ"),
    subdistrict_code: Optional[str] = Query(None, description="รหัสตำบล"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.list_municipalities(
        keyword=keyword,
        municipality_type_code=municipality_type_code,
        province_code=province_code,
        district_code=district_code,
        subdistrict_code=subdistrict_code,
        limit=limit,
        offset=offset,
    )


@geo_management_router.get("/municipalities/{municipality_id}")
async def get_municipality(
    municipality_id: str = Path(..., description="ID เทศบาล"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.get_municipality(municipality_id)


@geo_management_router.post("/municipalities", status_code=status.HTTP_201_CREATED)
async def create_municipality(
    payload: MunicipalityCreateRequest,
    current_user: dict = Depends(_require_officer),
):
    return await GeographyManagementService.create_municipality(
        payload.model_dump(),
        actor_id=current_user.get("user_id"),
    )


@geo_management_router.patch("/municipalities/{municipality_id}")
async def update_municipality(
    municipality_id: str = Path(..., description="ID เทศบาล"),
    payload: MunicipalityUpdateRequest = None,
    current_user: dict = Depends(_require_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    return await GeographyManagementService.update_municipality(
        municipality_id,
        data,
        actor_id=current_user.get("user_id"),
    )


@geo_management_router.delete("/municipalities/{municipality_id}")
async def delete_municipality(
    municipality_id: str = Path(..., description="ID เทศบาล"),
    current_user: dict = Depends(_require_officer),
):
    return await GeographyManagementService.delete_municipality(
        municipality_id,
        actor_id=current_user.get("user_id"),
    )


# Health Areas ----------------------------------------------------------------


@geo_management_router.get("/health-areas")
async def list_health_areas(
    keyword: Optional[str] = Query(None, description="ค้นหาเขตสุขภาพ"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.list_health_areas(
        keyword=keyword,
        limit=limit,
        offset=offset,
    )


@geo_management_router.get("/health-areas/{code}")
async def get_health_area(
    code: str = Path(..., description="รหัสเขตสุขภาพ"),
    _: dict = Depends(_require_officer),
):
    return await GeographyManagementService.get_health_area(code)


@geo_management_router.post("/health-areas", status_code=status.HTTP_201_CREATED)
async def create_health_area(
    payload: HealthAreaCreateRequest,
    current_user: dict = Depends(_require_officer),
):
    return await GeographyManagementService.create_health_area(
        payload.model_dump(),
        actor_id=current_user.get("user_id"),
    )


@geo_management_router.patch("/health-areas/{code}")
async def update_health_area(
    code: str = Path(..., description="รหัสเขตสุขภาพ"),
    payload: HealthAreaUpdateRequest = None,
    current_user: dict = Depends(_require_officer),
):
    data = payload.model_dump(exclude_unset=True) if payload else {}
    return await GeographyManagementService.update_health_area(
        code,
        data,
        actor_id=current_user.get("user_id"),
    )


@geo_management_router.delete("/health-areas/{code}")
async def delete_health_area(
    code: str = Path(..., description="รหัสเขตสุขภาพ"),
    current_user: dict = Depends(_require_officer),
):
    return await GeographyManagementService.delete_health_area(
        code,
        actor_id=current_user.get("user_id"),
    )
