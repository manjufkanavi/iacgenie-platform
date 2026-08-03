from typing import List, Optional, Dict, Any

import uuid

from datetime import datetime

from pydantic import BaseModel, Field

from .error_classes import ErrorClass

from .pipeline_phases import PipelinePhase


class IaCState(BaseModel):
    """State schema for the agentic IaC pipeline."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    user_request: str = Field(..., description="Original user input/request")
    refined_spec: Optional[str] = Field(
        None, description="Refined architecture specification (JSON) from clarify agent"
    )
    hcl_code: Optional[str] = Field(None, description="Last generated HCL code")
    work_dir: Optional[str] = Field(
        None, description="Temporary workspace directory path"
    )
    # State tracking
    current_phase: PipelinePhase = Field(
        default=PipelinePhase.CLARIFY, description="Current pipeline phase"
    )
    retry_counts: Dict[str, int] = Field(
        default_factory=dict, description="Per-phase retry counts"
    )
    last_error: Optional[str] = Field(None, description="Last error details")
    last_error_class: Optional[ErrorClass] = Field(
        None, description="Last error classification"
    )
    # Execution artifacts
    command_outputs: Dict[str, str] = Field(
        default_factory=dict, description="Command execution outputs"
    )
    approvals: Dict[str, bool] = Field(
        default_factory=dict, description="Human approvals (e.g., plan_approved)"
    )
    # Conversation history
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation history for observability"
    )
    # Model routing metadata
    model_routing: Dict[str, str] = Field(
        default_factory=dict, description="Model selection metadata"
    )
    # Retry feedback
    retry_feedback: Optional[str] = Field(
        None, description="Feedback for retry attempts"
    )
    # Clarification chat
    clarification_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Clarification history during clarification phase",
    )
    expected_clarification_questions: Optional[int] = Field(
        None, description="Model's estimated number of questions needed"
    )
    # Timestamps
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Pipeline start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Pipeline completion timestamp"
    )

    def checkpoint(self) -> Dict[str, Any]:
        """Create a checkpoint of the current state."""
        return self.model_dump(exclude={"work_dir"})  # Don't checkpoint absolute paths

    @classmethod
    def restore_from_checkpoint(cls, checkpoint_data: Dict[str, Any]) -> "IaCState":
        """Restore state from a checkpoint."""
        return cls(**checkpoint_data)

    def get_phase_history(self) -> List[PipelinePhase]:
        """Get the history of phases visited (from messages)."""
        phase_history = []
        for message in self.messages:
            if message.get("phase_transition"):
                phase_history.append(message["phase_transition"])
        return phase_history

    def add_message(
        self, role: str, content: str, phase_transition: Optional[PipelinePhase] = None
    ) -> None:
        """Add a message to the conversation history."""
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,
            "content": content,
        }
        if phase_transition:
            message["phase_transition"] = phase_transition
        self.messages.append(message)
