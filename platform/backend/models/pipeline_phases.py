from enum import Enum


class PipelinePhase(str, Enum):
    """Phases in the agentic pipeline."""

    CLARIFY = "clarify"  # User request clarification phase
    GENERATE = "generate"  # HCL code generation phase
    FORMAT = "format"  # Code formatting phase (tofu fmt)
    STATIC_ANALYSIS = "static_analysis"  # Static analysis and security checks
    INIT = "init"  # Terraform initialization phase (tofu init)
    VALIDATE = "validate"  # Terraform validation phase (tofu validate)
    PLAN_REVIEW = "plan_review"  # Human review of execution plan
    PLAN = "plan"  # Terraform planning phase (tofu plan)
    APPLY_REVIEW = "apply_review"  # Final approval before apply
    APPLY = "apply"  # Terraform apply phase (tofu apply)
    GIT_PUSH = "git_push"  # Git push phase
    CI_TRIGGER = "ci_trigger"  # CI pipeline trigger phase
    CI_MONITOR = "ci_monitor"  # CI pipeline monitoring phase
    ESCALATE = "escalate"  # Error escalation and human intervention
    COMPLETE = "complete"  # Pipeline completion phase
