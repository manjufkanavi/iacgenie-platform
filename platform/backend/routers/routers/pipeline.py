from fastapi import APIRouter, HTTPException, Query, Depends, Path, Body

from typing import Any, Dict, Optional, List, cast

from pydantic import BaseModel, Field

from uuid import UUID

import logging
from datetime import datetime
import subprocess
import json
import os
from modules.agent_executor.utils import create_session_workspace

logger = logging.getLogger(__name__)

# Existing imports

from pipeline.factory import PipelineFactory

from human_loop.interrupt_manager import InterruptManager

from human_loop.approval_service import ApprovalService

from human_loop.escalation_handler import EscalationHandler

from security.access_control import PipelineAccessControl

from observability.audit_logger import AuditLogger

from observability.pipeline_monitor import PipelineMonitor

from observability.tracing_service import TracingService

from models.error_classes import ErrorClass

# New imports for enhanced features

from repositories.pipeline_repository import PipelineRepository

from middleware.auth_middleware import verify_access_token

# Create router

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline Management"])

# Initialize services

pipeline_factory = PipelineFactory()

interrupt_manager = InterruptManager()

approval_service = ApprovalService()

escalation_handler = EscalationHandler()

access_control = PipelineAccessControl()

audit_logger = AuditLogger()

pipeline_monitor = PipelineMonitor()

tracing_service = TracingService()

pipeline_repo = PipelineRepository()

# Request/Response Models


class StartPipelineRequest(BaseModel):
    user_request: str = Field(
        ..., min_length=1, description="User's infrastructure request"
    )
    name: Optional[str] = Field(None, description="Optional pipeline name")
    workspace_id: Optional[str] = Field(None, description="Optional workspace ID")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    deploymentMode: Optional[str] = Field(None, description="Optional deployment mode")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Optional pipeline configuration"
    )


class CreatePipelineRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    workspace_id: Optional[UUID] = None
    user_request: str = Field(..., min_length=1)


class PipelineListItem(BaseModel):
    session_id: str
    name: str
    phase: str
    status: str
    current_phase_progress: int
    retry_count: int
    error_count: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class PipelineDetailResponse(BaseModel):
    session_id: str
    name: str
    description: Optional[str] = None
    phase: str
    status: str
    current_phase_progress: int
    retry_count: int
    max_retries: int
    error_count: int
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_by: Optional[str] = None
    phase_history: List[Dict[str, Any]] = []
    logs: List[Dict[str, Any]] = []


class PipelineUpdateResponse(BaseModel):
    action: str
    new_status: str
    message: str


class ListPipelinesResponse(BaseModel):
    pipelines: List[PipelineListItem]
    total: int
    limit: int
    offset: int


class PipelineResponse(BaseModel):
    session_id: str = Field(..., description="Pipeline session ID")
    status: str = Field(..., description="Pipeline status")
    current_phase: Optional[str] = Field(None, description="Current pipeline phase")
    started_at: str = Field(..., description="Pipeline start timestamp")
    completed_at: Optional[str] = Field(
        None, description="Pipeline completion timestamp"
    )


class CostEstimateResponse(BaseModel):
    success: bool = Field(True, description="Success status")
    estimated_cost_usd: float = Field(..., description="Estimated cost in USD")
    breakdown: Optional[Dict[str, Any]] = Field(None, description="Cost breakdown")
    currency: str = Field("USD", description="Currency code")


class PipelineStatusResponse(BaseModel):
    session_id: str = Field(..., description="Pipeline session ID")
    status: str = Field(..., description="Pipeline status")
    current_phase: str = Field(..., description="Current pipeline phase")
    last_error: Optional[str] = Field(None, description="Last error message")
    error_class: Optional[str] = Field(None, description="Last error classification")
    retry_counts: Dict[str, int] = Field(
        default_factory=dict, description="Retry counts by phase"
    )
    approvals: Dict[str, bool] = Field(
        default_factory=dict, description="Approval status"
    )


