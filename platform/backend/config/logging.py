"""

Structured Logging Configuration

Provides centralized logging with correlation IDs and structured output

"""

import sys

import logging

from typing import Dict, Any, Optional

import os

from dotenv import load_dotenv

load_dotenv()

# Environment configuration

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

SENTRY_DSN = os.getenv("SENTRY_DSN")


def configure_logging() -> None:
    """Configure logging for the application - using standard library logging to avoid structlog issues"""
    # Use simple dictConfig for structured logging
    import logging.config

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] %(message)s",
            },
        },
        "handlers": {
            "default": {
                "level": LOG_LEVEL.upper(),
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["default"],
                "level": LOG_LEVEL.upper(),
                "propagate": True,
            },
        },
    }
    logging.config.dictConfig(logging_config)
    # Set specific logger levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    # Configure Sentry if DSN is provided and valid (not a placeholder)
    # Disable Sentry to avoid structlog compatibility issues
    SENTRY_ENABLED = os.getenv("SENTRY_ENABLED", "false").lower() == "true"
    if (
        SENTRY_ENABLED
        and SENTRY_DSN
        and SENTRY_DSN.strip()
        and SENTRY_DSN != "your_sentry_dsn_here"
    ):
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_logging = LoggingIntegration(
                level=logging.INFO, event_level=logging.ERROR
            )
            sentry_sdk.init(
                dsn=SENTRY_DSN,
                integrations=[
                    FastApiIntegration(),
                    sentry_logging,
                ],
                environment=ENVIRONMENT,
                traces_sample_rate=0.1 if ENVIRONMENT == "production" else 1.0,
                profiles_sample_rate=0.1 if ENVIRONMENT == "production" else 1.0,
            )
        except Exception as e:
            print(f"Sentry initialization failed: {e}", file=sys.stderr)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance - using standard library logging to avoid structlog issues"""
    return logging.getLogger(name)


class RequestLogger:
    """Request logging middleware helper"""

    def __init__(self) -> None:
        self.logger = get_logger("request")

    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        user_id: Optional[str] = None,
        duration: Optional[float] = None,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log HTTP request details"""
        # Build log message
        msg = f"http_request request_id={request_id} method={method} path={path} status_code={status_code or 0}"
        if user_id:
            msg += f" user_id={user_id}"
        if duration is not None:
            msg += f" duration_ms={round(duration * 1000, 2)}"
        if error:
            msg += f" error={error}"
        if status_code and status_code >= 400:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security-related events"""
        msg = f"security_event event_type={event_type}"
        if user_id:
            msg += f" user_id={user_id}"
        if ip_address:
            msg += f" ip_address={ip_address}"
        if details:
            msg += f" details={details}"
        self.logger.warning(msg)


class BusinessLogger:
    """Business logic logging helper"""

    def __init__(self, component: str):
        self.logger = get_logger(f"business.{component}")

    def log_operation(
        self,
        operation: str,
        user_id: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """Log business operations"""
        msg = f"business_operation operation={operation} user_id={user_id} success={success}"
        if resource_id:
            msg += f" resource_id={resource_id}"
        if details:
            msg += f" details={details}"
        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)

    def log_ai_generation(
        self,
        job_id: str,
        user_id: str,
        model: str,
        provider: str,
        prompt_length: int,
        success: bool,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log AI generation events"""
        msg = (
            f"ai_generation job_id={job_id} user_id={user_id} "
            f"model={model} provider={provider} "
            f"prompt_length={prompt_length} success={success}"
        )
        if duration:
            msg += f" duration_ms={round(duration * 1000, 2)}"
        if error:
            msg += f" error={error}"
        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)


# Global logger instances


request_logger = RequestLogger()
