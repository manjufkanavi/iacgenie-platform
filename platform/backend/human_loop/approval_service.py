"""Stub ApprovalService."""
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class ApprovalService:
    """Stub approval service — returns success with no-op behavior."""

    async def request_approval(self, session_id: str, approval_type: str, context: Optional[dict] = None):
        logger.info(f"[HUMAN LOOP] Approval requested for session {session_id}, type={approval_type}")
        token = str(uuid.uuid4())
        return {
            "success": True,
            "approval_token": token,
        }

    async def submit_approval(self, approval_token: str, approved: bool, comments: Optional[str] = None):
        logger.info(f"[HUMAN LOOP] Approval submitted: token={approval_token}, approved={approved}")
        return {
            "success": True,
            "approved": approved,
        }
