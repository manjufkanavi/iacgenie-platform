from fastapi import APIRouter, HTTPException, Depends, Path, Query

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from observability.audit_logger import AuditLogger

from observability.pipeline_monitor import PipelineMonitor

from observability.tracing_service import TracingService

from middleware.auth_middleware import verify_access_token

import logging

logger = logging.getLogger(__name__)

# Create router


def _resolve_log_details(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve log details by trying multiple possible key names."""
    for key in (
        "state",
        "transition",
        "agent_execution",
        "intervention",
        "approval",
        "error",
    ):
        val = entry.get(key)
        if val is not None:
            return val
    return {}


router = APIRouter(prefix="/api/observability", tags=["Observability"])

# Initialize services

audit_logger = AuditLogger()

pipeline_monitor = PipelineMonitor()

tracing_service = TracingService()

# Request/Response Models


class AuditLogResponse(BaseModel):
    timestamp: str = Field(..., description="Log entry timestamp")
    event_type: str = Field(..., description="Type of event")
    session_id: str = Field(..., description="Pipeline session ID")
    details: Dict[str, Any] = Field(..., description="Event details")


class MetricsResponse(BaseModel):
    active_pipelines: int = Field(..., description="Number of active pipelines")
    total_agent_executions: int = Field(..., description="Total agent executions")
    error_rate: float = Field(..., description="Error rate")
    warning_rate: float = Field(..., description="Warning rate")
    status: str = Field(..., description="System status")


class TraceResponse(BaseModel):
    trace_id: str = Field(..., description="Trace ID")
    session_id: str = Field(..., description="Pipeline session ID")
    operation_name: str = Field(..., description="Operation being traced")
    status: str = Field(..., description="Trace status")
    duration_ms: Optional[float] = Field(
        None, description="Trace duration in milliseconds"
    )


# API Endpoints


@router.get("/audit-logs")
async def get_audit_logs(
    user: Any = Depends(verify_access_token),
    limit: int = Query(100, ge=1, le=1000, description="Max logs to return"),
    run_id: Optional[str] = Query(None, description="Optional run ID"),
) -> Dict[str, Any]:
    """
    Get recent audit logs.
    Args:
        limit: Maximum number of logs to return
        run_id: Optional run ID
    Returns:
        Audit logs
    """
    try:
        if run_id:
            result = audit_logger.get_session_audit_logs(run_id)
        else:
            result = audit_logger.get_audit_logs(limit)
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "Failed to retrieve audit logs"),
                    "error_class": result.get("error_class", "audit_retrieval_failed"),
                },
            )
        # Format logs for response
        formatted_logs = []
        for log_entry in result["logs"]:
            details = _resolve_log_details(log_entry)
            formatted_logs.append(
                {
                    "timestamp": log_entry["timestamp"],
                    "event_type": log_entry["event_type"],
                    "session_id": log_entry["session_id"],
                    "details": details,
                }
            )
        return {
            "success": True,
            "logs": formatted_logs,
            "count": len(formatted_logs),
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Failed to get audit logs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "audit_log_retrieval_failed"},
        )


@router.get("/session/{session_id}/audit-logs")
async def get_session_audit_logs(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Get audit logs for a specific session.
    Args:
        session_id: Pipeline session ID
    Returns:
        Session audit logs
    """
    try:
        # Get session audit logs
        result = audit_logger.get_session_audit_logs(session_id)
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get(
                        "error", "Failed to retrieve session audit logs"
                    ),
                    "error_class": result.get("error_class", "audit_retrieval_failed"),
                },
            )
        # Format logs for response
        formatted_logs = []
        for log_entry in result["logs"]:
            details = _resolve_log_details(log_entry)
            formatted_logs.append(
                {
                    "timestamp": log_entry["timestamp"],
                    "event_type": log_entry["event_type"],
                    "session_id": log_entry["session_id"],
                    "details": details,
                }
            )
        return {
            "success": True,
            "session_id": session_id,
            "logs": formatted_logs,
            "count": len(formatted_logs),
        }
    except Exception as e:
        logger.error(f"Failed to get session audit logs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_class": "session_audit_log_retrieval_failed",
            },
        )


