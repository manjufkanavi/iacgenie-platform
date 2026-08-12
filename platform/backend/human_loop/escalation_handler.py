"""Stub EscalationHandler."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EscalationHandler:
    """Stub escalation handler — no-op escalation."""

    def __init__(self):
        pass

    async def escalate(self, session_id: str, reason: Optional[str] = None):
        logger.info(f"[HUMAN LOOP] Escalated session {session_id}")
        return {"success": True}