class InterruptRequest(BaseModel):
    error_class: str = Field(..., description="Classification of the error")
    context: Dict[str, Any] = Field(
        ..., description="Additional context about the interrupt"
    )


class InterruptResponse(BaseModel):
    interrupt_id: str = Field(..., description="Interrupt ID")
    session_id: str = Field(..., description="Pipeline session ID")
    status: str = Field(..., description="Interrupt status")


class ApprovalRequest(BaseModel):
    approval_type: str = Field(..., description="Type of approval")
    context: Dict[str, Any] = Field(
        ..., description="Additional context for the approval"
    )


class ApprovalResponse(BaseModel):
    approval_token: str = Field(..., description="Approval token")
    approval_status: str = Field(..., description="Approval status")


class HumanInterventionRequest(BaseModel):
    resolution_type: str = Field(..., description="Type of resolution")
    resolution_data: Dict[str, Any] = Field(..., description="Resolution data")


# API Endpoints


@router.get("/", response_model=ListPipelinesResponse)
async def list_pipelines(
    user: Any = Depends(verify_access_token),
    tenant_id: UUID = Query(..., description="Tenant ID for filtering"),
    limit: int = Query(50, ge=1, le=100, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
) -> ListPipelinesResponse:
    """List pipelines with filtering and pagination."""
    try:
        pipelines = pipeline_repo.list_pipelines(
            tenant_id=tenant_id, limit=limit, offset=offset, status_filter=status_filter
        )
        total = pipeline_repo.count_pipelines(
            tenant_id=tenant_id, status_filter=status_filter
        )
        items = [
            PipelineListItem(
                session_id=cast(str, p.session_id),
                name=cast(str, p.name),
                phase=cast(str, p.phase),
                status=cast(str, p.status),
                current_phase_progress=cast(int, p.current_phase_progress),
                retry_count=cast(int, p.retry_count),
                error_count=cast(int, p.error_count),
                created_at=p.created_at.isoformat() if p.created_at else "",
                started_at=p.started_at.isoformat() if p.started_at else None,
                completed_at=p.completed_at.isoformat() if p.completed_at else None,
            )
            for p in pipelines
        ]
        return ListPipelinesResponse(
            pipelines=items, total=total, limit=limit, offset=offset
        )
    except Exception as e:
        logger.error(f"Failed to list pipelines: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e), "code": 500})


@router.get("/{session_id}/detail", response_model=PipelineDetailResponse)
async def get_pipeline_detail(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> PipelineDetailResponse:
    """Get full pipeline detail including phase history and logs."""
    try:
        pipeline = pipeline_repo.get_pipeline(session_id)
        if not pipeline:
            raise HTTPException(
                status_code=404, detail={"error": "Pipeline not found", "code": 404}
            )
        pipeline_id = cast(Any, pipeline.id)
        phase_history = pipeline_repo.get_phase_history(pipeline_id)
        logs = pipeline_repo.get_logs(pipeline_id, limit=100)
        return PipelineDetailResponse(
            session_id=cast(str, pipeline.session_id),
            name=cast(str, pipeline.name),
            description=cast(Optional[str], pipeline.description),
            phase=cast(str, pipeline.phase),
            status=cast(str, pipeline.status),
            current_phase_progress=cast(int, pipeline.current_phase_progress),
            retry_count=cast(int, pipeline.retry_count),
            max_retries=cast(int, pipeline.max_retries),
            error_count=cast(int, pipeline.error_count),
            error_message=cast(Optional[str], pipeline.error_message),
            created_at=pipeline.created_at.isoformat() if pipeline.created_at else "",
            started_at=pipeline.started_at.isoformat() if pipeline.started_at else None,
            completed_at=pipeline.completed_at.isoformat()
            if pipeline.completed_at
            else None,
            created_by=cast(Optional[str], pipeline.created_by),
            phase_history=[
                {
                    "phase": cast(str, h.phase),
                    "status": cast(str, h.status),
                    "duration_seconds": cast(Optional[int], h.duration_seconds),
                    "started_at": h.started_at.isoformat() if h.started_at else None,
                    "completed_at": h.completed_at.isoformat()
                    if h.completed_at
                    else None,
                    "details": h.details,
                    "retry_number": cast(int, h.retry_number),
                }
                for h in phase_history
            ],
            logs=[
                {
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "phase": cast(Optional[str], log.phase),
                    "level": cast(str, log.level),
                    "message": cast(str, log.message),
                    "meta_data": log.meta_data,
                }
                for log in logs
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline detail: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e), "code": 500})


@router.delete("/{session_id}")
async def delete_pipeline(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """Soft-delete a pipeline."""
    try:
        deleted = pipeline_repo.delete_pipeline(session_id)
        if not deleted:
            raise HTTPException(
                status_code=404, detail={"error": "Pipeline not found", "code": 404}
            )
        return {"success": True, "message": "Pipeline deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e), "code": 500})


@router.post("/start", response_model=PipelineResponse)
async def start_pipeline(
    user: Any = Depends(verify_access_token),
    pipeline_request: StartPipelineRequest = Body(...),
    user_id: Optional[
        str
    ] = None,  # Would come from auth middleware in real implementation
) -> PipelineResponse:
    """
    Start a new pipeline execution.
    Args:
        pipeline_request: Pipeline start request
        user_id: User ID from authentication
    Returns:
        Pipeline response with session details
    """
    try:
        # Check permissions (in real implementation)
        # permission_result = access_control.check_pipeline_access(
        #     user_id or "anonymous", pipeline_request.session_id or "", "start"
        # )
        # if not permission_result.get("permission_granted", False):
        #     raise HTTPException(status_code=403, detail="Permission denied")
        config = pipeline_request.config or {}
        if pipeline_request.deploymentMode:
            config["deploymentMode"] = pipeline_request.deploymentMode
        if pipeline_request.name:
            config["name"] = pipeline_request.name
        if pipeline_request.workspace_id:
            config["workspace_id"] = pipeline_request.workspace_id

        # Create pipeline
        pipeline = pipeline_factory.create_pipeline(config)
        # Start pipeline
        result = await pipeline.start_pipeline(
            pipeline_request.user_request, pipeline_request.session_id
        )
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "error_class": result.get("error_class", "unknown"),
                },
            )
        # Log the event
        audit_logger.log_pipeline_event(
            "pipeline_started",
            result["session_id"],
            {
                "user_request": pipeline_request.user_request,
                "initial_phase": "clarify",
                "user_id": user_id or "anonymous",
            },
        )
        # Start monitoring
        pipeline_monitor.start_pipeline_monitoring(result["session_id"])
        return PipelineResponse(
            session_id=result["session_id"],
            status="running",
            current_phase="clarify",
            started_at=result.get("started_at", datetime.utcnow().isoformat()),
            completed_at=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start pipeline: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "pipeline_start_failed"},
        )


@router.get("/{session_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> PipelineStatusResponse:
    """
    Get the status of a pipeline.
    Args:
        session_id: Pipeline session ID
    Returns:
        Pipeline status response
    """
    try:
        # Create pipeline instance
        pipeline = pipeline_factory.create_pipeline()
        # Get status
        status_result = await pipeline.get_pipeline_status()
        if not status_result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail={
                    "error": status_result.get("error", "Pipeline not found"),
                    "error_class": status_result.get("error_class", "not_found"),
                },
            )
        return PipelineStatusResponse(
            session_id=session_id,
            status=status_result["status"],
            current_phase=status_result["current_phase"],
            last_error=status_result.get("last_error"),
            error_class=status_result.get("error_class"),
            retry_counts=status_result.get("retry_counts", {}),
            approvals=status_result.get("approvals", {}),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "status_retrieval_failed"},
        )


