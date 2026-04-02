"""Async database helpers backed by Tortoise ORM.

Historically this module exposed SQLAlchemy session utilities.  During the
migration to Tortoise those helpers became no-ops.  The new implementation
provides high-level helpers that the rest of the codebase (and external
scripts) can use without caring about the underlying ORM.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from tortoise import Tortoise

from app.db.tortoise_config import get_tortoise_config

__all__ = ["init_db", "close_db", "db_lifespan"]


async def init_db(config: dict | None = None, *, generate_schema: bool = False) -> None:
    """Initialise Tortoise ORM using the project configuration.

    Parameters
    ----------
    config:
        Optional custom configuration.  When omitted the standard project
        configuration returned by :func:`get_tortoise_config` is used.
    generate_schema:
        When ``True`` the database schema will be generated after initialising
        the connection.  This mirrors the behaviour that scripts relied on
        when using the old SQLAlchemy helpers.
    """

    await Tortoise.init(config=config or get_tortoise_config())
    if generate_schema:
        await Tortoise.generate_schemas()


async def close_db() -> None:
    """Close all Tortoise ORM connections."""

    await Tortoise.close_connections()


@asynccontextmanager
async def db_lifespan(config: dict | None = None, *, generate_schema: bool = False) -> AsyncIterator[None]:
    """Async context manager that initialises and tears down the ORM."""

    await init_db(config=config, generate_schema=generate_schema)
    try:
        yield
    finally:
        await close_db()
