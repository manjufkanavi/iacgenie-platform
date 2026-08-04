"""

Database Health Check and Monitoring Endpoints

"""

from fastapi import APIRouter, HTTPException, Depends

from typing import Dict, Any

from datetime import datetime

from db.db_provider import db_provider

from config.logging import get_logger

from middleware.auth_middleware import require_admin

logger = get_logger("database.router")

router = APIRouter(prefix="/database", tags=["database"])


@router.get("/health")
async def database_health_check(
    admin_user: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """Check database health"""
    try:
        health = await db_provider.health_check()
        return {
            "status": "success",
            "data": health,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database health check failed: {str(e)}"
        )


@router.get("/stats")
async def database_stats(admin_user: Any = Depends(require_admin)) -> Dict[str, Any]:
    """Get database statistics"""
    try:
        stats = await db_provider.get_connection_stats()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get database stats: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get database stats: {str(e)}"
        )


@router.get("/info")
async def database_info(admin_user: Any = Depends(require_admin)) -> Dict[str, Any]:
    """Get database information"""
    try:
        return {
            "status": "success",
            "data": {
                "provider": db_provider.provider,
                "initialized": db_provider._is_initialized,
                "adapter_type": type(db_provider.adapter).__name__
                if db_provider.adapter
                else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get database info: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get database info: {str(e)}"
        )


@router.post("/test-connection")
async def test_database_connection(
    admin_user: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """Test database connection"""
    try:
        # Test with a simple query
        if db_provider.provider == "sqlite":
            result = await db_provider.execute_query("SELECT 1 as test")
        else:
            result = await db_provider.execute_query("SELECT 1 as test")
        return {
            "status": "success",
            "data": {"connection": "successful", "result": result},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return {
            "status": "error",
            "data": {"connection": "failed", "error": str(e)},
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/migrations/status")
async def migration_status(admin_user: Any = Depends(require_admin)) -> Dict[str, Any]:
    """Get migration status"""
    try:
        # This would typically check Alembic migration status
        # For now, return basic info
        return {
            "status": "success",
            "data": {
                "migrations_enabled": True,
                "provider": db_provider.provider,
                "note": "Migration status requires Alembic integration",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get migration status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get migration status: {str(e)}"
        )


@router.post("/migrations/run")
async def run_migrations(admin_user: Any = Depends(require_admin)) -> Dict[str, Any]:
    """Run database migrations"""
    try:
        # This would typically run Alembic migrations
        # For now, return basic info
        return {
            "status": "success",
            "data": {
                "message": "Migrations would be run here",
                "provider": db_provider.provider,
                "note": "Migration execution requires Alembic integration",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to run migrations: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to run migrations: {str(e)}"
        )