@router.post("/{session_id}/resume")
async def resume_pipeline(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Resume a paused pipeline.
    Args:
        session_id: Pipeline session ID
    Returns:
        Resume operation result
    """
    try:
        # Create pipeline instance
        pipeline = pipeline_factory.create_pipeline()
        # Resume pipeline
        result = await pipeline.resume_pipeline(session_id)
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "error_class": result.get("error_class", "unknown"),
                },
            )
        # Log the event
        audit_logger.log_pipeline_event(
            "pipeline_resumed", session_id, {"result": "success"}
        )
        return {
            "success": True,
            "message": "Pipeline resumed successfully",
            "next_phase": result.get("next_phase"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume pipeline: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "pipeline_resume_failed"},
        )


@router.post("/{session_id}/stop")
async def stop_pipeline(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Stop a running pipeline.
    Args:
        session_id: Pipeline session ID
    Returns:
        Stop operation result
    """
    try:
        # Create pipeline instance
        pipeline = pipeline_factory.create_pipeline()
        # Stop pipeline
        result = await pipeline.stop_pipeline()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "error_class": result.get("error_class", "unknown"),
                },
            )
        # Log the event
        audit_logger.log_pipeline_event(
            "pipeline_stopped", session_id, {"result": "success"}
        )
        return {"success": True, "message": "Pipeline stopped successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop pipeline: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "pipeline_stop_failed"},
        )


