from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.api.v1.schemas.osm_schema import OsmCreateSchema, OsmUpdateSchema
from app.api.v1.schemas.query_schema import OsmQueryParams
from app.models.audit_model import AdminAuditLog
from app.models.osm_model import OSMProfile
from app.repositories.osm_profile_repository import OSMProfileRepository
from app.services.audit_service import AuditService
from app.services.osm_service import OsmService


def _enum_to_str(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    return value


def _serialize_prefix(prefix: Optional[Any]) -> Optional[Dict[str, Any]]:
    if prefix is None:
        return None
    return {
        "id": str(prefix.id),
        "nameTh": getattr(prefix, "prefix_name_th", None),
        "nameEn": getattr(prefix, "prefix_name_en", None),
    }


def _serialize_geo(entity: Optional[Any], code_attr: str, name_attr: str) -> Optional[Dict[str, Any]]:
    if entity is None:
        return None
    code = getattr(entity, code_attr, None)
    name = getattr(entity, name_attr, None)
    if not code and not name:
        return None
    return {
        "id": code,
        "code": code,
        "name": name,
    }


def _serialize_health_service(entity: Optional[Any]) -> Optional[Dict[str, Any]]:
    if entity is None:
        return None
    return {
        "code": getattr(entity, "health_service_code", None),
        "name": getattr(entity, "health_service_name_th", None),
    }


def _serialize_contact(profile: OSMProfile) -> Dict[str, Any]:
    citizen_id = getattr(profile, "citizen_id", None)
    gender = getattr(profile, "gender", None)
    return {
        "citizenId": citizen_id,
        "prefix": _serialize_prefix(getattr(profile, "prefix", None)),
        "gender": _enum_to_str(gender) if gender is not None else None,
        "phone": getattr(profile, "phone", None),
        "email": getattr(profile, "email", None),
        "birthDate": profile.birth_date.isoformat() if getattr(profile, "birth_date", None) else None,
    }


def _serialize_address(profile: OSMProfile) -> Dict[str, Any]:
    return {
        "houseNumber": getattr(profile, "address_number", None),
        "alley": getattr(profile, "alley", None),
        "street": getattr(profile, "street", None),
        "village": getattr(profile, "village_name", None),
        "villageNo": getattr(profile, "village_no", None),
        "postalCode": getattr(profile, "postal_code", None),
        "province": _serialize_geo(getattr(profile, "province", None), "province_code", "province_name_th"),
        "district": _serialize_geo(getattr(profile, "district", None), "district_code", "district_name_th"),
        "subDistrict": _serialize_geo(getattr(profile, "subdistrict", None), "subdistrict_code", "subdistrict_name_th"),
    }


def _serialize_spouse(spouse: Optional[Any]) -> Optional[Dict[str, Any]]:
    if spouse is None:
        return None
    gender = getattr(spouse, "gender", None)
    return {
        "id": str(spouse.id),
        "citizenId": spouse.citizen_id,
        "prefix": _serialize_prefix(getattr(spouse, "prefix", None)),
        "firstName": spouse.first_name,
        "lastName": spouse.last_name,
        "phone": spouse.phone,
        "email": spouse.email,
        "gender": _enum_to_str(gender) if gender is not None else None,
        "birthDate": spouse.birth_date.isoformat() if getattr(spouse, "birth_date", None) else None,
        "occupationId": str(spouse.occupation_id) if getattr(spouse, "occupation_id", None) else None,
        "occupationNameTh": getattr(getattr(spouse, "occupation", None), "occupation_name_th", None),
        "educationId": str(spouse.education_id) if getattr(spouse, "education_id", None) else None,
        "educationNameTh": getattr(getattr(spouse, "education", None), "education_name_th", None),
        "bloodType": _enum_to_str(spouse.blood_type),
        "address": {
            "houseNumber": spouse.address_number,
            "alley": spouse.alley,
            "street": spouse.street,
            "village": spouse.village_name,
            "villageNo": spouse.village_no,
            "postalCode": spouse.postal_code,
            "province": _serialize_geo(getattr(spouse, "province", None), "province_code", "province_name_th"),
            "district": _serialize_geo(getattr(spouse, "district", None), "district_code", "district_name_th"),
            "subDistrict": _serialize_geo(getattr(spouse, "subdistrict", None), "subdistrict_code", "subdistrict_name_th"),
        },
    }


def _serialize_children(children: Optional[List[Any]]) -> List[Dict[str, Any]]:
    if not children:
        return []
    serialized: List[Dict[str, Any]] = []
    for child in children:
        gender = getattr(child, "gender", None)
        serialized.append(
            {
                "id": str(child.id),
                "order": child.order_of_children,
                "citizenId": child.citizen_id,
                "prefix": _serialize_prefix(getattr(child, "prefix", None)),
                "firstName": child.first_name,
                "lastName": child.last_name,
                "gender": _enum_to_str(gender) if gender is not None else None,
                "birthDate": child.birth_date.isoformat() if getattr(child, "birth_date", None) else None,
                "occupationId": str(child.occupation_id) if getattr(child, "occupation_id", None) else None,
                "occupationNameTh": getattr(getattr(child, "occupation", None), "occupation_name_th", None),
                "educationId": str(child.education_id) if getattr(child, "education_id", None) else None,
                "educationNameTh": getattr(getattr(child, "education", None), "education_name_th", None),
                "bloodType": _enum_to_str(child.blood_type),
                "address": {
                    "houseNumber": child.address_number,
                    "alley": child.alley,
                    "street": child.street,
                    "village": child.village_name,
                    "villageNo": child.village_no,
                    "postalCode": child.postal_code,
                    "province": _serialize_geo(getattr(child, "province", None), "province_code", "province_name_th"),
                    "district": _serialize_geo(getattr(child, "district", None), "district_code", "district_name_th"),
                    "subDistrict": _serialize_geo(getattr(child, "subdistrict", None), "subdistrict_code", "subdistrict_name_th"),
                },
            }
        )
    return serialized


class VolunteerService:
    @staticmethod
    async def list_volunteers(filter_params: OsmQueryParams) -> Dict[str, Any]:
        volunteers = await OSMProfileRepository.find_all_osm(filter_params)
        total = await OSMProfileRepository.count_filtered_osm(filter_params)

        items: List[Dict[str, Any]] = []
        for profile in volunteers:
            osm_code = getattr(profile, "osm_code", None)
            volunteer_status = getattr(profile, "volunteer_status", None)
            items.append(
                {
                    "id": str(profile.id),
                    "osmCode": osm_code,
                    "firstName": getattr(profile, "first_name", None),
                    "lastName": getattr(profile, "last_name", None),
                    "status": _enum_to_str(volunteer_status) if volunteer_status is not None else None,
                    "hospitalCode": getattr(getattr(profile, "health_service", None), "health_service_code", None),
                    "healthService": _serialize_health_service(getattr(profile, "health_service", None)),
                    "province": _serialize_geo(getattr(profile, "province", None), "province_code", "province_name_th"),
                    "district": _serialize_geo(getattr(profile, "district", None), "district_code", "district_name_th"),
                    "subDistrict": _serialize_geo(getattr(profile, "subdistrict", None), "subdistrict_code", "subdistrict_name_th"),
                    "personal": _serialize_contact(profile),
                    "createdAt": profile.created_at.isoformat() if getattr(profile, "created_at", None) else None,
                    "updatedAt": profile.updated_at.isoformat() if getattr(profile, "updated_at", None) else None,
                }
            )

        return {
            "success": True,
            "message": "Volunteers fetched",
            "items": items,
            "total": total,
            "page": filter_params.page,
            "pageSize": filter_params.limit,
        }

    @staticmethod
    async def get_volunteer(volunteer_id: str) -> Dict[str, Any]:
        result = await OSMProfileRepository.find_osm_by_id(volunteer_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="volunteer_not_found")

        profile: OSMProfile = result["osm_profile"]
        spouse = result.get("spouses", [])
        first_spouse = spouse[0] if spouse else None
        children = result.get("children", [])

        data = {
            "id": str(profile.id),
            "osmCode": profile.osm_code,
            "status": _enum_to_str(profile.volunteer_status),
            "approvalStatus": _enum_to_str(profile.approval_status),
            "personal": _serialize_contact(profile),
            "address": _serialize_address(profile),
            "healthService": _serialize_health_service(getattr(profile, "health_service", None)),
            "bank": {
                "id": str(profile.bank_id) if profile.bank_id else None,
                "nameTh": getattr(getattr(profile, "bank", None), "bank_name_th", None),
            }
            if getattr(profile, "bank", None)
            else None,
            "volunteerStatus": _enum_to_str(profile.volunteer_status),
            "isSmartphoneOwner": profile.is_smartphone_owner,
            "allowance": {
                "year": profile.allowance_year,
                "months": profile.allowance_months,
                "status": _enum_to_str(profile.new_registration_allowance_status),
            },
            "spouse": _serialize_spouse(first_spouse),
            "children": _serialize_children(children),
            "createdAt": profile.created_at.isoformat() if profile.created_at else None,
            "updatedAt": profile.updated_at.isoformat() if profile.updated_at else None,
            "training": {
                "selectedCourseIds": [],
                "lastTrainingAt": None,
            },
            "outstanding": {
                "items": [],
            },
            "activityPhotos": [],
        }

        return {
            "success": True,
            "message": "Volunteer fetched",
            "data": data,
        }

    @staticmethod
    async def create_volunteer(payload: OsmCreateSchema, current_user: Dict[str, Any]) -> Dict[str, Any]:
        user_id = current_user.get("user_id")
        result = await OsmService.create_osm(payload, current_user=current_user)
        data = result.get("data") if isinstance(result, dict) else None

        await AuditService.log_action(
            user_id=user_id,
            action_type="create",
            target_type="volunteer",
            description=f"Created volunteer {data.get('id') if data else ''}",
            new_data={
                "volunteerId": data.get("id") if data else None,
                "payload": payload.model_dump(),
            },
        )

        return {
            "success": True,
            "message": result.get("message", "Volunteer created"),
            "data": data,
        }

    @staticmethod
    async def update_volunteer(volunteer_id: str, payload: OsmUpdateSchema, user_id: str) -> Dict[str, Any]:
        existing = await OSMProfileRepository.find_osm_by_id(volunteer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="volunteer_not_found")

        old_profile: OSMProfile = existing["osm_profile"]
        update_data = payload.model_dump(exclude_unset=True)
        updated = await OsmService.update_osm(volunteer_id, payload, user_id)

        await AuditService.log_action(
            user_id=user_id,
            action_type="update",
            target_type="volunteer",
            description=f"Updated volunteer {volunteer_id}",
            old_data={
                "volunteerId": volunteer_id,
                "firstName": old_profile.first_name,
                "lastName": old_profile.last_name,
            },
            new_data={
                "volunteerId": volunteer_id,
                "changes": update_data,
            },
        )

        return {
            "success": True,
            "message": "Volunteer updated",
            "data": updated,
        }

    @staticmethod
    async def delete_volunteer(volunteer_id: str, user_id: str) -> Dict[str, Any]:
        await OsmService.delete_osm(volunteer_id)

        await AuditService.log_action(
            user_id=user_id,
            action_type="delete",
            target_type="volunteer",
            description=f"Deleted volunteer {volunteer_id}",
            old_data={"volunteerId": volunteer_id},
        )

        return {
            "success": True,
            "message": "Volunteer deleted",
        }

    @staticmethod
    async def get_history(volunteer_id: str, page: int, page_size: int) -> Dict[str, Any]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        query = AdminAuditLog.filter(
            target_type="volunteer",
            new_data__contains={"volunteerId": volunteer_id},
        ).order_by("-created_at")

        total = await query.count()
        logs = await query.offset((page - 1) * page_size).limit(page_size)

        items = [
            {
                "id": str(log.id),
                "timestamp": log.created_at.isoformat() if isinstance(log.created_at, datetime) else str(log.created_at),
                "action": log.action_type,
                "description": log.description,
                "by": str(log.user_id) if isinstance(log.user_id, UUID) else log.user_id,
                "success": log.success,
            }
            for log in logs
        ]

        return {
            "success": True,
            "message": "History fetched",
            "items": items,
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
