"""Stub AuditLogger with all methods needed by routers."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    def log_event(self, event_type: str, details: Optional[dict] = None, user_id: Optional[str] = None):
        logger.info(f"[AUDIT] {event_type}: {details or {}}")

    def log_pipeline_run(self, pipeline_id: str, phase: str, status: str, user_id: Optional[str] = None):
        logger.info(f"[AUDIT] Pipeline {pipeline_id}: {phase} -> {status}")

    def log_error(self, error: Exception, context: Optional[dict] = None):
        logger.error(f"[AUDIT] Error: {error} {context or {}}")

    def log_pipeline_event(self, session_id: str, event_type: str, details: Optional[dict] = None, user_id: Optional[str] = None):
        logger.info(f"[AUDIT] Pipeline {session_id}: {event_type}")

    def log_human_intervention(self, session_id: str, action: str, details: Optional[dict] = None, user_id: Optional[str] = None):
        logger.info(f"[AUDIT] Human intervention on {session_id}: {action}")

    def log_approval_event(self, session_id: str, approval_type: str, action: str, details: Optional[dict] = None, user_id: Optional[str] = None):
        logger.info(f"[AUDIT] Approval on {session_id}: {approval_type} -> {action}")

    async def async_log(self, event_type: str, details: Optional[dict] = None):
        self.log_event(event_type, details)

    def get_audit_logs(self, limit: int = 100):
        logger.info(f"[AUDIT] get_audit_logs(limit={limit})")
        return {"success": True, "logs": [], "count": 0}

    def get_session_audit_logs(self, session_id: str):
        logger.info(f"[AUDIT] get_session_audit_logs(session_id={session_id})")
        return {"success": True, "logs": [], "count": 0}

    def get_audit_stats(self):
        logger.info("[AUDIT] get_audit_stats()")
        return {"success": True, "stats": {"total_logs": 0}}
