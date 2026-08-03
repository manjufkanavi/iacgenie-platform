"""

Agents Router

API endpoints for agent executor operations.

Integrates with Keycloak authentication, workflow engine, and artifact store.

"""

import logging

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends

from pydantic import BaseModel, Field

from modules.agent_executor.task_router import TaskRouter

from modules.agent_executor.exceptions import AgentExecutionError, AgentNotFoundError

from modules.workflow_engine.session_manager import session_manager

from middleware.auth_middleware import get_user_id

from middleware.error_handling import create_success_response

logger = logging.getLogger(__name__)

# Create router

router = APIRouter(prefix="/api/agents", tags=["Agent Executor"])

# Global instances

_task_router: Optional[TaskRouter] = None


def get_task_router() -> TaskRouter:
    """Get the global TaskRouter instance."""
    global _task_router
    if _task_router is None:
        _task_router = TaskRouter()
    return _task_router


# ============================================================================

# Request Models

# ============================================================================


class SubmitTaskRequest(BaseModel):
    """Request to submit an agent task."""

    agent_type: str = Field(
        ..., description="Type of agent (code_review, testing, deployment)"
    )
    task_data: Dict[str, Any] = Field(
        ..., description="Task data specific to agent type"
    )
    session_id: Optional[str] = Field(None, description="Session ID for tracing")
    priority: int = Field(5, ge=1, le=10, description="Task priority (1-10)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class GetAgentStatusRequest(BaseModel):
    """Request to get agent status."""

    agent_id: str = Field(..., description="Agent ID")


class StopAgentRequest(BaseModel):
    """Request to stop an agent."""

    agent_id: str = Field(..., description="Agent ID")
    reason: Optional[str] = Field("", description="Reason for stopping")


class ListAgentsRequest(BaseModel):
    """Request to list agents."""

    session_id: Optional[str] = Field(None, description="Filter by session ID")
    agent_type: Optional[str] = Field(None, description="Filter by agent type")
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


# ============================================================================

# Response Models

# ============================================================================


class AgentResponse(BaseModel):
    """Response model for agent."""

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Type of agent")
    status: str = Field(..., description="Agent status")
    task_data: Optional[Dict[str, Any]] = Field(None, description="Task data")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class TaskResponse(BaseModel):
    """Response model for task submission."""

    agent_id: str = Field(..., description="Agent ID")
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    priority: int = Field(..., description="Task priority")
    created_at: str = Field(..., description="Creation timestamp")


class AgentsListResponse(BaseModel):
    """Response model for agents list."""

    agents: List[AgentResponse] = Field(..., description="List of agents")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


# ============================================================================

# Endpoints

# ============================================================================


@router.post("/submit", response_model=TaskResponse)
async def submit_task(
    request: SubmitTaskRequest, user_id: str = Depends(get_user_id)
) -> TaskResponse:
    """
    Submit a task to an agent.
    Args:
        request: Task submission request
        user_id: Authenticated user ID from auth middleware
    Returns:
        TaskResponse with task details
    Raises:
        HTTPException: If task submission fails
    """
    try:
        task_router = get_task_router()
        # Create agent
        agent = await task_router.create_agent(
            agent_type=request.agent_type,
            user_id=user_id,  # Authenticated user ID
            session_id=request.session_id,
            metadata=request.metadata,
        )
        # Submit task to agent
        task = await task_router.submit_task(
            agent_id=agent.id,
            task_data=request.task_data,
            priority=request.priority,
            user_id=user_id,  # Authenticated user ID
            session_id=request.session_id,
        )
        # Connect to workflow engine for session tracking
        if request.session_id:
            try:
                session = await session_manager.get_session(request.session_id)
                if session:
                    logger.info(
                        "Agent task submitted for workflow session",
                        extra={
                            "user_id": user_id,
                            "session_id": request.session_id,
                            "agent_id": agent.id,
                            "task_id": task.id,  # type: ignore[attr-defined]
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to get session {request.session_id}: {e}")
        logger.info(
            "Agent task submitted",
            extra={
                "user_id": user_id,
                "agent_id": agent.id,
                "task_id": task.id,  # type: ignore[attr-defined]
                "agent_type": request.agent_type,
            },
        )
        return TaskResponse(
            agent_id=agent.id,
            task_id=task.id,  # type: ignore[attr-defined]
            status="pending",
            priority=request.priority,
            created_at=task.created_at,  # type: ignore[attr-defined]
        )
    except AgentExecutionError as e:
        logger.error(f"Error submitting agent task for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "execution_error",
                    "code": "internal_error",
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Unexpected error submitting agent task for user {user_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for agent executor service.
    Returns:
        Health status of the agent executor service
    """
    try:
        task_router = get_task_router()
        return {
            "status": "healthy",
            "service": "agent_executor",
            "task_router_initialized": task_router is not None,
            "redis_connected": task_router.redis_client is not None
            if task_router
            else False,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "service": "agent_executor", "error": str(e)}


@router.get("/", response_model=AgentsListResponse)
async def list_agents(
    session_id: Optional[str] = None,
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(get_user_id),
) -> AgentsListResponse:
    """
    List agents with optional filters.
    Args:
        session_id: Filter by session ID
        agent_type: Filter by agent type
        status: Filter by status
        limit: Maximum number to return
        offset: Offset for pagination
        user_id: Authenticated user ID from auth middleware
    Returns:
        AgentsListResponse with filtered agents
    Raises:
        HTTPException: If listing fails
    """
    try:
        task_router = get_task_router()
        # List agents
        agents = await task_router.list_agents(  # type: ignore[attr-defined]
            user_id=user_id,  # Authenticated user ID
            session_id=session_id,
            agent_type=agent_type,
            status=status,
            limit=limit,
            offset=offset,
        )
        logger.info(
            "Agents listed",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "agent_type": agent_type,
                "status": status,
                "count": len(agents),
            },
        )
        return AgentsListResponse(
            agents=[
                AgentResponse(
                    agent_id=agent.id,
                    agent_type=agent.agent_type,
                    status=agent.status,
                    task_data=agent.task_data,
                    created_at=agent.created_at,
                    updated_at=agent.updated_at,
                )
                for agent in agents
            ],
            total=len(agents),
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error listing agents for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_status(
    agent_id: str, user_id: str = Depends(get_user_id)
) -> AgentResponse:
    """
    Get the status of an agent.
    Args:
        agent_id: Agent ID
        user_id: Authenticated user ID from auth middleware
    Returns:
        AgentResponse with agent status
    Raises:
        HTTPException: If agent not found
    """
    try:
        task_router = get_task_router()
        # Get agent status
        agent = await task_router.get_agent(agent_id, user_id)
        logger.info(
            "Agent status retrieved",
            extra={"user_id": user_id, "agent_id": agent_id, "status": agent.status},
        )
        return AgentResponse(
            agent_id=agent.id,
            agent_type=agent.agent_type,
            status=agent.status,
            task_data=agent.task_data,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
    except AgentNotFoundError as e:
        logger.warning(f"Agent not found for user {user_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": str(e),
                    "type": "not_found",
                    "code": "agent_not_found",
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Error getting agent status for user {user_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str, request: StopAgentRequest, user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Stop an agent.
    Args:
        agent_id: Agent ID
        request: Stop request parameters
        user_id: Authenticated user ID from auth middleware
    Returns:
        Success response
    Raises:
        HTTPException: If agent cannot be stopped
    """
    try:
        task_router = get_task_router()
        # Stop agent
        await task_router.stop_agent(
            agent_id=agent_id,
            user_id=user_id,  # Authenticated user ID
            reason=request.reason,
        )
        logger.info(
            "Agent stopped",
            extra={"user_id": user_id, "agent_id": agent_id, "reason": request.reason},
        )
        return create_success_response(
            message="Agent stopped successfully", data={"agent_id": agent_id}
        )
    except AgentNotFoundError as e:
        logger.warning(f"Agent not found for user {user_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": str(e),
                    "type": "not_found",
                    "code": "agent_not_found",
                }
            },
        )
    except Exception as e:
        logger.error(f"Error stopping agent for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to stop agent",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )
