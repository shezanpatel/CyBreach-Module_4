"""Structured logging configuration for the application."""

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def setup_logging(level: LogLevel = "INFO") -> logging.Logger:
    """
    Configure application-wide logging with a consistent format.

    Args:
        level: Minimum log level to emit.

    Returns:
        Configured root application logger.
    """
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("redis_leaderboard")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the application namespace."""
    return logging.getLogger(f"redis_leaderboard.{name}")
