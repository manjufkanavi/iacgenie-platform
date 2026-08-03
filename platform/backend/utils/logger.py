"""Structured logging utilities for pipeline execution."""

import logging

import threading

from contextlib import contextmanager

from typing import Optional, Dict, Any, Generator

_ctx_local = threading.local()


def get_pipeline_logger(name: str = "pipeline") -> logging.Logger:
    """Return a logger pre-configured with pipeline context fields."""
    return logging.getLogger(name)


def setup_structured_logging(environment: str = "development") -> None:
    """Configure the root logger with structured JSON output."""
    import logging.config

    log_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": PipelineLogFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }
    if environment == "development":
        log_config["handlers"]["console"]["level"] = "DEBUG"
    else:
        log_config["handlers"]["console"]["level"] = "INFO"
    logging.config.dictConfig(log_config)


class PipelineLogFormatter(logging.Formatter):
    """Formats log records with structured key=value pairs including pipeline context."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        session_id = getattr(_ctx_local, "session_id", None)
        if session_id:
            log_data["session_id"] = session_id
        phase = getattr(_ctx_local, "phase", None)
        if phase:
            log_data["phase"] = phase
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        return _to_json(log_data)


@contextmanager
def pipeline_log_context(
    session_id: str, phase: Optional[str] = None
) -> Generator[None, None, None]:
    """Context manager that adds pipeline context to all log calls in a block."""
    _ctx_local.session_id = session_id
    _ctx_local.phase = phase
    try:
        yield
    finally:
        _ctx_local.session_id = None
        _ctx_local.phase = None


def _to_json(data: Dict[str, Any]) -> str:
    import json

    return json.dumps(data, default=str)
