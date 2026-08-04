import logging

from typing import List, Dict, Any

from fastapi import APIRouter, Depends

from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field
from sqlalchemy import delete

from db.db_provider import db_provider
from utils.serialization import prepare_api_response

from middleware.auth_middleware import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])

# Pydantic models


class AuditLogRequest(BaseModel):
    projectId: str = Field(..., description="Project identifier")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource affected")
    details: Dict[str, Any] = Field(default={}, description="Additional details")


class AuditLogResponse(BaseModel):
    id: str
    userId: str
    projectId: str
    actor: Dict[str, str]
    action: str
    resource: str
    details: Dict[str, Any]
    ipAddress: str
    timestamp: str


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int


# Service layer


class AuditLogService:
    @staticmethod
    def _map_to_ui(log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map postgres snake_case fields to UI camelCase fields"""
        if not log_data:
            return {}
        return {
            "id": log_data.get("id"),
            "userId": log_data.get("user_id"),
            "projectId": "",
            "actor": {
                "name": "User",
                "email": "",
            },
            "action": log_data.get("action"),
            "resource": log_data.get("resource_type", ""),
            "details": log_data.get("details", {}),
            "ipAddress": log_data.get("ip_address", ""),
            "timestamp": log_data.get("created_at", ""),
        }

    @staticmethod
    async def list_audit_logs(uid: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List audit logs for a user"""
        try:
            logs_data = await db_provider.list_audit_logs(uid)
            mapped = [AuditLogService._map_to_ui(log) for log in logs_data]
            return mapped[:limit]
        except Exception as e:
            logger.error(f"Error listing audit logs: {str(e)}")
            raise e

    @staticmethod
    async def create_audit_log(
        uid: str, log_data: Dict[str, Any], user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new audit log entry"""
        try:
            # Parse resource field into resource_type/resource_id
            resource = log_data.get("resource", "")
            resource_type = resource
            resource_id = ""
            if ":" in resource:
                resource_type, _, resource_id = resource.partition(":")

            db_log_data = {
                "action": log_data.get("action", ""),
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": log_data.get("details", {}),
                "ip_address": user_info.get("ipAddress", "Unknown"),
                "user_agent": user_info.get("userAgent"),
            }
            log_id = await db_provider.create_audit_log(uid, db_log_data)
            if not log_id:
                raise ValueError("Failed to create audit log")
            # Read back the created log
            all_logs = await db_provider.list_audit_logs(uid)
            for log in all_logs:
                if log.get("id") == log_id:
                    return AuditLogService._map_to_ui(log)
            return AuditLogService._map_to_ui({"id": log_id})
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            raise e

    @staticmethod
    async def delete_audit_log(uid: str, log_id: str) -> Dict[str, Any]:
        """Delete an audit log entry (admin only)"""
        try:
            from db.adapters.postgres_adapter import postgres_adapter

            if not postgres_adapter._is_initialized:
                raise ValueError("Database not initialized")
            async with postgres_adapter.async_session_factory() as session:  # type: ignore[misc]
                stmt = (
                    delete(postgres_adapter.audit_logs_table)
                    .where(postgres_adapter.audit_logs_table.c.id == log_id)
                    .where(postgres_adapter.audit_logs_table.c.user_id == uid)
                )
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount == 0:
                    raise ValueError("Audit log not found")
            return {
                "success": True,
                "message": "Audit log deleted successfully",
                "log_id": log_id,
            }
        except Exception as e:
            logger.error(f"Error deleting audit log: {str(e)}")
            raise e


# Initialize service


audit_log_service = AuditLogService()

# API Endpoints


@router.get("/{project_id}", response_model=AuditLogListResponse)
async def list_audit_logs(
    project_id: str, limit: int = 100, user: Any = Depends(verify_access_token)
) -> Any:
    """List audit logs for a project"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        logs_data = await audit_log_service.list_audit_logs(uid, limit)
        logs = [AuditLogResponse(**log_data) for log_data in logs_data]
        return AuditLogListResponse(logs=logs, total=len(logs))
    except Exception as e:
        logger.error(f"Failed to list audit logs: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to list audit logs: {str(e)}",
            },
        )


@router.post("/{project_id}")
async def create_audit_log(
    project_id: str, log: AuditLogRequest, user: Any = Depends(verify_access_token)
) -> Any:
    """Create a new audit log entry"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        user_info = {
            "name": user.get("name", "Unknown"),
            "email": user.get("email", "unknown@example.com"),
            "ipAddress": user.get("ipAddress", "Unknown"),
        }
        result = await audit_log_service.create_audit_log(
            uid, log.model_dump(), user_info
        )
        response_content = {"success": True, "result": result}
        return JSONResponse(
            status_code=201, content=prepare_api_response(response_content)
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to create audit log: {str(e)}",
            },
        )


@router.delete("/{project_id}/{log_id}")
async def delete_audit_log(
    project_id: str, log_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Delete an audit log entry (admin only)"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await audit_log_service.delete_audit_log(uid, log_id)
        response_content = {"success": True, "result": result}
        return JSONResponse(
            status_code=200, content=prepare_api_response(response_content)
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to delete audit log: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to delete audit log: {str(e)}",
            },
        )
