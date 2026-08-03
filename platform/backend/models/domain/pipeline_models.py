"""SQLAlchemy ORM models for pipeline state management tables."""

import uuid

from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Index,
)

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import func

Base = declarative_base()


class PipelinePhase(str, Enum):
    CLARIFY = "clarify"
    GENERATE = "generate"
    FORMAT = "format"
    STATIC_ANALYSIS = "static_analysis"
    INIT = "init"
    VALIDATE = "validate"
    PLAN_REVIEW = "plan_review"
    PLAN = "plan"
    APPLY_REVIEW = "apply_review"
    APPLY = "apply"
    ESCALATE = "escalate"
    COMPLETE = "complete"


class PipelineStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class Pipeline(Base):  # type: ignore[misc,valid-type]
    """Main pipeline state table."""

    __tablename__ = "pipelines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    deployment_mode = Column(String(32), nullable=True, default="aws")
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    phase = Column(String(32), nullable=False, default=PipelinePhase.CLARIFY.value)
    status = Column(String(16), nullable=False, default=PipelineStatus.RUNNING.value)
    current_phase_progress = Column(Integer, nullable=False, default=0)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_count = Column(Integer, nullable=False, default=0)
    refined_spec = Column(JSONB, nullable=True)
    generated_files_s3_key = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    error_phase = Column(String(32), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # type: ignore[misc]
        nullable=False,
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # type: ignore[misc]
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(255), nullable=True)
    __table_args__ = (Index("ix_pipelines_tenant_status", "tenant_id", "status"),)


class PipelinePhaseHistory(Base):  # type: ignore[misc,valid-type]
    """Tracks each phase execution within a pipeline."""

    __tablename__ = "pipeline_phase_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False)  # success, running, pending, failed
    duration_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    details = Column(JSONB, nullable=True)  # questions asked, files generated, etc.
    retry_number = Column(Integer, nullable=False, default=0)
    __table_args__ = (Index("ix_phase_history_pipeline", "pipeline_id", "phase"),)


class PipelineLog(Base):  # type: ignore[misc,valid-type]
    """Structured log entries for pipeline execution."""

    __tablename__ = "pipeline_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # type: ignore[misc]
        nullable=False,
    )
    phase = Column(String(32), nullable=True)
    message = Column(Text, nullable=False)
    level = Column(String(10), nullable=False, default="info")  # info, warning, error
    meta_data = Column(JSONB, nullable=True)
    __table_args__ = (Index("ix_pipeline_logs_pipeline", "pipeline_id", "timestamp"),)
