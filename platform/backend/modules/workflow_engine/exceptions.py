"""

Workflow Engine Exceptions

Custom exception classes for Workflow Engine. Defines all

error types that can be raised during workflow execution.

"""

from typing import Any, Dict, Optional
# ============================================================================

# Base Exception Classes

# ============================================================================


class WorkflowEngineError(Exception):
    """Base exception for all Workflow Engine errors."""

    def __init__(
        self, message: str, session_id: Optional[str] = None, **kwargs: Any
    ) -> None:
        self.message = message
        self.session_id = session_id
        self.details = kwargs
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format exception message."""
        if self.session_id:
            return f"[Session {self.session_id}] {self.message}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "session_id": self.session_id,
            "details": self.details,
        }


class SessionNotFoundError(WorkflowEngineError):
    """Exception raised when a session is not found."""

    pass


class InvalidStateTransitionError(WorkflowEngineError):
    """Exception raised for invalid state transitions."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(message, session_id, from_state=from_state, to_state=to_state)


class StateMachineError(WorkflowEngineError):
    """Exception raised for state machine errors."""

    pass


class RetryError(WorkflowEngineError):
    """Exception raised for retry-related errors."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> None:
        self.retry_count = retry_count
        self.max_retries = max_retries
        super().__init__(
            message, session_id, retry_count=retry_count, max_retries=max_retries
        )


class DeadLetterQueueError(WorkflowEngineError):
    """Exception raised for DLQ-related errors."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> None:
        self.task_id = task_id
        self.task_type = task_type
        super().__init__(message, session_id, task_id=task_id, task_type=task_type)


class SagaError(WorkflowEngineError):
    """Exception raised for saga-related errors."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        saga_id: Optional[str] = None,
        step_name: Optional[str] = None,
    ) -> None:
        self.saga_id = saga_id
        self.step_name = step_name
        super().__init__(message, session_id, saga_id=saga_id, step_name=step_name)


class IdempotencyError(WorkflowEngineError):
    """Exception raised for idempotency-related errors."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(message, session_id, idempotency_key=idempotency_key)


# ============================================================================

# Specific Exception Classes

# ============================================================================


class SessionError(WorkflowEngineError):
    """Exception raised for session-related errors."""

    pass


class SessionTimeoutError(SessionError):
    """Exception raised when a session times out."""

    pass


class MaxIterationsExceededError(SessionError):
    """Exception raised when max iterations are exceeded."""

    pass


class StateTransitionError(WorkflowEngineError):
    """Exception raised for state transition errors."""

    pass


class StateTransitionTimeoutError(StateTransitionError):
    """Exception raised when state transition times out."""

    pass


class CompensationFailedError(SagaError):
    """Exception raised when saga compensation fails."""

    pass


class DLQFullError(DeadLetterQueueError):
    """Exception raised when dead letter queue is full."""

    pass


class IdempotencyKeyExistsError(IdempotencyError):
    """Exception raised when idempotency key already exists."""

    pass


class RedisError(WorkflowEngineError):
    """Raised when a Redis operation fails."""

    pass