@router.get("/audit-stats")
async def get_audit_stats(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Get statistics about audit logs.
    Returns:
        Audit statistics
    """
    try:
        # Get audit stats
        result = audit_logger.get_audit_stats()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "Failed to retrieve audit statistics"),
                    "error_class": result.get("error_class", "stats_retrieval_failed"),
                },
            )
        return {"success": True, "stats": result["stats"]}
    except Exception as e:
        logger.error(f"Failed to get audit stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "audit_stats_retrieval_failed"},
        )


@router.get("/metrics")
async def get_metrics(
    user: Any = Depends(verify_access_token),
) -> MetricsResponse:
    """
    Get system metrics.
    Returns:
        System metrics
    """
    try:
        # Get health metrics
        result = pipeline_monitor.get_health_metrics()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "Failed to retrieve metrics"),
                    "error_class": result.get(
                        "error_class", "metrics_retrieval_failed"
                    ),
                },
            )
        health_metrics = result["health_metrics"]
        return MetricsResponse(
            active_pipelines=health_metrics["active_pipelines"],
            total_agent_executions=health_metrics["summary"]["total_agent_executions"],
            error_rate=health_metrics["error_rate"],
            warning_rate=health_metrics["warning_rate"],
            status=health_metrics["status"],
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "metrics_retrieval_failed"},
        )


@router.get("/pipeline-metrics")
async def get_pipeline_metrics(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Get metrics for all pipelines.
    Returns:
        Pipeline metrics
    """
    try:
        # Get all metrics
        result = pipeline_monitor.get_all_metrics()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "Failed to retrieve pipeline metrics"),
                    "error_class": result.get(
                        "error_class", "metrics_retrieval_failed"
                    ),
                },
            )
        return {
            "success": True,
            "summary": result["summary"],
            "pipeline_summaries": result["pipeline_summaries"],
        }
    except Exception as e:
        logger.error(f"Failed to get pipeline metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_class": "pipeline_metrics_retrieval_failed",
            },
        )


@router.get("/agent-performance")
async def get_agent_performance(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Get performance metrics for all agents.
    Returns:
        Agent performance metrics
    """
    try:
        # Get agent performance
        result = pipeline_monitor.get_agent_performance()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get(
                        "error", "Failed to retrieve agent performance"
                    ),
                    "error_class": result.get(
                        "error_class", "performance_retrieval_failed"
                    ),
                },
            )
        return {"success": True, "agent_performance": result["agent_performance"]}
    except Exception as e:
        logger.error(f"Failed to get agent performance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_class": "agent_performance_retrieval_failed",
            },
        )


@router.get("/phase-statistics")
async def get_phase_statistics(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Get statistics about phase transitions.
    Returns:
        Phase statistics
    """
    try:
        # Get phase statistics
        result = pipeline_monitor.get_phase_statistics()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "Failed to retrieve phase statistics"),
                    "error_class": result.get(
                        "error_class", "phase_stats_retrieval_failed"
                    ),
                },
            )
        return {"success": True, "phase_statistics": result["phase_statistics"]}
    except Exception as e:
        logger.error(f"Failed to get phase statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_class": "phase_statistics_retrieval_failed",
            },
        )


