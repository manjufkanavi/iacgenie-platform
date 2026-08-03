"""

Sandbox Manager Router

API endpoints for sandbox container operations.

Integrates with Keycloak authentication, Docker SDK, workflow engine, and artifact store.

"""

import logging

from typing import Any, Optional, Dict, List, cast

from fastapi import APIRouter, HTTPException, Depends

from pydantic import BaseModel, Field

from src.sandbox_manager.container_provisioner import ContainerProvisioner
from src.sandbox_manager.command_executor import CommandExecutor
from src.sandbox_manager.mtls_enforcer import MTLSEnforcer
from src.sandbox_manager.exceptions import (
    SandboxProvisionError,
    ContainerNotFoundError,
)

from middleware.auth_middleware import get_user_id

from middleware.error_handling import create_success_response

logger = logging.getLogger(__name__)

# Create router

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox Manager"])

# Global instances

_container_provisioner: Optional[ContainerProvisioner] = None

_command_executor: Optional[CommandExecutor] = None

_mtls_enforcer: Optional[MTLSEnforcer] = None


def get_container_provisioner() -> ContainerProvisioner:
    """Get the global ContainerProvisioner instance."""
    global _container_provisioner
    if _container_provisioner is None:
        _container_provisioner = ContainerProvisioner()
    return _container_provisioner


def get_command_executor() -> CommandExecutor:
    """Get the global CommandExecutor instance."""
    global _command_executor
    if _command_executor is None:
        _command_executor = CommandExecutor()
    return _command_executor


def get_mtls_enforcer() -> MTLSEnforcer:
    """Get the global MTLSEnforcer instance."""
    global _mtls_enforcer
    if _mtls_enforcer is None:
        _mtls_enforcer = MTLSEnforcer()
    return _mtls_enforcer


# ============================================================================

# Request Models

# ============================================================================


