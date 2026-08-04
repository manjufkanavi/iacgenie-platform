import logging

from typing import List, Dict, Any

from datetime import datetime

from fastapi import APIRouter, Depends

from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field

from middleware.auth_middleware import verify_access_token
from db.db_provider import db_provider
from fastapi import WebSocket, WebSocketDisconnect
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deployments", tags=["deployments"])

# Pydantic models


class DeploymentRequest(BaseModel):
    projectId: str = Field(..., description="Project identifier")
    generationId: str = Field(..., description="Generation ID to deploy")
    provider: str = Field(..., description="Cloud provider (aws, gcp, azure)")
    region: str = Field(..., description="Deployment region")
    credentialsId: str = Field(..., description="Cloud credentials ID to use")


class DeploymentResponse(BaseModel):
    id: str
    userId: str
    projectId: str
    generationId: str
    provider: str
    region: str
    credentialsId: str
    status: str
    logs: List[Dict[str, Any]]
    outputs: Dict[str, Any]
    createdAt: str
    updatedAt: str


class DeploymentListResponse(BaseModel):
    deployments: List[DeploymentResponse]
    total: int


# Service layer


class DeploymentService:
    @staticmethod
    async def list_deployments(uid: str, project_id: str) -> List[Dict[str, Any]]:
        """List all deployments for a user's project"""
        try:
            deployments = await db_provider.list_deployments(uid, project_id)
            # Ensure proper typing
            for dep in deployments:
                dep["createdAt"] = str(dep.get("created_at", ""))
                dep["updatedAt"] = str(dep.get("updated_at", ""))
                dep["userId"] = dep.get("user_id")
                dep["projectId"] = dep.get("project_id")
                # Parse metadata
                meta = dep.get("metadata", {})
                if isinstance(meta, str):
                    meta = json.loads(meta)
                dep["generationId"] = meta.get("generationId", "")
                dep["credentialsId"] = meta.get("credentialsId", "")
                dep["region"] = meta.get("region", "")
                dep["logs"] = meta.get("logs", [])
                dep["outputs"] = meta.get("outputs", {})
            return deployments
        except Exception as e:
            logger.error(f"Error listing deployments: {str(e)}")
            raise e

    @staticmethod
    async def create_deployment(
        uid: str, project_id: str, dep_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new deployment record"""
        try:
            now = datetime.now()
            meta_data = {
                "generationId": dep_data["generationId"],
                "region": dep_data["region"],
                "credentialsId": dep_data["credentialsId"],
                "logs": [],
                "outputs": {},
            }
            storage_data = {
                "user_id": uid,
                "project_id": project_id,
                "platform": dep_data["provider"],
                "status": "pending",
                "metadata": meta_data,
                "created_at": now,
                "updated_at": now,
            }
            dep_id = await db_provider.create_deployment(storage_data)
            if not dep_id:
                raise ValueError("Failed to create deployment in db")

            result = storage_data.copy()
            result["id"] = dep_id
            result["userId"] = uid
            result["projectId"] = project_id
            result["generationId"] = dep_data["generationId"]
            result["provider"] = dep_data["provider"]
            result["region"] = dep_data["region"]
            result["credentialsId"] = dep_data["credentialsId"]
            result["logs"] = []
            result["outputs"] = {}
            result["createdAt"] = str(now)
            result["updatedAt"] = str(now)
            return result
        except Exception as e:
            logger.error(f"Error creating deployment: {str(e)}")
            raise e

    @staticmethod
    async def update_deployment(
        uid: str, project_id: str, dep_id: str, dep_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing deployment record"""
        try:
            existing = await db_provider.get_deployment(dep_id)
            if not existing:
                raise ValueError("Deployment not found")
            if existing.get("user_id") != uid:
                raise ValueError("Unauthorized access to deployment")

            now = datetime.now()

            # Extract metadata updates
            meta = existing.get("metadata", {})
            if isinstance(meta, str):
                meta = json.loads(meta)

            if "logs" in dep_data:
                meta["logs"] = dep_data["logs"]
            if "outputs" in dep_data:
                meta["outputs"] = dep_data["outputs"]

            updates = {
                "status": dep_data.get("status", existing.get("status")),
                "metadata": meta,
                "updated_at": now,
            }

            await db_provider.update_deployment(dep_id, updates)

            result = existing.copy()
            result.update(updates)
            result["userId"] = uid
            result["projectId"] = project_id
            result["generationId"] = meta.get("generationId", "")
            result["credentialsId"] = meta.get("credentialsId", "")
            result["region"] = meta.get("region", "")
            result["logs"] = meta.get("logs", [])
            result["outputs"] = meta.get("outputs", {})
            result["createdAt"] = str(existing.get("created_at", ""))
            result["updatedAt"] = str(now)
            return result
        except Exception as e:
            logger.error(f"Error updating deployment: {str(e)}")
            raise e

    @staticmethod
    async def delete_deployment(
        uid: str, project_id: str, dep_id: str
    ) -> Dict[str, Any]:
        """Delete a deployment record"""
        try:
            existing = await db_provider.get_deployment(dep_id)
            if not existing:
                raise ValueError("Deployment not found")
            if existing.get("user_id") != uid:
                raise ValueError("Unauthorized access to deployment")

            await db_provider.delete_deployment(dep_id)
            return {
                "success": True,
                "message": "Deployment deleted successfully",
                "dep_id": dep_id,
            }
        except Exception as e:
            logger.error(f"Error deleting deployment: {str(e)}")
            raise e


# Initialize service


deployment_service = DeploymentService()

# API Endpoints


@router.get("/{project_id}", response_model=DeploymentListResponse)
async def list_deployments(
    project_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """List all deployments for a project"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        # Get deployments from database
        deployments_data = await deployment_service.list_deployments(uid, project_id)
        # Convert to Pydantic models
        deployments = []
        for dep_data in deployments_data:
            deployments.append(DeploymentResponse(**dep_data))
        response = DeploymentListResponse(
            deployments=deployments, total=len(deployments)
        )
        return response
    except Exception as e:
        logger.error(f"Failed to list deployments: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to list deployments: {str(e)}",
            },
        )


@router.post("/{project_id}")
async def create_deployment(
    project_id: str, dep: DeploymentRequest, user: Any = Depends(verify_access_token)
) -> Any:
    """Create a new deployment record"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        # Create the deployment record
        result = await deployment_service.create_deployment(uid, project_id, dep.dict())
        response_content = {"success": True, "result": result}
        return JSONResponse(status_code=201, content=response_content)
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to create deployment: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to create deployment: {str(e)}",
            },
        )


