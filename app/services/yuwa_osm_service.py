from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple, List
from uuid import UUID

from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from fastapi import HTTPException, status

from app.api.v1.schemas.yuwa_osm_schema import (
    YuwaOSMCreateSchema,
    YuwaOSMDecisionPayload,
    YuwaOSMQueryParams,
    YuwaOSMSummaryQueryParams,
    YuwaOSMRejectPayload,
    YuwaOSMResponseSchema,
    YuwaOSMUpdateSchema,
)
from app.models.geography_model import District, Province, Subdistrict
from app.models.personal_model import Prefix
from app.models.enum_models import AdministrativeLevelEnum, ApprovalStatus
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.repositories.people_user_repository import PeopleUserRepository
from app.services.audit_service import AuditService
from app.services.officer_snapshot_helper import build_officer_snapshot
from app.services.officer_service import OfficerService
from app.services.oauth2_service import bcrypt_hash_password
from app.services.notification_service import NotificationService
from app.cache.redis_client import cache_delete_pattern
from app.api.middleware.middleware import invalidate_user_sessions
from app.services.people_service import PeopleService


class YuwaOsmService:
    """Business logic for managing Yuwa OSM accounts."""

    _allowed_approval_status_values = tuple(status.value for status in ApprovalStatus)

    @staticmethod
    async def register_user(payload: YuwaOSMCreateSchema, actor_id: str | None) -> Dict[str, Any]:
        phone = YuwaOsmService._clean_str(payload.phone)
        if phone is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_phone")
        if await YuwaOSMUserRepository.exists_by_phone(phone):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="phone_already_registered")

        citizen_id = YuwaOsmService._clean_str(payload.citizen_id)
        if not citizen_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="citizen_id_required")
        if await YuwaOSMUserRepository.exists_by_citizen_id(citizen_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="citizen_id_already_registered")

        if not payload.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_required")

        first_name = YuwaOsmService._clean_str(payload.first_name)
        last_name = YuwaOsmService._clean_str(payload.last_name)
        if not first_name or not last_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name_required")

        line_id = YuwaOsmService._clean_str(payload.line_id)
        school = YuwaOsmService._clean_str(payload.school)
        organization = YuwaOsmService._clean_str(payload.organization)
        profile_image = YuwaOsmService._clean_str(payload.profile_image)
        registration_reason = YuwaOsmService._clean_str(payload.reason)
        province_name = YuwaOsmService._clean_str(payload.province)
        district_name = YuwaOsmService._clean_str(payload.district)
        subdistrict_name = YuwaOsmService._clean_str(payload.sub_district)
        province_code = YuwaOsmService._clean_str(payload.province_code)
        district_code = YuwaOsmService._clean_str(payload.district_code)
        subdistrict_code = YuwaOsmService._clean_str(payload.subdistrict_code)

        resolved_prefix = await YuwaOsmService._resolve_prefix(payload.prefix)
        province, district, subdistrict = await YuwaOsmService._resolve_geography(
            province_code=province_code,
            province_name=province_name,
            district_code=district_code,
            district_name=district_name,
            subdistrict_code=subdistrict_code,
            subdistrict_name=subdistrict_name,
            province_required=True,
            district_required=True,
            subdistrict_required=True,
        )

        hashed_password = bcrypt_hash_password(payload.password)

        create_payload: Dict[str, Any] = {
            "phone_number": phone,
            "password_hash": hashed_password,
            "is_first_login": False,
            "is_active": False,
            "first_name": first_name,
            "last_name": last_name,
            "gender": YuwaOsmService._normalize_gender(payload.gender),
            "email": payload.email,
            "line_id": line_id,
            "school": school,
            "organization": organization,
            "citizen_id": citizen_id,
            "prefix": resolved_prefix,
            "province_code": province.province_code if province else province_code,
            "province_name": province.province_name_th if province else province_name,
            "district_code": district.district_code if district else district_code,
            "district_name": district.district_name_th if district else district_name,
            "subdistrict_code": subdistrict.subdistrict_code if subdistrict else subdistrict_code,
            "subdistrict_name": subdistrict.subdistrict_name_th if subdistrict else subdistrict_name,
            "profile_image": profile_image,
            "registration_reason": registration_reason,
            "photo_1inch": YuwaOsmService._clean_str(getattr(payload, "photo_1inch", None)),
            "attachments": getattr(payload, "attachments", None),
            "birthday": payload.birthday,
            "approval_status": ApprovalStatus.PENDING.value,
        }

        # remove empty strings to avoid violating DB constraints
        create_payload = {k: v for k, v in create_payload.items() if v not in {None, ""}}

        try:
            user = await YuwaOSMUserRepository.create_user(create_payload)
        except HTTPException:
            raise
        except Exception as exc:
            # Integrity errors already raised; general error fallback for unexpected cases
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        await AuditService.log_action(
            user_id=actor_id,
            action_type="create",
            target_type="yuwa_osm",
            description=f"Registered Yuwa OSM user {user.phone_number}",
            new_data={"yuwaUserId": str(user.id), "phone": user.phone_number},
        )
        await NotificationService.create_notification(
            actor_id=actor_id,
            action_type="create",
            target_type="yuwa_osm",
            target_id=str(user.id),
            target_name=f"{user.first_name} {user.last_name}".strip(),
            citizen_id=getattr(user, "citizen_id", None),
            province_code=getattr(user, "province_code", None),
            district_code=getattr(user, "district_code", None),
            subdistrict_code=getattr(user, "subdistrict_code", None),
        )

        payload = YuwaOsmService._serialize_user(user)
        payload = await YuwaOsmService._attach_actor_metadata(payload)
        return {
            "success": True,
            "message": "Yuwa OSM user registered",
            "data": payload,
        }

    @staticmethod
    def _ensure_management_scope(viewer_scope) -> None:
        allowed_levels = {
            AdministrativeLevelEnum.COUNTRY,
            AdministrativeLevelEnum.REGION,
            AdministrativeLevelEnum.AREA,
            AdministrativeLevelEnum.PROVINCE,
        }
        if viewer_scope is None or getattr(viewer_scope, "level", None) not in allowed_levels:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_scope_department_required")

    @staticmethod
    def _build_public_url(relative_path: str | None) -> str | None:
        if not relative_path:
            return None
        if relative_path.startswith("http://") or relative_path.startswith("https://"):
            return relative_path
        from app.configs.config import settings
        base = settings.PUBLIC_BASE_URL
        if not base:
            return relative_path
        base = base.rstrip("/")
        return f"{base}/{relative_path}"

    @staticmethod
    def _serialize_user(user) -> Dict[str, Any]:
        response = YuwaOSMResponseSchema.model_validate(user)
        payload = response.model_dump(mode="json")
        if payload.get("people_id") is None and payload.get("source_people_id") is not None:
            payload["people_id"] = payload.get("source_people_id")
        if payload.get("profile_image"):
            payload["profile_image"] = YuwaOsmService._build_public_url(payload["profile_image"])
        return payload

    @staticmethod
    async def _attach_actor_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return payload

        approved_snapshot = await build_officer_snapshot(payload.get("approved_by"))
        payload["approved_by_name"] = approved_snapshot.get("name") if approved_snapshot else None
        payload["approved_by_position_name"] = approved_snapshot.get("position_name") if approved_snapshot else None
        payload["approved_by_scope_level"] = approved_snapshot.get("scope_level") if approved_snapshot else None
        payload["approved_by_scope_label"] = approved_snapshot.get("scope_label") if approved_snapshot else None

        rejected_snapshot = await build_officer_snapshot(payload.get("rejected_by"))
        payload["rejected_by_name"] = rejected_snapshot.get("name") if rejected_snapshot else None
        payload["rejected_by_position_name"] = rejected_snapshot.get("position_name") if rejected_snapshot else None
        payload["rejected_by_scope_level"] = rejected_snapshot.get("scope_level") if rejected_snapshot else None
        payload["rejected_by_scope_label"] = rejected_snapshot.get("scope_label") if rejected_snapshot else None
        return payload

    @staticmethod
    def _normalize_approval_status(value: Optional[ApprovalStatus | str]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, ApprovalStatus):
            return value.value
        cleaned = str(value).strip().lower()
        if not cleaned:
            return None
        try:
            return ApprovalStatus(cleaned).value
        except ValueError as exc:
            allowed_display = ", ".join(YuwaOsmService._allowed_approval_status_values)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid_approval_status: expected one of {allowed_display}",
            ) from exc

    @staticmethod
    def _parse_status_filter(value: Optional[str | bool]) -> Tuple[Optional[bool], Optional[str]]:
        """Interpret is_active filter supporting tri-state approval keywords."""
        if value is None:
            return None, None
        if isinstance(value, bool):
            return value, None

        keyword = str(value).strip().lower()
        if not keyword:
            return None, None

        if keyword in {"1", "true", "yes", "active", "ใช้งาน"}:
            return True, None
        if keyword in {"0", "false", "no", "inactive", "ไม่ใช้งาน"}:
            return False, None

        if keyword in {"approved", "อนุมัติ"}:
            return None, ApprovalStatus.APPROVED.value
        if keyword in {"pending", "รออนุมัติ", "รอ"}:
            return None, ApprovalStatus.PENDING.value
        if keyword in {"rejected", "ปฏิเสธ", "ไม่อนุมัติ"}:
            return None, ApprovalStatus.REJECTED.value
        if keyword in {"retired", "พ้นสภาพ"}:
            return None, ApprovalStatus.RETIRED.value

        return None, None

    @staticmethod
    def _birthdate_range_for_age(
        *,
        min_age: Optional[int],
        max_age: Optional[int],
    ) -> Tuple[Optional[date], Optional[date]]:
        today = date.today()
        max_birth_date: Optional[date] = None
        min_birth_date: Optional[date] = None

        if min_age is not None:
            year = today.year - min_age
            try:
                max_birth_date = today.replace(year=year)
            except ValueError:
                max_birth_date = today.replace(year=year, month=2, day=28)

        if max_age is not None:
            year = today.year - max_age
            try:
                min_birth_date = today.replace(year=year)
            except ValueError:
                min_birth_date = today.replace(year=year, month=2, day=28)

        return min_birth_date, max_birth_date

    @staticmethod
    async def list_users(filter_params: YuwaOSMQueryParams, current_user: dict) -> Dict[str, Any]:
        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        YuwaOsmService._ensure_management_scope(viewer_scope)

        status_bool, status_approval = YuwaOsmService._parse_status_filter(filter_params.is_active)
        approval_status = YuwaOsmService._normalize_approval_status(filter_params.approval_status) or status_approval
        records, total = await YuwaOSMUserRepository.list_users(
            page=filter_params.page,
            limit=filter_params.limit,
            search=filter_params.search,
            approval_status=approval_status,
            is_active=status_bool,
            province_code=filter_params.province_code,
            district_code=filter_params.district_code,
            subdistrict_code=filter_params.subdistrict_code,
            order_by=filter_params.order_by or "created_at",
            sort_dir=(filter_params.sort_dir or "desc").lower(),
        )

        items = []
        for record in records:
            serialized = YuwaOsmService._serialize_user(record)
            enriched = await YuwaOsmService._attach_actor_metadata(serialized)
            items.append(enriched)
        pages = 0
        if filter_params.limit:
            pages = (total + filter_params.limit - 1) // filter_params.limit

        return {
            "success": True,
            "message": "Yuwa OSM users fetched",
            "items": items,
            "total": total,
            "page": filter_params.page,
            "pageSize": filter_params.limit,
            "pages": pages,
            "viewer": {
                "id": str(getattr(viewer_profile, "id", "")) if viewer_profile else None,
                "scopeLevel": getattr(getattr(viewer_scope, "level", None), "value", None),
            },
        }

    @staticmethod
    async def summary(filter_params: YuwaOSMSummaryQueryParams, current_user: dict) -> Dict[str, Any]:
        _viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        YuwaOsmService._ensure_management_scope(viewer_scope)

        if filter_params.min_age is not None and filter_params.max_age is not None:
            if filter_params.min_age > filter_params.max_age:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_age_range")

        min_birth_date, max_birth_date = YuwaOsmService._birthdate_range_for_age(
            min_age=filter_params.min_age,
            max_age=filter_params.max_age,
        )
        approval_status = YuwaOsmService._normalize_approval_status(filter_params.approval_status)

        summary = await YuwaOSMUserRepository.summary(
            province=filter_params.province,
            province_code=filter_params.province_code,
            province_name=filter_params.province_name,
            birthday=filter_params.birthday,
            school=filter_params.school,
            organization=filter_params.organization,
            approval_status=approval_status,
            min_birth_date=min_birth_date,
            max_birth_date=max_birth_date,
        )

        return {
            "success": True,
            "message": "Yuwa OSM summary fetched",
            "filters": {
                "province": filter_params.province,
                "province_code": filter_params.province_code,
                "province_name": filter_params.province_name,
                "birthday": filter_params.birthday.isoformat() if filter_params.birthday else None,
                "school": filter_params.school,
                "organization": filter_params.organization,
                "approval_status": approval_status,
                "min_age": filter_params.min_age,
                "max_age": filter_params.max_age,
            },
            "summary": summary,
        }

    @staticmethod
    async def get_user(user_id: str, current_user: dict) -> Dict[str, Any]:
        # yuwa_osm user ดูโปรไฟล์ตัวเอง — bypass officer scope check
        is_self = (
            current_user.get("user_type") == "yuwa_osm"
            and str(current_user.get("user_id")) == str(user_id)
        )

        if not is_self:
            viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
            YuwaOsmService._ensure_management_scope(viewer_scope)

        user = None
        try:
            UUID(str(user_id))
            user = await YuwaOSMUserRepository.get_user_for_management(user_id)
        except (ValueError, TypeError):
            user = None

        if not user:
            if user_id and user_id.isdigit() and len(user_id) == 13:
                user = await YuwaOSMUserRepository.get_user_by_citizen_id(user_id)
            else:
                user = await YuwaOSMUserRepository.get_user_by_yuwa_osm_code(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        if not is_self:
            target_scope, _ = await OfficerService._resolve_yuwa_management_context(user)
            OfficerService._ensure_scope_permission(viewer_scope, target_scope)

        payload = YuwaOsmService._serialize_user(user)
        payload = await YuwaOsmService._attach_actor_metadata(payload)
        return {
            "success": True,
            "message": "Yuwa OSM user fetched",
            "data": payload,
        }

    @staticmethod
    async def update_user(user_id: str, payload: YuwaOSMUpdateSchema, current_user: dict) -> Dict[str, Any]:
        # yuwa_osm user แก้โปรไฟล์ตัวเอง — bypass officer scope check
        is_self = (
            current_user.get("user_type") == "yuwa_osm"
            and str(current_user.get("user_id")) == str(user_id)
        )

        user = await YuwaOSMUserRepository.get_user_for_management(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        updates = payload.model_dump(exclude_unset=True)

        # yuwa_osm user ห้ามแก้ field ที่ officer เท่านั้นที่ทำได้
        existing_location_context = None
        if is_self:
            officer_only_fields = {"is_active"}
            forbidden = officer_only_fields.intersection(updates.keys())
            if forbidden:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"forbidden: cannot update {', '.join(forbidden)}")
        else:
            viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
            YuwaOsmService._ensure_management_scope(viewer_scope)
            target_scope, existing_location_context = await OfficerService._resolve_yuwa_management_context(user)
            require_strict = "is_active" in updates
            OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=require_strict)

        update_payload: Dict[str, Any] = {}
        updated_location_context: Optional[Dict[str, Optional[str]]] = None

        first_name = updates.get("first_name")
        if first_name is not None:
            cleaned = YuwaOsmService._clean_str(first_name)
            if not cleaned:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name_required")
            update_payload["first_name"] = cleaned

        last_name = updates.get("last_name")
        if last_name is not None:
            cleaned = YuwaOsmService._clean_str(last_name)
            if not cleaned:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name_required")
            update_payload["last_name"] = cleaned

        if "phone" in updates:
            phone = YuwaOsmService._clean_str(updates.get("phone"))
            if not phone:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_phone")
            if await YuwaOSMUserRepository.exists_by_phone(phone, exclude_id=user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="phone_already_registered")
            update_payload["phone_number"] = phone

        if "citizen_id" in updates:
            citizen_id = YuwaOsmService._clean_str(updates.get("citizen_id"))
            if not citizen_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="citizen_id_required")
            if await YuwaOSMUserRepository.exists_by_citizen_id(citizen_id, exclude_id=user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="citizen_id_already_registered")
            update_payload["citizen_id"] = citizen_id

        if "gender" in updates:
            update_payload["gender"] = YuwaOsmService._normalize_gender(updates.get("gender"))

        if "email" in updates:
            update_payload["email"] = updates.get("email")

        if "line_id" in updates:
            update_payload["line_id"] = YuwaOsmService._clean_str(updates.get("line_id"))

        if "school" in updates:
            update_payload["school"] = YuwaOsmService._clean_str(updates.get("school"))

        if "organization" in updates:
            update_payload["organization"] = YuwaOsmService._clean_str(updates.get("organization"))

        if "prefix" in updates and updates.get("prefix") is not None:
            update_payload["prefix"] = await YuwaOsmService._resolve_prefix(updates.get("prefix"))

        location_keys = {
            "province",
            "province_code",
            "district",
            "district_code",
            "sub_district",
            "subdistrict_code",
        }
        if location_keys.intersection(updates.keys()):
            province_code = YuwaOsmService._clean_str(updates.get("province_code")) or getattr(user, "province_code", None)
            province_name = YuwaOsmService._clean_str(updates.get("province")) or getattr(user, "province_name", None)
            district_code = YuwaOsmService._clean_str(updates.get("district_code")) or getattr(user, "district_code", None)
            district_name = YuwaOsmService._clean_str(updates.get("district")) or getattr(user, "district_name", None)
            subdistrict_code = YuwaOsmService._clean_str(updates.get("subdistrict_code")) or getattr(user, "subdistrict_code", None)
            subdistrict_name = YuwaOsmService._clean_str(updates.get("sub_district") or updates.get("subdistrict")) or getattr(user, "subdistrict_name", None)

            province, district, subdistrict = await YuwaOsmService._resolve_geography(
                province_code=province_code,
                province_name=province_name,
                district_code=district_code,
                district_name=district_name,
                subdistrict_code=subdistrict_code,
                subdistrict_name=subdistrict_name,
            )

            update_payload["province_code"] = province.province_code if province else province_code
            update_payload["province_name"] = province.province_name_th if province else province_name
            update_payload["district_code"] = district.district_code if district else district_code
            update_payload["district_name"] = district.district_name_th if district else district_name
            update_payload["subdistrict_code"] = subdistrict.subdistrict_code if subdistrict else subdistrict_code
            update_payload["subdistrict_name"] = subdistrict.subdistrict_name_th if subdistrict else subdistrict_name

            updated_location_context = {
                "province_code": update_payload.get("province_code"),
                "district_code": update_payload.get("district_code"),
                "subdistrict_code": update_payload.get("subdistrict_code"),
            }

        if "profile_image" in updates:
            update_payload["profile_image"] = YuwaOsmService._clean_str(updates.get("profile_image"))

        if "reason" in updates:
            update_payload["registration_reason"] = YuwaOsmService._clean_str(updates.get("reason"))

        if "photo_1inch" in updates:
            update_payload["photo_1inch"] = YuwaOsmService._clean_str(updates.get("photo_1inch"))

        if "attachments" in updates:
            update_payload["attachments"] = updates.get("attachments")

        if "birthday" in updates:
            update_payload["birthday"] = updates.get("birthday")

        if "is_active" in updates:
            update_payload["is_active"] = bool(updates.get("is_active"))

        if not update_payload:
            serialized = YuwaOsmService._serialize_user(user)
            serialized = await YuwaOsmService._attach_actor_metadata(serialized)
            return {
                "success": True,
                "message": "No changes detected",
                "data": serialized,
            }

        updated = await YuwaOSMUserRepository.update_user(user_id, update_payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="yuwa_osm_update_failed")

        refreshed = await YuwaOSMUserRepository.get_user_for_management(user_id)
        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="update",
            target_type="yuwa_osm",
            description=f"Officer updated Yuwa OSM user {user_id}",
            old_data={
                "yuwaUserId": user_id,
                "provinceCode": (existing_location_context or {}).get("province_code") if isinstance(existing_location_context, dict) else getattr(user, "province_code", None),
                "districtCode": (existing_location_context or {}).get("district_code") if isinstance(existing_location_context, dict) else getattr(user, "district_code", None),
                "subdistrictCode": (existing_location_context or {}).get("subdistrict_code") if isinstance(existing_location_context, dict) else getattr(user, "subdistrict_code", None),
            },
            new_data={
                "yuwaUserId": user_id,
                "changes": {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in update_payload.items()},
                "location": updated_location_context,
            },
        )
        await NotificationService.create_notification(
            actor_id=str(current_user.get("user_id")) if current_user else None,
            action_type="update",
            target_type="yuwa_osm",
            target_id=user_id,
            target_name=f"{getattr(refreshed, 'first_name', '')} {getattr(refreshed, 'last_name', '')}".strip(),
            citizen_id=getattr(refreshed, "citizen_id", None),
            province_code=getattr(refreshed, "province_code", None),
            district_code=getattr(refreshed, "district_code", None),
            subdistrict_code=getattr(refreshed, "subdistrict_code", None),
        )

        await cache_delete_pattern("dashboard:*")
        payload = YuwaOsmService._serialize_user(refreshed)
        payload = await YuwaOsmService._attach_actor_metadata(payload)
        return {
            "success": True,
            "message": "Yuwa OSM user updated",
            "data": payload,
        }

    @staticmethod
    async def delete_user(user_id: str, current_user: dict) -> Dict[str, Any]:
        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        YuwaOsmService._ensure_management_scope(viewer_scope)

        user = await YuwaOSMUserRepository.get_user_for_management(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        target_scope, location_context = await OfficerService._resolve_yuwa_management_context(user)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        deleted = await YuwaOSMUserRepository.delete_user(user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delete_failed")

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="delete",
            target_type="yuwa_osm",
            description=f"Officer deleted Yuwa OSM user {user_id}",
            old_data={
                "yuwaUserId": user_id,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
            },
        )
        await NotificationService.create_notification(
            actor_id=str(current_user.get("user_id")),
            action_type="delete",
            target_type="yuwa_osm",
            target_id=user_id,
            target_name=f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip(),
            citizen_id=getattr(user, "citizen_id", None),
            province_code=location_context.get("province_code"),
            district_code=location_context.get("district_code"),
            subdistrict_code=location_context.get("subdistrict_code"),
        )

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(user_id)
        except Exception:
            pass
        return {
            "success": True,
            "message": "Yuwa OSM user deleted",
        }

    @staticmethod
    async def approve_user(user_id: str, payload: YuwaOSMDecisionPayload, current_user: dict) -> Dict[str, Any]:
        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        YuwaOsmService._ensure_management_scope(viewer_scope)

        user = await YuwaOSMUserRepository.get_user_for_management(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        target_scope, location_context = await OfficerService._resolve_yuwa_management_context(user)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True, allow_same_level=True)

        current_status = getattr(user, "approval_status", None)
        if current_status == ApprovalStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already_approved")

        update_payload = {
            "approval_status": ApprovalStatus.APPROVED.value,
            "approved_by": getattr(viewer_profile, "id", None),
            "approved_at": datetime.utcnow(),
            "rejected_by": None,
            "rejected_at": None,
            "rejection_reason": None,
            "is_active": True,
        }

        updated = await YuwaOSMUserRepository.update_user(user_id, update_payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="yuwa_osm_update_failed")

        refreshed = await YuwaOSMUserRepository.get_user_for_management(user_id)
        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="approve",
            target_type="yuwa_osm",
            description=f"Officer approved Yuwa OSM user {user_id}",
            old_data={
                "yuwaUserId": user_id,
                "previousStatus": current_status.value if isinstance(current_status, ApprovalStatus) else current_status,
            },
            new_data={
                "yuwaUserId": user_id,
                "approvalStatus": ApprovalStatus.APPROVED.value,
                "note": getattr(payload, "note", None),
            },
        )
        await NotificationService.create_notification(
            actor_id=str(current_user.get("user_id")),
            action_type="approve",
            target_type="yuwa_osm",
            target_id=user_id,
            target_name=f"{getattr(refreshed, 'first_name', '')} {getattr(refreshed, 'last_name', '')}".strip(),
            citizen_id=getattr(refreshed, "citizen_id", None),
            province_code=location_context.get("province_code"),
            district_code=location_context.get("district_code"),
            subdistrict_code=location_context.get("subdistrict_code"),
        )

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(user_id)
        except Exception:
            pass
        payload = YuwaOsmService._serialize_user(refreshed)
        payload = await YuwaOsmService._attach_actor_metadata(payload)
        return {
            "success": True,
            "message": "Yuwa OSM user approved",
            "data": payload,
        }

    @staticmethod
    async def reject_user(user_id: str, payload: YuwaOSMRejectPayload, current_user: dict) -> Dict[str, Any]:
        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        YuwaOsmService._ensure_management_scope(viewer_scope)

        user = await YuwaOSMUserRepository.get_user_for_management(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        target_scope, location_context = await OfficerService._resolve_yuwa_management_context(user)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        current_status = getattr(user, "approval_status", None)
        if current_status == ApprovalStatus.REJECTED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already_rejected")

        reason = YuwaOsmService._clean_str(payload.reason)
        if not reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rejection_reason_required")

        update_payload = {
            "approval_status": ApprovalStatus.REJECTED.value,
            "approved_by": None,
            "approved_at": None,
            "rejected_by": getattr(viewer_profile, "id", None),
            "rejected_at": datetime.utcnow(),
            "rejection_reason": reason,
            "is_active": False,
        }

        updated = await YuwaOSMUserRepository.update_user(user_id, update_payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="yuwa_osm_update_failed")

        refreshed = await YuwaOSMUserRepository.get_user_for_management(user_id)
        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="reject",
            target_type="yuwa_osm",
            description=f"Officer rejected Yuwa OSM user {user_id}",
            old_data={
                "yuwaUserId": user_id,
                "previousStatus": current_status.value if isinstance(current_status, ApprovalStatus) else current_status,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
            },
            new_data={
                "yuwaUserId": user_id,
                "approvalStatus": ApprovalStatus.REJECTED.value,
                "reason": reason,
                "note": getattr(payload, "note", None),
            },
        )
        await NotificationService.create_notification(
            actor_id=str(current_user.get("user_id")),
            action_type="reject",
            target_type="yuwa_osm",
            target_id=user_id,
            target_name=f"{getattr(refreshed, 'first_name', '')} {getattr(refreshed, 'last_name', '')}".strip(),
            citizen_id=getattr(refreshed, "citizen_id", None),
            province_code=location_context.get("province_code"),
            district_code=location_context.get("district_code"),
            subdistrict_code=location_context.get("subdistrict_code"),
        )

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(user_id)
        except Exception:
            pass
        payload = YuwaOsmService._serialize_user(refreshed)
        payload = await YuwaOsmService._attach_actor_metadata(payload)
        return {
            "success": True,
            "message": "Yuwa OSM user rejected",
            "data": payload,
        }

    @staticmethod
    async def retire_user(user_id: str, payload: YuwaOSMDecisionPayload, current_user: dict) -> Dict[str, Any]:
        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        YuwaOsmService._ensure_management_scope(viewer_scope)

        user = await YuwaOSMUserRepository.get_user_for_management(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")

        target_scope, location_context = await OfficerService._resolve_yuwa_management_context(user)
        OfficerService._ensure_scope_permission(viewer_scope, target_scope, require_strict=True)

        current_status = getattr(user, "approval_status", None)
        if current_status == ApprovalStatus.RETIRED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already_retired")

        update_payload = {
            "approval_status": ApprovalStatus.RETIRED.value,
            "approved_by": None,
            "approved_at": None,
            "rejected_by": None,
            "rejected_at": None,
            "rejection_reason": None,
            "is_active": False,
        }

        updated = await YuwaOSMUserRepository.update_user(user_id, update_payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="yuwa_osm_update_failed")

        refreshed = await YuwaOSMUserRepository.get_user_for_management(user_id)
        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="retire",
            target_type="yuwa_osm",
            description=f"Officer retired Yuwa OSM user {user_id}",
            old_data={
                "yuwaUserId": user_id,
                "previousStatus": current_status.value if isinstance(current_status, ApprovalStatus) else current_status,
                "provinceCode": location_context.get("province_code"),
                "districtCode": location_context.get("district_code"),
                "subdistrictCode": location_context.get("subdistrict_code"),
            },
            new_data={
                "yuwaUserId": user_id,
                "approvalStatus": ApprovalStatus.RETIRED.value,
                "note": getattr(payload, "note", None),
            },
        )
        await NotificationService.create_notification(
            actor_id=str(current_user.get("user_id")),
            action_type="retire",
            target_type="yuwa_osm",
            target_id=user_id,
            target_name=f"{getattr(refreshed, 'first_name', '')} {getattr(refreshed, 'last_name', '')}".strip(),
            citizen_id=getattr(refreshed, "citizen_id", None),
            province_code=location_context.get("province_code"),
            district_code=location_context.get("district_code"),
            subdistrict_code=location_context.get("subdistrict_code"),
        )

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(user_id)
        except Exception:
            pass
        payload = YuwaOsmService._serialize_user(refreshed)
        payload = await YuwaOsmService._attach_actor_metadata(payload)
        return {
            "success": True,
            "message": "Yuwa OSM user retired",
            "data": payload,
        }

    @staticmethod
    async def transfer_from_people(people_id: str, current_user: dict, note: str | None = None) -> Dict[str, Any]:
        viewer_profile, viewer_scope = await OfficerService._resolve_officer_scope(current_user, require_active=True)
        YuwaOsmService._ensure_management_scope(viewer_scope)

        people = await PeopleUserRepository.get_user_for_management(people_id)
        if not people:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="people_user_not_found")

        if getattr(people, "is_transferred", False):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="people_already_transferred")

        if await YuwaOSMUserRepository.exists_by_citizen_id(getattr(people, "citizen_id", None)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="citizen_id_already_in_yuwa_osm")

        yuwa_osm_code = getattr(people, "yuwa_osm_code", None)
        if not yuwa_osm_code:
            yuwa_osm_code = await PeopleService._generate_yuwa_osm_code()
            people.yuwa_osm_code = yuwa_osm_code
        if yuwa_osm_code and await YuwaOSMUserRepository.exists_by_yuwa_osm_code(yuwa_osm_code):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="yuwa_osm_code_exists")

        now = datetime.utcnow()
        create_payload: Dict[str, Any] = {
            "citizen_id": people.citizen_id,
            "prefix": getattr(people, "prefix", None),
            "first_name": people.first_name,
            "last_name": people.last_name,
            "gender": getattr(people, "gender", None),
            "phone_number": getattr(people, "phone_number", None),
            "email": getattr(people, "email", None),
            "line_id": getattr(people, "line_id", None),
            "school": getattr(people, "school", None),
            "organization": getattr(people, "organization", None),
            "province_code": getattr(people, "province_code", None),
            "province_name": getattr(people, "province_name", None),
            "district_code": getattr(people, "district_code", None),
            "district_name": getattr(people, "district_name", None),
            "subdistrict_code": getattr(people, "subdistrict_code", None),
            "subdistrict_name": getattr(people, "subdistrict_name", None),
            "profile_image": getattr(people, "profile_image", None),
            "registration_reason": getattr(people, "registration_reason", None),
            "photo_1inch": getattr(people, "photo_1inch", None),
            "attachments": getattr(people, "attachments", None),
            "birthday": getattr(people, "birthday", None),
            "password_hash": getattr(people, "password_hash", None),
            "yuwa_osm_code": yuwa_osm_code,
            "is_active": True,
            "is_first_login": False,
            "approval_status": ApprovalStatus.APPROVED.value,
            "source_people_id": people.id,
            "transferred_by": current_user.get("user_id"),
            "transferred_at": now,
        }

        create_payload = {k: v for k, v in create_payload.items() if v is not None}

        async with in_transaction():
            user = await YuwaOSMUserRepository.create_user(create_payload)

            people.is_transferred = True
            people.transferred_at = now
            people.transferred_by = current_user.get("user_id")
            people.yuwa_osm_id = user.id
            people.is_active = False
            people.updated_at = now
            await people.save()

        await AuditService.log_action(
            user_id=current_user.get("user_id"),
            action_type="transfer",
            target_type="yuwa_osm",
            description=f"Transferred People user {people_id} to Yuwa OSM",
            old_data={"people_id": people_id},
            new_data={
                "yuwa_osm_id": str(user.id),
                "yuwa_osm_code": yuwa_osm_code,
                "note": note,
            },
        )
        await NotificationService.create_notification(
            actor_id=str(current_user.get("user_id")),
            action_type="create",
            target_type="yuwa_osm",
            target_id=str(user.id),
            target_name=f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip(),
            citizen_id=getattr(user, "citizen_id", None),
            province_code=getattr(user, "province_code", None),
            district_code=getattr(user, "district_code", None),
            subdistrict_code=getattr(user, "subdistrict_code", None),
        )

        await cache_delete_pattern("dashboard:*")
        try:
            await invalidate_user_sessions(people_id)
        except Exception:
            pass
        payload = YuwaOsmService._serialize_user(user)
        payload = await YuwaOsmService._attach_actor_metadata(payload)
        return {
            "success": True,
            "message": "People user transferred to Yuwa OSM",
            "data": payload,
        }

    @staticmethod
    def _clean_str(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _normalize_gender(gender: Optional[str]) -> Optional[str]:
        cleaned = YuwaOsmService._clean_str(gender)
        if not cleaned:
            return None
        normalized = cleaned.lower()
        if normalized in {"male", "female", "other"}:
            return normalized
        return cleaned

    @staticmethod
    async def _resolve_prefix(prefix_value: Optional[str]) -> Optional[str]:
        if prefix_value is None:
            return None
        normalized = prefix_value.strip()
        if not normalized:
            return None

        prefix_record = None
        try:
            prefix_record = await Prefix.get(id=UUID(normalized))
        except (ValueError, DoesNotExist):
            prefix_record = None

        if not prefix_record:
            prefix_record = await Prefix.filter(prefix_name_th__iexact=normalized).first()

        if not prefix_record:
            prefix_record = await Prefix.filter(prefix_name_en__iexact=normalized).first()

        if not prefix_record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_prefix")

        return prefix_record.prefix_name_th

    @staticmethod
    async def _resolve_geography(
        *,
        province_code: Optional[str],
        province_name: Optional[str],
        district_code: Optional[str],
        district_name: Optional[str],
        subdistrict_code: Optional[str],
        subdistrict_name: Optional[str],
        province_required: bool = False,
        district_required: bool = False,
        subdistrict_required: bool = False,
    ) -> Tuple[Optional[Province], Optional[District], Optional[Subdistrict]]:
        province = await YuwaOsmService._resolve_province(
            province_code,
            province_name,
            required=province_required,
        )
        district, province = await YuwaOsmService._resolve_district(
            district_code,
            district_name,
            province,
            required=district_required,
        )
        subdistrict, district = await YuwaOsmService._resolve_subdistrict(
            subdistrict_code,
            subdistrict_name,
            district,
            required=subdistrict_required,
        )
        return province, district, subdistrict

    @staticmethod
    async def _resolve_province(
        code: Optional[str],
        name: Optional[str],
        *,
        required: bool = False,
    ) -> Optional[Province]:
        candidate_code = code.strip() if code else None
        candidate_name = name.strip() if name else None

        if not candidate_code and not candidate_name:
            if required:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="province_required")
            return None

        province = None
        if candidate_code:
            province = await Province.filter(province_code=candidate_code).first()

        if not province and candidate_name:
            province = await Province.filter(province_name_th__iexact=candidate_name).first()
            if not province:
                province = await Province.filter(province_name_en__iexact=candidate_name).first()

        if not province:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_province")

        return province

    @staticmethod
    async def _resolve_district(
        code: Optional[str],
        name: Optional[str],
        province: Optional[Province],
        *,
        required: bool = False,
    ) -> Tuple[Optional[District], Optional[Province]]:
        candidate_code = code.strip() if code else None
        candidate_name = name.strip() if name else None

        if not candidate_code and not candidate_name:
            if required:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="district_required")
            return None, province

        district = None
        if candidate_code:
            district = await District.filter(district_code=candidate_code).first()

        if not district and candidate_name:
            filters: Dict[str, Any] = {}
            if province:
                filters["province_id"] = province.province_code
            district = await District.filter(**filters, district_name_th__iexact=candidate_name).first()
            if not district:
                district = await District.filter(**filters, district_name_en__iexact=candidate_name).first()

        if not district:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_district")

        if province and district.province_id != province.province_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="district_not_in_province")

        if not province:
            await district.fetch_related("province")
            province = district.province

        return district, province

    @staticmethod
    async def _resolve_subdistrict(
        code: Optional[str],
        name: Optional[str],
        district: Optional[District],
        *,
        required: bool = False,
    ) -> Tuple[Optional[Subdistrict], Optional[District]]:
        candidate_code = code.strip() if code else None
        candidate_name = name.strip() if name else None

        if not candidate_code and not candidate_name:
            if required:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subdistrict_required")
            return None, district

        subdistrict = None
        if candidate_code:
            subdistrict = await Subdistrict.filter(subdistrict_code=candidate_code).first()

        if not subdistrict and candidate_name:
            filters: Dict[str, Any] = {}
            if district:
                filters["district_id"] = district.district_code
            subdistrict = await Subdistrict.filter(**filters, subdistrict_name_th__iexact=candidate_name).first()
            if not subdistrict:
                subdistrict = await Subdistrict.filter(**filters, subdistrict_name_en__iexact=candidate_name).first()

        if not subdistrict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_subdistrict")

        await subdistrict.fetch_related("district")
        actual_district = subdistrict.district

        if district and actual_district and actual_district.district_code != district.district_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subdistrict_not_in_district")

        if not district:
            district = actual_district

        return subdistrict, district

    @staticmethod
    async def get_yuwa_osm_by_ids(user_ids: List[str], current_user: dict):
        """Batch fetch Yuwa OSM users by IDs (UUID or yuwa_osm_code)."""
        if not user_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids_required")

        unique_ids = list(dict.fromkeys(user_ids))
        items: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        for user_id in unique_ids:
            try:
                result = await YuwaOsmService.get_user(user_id, current_user)
                items.append(result.get("data"))
            except HTTPException as exc:
                errors.append({"id": user_id, "error": str(exc.detail)})

        return {
            "status": "success",
            "data": items,
            "errors": errors,
            "message": "ดึงข้อมูล Yuwa OSM Users สำเร็จ",
        }
