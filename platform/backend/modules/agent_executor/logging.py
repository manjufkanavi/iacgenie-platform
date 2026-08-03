"""Logging configuration for Agent Executor."""

import logging

import sys

from typing import Any, Optional

from .config import config


def setup_logging() -> Any:
    """Set up logging configuration for the application."""
    # Get log level from config or default to INFO
    log_level = getattr(config, "LOG_LEVEL", "INFO")
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=config.LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Create logger for this module
    logger = logging.getLogger(__name__)
    return logger


# Create a global logger instance


logger = setup_logging()


def log_info(message: str, extra: Optional[dict] = None) -> None:
    """Log an info message with optional extra context."""
    logger.info(message, extra=extra or {})


def log_debug(message: str, extra: Optional[dict] = None) -> None:
    """Log a debug message with optional extra context."""
    logger.debug(message, extra=extra or {})


def log_error(message: str, extra: Optional[dict] = None) -> None:
    """Log an error message with optional extra context."""
    logger.error(message, extra=extra or {})


def log_warning(message: str, extra: Optional[dict] = None) -> None:
    """Log a warning message with optional extra context."""
    logger.warning(message, extra=extra or {})


def log_critical(message: str, extra: Optional[dict] = None) -> None:
    """Log a critical message with optional extra context."""
    logger.critical(message, extra=extra or {})


__all__ = [
    "setup_logging",
    "logger",
    "log_info",
    "log_debug",
    "log_error",
    "log_warning",
    "log_critical",
]
