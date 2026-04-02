from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.api.middleware.mock_auth import get_mock_current_user
from app.services.mock_data_store import MockDataStore


area_info_router = APIRouter(prefix="/area-info", tags=["area-info"])


def _area_info(level: str, year: Optional[str], province: Optional[str], district: Optional[str], subdistrict: Optional[str], search: Optional[str], page: int, page_size: int):
    filters = {
        "year": year,
        "province": province,
        "district": district,
        "subdistrict": subdistrict,
        "search": search,
    }
    return MockDataStore.get_area_info(level, filters, page, page_size)


@area_info_router.get("/provinces")
async def area_info_provinces(
    year: Optional[str] = None,
    province: Optional[str] = None,
    district: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    return _area_info("provinces", year, province, district, None, search, page, pageSize)


@area_info_router.get("/districts")
async def area_info_districts(
    year: Optional[str] = None,
    province: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    return _area_info("districts", year, province, None, None, search, page, pageSize)


@area_info_router.get("/subdistricts")
async def area_info_subdistricts(
    year: Optional[str] = None,
    province: Optional[str] = None,
    district: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    return _area_info("subdistricts", year, province, district, None, search, page, pageSize)


@area_info_router.get("/villages")
async def area_info_villages(
    year: Optional[str] = None,
    subdistrict: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    return _area_info("villages", year, None, None, subdistrict, search, page, pageSize)


@area_info_router.get("/communities")
async def area_info_communities(
    year: Optional[str] = None,
    village: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    current_user=Depends(get_mock_current_user),
):
    return _area_info("communities", year, None, None, village, search, page, pageSize)
