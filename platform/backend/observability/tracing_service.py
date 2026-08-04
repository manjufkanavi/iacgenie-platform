"""Stub TracingService with all methods needed by routers."""


class TracingService:
    def __init__(self):
        self.active_traces = {}

    def start_span(self, operation: str):
        return None

    def end_span(self, span):
        pass

    def set_tag(self, span, key: str, value: str):
        pass

    def inject_context(self):
        return {}

    def extract_context(self):
        return None

    def log_trace(self, trace_id: str, event: str):
        pass

    def get_trace_stats(self):
        return {"success": True, "stats": {"total_traces": 0}}

    def get_session_traces(self, session_id: str):
        return {"success": True, "traces": []}

    def get_trace(self, trace_id: str):
        return {"success": False, "error": "Trace not found"}
