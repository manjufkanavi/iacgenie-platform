"""SQLAlchemy-based repository for pipeline CRUD operations."""

import uuid

from datetime import datetime

from typing import Optional, List, Dict, Any, Callable

from sqlalchemy import create_engine, desc

from sqlalchemy.orm import Session, sessionmaker

from models.domain.pipeline_models import (
    Pipeline,
    PipelinePhaseHistory,
    PipelineLog,
)


def _get_engine() -> Any:
    """Create engine from database settings."""
    from config.database import get_database_settings

    settings = get_database_settings()
    if settings.provider == "postgres":
        url = settings.postgres_async_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
    else:
        url = f"sqlite:///{settings.SQLITE_PATH}"
    return create_engine(url, echo=False)


def _get_session_factory() -> Callable[..., Session]:
    engine = _get_engine()
    return sessionmaker(bind=engine)


class PipelineRepository:
    """Repository for pipeline state CRUD operations."""

    def __init__(
        self, session_factory: Optional[Callable[..., Session]] = None
    ) -> None:
        self._factory = session_factory or _get_session_factory()

    def _session(self) -> Session:
        return self._factory()

    def create_pipeline(
        self,
        session_id: str,
        tenant_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None,
        created_by: Optional[str] = None,
    ) -> Pipeline:
        with self._session() as db:
            pipeline = Pipeline(
                id=uuid.uuid4(),
                session_id=session_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                name=name,
                description=description,
                created_by=created_by,
            )
            db.add(pipeline)
            db.commit()
            db.refresh(pipeline)
            return pipeline

    def get_pipeline(self, session_id: str) -> Optional[Pipeline]:
        with self._session() as db:
            return db.query(Pipeline).filter(Pipeline.session_id == session_id).first()

    def get_pipeline_by_id(self, pipeline_id: uuid.UUID) -> Optional[Pipeline]:
        with self._session() as db:
            return db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()

    def update_status(
        self,
        session_id: str,
        status: str,
        phase: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Pipeline]:
        with self._session() as db:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.session_id == session_id).first()
            )
            if not pipeline:
                return None
            pipeline.status = status  # type: ignore[assignment]
            if phase is not None:
                pipeline.phase = phase  # type: ignore[assignment]
            if error_message is not None:
                pipeline.error_message = error_message  # type: ignore[assignment]
            if status == "completed":
                pipeline.completed_at = datetime.utcnow()  # type: ignore[assignment]
            db.commit()
            db.refresh(pipeline)
            return pipeline

    def increment_error_count(self, session_id: str) -> None:
        with self._session() as db:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.session_id == session_id).first()
            )
            if pipeline:
                pipeline.error_count += 1  # type: ignore[assignment]
                db.commit()

    def increment_retry_count(self, session_id: str) -> int:
        with self._session() as db:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.session_id == session_id).first()
            )
            if pipeline:
                pipeline.retry_count += 1  # type: ignore[assignment]
                db.commit()
                return pipeline.retry_count  # type: ignore[return-value]
            return 0

    def list_pipelines(
        self,
        tenant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> List[Pipeline]:
        with self._session() as db:
            query = db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id)
            if status_filter:
                query = query.filter(Pipeline.status == status_filter)
            query = query.order_by(desc(Pipeline.created_at))
            return query.limit(limit).offset(offset).all()

    def count_pipelines(
        self, tenant_id: uuid.UUID, status_filter: Optional[str] = None
    ) -> int:
        with self._session() as db:
            query = db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id)
            if status_filter:
                query = query.filter(Pipeline.status == status_filter)
            return query.count()

    def record_phase_history(
        self,
        pipeline_id: uuid.UUID,
        phase: str,
        status: str,
        agent_name: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_number: int = 0,
    ) -> PipelinePhaseHistory:
        with self._session() as db:
            history = PipelinePhaseHistory(
                pipeline_id=pipeline_id,
                phase=phase,
                status=status,
                duration_seconds=duration_seconds,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
                if status in ("success", "failed")
                else None,
                details=details,
                retry_number=retry_number,
            )
            db.add(history)
            db.commit()
            db.refresh(history)
            return history

    def get_phase_history(self, pipeline_id: uuid.UUID) -> List[PipelinePhaseHistory]:
        with self._session() as db:
            return (
                db.query(PipelinePhaseHistory)
                .filter(PipelinePhaseHistory.pipeline_id == pipeline_id)
                .order_by(PipelinePhaseHistory.started_at)
                .all()
            )

    def record_log(
        self,
        pipeline_id: uuid.UUID,
        level: str,
        message: str,
        phase: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineLog:
        with self._session() as db:
            log_entry = PipelineLog(
                pipeline_id=pipeline_id,
                level=level,
                message=message,
                phase=phase,
                metadata=metadata,
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry

    def get_logs(
        self,
        pipeline_id: uuid.UUID,
        limit: int = 100,
        phase_filter: Optional[str] = None,
    ) -> List[PipelineLog]:
        with self._session() as db:
            query = (
                db.query(PipelineLog)
                .filter(PipelineLog.pipeline_id == pipeline_id)
                .order_by(desc(PipelineLog.timestamp))
            )
            if phase_filter:
                query = query.filter(PipelineLog.phase == phase_filter)
            return query.limit(limit).all()

    def delete_pipeline(self, session_id: str) -> bool:
        with self._session() as db:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.session_id == session_id).first()
            )
            if not pipeline:
                return False
            db.delete(pipeline)
            db.commit()
            return True
