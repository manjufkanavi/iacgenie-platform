"""Enhanced error classification models for pipeline errors."""

import uuid

from datetime import datetime

from enum import Enum

from typing import List, Optional


class ErrorCategory(str, Enum):
    """Categories of errors that can occur in the pipeline."""

    LLM_API_ERROR = "llm_api_error"
    VALIDATION_ERROR = "validation_error"
    SECURITY_VIOLATION = "security_violation"
    COMMAND_FAILURE = "command_failure"
    STATE_LOCK_CONFLICT = "state_lock_conflict"
    PERMISSION_DENIED = "permission_denied"


class ErrorSeverity(str, Enum):
    """How severely an error impacts pipeline execution."""

    RETRYABLE = "RETRYABLE"
    CLARIFICATION = "CLARIFICATION"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    FATAL = "FATAL"


class ErrorClassification:
    """Structured error classification with auto-fix suggestions."""

    def __init__(
        self,
        error_id: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.FATAL,
        category: ErrorCategory = ErrorCategory.PERMISSION_DENIED,
        phase: str = "unknown",
        message: str = "",
        details: Optional[dict] = None,
        auto_fix_available: bool = False,
        suggested_actions: Optional[List[str]] = None,
    ):
        self.error_id = error_id or str(uuid.uuid4())
        self.severity = severity
        self.category = category
        self.phase = phase
        self.message = message
        self.details = details or {}
        self.auto_fix_available = auto_fix_available
        self.suggested_actions = suggested_actions or []
        self.classified_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "error_id": self.error_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "phase": self.phase,
            "message": self.message,
            "details": self.details,
            "auto_fix_available": self.auto_fix_available,
            "suggested_actions": self.suggested_actions,
            "classified_at": self.classified_at.isoformat(),
        }


class ErrorPattern:
    """Tracks recurring error patterns across sessions."""

    def __init__(self, category: ErrorCategory):
        self.pattern_id = str(uuid.uuid4())
        self.category = category
        self.frequency: int = 0
        self.first_seen: Optional[datetime] = None
        self.last_seen: Optional[datetime] = None
        self.affected_sessions: List[str] = []

    def record(self, session_id: str) -> None:
        self.frequency += 1
        now = datetime.utcnow()
        if self.first_seen is None:
            self.first_seen = now
        self.last_seen = now
        if session_id not in self.affected_sessions:
            self.affected_sessions.append(session_id)

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "category": self.category.value,
            "frequency": self.frequency,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "affected_sessions": self.affected_sessions,
        }
