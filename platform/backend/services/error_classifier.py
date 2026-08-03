"""Error classification service for pipeline errors."""

import re

from typing import Dict, Any, List

from models.domain.error_classification import (
    ErrorCategory,
    ErrorSeverity,
    ErrorClassification,
    ErrorPattern,
)


class ErrorClassifier:
    """Classify errors and determine handling strategy."""

    CLASSIFICATION_RULES: List[Dict[str, Any]] = [
        # Most specific patterns first
        {
            "pattern": re.compile(r"tofu.fmt|format.failed", re.IGNORECASE),
            "severity": ErrorSeverity.RETRYABLE,
            "category": ErrorCategory.COMMAND_FAILURE,
            "actions": ["Run tofu fmt to auto-fix", "Check HCL syntax"],
        },
        {
            "pattern": re.compile(
                r"state.lock|lock.timeout|another.process", re.IGNORECASE
            ),
            "severity": ErrorSeverity.RETRYABLE,
            "category": ErrorCategory.STATE_LOCK_CONFLICT,
            "actions": ["Wait for lock release", "Force-unlock if process is dead"],
        },
        {
            "pattern": re.compile(r"rate.limit|429|too.many.requests", re.IGNORECASE),
            "severity": ErrorSeverity.RETRYABLE,
            "category": ErrorCategory.LLM_API_ERROR,
            "actions": [
                "Wait and retry with exponential backoff",
                "Check API quota limits",
            ],
        },
        {
            "pattern": re.compile(
                r"timeout|timed.out|deadline.exceeded", re.IGNORECASE
            ),
            "severity": ErrorSeverity.RETRYABLE,
            "category": ErrorCategory.LLM_API_ERROR,
            "actions": ["Retry with increased timeout", "Check network connectivity"],
        },
        {
            "pattern": re.compile(
                r"syntax.error|parse.error|hcl.syntax", re.IGNORECASE
            ),
            "severity": ErrorSeverity.HUMAN_REQUIRED,
            "category": ErrorCategory.VALIDATION_ERROR,
            "actions": ["Review HCL syntax", "Run tofu fmt to auto-fix formatting"],
        },
        {
            "pattern": re.compile(
                r"cis.violation|security.breach|hardcoded.secret", re.IGNORECASE
            ),
            "severity": ErrorSeverity.HUMAN_REQUIRED,
            "category": ErrorCategory.SECURITY_VIOLATION,
            "actions": ["Review security findings", "Remove hardcoded credentials"],
        },
        {
            "pattern": re.compile(
                r"403.forbidden|permission.denied|access.denied|IAM", re.IGNORECASE
            ),
            "severity": ErrorSeverity.FATAL,
            "category": ErrorCategory.PERMISSION_DENIED,
            "actions": ["Check IAM permissions", "Verify service account credentials"],
        },
        {
            "pattern": re.compile(
                r"auth.fail|unauthorized|invalid.token", re.IGNORECASE
            ),
            "severity": ErrorSeverity.FATAL,
            "category": ErrorCategory.PERMISSION_DENIED,
            "actions": ["Re-authenticate", "Check API key validity"],
        },
    ]

    def __init__(self) -> None:
        self._error_patterns: Dict[str, ErrorPattern] = {}

    def classify(
        self, error_message: str, phase: str = "unknown"
    ) -> ErrorClassification:
        """Classify an error based on pattern matching."""
        for rule in self.CLASSIFICATION_RULES:
            if rule["pattern"].search(error_message):
                classification = ErrorClassification(
                    severity=rule["severity"],
                    category=rule["category"],
                    phase=phase,
                    message=error_message[:500],
                    details={"matched_pattern": rule["pattern"].pattern},
                    auto_fix_available=rule["category"]
                    == ErrorCategory.COMMAND_FAILURE,
                    suggested_actions=rule["actions"],
                )
                self._record_pattern(classification)
                return classification
        # Default: treat unknown errors as fatal
        return ErrorClassification(
            severity=ErrorSeverity.FATAL,
            category=ErrorCategory.PERMISSION_DENIED,
            phase=phase,
            message=error_message[:500],
        )

    def _record_pattern(self, classification: ErrorClassification) -> None:
        key = classification.category.value
        if key not in self._error_patterns:
            self._error_patterns[key] = ErrorPattern(classification.category)
        self._error_patterns[key].record(classification.phase)

    def get_error_stats(self) -> Dict[str, Any]:
        return {
            category: pattern.to_dict()
            for category, pattern in self._error_patterns.items()
        }
