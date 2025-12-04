"""Structured logging configuration for Babble Buddy."""

import logging
import sys
from typing import Any

from app.config import settings


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("babble_buddy")

    # Set level based on environment
    level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler with structured format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Format: timestamp - level - module - message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Singleton logger instance
logger = setup_logging()


def log_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Log HTTP request details."""
    logger.info(
        "HTTP %s %s - %d (%.2fms)",
        method,
        path,
        status_code,
        duration_ms,
    )


def log_chat(session_id: str, message_len: int, provider: str) -> None:
    """Log chat interaction."""
    logger.info(
        "Chat session=%s message_len=%d provider=%s",
        session_id[:8] if session_id else "new",
        message_len,
        provider,
    )


def log_provider_error(provider: str, error: Exception) -> None:
    """Log provider errors."""
    logger.error(
        "Provider error provider=%s error=%s",
        provider,
        str(error),
    )


def log_auth(token_id: str | None, success: bool, reason: str = "") -> None:
    """Log authentication attempts."""
    if success:
        logger.debug("Auth success token_id=%s", token_id[:8] if token_id else "none")
    else:
        logger.warning("Auth failed reason=%s", reason)


def log_startup(info: dict[str, Any]) -> None:
    """Log application startup information."""
    logger.info("Starting Babble Buddy Agent Core")
    for key, value in info.items():
        logger.info("  %s: %s", key, value)
