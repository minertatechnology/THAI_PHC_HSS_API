"""Self-service account deletion (App Store Review Guideline 5.1.1(v)).

Gen H and Yuwa OSM users may delete their own account from the mobile app.
Other user types (osm / officer / people) are managed by officials and are not
self-deletable here.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.api.middleware.middleware import invalidate_user_sessions
from app.cache.redis_client import cache_delete, cache_delete_pattern
from app.models.auth_model import OAuthAuthorizationCode, OAuthConsent, RefreshToken
from app.repositories.gen_h_user_repository import GenHUserRepository
from app.repositories.yuwa_osm_user_repository import YuwaOSMUserRepository
from app.services.audit_service import AuditService
from app.utils.logging_utils import get_logger, log_error
from app.utils.user_identity import encode_user_id_for_oauth

logger = get_logger(__name__)

SELF_DELETABLE_USER_TYPES = {"gen_h", "yuwa_osm"}


def _remove_file(path: Optional[str]) -> None:
    """Best-effort removal of an uploaded file referenced by a stored path/URL."""
    if not path:
        return
    try:
        p = Path(str(path).replace("\\", "/").lstrip("/"))
        if p.exists() and p.is_file():
            p.unlink()
    except Exception as exc:  # never fail deletion because of a file
        log_error(logger, f"account deletion: failed to remove file {path}", exc=exc)


class AccountDeletionService:
    @staticmethod
    async def delete_my_account(
        current_user: dict,
        *,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_id = str(current_user.get("user_id") or "")
        user_type = str(current_user.get("user_type") or "")
        client_id = current_user.get("client_id")

        if not user_id or not user_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_context_missing")
        if user_type not in SELF_DELETABLE_USER_TYPES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="self_delete_not_supported_for_user_type",
            )

        # ── 1) Load + delete the profile row (credentials live on the same row) ──
        summary: Dict[str, Any] = {"user_id": user_id, "user_type": user_type}

        if user_type == "gen_h":
            user = await GenHUserRepository.get_by_id(user_id)  # type: ignore[arg-type]
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="gen_h_user_not_found")
            summary["citizen_id"] = getattr(user, "citizen_id", None)
            summary["gen_h_code"] = getattr(user, "gen_h_code", None)
            for attr in ("profile_image_url", "photo_1inch", "member_card_url"):
                await asyncio.to_thread(_remove_file, getattr(user, attr, None))
            await GenHUserRepository.delete_user(user)
        else:  # yuwa_osm
            user = await YuwaOSMUserRepository.get_user_for_management(user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="yuwa_osm_user_not_found")
            summary["citizen_id"] = getattr(user, "citizen_id", None)
            summary["yuwa_osm_code"] = getattr(user, "yuwa_osm_code", None)
            await asyncio.to_thread(_remove_file, getattr(user, "profile_image", None))
            deleted = await YuwaOSMUserRepository.delete_user(user_id)
            if not deleted:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delete_failed")

        # ── 2) Revoke every session/token for this identity ──
        stored_uid = encode_user_id_for_oauth(user_id, user_type)
        try:
            await RefreshToken.filter(user_id=stored_uid).update(is_revoked=True)
            await OAuthAuthorizationCode.filter(user_id=stored_uid).delete()
            await OAuthConsent.filter(user_id=stored_uid).delete()
        except Exception as exc:
            log_error(logger, "account deletion: token cleanup failed", exc=exc)

        # ── 3) Drop caches so the token stops working immediately ──
        try:
            await invalidate_user_sessions(user_id)
            await cache_delete(f"cid:{user_type}:{user_id}")
            if client_id:
                await cache_delete(f"session:{user_id}:{client_id}:{user_type}")
            await cache_delete_pattern("dashboard:*")
        except Exception as exc:
            log_error(logger, "account deletion: cache invalidation failed", exc=exc)

        # ── 4) Audit trail (no PII beyond what is needed to prove the request) ──
        try:
            await AuditService.log_action(
                user_id=user_id,
                action_type="delete",
                target_type=user_type,
                description=f"User self-deleted account ({user_type} {user_id})",
                old_data={k: v for k, v in summary.items() if k != "citizen_id"},
                ip=ip,
                user_agent=user_agent,
            )
        except Exception as exc:
            log_error(logger, "account deletion: audit log failed", exc=exc)

        return {"success": True, "message": "account_deleted", "user_type": user_type}