class StartSandboxRequest(BaseModel):
    """Request to start a sandbox container."""

    session_id: str = Field(..., description="Session ID for tracing")
    resources: Dict[str, Any] = Field(
        ..., description="Resource limits (cpu, memory, storage)"
    )
    services: Optional[List[str]] = Field(None, description="Services to install")
    timeout: Optional[int] = Field(3600, description="Container timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ExecCommandRequest(BaseModel):
    """Request to execute a command in sandbox."""

    container_id: str = Field(..., description="Container ID")
    command: List[str] = Field(..., description="Command to execute")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    timeout: Optional[int] = Field(300, description="Command timeout in seconds")
    working_dir: Optional[str] = Field("/workspace", description="Working directory")


class StopSandboxRequest(BaseModel):
    """Request to stop a sandbox container."""

    container_id: str = Field(..., description="Container ID")
    reason: Optional[str] = Field("", description="Reason for stopping")


class GetSandboxStatusRequest(BaseModel):
    """Request to get sandbox status."""

    container_id: str = Field(..., description="Container ID")


class ListSandboxesRequest(BaseModel):
    """Request to list sandboxes."""

    session_id: Optional[str] = Field(None, description="Filter by session ID")
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


# ============================================================================

# Response Models

# ============================================================================


class SandboxResponse(BaseModel):
    """Response model for sandbox."""

    container_id: str = Field(..., description="Container ID")
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Container status")
    resources: Dict[str, Any] = Field(..., description="Resource limits")
    workspace_path: str = Field(..., description="Workspace path")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    stopped_at: Optional[str] = Field(None, description="Stop timestamp")


class CommandResponse(BaseModel):
    """Response model for command execution."""

    container_id: str = Field(..., description="Container ID")
    command: List[str] = Field(..., description="Executed command")
    exit_code: int = Field(..., description="Exit code")
    stdout: str = Field(..., description="Standard output")
    stderr: Optional[str] = Field(None, description="Error output")
    execution_time: Optional[float] = Field(
        None, description="Execution time in seconds"
    )


class SandboxesListResponse(BaseModel):
    """Response model for sandboxes list."""

    sandboxes: List[SandboxResponse] = Field(..., description="List of sandboxes")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


# ============================================================================

# Endpoints

# ============================================================================


@router.post("/start", response_model=SandboxResponse)
async def start_sandbox(
    request: StartSandboxRequest, user_id: str = Depends(get_user_id)
) -> SandboxResponse:
    """
    Start a sandbox container.
    Args:
        request: Sandbox start request parameters
        user_id: Authenticated user ID from auth middleware
    Returns:
        SandboxResponse with container details
    Raises:
        HTTPException: If container start fails
    """
    try:
        container_provisioner = get_container_provisioner()
        # Enforce resource quotas
        cpu_limit = request.resources.get("cpu", "100m")
        memory_limit = request.resources.get("memory", "512m")
        storage_limit = request.resources.get("storage", "10g")
        # Enforce timeout
        timeout = min(request.timeout or 3600, 3600)
        # Start container
        sandbox = await container_provisioner.provision_container(  # type: ignore[call-arg]
            session_id=request.session_id,
            resources={
                "cpu": cpu_limit,
                "memory": memory_limit,
                "storage": storage_limit,
            },
            services=request.services,
            timeout=timeout,
            user_id=user_id,  # Authenticated user ID
            metadata=request.metadata,
        )
        logger.info(
            "Sandbox container started",
            extra={
                "user_id": user_id,
                "session_id": request.session_id,
                "container_id": sandbox.container_id,
                "resources": sandbox.resources,
            },
        )
        return SandboxResponse(
            container_id=sandbox.container_id,
            session_id=request.session_id,
            status=str(sandbox.status),
            resources=sandbox.resources,
            workspace_path=sandbox.workspace_path,
            created_at=str(sandbox.created_at),
            started_at=str(sandbox.started_at) if sandbox.started_at else None,
            stopped_at=str(sandbox.stopped_at) if sandbox.stopped_at else None,
        )
    except SandboxProvisionError as e:
        logger.error(f"Error starting sandbox for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "provision_error",
                    "code": "internal_error",
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Unexpected error starting sandbox for user {user_id}: {e}", exc_info=True
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


@router.post("/exec", response_model=CommandResponse)
async def exec_command(
    request: ExecCommandRequest, user_id: str = Depends(get_user_id)
) -> CommandResponse:
    """
    Execute a command in a sandbox container.
    Args:
        request: Command execution request
        user_id: Authenticated user ID from auth middleware
    Returns:
        CommandResponse with execution results
    Raises:
        HTTPException: If command execution fails
    """
    try:
        command_executor = get_command_executor()
        # Enforce timeout
        timeout = min(request.timeout or 300, 300)
        # Execute command
        result = await command_executor.execute_command(  # type: ignore[call-arg]
            container_id=request.container_id,
            command=request.command,
            env=request.env,
            timeout=timeout,
            working_dir=request.working_dir,
            user_id=user_id,  # Authenticated user ID
        )
        cmd_result: CommandResponse = cast(CommandResponse, result)
        logger.info(
            "Command executed in sandbox",
            extra={
                "user_id": user_id,
                "container_id": request.container_id,
                "command": " ".join(request.command),
                "exit_code": cmd_result.exit_code,
            },
        )
        return CommandResponse(
            container_id=request.container_id,
            command=request.command,
            exit_code=cmd_result.exit_code,
            stdout=cmd_result.stdout,
            stderr=cmd_result.stderr,
            execution_time=cmd_result.execution_time,
        )
    except Exception as e:
        logger.error(f"Error executing command for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to execute command",
                    "type": "execution_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/stop")
async def stop_sandbox(
    request: StopSandboxRequest, user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Stop a sandbox container.
    Args:
        request: Stop request parameters
        user_id: Authenticated user ID from auth middleware
    Returns:
        Success response
    Raises:
        HTTPException: If container cannot be stopped
    """
    try:
        container_provisioner = get_container_provisioner()
        # Stop container
        await container_provisioner.stop_container(  # type: ignore[call-arg]
            container_id=request.container_id,
            user_id=user_id,  # Authenticated user ID
            reason=request.reason,
        )
        logger.info(
            "Sandbox container stopped",
            extra={
                "user_id": user_id,
                "container_id": request.container_id,
                "reason": request.reason,
            },
        )
        return create_success_response(
            message="Sandbox container stopped successfully",
            data={"container_id": request.container_id},
        )
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found for user {user_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": str(e),
                    "type": "not_found",
                    "code": "container_not_found",
                }
            },
        )
    except Exception as e:
        logger.error(f"Error stopping sandbox for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to stop sandbox",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for sandbox manager service.
    Returns:
        Health status of the sandbox manager service
    """
    try:
        container_provisioner = get_container_provisioner()
        command_executor = get_command_executor()
        mtls_enforcer = get_mtls_enforcer()
        return {
            "status": "healthy",
            "service": "sandbox_manager",
            "docker_available": container_provisioner.client is not None,
            "command_executor_initialized": command_executor is not None,
            "mtls_enforcer_initialized": mtls_enforcer is not None,
            "resource_quotas_enabled": True,
            "timeout_enforcement_enabled": True,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "service": "sandbox_manager", "error": str(e)}


@router.get("/{container_id}", response_model=SandboxResponse)
async def get_sandbox_status(
    container_id: str, user_id: str = Depends(get_user_id)
) -> SandboxResponse:
    """
    Get the status of a sandbox container.
    Args:
        container_id: Container ID
        user_id: Authenticated user ID from auth middleware
    Returns:
        SandboxResponse with container status
    Raises:
        HTTPException: If container not found
    """
    try:
        container_provisioner = get_container_provisioner()
        # Get sandbox status
        sandbox = await container_provisioner.get_sandbox_status(  # type: ignore[attr-defined]
            container_id=container_id,
            user_id=user_id,  # Authenticated user ID
        )
        logger.info(
            "Sandbox status retrieved",
            extra={
                "user_id": user_id,
                "container_id": container_id,
                "status": sandbox.status,
            },
        )
        return SandboxResponse(
            container_id=sandbox.container_id,
            session_id=sandbox.session_id,
            status=str(sandbox.status),
            resources=sandbox.resources,
            workspace_path=sandbox.workspace_path,
            created_at=str(sandbox.created_at),
            started_at=str(sandbox.started_at) if sandbox.started_at else None,
            stopped_at=str(sandbox.stopped_at) if sandbox.stopped_at else None,
        )
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found for user {user_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": str(e),
                    "type": "not_found",
                    "code": "container_not_found",
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Error getting sandbox status for user {user_id}: {e}", exc_info=True
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


@router.get("", response_model=SandboxesListResponse)
async def list_sandboxes(
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(get_user_id),
) -> SandboxesListResponse:
    """
    List sandbox containers with optional filters.
    Args:
        session_id: Filter by session ID
        status: Filter by status
        limit: Maximum number to return
        offset: Offset for pagination
        user_id: Authenticated user ID from auth middleware
    Returns:
        SandboxesListResponse with filtered sandboxes
    Raises:
        HTTPException: If listing fails
    """
    try:
        container_provisioner = get_container_provisioner()
        # List sandboxes
        sandboxes = await container_provisioner.list_sandboxes(  # type: ignore[attr-defined]
            user_id=user_id,  # Authenticated user ID
            session_id=session_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        logger.info(
            "Sandboxes listed",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "status": status,
                "count": len(sandboxes),
            },
        )
        return SandboxesListResponse(
            sandboxes=[
                SandboxResponse(
                    container_id=sandbox.container_id,
                    session_id=sandbox.session_id,
                    status=str(sandbox.status),
                    resources=sandbox.resources,
                    workspace_path=sandbox.workspace_path,
                    created_at=str(sandbox.created_at),
                    started_at=str(sandbox.started_at) if sandbox.started_at else None,
                    stopped_at=str(sandbox.stopped_at) if sandbox.stopped_at else None,
                )
                for sandbox in sandboxes
            ],
            total=len(sandboxes),
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error listing sandboxes for user {user_id}: {e}", exc_info=True)
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