@router.post("/{session_id}/interrupt")
async def trigger_interrupt(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
    interrupt_request: InterruptRequest = Body(...),
) -> InterruptResponse:
    """
    Trigger an interrupt for human intervention.
    Args:
        session_id: Pipeline session ID
        interrupt_request: Interrupt request details
    Returns:
        Interrupt response
    """
    try:
        # Trigger interrupt
        result = await interrupt_manager.trigger_interrupt(
            session_id,
            ErrorClass(interrupt_request.error_class),
            interrupt_request.context,
        )
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "error_class": result.get("error_class", "unknown"),
                },
            )
        # Log the event
        audit_logger.log_human_intervention(
            session_id,
            "interrupt_triggered",
            {
                "interrupt_id": result["interrupt_id"],
                "error_class": interrupt_request.error_class,
                "context": interrupt_request.context,
            },
        )
        return InterruptResponse(
            interrupt_id=result["interrupt_id"],
            session_id=session_id,
            status="triggered",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger interrupt: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": str(e), "error_class": "interrupt_failed"}
        )


@router.post("/{session_id}/approve")
async def request_approval(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
    approval_request: ApprovalRequest = Body(...),
) -> ApprovalResponse:
    """
    Request approval for a pipeline operation.
    Args:
        session_id: Pipeline session ID
        approval_request: Approval request details
    Returns:
        Approval response
    """
    try:
        # Request approval
        result = await approval_service.request_approval(
            session_id, approval_request.approval_type, approval_request.context
        )
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "error_class": result.get("error_class", "unknown"),
                },
            )
        # Log the event
        audit_logger.log_approval_event(
            session_id,
            approval_request.approval_type,
            "requested",
            {
                "approval_token": result["approval_token"],
                "context": approval_request.context,
            },
        )
        return ApprovalResponse(
            approval_token=result["approval_token"], approval_status="requested"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to request approval: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "approval_request_failed"},
        )


