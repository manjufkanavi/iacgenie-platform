"""

Health Check Service

Provides comprehensive health monitoring for all system dependencies

"""

import time

try:
    import psutil
except ImportError:
    psutil = None
import redis as _redis_module

from typing import Any, Dict

redis: Any = None  # module-level Any declaration
redis = _redis_module

import httpx

from datetime import datetime

from config.logging import get_logger

import os

logger = get_logger("health")


class HealthService:
    """Comprehensive health monitoring service"""

    def __init__(self) -> None:
        self.redis_client = None
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection for health checks"""
        try:
            from config.redis import get_redis_url

            self.redis_client = redis.from_url(get_redis_url(), decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed for health checks: {e}")
            self.redis_client = None

    async def check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        start_time = time.time()
        health_checks = {
            "database": await self._check_database(),
            "redis": await self._check_redis(),
            "ai_services": await self._check_ai_services(),
            "system_resources": self._check_system_resources(),
            "external_services": await self._check_external_services(),
        }
        # Determine overall health
        # Redis and external services can be "warning" status, not just "healthy"
        all(
            check.get("status") == "healthy"
            for check in health_checks.values()
            if check.get("status") != "warning" and check.get("message", "") == ""
        )
        # Check if critical services are working
        db_status = health_checks.get("database", {}).get("status", "unknown")
        system_status = health_checks.get("system_resources", {}).get("status")
        # If database is healthy and system resources are OK (or warning, e.g.
        # psutil missing), overall status is healthy
        if db_status == "healthy" and system_status in ["healthy", "warning"]:
            overall_status = "healthy"
        else:
            # If database fails or system resources are unhealthy, overall is unhealthy
            overall_status = "unhealthy"
        # Calculate check duration
        duration = time.time() - start_time
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": round(duration * 1000, 2),
            "checks": health_checks,
            "version": "2.0.0",
        }

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            from db.db_provider import db_provider

            start_time = time.time()
            db_health = await db_provider.health_check()
            duration = time.time() - start_time
            return {
                "status": db_health.get("status", "unknown"),
                "provider": db_health.get("provider", "unknown"),
                "response_time_ms": round(duration * 1000, 2),
                "details": db_health,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance
        Redis is optional for development. When not available, falls back to in-memory rate limiting.
        """
        # If Redis client is None (connection failed), return warning status
        if not self.redis_client:
            logger.info("Redis client not initialized. Using in-memory rate limiting.")
            return {
                "status": "warning",
                "message": "Redis not available, using in-memory rate limiting",
                "timestamp": datetime.utcnow().isoformat(),
            }
        try:
            start_time = time.time()
            self.redis_client.ping()
            duration = time.time() - start_time
            # Check Redis info
            info = self.redis_client.info()
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Redis health check failed (using in-memory): {e}")
            return {
                "status": "warning",
                "message": f"Redis check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _check_ai_services(self) -> Dict[str, Any]:
        """Check AI service providers"""
        try:
            from services.ai_service import ai_service

            start_time = time.time()
            health = await ai_service.health_check()
            duration = time.time() - start_time
            return {
                "status": "healthy"
                if health.get("status") == "healthy"
                else "unhealthy",
                "response_time_ms": round(duration * 1000, 2),
                "providers": health.get("providers", {}),
                "details": health,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"AI services health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # Check if psutil is available
            if psutil is None:
                logger.warning("psutil not installed, skipping system resources check")
                return {
                    "status": "warning",
                    "message": "psutil not installed, skipping system resources check",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            # Memory usage
            memory = psutil.virtual_memory()
            # Disk usage
            disk = psutil.disk_usage("/")
            # Network I/O
            network = psutil.net_io_counters()
            return {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": round((disk.used / disk.total) * 100, 2),
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"System resources health check failed: {e}")
            return {
                "status": "warning",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service dependencies"""
        external_checks = {}
        # Check GitHub API
        external_checks["github"] = await self._check_github()
        # Check Google Cloud (if configured)
        google_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if google_project_id:
            external_checks["google_cloud"] = await self._check_google_cloud()
        return external_checks

    async def _check_github(self) -> Dict[str, Any]:
        """Check GitHub API connectivity"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://api.github.com/zen")
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": round(
                        response.elapsed.total_seconds() * 1000, 2
                    ),
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _check_google_cloud(self) -> Dict[str, Any]:
        """Check Google Cloud connectivity"""
        try:
            # This is a basic check - in production you'd want more comprehensive checks
            return {
                "status": "healthy",
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of system health"""
        health = await self.check_system_health()
        # Count healthy vs unhealthy checks
        checks = health.get("checks", {})
        total_checks = len(checks)
        # Count warnings separately from unhealthy
        healthy_checks = sum(
            1 for check in checks.values() if check.get("status") == "healthy"
        )
        warning_checks = sum(
            1 for check in checks.values() if check.get("status") == "warning"
        )
        return {
            "overall_status": health["status"],
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "warning_checks": warning_checks,
            "unhealthy_checks": total_checks - healthy_checks - warning_checks,
            "health_percentage": round((healthy_checks / total_checks) * 100, 2)
            if total_checks > 0
            else 0,
            "timestamp": health["timestamp"],
            "response_time_ms": health["duration_ms"],
        }


# Global health service instance


health_service = HealthService()
