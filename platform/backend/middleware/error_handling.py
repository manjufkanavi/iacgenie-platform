"""

Error handling middleware for consistent API responses

"""

import logging

from typing import Dict, Any, Optional, Callable

from datetime import datetime

from fastapi import Request, Response, HTTPException

from fastapi.responses import JSONResponse

from fastapi.exceptions import RequestValidationError

import asyncio
import sqlalchemy.exc

from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for API responses"""

    @staticmethod
    def create_error_response(
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized error response
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
        Returns:
            Standardized error response dictionary
        """
        error_response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "statusCode": status_code,
                "details": details or {},
                "timestamp": datetime.now().isoformat(),
            },
        }
        return error_response

    @staticmethod
    def create_http_error_response(
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """
        Create a JSONResponse with standardized error format
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
        Returns:
            JSONResponse with error details
        """
        error_data = ErrorHandler.create_error_response(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )
        return JSONResponse(status_code=status_code, content=error_data)

    @staticmethod
    def handle_webhook_error(exc: Exception) -> Dict[str, Any]:
        """Handle webhook errors, return error response dict."""
        return ErrorHandler.create_error_response(
            message=f"Webhook error: {str(exc)}",
            error_code="WEBHOOK_ERROR",
            status_code=400,
        )

    @staticmethod
    def handle_validation_error(exc: Exception) -> Dict[str, Any]:
        """Handle validation errors, return error response dict."""
        msg = str(exc)
        if hasattr(exc, "errors"):
            msg = str(exc.errors())
        return ErrorHandler.create_error_response(
            message=msg, error_code="VALIDATION_ERROR", status_code=422
        )

    @staticmethod
    def handle_http_exception(exc: HTTPException) -> Dict[str, Any]:
        """Handle HTTP exceptions, return error response dict."""
        msg = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        status = exc.status_code if hasattr(exc, "status_code") else 400
        return ErrorHandler.create_error_response(
            message=msg, error_code="HTTP_ERROR", status_code=status
        )

    @staticmethod
    def handle_concurrent_modification(resource_type: str, resource_id: str) -> None:
        """Raise HTTPException for concurrent modification conflicts."""
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "CONCURRENT_MODIFICATION",
                    "message": f"Concurrent modification detected for {resource_type} {resource_id}",
                }
            },
        )


def create_success_response(
    data: Dict[str, Any], message: str = "Operation completed successfully"
) -> Dict[str, Any]:
    """
    Create a standardized success response
    Args:
        data: Response data
        message: Success message
    Returns:
        Standardized success response dictionary
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }


# Global error handler instance


error_handler = ErrorHandler()


async def error_handling_middleware(
    request: Request, call_next: Callable[..., Any]
) -> Response:
    """Enhanced error handling middleware"""
    start_time = datetime.utcnow()
    try:
        # Add request ID for tracking
        request_id = request.headers.get(
            "X-Request-ID", f"req_{start_time.timestamp()}"
        )
        request.state.request_id = request_id
        # Process request
        response = await call_next(request)
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = str(
            (datetime.utcnow() - start_time).total_seconds()
        )
        return response
    except RequestValidationError as exc:
        # Handle validation errors
        error_response = error_handler.handle_validation_error(exc)
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response["error"],
        )
    except HTTPException as exc:
        # Handle HTTP exceptions
        error_response = error_handler.handle_http_exception(exc)
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response["error"],
        )
    except sqlalchemy.exc.IntegrityError as exc:
        logger.warning(f"Database integrity error: {str(exc)}")
        error_response = error_handler.create_error_response(
            message="Resource conflict or constraint violation",
            error_code="DATABASE_CONFLICT",
            status_code=409,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response["error"],
        )
    except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.InterfaceError) as exc:
        logger.error(f"Database connection error: {str(exc)}")
        error_response = error_handler.create_error_response(
            message="Service temporarily unavailable due to database connection issues",
            error_code="DATABASE_UNAVAILABLE",
            status_code=503,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response["error"],
        )
    except sqlalchemy.exc.SQLAlchemyError as exc:
        logger.error(f"Database error: {str(exc)}")
        error_response = error_handler.create_error_response(
            message="An internal database error occurred",
            error_code="DATABASE_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response["error"],
        )
    except Exception as exc:
        # Handle unexpected errors
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        error_response = error_handler.create_error_response(
            message=f"An unexpected error occurred: {str(exc)}",
            error_code="INTERNAL_ERROR",
            status_code=500,
            details={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "endpoint": str(request.url.path),
                "method": request.method,
                "original_error": str(exc),
            },
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response["error"],
        )


@asynccontextmanager
async def transaction_context(db_adapter: Any, max_retries: int = 3) -> Any:
    """Context manager for database transactions with retry logic"""
    for attempt in range(max_retries):
        try:
            # Start transaction
            transaction = await db_adapter.start_transaction()
            try:
                yield transaction
                # Commit transaction
                await db_adapter.commit_transaction(transaction)
                break
            except Exception as e:
                # Rollback transaction
                await db_adapter.rollback_transaction(transaction)
                raise e
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            # Wait before retry (exponential backoff)
            await asyncio.sleep(2**attempt)
            logger.warning(f"Transaction retry {attempt + 1}/{max_retries}: {str(e)}")


async def handle_concurrent_operation(
    operation_name: str,
    operation_func: Callable[..., Any],
    resource_type: str,
    resource_id: str,
    max_retries: int = 3,
) -> Any:
    """Handle operations that might have race conditions"""
    for attempt in range(max_retries):
        try:
            return await operation_func()
        except Exception as e:
            error_message = str(e).lower()
            if "concurrent" in error_message or "conflict" in error_message:
                if attempt == max_retries - 1:
                    error_handler.handle_concurrent_modification(
                        resource_type, resource_id
                    )
                # Wait before retry
                await asyncio.sleep(2**attempt)
                logger.warning(
                    f"Concurrent operation retry {attempt + 1}/{max_retries}: {operation_name}"
                )
                continue
            else:
                raise e


def log_api_request(request: Request, response: Response, duration: float) -> None:
    """Log API request details"""
    try:
        # Extract relevant information
        method = request.method
        path = request.url.path
        status_code = response.status_code
        user_agent = request.headers.get("User-Agent", "Unknown")
        ip_address = request.client.host if request.client else "Unknown"
        request_id = getattr(request.state, "request_id", "Unknown")
        # Determine log level
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        # Create log message
        log_message = (
            f"API Request: {method} {path} - {status_code} "
            f"({duration:.3f}s) - {ip_address} - {user_agent} - {request_id}"
        )
        logger.log(log_level, log_message)
    except Exception as e:
        logger.error(f"Failed to log API request: {str(e)}")
