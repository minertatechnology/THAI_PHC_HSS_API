from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import Request

from app.configs.config import settings
from app.models.thaid_models import FormatResponseModel


RESPONSE_CODE_MESSAGES: dict[str, str] = {
    "0000": "GET_DATA_SUCCESSFULLY",
    "0001": "CREATE_DATA_SUCCESSFULLY",
    "4010": "UNAUTHORIZED",
    "5000": "INTERNAL_SERVER_ERROR",
    "5001": "THAID_NOT_CONFIGURED",
    "5002": "THAID_DEPENDENCY_MISSING",
}

def format_response(res_code: str, res_data: Any) -> FormatResponseModel:
    return FormatResponseModel(
        res_code=res_code,
        res_message=RESPONSE_CODE_MESSAGES.get(res_code, ""),
        res_data=res_data,
    )


def mask_secret(value: Optional[str], visible: int = 3) -> Optional[str]:
    if not value:
        return value
    prefix = value[:visible]
    return f"{prefix}{'*' * max(len(value) - visible, 0)}"


def mask_pid(pid: Optional[str]) -> Optional[str]:
    if not pid:
        return pid
    return f"{'*' * max(len(pid) - 4, 0)}{pid[-4:]}"


def mask_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    return f"{value[0]}***" if len(value) > 1 else value


def sanitize_thaid_for_log(thaid_data: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in thaid_data.items():
        if key in {"access_token", "refresh_token", "id_token"}:
            sanitized[key] = mask_secret(value)
        elif key == "pid":
            sanitized[key] = mask_pid(value)
        elif key in {"family_name", "given_name", "title", "titleTh"}:
            sanitized[key] = mask_name(value)
        elif key in {"address", "address_other"}:
            sanitized[key] = {"formatted": "***masked***"} if value else None
        else:
            sanitized[key] = value
    return sanitized


def get_thaid_logger() -> logging.Logger:
    logger = logging.getLogger("thaid")
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
        logger.propagate = False
    level_name = settings.ENVIRONMENT.lower()
    logger.setLevel(logging.DEBUG if level_name == "development" else logging.INFO)
    return logger


def extract_request_metadata(request: Request) -> dict[str, Any]:
    forwarded_for = request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("X-Real-IP")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else None
    if not client_ip:
        client_ip = real_ip
    if not client_ip:
        client_ip = getattr(request.client, "host", None)
    return {
        "ip": client_ip,
        "user_agent": request.headers.get("User-Agent"),
    }
