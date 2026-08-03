"""Data models for Agent Executor."""

from enum import Enum

from pydantic import ConfigDict, BaseModel, Field

from typing import Optional

from datetime import datetime

import uuid


class AgentType(str, Enum):
    """Enumeration of agent types as defined in the design document."""

    CODER = "coder"
    VALIDATOR = "validator"
    PLANNER = "planner"
    APPLIER = "applier"
    TESTER = "tester"


class AgentStatus(str, Enum):
    """Enumeration of agent statuses as defined in the design document."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Agent(BaseModel):
    """Data model representing an agent in the system."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the agent",
    )
    agent_type: AgentType = Field(
        ..., description="Type of agent (coder, validator, planner, applier, tester)"
    )
    session_id: str = Field(..., description="UUID of the associated session")
    status: AgentStatus = Field(
        AgentStatus.RUNNING, description="Current status of the agent"
    )
    started_at: Optional[datetime] = Field(
        None, description="Timestamp when the agent started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Timestamp when the agent completed"
    )
    build_id: str = Field(..., description="Build identifier for the task")
    iteration: int = Field(1, description="Iteration number for the task")
    model_config = ConfigDict(from_attributes=True)

    def serialize_datetime(cls, v: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return v.isoformat() if v else None

    def serialize_uuid(cls, v: str) -> str:
        """Serialize UUID to string."""
        return str(v)

    def start(self) -> "Agent":
        """Mark the agent as started."""
        self.started_at = datetime.utcnow()
        self.status = AgentStatus.RUNNING
        return self

    def complete(self) -> "Agent":
        """Mark the agent as completed."""
        self.completed_at = datetime.utcnow()
        self.status = AgentStatus.COMPLETED
        return self

    def fail(self, reason: str = "Unknown failure") -> "Agent":
        """Mark the agent as failed."""
        self.completed_at = datetime.utcnow()
        self.status = AgentStatus.FAILED
        return self

    def timeout(self) -> "Agent":
        """Mark the agent as timed out."""
        self.completed_at = datetime.utcnow()
        self.status = AgentStatus.TIMEOUT
        return self

    def is_running(self) -> bool:
        """Check if the agent is currently running."""
        return self.status == AgentStatus.RUNNING

    def is_completed(self) -> bool:
        """Check if the agent has completed successfully."""
        return self.status == AgentStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if the agent has failed."""
        return self.status == AgentStatus.FAILED

    def is_timed_out(self) -> bool:
        """Check if the agent has timed out."""
        return self.status == AgentStatus.TIMEOUT


class AgentCreate(BaseModel):
    """Model for creating a new agent."""

    agent_type: AgentType
    session_id: str
    build_id: str
    iteration: int = 1
    model_config = ConfigDict(from_attributes=True)


class AgentUpdate(BaseModel):
    """Model for updating an existing agent."""

    status: AgentStatus
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
