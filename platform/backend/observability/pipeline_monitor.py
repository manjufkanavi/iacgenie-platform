"""Stub PipelineMonitor with all methods needed by routers."""


class PipelineMonitor:
    def __init__(self):
        pass

    def record_phase_duration(self, pipeline_id: str, phase: str, duration_ms: float):
        pass

    def record_error(self, pipeline_id: str, phase: str, error: str):
        pass

    def set_status(self, pipeline_id: str, status: str):
        pass

    def get_metrics(self):
        return {}

    def get_health_metrics(self):
        return {
            "success": True,
            "health_metrics": {
                "active_pipelines": 0,
                "total_agent_executions": 0,
                "error_rate": 0.0,
                "warning_rate": 0.0,
                "status": "healthy",
                "summary": {"total_agent_executions": 0},
            },
        }

    def get_all_metrics(self):
        return {
            "success": True,
            "summary": {"total_pipelines": 0},
            "pipeline_summaries": [],
        }

    def get_agent_performance(self):
        return {
            "success": True,
            "agent_performance": [],
        }

    def get_phase_statistics(self):
        return {
            "success": True,
            "phase_statistics": [],
        }