@router.post("/approval/{approval_token}/submit")
async def submit_approval(
    user: Any = Depends(verify_access_token),
    approval_token: str = Path(..., description="Approval Token"),
    approved: bool = Body(...),
    comments: Optional[str] = Body(None),
) -> Dict[str, Any]:
    """
    Submit an approval decision.
    Args:
        approval_token: Approval token
        approved: Approval decision
        comments: Optional comments
    Returns:
        Approval submission result
    """
    try:
        # Submit approval
        result = await approval_service.submit_approval(
            approval_token, approved, comments
        )
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "error_class": result.get("error_class", "unknown"),
                },
            )
        # Log the event
        status = "approved" if approved else "rejected"
        audit_logger.log_approval_event(
            result["session_id"],
            "plan_approval",  # Would get actual type from token
            status,
            {
                "approval_token": approval_token,
                "approved": approved,
                "comments": comments,
            },
        )
        return {
            "success": True,
            "approval_status": status,
            "message": f"Approval {status} successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit approval: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "approval_submission_failed"},
        )


@router.post("/{session_id}/intervene")
async def human_intervention(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
    intervention_request: HumanInterventionRequest = Body(...),
) -> Dict[str, Any]:
    """
    Perform human intervention on a pipeline.
    Args:
        session_id: Pipeline session ID
        intervention_request: Intervention request details
    Returns:
        Intervention result
    """
    try:
        # Create pipeline instance
        pipeline = pipeline_factory.create_pipeline()
        # Prepare intervention data
        intervention_data = {
            "type": intervention_request.resolution_type,
            **intervention_request.resolution_data,
        }
        # Handle intervention
        result = await pipeline.handle_human_intervention(session_id, intervention_data)
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "error_class": result.get("error_class", "unknown"),
                },
            )
        # Log the event
        audit_logger.log_human_intervention(
            session_id,
            intervention_request.resolution_type,
            {"intervention_data": intervention_data, "result": "success"},
        )
        return {
            "success": True,
            "message": "Human intervention applied successfully",
            "next_actions": result.get("next_actions", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply human intervention: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "intervention_failed"},
        )


