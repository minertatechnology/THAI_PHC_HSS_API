from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from app.configs.config import settings

_MODEL_MODULES: list[str] = [
    "app.models.officer_model",
    "app.models.osm_model",
    "app.models.yuwa_osm_model",
    "app.models.people_model",
    "app.models.auth_model",
    "app.models.geography_model",
    "app.models.health_model",
    "app.models.award_training_model",
    "app.models.dashboard_model",
    "app.models.personal_model",
    "app.models.administration_model",
    "app.models.position_model",
    "app.models.phc_permission_model",
    "app.models.report_model",
    "app.models.audit_model",
    "app.models.news_model",
    "app.models.mobile_menu_model",
    "app.models.mobile_banner_model",
    "app.models.notification_model",
    "app.models.gen_h_model",
    "aerich.models",
]


def _build_postgres_credentials(parsed) -> dict[str, object]:
    database_name = (parsed.path or "/").lstrip("/")
    return {
        "engine": "tortoise.backends.asyncpg",
        "credentials": {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username,
            "password": parsed.password,
            "database": database_name,
            "min_size": int(os.getenv("DB_POOL_MIN", "5")),
            "max_size": int(os.getenv("DB_POOL_MAX", "20")),
            "statement_cache_size": 0,
        },
    }


def _build_sqlite_credentials(parsed) -> dict[str, object]:
    raw_path = parsed.path or ""
    if parsed.netloc and parsed.netloc != "":
        raw_path = f"{parsed.netloc}{raw_path}"
    file_path = raw_path.lstrip("/") or ":memory:"
    resolved_path = file_path
    if file_path not in {":memory:", "memory"}:
        resolved_path = str(Path(file_path).expanduser())
    return {
        "engine": "tortoise.backends.sqlite",
        "credentials": {
            "file_path": resolved_path,
        },
    }


def get_tortoise_config() -> dict[str, object]:
    database_url = os.getenv("DATABASE_URL", settings.POSTGRES_DATABASE_URL)
    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "postgres").lower()

    if scheme in {"sqlite", "sqlite3"}:
        connection = _build_sqlite_credentials(parsed)
    else:
        connection = _build_postgres_credentials(parsed)

    return {
        "connections": {
            "default": connection,
        },
        "apps": {
            "models": {
                "models": _MODEL_MODULES,
                "default_connection": "default",
            },
        },
    }


TORTOISE_ORM = get_tortoise_config()