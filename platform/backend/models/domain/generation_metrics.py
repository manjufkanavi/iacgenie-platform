"""SQLAlchemy ORM model for generation metrics."""

import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Float,
    Boolean,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func

Base = declarative_base()


class GenerationMetrics(Base):  # type: ignore[misc,valid-type]
    """Model for tracking LLM proxy generation telemetry."""

    __tablename__ = "generation_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(255), index=True, nullable=False)
    tenant_id = Column(String(255), index=True, nullable=False)
    generation_id = Column(String(255), unique=True, nullable=False)

    requested_model = Column(String(255), nullable=False)
    model_used = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=False)

    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    total_cost = Column(Float, nullable=False, default=0.0)

    latency_ms = Column(Float, nullable=True)
    is_cached = Column(Boolean, nullable=False, default=False)
    failover_occurred = Column(Boolean, nullable=False, default=False)
    failover_from = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # type: ignore[misc]
        nullable=False,
    )

    __table_args__ = (
        Index("ix_metrics_project_date", "project_id", "created_at"),
        Index("ix_metrics_tenant_date", "tenant_id", "created_at"),
    )