@router.get("/{session_id}/metrics")
async def get_pipeline_metrics(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Get metrics for a pipeline.
    Args:
        session_id: Pipeline session ID
    Returns:
        Pipeline metrics
    """
    try:
        # Get metrics
        result = pipeline_monitor.get_pipeline_metrics(session_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": result.get("error", "Metrics not found"),
                    "error_class": result.get("error_class", "not_found"),
                },
            )
        return {
            "success": True,
            "metrics": result["pipeline_metrics"],
            "phase_metrics": result["phase_metrics"],
            "agent_metrics": result["agent_metrics"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "metrics_retrieval_failed"},
        )


@router.get("/{session_id}/estimate-cost", response_model=CostEstimateResponse)
async def estimate_cost(
    session_id: str, user: Any = Depends(verify_access_token)
) -> CostEstimateResponse:
    """Estimate infrastructure cost for a pipeline session."""
    workspace_dir = create_session_workspace(session_id)
    try:
        # Run infracost
        result = subprocess.run(
            ["infracost", "breakdown", "--path", workspace_dir, "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        total_monthly_cost = float(data.get("totalMonthlyCost", "0.0"))

        # Simple breakdown extraction
        breakdown: Dict[str, float] = {}
        for project in data.get("projects", []):
            for resource in project.get("breakdown", {}).get("resources", []):
                res_type = resource.get("name", "unknown")
                cost = float(resource.get("monthlyCost", "0.0"))
                breakdown[res_type] = breakdown.get(res_type, 0.0) + cost

        return CostEstimateResponse(
            success=True,
            estimated_cost_usd=total_monthly_cost,
            breakdown=breakdown,
            currency="USD",
        )
    except FileNotFoundError:
        # Fallback if infracost is not installed
        logger.warning("Infracost binary not found. Using fallback estimation.")
        return CostEstimateResponse(
            success=True,
            estimated_cost_usd=45.0,
            breakdown={"compute": 30.0, "storage": 15.0},
            currency="USD",
        )
    except Exception as e:
        logger.error(f"Infracost estimation failed: {e}")
        raise HTTPException(
            status_code=500, detail={"error": "Failed to estimate cost", "code": 500}
        )


@router.get("/health")
async def get_health_status() -> Dict[str, Any]:
    """
    Get health status of the pipeline service.
    Returns:
        Health status information
    """
    try:
        # Get health metrics
        health_result = pipeline_monitor.get_health_metrics()
        # Get system stats
        system_stats = {
            "active_pipelines": len(pipeline_monitor.pipeline_metrics),
            "uptime_seconds": health_result["health_metrics"]["uptime_seconds"],
            "status": health_result["health_metrics"]["status"],
        }
        return {
            "success": True,
            "status": "healthy",
            "system": system_stats,
            "health_metrics": health_result["health_metrics"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get health status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "health_check_failed"},
        )


@router.post("/{session_id}/teardown")
async def teardown_simulation(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Teardown LocalStack simulation infrastructure for a pipeline session.
    Args:
        session_id: Pipeline session ID
    Returns:
        Teardown operation result
    """
    try:
        workspace_dir = create_session_workspace(session_id)
        if not os.path.exists(workspace_dir):
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Execute tofu destroy
        env = os.environ.copy()
        env["ENABLE_LOCALSTACK_SIMULATION"] = "true"

        result = subprocess.run(
            ["tofu", "destroy", "-auto-approve"],
            cwd=workspace_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Teardown failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Teardown execution failed", "stderr": result.stderr},
            )

        # Log the event
        audit_logger.log_pipeline_event(
            "pipeline_teardown", session_id, {"result": "success"}
        )
        return {
            "success": True,
            "message": "Simulation infrastructure torn down successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to teardown simulation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "teardown_failed"},
        )


@router.get("/runs")
async def list_all_runs(
    project_id: Optional[str] = Query(
        None, description="Optional project ID to filter generations"
    ),
    limit: int = 50,
    offset: int = 0,
    user: Any = Depends(verify_access_token),
) -> Any:
    """List all pipeline and generation runs, unified."""
    try:
        uid = user.get("uid")
        if not uid:
            return {"success": False, "message": "Invalid user token"}

        tenant_uuid = None
        try:
            tenant_uuid = UUID(uid)
        except ValueError:
            pass

        pipelines = []
        if tenant_uuid:
            db_pipelines = pipeline_repo.list_pipelines(
                tenant_id=tenant_uuid, limit=limit, offset=offset
            )
            for p in db_pipelines:
                pipelines.append(
                    {
                        "run_type": "pipeline",
                        "id": str(p.id),
                        "session_id": p.session_id,
                        "name": p.name,
                        "status": p.status,
                        "phase": p.phase,
                        "created_at": p.created_at.isoformat()
                        if p.created_at
                        else None,
                        "started_at": p.started_at.isoformat()
                        if p.started_at
                        else None,
                        "completed_at": p.completed_at.isoformat()
                        if p.completed_at
                        else None,
                    }
                )

        generations = []
        if project_id:
            from db.db_provider import db_provider

            db_gens = await db_provider.list_generations(uid, project_id)
            for g in db_gens:
                generations.append(
                    {
                        "run_type": "generation",
                        "id": g.get("id"),
                        "session_id": g.get(
                            "id"
                        ),  # Use id as session_id for UI compatibility
                        "name": g.get("model", "Generation"),
                        "status": g.get("status"),
                        "phase": "completed"
                        if g.get("status") == "completed"
                        else "running",
                        "created_at": g.get("created_at"),
                        "started_at": g.get("created_at"),
                        "completed_at": g.get("created_at")
                        if g.get("status") in ["completed", "failed"]
                        else None,
                    }
                )

        # Combine and sort by created_at descending
        all_runs = pipelines + generations
        all_runs.sort(key=lambda x: x.get("created_at") or "", reverse=True)

        # Apply pagination after combining
        paginated_runs = all_runs[offset : offset + limit]

        return {"success": True, "data": paginated_runs, "total": len(all_runs)}
    except Exception as e:
        logger.error(f"Failed to list all runs: {str(e)}")
        return {"success": False, "message": str(e)}
