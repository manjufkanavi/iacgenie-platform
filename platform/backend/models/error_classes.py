from enum import Enum


class ErrorClass(str, Enum):
    """Classification of errors in the agentic pipeline."""

    RETRYABLE = "retryable"  # Transient errors that can be retried (syntax issues, provider install hiccups)
    CLARIFICATION = (
        "clarification"  # Ambiguous architecture requests requiring user clarification
    )
    HUMAN_REQUIRED = "human_required"  # Errors requiring human intervention (IAM issues, quotas, drift)
    FATAL = "fatal"  # Non-recoverable errors (auth failures, binary crashes)
