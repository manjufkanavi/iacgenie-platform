"""

Logging Middleware

Provides request/response logging with correlation IDs and performance tracking

"""

import time

import uuid

from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response

from config.logging import request_logger, get_logger

logger = get_logger("middleware.logging")


async def logging_middleware(
    request: Request, call_next: Callable[..., Any]
) -> Response:
    """Log all requests and responses with correlation IDs"""
    # Generate correlation ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    # Extract user ID from token if available
    user_id = None
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # In a real implementation, you'd decode the JWT to get user ID
            # For now, we'll use a hash of the token
            import hashlib

            token = auth_header.split(" ")[1]
            user_id = hashlib.md5(token.encode()).hexdigest()[:8]
    except Exception:
        pass
    # Start timing
    start_time = time.time()
    # Add request ID to headers
    request.headers.__dict__["_list"].append((b"x-request-id", request_id.encode()))
    try:
        # Process request
        response = await call_next(request)
        # Calculate duration
        duration = time.time() - start_time
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        # Log successful request
        request_logger.log_request(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            user_id=user_id,
            duration=duration,
            status_code=response.status_code,
        )
        return response
    except Exception as e:
        # Calculate duration
        duration = time.time() - start_time
        # Log failed request
        request_logger.log_request(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            user_id=user_id,
            duration=duration,
            status_code=500,
            error=str(e),
        )
        # Re-raise the exception
        raise


def log_security_event(
    event_type: str,
    request: Request,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log security events with request context"""
    ip_address = request.client.host if request.client else "unknown"
    request_logger.log_security_event(
        event_type=event_type, user_id=user_id, ip_address=ip_address, details=details
    )


def log_business_operation(
    operation: str,
    user_id: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> None:
    """Log business operations"""
    from config.logging import BusinessLogger

    business_logger = BusinessLogger("operations")
    business_logger.log_operation(
        operation=operation,
        user_id=user_id,
        resource_id=resource_id,
        details=details,
        success=success,
    )


def log_ai_generation(
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
    from config.logging import BusinessLogger

    ai_logger = BusinessLogger("ai")
    ai_logger.log_ai_generation(
        job_id=job_id,
        user_id=user_id,
        model=model,
        provider=provider,
        prompt_length=prompt_length,
        success=success,
        duration=duration,
        error=error,
    )
