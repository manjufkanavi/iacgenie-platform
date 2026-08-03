"""

Rate limiting middleware with Redis support

"""

import time
import os
import hashlib

from typing import Optional, Dict, Any, Callable

from fastapi import Request, Response

from fastapi.responses import JSONResponse

import logging

import redis as _redis_lib

redis: Any = _redis_lib

import threading

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with Redis backend"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_limit: int = 100,
        default_window: int = 3600,
    ) -> None:
        if redis_url is None:
            from config.redis import get_redis_url

            redis_url = get_redis_url()
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.default_window = default_window
        self.redis_client: Optional[Any] = None
        self._memory_cache: dict[str, Any] = {}
        self._memory_lock = threading.Lock()
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for rate limiting")
        except Exception as e:
            logger.warning(
                f"Redis connection failed, using in-memory rate limiting: {str(e)}"
            )
            self.redis_client = None

    def _get_client_key(self, request: Request) -> str:
        """Generate a unique key for the client"""
        # Try to get user ID from token first
        user_id = None
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # In a real implementation, you'd decode the JWT to get user ID
                # For now, we'll use a hash of the token
                token = auth_header.split(" ")[1]
                user_id = hashlib.md5(token.encode()).hexdigest()[:8]
        except Exception:
            pass
        # Fallback to IP address
        if not user_id:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                user_id = forwarded.split(",")[0].strip()
            elif request.headers.get("X-Real-IP"):
                user_id = request.headers.get("X-Real-IP")
            else:
                user_id = request.client.host if request.client else "127.0.0.1"
        # nosemgrep: python.flask.security.audit.directly-returned-format-string.directly-returned-format-string
        return f"rate_limit:{user_id}"

    def _get_endpoint_key(self, request: Request) -> str:
        """Generate a key for the specific endpoint"""
        path = request.url.path
        method = request.method
        return f"{method}:{path}"

    def _get_rate_limit_config(self, request: Request) -> Dict[str, Any]:
        """Get rate limit configuration for the endpoint"""
        path = request.url.path
        method = request.method
        # Define rate limits for different endpoints
        rate_limits = {
            # Authentication endpoints - strict limits for security
            "POST:/api/auth/token": {
                "limit": 5,
                "window": 300,
            },  # 5 per 5 minutes (login)
            "POST:/api/auth/login": {"limit": 5, "window": 300},  # 5 per 5 minutes
            "POST:/api/auth/signup": {"limit": 3, "window": 300},  # 3 per 5 minutes
            "POST:/api/auth/refresh": {"limit": 10, "window": 3600},  # 10 per hour
            "POST:/api/auth/reset-password/request": {
                "limit": 3,
                "window": 3600,
            },  # 3 per hour
            "POST:/api/auth/reset-password": {"limit": 3, "window": 3600},  # 3 per hour
            "POST:/api/auth/verify-otp": {"limit": 5, "window": 300},  # 5 per 5 minutes
            "POST:/api/auth/forgot-password-otp": {
                "limit": 3,
                "window": 3600,
            },  # 3 per hour
            "POST:/api/auth/verify-otp-for-password-reset": {"limit": 5, "window": 300},
            "POST:/api/auth/verify-otp-and-login": {"limit": 5, "window": 300},
            "POST:/api/auth/resend-otp": {"limit": 3, "window": 60},  # 3 per minute
            "POST:/api/auth/send-security-alert": {"limit": 10, "window": 3600},
            # Authentication endpoints - more lenient
            "POST:/api/auth/token/verify": {
                "limit": 20,
                "window": 300,
            },  # 20 per 5 minutes
            "POST:/api/auth/verify-token": {
                "limit": 20,
                "window": 300,
            },  # 20 per 5 minutes
            "GET:/api/auth/health": {"limit": 100, "window": 3600},  # 100 per hour
            # Public endpoints - moderate limits
            "GET:/api/generate/status/": {"limit": 60, "window": 3600},  # 60 per hour
            "GET:/api/logs/": {"limit": 60, "window": 3600},  # 60 per hour
            "GET:/api/download/": {"limit": 30, "window": 3600},  # 30 per hour
            "GET:/api/models": {"limit": 100, "window": 3600},  # 100 per hour
            "GET:/api/models/health": {"limit": 100, "window": 3600},  # 100 per hour
            # Health and system endpoints - high limits
            "GET:/api/health": {"limit": 1000, "window": 3600},  # 1000 per hour
            "GET:/api/database/health": {
                "limit": 1000,
                "window": 3600,
            },  # 1000 per hour
            "GET:/api/database/info": {"limit": 100, "window": 3600},  # 100 per hour
            "GET:/api/debug/database": {"limit": 50, "window": 3600},  # 50 per hour
            # CRUD endpoints - standard limits
            "GET:/api/projects/": {"limit": 100, "window": 3600},  # 100 per hour
            "POST:/api/projects/": {"limit": 20, "window": 3600},  # 20 per hour
            "PUT:/api/projects/": {"limit": 50, "window": 3600},  # 50 per hour
            "DELETE:/api/projects/": {"limit": 10, "window": 3600},  # 10 per hour
            # Model configurations - higher limits for development
            "GET:/api/model-configs/": {"limit": 200, "window": 3600},
            "POST:/api/model-configs/": {"limit": 50, "window": 3600},
            "PUT:/api/model-configs/": {"limit": 100, "window": 3600},
            "DELETE:/api/model-configs/": {"limit": 20, "window": 3600},
            # Code generation - lower limits due to cost
            "POST:/api/generate": {"limit": 30, "window": 3600},  # 30 per hour
            "POST:/api/generate/": {"limit": 30, "window": 3600},
            # Admin endpoints - very low limits
            "GET:/api/admin/": {"limit": 10, "window": 3600},
            "POST:/api/admin/": {"limit": 5, "window": 3600},
            "PUT:/api/admin/": {"limit": 5, "window": 3600},
            "DELETE:/api/admin/": {"limit": 2, "window": 3600},
            # Webhook endpoints - moderate limits
            "POST:/api/webhooks/": {"limit": 100, "window": 3600},
            "GET:/api/webhooks/": {"limit": 200, "window": 3600},
        }
        endpoint_key = f"{method}:{path}"
        return rate_limits.get(
            endpoint_key, {"limit": self.default_limit, "window": self.default_window}
        )

    def check_rate_limit(
        self, request: Request, endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if the request is within rate limits"""
        client_key = self._get_client_key(request)
        if endpoint is not None:
            endpoint_key = f"custom:{endpoint}"
        else:
            endpoint_key = self._get_endpoint_key(request)
        # Use a minimal request for rate-limit config lookup when endpoint is custom
        if endpoint is not None:
            config = {"limit": self.default_limit, "window": self.default_window}
        else:
            config = self._get_rate_limit_config(request)
        limit = config["limit"]
        window = config["window"]
        if self.redis_client:
            return self._check_redis_rate_limit(client_key, endpoint_key, limit, window)
        else:
            return self._check_memory_rate_limit(
                client_key, endpoint_key, limit, window
            )

    def _check_redis_rate_limit(
        self, client_key: str, endpoint_key: str, limit: int, window: int
    ) -> Dict[str, Any]:
        """Check rate limit using Redis"""
        try:
            assert self.redis_client is not None
            current_time = int(time.time())
            window_start = current_time - window
            # Use Redis sorted set to track requests
            key = f"{client_key}:{endpoint_key}"
            # Remove old entries
            self.redis_client.zremrangebyscore(key, 0, window_start)
            # Count current requests
            current_count = self.redis_client.zcard(key)
            if current_count >= limit:
                # Get the oldest request time
                oldest_request = self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_request:
                    reset_time = oldest_request[0][1] + window
                    return {
                        "allowed": False,
                        "limit": limit,
                        "remaining": 0,
                        "reset_time": reset_time,
                        "retry_after": max(0, reset_time - current_time),
                        "window": window,
                    }
            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            self.redis_client.expire(key, window)
            return {
                "allowed": True,
                "limit": limit,
                "remaining": max(0, limit - current_count - 1),
                "reset_time": current_time + window,
                "retry_after": 0,
                "window": window,
            }
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {str(e)}")
            # Fallback to memory-based rate limiting
            return self._check_memory_rate_limit(
                client_key, endpoint_key, limit, window
            )

    def _check_memory_rate_limit(
        self, client_key: str, endpoint_key: str, limit: int, window: int
    ) -> Dict[str, Any]:
        """Check rate limit using in-memory storage (fallback)"""
        current_time = int(time.time())
        window_start = current_time - window
        key = f"{client_key}:{endpoint_key}"
        with self._memory_lock:
            if key not in self._memory_cache:
                self._memory_cache[key] = []
            # Keep only timestamps within window
            self._memory_cache[key] = [
                t for t in self._memory_cache[key] if t > window_start
            ]
            current_count = len(self._memory_cache[key])
            if current_count >= limit:
                oldest_request = self._memory_cache[key][0]
                reset_time = oldest_request + window
                return {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "retry_after": max(0, reset_time - current_time),
                    "window": window,
                }
            self._memory_cache[key].append(current_time)
            return {
                "allowed": True,
                "limit": limit,
                "remaining": max(0, limit - current_count - 1),
                "reset_time": current_time + window,
                "retry_after": 0,
                "window": window,
            }


# Global rate limiter instance


rate_limiter = RateLimiter()


async def rate_limit_middleware(
    request: Request, call_next: Callable[..., Any]
) -> Response:
    """Async rate limiting middleware"""
    try:
        # Skip rate limiting for health checks, test environments, or testing header
        if (
            request.url.path in ["/api/health", "/api/database/health"]
            or os.getenv("ENVIRONMENT") == "test"
            or os.getenv("TESTING") == "true"
            or request.headers.get("x-testing") == "true"
        ):
            return await call_next(request)
        # Check rate limit
        rate_limit_info = rate_limiter.check_rate_limit(request)
        if not rate_limit_info["allowed"]:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": (
                        f"Too many requests. "
                        f"Limit: {rate_limit_info['limit']} "
                        f"per {rate_limit_info.get('window', rate_limiter.default_window)} seconds"
                    ),
                    "retry_after": rate_limit_info["retry_after"],
                    "reset_time": rate_limit_info["reset_time"],
                },
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_limit_info["reset_time"]),
                    "Retry-After": str(rate_limit_info["retry_after"]),
                },
            )
        # Await the response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
        return response
    except Exception as e:
        logger.error(f"Rate limiting middleware error: {str(e)}")
        # Continue without rate limiting if there's an error
        return await call_next(request)


def get_rate_limit_info(request: Request) -> Dict[str, Any]:
    """Get current rate limit information for the request"""
    return rate_limiter.check_rate_limit(request)
