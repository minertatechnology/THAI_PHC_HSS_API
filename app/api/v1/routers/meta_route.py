from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, Query

from app.api.middleware.mock_auth import get_mock_current_user
from app.services.mock_data_store import MockDataStore


meta_router = APIRouter(prefix="/meta", tags=["meta"])


def _meta_response(items, message: str = "Success") -> Dict[str, object]:
    return {"success": True, "message": message, "items": items}


_META_KEYS: Dict[str, str] = {
    "prefixes": "prefixes",
    "genders": "genders",
    "education-levels": "education-levels",
    "marital-status": "marital-status",
    "occupations": "occupations",
    "religions": "religions",
    "banks": "banks",
    "health-facilities": "health-facilities",
    "children-count": "children-count",
    "positions": "positions",
    "specialties": "specialties",
    "osmo-club-positions": "osmo-club-positions",
    "vaccine-types": "vaccine-types",
    "training-courses": "training-courses",
    "nfe-levels": "nfe-levels",
    "award-levels": "award-levels",
    "award-categories": "award-categories",
    "resignation-reasons": "resignation-reasons",
    "activity-locations": "activity-locations",
}


def _register_meta_endpoint(path: str, key: str) -> None:
    async def _endpoint(current_user=Depends(get_mock_current_user)):
        items = MockDataStore.get_meta(key)
        return _meta_response(items)

    meta_router.add_api_route(path, _endpoint, methods=["GET"])


for route_path, meta_key in _META_KEYS.items():
    _register_meta_endpoint(f"/{route_path}", meta_key)


@meta_router.get("/years")
async def meta_years(
    range: str = Query("be", description="Range type: be or ce"),
    count: int = Query(50, ge=1, le=200),
    current_user=Depends(get_mock_current_user),
):
    items = MockDataStore.get_years(range, count)
    return _meta_response(items)


@meta_router.get("/course-catalog")
async def meta_course_catalog(
    year: int = Query(2568),
    current_user=Depends(get_mock_current_user),
):
    catalog = MockDataStore.get_course_catalog(year)
    return {"success": True, "message": "Success", **catalog}


@meta_router.get("/form-config")
async def meta_form_config(current_user=Depends(get_mock_current_user)):
    config = MockDataStore.get_form_config()
    return {"success": True, "message": "Success", "data": config}
