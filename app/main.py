from contextlib import asynccontextmanager
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from tortoise.contrib.fastapi import register_tortoise

from app.configs.config import settings
from app.router.root import rootRouter
from app.api.v1.routers.thaid_route import callback_router as thaid_callback_router
from app.db.tortoise_config import get_tortoise_config
from app.utils.logging_utils import configure_logging, get_logger, log_request

# =========================
# Logging
# =========================
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    # Initialize Redis cache
    from app.cache.redis_client import init_redis, close_redis
    await init_redis()
    try:
        yield
    finally:
        await close_redis()
        logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)


# =========================
# CORS
# =========================
def _resolve_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", settings.CORS_ALLOWED_ORIGINS)
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return origins


ALLOWED_ORIGINS = _resolve_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Static files: /uploads/**
# =========================
def _resolve_uploads_root() -> Path:
    configured = Path(os.getenv("STATIC_UPLOADS_ROOT", "/app/uploads")).resolve()
    if configured.exists():
        logger.info("Serving uploads from: %s", configured)
        return configured

    repo_uploads = Path(__file__).resolve().parents[1] / "uploads"
    repo_uploads.mkdir(parents=True, exist_ok=True)
    logger.warning(
        "STATIC_UPLOADS_ROOT does not exist: %s. Falling back to %s",
        configured,
        repo_uploads,
    )
    return repo_uploads


UPLOADS_ROOT = _resolve_uploads_root()

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_ROOT)),
    name="uploads",
)


def _json_safe(value):
    """Convert nested structures to JSON-friendly primitives."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return f"<binary:{len(value)} bytes>"
    if isinstance(value, dict):
        return {key: _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    detail = _json_safe(exc.errors())
    body = _json_safe(getattr(exc, "body", None))
    return JSONResponse(status_code=422, content={"detail": detail, "body": body})


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    detail = _json_safe(exc.errors())
    return JSONResponse(status_code=422, content={"detail": detail})

# =========================
# Routers
# =========================
app.include_router(rootRouter)
# ThaiD DOPA callback at root level: GET /callback
app.include_router(thaid_callback_router)


# =========================
# Request logging middleware
# =========================
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        if logger.isEnabledFor(logging.INFO):
            threshold_ms = int(os.getenv("REQ_LOG_THRESHOLD_MS", "0"))
            if (
                duration_ms >= threshold_ms
                and os.getenv("LOG_REQUESTS", "1").lower() in {"1", "true", "yes", "on"}
            ):
                log_request(
                    logger,
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                    client_ip=getattr(request.client, "host", None),
                    user_agent=request.headers.get("user-agent"),
                )
        return response
    except Exception:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.exception(
            "Unhandled exception for %s %s after %dms",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise


# =========================
# Tortoise ORM
# =========================
register_tortoise(
    app,
    config=get_tortoise_config(),
    generate_schemas=False,
    add_exception_handlers=True,
)