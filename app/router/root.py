from fastapi import APIRouter
from app.configs.config import settings
from app.api.v1.routers.healthcheck import healthcheck_router
from app.api.v1.routers.oauth2_route import oauth2_router
from app.api.v1.routers.osm_route import osm_router
from app.api.v1.routers.report_route import report_router
from app.api.v1.routers.report_definition_route import report_definition_router
from app.api.v1.routers.officer_route import officer_router
from app.api.v1.routers.thaid_route import router as thaid_router
from app.api.v1.routers.volunteer_route import volunteer_router
from app.api.v1.routers.meta_route import meta_router
from app.api.v1.routers.area_route import area_router
from app.api.v1.routers.area_info_route import area_info_router
from app.api.v1.routers.announcement_route import announcement_router
from app.api.v1.routers.reports_router import reports_router
from app.api.v1.routers.admin_route import admin_router
from app.api.v1.routers.yuwa_osm_route import yuwa_osm_router
from app.api.v1.routers.people_route import people_router
from app.api.v1.routers.lookup_route import lookup_router
from app.api.v1.routers.user_lookup_route import user_lookup_router
from app.api.v1.routers.dashboard_route import dashboard_router
from app.api.v1.routers.geography_management_route import geo_management_router
from app.api.v1.routers.permission_page_route import permission_page_router
from app.api.v1.routers.news_route import news_router
from app.api.v1.routers.mobile_menu_route import mobile_menu_router
from app.api.v1.routers.mobile_banner_route import mobile_banner_router
from app.api.v1.routers.osm_outstanding_route import osm_outstanding_router
from app.api.v1.routers.notification_route import notification_router
from app.api.v1.routers.gen_h_route import gen_h_router

v1_router = APIRouter(prefix=f"{settings.API_V1_PREFIX}")

v1_router.include_router(healthcheck_router)
v1_router.include_router(oauth2_router)
v1_router.include_router(osm_router) 
v1_router.include_router(report_router)
v1_router.include_router(report_definition_router)
v1_router.include_router(officer_router)
v1_router.include_router(thaid_router)
v1_router.include_router(volunteer_router)
v1_router.include_router(meta_router)
v1_router.include_router(area_router)
v1_router.include_router(area_info_router)
v1_router.include_router(announcement_router)
v1_router.include_router(reports_router)
v1_router.include_router(admin_router)
v1_router.include_router(yuwa_osm_router)
v1_router.include_router(people_router)
v1_router.include_router(lookup_router)
v1_router.include_router(user_lookup_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(geo_management_router)
v1_router.include_router(permission_page_router)
v1_router.include_router(news_router)
v1_router.include_router(mobile_menu_router)
v1_router.include_router(mobile_banner_router)
v1_router.include_router(osm_outstanding_router)
v1_router.include_router(notification_router)
v1_router.include_router(gen_h_router)


rootRouter = APIRouter()
rootRouter.include_router(healthcheck_router)
rootRouter.include_router(v1_router)
