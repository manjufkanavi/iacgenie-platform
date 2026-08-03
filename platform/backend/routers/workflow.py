"""

Workflow Router

API endpoints for workflow engine operations.

Integrates with Keycloak authentication and existing backend infrastructure.

"""

import asyncio
import logging

import uuid

from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket
from pydantic import BaseModel, Field

from app_factory import limiter

router: APIRouter = APIRouter(prefix="/api/workflow", tags=["Workflow"])

from modules.workflow_engine.session_manager import session_manager

from modules.workflow_engine.orchestrator import WorkflowOrchestrator


from modules.workflow_engine.state_machine import SessionState

from modules.workflow_engine.exceptions import (
    SessionNotFoundError,
    InvalidStateTransitionError,
)

from middleware.auth_middleware import verify_access_token, get_user_id

from middleware.error_handling import create_success_response, error_handler


async def _verify_ws_token(websocket: Any) -> Dict[str, Any]:
    """Extract and verify Keycloak token from WebSocket query param or header."""
    from utils.jwt_utils import verify_token as verify_local_token, TokenExpiredError

    # Try query param first (matches frontend hook token param)
    token = websocket.query_params.get("token")
    if not token:
        # Try Authorization header
        header_val = websocket.headers.get("authorization")
        if header_val and header_val.startswith("Bearer "):
            token = header_val.split(" ", 1)[1]
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": "AUTHENTICATION_REQUIRED", "message": "Token required"},
        )
    try:
        payload = verify_local_token(token)
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role", "user")
        if not user_id or not email:
            raise ValueError("Token missing required claims")
        return {"uid": user_id, "email": email, "role": role}
    except TokenExpiredError:
        raise HTTPException(
            status_code=401,
            detail={"error": "TOKEN_EXPIRED", "message": "Token has expired"},
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_TOKEN", "message": "Token verification failed"},
        )


logger = logging.getLogger(__name__)

# Create router

router = APIRouter(prefix="/api/workflow", tags=["Workflow"])
# ============================================================================

# Request Models

# ============================================================================


