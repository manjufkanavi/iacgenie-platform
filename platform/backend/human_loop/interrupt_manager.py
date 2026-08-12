"""Stub InterruptManager."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InterruptManager:
    """Stub interrupt manager — returns success with no-op behavior."""

    async def trigger_interrupt(self, session_id: str, error_class, context: Optional[dict] = None):
        logger.info(f"[HUMAN LOOP] Interrupt triggered for session {session_id}")
        return {
            "success": True,
            "interrupt_id": f"interrupt-{session_id}",
        }
