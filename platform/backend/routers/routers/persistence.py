"""

Persistence API Router

This router provides HTTP endpoints for persistence operations (session states,

iterations, artifacts, user repo configs, idempotency).

Endpoints are prefixed with `/api/persistence` and require authentication.

"""

import logging

from fastapi import APIRouter, HTTPException, Depends, Request

from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Import persistence adapter

from db.adapters.persistence_adapter import persistence_adapter

# Import authentication middleware

from middleware.auth_middleware import verify_access_token, get_user_id

# Import response utilities

from middleware.error_handling import create_success_response, error_handler

# Create router

router = APIRouter(
    prefix="/api/persistence",
    tags=["Persistence"],
    responses={404: {"description": "Not found"}},
)
# ============================================================================

# Session State Endpoints

# ============================================================================


@router.post("/sessions", response_model=dict, summary="Create Session")
async def create_session(
    request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Create a new session state record.
    **Authentication Required**: API token in Authorization header
    **Request Body**:
    ```json
    {
        "build_id": "unique-build-id",
        "user_id": "user-uuid",
        "prompt": "Generate a Terraform script for AWS EC2",
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
            "build_id": "unique-build-id",
            "user_id": "user-uuid",
            "status": "CREATED"
        }
    }
    ```
    """
    try:
        # Get user ID from token
        user_id = get_user_id(user)
        # Parse request body
        body = await request.json()
        build_id = body.get("build_id")
        prompt = body.get("prompt")
        git_repo_url = body.get("git_repo_url")
        git_branch = body.get("git_branch")
        ci_provider = body.get("ci_provider")
        ci_inputs = body.get("ci_inputs", {})
        if not build_id:
            raise HTTPException(
                status_code=400,
                detail=error_handler.create_error_response(
                    message="build_id is required",
                    error_code="MISSING_FIELD",
                    status_code=400,
                ),
            )
        # Create session
        session = persistence_adapter.create_session(
            build_id=build_id,
            user_id=user_id,
            prompt=prompt,
            git_repo_url=git_repo_url,
            git_branch=git_branch,
            ci_provider=ci_provider,
            ci_inputs=ci_inputs,
        )
        if not session:
            raise HTTPException(
                status_code=500,
                detail=error_handler.create_error_response(
                    message="Failed to create session",
                    error_code="SESSION_CREATION_FAILED",
                    status_code=500,
                ),
            )
        return create_success_response(
            data=session, message="Session created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to create session",
            error_code="INTERNAL_ERROR",
            status_code=500,
            details={"original_error": str(e)},
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/sessions/{session_id}", response_model=dict, summary="Get Session")
async def get_session(
    session_id: str, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Get session state by ID.
    **Authentication Required**: API token in Authorization header
    """
    try:
        session = persistence_adapter.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=error_handler.create_error_response(
                    message="Session not found",
                    error_code="SESSION_NOT_FOUND",
                    status_code=404,
                ),
            )
        return create_success_response(
            data=session, message="Session retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get session",
            error_code="INTERNAL_ERROR",
            status_code=500,
            details={"original_error": str(e)},
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.put("/sessions/{session_id}", response_model=dict, summary="Update Session")
async def update_session(
    session_id: str, request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Update session state.
    **Authentication Required**: API token in Authorization header
    **Request Body** (all fields optional):
    ```json
    {
        "status": "CODING",
        "current_iteration": 1,
        "git_repo_url": "https://github.com/user/repo",
        "git_branch": "main",
        "git_commit_sha": "abc123",
        "ci_provider": "github",
        "ci_run_id": "run-123",
        "deployment_status": "pending"
    }
    ```
    """
    try:
        body = await request.json()
        session = persistence_adapter.update_session_status(
            session_id=session_id,
            status=body.get("status"),
            current_iteration=body.get("current_iteration"),
            git_repo_url=body.get("git_repo_url"),
            git_branch=body.get("git_branch"),
            git_commit_sha=body.get("git_commit_sha"),
            ci_provider=body.get("ci_provider"),
            ci_run_id=body.get("ci_run_id"),
            deployment_status=body.get("deployment_status"),
        )
        if not session:
            raise HTTPException(
                status_code=404,
                detail=error_handler.create_error_response(
                    message="Session not found",
                    error_code="SESSION_NOT_FOUND",
                    status_code=404,
                ),
            )
        return create_success_response(
            data=session, message="Session updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to update session",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/sessions", response_model=dict, summary="List Sessions")
async def list_sessions(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    List session states with optional filters.
    **Authentication Required**: API token in Authorization header
    **Query Parameters**:
    - user_id: Filter by user ID
    - status: Filter by session status
    - limit: Number of results (default: 100)
    - offset: Pagination offset (default: 0)
    """
    try:
        # If user_id not provided, use authenticated user's ID
        if not user_id:
            user_id = get_user_id(user)
        sessions = persistence_adapter.list_sessions(
            user_id=user_id, status=status, limit=limit, offset=offset
        )
        return create_success_response(
            data={"sessions": sessions}, message="Sessions retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to list sessions",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# ============================================================================

# Iteration Endpoints

# ============================================================================


@router.post(
    "/sessions/{session_id}/iterations", response_model=dict, summary="Create Iteration"
)
async def create_iteration(
    session_id: str, request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Create a new iteration record.
    **Authentication Required**: API token in Authorization header
    **Request Body**:
    ```json
    {
        "iteration_num": 0,
        "error": null,
        "artifacts": []
    }
    ```
    """
    try:
        body = await request.json()
        iteration = persistence_adapter.create_iteration(
            session_id=session_id,
            iteration_num=body.get("iteration_num", 0),
            error=body.get("error"),
            artifacts=body.get("artifacts"),
        )
        if not iteration:
            raise HTTPException(
                status_code=500,
                detail=error_handler.create_error_response(
                    message="Failed to create iteration",
                    error_code="ITERATION_CREATION_FAILED",
                    status_code=500,
                ),
            )
        return create_success_response(
            data=iteration, message="Iteration created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create iteration: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to create iteration",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get(
    "/sessions/{session_id}/iterations", response_model=dict, summary="List Iterations"
)
async def list_iterations(
    session_id: str, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    List iterations for a session.
    **Authentication Required**: API token in Authorization header
    """
    try:
        iterations = persistence_adapter.list_iterations(session_id)
        return create_success_response(
            data={"iterations": iterations}, message="Iterations retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to list iterations: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to list iterations",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# ============================================================================

# Artifact Endpoints

# ============================================================================


@router.post(
    "/sessions/{session_id}/artifacts", response_model=dict, summary="Create Artifact"
)
async def create_artifact(
    session_id: str, request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Create a new artifact record.
    **Authentication Required**: API token in Authorization header
    **Request Body**:
    ```json
    {
        "iteration_num": 0,
        "artifact_type": "code",
        "storage_path": "/path/to/file",
        "content_type": "text/plain"
    }
    ```
    **Artifact Types**: code, log, plan, output
    """
    try:
        body = await request.json()
        artifact_type = body.get("artifact_type")
        storage_path = body.get("storage_path")
        content_type = body.get("content_type")
        if not all([artifact_type, storage_path, content_type]):
            raise HTTPException(
                status_code=400,
                detail=error_handler.create_error_response(
                    message="artifact_type, storage_path, and content_type are required",
                    error_code="MISSING_FIELD",
                    status_code=400,
                ),
            )
        artifact = persistence_adapter.create_artifact(
            session_id=session_id,
            iteration_num=body.get("iteration_num", 0),
            artifact_type=artifact_type,
            storage_path=storage_path,
            content_type=content_type,
        )
        if not artifact:
            raise HTTPException(
                status_code=500,
                detail=error_handler.create_error_response(
                    message="Failed to create artifact",
                    error_code="ARTIFACT_CREATION_FAILED",
                    status_code=500,
                ),
            )
        return create_success_response(
            data=artifact, message="Artifact created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create artifact: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to create artifact",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get(
    "/sessions/{session_id}/artifacts", response_model=dict, summary="List Artifacts"
)
async def list_artifacts(
    session_id: str,
    iteration_num: Optional[int] = None,
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    List artifacts for a session.
    **Authentication Required**: API token in Authorization header
    **Query Parameters**:
    - iteration_num: Filter by iteration number (optional)
    """
    try:
        artifacts = persistence_adapter.list_artifacts(
            session_id=session_id, iteration_num=iteration_num
        )
        return create_success_response(
            data={"artifacts": artifacts}, message="Artifacts retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to list artifacts: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to list artifacts",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# ============================================================================

# User Repo Config Endpoints

# ============================================================================


@router.post(
    "/user-repo-configs", response_model=dict, summary="Create User Repo Config"
)
async def create_user_repo_config(
    request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Create a new user repository configuration.
    **Authentication Required**: API token in Authorization header
    **Request Body**:
    ```json
    {
        "repo_url": "https://github.com/user/repo",
        "default_branch": "main",
        "git_provider": "github",
        "credentials_ref": "vault/path/to/creds",
        "ci_provider": "github",
        "ci_workflow_id": ".github/workflows/deploy.yml"
    }
    ```
    """
    try:
        body = await request.json()
        user_id = get_user_id(user)
        config = persistence_adapter.create_user_repo_config(
            user_id=user_id,
            repo_url=body.get("repo_url"),
            default_branch=body.get("default_branch", "main"),
            git_provider=body.get("git_provider", "github"),
            credentials_ref=body.get("credentials_ref"),
            ci_provider=body.get("ci_provider"),
            ci_workflow_id=body.get("ci_workflow_id"),
            ci_inputs=body.get("ci_inputs", {}),
        )
        if not config:
            raise HTTPException(
                status_code=500,
                detail=error_handler.create_error_response(
                    message="Failed to create user repo config",
                    error_code="CONFIG_CREATION_FAILED",
                    status_code=500,
                ),
            )
        return create_success_response(
            data=config, message="User repo config created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user repo config: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to create user repo config",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get(
    "/user-repo-configs/{repo_url}", response_model=dict, summary="Get User Repo Config"
)
async def get_user_repo_config(
    repo_url: str, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Get user repository configuration by repo URL.
    **Authentication Required**: API token in Authorization header
    """
    try:
        user_id = get_user_id(user)
        config = persistence_adapter.get_user_repo_config(
            user_id=user_id, repo_url=repo_url
        )
        if not config:
            raise HTTPException(
                status_code=404,
                detail=error_handler.create_error_response(
                    message="User repo config not found",
                    error_code="CONFIG_NOT_FOUND",
                    status_code=404,
                ),
            )
        return create_success_response(
            data=config, message="User repo config retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user repo config: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get user repo config",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/user-repo-configs", response_model=dict, summary="List User Repo Configs")
async def list_user_repo_configs(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    List all repository configurations for the authenticated user.
    **Authentication Required**: API token in Authorization header
    """
    try:
        user_id = get_user_id(user)
        configs = persistence_adapter.list_user_repo_configs(user_id=user_id)
        return create_success_response(
            data={"configs": configs},
            message="User repo configs retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list user repo configs: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to list user repo configs",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# ============================================================================

# Idempotency Endpoints

# ============================================================================


@router.post("/idempotency/check", response_model=dict, summary="Check Idempotency")
async def check_idempotency(
    request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Check if an idempotency key exists and return cached result.
    **Authentication Required**: API token in Authorization header
    **Request Body**:
    ```json
    {
        "idempotency_key": "unique-key-for-request"
    }
    ```
    """
    try:
        body = await request.json()
        idempotency_key = body.get("idempotency_key")
        if not idempotency_key:
            raise HTTPException(
                status_code=400,
                detail=error_handler.create_error_response(
                    message="idempotency_key is required",
                    error_code="MISSING_FIELD",
                    status_code=400,
                ),
            )
        result = persistence_adapter.check_idempotency(idempotency_key)
        return create_success_response(
            data=result or {}, message="Idempotency check completed"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check idempotency: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to check idempotency",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post(
    "/idempotency/record", response_model=dict, summary="Create Idempotency Record"
)
async def create_idempotency_record(
    request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Create a new idempotency record with TTL.
    **Authentication Required**: API token in Authorization header
    **Request Body**:
    ```json
    {
        "idempotency_key": "unique-key-for-request",
        "result": {"status": "success"},
        "ttl_seconds": 3600
    }
    ```
    """
    try:
        body = await request.json()
        idempotency_key = body.get("idempotency_key")
        result_data = body.get("result", {})
        ttl_seconds = body.get("ttl_seconds", 3600)
        if not idempotency_key:
            raise HTTPException(
                status_code=400,
                detail=error_handler.create_error_response(
                    message="idempotency_key is required",
                    error_code="MISSING_FIELD",
                    status_code=400,
                ),
            )
        record = persistence_adapter.create_idempotency_record(
            idempotency_key=idempotency_key, result=result_data, ttl_seconds=ttl_seconds
        )
        return create_success_response(
            data=record or {}, message="Idempotency record created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create idempotency record: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to create idempotency record",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# ============================================================================

# Health Check Endpoint

# ============================================================================


@router.get("/health", response_model=dict, summary="Persistence Health Check")
async def persistence_health_check() -> Dict[str, Any]:
    """
    Check if the persistence layer is healthy.
    **No Authentication Required**: Public health check endpoint
    """
    try:
        is_healthy = persistence_adapter.is_initialized
        return create_success_response(
            data={
                "status": "healthy" if is_healthy else "unhealthy",
                "initialized": is_healthy,
            },
            message="Persistence health check completed",
        )
    except Exception as e:
        logger.error(f"Failed to check persistence health: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to check persistence health",
            error_code="HEALTH_CHECK_FAILED",
            status_code=503,
        )
        raise HTTPException(status_code=503, detail=error_response)