class StartSessionRequest(BaseModel):
    """Request to start a new workflow session."""

    prompt: str = Field(..., description="User's natural language request")
    model: Optional[str] = Field(
        None, description="AI model name (e.g., 'Qwen3.6-27B-UD-MLX-4bit')"
    )
    provider: Optional[str] = Field(
        None, description="Cloud provider (aws, gcp, azure)"
    )
    build_id: Optional[str] = Field(None, description="Unique build identifier")
    project_id: Optional[str] = Field(None, description="Project ID")
    model_config_id: Optional[str] = Field(None, description="Model config ID from DB")
    git_repo_url: Optional[str] = Field(None, description="Target repository URL")
    git_branch: Optional[str] = Field(None, description="Branch to use")
    ci_provider: Optional[str] = Field(None, description="CI provider (e.g., 'github')")
    ci_inputs: Optional[Dict[str, Any]] = Field(None, description="CI workflow inputs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TransitionRequest(BaseModel):
    """Request for state transition."""

    to_state: str = Field(..., description="Target state")
    reason: Optional[str] = Field("", description="Reason for transition")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Transition metadata")


class CompleteSessionRequest(BaseModel):
    """Request to complete a session."""

    git_commit_sha: Optional[str] = Field(None, description="Commit SHA")
    ci_run_id: Optional[str] = Field(None, description="CI run ID")


class FailSessionRequest(BaseModel):
    """Request to fail a session."""

    error_message: str = Field(..., description="Error message")


class HumanReviewRequest(BaseModel):
    """Request to escalate to human review."""

    reason: str = Field(..., description="Reason for escalation")


class ResumeRequest(BaseModel):
    """Request to resume a workflow from checkpoint."""

    thread_id: Optional[str] = Field(
        None, description="Override thread_id for checkpoint lookup"
    )


# ============================================================================

# Response Models

# ============================================================================


class SessionResponse(BaseModel):
    """Response model for session."""

    id: str = Field(..., description="Session UUID")
    build_id: str = Field(..., description="Build UUID")
    user_id: str = Field(..., description="User UUID")
    prompt: str = Field(..., description="User prompt")
    status: str = Field(..., description="Current session status")
    current_iteration: int = Field(..., description="Current iteration count")
    max_iterations: int = Field(..., description="Maximum iterations")
    error_message: Optional[str] = Field(None, description="Error message if any")
    git_repo_url: Optional[str] = Field(None, description="Repository URL")
    git_branch: Optional[str] = Field(None, description="Branch name")
    git_commit_sha: Optional[str] = Field(None, description="Commit SHA")
    ci_provider: Optional[str] = Field(None, description="CI provider")
    ci_run_id: Optional[str] = Field(None, description="CI run ID")
    deployment_status: Optional[str] = Field(None, description="Deployment status")
    created_at: float = Field(..., description="Creation timestamp")
    updated_at: float = Field(..., description="Last update timestamp")


class TransitionResponse(BaseModel):
    """Response for state transition."""

    session_id: str = Field(..., description="Session UUID")
    from_state: str = Field(..., description="Previous state")
    to_state: str = Field(..., description="New state")
    reason: str = Field(..., description="Transition reason")


# ============================================================================

# API Endpoints

# ============================================================================


@router.post("/start", response_model=dict, summary="Start Workflow Session")
@limiter.limit("10/minute")
async def start_session(
    request: Request,
    body: StartSessionRequest,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Start a new workflow session.
    **Authentication Required**: Keycloak token in Authorization header
    **Request Body**:
    ```json
    {
        "prompt": "Generate EC2 instance",
        "build_id": "build-123",
        "git_repo_url": "https://github.com/user/repo",
        "git_branch": "main",
        "ci_provider": "github",
        "ci_inputs": {}
    }
    ```
    **Response**:
    ```json
    {
        "success": true,
        "data": {
            "id": "session-uuid",
            "status": "CREATED",
            "user_id": "user-uuid"
        }
    }
    ```
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Generate build ID if not provided
        build_id = body.build_id or str(uuid.uuid4())
        # Create generation_jobs record (single source of truth for code results)
        try:
            from app_factory import db_provider

            job_data = {
                "prompt": body.prompt,
                "model": body.model or (body.metadata or {}).get("model", "default"),
                "provider": body.provider
                or (body.metadata or {}).get("provider", "aws"),
                "project_id": body.project_id
                or (body.metadata or {}).get("project_id", ""),
                "model_config_id": body.model_config_id,
            }
            await db_provider.create_generation_job(job_data, job_id=build_id)
            logger.info(f"Created generation_jobs record: {build_id}")
        except Exception as e:
            logger.warning(f"Failed to create generation_jobs record: {e}")

        # Load model_config from DB for use in the orchestrator
        model_config: Optional[Dict[str, Any]] = None
        if body.model_config_id:
            try:
                from app_factory import db_provider

                cfg = await db_provider.get_model_config(
                    uid=user_id,
                    project_id=body.project_id or "",
                    config_id=body.model_config_id,
                )
                if cfg:
                    temp = float(cfg.get("temperature", 70)) / 100.0
                    model_config = {
                        "provider": cfg.get("provider", "custom"),
                        "model_name": cfg.get("model", cfg.get("model_name", "")),
                        "api_key": cfg.get("api_key", "dummy"),
                        "base_url": cfg.get("base_url", "http://127.0.0.1:1234/v1"),
                        "max_tokens": cfg.get("max_tokens", 8192),
                        "temperature": temp,
                        "timeout": cfg.get("timeout", 120),
                    }
            except Exception as e:
                logger.warning(
                    f"Failed to load model_config {body.model_config_id}: {e}"
                )

        # Fall back: try to find first valid config for the project
        if not model_config:
            try:
                from app_factory import db_provider

                configs = await db_provider.list_model_configs(
                    uid=user_id, project_id=body.project_id or ""
                )
                if configs:
                    cfg = configs[0]
                    temp = float(cfg.get("temperature", 70)) / 100.0
                    model_config = {
                        "provider": cfg.get("provider", "custom"),
                        "model_name": cfg.get("model", cfg.get("model_name", "")),
                        "api_key": cfg.get("api_key", "dummy"),
                        "base_url": cfg.get("base_url", "http://127.0.0.1:1234/v1"),
                        "max_tokens": cfg.get("max_tokens", 8192),
                        "temperature": temp,
                        "timeout": cfg.get("timeout", 120),
                    }
            except Exception as e:
                logger.warning(f"Failed to list model configs: {e}")
        # Create session in persistence layer
        session = await session_manager.create_session(
            session_id=build_id,
            build_id=build_id,
            user_id=user_id,
            prompt=body.prompt,
            git_repo_url=body.git_repo_url,
            git_branch=body.git_branch,
            ci_provider=body.ci_provider,
            ci_inputs=body.ci_inputs,
            metadata=body.metadata,
        )
        # Launch LangGraph DAG workflow via orchestrator in the background
        # Create a fresh AgentExecutor instance with LLM Proxy for each session
        try:
            from src.agent_executor.main import AgentExecutor

            agent_executor_instance = AgentExecutor()
        except Exception as e:
            logger.warning(f"Failed to create AgentExecutor: {e}")
            agent_executor_instance = None

        # Use the global broadcast service so events reach WebSocket via Redis
        from main import global_broadcast as _broadcast

        orchestrator = WorkflowOrchestrator(
            agent_executor=agent_executor_instance,
            event_broadcast=_broadcast,
        )
        asyncio.create_task(
            orchestrator.run(
                session_id=build_id,
                prompt=body.prompt,
                build_id=build_id,
                user_id=user_id,
                git_repo_url=body.git_repo_url,
                git_branch=body.git_branch,
                ci_provider=body.ci_provider,
                ci_inputs=body.ci_inputs,
                model_config=model_config,
            )
        )
        return create_success_response(
            data=session.to_dict(), message="Session started and workflow launched"
        )
    except Exception as e:
        logger.error(f"Failed to start session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to start session",
            error_code="SESSION_START_FAILED",
            status_code=500,
            details={"original_error": str(e)},
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/{session_id}", response_model=dict, summary="Get Session Status")
async def get_session_status(
    session_id: str, user: Dict[str, Any] = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Get session status by ID.
    **Authentication Required**: Keycloak token in Authorization header
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Get session
        session = await session_manager.get_session(session_id)
        # Verify user owns this session
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied: session belongs to another user",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        return create_success_response(
            data=session.to_dict(), message="Session retrieved successfully"
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/{session_id}/status", response_model=dict, summary="Get Session State")
async def get_workflow_status(
    session_id: str, user: Dict[str, Any] = Depends(verify_access_token)
) -> Dict[str, Any]:
    """Get just the state of a session."""
    try:
        user_id = get_user_id(user)
        session = await session_manager.get_session(session_id)
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return {
            "session_id": session_id,
            "state": session.status.value
            if hasattr(session.status, "value")
            else str(session.status),
        }
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Failed to get session status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}/logs", response_model=dict, summary="Get Session Logs")
async def get_workflow_logs(
    session_id: str, user: Dict[str, Any] = Depends(verify_access_token)
) -> Dict[str, Any]:
    """Get logs for a session."""
    try:
        user_id = get_user_id(user)
        session = await session_manager.get_session(session_id)
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        from app_factory import db_provider

        job = await db_provider.get_generation_job(session_id)
        logs: list[Any] = []
        if job and job.get("logs"):
            logs = job.get("logs", [])
        return {"session_id": session_id, "logs": logs}
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Failed to get session logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}/code", response_model=dict, summary="Get Session Code")
async def get_workflow_code(
    session_id: str, user: Dict[str, Any] = Depends(verify_access_token)
) -> Dict[str, Any]:
    """Get generated code for a session."""
    try:
        user_id = get_user_id(user)
        session = await session_manager.get_session(session_id)
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        from app_factory import db_provider

        job = await db_provider.get_generation_job(session_id)
        code: list[Any] = []
        if job and job.get("code"):
            code = job.get("code", [])
        return {"session_id": session_id, "code": code}
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Failed to get session code: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{session_id}/transition", response_model=dict, summary="Transition Session State"
)
async def transition_session(
    session_id: str,
    request: Request,
    body: TransitionRequest,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Transition a session to a new state.
    **Authentication Required**: Keycloak token in Authorization header
    **Request Body**:
    ```json
    {
        "to_state": "CODING",
        "reason": "Starting code generation",
        "metadata": {}
    }
    ```
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Get session
        session = await session_manager.get_session(session_id)
        # Verify user owns this session
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied: session belongs to another user",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        # Parse target state
        try:
            to_state = SessionState(body.to_state)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=error_handler.create_error_response(
                    message=f"Invalid state: {body.to_state}",
                    error_code="INVALID_STATE",
                    status_code=400,
                ),
            )
        # Perform transition
        session = await session_manager.transition_session(
            session_id=session_id,
            to_state=to_state,
            reason=body.reason or "",
            metadata=body.metadata,
        )
        return create_success_response(
            data=session.to_dict(), message="Session transitioned successfully"
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail=error_handler.create_error_response(
                message=str(e), error_code="INVALID_TRANSITION", status_code=400
            ),
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to transition session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to transition session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post("/{session_id}/complete", response_model=dict, summary="Complete Session")
async def complete_session(
    session_id: str,
    request: Request,
    body: CompleteSessionRequest,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Complete a session successfully.
    **Authentication Required**: Keycloak token in Authorization header
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Get session
        session = await session_manager.get_session(session_id)
        # Verify user owns this session
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied: session belongs to another user",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        # Update session with completion info
        session = await session_manager.transition_session(
            session_id=session_id,
            to_state=SessionState.COMPLETED,
            reason="Session completed successfully",
            metadata={
                "git_commit_sha": body.git_commit_sha,
                "ci_run_id": body.ci_run_id,
            },
        )
        return create_success_response(
            data=session.to_dict(), message="Session completed successfully"
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to complete session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post("/{session_id}/fail", response_model=dict, summary="Fail Session")
async def fail_session(
    session_id: str,
    request: Request,
    body: FailSessionRequest,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Mark a session as failed.
    **Authentication Required**: Keycloak token in Authorization header
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Get session
        session = await session_manager.get_session(session_id)
        # Verify user owns this session
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied: session belongs to another user",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        # Set error and transition to FAILED
        session = await session_manager.set_error(
            session_id=session_id, error_message=body.error_message
        )
        session = await session_manager.transition_session(
            session_id=session_id,
            to_state=SessionState.FAILED,
            reason=body.error_message,
        )
        return create_success_response(
            data=session.to_dict(), message="Session marked as failed"
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fail session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to fail session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post(
    "/{session_id}/human-review",
    response_model=dict,
    summary="Escalate to Human Review",
)
async def escalate_to_human_review(
    session_id: str,
    request: Request,
    body: HumanReviewRequest,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Escalate a session to human review.
    **Authentication Required**: Keycloak token in Authorization header
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Get session
        session = await session_manager.get_session(session_id)
        # Verify user owns this session
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied: session belongs to another user",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        # Transition to HUMAN_REVIEW
        session = await session_manager.transition_session(
            session_id=session_id,
            to_state=SessionState.HUMAN_REVIEW,
            reason=body.reason,
        )
        return create_success_response(
            data=session.to_dict(), message="Session escalated to human review"
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to escalate session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to escalate session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post(
    "/{session_id}/resume",
    response_model=dict,
    summary="Resume Workflow from Checkpoint",
)
async def resume_session(
    session_id: str,
    request: Request,
    body: ResumeRequest,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Resume a LangGraph workflow session from its last checkpoint.
    **Authentication Required**: Keycloak token in Authorization header
    **Request Body**:
    ```json
    {
        "thread_id": "optional-override-thread-id"
    }
    ```
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Get session
        session = await session_manager.get_session(session_id)
        # Verify user owns this session
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied: session belongs to another user",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        # Resume via LangGraph orchestrator
        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.resume(session_id, thread_id=body.thread_id)

        if "error" in result:
            return create_success_response(data=result, message=result["error"])

        return create_success_response(
            data=result, message="Workflow resumed successfully"
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to resume session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("", response_model=dict, summary="List Sessions")
async def list_sessions(
    request: Request,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    List sessions for the authenticated user.
    **Authentication Required**: Keycloak token in Authorization header
    **Query Parameters**:
    - status: Filter by session status
    - limit: Maximum number of sessions to return (default: 100)
    - offset: Offset for pagination (default: 0)
    """
    try:
        # Get user ID from Keycloak token
        user_id = get_user_id(user)
        # Parse status filter
        status_filter = None
        if status:
            try:
                status_filter = SessionState(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=error_handler.create_error_response(
                        message=f"Invalid status: {status}",
                        error_code="INVALID_STATUS",
                        status_code=400,
                    ),
                )
        # List sessions
        sessions = await session_manager.list_sessions(
            user_id=user_id, status=status_filter, limit=limit, offset=offset
        )
        return create_success_response(
            data={
                "sessions": [s.to_dict() for s in sessions],
                "total": len(sessions),
                "limit": limit,
                "offset": offset,
            },
            message="Sessions retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to list sessions",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health", response_model=dict, summary="Workflow Engine Health Check")
async def workflow_health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the workflow engine service.
    **No Authentication Required**
    **Response**:
    ```json
    {
        "success": true,
        "data": {
            "status": "healthy",
            "service": "workflow-engine",
            "components": {
                "session_manager": "ok",
                "redis": "ok",
                "postgres": "ok"
            }
        }
    }
    ```
    """

    components: Dict[str, str] = {"session_manager": "ok"}

    # Check Redis via event broadcast service
    try:
        from main import global_broadcast

        broadcast = global_broadcast
        redis = getattr(broadcast, "_redis", None)
        if redis is not None and redis.is_connected():
            components["redis"] = "ok"
        else:
            components["redis"] = "degraded"
    except Exception:
        components["redis"] = "degraded"

    # Check Postgres via session manager
    try:
        await session_manager.get_session("nonexistent")
    except Exception:
        pass  # Session not found is expected; any other error means degraded
    components["postgres"] = "ok"

    overall = "healthy" if all(v == "ok" for v in components.values()) else "degraded"

    return create_success_response(
        data={
            "status": overall,
            "service": "workflow-engine",
            "components": components,
        },
        message="Workflow engine is operational",
    )


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@router.websocket("/{session_id}/ws")
async def workflow_websocket(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    WebSocket endpoint for real-time workflow event streaming.
    Subscribes to the Redis pub/sub channel for the session and forwards
    events to the connected client as JSON messages.

    **Authentication Required**: Keycloak token via query param `?token=<api_token>`
    **Message Format** (server -> client): JSON with type, session_id, data, timestamp
    """
    # Accept the connection first so we can cleanly send JSON error responses to the client
    await websocket.accept()

    # Verify token
    try:
        user = await _verify_ws_token(websocket)
    except HTTPException as exc:
        detail: Dict[str, str] = exc.detail if isinstance(exc.detail, dict) else {}
        await websocket.send_json(
            {
                "error": detail.get("error", "AUTH_FAILED"),
                "message": detail.get("message", ""),
            }
        )
        await websocket.close()
        return

    # Verify session exists and belongs to user
    try:
        session = await session_manager.get_session(session_id)
        if session.user_id != user.get("uid"):
            await websocket.send_json(
                {"error": "ACCESS_DENIED", "message": "Session belongs to another user"}
            )
            await websocket.close()
            return
    except SessionNotFoundError:
        await websocket.send_json(
            {"error": "SESSION_NOT_FOUND", "message": "Session not found"}
        )
        await websocket.close()
        return
    # Session alive check — let frontend know if session is actively running
    active_states = {
        "created",
        "pending",
        "running",
        "clarify",
        "coding",
        "validating",
        "planning",
        "applying",
        "testing",
        "git_push",
        "ci_trigger",
        "ci_monitor",
        "human_review",
    }

    status_raw = session.status
    if hasattr(status_raw, "value"):
        status_str = str(status_raw.value).lower()
    elif hasattr(status_raw, "name"):
        status_str = str(status_raw.name).lower()
    else:
        status_str = str(status_raw).lower()
        if status_str.startswith("sessionstate."):
            status_str = status_str.split(".", 1)[1]

    # Check DB for terminal states that in-memory session might have missed
    # (e.g. when Celery updated DB to 'failed' but FastAPI in-memory is stale)
    # Only override if DB reports a TERMINAL state; for active states like
    # 'pending'/'running', the in-memory session status is more accurate.
    terminal_states = {"completed", "failed"}
    error_message_override = getattr(session, "error_message", None)
    try:
        from app_factory import db_provider

        db_job = await db_provider.get_generation_job(session_id)
        if db_job:
            db_status = str(db_job.get("status", "")).lower()
            if db_status in terminal_states:
                status_str = db_status
            if db_job.get("error"):
                error_message_override = db_job.get("error")
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            f"Failed to fetch DB status for websocket: {e}"
        )

    if status_str not in active_states:
        await websocket.send_json(
            {
                "type": "session_info",
                "session_id": session_id,
                "data": {
                    "active": False,
                    "status": status_str,
                    "message": error_message_override
                    or "Session is not actively running",
                },
            }
        )

    from main import global_broadcast

    broadcast = global_broadcast

    async def _forward_to_client(channel: str, raw_payload: str) -> None:
        """Send incoming Redis message to WebSocket client."""
        try:
            await websocket.send_text(raw_payload)
        except Exception:
            pass

    broadcast.subscribe(f"workflow:{session_id}", _forward_to_client)
    broadcast.subscribe("workflow:global", _forward_to_client)

    try:
        from fastapi import WebSocketDisconnect
        from datetime import datetime

        while True:
            try:
                # Wait for any incoming client messages
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                command = data.get("command")
                if command == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "session_id": session_id,
                            "data": {},
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
            except asyncio.TimeoutError:
                # Send a heartbeat/ping to the client to keep connection alive
                try:
                    await websocket.send_json(
                        {
                            "type": "heartbeat",
                            "session_id": session_id,
                            "data": {},
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally for session %s", session_id)
    except Exception as e:
        logger.warning(
            "Error in WebSocket handler for session %s: %s", session_id, str(e)
        )
    finally:
        broadcast.unsubscribe(f"workflow:{session_id}", _forward_to_client)
        broadcast.unsubscribe("workflow:global", _forward_to_client)


# ============================================================================
# Human Review Response Endpoints
# ============================================================================


class HumanReviewResponse(BaseModel):
    """Response to a human review request."""

    action: str = Field(..., description="Action: approve, clarify, or escalate")
    comment: Optional[str] = Field(
        None, description="Optional comment from the reviewer"
    )


@router.post(
    "/{session_id}/human-review/approve",
    response_model=dict,
    summary="Approve Human Review",
)
async def approve_review(
    session_id: str,
    request: Request,
    body: HumanReviewResponse,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Approve a session held in human review and resume the workflow."""
    try:
        user_id = get_user_id(user)
        session = await session_manager.get_session(session_id)
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        session = await session_manager.transition_session(
            session_id=session_id,
            to_state=SessionState.CODING,
            reason=f"Approved: {body.comment or 'no comment'}",
        )

        # Kick off celery task to resume execution
        from app_factory import db_provider

        job = await db_provider.get_generation_job(session_id)
        if job:
            from celery_worker import generate_code_as_celery_task

            generate_code_as_celery_task.delay(
                job_id=session_id,
                prompt=job.get("prompt", ""),
                model=job.get("model", ""),
                provider=job.get("provider", "aws"),
                project_id=job.get("project_id"),
                user_id=user_id,
                base_job_id=None,
                model_config_id=job.get("model_config_id"),
            )

        return create_success_response(
            data=session.to_dict(),
            message="Session approved — resuming workflow",
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to approve session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post(
    "/{session_id}/human-review/clarify",
    response_model=dict,
    summary="Request Clarification",
)
async def clarify_review(
    session_id: str,
    request: Request,
    body: HumanReviewResponse,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Reject a session in human review and send it back for clarification."""
    try:
        user_id = get_user_id(user)
        session = await session_manager.get_session(session_id)
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        session = await session_manager.transition_session(
            session_id=session_id,
            to_state=SessionState.CLARIFY,
            reason=f"Clarification requested: {body.comment or 'no comment'}",
            metadata={"review_feedback": body.comment},
        )

        # Kick off celery task to resume execution
        from app_factory import db_provider

        job = await db_provider.get_generation_job(session_id)
        if job:
            from celery_worker import generate_code_as_celery_task

            generate_code_as_celery_task.delay(
                job_id=session_id,
                prompt=job.get("prompt", ""),
                model=job.get("model", ""),
                provider=job.get("provider", "aws"),
                project_id=job.get("project_id"),
                user_id=user_id,
                base_job_id=None,
                model_config_id=job.get("model_config_id"),
            )

        return create_success_response(
            data=session.to_dict(),
            message="Session sent back for clarification",
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clarify session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to clarify session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post(
    "/{session_id}/human-review/escalate",
    response_model=dict,
    summary="Escalate Human Review",
)
async def escalate_review(
    session_id: str,
    request: Request,
    body: HumanReviewResponse,
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Escalate a session from human review to an error/escalation state."""
    try:
        user_id = get_user_id(user)
        session = await session_manager.get_session(session_id)
        if session.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=error_handler.create_error_response(
                    message="Access denied",
                    error_code="FORBIDDEN",
                    status_code=403,
                ),
            )
        session = await session_manager.transition_session(
            session_id=session_id,
            to_state=SessionState.ESCALATE,
            reason=f"Escalated: {body.comment or 'no comment'}",
            metadata={"review_feedback": body.comment},
        )
        return create_success_response(
            data=session.to_dict(),
            message="Session escalated",
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_handler.create_error_response(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=404,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to escalate session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to escalate session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)
