"""Structured logging helpers (structlog)."""

import logging
import sys
from typing import Any, Optional

import structlog

from app.core.settings import settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(
    name: str,
    *,
    tenant_id: Optional[str] = None,
    event_type: Optional[str] = None,
    correlation_id: Optional[str] = None,
    **extra: Any,
) -> structlog.stdlib.BoundLogger:
    configure_logging()
    logger = structlog.get_logger(name)
    bindings: dict[str, Any] = {}
    if tenant_id:
        bindings["tenant_id"] = tenant_id
    if event_type:
        bindings["event_type"] = event_type
    if correlation_id:
        bindings["correlation_id"] = correlation_id
    bindings.update(extra)
    if bindings:
        return logger.bind(**bindings)
    return logger
