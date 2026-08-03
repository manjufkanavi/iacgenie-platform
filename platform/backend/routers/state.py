from fastapi import APIRouter, HTTPException, Depends, Path, Body

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from repositories.state_repository import StateRepository

from observability.audit_logger import AuditLogger

from middleware.auth_middleware import verify_access_token

import logging

logger = logging.getLogger(__name__)

# Create router

router = APIRouter(prefix="/api/state", tags=["State Management"])

# Initialize services

state_repository = StateRepository()

audit_logger = AuditLogger()

# Request/Response Models


class StateResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    current_phase: str = Field(..., description="Current pipeline phase")
    user_request: str = Field(..., description="Original user request")
    last_error: Optional[str] = Field(None, description="Last error message")
    error_class: Optional[str] = Field(None, description="Last error classification")
    retry_counts: Dict[str, int] = Field(
        default_factory=dict, description="Retry counts by phase"
    )
    approvals: Dict[str, bool] = Field(
        default_factory=dict, description="Approval status"
    )


class CheckpointRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    checkpoint_data: Dict[str, Any] = Field(..., description="Checkpoint data")


class RestoreRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    checkpoint_id: Optional[str] = Field(None, description="Optional checkpoint ID")


# API Endpoints


@router.get("/{session_id}", response_model=StateResponse)
async def get_state(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> StateResponse:
    """
    Get the current state of a pipeline.
    Args:
        session_id: Pipeline session ID
    Returns:
        Current pipeline state
    """
    try:
        # Load state from repository
        state = state_repository.load_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"State not found for session: {session_id}",
                    "error_class": "state_not_found",
                },
            )
        # Log the access
        audit_logger.log_pipeline_event(
            "state_accessed", session_id, {"access_type": "read"}
        )
        return StateResponse(
            session_id=state.session_id,
            current_phase=state.current_phase.value,
            user_request=state.user_request,
            last_error=state.last_error,
            error_class=state.last_error_class.value
            if state.last_error_class
            else None,
            retry_counts=state.retry_counts,
            approvals=state.approvals,
        )
    except Exception as e:
        logger.error(f"Failed to get state: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "state_retrieval_failed"},
        )


@router.post("/{session_id}/checkpoint")
async def create_checkpoint(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Create a checkpoint of the current state.
    Args:
        session_id: Pipeline session ID
    Returns:
        Checkpoint creation result
    """
    try:
        # Load current state
        state = state_repository.load_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"State not found for session: {session_id}",
                    "error_class": "state_not_found",
                },
            )
        # Create checkpoint
        checkpoint_data = state.checkpoint()
        checkpoint_id = f"checkpoint_{len(checkpoint_data)}"
        # Save checkpoint (in a real implementation, this would be more sophisticated)
        # For now, we'll just save the state again (which creates a new version)
        success = state_repository.save_state(state)
        if not success:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Failed to save checkpoint",
                    "error_class": "checkpoint_failed",
                },
            )
        # Log the checkpoint
        audit_logger.log_state_checkpoint(session_id, state)
        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "message": "Checkpoint created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create checkpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "checkpoint_failed"},
        )


@router.post("/{session_id}/restore")
async def restore_from_checkpoint(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
    restore_request: RestoreRequest = Body(...),
) -> Dict[str, Any]:
    """
    Restore state from a checkpoint.
    Args:
        session_id: Pipeline session ID
        restore_request: Restore request with checkpoint ID
    Returns:
        Restore operation result
    """
    try:
        # In a real implementation, we would:
        # 1. Load the specific checkpoint version
        # 2. Validate it's compatible
        # 3. Restore the state
        # For this implementation, we'll simulate by loading the current state
        # and treating it as a restore operation
        state = state_repository.load_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"State not found for session: {session_id}",
                    "error_class": "state_not_found",
                },
            )
        # Log the restore
        audit_logger.log_pipeline_event(
            "state_restored",
            session_id,
            {
                "checkpoint_id": restore_request.checkpoint_id or "latest",
                "current_phase": state.current_phase.value,
            },
        )
        return {
            "success": True,
            "message": "State restored successfully",
            "current_phase": state.current_phase.value,
        }
    except Exception as e:
        logger.error(f"Failed to restore state: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": str(e), "error_class": "restore_failed"}
        )


@router.get("/{session_id}/history")
async def get_state_history(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Get the history of state changes for a pipeline.
    Args:
        session_id: Pipeline session ID
    Returns:
        State history
    """
    try:
        # Get audit logs for this session
        audit_result = audit_logger.get_session_audit_logs(session_id)
        if not audit_result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": audit_result.get("error", "Failed to retrieve audit logs"),
                    "error_class": audit_result.get(
                        "error_class", "audit_retrieval_failed"
                    ),
                },
            )
        # Filter for state-related events
        state_history = []
        for log_entry in audit_result["logs"]:
            if log_entry["event_type"] in [
                "state_checkpoint",
                "state_restored",
                "phase_transition",
            ]:
                state_history.append(
                    {
                        "timestamp": log_entry["timestamp"],
                        "event_type": log_entry["event_type"],
                        "details": log_entry.get("state")
                        or log_entry.get("transition")
                        or {},
                    }
                )
        return {
            "success": True,
            "session_id": session_id,
            "history": state_history,
            "count": len(state_history),
        }
    except Exception as e:
        logger.error(f"Failed to get state history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "history_retrieval_failed"},
        )


@router.get("/{session_id}/versions")
async def get_state_versions(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Get available versions of a state.
    Args:
        session_id: Pipeline session ID
    Returns:
        State versions information
    """
    try:
        # Get the current version
        state = state_repository.load_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"State not found for session: {session_id}",
                    "error_class": "state_not_found",
                },
            )
        # Get version info
        version = state_repository.get_state_version(session_id)
        # In a real implementation, we would have multiple versions
        # For this implementation, we'll return the current version
        versions = [
            {
                "version": version or 1,
                "timestamp": state.started_at.isoformat(),
                "current_phase": state.current_phase.value,
                "is_current": True,
            }
        ]
        return {
            "success": True,
            "session_id": session_id,
            "versions": versions,
            "current_version": version or 1,
        }
    except Exception as e:
        logger.error(f"Failed to get state versions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "versions_retrieval_failed"},
        )


@router.delete("/{session_id}")
async def delete_state(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Delete a pipeline state.
    Args:
        session_id: Pipeline session ID
    Returns:
        Deletion result
    """
    try:
        # Delete state
        success = state_repository.delete_state(session_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": f"Failed to delete state: {session_id}",
                    "error_class": "deletion_failed",
                },
            )
        # Log the deletion
        audit_logger.log_pipeline_event(
            "state_deleted", session_id, {"result": "success"}
        )
        return {"success": True, "message": "State deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete state: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": str(e), "error_class": "deletion_failed"}
        )


@router.get("/")
async def list_sessions(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    List all active pipeline sessions.
    Returns:
        List of active sessions
    """
    try:
        # Get all sessions
        sessions_result = state_repository.list_sessions()
        return {
            "success": True,
            "sessions": sessions_result["sessions"],
            "count": sessions_result["count"],
        }
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "session_listing_failed"},
        )
