from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.middleware.mock_auth import get_mock_current_user
from app.services.mock_data_store import MockDataStore


area_router = APIRouter(prefix="/areas", tags=["areas"])


def _raise_if_error(result: Dict[str, object]):
    if result.get("success"):
        return result
    raise HTTPException(status_code=result.get("status_code", status.HTTP_400_BAD_REQUEST), detail=result.get("message"))


@area_router.get("/provinces")
async def list_provinces(
    keyword: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    filters = {"keyword": keyword}
    return MockDataStore.list_areas("provinces", filters, page, pageSize)


@area_router.post("/provinces")
async def create_province(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.create_area("provinces", payload)
    return _raise_if_error(result)


@area_router.put("/provinces/{province_id}")
async def update_province(province_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.update_area("provinces", province_id, payload)
    return _raise_if_error(result)


@area_router.delete("/provinces/{province_id}")
async def delete_province(province_id: str, current_user=Depends(get_mock_current_user)):
    result = MockDataStore.delete_area("provinces", province_id)
    return _raise_if_error(result)


@area_router.get("/districts")
async def list_districts(
    provinceId: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    filters = {"provinceId": provinceId, "keyword": keyword}
    return MockDataStore.list_areas("districts", filters, page, pageSize)


@area_router.post("/districts")
async def create_district(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.create_area("districts", payload)
    return _raise_if_error(result)


@area_router.put("/districts/{district_id}")
async def update_district(district_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.update_area("districts", district_id, payload)
    return _raise_if_error(result)


@area_router.delete("/districts/{district_id}")
async def delete_district(district_id: str, current_user=Depends(get_mock_current_user)):
    result = MockDataStore.delete_area("districts", district_id)
    return _raise_if_error(result)


@area_router.get("/subdistricts")
async def list_subdistricts(
    provinceId: Optional[str] = None,
    districtId: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    filters = {
        "provinceId": provinceId,
        "districtId": districtId,
        "keyword": keyword,
    }
    return MockDataStore.list_areas("subdistricts", filters, page, pageSize)


@area_router.post("/subdistricts")
async def create_subdistrict(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.create_area("subdistricts", payload)
    return _raise_if_error(result)


@area_router.put("/subdistricts/{subdistrict_id}")
async def update_subdistrict(subdistrict_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.update_area("subdistricts", subdistrict_id, payload)
    return _raise_if_error(result)


@area_router.delete("/subdistricts/{subdistrict_id}")
async def delete_subdistrict(subdistrict_id: str, current_user=Depends(get_mock_current_user)):
    result = MockDataStore.delete_area("subdistricts", subdistrict_id)
    return _raise_if_error(result)


@area_router.get("/villages")
async def list_villages(
    provinceId: Optional[str] = None,
    districtId: Optional[str] = None,
    subdistrictId: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    filters = {
        "provinceId": provinceId,
        "districtId": districtId,
        "subdistrictId": subdistrictId,
        "keyword": keyword,
    }
    return MockDataStore.list_areas("villages", filters, page, pageSize)


@area_router.post("/villages")
async def create_village(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.create_area("villages", payload)
    return _raise_if_error(result)


@area_router.put("/villages/{village_id}")
async def update_village(village_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.update_area("villages", village_id, payload)
    return _raise_if_error(result)


@area_router.delete("/villages/{village_id}")
async def delete_village(village_id: str, current_user=Depends(get_mock_current_user)):
    result = MockDataStore.delete_area("villages", village_id)
    return _raise_if_error(result)


@area_router.get("/communities")
async def list_communities(
    provinceId: Optional[str] = None,
    districtId: Optional[str] = None,
    subdistrictId: Optional[str] = None,
    villageId: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    filters = {
        "provinceId": provinceId,
        "districtId": districtId,
        "subdistrictId": subdistrictId,
        "villageId": villageId,
        "keyword": keyword,
    }
    return MockDataStore.list_areas("communities", filters, page, pageSize)


@area_router.post("/communities")
async def create_community(payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.create_area("communities", payload)
    return _raise_if_error(result)


@area_router.put("/communities/{community_id}")
async def update_community(community_id: str, payload: Dict[str, object], current_user=Depends(get_mock_current_user)):
    result = MockDataStore.update_area("communities", community_id, payload)
    return _raise_if_error(result)


@area_router.delete("/communities/{community_id}")
async def delete_community(community_id: str, current_user=Depends(get_mock_current_user)):
    result = MockDataStore.delete_area("communities", community_id)
    return _raise_if_error(result)