@router.get("/traces")
async def get_active_traces(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Get all active traces.
    Returns:
        Active traces information
    """
    try:
        # Get trace stats to see active traces
        stats_result = tracing_service.get_trace_stats()
        if not stats_result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": stats_result.get(
                        "error", "Failed to retrieve trace statistics"
                    ),
                    "error_class": stats_result.get(
                        "error_class", "trace_stats_retrieval_failed"
                    ),
                },
            )
        # Get active traces
        active_traces = []
        for trace_id, trace_data in tracing_service.active_traces.items():
            active_traces.append(
                {
                    "trace_id": trace_id,
                    "session_id": trace_data["session_id"],
                    "operation_name": trace_data["operation_name"],
                    "start_time": trace_data["start_time"],
                    "status": trace_data["status"],
                }
            )
        return {
            "success": True,
            "active_traces": active_traces,
            "count": len(active_traces),
            "stats": stats_result["stats"],
        }
    except Exception as e:
        logger.error(f"Failed to get active traces: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "active_traces_retrieval_failed"},
        )


@router.get("/session/{session_id}/traces")
async def get_session_traces(
    user: Any = Depends(verify_access_token),
    session_id: str = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """
    Get all traces for a session.
    Args:
        session_id: Pipeline session ID
    Returns:
        Session traces information
    """
    try:
        # Get session traces
        result = tracing_service.get_session_traces(session_id)
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "Failed to retrieve session traces"),
                    "error_class": result.get(
                        "error_class", "session_traces_retrieval_failed"
                    ),
                },
            )
        # Format traces for response
        formatted_traces = []
        for trace_info in result["traces"]:
            trace_data = trace_info["data"]
            formatted_traces.append(
                {
                    "trace_id": trace_info["trace_id"],
                    "status": trace_info["status"],
                    "operation_name": trace_data["operation_name"],
                    "start_time": trace_data["start_time"],
                    "end_time": trace_data.get("end_time"),
                    "duration_ms": trace_data.get("duration_ms"),
                    "span_count": len(trace_data["spans"]),
                }
            )
        return {
            "success": True,
            "session_id": session_id,
            "traces": formatted_traces,
            "count": len(formatted_traces),
        }
    except Exception as e:
        logger.error(f"Failed to get session traces: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "session_traces_retrieval_failed"},
        )


@router.get("/trace/{trace_id}")
async def get_trace_details(
    user: Any = Depends(verify_access_token),
    trace_id: str = Path(..., description="Trace ID"),
) -> Dict[str, Any]:
    """
    Get details for a specific trace.
    Args:
        trace_id: Trace ID
    Returns:
        Trace details
    """
    try:
        # Get trace details
        result = tracing_service.get_trace(trace_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": result.get("error", "Trace not found"),
                    "error_class": result.get("error_class", "trace_not_found"),
                },
            )
        trace_data = result["trace"]
        # Format spans for response
        formatted_spans = []
        for span in trace_data["spans"]:
            formatted_span = {
                "span_id": span["span_id"],
                "parent_id": span.get("parent_id"),
                "name": span["name"],
                "start_time": span["start_time"],
                "end_time": span.get("end_time"),
                "duration_ms": span.get("duration_ms"),
                "status": span["status"],
                "events": span.get("events", []),
            }
            formatted_spans.append(formatted_span)
        return {
            "success": True,
            "trace_id": trace_id,
            "session_id": trace_data["session_id"],
            "operation_name": trace_data["operation_name"],
            "status": result["status"],
            "start_time": trace_data["start_time"],
            "end_time": trace_data.get("end_time"),
            "duration_ms": trace_data.get("duration_ms"),
            "spans": formatted_spans,
            "span_count": len(formatted_spans),
        }
    except Exception as e:
        logger.error(f"Failed to get trace details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "trace_details_retrieval_failed"},
        )


@router.get("/trace-stats")
async def get_trace_stats(
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Get statistics about traces.
    Returns:
        Trace statistics
    """
    try:
        # Get trace stats
        result = tracing_service.get_trace_stats()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "Failed to retrieve trace statistics"),
                    "error_class": result.get(
                        "error_class", "trace_stats_retrieval_failed"
                    ),
                },
            )
        return {"success": True, "stats": result["stats"]}
    except Exception as e:
        logger.error(f"Failed to get trace stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "error_class": "trace_stats_retrieval_failed"},
        )


@router.get("/runs/{run_id}/summary")
async def get_run_summary(
    run_id: str = Path(..., description="Run ID"),
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Get unified summary for a run including metrics, traces, and audit logs."""
    try:
        audit = audit_logger.get_session_audit_logs(run_id)
        metrics = pipeline_monitor.get_pipeline_metrics(run_id)
        traces = tracing_service.get_session_traces(run_id)

        return {
            "success": True,
            "run_id": run_id,
            "summary": {
                "audit_logs": audit.get("logs", []) if audit.get("success") else [],
                "metrics": metrics.get("metrics", {}) if metrics.get("success") else {},
                "traces": traces.get("traces", []) if traces.get("success") else [],
            },
        }
    except Exception as e:
        logger.error(f"Failed to get run summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
