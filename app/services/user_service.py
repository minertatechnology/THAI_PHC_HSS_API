from copy import deepcopy
from typing import Any, Dict, Optional

from app.api.v1.exceptions.http_exceptions import NotFoundException
from app.repositories.officer_profile_repository import OfficerProfileRepository
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.repositories.people_user_repository import PeopleUserRepository
from app.repositories.gen_h_user_repository import GenHUserRepository
from app.models.geography_model import Village

class UserService:
    @staticmethod
    def _serialize_prefix(prefix: Any, fallback_name: Optional[str] = None) -> Optional[Dict[str, Optional[str]]]:
        if not prefix and not fallback_name:
            return None
        prefix_id = getattr(prefix, "id", None)
        name_th = getattr(prefix, "prefix_name_th", None) or fallback_name
        name_en = getattr(prefix, "prefix_name_en", None)
        if not (prefix_id or name_th or name_en):
            return None
        return {
            "id": str(prefix_id) if prefix_id else None,
            "name_th": name_th,
            "name_en": name_en,
        }

    @staticmethod
    def _serialize_health_service(health_service: Any) -> Optional[Dict[str, Any]]:
        if not health_service:
            return None
        code = getattr(health_service, "health_service_code", None)
        hs_type = getattr(health_service, "health_service_type", None)
        payload: Dict[str, Any] = {
            "id": str(code) if code is not None else None,
            "code": code,
            "name_th": getattr(health_service, "health_service_name_th", None),
            "name_en": getattr(health_service, "health_service_name_en", None),
            "legacy_5digit_code": getattr(health_service, "legacy_5digit_code", None),
            "legacy_9digit_code": getattr(health_service, "legacy_9digit_code", None),
        }
        if hs_type:
            type_id = getattr(hs_type, "id", None)
            payload["type"] = {
                "id": str(type_id) if type_id else None,
                "name_th": getattr(hs_type, "health_service_type_name_th", None),
                "name_en": getattr(hs_type, "health_service_type_name_en", None),
            }
        else:
            payload["type"] = None
        return payload

    @staticmethod
    def _is_hospital_service(health_service: Any) -> bool:
        if not health_service:
            return False
        keywords = ("โรงพยาบาล", "hospital")
        candidate_sources = [
            getattr(health_service, "health_service_name_th", "") or "",
            getattr(health_service, "health_service_name_en", "") or "",
        ]
        hs_type = getattr(health_service, "health_service_type", None)
        if hs_type:
            candidate_sources.append(getattr(hs_type, "health_service_type_name_th", "") or "")
            candidate_sources.append(getattr(hs_type, "health_service_type_name_en", "") or "")
        combined = " ".join(candidate_sources).lower()
        return any(keyword in combined for keyword in keywords)

    @staticmethod
    async def _fetch_village_snapshot(village_code: Optional[str]) -> Optional[Dict[str, Any]]:
        if not village_code:
            return None
        village = (
            await Village
            .filter(village_code=village_code, deleted_at__isnull=True)
            .only("village_code", "village_name_th", "village_name_en", "village_no")
            .first()
        )
        if not village:
            return None
        return {
            "code": getattr(village, "village_code", None),
            "name_th": getattr(village, "village_name_th", None),
            "name_en": getattr(village, "village_name_en", None),
            "village_no": getattr(village, "village_no", None),
        }

    @staticmethod
    def _merge_village_snapshot(user_info: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        if not snapshot:
            return
        if snapshot.get("code") and not user_info.get("village_code"):
            user_info["village_code"] = snapshot["code"]
        preferred_name = snapshot.get("name_th") or snapshot.get("name_en")
        if preferred_name:
            user_info["village_name"] = preferred_name
        if snapshot.get("name_th") is not None:
            user_info["village_name_th"] = snapshot.get("name_th")
        if snapshot.get("name_en") is not None:
            user_info["village_name_en"] = snapshot.get("name_en")
        if snapshot.get("village_no") is not None:
            user_info["village_no"] = snapshot.get("village_no")

    @staticmethod
    async def _attach_village_metadata(user_info: Dict[str, Any]) -> None:
        village_code = user_info.get("village_code")
        if not village_code:
            return
        snapshot = await UserService._fetch_village_snapshot(village_code)
        if not snapshot:
            return
        UserService._merge_village_snapshot(user_info, snapshot)

    async def get_user_info(user_id: str, scopes: list = None, user_type: str = None)-> Dict[str, Any]:  
        user_info: Dict[str, Any] = {
            "sub": user_id,
            "user_type": user_type,
            "is_first_login": False,
            "prefix": None,
            "hospital": None,
            "service_unit": None,
        }  # sub (subject) ต้องมีเสมอ

        if user_type == "osm":
            # ใช้ method ที่มี related fields สำหรับ UserInfo
            osm_profile = await OSMProfileRepository.find_osm_profile_with_related_fields(user_id)
            if osm_profile:
                user_info["citizen_id"] = osm_profile.citizen_id
                user_info["osm_code"] = osm_profile.osm_code
                user_info["is_first_login"] = bool(getattr(osm_profile, "is_first_login", False))

                if not scopes or "profile" in scopes:
                    # สร้างชื่อเต็มพร้อม prefix
                    full_name = f"{osm_profile.first_name} {osm_profile.last_name}"
                    prefix_payload = UserService._serialize_prefix(getattr(osm_profile, "prefix", None))
                    if prefix_payload and prefix_payload.get("name_th"):
                        full_name = f"{prefix_payload['name_th']} {full_name}"

                    user_info.update({
                        "name": full_name,  # ใช้ name แทน prefix + first_name + last_name
                        "prefix": prefix_payload,
                        "profile_image": getattr(osm_profile, "profile_image", None),
                    })

                # Address scope (ถ้ามี)
                if not scopes or "address" in scopes:
                    address_info = {}
                    if osm_profile.province:
                        address_info["province_code"] = osm_profile.province.province_code
                        address_info["province_name"] = osm_profile.province.province_name_th
                    if osm_profile.district:
                        address_info["district_code"] = osm_profile.district.district_code
                        address_info["district_name"] = osm_profile.district.district_name_th
                    if osm_profile.subdistrict:
                        address_info["subdistrict_code"] = osm_profile.subdistrict.subdistrict_code
                        address_info["subdistrict_name"] = osm_profile.subdistrict.subdistrict_name_th
                    village_code = getattr(osm_profile, "village_code", None) or None
                    if village_code:
                        address_info["village_code"] = village_code
                    address_info["address_number"] = getattr(osm_profile, "address_number", None)
                    address_info["village_no"] = getattr(osm_profile, "village_no", None)
                    address_info["village_name"] = getattr(osm_profile, "village_name", None)
                    address_info["alley"] = getattr(osm_profile, "alley", None)
                    address_info["street"] = getattr(osm_profile, "street", None)
                    address_info["postal_code"] = getattr(osm_profile, "postal_code", None)
                    user_info.update(address_info)

                if not scopes or "phone" in scopes:
                    user_info["phone"] = osm_profile.phone

                if not scopes or "email" in scopes:
                    user_info["email"] = osm_profile.email

                if not scopes or "birth_date" in scopes:
                    user_info["birth_date"] = str(osm_profile.birth_date) if osm_profile.birth_date else None

                if not scopes or "gender" in scopes:
                    user_info["gender"] = osm_profile.gender.value if osm_profile.gender else None

                health_service = getattr(osm_profile, "health_service", None)
                service_unit_payload = UserService._serialize_health_service(health_service)
                if service_unit_payload:
                    user_info["service_unit"] = service_unit_payload
                    if UserService._is_hospital_service(health_service):
                        user_info["hospital"] = deepcopy(service_unit_payload)
        
        elif user_type == "officer":
            officer_profile = await OfficerProfileRepository.find_officer_profile_with_related_fields(user_id)
            if officer_profile:
                user_info["citizen_id"] = officer_profile.citizen_id
                user_info["osm_code"] = getattr(officer_profile, "osm_code", None)
                user_info["is_first_login"] = bool(getattr(officer_profile, "is_first_login", False))

                health_service = getattr(officer_profile, "health_service", None)
                health_service_id = getattr(officer_profile, "health_service_id", None)
                health_service_code = getattr(health_service, "health_service_code", None)
                health_service_name_th = getattr(health_service, "health_service_name_th", None)
                user_info["health_service_id"] = health_service_code or health_service_id
                user_info["health_service_name_th"] = health_service_name_th

                if not scopes or "profile" in scopes:
                    prefix_payload = UserService._serialize_prefix(getattr(officer_profile, "prefix", None))
                    full_name = f"{officer_profile.first_name} {officer_profile.last_name}"
                    if prefix_payload and prefix_payload.get("name_th"):
                        full_name = f"{prefix_payload['name_th']} {full_name}"
                    user_info.update({
                        "name": full_name,
                        "prefix": prefix_payload,
                        "profile_image": getattr(officer_profile, "profile_image", None),
                    })

                # include position context to determine scope permissions on the client
                if officer_profile.position:
                    user_info["position_id"] = str(officer_profile.position.id)
                    user_info["position_name_th"] = getattr(officer_profile.position, "position_name_th", None)
                    scope_level = getattr(officer_profile.position, "scope_level", None)
                    user_info["position_scope_level"] = scope_level.value if scope_level else None

                if not scopes or "address" in scopes:
                    address_info = {}
                    province_obj = officer_profile.province
                    if province_obj:
                        address_info["province_code"] = province_obj.province_code
                        address_info["province_name"] = province_obj.province_name_th

                        # region (ภาค)
                        region_obj = getattr(province_obj, "region", None)
                        if region_obj:
                            address_info["region_code"] = getattr(region_obj, "code", None)
                            address_info["region_name"] = getattr(region_obj, "region_name_th", None)
                        elif getattr(province_obj, "region_id", None):
                            address_info["region_code"] = str(province_obj.region_id)

                        # health_area (เขตสุขภาพ) — from province relation
                        ha_obj = getattr(province_obj, "health_area", None)
                        if ha_obj:
                            address_info["health_area_code"] = getattr(ha_obj, "code", None)
                            address_info["health_area_name"] = getattr(ha_obj, "health_area_name_th", None)
                        elif getattr(province_obj, "health_area_id", None):
                            address_info["health_area_code"] = str(province_obj.health_area_id)

                    if officer_profile.district:
                        address_info["district_code"] = officer_profile.district.district_code
                        address_info["district_name"] = officer_profile.district.district_name_th
                    if officer_profile.subdistrict:
                        address_info["subdistrict_code"] = officer_profile.subdistrict.subdistrict_code
                        address_info["subdistrict_name"] = officer_profile.subdistrict.subdistrict_name_th
                    area_code = getattr(officer_profile, "area_code", None) or None
                    if area_code:
                        address_info["area_code"] = area_code
                        address_info["village_code"] = area_code

                    # fallback health_area from officer's own FK (if province didn't resolve it)
                    if "health_area_code" not in address_info:
                        ha_direct = getattr(officer_profile, "health_area", None)
                        if ha_direct:
                            address_info["health_area_code"] = getattr(ha_direct, "code", None)
                            address_info["health_area_name"] = getattr(ha_direct, "health_area_name_th", None)

                    if health_service_id or health_service_code:
                        address_info["health_service_id"] = str(health_service_code or health_service_id)
                    if health_service_name_th is not None:
                        address_info["health_service_name_th"] = health_service_name_th
                    user_info.update(address_info)

                if not scopes or "phone" in scopes:
                    user_info["phone"] = officer_profile.phone

                if not scopes or "email" in scopes:
                    user_info["email"] = officer_profile.email

                if not scopes or "birth_date" in scopes:
                    user_info["birth_date"] = str(officer_profile.birth_date) if officer_profile.birth_date else None

                if not scopes or "gender" in scopes:
                    user_info["gender"] = officer_profile.gender.value if officer_profile.gender else None
        elif user_type == "yuwa_osm":
            profile = await YuwaOSMUserRepository.find_profile_by_id(user_id)
            if profile:
                user_info["citizen_id"] = profile.citizen_id
                user_info["is_first_login"] = bool(getattr(profile, "is_first_login", False))

                if not scopes or "profile" in scopes:
                    user_info["name"] = f"{profile.first_name} {profile.last_name}".strip()
                    user_info["yuwa_osm_code"] = getattr(profile, "yuwa_osm_code", None)
                    user_info["prefix"] = UserService._serialize_prefix(None, fallback_name=profile.prefix)
                    user_info["school"] = profile.school
                    user_info["organization"] = profile.organization
                    user_info["profile_image"] = getattr(profile, "profile_image", None)
                    user_info["line_id"] = getattr(profile, "line_id", None)
                    user_info["registration_reason"] = getattr(profile, "registration_reason", None)
                    user_info["photo_1inch"] = getattr(profile, "photo_1inch", None)
                    user_info["attachments"] = getattr(profile, "attachments", None)
                if not scopes or "phone" in scopes:
                    user_info["phone"] = profile.phone_number
                if not scopes or "email" in scopes:
                    user_info["email"] = profile.email
                if not scopes or "address" in scopes:
                    if profile.province_code:
                        user_info["province_code"] = profile.province_code
                        user_info["province_name"] = profile.province_name
                    if profile.district_code:
                        user_info["district_code"] = profile.district_code
                        user_info["district_name"] = profile.district_name
                    if profile.subdistrict_code:
                        user_info["subdistrict_code"] = profile.subdistrict_code
                        user_info["subdistrict_name"] = profile.subdistrict_name
                if not scopes or "birth_date" in scopes:
                    user_info["birth_date"] = str(profile.birthday) if profile.birthday else None
        elif user_type == "people":
            profile = await PeopleUserRepository.find_profile_by_id(user_id)
            if profile:
                user_info["citizen_id"] = profile.citizen_id
                user_info["is_first_login"] = bool(getattr(profile, "is_first_login", False))

                if not scopes or "profile" in scopes:
                    user_info["name"] = f"{profile.first_name} {profile.last_name}".strip()
                    user_info["profile_image"] = getattr(profile, "profile_image", None)
                    user_info["line_id"] = getattr(profile, "line_id", None)
                    user_info["organization"] = getattr(profile, "organization", None)
                    user_info["registration_reason"] = getattr(profile, "registration_reason", None)
                    user_info["photo_1inch"] = getattr(profile, "photo_1inch", None)
                    user_info["attachments"] = getattr(profile, "attachments", None)
                    user_info["school"] = getattr(profile, "school", None)
                    user_info["prefix"] = UserService._serialize_prefix(None, fallback_name=getattr(profile, "prefix", None))

                if not scopes or "phone" in scopes:
                    user_info["phone"] = profile.phone_number

                if not scopes or "email" in scopes:
                    user_info["email"] = profile.email

                if not scopes or "address" in scopes:
                    if profile.province_code:
                        user_info["province_code"] = profile.province_code
                        user_info["province_name"] = profile.province_name
                    if profile.district_code:
                        user_info["district_code"] = profile.district_code
                        user_info["district_name"] = profile.district_name
                    if profile.subdistrict_code:
                        user_info["subdistrict_code"] = profile.subdistrict_code
                        user_info["subdistrict_name"] = profile.subdistrict_name

                if not scopes or "birth_date" in scopes:
                    user_info["birth_date"] = str(profile.birthday) if profile.birthday else None

        elif user_type == "gen_h":
            profile = await GenHUserRepository.find_basic_profile_by_id(user_id)
            if profile:
                user_info["gen_h_code"] = profile.gen_h_code
                user_info["is_first_login"] = bool(getattr(profile, "is_first_login", False))
                user_info["points"] = getattr(profile, "points", 0)

                if not scopes or "profile" in scopes:
                    user_info["name"] = f"{profile.first_name} {profile.last_name}".strip()
                    user_info["prefix"] = UserService._serialize_prefix(None, fallback_name=profile.prefix)
                    user_info["school"] = profile.school
                    user_info["profile_image"] = getattr(profile, "profile_image_url", None)
                    user_info["line_id"] = getattr(profile, "line_id", None)
                    user_info["member_card_url"] = getattr(profile, "member_card_url", None)
                if not scopes or "phone" in scopes:
                    user_info["phone"] = profile.phone_number
                if not scopes or "email" in scopes:
                    user_info["email"] = profile.email
                if not scopes or "address" in scopes:
                    if profile.province_code:
                        user_info["province_code"] = profile.province_code
                        user_info["province_name"] = profile.province_name
                    if profile.district_code:
                        user_info["district_code"] = profile.district_code
                        user_info["district_name"] = profile.district_name
                    if profile.subdistrict_code:
                        user_info["subdistrict_code"] = profile.subdistrict_code
                        user_info["subdistrict_name"] = profile.subdistrict_name
                if not scopes or "gender" in scopes:
                    user_info["gender"] = profile.gender

        await UserService._attach_village_metadata(user_info)

        minimal_keys = {"sub", "user_type", "is_first_login", "prefix", "hospital", "service_unit"}
        if not any(key not in minimal_keys for key in user_info if user_info.get(key) is not None):
            raise NotFoundException(detail="User profile not found")
        
        return user_info