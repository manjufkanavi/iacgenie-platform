"""

Artifacts Router

API endpoints for artifact store operations.

Integrates with Keycloak authentication and tenant isolation.

"""

import logging

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Request

from pydantic import BaseModel, Field

from modules.artifact_store.artifact_persister import artifact_persister

from middleware.auth_middleware import verify_access_token, get_user_id

from middleware.error_handling import create_success_response, error_handler

logger = logging.getLogger(__name__)

# Create router

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])
# ============================================================================

# Request Models

# ============================================================================


class UploadArtifactRequest(BaseModel):
    """Request to upload an artifact."""

    session_id: str = Field(..., description="Session identifier")
    iteration_num: int = Field(..., ge=0, description="Iteration number")
    artifact_type: str = Field(..., description="Type (code, log, plan, output)")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field("application/octet-stream", description="MIME type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class GetArtifactRequest(BaseModel):
    """Request to get artifact information."""

    artifact_id: str = Field(..., description="Artifact ID")


class ListArtifactsRequest(BaseModel):
    """Request to list artifacts."""

    session_id: str = Field(..., description="Session identifier")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class DeleteArtifactRequest(BaseModel):
    """Request to delete an artifact."""

    artifact_id: str = Field(..., description="Artifact ID")


# ============================================================================

# Response Models

# ============================================================================


class ArtifactResponse(BaseModel):
    """Response model for artifact."""

    id: str = Field(..., description="Artifact ID")
    session_id: str = Field(..., description="Session ID")
    iteration_num: int = Field(..., description="Iteration number")
    type: str = Field(..., description="Artifact type")
    filename: str = Field(..., description="Original filename")
    storage_path: str = Field(..., description="MinIO storage path")
    url: str = Field(..., description="Download URL")
    size: Optional[int] = Field(None, description="File size in bytes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Artifact metadata")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")


class ArtifactsListResponse(BaseModel):
    """Response model for artifacts list."""

    artifacts: List[ArtifactResponse] = Field(..., description="List of artifacts")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


# ============================================================================

# API Endpoints

# ============================================================================


@router.post("/upload", response_model=dict, summary="Upload Artifact")
async def upload_artifact(
    request: Request,
    body: UploadArtifactRequest,
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Upload an artifact to MinIO with PostgreSQL metadata.
    **Authentication Required**: API token in Authorization header
    **Request Body**:
    ```json
    {
        "session_id": "session-uuid",
        "iteration_num": 0,
        "artifact_type": "code",
        "filename": "main.tf",
        "metadata": {"description": "Terraform configuration"}
    }
    ```
    **Response**:
    ```json
    {
        "success": true,
        "data": {
            "storage_path": "sessions/session-uuid/iter_0/main.tf",
            "url": "http://localhost:9000/sessions/session-uuid/iter_0/main.tf",
            "artifact_id": "artifact-uuid",
            "expires_at": "2026-03-19T00:00:00Z"
        }
    }
    ```
    """
    try:
        # Get user ID from authenticated token
        get_user_id(user)
        # Get tenant ID
        tenant_id = getattr(request.state, "tenant_id", None)
        # Upload artifact
        result = await artifact_persister.upload_artifact(
            session_id=body.session_id,
            iteration_num=body.iteration_num,
            artifact_type=body.artifact_type,
            filename=body.filename,
            content=b"",
            content_type=body.content_type,
            metadata=body.metadata,
            tenant_id=tenant_id,
        )
        return create_success_response(
            data=result, message="Artifact uploaded successfully"
        )
    except ValueError as e:
        error_response = error_handler.create_error_response(
            message=str(e), error_code="VALIDATION_ERROR", status_code=400
        )
        raise HTTPException(status_code=400, detail=error_response)
    except Exception as e:
        logger.error(f"Failed to upload artifact: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to upload artifact",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/{artifact_id}", response_model=dict, summary="Get Artifact")
async def get_artifact(
    artifact_id: str, request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Get artifact information by ID.
    **Authentication Required**: API token in Authorization header
    """
    try:
        # Get user ID from authenticated token
        get_user_id(user)
        # Get tenant ID
        tenant_id = getattr(request.state, "tenant_id", None)
        # Get artifact
        artifact_data = await artifact_persister.get_artifact(
            artifact_id=artifact_id, tenant_id=tenant_id
        )
        if not artifact_data:
            error_response = error_handler.create_error_response(
                message="Artifact not found",
                error_code="ARTIFACT_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response)
        return create_success_response(
            data=artifact_data, message="Artifact retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get artifact: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get artifact",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("", response_model=dict, summary="List Artifacts")
async def list_artifacts(
    request: Request,
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    List artifacts for a session.
    **Authentication Required**: API token in Authorization header
    **Query Parameters**:
    - session_id: Session identifier
    - limit: Maximum number to return (default: 100)
    - offset: Offset for pagination (default: 0)
    """
    try:
        # Get user ID from authenticated token
        get_user_id(user)
        # Get tenant ID
        tenant_id = getattr(request.state, "tenant_id", None)
        # List artifacts
        artifacts = await artifact_persister.list_artifacts(
            session_id=session_id, tenant_id=tenant_id, limit=limit, offset=offset
        )
        return create_success_response(
            data={
                "artifacts": artifacts,
                "total": len(artifacts),
                "limit": limit,
                "offset": offset,
            },
            message="Artifacts retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list artifacts: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to list artifacts",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.delete("/{artifact_id}", response_model=dict, summary="Delete Artifact")
async def delete_artifact(
    artifact_id: str, request: Request, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Delete an artifact by ID.
    **Authentication Required**: API token in Authorization header
    """
    try:
        # Get user ID from authenticated token
        get_user_id(user)
        # Get tenant ID
        tenant_id = getattr(request.state, "tenant_id", None)
        # Delete artifact
        success = await artifact_persister.delete_artifact(
            artifact_id=artifact_id, tenant_id=tenant_id
        )
        if not success:
            error_response = error_handler.create_error_response(
                message="Artifact not found",
                error_code="ARTIFACT_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response)
        return create_success_response(data={}, message="Artifact deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete artifact: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to delete artifact",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)