@router.put("/{project_id}/{dep_id}")
async def update_deployment(
    project_id: str,
    dep_id: str,
    dep: DeploymentRequest,
    user: Any = Depends(verify_access_token),
) -> Any:
    """Update an existing deployment record"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        # Update the deployment record
        result = await deployment_service.update_deployment(
            uid, project_id, dep_id, dep.dict()
        )
        response_content = {"success": True, "result": result}
        return JSONResponse(status_code=200, content=response_content)
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to update deployment: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to update deployment: {str(e)}",
            },
        )


@router.delete("/{project_id}/{dep_id}")
async def delete_deployment(
    project_id: str, dep_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Delete a deployment record"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        # Delete the deployment record
        result = await deployment_service.delete_deployment(uid, project_id, dep_id)
        response_content = {"success": True, "result": result}
        return JSONResponse(status_code=200, content=response_content)
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to delete deployment: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to delete deployment: {str(e)}",
            },
        )


@router.websocket("/ws/{dep_id}/logs")
async def deployment_logs_websocket(websocket: WebSocket, dep_id: str) -> None:
    """Stream deployment logs via WebSocket subscribing to Redis"""
    await websocket.accept()

    try:
        from modules.workflow_engine.config import WorkflowConfig
        import redis.asyncio as aioredis

        config = WorkflowConfig()
        client = aioredis.from_url(config.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
        pubsub = client.pubsub()
        channel_id = f"deployment:logs:{dep_id}"
        await pubsub.subscribe(channel_id)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    try:
                        # Ensure it's valid JSON before sending
                        json_data = json.loads(data) if isinstance(data, str) else data
                        await websocket.send_json(json_data)
                    except json.JSONDecodeError:
                        await websocket.send_text(data)
        except WebSocketDisconnect:
            pass
        finally:
            await pubsub.unsubscribe(channel_id)
            await client.close()

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except RuntimeError:
            pass


@router.post("/{project_id}/{dep_id}/cancel")
async def cancel_deployment(
    project_id: str, dep_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Cancel an active deployment execution"""
    try:
        uid = user.get("uid")
        if not uid:
            return JSONResponse(
                status_code=401, content={"success": False, "message": "Invalid token"}
            )

        existing = await db_provider.get_deployment(dep_id)
        if not existing or existing.get("user_id") != uid:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Deployment not found"},
            )

        if existing.get("status") in ["completed", "failed", "cancelled"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Deployment already finished"},
            )

        # Publish cancellation event to Redis
        from modules.workflow_engine.config import WorkflowConfig
        from modules.workflow_engine.redis_client import RedisClient

        config = WorkflowConfig()
        redis_client = RedisClient(config=config)
        redis_client.connect()

        cancel_channel = f"deployment:cancel:{dep_id}"
        redis_client.publish(cancel_channel, {"action": "cancel", "dep_id": dep_id})

        # Mark as cancelled in DB
        await db_provider.update_deployment(
            dep_id, {"status": "cancelled", "updated_at": datetime.now()}
        )

        redis_client.disconnect()

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Cancellation signal sent"},
        )
    except Exception as e:
        logger.error(f"Failed to cancel deployment: {str(e)}")
        return JSONResponse(
            status_code=500, content={"success": False, "message": str(e)}
        )
