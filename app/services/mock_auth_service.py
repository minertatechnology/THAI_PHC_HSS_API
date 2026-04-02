from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, status

from app.configs.config import settings
from app.services.mock_data_store import MockDataStore


class MockAuthService:
    """Lightweight token service used by the mock API layer."""

    _secret_key: str = getattr(settings, "JWT_SECRET_KEY", "mock-secret") or "mock-secret"
    _algorithm: str = "HS256"
    _access_minutes: int = 60
    _refresh_days: int = 7
    _refresh_tokens: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def login(cls, username: str, password: str) -> Dict[str, Any]:
        MockDataStore.ensure_initialized()
        user = MockDataStore.find_user_by_username(username)
        if not user or user.get("password") != password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
        access_token = cls._generate_token(user, token_type="access")
        refresh_token = cls._generate_token(user, token_type="refresh")
        cls._refresh_tokens[refresh_token] = {
            "user_id": user["id"],
            "expires_at": cls._now() + timedelta(days=cls._refresh_days),
        }
        profile = {
            "id": user["id"],
            "username": user["username"],
            "firstName": user.get("firstName"),
            "lastName": user.get("lastName"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "groupName": user.get("groupName"),
            "status": user.get("status"),
        }
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": cls._access_minutes * 60,
            "scope": "profile",
            "profile": profile,
        }

    @classmethod
    def refresh(cls, refresh_token: str) -> Dict[str, Any]:
        MockDataStore.ensure_initialized()
        stored = cls._refresh_tokens.get(refresh_token)
        if not stored:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")
        if stored["expires_at"] < cls._now():
            cls._refresh_tokens.pop(refresh_token, None)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh_token_expired")
        user = MockDataStore.find_user_by_id(stored["user_id"])
        if not user:
            cls._refresh_tokens.pop(refresh_token, None)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
        cls._refresh_tokens.pop(refresh_token, None)
        new_access = cls._generate_token(user, token_type="access")
        new_refresh = cls._generate_token(user, token_type="refresh")
        cls._refresh_tokens[new_refresh] = {
            "user_id": user["id"],
            "expires_at": cls._now() + timedelta(days=cls._refresh_days),
        }
        return {
            "success": True,
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "Bearer",
            "expires_in": cls._access_minutes * 60,
            "scope": "profile",
            "profile": {
                "id": user["id"],
                "username": user["username"],
                "firstName": user.get("firstName"),
                "lastName": user.get("lastName"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "groupName": user.get("groupName"),
                "status": user.get("status"),
            },
        }

    @classmethod
    def logout(cls, user_id: str) -> Dict[str, Any]:
        MockDataStore.ensure_initialized()
        cls._refresh_tokens = {token: meta for token, meta in cls._refresh_tokens.items() if meta["user_id"] != user_id}
        return {"success": True, "message": "logged_out"}

    @classmethod
    def decode_access_token(cls, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, cls._secret_key, algorithms=[cls._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired") from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_type")
        user = MockDataStore.find_user_by_id(payload.get("sub"))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
        return {
            "user": {
                "id": user["id"],
                "username": user["username"],
                "firstName": user.get("firstName"),
                "lastName": user.get("lastName"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "groupName": user.get("groupName"),
                "status": user.get("status"),
            },
            "scopes": payload.get("scopes", []),
        }

    @classmethod
    def _generate_token(cls, user: Dict[str, Any], token_type: str) -> str:
        now = cls._now()
        if token_type == "access":
            exp = now + timedelta(minutes=cls._access_minutes)
        else:
            exp = now + timedelta(days=cls._refresh_days)
        payload = {
            "sub": user["id"],
            "username": user["username"],
            "type": token_type,
            "scopes": user.get("scopes", ["profile"]),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        return jwt.encode(payload, cls._secret_key, algorithm=cls._algorithm)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


MockDataStore.ensure_initialized()
