from __future__ import annotations

import functools
import inspect
import logging
import os
from typing import Any, Callable, Optional


def configure_logging(level: Optional[str] = None, pretty: Optional[bool] = None) -> None:
    """Configure the root logger once, idempotently.

    - level: e.g. "DEBUG", "INFO", "WARNING"; defaults to env LOG_LEVEL or INFO
    - pretty: multi-line human-friendly format when True; defaults to env LOG_PRETTY
    """
    level_str = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    level_val = getattr(logging, level_str, logging.INFO)

    if pretty is None:
        pretty = os.getenv("LOG_PRETTY", "0").lower() in {"1", "true", "yes", "on"}

    fmt = (
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
        if not pretty
        else (
            "%(asctime)s %(levelname)s %(name)s\n"
            "  %(message)s"
        )
    )

    root = logging.getLogger()
    root.setLevel(level_val)

    # Reuse or create a single StreamHandler
    stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
    if stream_handlers:
        handler = stream_handlers[0]
        handler.setLevel(level_val)
        handler.setFormatter(logging.Formatter(fmt))
        return

    handler = logging.StreamHandler()
    handler.setLevel(level_val)
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)

    # Nothing else to configure


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module/application logger. Ensures base config exists."""
    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name if name else __name__)


def log_error(logger: logging.Logger, message: str, exc: Optional[BaseException] = None, **context: Any) -> None:
    """Unified error logging helper.

    Usage:
        log_error(logger, "create_user failed", exc=e, user_id=user_id)
    """
    if context:
        message = f"{message} | " + " ".join(f"{k}={v}" for k, v in context.items())
    if exc is not None:
        logger.exception(message)
    else:
        logger.error(message)


def log_exceptions(logger_name: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to log exceptions for both sync/async functions, then re-raise.

    Example:
        @log_exceptions("service.user")
        async def handle(...):
            ...
    """

    logger = get_logger(logger_name)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    logger.exception("uncaught exception in %s", func.__name__)
                    raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any):
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.exception("uncaught exception in %s", func.__name__)
                raise

        return sync_wrapper

    return decorator

def log_info(logger: logging.Logger, message: str, **context: Any) -> None:
    """Unified info logging helper.

    Usage:
        log_info(logger, "create_user success", user_id=user_id)
    """
    if context:
        message = f"{message} | " + " ".join(f"{k}={v}" for k, v in context.items())
    logger.info(message)


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    client_ip: Optional[str] | None = None,
    user_agent: Optional[str] | None = None,
    **context: Any,
) -> None:
    """Compact, readable request log line with optional context.

    Example usage:
        log_request(logger, request.method, request.url.path, response.status_code, duration_ms,
                    client_ip=getattr(request.client, "host", None),
                    user_agent=request.headers.get("user-agent"))
    """
    parts = [
        method,
        path,
        str(status_code),
        f"{duration_ms}ms",
    ]
    if client_ip:
        parts.append(f"ip={client_ip}")
    if user_agent:
        parts.append(f"ua={user_agent}")
    if context:
        parts.append("| " + " ".join(f"{k}={v}" for k, v in context.items()))
    logger.info(" ".join(parts))
