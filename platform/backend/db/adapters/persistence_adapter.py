"""

Persistence Database Adapter

Integrates new persistence layer (session_states, iterations, artifacts) with existing database

This adapter extends the PostgreSQLAdapter to support both:

1. Existing tables (users, projects, ai_generations, deployments)

2. New persistence tables (session_states, iterations, artifacts, user_repo_configs, processed_events)

Strategy: Dual-write support during migration period

"""

from typing import Dict, Any, List, Optional

from datetime import datetime

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    JSON,
)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import QueuePool

from datetime import timezone as tz

from uuid import uuid4

from config.database import db_settings

from config.logging import get_logger

from services.business_metrics_service import business_metrics

# Import existing adapter for backward compatibility

logger = get_logger("db.persistence")
# ============================================================================

# New Persistence Table Definitions

# ============================================================================


class PersistenceAdapter:
    """
    Adapter for new persistence layer with session lifecycle management
    Supports both existing and new table schemas during migration period.
    """

    def __init__(self) -> None:
        self.engine: Any = None
        self.async_engine: Any = None
        self.session_factory: Any = None
        self.async_session_factory: Any = None
        self.metadata = MetaData()
        self._is_initialized = False
        # Define both existing and new tables
        self._define_existing_tables()
        self._define_persistence_tables()

    def _define_existing_tables(self) -> None:
        """Define existing table schemas for backward compatibility"""
        # Users table
        self.users_table = Table(
            "users",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("email", String, unique=True, nullable=False),
            Column("name", String),
            Column("role", String, default="user"),
            Column("is_active", Boolean, default=True),
            Column("password_hash", String),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
            Column("metadata", JSON),
        )
        # Projects table
        self.projects_table = Table(
            "projects",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("name", String, nullable=False),
            Column("description", String),
            Column("status", String, default="active"),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
            Column("metadata", JSON),
        )
        # AI Generations table
        self.generations_table = Table(
            "ai_generations",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("project_id", String),
            Column("model", String, nullable=False),
            Column("prompt", String, nullable=False),
            Column("response", String),
            Column("status", String, default="pending"),
            Column("tokens_used", Integer),
            Column("duration_ms", Integer),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column("metadata", JSON),
        )
        # Deployments table
        self.deployments_table = Table(
            "deployments",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("project_id", String, nullable=False),
            Column("platform", String, nullable=False),
            Column("status", String, default="pending"),
            Column("url", String),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
            Column("metadata", JSON),
        )

    def _define_persistence_tables(self) -> None:
        """Define new persistence layer table schemas"""
        # Valid session statuses
        # Valid artifact types
        # Valid git providers
        # Session States table
        self.session_states_table = Table(
            "session_states",
            self.metadata,
            Column("id", String, primary_key=True, default=lambda: str(uuid4())),
            Column("build_id", String, nullable=False, index=True),
            Column("user_id", String, nullable=False),
            Column("prompt", String, nullable=True),
            Column("status", String, default="CREATED"),
            Column("current_iteration", Integer, default=0),
            Column("git_repo_url", String, nullable=True),
            Column("git_branch", String, nullable=True),
            Column("git_commit_sha", String, nullable=True),
            Column("ci_provider", String, nullable=True),
            Column("ci_run_id", String, nullable=True),
            Column("deployment_status", String, default="pending"),
            Column("error_message", String, nullable=True),
            Column("version", Integer, default=1),
            Column("created_at", DateTime, default=lambda: datetime.now(tz.utc)),
            Column(
                "updated_at",
                DateTime,
                default=lambda: datetime.now(tz.utc),
                onupdate=lambda: datetime.now(tz.utc),
            ),
        )
        # Iterations table
        self.iterations_table = Table(
            "iterations",
            self.metadata,
            Column("id", String, primary_key=True, default=lambda: str(uuid4())),
            Column("session_id", String, nullable=False),
            Column("iteration_num", Integer, nullable=False),
            Column("error", String, nullable=True),
            Column("artifacts", JSON, nullable=True, default=[]),
            Column("created_at", DateTime, default=lambda: datetime.now(tz.utc)),
        )
        # Artifacts table
        self.artifacts_table = Table(
            "artifacts",
            self.metadata,
            Column("id", String, primary_key=True, default=lambda: str(uuid4())),
            Column("session_id", String, nullable=False),
            Column("iteration_num", Integer, nullable=False),
            Column("type", String, nullable=False),
            Column("storage_path", String, nullable=False),
            Column("content_type", String, nullable=False),
            Column("created_at", DateTime, default=lambda: datetime.now(tz.utc)),
        )
        # User Repo Configs table
        self.user_repo_configs_table = Table(
            "user_repo_configs",
            self.metadata,
            Column("id", String, primary_key=True, default=lambda: str(uuid4())),
            Column("user_id", String, nullable=False),
            Column("repo_url", String, nullable=False),
            Column("default_branch", String, default="main"),
            Column("git_provider", String, default="github"),
            Column("credentials_ref", String, nullable=True),
            Column("ci_provider", String, nullable=True),
            Column("ci_workflow_id", String, nullable=True),
            Column("ci_inputs", JSON, nullable=True, default={}),
            Column("created_at", DateTime, default=lambda: datetime.now(tz.utc)),
        )
        # Processed Events (Idempotency) table
        self.processed_events_table = Table(
            "processed_events",
            self.metadata,
            Column("idempotency_key", String, primary_key=True),
            Column("result", JSON, nullable=True),
            Column("expires_at", DateTime, nullable=False),
        )

    async def initialize(self) -> bool:
        """Initialize database connection and create tables"""
        try:
            logger.info("[PERSISTENCE] Initializing Persistence Adapter...")
            # Check if PostgreSQL is configured
            provider = db_settings.DATABASE_PROVIDER
            logger.info(f"[PERSISTENCE] DATABASE_PROVIDER: {provider}")
            if provider not in ["postgres", "postgresql"]:
                logger.warning(
                    "[PERSISTENCE] PostgreSQL not configured, using fallback"
                )
                return False
            # Create engines with connection pooling
            pool_config = db_settings.get_pool_config()
            # Synchronous engine
            self.engine = create_engine(
                db_settings.postgres_url, poolclass=QueuePool, **pool_config
            )
            # Asynchronous engine
            self.async_engine = create_async_engine(
                db_settings.postgres_async_url, echo=pool_config.get("echo", False)
            )
            # Create session factories
            self.session_factory = sessionmaker(
                bind=self.engine, expire_on_commit=False
            )
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine, expire_on_commit=False, class_=AsyncSession
            )
            # Create tables
            await self._create_tables()
            self._is_initialized = True
            logger.info("[PERSISTENCE] Persistence Adapter initialized successfully")
            # Record metrics
            business_metrics.record_integration("persistence", "success", "system")
            return True
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to initialize: {str(e)}")
            return False

    async def _create_tables(self) -> None:
        """Create all tables if they don't exist"""
        try:
            # Create existing tables
            if self.engine is not None:
                self.metadata.create_all(self.engine)
            logger.info("[PERSISTENCE] Tables created successfully")
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to create tables: {str(e)}")
            raise

    def create_session(
        self,
        build_id: str,
        user_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        git_repo_url: Optional[str] = None,
        git_branch: Optional[str] = None,
        ci_provider: Optional[str] = None,
        ci_inputs: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new session state record
        Args:
            build_id: Unique build identifier
            user_id: Tenant user ID
            prompt: User's natural language request
            session_id: Optional explicit session ID
            git_repo_url: Target repository URL
            git_branch: Branch to use
            ci_provider: CI provider (e.g., 'github')
            ci_inputs: CI workflow inputs
        Returns:
            Session state dictionary
        """
        session_id = session_id or str(uuid4())
        with self.session_factory() as session:
            try:
                # Insert into session_states table
                insert_stmt = self.session_states_table.insert().values(
                    id=session_id,
                    build_id=build_id,
                    user_id=user_id,
                    prompt=prompt,
                    status="CREATED",
                    current_iteration=0,
                    git_repo_url=git_repo_url,
                    git_branch=git_branch,
                    ci_provider=ci_provider,
                    deployment_status="pending",
                    version=1,
                )
                session.execute(insert_stmt)
                session.commit()
                # Return created session
                select_stmt = self.session_states_table.select().where(
                    self.session_states_table.c.id == session_id
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                session.rollback()
                logger.error(f"[PERSISTENCE] Failed to create session: {str(e)}")
                raise

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state by ID"""
        with self.session_factory() as session:
            try:
                select_stmt = self.session_states_table.select().where(
                    self.session_states_table.c.id == session_id
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                logger.error(f"[PERSISTENCE] Failed to get session: {str(e)}")
                return None

    def update_session_status(
        self,
        session_id: str,
        status: Optional[str] = None,
        current_iteration: Optional[int] = None,
        git_repo_url: Optional[str] = None,
        git_branch: Optional[str] = None,
        git_commit_sha: Optional[str] = None,
        ci_provider: Optional[str] = None,
        ci_run_id: Optional[str] = None,
        deployment_status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update session state"""
        with self.session_factory() as session:
            try:
                # Get current version
                select_stmt = self.session_states_table.select().where(
                    self.session_states_table.c.id == session_id
                )
                row = session.execute(select_stmt).fetchone()
                if not row:
                    return None
                current_version = dict(row._mapping).get("version", 1)
                # Update session
                update_stmt = (
                    self.session_states_table.update()
                    .where(self.session_states_table.c.id == session_id)
                    .values(
                        status=status,
                        current_iteration=current_iteration,
                        git_repo_url=git_repo_url,
                        git_branch=git_branch,
                        git_commit_sha=git_commit_sha,
                        ci_provider=ci_provider,
                        ci_run_id=ci_run_id,
                        deployment_status=deployment_status,
                        error_message=error_message,
                        version=current_version + 1,
                    )
                )
                session.execute(update_stmt)
                session.commit()
                # Return updated session
                select_stmt = self.session_states_table.select().where(
                    self.session_states_table.c.id == session_id
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                session.rollback()
                logger.error(f"[PERSISTENCE] Failed to update session: {str(e)}")
                return None

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List session states with optional filters"""
        with self.session_factory() as session:
            try:
                select_stmt = self.session_states_table.select()
                if user_id:
                    select_stmt = select_stmt.where(
                        self.session_states_table.c.user_id == user_id
                    )
                if status:
                    select_stmt = select_stmt.where(
                        self.session_states_table.c.status == status
                    )
                select_stmt = select_stmt.limit(limit).offset(offset)
                rows = session.execute(select_stmt).fetchall()
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                logger.error(f"[PERSISTENCE] Failed to list sessions: {str(e)}")
                return []

    def create_iteration(
        self,
        session_id: str,
        iteration_num: int,
        error: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new iteration record"""
        iteration_id = str(uuid4())
        with self.session_factory() as session:
            try:
                insert_stmt = self.iterations_table.insert().values(
                    id=iteration_id,
                    session_id=session_id,
                    iteration_num=iteration_num,
                    error=error,
                    artifacts=artifacts or [],
                )
                session.execute(insert_stmt)
                session.commit()
                # Return created iteration
                select_stmt = self.iterations_table.select().where(
                    self.iterations_table.c.id == iteration_id
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                session.rollback()
                logger.error(f"[PERSISTENCE] Failed to create iteration: {str(e)}")
                return None

    def get_iteration(
        self, session_id: str, iteration_num: int
    ) -> Optional[Dict[str, Any]]:
        """Get iteration by session_id and iteration_num"""
        with self.session_factory() as session:
            try:
                select_stmt = self.iterations_table.select().where(
                    self.iterations_table.c.session_id == session_id,
                    self.iterations_table.c.iteration_num == iteration_num,
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                logger.error(f"[PERSISTENCE] Failed to get iteration: {str(e)}")
                return None

    def list_iterations(self, session_id: str) -> List[Dict[str, Any]]:
        """List iterations for a session"""
        with self.session_factory() as session:
            try:
                select_stmt = self.iterations_table.select().where(
                    self.iterations_table.c.session_id == session_id
                )
                rows = session.execute(select_stmt).fetchall()
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                logger.error(f"[PERSISTENCE] Failed to list iterations: {str(e)}")
                return []

    def create_artifact(
        self,
        session_id: str,
        iteration_num: int,
        artifact_type: str,
        storage_path: str,
        content_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Create a new artifact record"""
        artifact_id = str(uuid4())
        with self.session_factory() as session:
            try:
                insert_stmt = self.artifacts_table.insert().values(
                    id=artifact_id,
                    session_id=session_id,
                    iteration_num=iteration_num,
                    type=artifact_type,
                    storage_path=storage_path,
                    content_type=content_type,
                )
                session.execute(insert_stmt)
                session.commit()
                # Return created artifact
                select_stmt = self.artifacts_table.select().where(
                    self.artifacts_table.c.id == artifact_id
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                session.rollback()
                logger.error(f"[PERSISTENCE] Failed to create artifact: {str(e)}")
                return None

    def list_artifacts(
        self, session_id: str, iteration_num: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List artifacts for a session, optionally filtered by iteration"""
        with self.session_factory() as session:
            try:
                select_stmt = self.artifacts_table.select().where(
                    self.artifacts_table.c.session_id == session_id
                )
                if iteration_num is not None:
                    select_stmt = select_stmt.where(
                        self.artifacts_table.c.iteration_num == iteration_num
                    )
                rows = session.execute(select_stmt).fetchall()
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                logger.error(f"[PERSISTENCE] Failed to list artifacts: {str(e)}")
                return []

    def create_user_repo_config(
        self,
        user_id: str,
        repo_url: str,
        default_branch: Optional[str] = None,
        git_provider: Optional[str] = None,
        credentials_ref: Optional[str] = None,
        ci_provider: Optional[str] = None,
        ci_workflow_id: Optional[str] = None,
        ci_inputs: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user repository configuration"""
        config_id = str(uuid4())
        with self.session_factory() as session:
            try:
                insert_stmt = self.user_repo_configs_table.insert().values(
                    id=config_id,
                    user_id=user_id,
                    repo_url=repo_url,
                    default_branch=default_branch or "main",
                    git_provider=git_provider or "github",
                    credentials_ref=credentials_ref,
                    ci_provider=ci_provider,
                    ci_workflow_id=ci_workflow_id,
                    ci_inputs=ci_inputs or {},
                )
                session.execute(insert_stmt)
                session.commit()
                # Return created config
                select_stmt = self.user_repo_configs_table.select().where(
                    self.user_repo_configs_table.c.id == config_id
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                session.rollback()
                logger.error(
                    f"[PERSISTENCE] Failed to create user repo config: {str(e)}"
                )
                return None

    def get_user_repo_config(
        self, user_id: str, repo_url: str
    ) -> Optional[Dict[str, Any]]:
        """Get user repository configuration by user_id and repo_url"""
        with self.session_factory() as session:
            try:
                select_stmt = self.user_repo_configs_table.select().where(
                    self.user_repo_configs_table.c.user_id == user_id,
                    self.user_repo_configs_table.c.repo_url == repo_url,
                )
                row = session.execute(select_stmt).fetchone()
                return dict(row._mapping) if row else {}
            except Exception as e:
                logger.error(f"[PERSISTENCE] Failed to get user repo config: {str(e)}")
                return None

    def list_user_repo_configs(self, user_id: str) -> List[Dict[str, Any]]:
        """List all repository configurations for a user"""
        with self.session_factory() as session:
            try:
                select_stmt = self.user_repo_configs_table.select().where(
                    self.user_repo_configs_table.c.user_id == user_id
                )
                rows = session.execute(select_stmt).fetchall()
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                logger.error(
                    f"[PERSISTENCE] Failed to list user repo configs: {str(e)}"
                )
                return []

    def check_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Check if an idempotency key exists and return cached result"""
        with self.session_factory() as session:
            try:
                select_stmt = self.processed_events_table.select().where(
                    self.processed_events_table.c.idempotency_key == idempotency_key
                )
                row = session.execute(select_stmt).fetchone()
                if not row:
                    return None
                result = dict(row._mapping)
                # Check if expired
                if result["expires_at"] and result["expires_at"] < datetime.now(tz.utc):
                    # Clean up expired record
                    delete_stmt = self.processed_events_table.delete().where(
                        self.processed_events_table.c.idempotency_key == idempotency_key
                    )
                    session.execute(delete_stmt)
                    session.commit()
                    return None
                return result
            except Exception as e:
                logger.error(f"[PERSISTENCE] Failed to check idempotency: {str(e)}")
                return None

    def create_idempotency_record(
        self, idempotency_key: str, result: Dict[str, Any], ttl_seconds: int = 3600
    ) -> Optional[Dict[str, Any]]:
        """Create a new idempotency record with TTL"""
        with self.session_factory() as session:
            try:
                expires_at = datetime.now(tz.utc).timestamp() + ttl_seconds
                insert_stmt = self.processed_events_table.insert().values(
                    idempotency_key=idempotency_key,
                    result=result,
                    expires_at=datetime.fromtimestamp(expires_at, tz.utc),
                )
                session.execute(insert_stmt)
                session.commit()
                return {"idempotency_key": idempotency_key, "result": result}
            except Exception as e:
                session.rollback()
                logger.error(
                    f"[PERSISTENCE] Failed to create idempotency record: {str(e)}"
                )
                return None

    def cleanup_expired_idempotency_records(self) -> int:
        """Clean up expired idempotency records"""
        with self.session_factory() as session:
            try:
                delete_stmt = self.processed_events_table.delete().where(
                    self.processed_events_table.c.expires_at < datetime.now(tz.utc)
                )
                result = session.execute(delete_stmt)
                session.commit()
                return result.rowcount
            except Exception as e:
                session.rollback()
                logger.error(
                    f"[PERSISTENCE] Failed to cleanup expired records: {str(e)}"
                )
                return 0

    def get_engine(self) -> Any:
        """Get synchronous engine"""
        return self.engine

    def get_async_engine(self) -> Any:
        """Get asynchronous engine"""
        return self.async_engine

    @property
    def is_initialized(self) -> bool:
        """Check if adapter is initialized"""
        return self._is_initialized


# Create singleton instance


persistence_adapter = PersistenceAdapter()
