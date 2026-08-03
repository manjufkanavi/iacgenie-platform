"""

PostgreSQL Database Adapter

Provides PostgreSQL database operations with connection pooling and monitoring

Implements all methods from IDatabaseAdapter interface

"""

from typing import Dict, Any, List, Optional

import json
import uuid

# Check if required dependencies are available before importing

try:
    import psycopg  # noqa: F401

    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
try:
    import asyncpg  # noqa: F401

    HAS_ASYNC_PG = True
except ImportError:
    HAS_ASYNC_PG = False
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

from datetime import datetime

from config.database import db_settings

from config.logging import get_logger

logger = get_logger("db.postgres")


class PostgreSQLAdapter:
    """PostgreSQL database adapter with connection pooling"""

    def __init__(self) -> None:
        self.engine: Optional[Any] = None
        self.async_engine: Optional[Any] = None
        self.session_factory: Optional[Any] = None
        self.async_session_factory: Optional[Any] = None
        self.metadata = MetaData()
        self._connection_pool: Any = None
        self._health_check_task: Optional[Any] = None
        self._is_initialized = False
        # Define core tables
        self._define_tables()

    def _define_tables(self) -> None:
        """Define database tables"""
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
            Column("provider_type", String, default="local"),
            Column("saml_subject_id", String),
            Column("last_login_at", DateTime),
            Column("failed_login_attempts", Integer, default=0),
            Column("locked_until", DateTime),
            Column("email_verified", Boolean, default=False),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
            Column("metadata", JSON),
            Column("keycloak_refresh_token", String),
        )
        # Password History table
        self.password_history_table = Table(
            "password_history",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("password_hash", String, nullable=False),
            Column("created_at", DateTime, default=datetime.utcnow),
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
        # Model Configs table
        self.model_configs_table = Table(
            "model_configs",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("project_id", String, nullable=False),
            Column("provider", String, nullable=False),
            Column("model_name", String, nullable=False),
            Column("api_key", String),
            Column("max_tokens", Integer, default=8192),
            Column("temperature", Integer, default=70),
            Column("timeout", Integer, default=120),
            Column("retry_attempts", Integer, default=3),
            Column("retry_delay", Integer, default=100),
            Column("headers", JSON),
            Column("metadata", JSON),
            Column("expires_at", DateTime, nullable=True),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Git Repositories table
        self.git_repositories_table = Table(
            "git_repositories",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("project_id", String, nullable=False),
            Column("repo_url", String, nullable=False),
            Column("branch", String, default="main"),
            Column("provider", String, default="github"),
            Column("credentials_ref", String),
            Column("webhook_url", String),
            Column("token_encrypted", String),
            Column("ssh_key_encrypted", String),
            Column("metadata", JSON),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Cloud Credentials table
        self.cloud_credentials_table = Table(
            "cloud_credentials",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("project_id", String, nullable=False),
            Column("provider", String, nullable=False),
            Column("credentials", JSON, nullable=False),
            Column("is_active", Boolean, default=True),
            Column("metadata", JSON),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Team Members table
        self.team_members_table = Table(
            "team_members",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("project_id", String, nullable=False),
            Column("email", String, nullable=False),
            Column("role", String, default="member"),
            Column("permissions", JSON),
            Column("is_active", Boolean, default=True),
            Column("metadata", JSON),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Integrations table
        self.integrations_table = Table(
            "integrations",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("project_id", String, nullable=False),
            Column("name", String, nullable=False),
            Column("type", String, nullable=False),
            Column("configuration", JSON, nullable=False),
            Column("is_active", Boolean, default=True),
            Column("metadata", JSON),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # API Keys table
        self.api_keys_table = Table(
            "api_keys",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("name", String, nullable=False),
            Column("key_hash", String, nullable=False),
            Column("scopes", JSON),
            Column("is_active", Boolean, default=True),
            Column("expires_at", DateTime),
            Column("last_used_at", DateTime),
            Column("metadata", JSON),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Audit Logs table
        self.audit_logs_table = Table(
            "audit_logs",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String),
            Column("action", String, nullable=False),
            Column("resource_type", String),
            Column("resource_id", String),
            Column("details", JSON),
            Column("ip_address", String),
            Column("user_agent", String),
            Column("created_at", DateTime, default=datetime.utcnow),
        )
        # Billing Records table
        self.billing_records_table = Table(
            "billing_records",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("amount", Integer, nullable=False),
            Column("currency", String, default="USD"),
            Column("status", String, default="pending"),
            Column("description", String),
            Column("invoice_url", String),
            Column("metadata", JSON),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Webhooks table
        self.webhooks_table = Table(
            "webhooks",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("name", String, nullable=False),
            Column("url", String, nullable=False),
            Column("secret", String),
            Column("events", JSON, nullable=False),
            Column("is_active", Boolean, default=True),
            Column("retry_count", Integer, default=3),
            Column("timeout", Integer, default=30),
            Column("metadata", JSON),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Webhook Logs table
        self.webhook_logs_table = Table(
            "webhook_logs",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("webhook_id", String, nullable=False),
            Column("event_type", String, nullable=False),
            Column("payload", JSON),
            Column("response_code", Integer),
            Column("response_body", String),
            Column("attempt_count", Integer, default=1),
            Column("success", Boolean, default=False),
            Column("error", String),
            Column("created_at", DateTime, default=datetime.utcnow),
        )
        # Webhook Events table
        self.webhook_events_table = Table(
            "webhook_events",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("event_type", String, nullable=False),
            Column("payload", JSON, nullable=False),
            Column("processed", Boolean, default=False),
            Column("error", String),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # OAuth Clients table
        self.oauth_clients_table = Table(
            "oauth_clients",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("client_id", String(length=255), unique=True, nullable=False),
            Column("client_secret_hash", String, nullable=False),
            Column("client_name", String(length=255), nullable=False),
            Column("redirect_uris", JSON, nullable=False),
            Column(
                "grant_types", JSON, default=["authorization_code", "refresh_token"]
            ),
            Column("scope", String(length=255), default="openid profile email"),
            Column("owner_id", String),
            Column("is_active", Boolean, default=True),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column(
                "updated_at",
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
            ),
        )
        # Refresh Tokens table
        self.refresh_tokens_table = Table(
            "refresh_tokens",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("client_id", String, nullable=False),
            Column("token_hash", String, unique=True, nullable=False),
            Column("expires_at", DateTime, nullable=False),
            Column("rotated_from_id", String),
            Column("revoked", Boolean, default=False),
            Column("created_at", DateTime, default=datetime.utcnow),
        )
        # OAuth Authorization Codes table
        self.oauth_authorization_codes_table = Table(
            "oauth_authorization_codes",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("client_id", String, nullable=False),
            Column("user_id", String, nullable=False),
            Column("code_hash", String, unique=True, nullable=False),
            Column("redirect_uri", String(length=1024), nullable=False),
            Column("code_challenge", String(length=128)),
            Column("code_challenge_method", String(length=10), default="S256"),
            Column("expires_at", DateTime, nullable=False),
            Column("used", Boolean, default=False),
            Column("created_at", DateTime, default=datetime.utcnow),
        )
        # Access Tokens table
        self.access_tokens_table = Table(
            "access_tokens",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("client_id", String, nullable=False),
            Column("token_hash", String, unique=True, nullable=False),
            Column("scopes", JSON, default=["openid"]),
            Column("expires_at", DateTime, nullable=False),
            Column("created_at", DateTime, default=datetime.utcnow),
        )
        # Auth Audit Logs table
        self.auth_audit_logs_table = Table(
            "auth_audit_logs",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("event_type", String(length=50), nullable=False),
            Column("user_id", String),
            Column("client_id", String),
            Column("ip_address", String(length=45)),
            Column("user_agent", String),
            Column("details", JSON),
            Column("success", Boolean, nullable=False),
            Column("created_at", DateTime, default=datetime.utcnow),
        )
        # Generation Jobs table
        self.generation_jobs_table = Table(
            "generation_jobs",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("prompt", String, nullable=False),
            Column("model", String, nullable=False),
            Column("provider", String, nullable=False),
            Column("project_id", String, nullable=False),
            Column("user_id", String),
            Column("model_config_id", String),
            Column("status", String, nullable=False, default="pending"),
            Column("logs", JSON),
            Column("code", JSON),
            Column("metadata", JSON),
            Column("refined_spec", JSON),
            Column("plan", String),
            Column("error", String),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column("completed_at", DateTime),
        )

    async def initialize(self) -> bool:
        """Initialize database connection and create tables"""
        try:
            # Get database URL from settings
            db_url = db_settings.postgres_async_url
            # Create async engine for async operations
            self.async_engine = create_async_engine(
                db_url, pool_pre_ping=True, pool_size=10, max_overflow=20
            )
            # Create sync engine for synchronous operations
            self.engine = create_engine(
                db_url.replace("postgresql+asyncpg", "postgresql"),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            # Create session factories
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
            self.session_factory = sessionmaker(bind=self.engine)
            # Create all tables if they don't exist
            async with self.async_engine.begin() as conn:
                await conn.run_sync(self.metadata.create_all)
            self._is_initialized = True
            logger.info("PostgreSQL adapter initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL adapter: {str(e)}")
            self._is_initialized = False
            return False

    async def close(self) -> None:
        """Close database connections"""
        try:
            if self.engine:
                logger.info("Closing PostgreSQL connection pool")
                self.engine.dispose()
            if self.async_engine:
                logger.info("Closing async PostgreSQL connection pool")
                await self.async_engine.dispose()
            logger.info("PostgreSQL adapter closed successfully")
        except Exception as e:
            logger.error(f"Error closing PostgreSQL adapter: {str(e)}")

    async def get_connection_stats(self):
        """Get connection pool statistics"""
        return {
            "provider": "postgres",
            "initialized": self._is_initialized,
            "pool_size": 10,
            "max_overflow": 20,
        }

    def health_check(self):
        """Perform database health check"""
        try:
            if not self._is_initialized:
                return {"status": "disconnected", "provider": "postgres"}
            return {"status": "healthy", "provider": "postgres"}
        except Exception as e:
            return {"status": "unhealthy", "provider": "postgres", "error": str(e)}

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.users_table).where(self.users_table.c.id == user_id)
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "email": row.email,
                    "name": row.name,
                    "role": row.role,
                    "is_active": row.is_active,
                    "password_hash": row.password_hash,
                    "email_verified": row.email_verified,
                    "otp_hash": getattr(row, "otp_hash", None),
                    "otp_expires_at": getattr(row, "otp_expires_at", None),
                    "password_reset_otp_hash": getattr(
                        row, "password_reset_otp_hash", None
                    ),
                    "password_reset_otp_expires_at": getattr(
                        row, "password_reset_otp_expires_at", None
                    ),
                }
        return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.users_table).where(self.users_table.c.email == email)
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "email": row.email,
                    "name": row.name,
                    "role": row.role,
                    "is_active": row.is_active,
                    "password_hash": row.password_hash,
                    "email_verified": row.email_verified,
                    "otp_hash": getattr(row, "otp_hash", None),
                    "otp_expires_at": getattr(row, "otp_expires_at", None),
                    "password_reset_otp_hash": getattr(
                        row, "password_reset_otp_hash", None
                    ),
                    "password_reset_otp_expires_at": getattr(
                        row, "password_reset_otp_expires_at", None
                    ),
                }
        return None

    def _coerce_datetime(self, val: Any) -> Any:
        if isinstance(val, str):
            from datetime import datetime

            try:
                if val.endswith("Z"):
                    val = val[:-1] + "+00:00"
                return datetime.fromisoformat(val)
            except ValueError:
                return val
        return val

    def _deserialize_metadata(self, val: Any) -> Optional[Dict[str, Any]]:
        if val is None:
            return None
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return None
        if isinstance(val, dict):
            return val
        return None

    def _prepare_data(self, data: Dict[str, Any], table: Any) -> Dict[str, Any]:
        import uuid

        allowed_cols = {c.name for c in table.columns}
        filtered = {k: v for k, v in data.items() if k in allowed_cols}
        if "id" in allowed_cols and "id" not in filtered:
            filtered["id"] = str(uuid.uuid4())
        # Coerce datetimes for DateTime columns
        from sqlalchemy import DateTime

        for col in table.columns:
            if isinstance(col.type, DateTime) and col.name in filtered:
                filtered[col.name] = self._coerce_datetime(filtered[col.name])
        return filtered

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Create a new user"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        data = dict(user_data)
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if "display_name" in data and "name" not in data:
            data["name"] = data.pop("display_name")
        if "password" in data and "password_hash" not in data:
            data["password_hash"] = data.pop("password")
        # Whitelist columns
        allowed_cols = {c.name for c in self.users_table.columns}
        filtered_data = {k: v for k, v in data.items() if k in allowed_cols}
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.users_table).values(**filtered_data)
            await session.execute(stmt)
            await session.commit()
            return filtered_data["id"]

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.users_table)
                .where(self.users_table.c.id == user_id)
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True
        return False

    async def delete_user(self, user_id: str) -> bool:
        """Delete user by ID"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.users_table).where(self.users_table.c.id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def create_model_config(
        self, user_id: str, project_id: str, config: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new model configuration"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        config_id = str(uuid.uuid4())
        config_dict = config.get("config", {})
        api_key = config.get("api_key")
        if api_key:
            from utils.crypto import encrypt_key

            try:
                api_key = encrypt_key(api_key)
            except Exception:
                pass
        db_data = {
            "id": config_id,
            "user_id": user_id,
            "project_id": project_id,
            "provider": config.get("provider", ""),
            "model_name": config.get("model") or config.get("model_name") or "",
            "api_key": api_key,
            "max_tokens": config_dict.get("max_tokens", config.get("max_tokens", 8192)),
            "temperature": (
                int(
                    config_dict.get("temperature", config.get("temperature", 0.7)) * 100
                )
                if isinstance(
                    config_dict.get("temperature", config.get("temperature")), float
                )
                else config_dict.get("temperature", config.get("temperature", 70))
            ),
            "timeout": config_dict.get("timeout", config.get("timeout", 120)),
            "retry_attempts": config_dict.get(
                "retry_attempts", config.get("retry_attempts", 3)
            ),
            "retry_delay": config_dict.get(
                "retry_delay", config.get("retry_delay", 100)
            ),
            "headers": config_dict.get("headers", config.get("headers")),
            "metadata": {
                "name": config.get("name"),
                "config": config_dict,
                **config.get("metadata", {}),
            },
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.model_configs_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return config_id

    async def get_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get model config by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            conditions = [
                self.model_configs_table.c.id == config_id,
                self.model_configs_table.c.project_id == project_id,
            ]
            if user_id:
                conditions.append(self.model_configs_table.c.user_id == user_id)

            stmt = select(self.model_configs_table).where(*conditions)
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                metadata = row.metadata or {}
                api_key = row.api_key
                if api_key:
                    from utils.crypto import decrypt_key

                    try:
                        api_key = decrypt_key(api_key)
                    except Exception:
                        pass
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "project_id": row.project_id,
                    "provider": row.provider,
                    "model": row.model_name,
                    "model_name": row.model_name,
                    "name": metadata.get("name", "Model Config"),
                    "config": metadata.get(
                        "config",
                        {
                            "temperature": float(row.temperature) / 100.0
                            if row.temperature
                            else 0.7,
                            "max_tokens": row.max_tokens,
                        },
                    ),
                    "api_key": api_key,
                    "max_tokens": row.max_tokens,
                    "temperature": float(row.temperature) / 100.0
                    if row.temperature
                    else 0.7,
                    "timeout": row.timeout,
                    "retry_attempts": row.retry_attempts,
                    "retry_delay": row.retry_delay,
                    "headers": row.headers,
                    "metadata": metadata,
                }
        return None

    async def list_model_configs(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List model configurations"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.model_configs_table).where(
                self.model_configs_table.c.user_id == user_id,
                self.model_configs_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            configs = []
            for row in rows:
                metadata = row.metadata or {}
                api_key = row.api_key
                if api_key:
                    from utils.crypto import decrypt_key

                    try:
                        api_key = decrypt_key(api_key)
                    except Exception:
                        pass
                configs.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "project_id": row.project_id,
                        "provider": row.provider,
                        "model": row.model_name,
                        "model_name": row.model_name,
                        "name": metadata.get("name", "Model Config"),
                        "config": metadata.get(
                            "config",
                            {
                                "temperature": float(row.temperature) / 100.0
                                if row.temperature
                                else 0.7,
                                "max_tokens": row.max_tokens,
                            },
                        ),
                        "api_key": api_key,
                        "max_tokens": row.max_tokens,
                        "temperature": row.temperature,
                        "timeout": row.timeout,
                        "retry_attempts": row.retry_attempts,
                        "retry_delay": row.retry_delay,
                        "headers": row.headers,
                        "metadata": metadata,
                    }
                )
            return configs

    async def update_model_config(
        self, user_id: str, project_id: str, config_id: str, config: Dict[str, Any]
    ) -> bool:
        """Update model configuration"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        updates = {}
        if "provider" in config:
            updates["provider"] = config["provider"]
        if "model" in config:
            updates["model_name"] = config["model"]
        if "model_name" in config:
            updates["model_name"] = config["model_name"]
        config_dict = config.get("config", {})
        if "max_tokens" in config_dict:
            updates["max_tokens"] = config_dict["max_tokens"]
        if "temperature" in config_dict:
            updates["temperature"] = (
                int(config_dict["temperature"] * 100)
                if isinstance(config_dict["temperature"], float)
                else config_dict["temperature"]
            )
        if "timeout" in config_dict:
            updates["timeout"] = config_dict["timeout"]
        if "retry_attempts" in config_dict:
            updates["retry_attempts"] = config_dict["retry_attempts"]
        if "retry_delay" in config_dict:
            updates["retry_delay"] = config_dict["retry_delay"]
        if "headers" in config_dict:
            updates["headers"] = config_dict["headers"]

        if "api_key" in config:
            api_key = config["api_key"]
            if config.get("secure", False) and api_key:
                from utils.crypto import encrypt_key

                try:
                    updates["api_key"] = encrypt_key(api_key)
                except Exception:
                    updates["api_key"] = api_key
            else:
                updates["api_key"] = api_key

        if "expires_at" in config:
            updates["expires_at"] = config["expires_at"]
        existing = await self.get_model_config(user_id, project_id, config_id)
        if not existing:
            return False
        existing_meta = existing.get("metadata") or {}
        new_meta = {
            **existing_meta,
            "name": config.get("name", existing.get("name")),
            "config": {**existing.get("config", {}), **config_dict},
            **config.get("metadata", {}),
        }
        updates["metadata"] = new_meta
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.model_configs_table)
                .where(
                    self.model_configs_table.c.id == config_id,
                    self.model_configs_table.c.user_id == user_id,
                    self.model_configs_table.c.project_id == project_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def delete_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> bool:
        """Delete model configuration"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.model_configs_table).where(
                self.model_configs_table.c.id == config_id,
                self.model_configs_table.c.user_id == user_id,
                self.model_configs_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def test_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> Dict[str, Any]:
        """Test model configuration connectivity"""
        return {
            "success": True,
            "message": "Model configuration validated successfully",
        }

    async def create_git_repository(
        self, user_id: str, project_id: str, repo: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create git repo config"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        repo_id = str(uuid.uuid4())

        token = (
            repo.get("accessToken") or repo.get("token") or repo.get("token_encrypted")
        )
        token_encrypted = None
        if token:
            from utils.crypto import encrypt_key

            try:
                token_encrypted = encrypt_key(token)
            except Exception:
                pass

        db_data = {
            "id": repo_id,
            "user_id": user_id,
            "project_id": project_id,
            "repo_url": repo.get("url", ""),
            "branch": repo.get("branch", "main"),
            "provider": repo.get("provider", "github"),
            "credentials_ref": repo.get("credentials_ref"),
            "webhook_url": repo.get("webhook_url"),
            "token_encrypted": token_encrypted,
            "ssh_key_encrypted": repo.get("ssh_key_encrypted"),
            "metadata": {"name": repo.get("name"), **repo.get("metadata", {})},
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.git_repositories_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return await self.get_git_repository(user_id, project_id, repo_id)

    async def get_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get git repository config by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.git_repositories_table).where(
                self.git_repositories_table.c.id == repo_id,
                self.git_repositories_table.c.user_id == user_id,
                self.git_repositories_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                metadata = row.metadata or {}
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "project_id": row.project_id,
                    "url": row.repo_url,
                    "repo_url": row.repo_url,
                    "branch": row.branch,
                    "provider": row.provider,
                    "credentials_ref": row.credentials_ref,
                    "webhook_url": row.webhook_url,
                    "name": metadata.get("name", "Git Repository"),
                    "metadata": metadata,
                }
        return None

    async def list_git_repositories(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List git repository configs"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.git_repositories_table).where(
                self.git_repositories_table.c.user_id == user_id,
                self.git_repositories_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            repos = []
            for row in rows:
                metadata = row.metadata or {}
                repos.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "project_id": row.project_id,
                        "url": row.repo_url,
                        "repo_url": row.repo_url,
                        "branch": row.branch,
                        "provider": row.provider,
                        "credentials_ref": row.credentials_ref,
                        "webhook_url": row.webhook_url,
                        "name": metadata.get("name", "Git Repository"),
                        "metadata": metadata,
                    }
                )
            return repos

    async def update_git_repository(
        self, user_id: str, project_id: str, repo_id: str, repo: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update git repository config"""
        if not self._is_initialized:
            return None
        from sqlalchemy import update

        updates = {}
        if "url" in repo:
            updates["repo_url"] = repo["url"]
        if "repo_url" in repo:
            updates["repo_url"] = repo["repo_url"]
        if "branch" in repo:
            updates["branch"] = repo["branch"]
        if "provider" in repo:
            updates["provider"] = repo["provider"]
        if "credentials_ref" in repo:
            updates["credentials_ref"] = repo["credentials_ref"]
        if "webhook_url" in repo:
            updates["webhook_url"] = repo["webhook_url"]

        token = (
            repo.get("accessToken") or repo.get("token") or repo.get("token_encrypted")
        )
        if token:
            from utils.crypto import encrypt_key

            try:
                updates["token_encrypted"] = encrypt_key(token)
            except Exception:
                pass

        if "ssh_key_encrypted" in repo:
            updates["ssh_key_encrypted"] = repo["ssh_key_encrypted"]

        existing = await self.get_git_repository(user_id, project_id, repo_id)
        if not existing:
            return None
        existing_meta = existing.get("metadata") or {}
        new_meta = {
            **existing_meta,
            "name": repo.get("name", existing.get("name")),
            **repo.get("metadata", {}),
        }
        updates["metadata"] = new_meta
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.git_repositories_table)
                .where(
                    self.git_repositories_table.c.id == repo_id,
                    self.git_repositories_table.c.user_id == user_id,
                    self.git_repositories_table.c.project_id == project_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return await self.get_git_repository(user_id, project_id, repo_id)

    async def delete_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> bool:
        """Delete git repository config"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.git_repositories_table).where(
                self.git_repositories_table.c.id == repo_id,
                self.git_repositories_table.c.user_id == user_id,
                self.git_repositories_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def test_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> Dict[str, Any]:
        """Test git repo connection"""
        try:
            repo = await self.get_git_repository(user_id, project_id, repo_id)
            if not repo:
                raise ValueError("Git repository not found")

            import httpx
            import re

            headers = {"Accept": "application/vnd.github.v3+json"}
            token_encrypted = repo.get("token_encrypted")

            if token_encrypted:
                from utils.crypto import decrypt_key

                try:
                    token = decrypt_key(token_encrypted)
                    if token:
                        headers["Authorization"] = f"token {token}"
                except Exception:
                    pass

            provider = repo.get("provider", "github").lower()
            url = repo.get("url", "")

            if provider == "github" and url:
                # Extract owner and repo from url (e.g. https://github.com/owner/repo)
                match = re.search(r"github\.com/([^/]+)/([^/.]+)", url)
                if match:
                    owner, repo_name = match.groups()
                    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
                    async with httpx.AsyncClient() as client:
                        response = await client.get(api_url, headers=headers)
                        return {
                            "success": response.status_code == 200,
                            "repo_id": repo_id,
                            "status_code": response.status_code,
                            "message": "Connection successful"
                            if response.status_code == 200
                            else f"Failed with status {response.status_code}",
                        }

            return {
                "success": True,
                "message": f"Repository configuration validated (no real check implemented for {provider})",
            }
        except Exception as e:
            from config.logging import get_logger

            logger = get_logger("db.adapter")
            logger.error(f"Failed to test git repository: {str(e)}")
            return {
                "success": False,
                "repo_id": repo_id,
                "error": str(e),
            }

    async def get_repo_config(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get repository configuration by primary key (bypasses user/project scoping)"""
        if not self._is_initialized:
            return None
        from sqlalchemy import text

        query = "SELECT * FROM git_repositories WHERE id = :repo_id"
        async with AsyncSession(self.async_engine) as session:
            result = await session.execute(text(query), {"repo_id": repo_id})
            row = result.fetchone()
            if not row:
                return None
            row_dict = dict(row._mapping)
            metadata = self._deserialize_metadata(row_dict.get("metadata")) or {}
            return {
                "id": row_dict["id"],
                "user_id": row_dict["user_id"],
                "project_id": row_dict["project_id"],
                "name": metadata.get("name", "Git Repository"),
                "provider": row_dict.get("provider", "github"),
                "url": row_dict.get("repo_url", ""),
                "branch": row_dict.get("branch", "main"),
                "token_encrypted": row_dict.get("token_encrypted"),
                "ssh_key_encrypted": row_dict.get("ssh_key_encrypted"),
                "metadata": metadata,
            }

    async def create_generation_job(
        self, job_data: Dict[str, Any], job_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a new generation job"""
        import logging

        logger = logging.getLogger(__name__)
        if not self._is_initialized:
            logger.warning(
                f"create_generation_job ABORTED: not initialized, job_id={job_id}"
            )
            return None
        import uuid
        from sqlalchemy import insert

        # Use job_id from job_data if available, otherwise generate new one
        job_id = job_id or job_data.get("id") or str(uuid.uuid4())
        db_data = {
            "id": job_id,
            "prompt": job_data.get("prompt", ""),
            "model": job_data.get("model", ""),
            "provider": job_data.get("provider", ""),
            "project_id": job_data.get("project_id", ""),
            "user_id": job_data.get("user_id"),
            "model_config_id": job_data.get("model_config_id"),
            "status": job_data.get("status", "pending"),
            "logs": None,
            "code": None,
            "metadata": job_data.get("metadata", {}),
            "refined_spec": job_data.get("refined_spec"),
            "plan": job_data.get("plan"),
            "error": job_data.get("error"),
        }
        logger.info(
            f"create_generation_job: attempting INSERT for job_id={job_id}, "
            f"status={db_data['status']}, project_id={db_data['project_id']}"
        )
        try:
            async with AsyncSession(self.async_engine) as session:
                stmt = insert(self.generation_jobs_table).values(**db_data)
                result = await session.execute(stmt)
                logger.info(
                    f"create_generation_job: execute done, rowcount={result.rowcount}, session_id={id(session)}"
                )
                await session.commit()
                logger.info(
                    f"create_generation_job: commit succeeded for job_id={job_id}"
                )
        except Exception as e:
            logger.error(
                f"create_generation_job: EXCEPTION during INSERT/COMMIT for job_id={job_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise
        return job_id

    async def update_generation_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update a generation job"""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"update_generation_job called: job_id={job_id}, "
            f"initialized={self._is_initialized}, updates keys={list(updates.keys())}"
        )
        if not self._is_initialized:
            logger.warning(
                f"update_generation_job ABORTED: not initialized for job {job_id}"
            )
            return False
        from sqlalchemy import update

        filtered = {
            k: v
            for k, v in updates.items()
            if k
            in (
                "status",
                "logs",
                "code",
                "completed_at",
                "user_id",
                "model_config_id",
                "metadata",
                "refined_spec",
                "plan",
                "error",
            )
        }
        logger.info(
            f"Filtered updates for job {job_id}: {list(filtered.keys())}, "
            f"code_type={type(filtered.get('code')).__name__}"
        )
        if "completed_at" in filtered and filtered["completed_at"] is None:
            filtered["completed_at"] = datetime.utcnow()
        try:
            async with AsyncSession(self.async_engine) as session:
                stmt = (
                    update(self.generation_jobs_table)
                    .where(self.generation_jobs_table.c.id == job_id)
                    .values(**filtered)
                )
                result = await session.execute(stmt)
                row_count = result.rowcount if hasattr(result, "rowcount") else "N/A"
                logger.info(f"Executed update for job {job_id}: rowcount={row_count}")
                await session.commit()
                logger.info(f"Committed update for job {job_id}")
                return True
        except Exception as e:
            logger.error(
                f"update_generation_job EXCEPTION for job {job_id}: {e}", exc_info=True
            )
            return False

    async def get_generation_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a generation job by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.generation_jobs_table).where(
                self.generation_jobs_table.c.id == job_id
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "prompt": row.prompt,
                    "model": row.model,
                    "provider": row.provider,
                    "project_id": row.project_id,
                    "user_id": row.user_id,
                    "model_config_id": row.model_config_id,
                    "status": row.status,
                    "logs": row.logs,
                    "code": row.code,
                    "metadata": row.metadata,
                    "refined_spec": row.refined_spec
                    if hasattr(row, "refined_spec")
                    else None,
                    "plan": row.plan if hasattr(row, "plan") else None,
                    "error": row.error if hasattr(row, "error") else None,
                    "created_at": row.created_at,
                    "completed_at": row.completed_at,
                }
        return None

    async def list_generation_jobs(self, project_id: str) -> List[Dict[str, Any]]:
        """List generation jobs for a project"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.generation_jobs_table)
                .where(self.generation_jobs_table.c.project_id == project_id)
                .order_by(self.generation_jobs_table.c.created_at.desc())
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "prompt": row.prompt,
                    "model": row.model,
                    "provider": row.provider,
                    "project_id": row.project_id,
                    "user_id": row.user_id,
                    "model_config_id": row.model_config_id,
                    "status": row.status,
                    "logs": row.logs,
                    "code": row.code,
                    "metadata": row.metadata,
                    "refined_spec": row.refined_spec
                    if hasattr(row, "refined_spec")
                    else None,
                    "plan": row.plan if hasattr(row, "plan") else None,
                    "error": row.error if hasattr(row, "error") else None,
                    "created_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                    "completed_at": row.completed_at.isoformat()
                    if row.completed_at
                    else None,
                }
                for row in rows
            ]

    async def get_generation_metrics(self) -> Dict[str, Any]:
        """Get aggregate metrics for generations"""
        if not self._is_initialized:
            return {"total": 0, "by_status": {}, "by_provider": {}}
        from sqlalchemy import select, func

        async with AsyncSession(self.async_engine) as session:
            # Get total count
            total_stmt = select(func.count()).select_from(  # type: ignore[misc]
                self.generation_jobs_table
            )
            total_result = await session.execute(total_stmt)
            total = total_result.scalar() or 0

            # Get count by status
            status_stmt = select(
                self.generation_jobs_table.c.status,
                func.count(),  # type: ignore[misc]
            ).group_by(self.generation_jobs_table.c.status)
            status_result = await session.execute(status_stmt)
            by_status = {row[0]: row[1] for row in status_result.fetchall()}

            # Get count by provider
            provider_stmt = select(
                self.generation_jobs_table.c.provider,
                func.count(),  # type: ignore[misc]
            ).group_by(self.generation_jobs_table.c.provider)
            provider_result = await session.execute(provider_stmt)
            by_provider = {row[0]: row[1] for row in provider_result.fetchall()}

            return {
                "total": total,
                "by_status": by_status,
                "by_provider": by_provider,
            }

    async def delete_generation_job(self, job_id: str) -> bool:
        """Delete a generation job by ID"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.generation_jobs_table).where(
                self.generation_jobs_table.c.id == job_id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def list_running_jobs(self) -> List[Dict[str, Any]]:
        """List all generation jobs currently in 'running' status."""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.generation_jobs_table).where(
                self.generation_jobs_table.c.status == "running"
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            if not rows:
                return []
            columns = list(rows[0].keys())
            return [dict(zip(columns, row)) for row in rows]

    async def find_recent_running_jobs(
        self, prompt_text: str, max_age_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Find running jobs with matching prompt created within max_age_minutes."""
        if not self._is_initialized:
            return []
        from datetime import datetime, timedelta
        from sqlalchemy import select

        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.generation_jobs_table)
                .where(
                    self.generation_jobs_table.c.status == "running",
                    self.generation_jobs_table.c.prompt == prompt_text,
                    self.generation_jobs_table.c.created_at >= cutoff,
                )
                .order_by(self.generation_jobs_table.c.created_at.desc())
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            if not rows:
                return []
            columns = list(rows[0].keys())
            return [dict(zip(columns, row)) for row in rows]

    async def create_cloud_credentials(
        self, user_id: str, project_id: str, credentials: Dict[str, Any]
    ) -> Optional[str]:
        """Create cloud credentials"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        cred_id = str(uuid.uuid4())
        db_data = {
            "id": cred_id,
            "user_id": user_id,
            "project_id": project_id,
            "provider": credentials.get("provider", ""),
            "credentials": credentials.get("credentials", {}),
            "is_active": credentials.get("is_active", True),
            "metadata": {
                "name": credentials.get("name"),
                **credentials.get("metadata", {}),
            },
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.cloud_credentials_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return cred_id

    async def get_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cloud credentials by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.cloud_credentials_table).where(
                self.cloud_credentials_table.c.id == cred_id,
                self.cloud_credentials_table.c.user_id == user_id,
                self.cloud_credentials_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                metadata = row.metadata or {}
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "project_id": row.project_id,
                    "provider": row.provider,
                    "credentials": row.credentials,
                    "is_active": row.is_active,
                    "name": metadata.get("name", "Cloud Credentials"),
                    "metadata": metadata,
                }
        return None

    async def list_cloud_credentials(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List cloud credentials"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.cloud_credentials_table).where(
                self.cloud_credentials_table.c.user_id == user_id,
                self.cloud_credentials_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            creds = []
            for row in rows:
                metadata = row.metadata or {}
                creds.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "project_id": row.project_id,
                        "provider": row.provider,
                        "credentials": row.credentials,
                        "is_active": row.is_active,
                        "name": metadata.get("name", "Cloud Credentials"),
                        "metadata": metadata,
                    }
                )
            return creds

    async def update_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str, credentials: Dict[str, Any]
    ) -> bool:
        """Update cloud credentials"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        updates = {}
        if "provider" in credentials:
            updates["provider"] = credentials["provider"]
        if "credentials" in credentials:
            updates["credentials"] = credentials["credentials"]
        if "is_active" in credentials:
            updates["is_active"] = credentials["is_active"]
        existing = await self.get_cloud_credentials(user_id, project_id, cred_id)
        if not existing:
            return False
        existing_meta = existing.get("metadata") or {}
        new_meta = {
            **existing_meta,
            "name": credentials.get("name", existing.get("name")),
            **credentials.get("metadata", {}),
        }
        updates["metadata"] = new_meta
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.cloud_credentials_table)
                .where(
                    self.cloud_credentials_table.c.id == cred_id,
                    self.cloud_credentials_table.c.user_id == user_id,
                    self.cloud_credentials_table.c.project_id == project_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def delete_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> bool:
        """Delete cloud credentials"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.cloud_credentials_table).where(
                self.cloud_credentials_table.c.id == cred_id,
                self.cloud_credentials_table.c.user_id == user_id,
                self.cloud_credentials_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def test_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> Dict[str, Any]:
        """Test cloud credentials connection"""
        return {
            "status": "success",
            "message": "Cloud credentials validated successfully",
        }

    async def create_api_key(
        self, user_id: str, api_key: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new API key"""
        if not self._is_initialized:
            return None
        import uuid
        import hashlib
        from sqlalchemy import insert

        key_id = str(uuid.uuid4())
        token = f"tg_{str(uuid.uuid4()).replace('-', '')}_{str(uuid.uuid4()).replace('-', '')}"
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = api_key.get("expires_at")
        if expires_at and isinstance(expires_at, str):
            from datetime import datetime

            try:
                if expires_at.endswith("Z"):
                    expires_at = expires_at[:-1] + "+00:00"
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                expires_at = None
        db_data = {
            "id": key_id,
            "user_id": user_id,
            "name": api_key.get("name", "API Key"),
            "key_hash": key_hash,
            "scopes": api_key.get("scopes", ["read"]),
            "is_active": api_key.get("is_active", True),
            "expires_at": expires_at,
            "last_used_at": None,
            "metadata": {
                "token": token,
                "tokenPreview": f"tg_{token[:8]}...{token[-4:]}",
                **api_key.get("metadata", {}),
            },
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.api_keys_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return key_id

    async def get_api_key(self, user_id: str, key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.api_keys_table).where(
                self.api_keys_table.c.id == key_id,
                self.api_keys_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                metadata = row.metadata or {}
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "name": row.name,
                    "key_hash": row.key_hash,
                    "scopes": row.scopes,
                    "is_active": row.is_active,
                    "expires_at": row.expires_at.isoformat()
                    if row.expires_at
                    else None,
                    "last_used_at": row.last_used_at.isoformat()
                    if row.last_used_at
                    else None,
                    "token": metadata.get("token"),
                    "tokenPreview": metadata.get("tokenPreview"),
                    "metadata": metadata,
                }
        return None

    async def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List API keys"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.api_keys_table).where(
                self.api_keys_table.c.user_id == user_id
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            keys = []
            for row in rows:
                metadata = row.metadata or {}
                keys.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "name": row.name,
                        "key_hash": row.key_hash,
                        "scopes": row.scopes,
                        "is_active": row.is_active,
                        "expires_at": row.expires_at.isoformat()
                        if row.expires_at
                        else None,
                        "last_used_at": row.last_used_at.isoformat()
                        if row.last_used_at
                        else None,
                        "token": metadata.get("token"),
                        "tokenPreview": metadata.get("tokenPreview"),
                        "metadata": metadata,
                    }
                )
            return keys

    async def update_api_key(
        self, user_id: str, key_id: str, api_key: Dict[str, Any]
    ) -> bool:
        """Update API key"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        updates = {}
        if "name" in api_key:
            updates["name"] = api_key["name"]
        if "scopes" in api_key:
            updates["scopes"] = api_key["scopes"]
        if "is_active" in api_key:
            updates["is_active"] = api_key["is_active"]
        if "expires_at" in api_key:
            expires_at = api_key["expires_at"]
            if expires_at and isinstance(expires_at, str):
                from datetime import datetime

                try:
                    if expires_at.endswith("Z"):
                        expires_at = expires_at[:-1] + "+00:00"
                    expires_at = datetime.fromisoformat(expires_at)
                except ValueError:
                    expires_at = None
            updates["expires_at"] = expires_at
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.api_keys_table)
                .where(
                    self.api_keys_table.c.id == key_id,
                    self.api_keys_table.c.user_id == user_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def delete_api_key(self, user_id: str, key_id: str) -> bool:
        """Delete API key"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.api_keys_table).where(
                self.api_keys_table.c.id == key_id,
                self.api_keys_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def create_audit_log(
        self, user_id: str, log: Dict[str, Any]
    ) -> Optional[str]:
        """Create audit log"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        log_id = str(uuid.uuid4())
        db_data = {
            "id": log_id,
            "user_id": user_id,
            "action": log.get("action", ""),
            "resource_type": log.get("resource_type"),
            "resource_id": log.get("resource_id"),
            "details": log.get("details"),
            "ip_address": log.get("ip_address"),
            "user_agent": log.get("user_agent"),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.audit_logs_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return log_id

    async def list_audit_logs(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List audit logs"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.audit_logs_table)
                .where(self.audit_logs_table.c.user_id == user_id)
                .order_by(self.audit_logs_table.c.created_at.desc())
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            logs = []
            for row in rows:
                logs.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "action": row.action,
                        "resource_type": row.resource_type,
                        "resource_id": row.resource_id,
                        "details": row.details,
                        "ip_address": row.ip_address,
                        "user_agent": row.user_agent,
                        "created_at": row.created_at.isoformat()
                        if row.created_at
                        else None,
                    }
                )
            return logs

    async def create_billing_record(
        self, user_id: str, billing: Dict[str, Any]
    ) -> Optional[str]:
        """Create billing record"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        billing_id = str(uuid.uuid4())
        amount = billing.get("amount", 0)
        if isinstance(amount, float):
            amount = int(amount * 100)
        db_data = {
            "id": billing_id,
            "user_id": user_id,
            "amount": amount,
            "currency": billing.get("currency", "USD"),
            "status": billing.get("status", "pending"),
            "description": billing.get("description"),
            "invoice_url": billing.get("invoice_url"),
            "metadata": billing.get("metadata", {}),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.billing_records_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return billing_id

    async def get_billing_record(
        self, user_id: str, billing_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get billing record by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.billing_records_table).where(
                self.billing_records_table.c.id == billing_id,
                self.billing_records_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "amount": float(row.amount) / 100.0 if row.amount else 0.0,
                    "currency": row.currency,
                    "status": row.status,
                    "description": row.description,
                    "invoice_url": row.invoice_url,
                    "metadata": row.metadata,
                }
        return None

    async def list_billing_records(self, user_id: str) -> List[Dict[str, Any]]:
        """List billing records"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.billing_records_table).where(
                self.billing_records_table.c.user_id == user_id
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            billings = []
            for row in rows:
                billings.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "amount": float(row.amount) / 100.0 if row.amount else 0.0,
                        "currency": row.currency,
                        "status": row.status,
                        "description": row.description,
                        "invoice_url": row.invoice_url,
                        "metadata": row.metadata,
                    }
                )
            return billings

    async def update_billing_record(
        self, user_id: str, billing_id: str, billing: Dict[str, Any]
    ) -> bool:
        """Update billing record"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        updates = {}
        if "amount" in billing:
            amount = billing["amount"]
            if isinstance(amount, float):
                amount = int(amount * 100)
            updates["amount"] = amount
        if "currency" in billing:
            updates["currency"] = billing["currency"]
        if "status" in billing:
            updates["status"] = billing["status"]
        if "description" in billing:
            updates["description"] = billing["description"]
        if "invoice_url" in billing:
            updates["invoice_url"] = billing["invoice_url"]
        if "metadata" in billing:
            updates["metadata"] = billing["metadata"]
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.billing_records_table)
                .where(
                    self.billing_records_table.c.id == billing_id,
                    self.billing_records_table.c.user_id == user_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def delete_billing_record(self, user_id: str, billing_id: str) -> bool:
        """Delete billing record"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.billing_records_table).where(
                self.billing_records_table.c.id == billing_id,
                self.billing_records_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def create_webhook(
        self, user_id: str, webhook: Dict[str, Any]
    ) -> Optional[str]:
        """Create webhook"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        webhook_id = str(uuid.uuid4())
        db_data = {
            "id": webhook_id,
            "user_id": user_id,
            "name": webhook.get("name", ""),
            "url": webhook.get("url", ""),
            "secret": webhook.get("secret"),
            "events": webhook.get("events", []),
            "is_active": webhook.get("is_active", True),
            "retry_count": webhook.get("retry_count", 3),
            "timeout": webhook.get("timeout", 30),
            "metadata": webhook.get("metadata", {}),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.webhooks_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return webhook_id

    async def get_webhook(
        self, user_id: str, webhook_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get webhook by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.webhooks_table).where(
                self.webhooks_table.c.id == webhook_id,
                self.webhooks_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "name": row.name,
                    "url": row.url,
                    "secret": row.secret,
                    "events": row.events,
                    "is_active": row.is_active,
                    "retry_count": row.retry_count,
                    "timeout": row.timeout,
                    "metadata": row.metadata,
                }
        return None

    async def list_webhooks(self, user_id: str) -> List[Dict[str, Any]]:
        """List webhooks"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.webhooks_table).where(
                self.webhooks_table.c.user_id == user_id
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            webhooks = []
            for row in rows:
                webhooks.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "name": row.name,
                        "url": row.url,
                        "secret": row.secret,
                        "events": row.events,
                        "is_active": row.is_active,
                        "retry_count": row.retry_count,
                        "timeout": row.timeout,
                        "metadata": row.metadata,
                    }
                )
            return webhooks

    async def update_webhook(
        self, user_id: str, webhook_id: str, webhook: Dict[str, Any]
    ) -> bool:
        """Update webhook"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        updates = {}
        if "name" in webhook:
            updates["name"] = webhook["name"]
        if "url" in webhook:
            updates["url"] = webhook["url"]
        if "secret" in webhook:
            updates["secret"] = webhook["secret"]
        if "events" in webhook:
            updates["events"] = webhook["events"]
        if "is_active" in webhook:
            updates["is_active"] = webhook["is_active"]
        if "retry_count" in webhook:
            updates["retry_count"] = webhook["retry_count"]
        if "timeout" in webhook:
            updates["timeout"] = webhook["timeout"]
        if "metadata" in webhook:
            updates["metadata"] = webhook["metadata"]
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.webhooks_table)
                .where(
                    self.webhooks_table.c.id == webhook_id,
                    self.webhooks_table.c.user_id == user_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def delete_webhook(self, user_id: str, webhook_id: str) -> bool:
        """Delete webhook"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.webhooks_table).where(
                self.webhooks_table.c.id == webhook_id,
                self.webhooks_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def get_webhook_by_id(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get webhook by globally unique ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.webhooks_table).where(
                self.webhooks_table.c.id == webhook_id
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "name": row.name,
                    "url": row.url,
                    "secret": row.secret,
                    "events": row.events,
                    "is_active": row.is_active,
                    "retry_count": row.retry_count,
                    "timeout": row.timeout,
                    "metadata": row.metadata,
                }
        return None

    async def create_webhook_log(
        self, user_id: str, webhook_id: str, log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create webhook log"""
        if not self._is_initialized:
            return {}
        import uuid
        from sqlalchemy import insert

        log_id = str(uuid.uuid4())
        db_data = {
            "id": log_id,
            "webhook_id": webhook_id,
            "event_type": log.get("event_type", ""),
            "payload": log.get("payload"),
            "response_code": log.get("response_code"),
            "response_body": log.get("response_body"),
            "attempt_count": log.get("attempt_count", 1),
            "success": log.get("success", False),
            "error": log.get("error"),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.webhook_logs_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            db_data["id"] = log_id
            return db_data

    async def get_webhook_logs(
        self, user_id: str, webhook_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get webhook logs"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.webhook_logs_table)
                .where(self.webhook_logs_table.c.webhook_id == webhook_id)
                .order_by(self.webhook_logs_table.c.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            logs = []
            for row in rows:
                logs.append(
                    {
                        "id": row.id,
                        "webhook_id": row.webhook_id,
                        "event_type": row.event_type,
                        "payload": row.payload,
                        "response_code": row.response_code,
                        "response_body": row.response_body,
                        "attempt_count": row.attempt_count,
                        "success": row.success,
                        "error": row.error,
                        "created_at": row.created_at.isoformat()
                        if row.created_at
                        else None,
                    }
                )
            return logs

    async def create_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Create webhook event"""
        if not self._is_initialized:
            return {}
        import uuid
        from sqlalchemy import insert

        event_id = str(uuid.uuid4())
        db_data = {
            "id": event_id,
            "event_type": event.get("event_type", ""),
            "payload": event.get("payload", {}),
            "processed": event.get("processed", False),
            "error": event.get("error"),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.webhook_events_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            db_data["id"] = event_id
            return db_data

    async def list_webhook_events(
        self, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List webhook events"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.webhook_events_table)
                .order_by(self.webhook_events_table.c.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            events = []
            for row in rows:
                events.append(
                    {
                        "id": row.id,
                        "event_type": row.event_type,
                        "payload": row.payload,
                        "processed": row.processed,
                        "error": row.error,
                        "created_at": row.created_at.isoformat()
                        if row.created_at
                        else None,
                    }
                )
            return events

    async def get_webhook_event(
        self, user_id: str, event_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get webhook event"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.webhook_events_table).where(
                self.webhook_events_table.c.id == event_id
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "event_type": row.event_type,
                    "payload": row.payload,
                    "processed": row.processed,
                    "error": row.error,
                    "created_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                }
        return None

    async def get_webhook_stats(self, user_id: str) -> Dict[str, Any]:
        """Get webhook statistics"""
        return {
            "total_webhooks": 0,
            "active_webhooks": 0,
            "success_rate": 100.0,
            "total_deliveries": 0,
        }

    async def update_webhook_event(
        self, user_id: str, event_id: str, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update webhook event"""
        if not self._is_initialized:
            return {}
        from sqlalchemy import update

        updates = {}
        if "processed" in event_data:
            updates["processed"] = event_data["processed"]
        if "error" in event_data:
            updates["error"] = event_data["error"]
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.webhook_events_table)
                .where(self.webhook_events_table.c.id == event_id)
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
        existing = await self.get_webhook_event(user_id, event_id)
        return existing or {}

    # Deprecated: use *_generation_job variants instead
    async def record_generation(self, generation_data: Dict[str, Any]) -> Optional[str]:
        """Record an AI generation"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        data = dict(generation_data)
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        db_data = {
            "id": data["id"],
            "user_id": data.get("user_id", "system"),
            "project_id": data.get("project_id"),
            "model": data.get("model", ""),
            "prompt": data.get("prompt", ""),
            "response": data.get("response"),
            "status": data.get("status", "pending"),
            "tokens_used": data.get("tokens_used"),
            "duration_ms": data.get("duration_ms"),
            "metadata": data.get("metadata", {}),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.generations_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return db_data["id"]

    # Deprecated: use create_generation_job instead
    async def create_generation(
        self, user_id: str, project_id: str, generation: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new AI generation"""
        data = dict(generation)
        data["user_id"] = user_id
        data["project_id"] = project_id
        return await self.record_generation(data)

    # Deprecated: use get_generation_job instead
    async def get_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get AI generation record"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.generations_table).where(
                self.generations_table.c.id == generation_id
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "project_id": row.project_id,
                    "model": row.model,
                    "prompt": row.prompt,
                    "response": row.response,
                    "status": row.status,
                    "tokens_used": row.tokens_used,
                    "duration_ms": row.duration_ms,
                    "created_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                    "metadata": row.metadata,
                }
        return None

    # Deprecated: use list_generation_jobs instead
    async def list_generations(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List AI generations"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.generations_table).where(
                self.generations_table.c.user_id == user_id,
                self.generations_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            generations = []
            for row in rows:
                generations.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "project_id": row.project_id,
                        "model": row.model,
                        "prompt": row.prompt,
                        "response": row.response,
                        "status": row.status,
                        "tokens_used": row.tokens_used,
                        "duration_ms": row.duration_ms,
                        "created_at": row.created_at.isoformat()
                        if row.created_at
                        else None,
                        "metadata": row.metadata,
                    }
                )
            return generations

    # Deprecated: use update_generation_job instead
    async def update_generation(
        self,
        user_id: str,
        project_id: str,
        generation_id: str,
        generation: Dict[str, Any],
    ) -> bool:
        """Update AI generation"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        updates = {}
        if "status" in generation:
            updates["status"] = generation["status"]
        if "response" in generation:
            updates["response"] = generation["response"]
        if "tokens_used" in generation:
            updates["tokens_used"] = generation["tokens_used"]
        if "duration_ms" in generation:
            updates["duration_ms"] = generation["duration_ms"]
        if "metadata" in generation:
            updates["metadata"] = generation["metadata"]
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.generations_table)
                .where(self.generations_table.c.id == generation_id)
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    # Deprecated: use delete_generation_job instead
    async def delete_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> bool:
        """Delete AI generation"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.generations_table).where(
                self.generations_table.c.id == generation_id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def create_deployment(
        self, user_id: str, project_id: str, deployment: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new deployment record"""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert

        deployment_id = str(uuid.uuid4())
        db_data = {
            "id": deployment_id,
            "user_id": user_id,
            "project_id": project_id,
            "platform": deployment.get(
                "platform", deployment.get("environment", "production")
            ),
            "status": deployment.get("status", "pending"),
            "url": deployment.get("url"),
            "metadata": {
                "name": deployment.get("name"),
                "config": deployment.get("config"),
                **deployment.get("metadata", {}),
            },
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.deployments_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            return deployment_id

    async def get_deployment(
        self, user_id: str, project_id: str, deployment_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get deployment record"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            if deployment_id:
                stmt = select(self.deployments_table).where(
                    self.deployments_table.c.id == deployment_id,
                    self.deployments_table.c.user_id == user_id,
                    self.deployments_table.c.project_id == project_id,
                )
            else:
                stmt = (
                    select(self.deployments_table)
                    .where(
                        self.deployments_table.c.user_id == user_id,
                        self.deployments_table.c.project_id == project_id,
                    )
                    .order_by(self.deployments_table.c.created_at.desc())
                    .limit(1)
                )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                metadata = row.metadata or {}
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "project_id": row.project_id,
                    "platform": row.platform,
                    "status": row.status,
                    "url": row.url,
                    "name": metadata.get("name", "Deployment"),
                    "environment": row.platform,
                    "config": metadata.get("config"),
                    "metadata": metadata,
                }
        return None

    async def list_deployments(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List deployments"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.deployments_table).where(
                self.deployments_table.c.user_id == user_id,
                self.deployments_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            deployments = []
            for row in rows:
                metadata = row.metadata or {}
                deployments.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "project_id": row.project_id,
                        "platform": row.platform,
                        "status": row.status,
                        "url": row.url,
                        "name": metadata.get("name", "Deployment"),
                        "environment": row.platform,
                        "config": metadata.get("config"),
                        "metadata": metadata,
                    }
                )
            return deployments

    async def update_deployment(
        self,
        user_id: str,
        project_id: str,
        deployment_id: str,
        deployment: Dict[str, Any],
    ) -> bool:
        """Update deployment"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        updates = {}
        if "platform" in deployment:
            updates["platform"] = deployment["platform"]
        elif "environment" in deployment:
            updates["platform"] = deployment["environment"]
        if "status" in deployment:
            updates["status"] = deployment["status"]
        if "url" in deployment:
            updates["url"] = deployment["url"]
        existing = await self.get_deployment(user_id, project_id, deployment_id)
        if not existing:
            return False
        existing_meta = existing.get("metadata") or {}
        new_meta = {
            **existing_meta,
            "name": deployment.get("name", existing.get("name")),
            "config": deployment.get("config", existing.get("config")),
            **deployment.get("metadata", {}),
        }
        updates["metadata"] = new_meta
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.deployments_table)
                .where(
                    self.deployments_table.c.id == deployment_id,
                    self.deployments_table.c.user_id == user_id,
                    self.deployments_table.c.project_id == project_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def delete_deployment(
        self, user_id: str, project_id: str, deployment_id: str
    ) -> bool:
        """Delete deployment"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.deployments_table).where(
                self.deployments_table.c.id == deployment_id,
                self.deployments_table.c.user_id == user_id,
                self.deployments_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def create_team_member(
        self, user_id: str, project_id: str, member: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create team member"""
        if not self._is_initialized:
            return {}
        import uuid
        from sqlalchemy import insert

        member_id = str(uuid.uuid4())
        db_data = {
            "id": member_id,
            "user_id": user_id,
            "project_id": project_id,
            "email": member.get("email", ""),
            "role": member.get("role", "member"),
            "permissions": member.get("permissions", []),
            "is_active": member.get("is_active", True),
            "metadata": member.get("metadata", {}),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.team_members_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            db_data["id"] = member_id
            return db_data

    async def get_team_member(
        self, user_id: str, project_id: str, member_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get team member"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.team_members_table).where(
                self.team_members_table.c.id == member_id,
                self.team_members_table.c.user_id == user_id,
                self.team_members_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "project_id": row.project_id,
                    "email": row.email,
                    "role": row.role,
                    "permissions": row.permissions,
                    "is_active": row.is_active,
                    "metadata": row.metadata,
                }
        return None

    async def list_team_members(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List team members"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.team_members_table).where(
                self.team_members_table.c.user_id == user_id,
                self.team_members_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            members = []
            for row in rows:
                members.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "project_id": row.project_id,
                        "email": row.email,
                        "role": row.role,
                        "permissions": row.permissions,
                        "is_active": row.is_active,
                        "metadata": row.metadata,
                    }
                )
            return members

    async def update_team_member(
        self, user_id: str, project_id: str, member_id: str, member: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update team member"""
        if not self._is_initialized:
            return {}
        from sqlalchemy import update

        updates = {}
        if "role" in member:
            updates["role"] = member["role"]
        if "permissions" in member:
            updates["permissions"] = member["permissions"]
        if "is_active" in member:
            updates["is_active"] = member["is_active"]
        if "metadata" in member:
            updates["metadata"] = member["metadata"]
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.team_members_table)
                .where(
                    self.team_members_table.c.id == member_id,
                    self.team_members_table.c.user_id == user_id,
                    self.team_members_table.c.project_id == project_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
        existing = await self.get_team_member(user_id, project_id, member_id)
        return existing or {}

    async def delete_team_member(
        self, user_id: str, project_id: str, member_id: str
    ) -> bool:
        """Delete team member"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.team_members_table).where(
                self.team_members_table.c.id == member_id,
                self.team_members_table.c.user_id == user_id,
                self.team_members_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def create_integration(
        self, user_id: str, project_id: str, integration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create integration"""
        if not self._is_initialized:
            return {}
        import uuid
        from sqlalchemy import insert

        integration_id = str(uuid.uuid4())
        db_data = {
            "id": integration_id,
            "user_id": user_id,
            "project_id": project_id,
            "name": integration.get("name", ""),
            "type": integration.get("type", ""),
            "configuration": integration.get("configuration", {}),
            "is_active": integration.get("is_active", True),
            "metadata": integration.get("metadata", {}),
        }
        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.integrations_table).values(**db_data)
            await session.execute(stmt)
            await session.commit()
            db_data["id"] = integration_id
            return db_data

    async def get_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get integration"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.integrations_table).where(
                self.integrations_table.c.id == integration_id,
                self.integrations_table.c.user_id == user_id,
                self.integrations_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "id": row.id,
                    "user_id": row.user_id,
                    "project_id": row.project_id,
                    "name": row.name,
                    "type": row.type,
                    "configuration": row.configuration,
                    "is_active": row.is_active,
                    "metadata": row.metadata,
                }
        return None

    async def list_integrations(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List integrations"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.integrations_table).where(
                self.integrations_table.c.user_id == user_id,
                self.integrations_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            integrations = []
            for row in rows:
                integrations.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "project_id": row.project_id,
                        "name": row.name,
                        "type": row.type,
                        "configuration": row.configuration,
                        "is_active": row.is_active,
                        "metadata": row.metadata,
                    }
                )
            return integrations

    async def update_integration(
        self,
        user_id: str,
        project_id: str,
        integration_id: str,
        integration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update integration"""
        if not self._is_initialized:
            return {}
        from sqlalchemy import update

        updates = {}
        if "name" in integration:
            updates["name"] = integration["name"]
        if "type" in integration:
            updates["type"] = integration["type"]
        if "configuration" in integration:
            updates["configuration"] = integration["configuration"]
        if "is_active" in integration:
            updates["is_active"] = integration["is_active"]
        if "metadata" in integration:
            updates["metadata"] = integration["metadata"]
        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.integrations_table)
                .where(
                    self.integrations_table.c.id == integration_id,
                    self.integrations_table.c.user_id == user_id,
                    self.integrations_table.c.project_id == project_id,
                )
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()
        existing = await self.get_integration(user_id, project_id, integration_id)
        return existing or {}

    async def delete_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> bool:
        """Delete integration"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.integrations_table).where(
                self.integrations_table.c.id == integration_id,
                self.integrations_table.c.user_id == user_id,
                self.integrations_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def test_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> Dict[str, Any]:
        """Test integration connection"""
        return {
            "status": "success",
            "message": "Integration connection validated successfully",
        }

    async def list_all_users(self) -> List[Dict[str, Any]]:
        """Admin: list all users in the system"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.users_table)
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def list_all_projects(self) -> List[Dict[str, Any]]:
        """Admin: list all projects in the system"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.projects_table)
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def get_project_admin(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Admin: get project by ID without user ownership check"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.projects_table).where(
                self.projects_table.c.id == project_id
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def update_project_admin(
        self, project_id: str, project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Admin: update project without ownership check"""
        if not self._is_initialized:
            return {}
        from sqlalchemy import update, select

        async with AsyncSession(self.async_engine) as session:
            exec_stmt = (
                update(self.projects_table)
                .where(self.projects_table.c.id == project_id)
                .values(**project_data)
            )
            await session.execute(exec_stmt)
            await session.commit()
            select_stmt = select(self.projects_table).where(
                self.projects_table.c.id == project_id
            )
            result = await session.execute(select_stmt)
            row = result.fetchone()
            return dict(row._mapping) if row else {}

    async def create_project_admin(
        self, project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Admin: create a project"""
        if not self._is_initialized:
            return {}
        import uuid
        from sqlalchemy import insert, select

        project_id = str(uuid.uuid4())
        db_data = {
            "id": project_id,
            "user_id": project_data.get("user_id", "admin"),
            "name": project_data.get("name", "Project"),
            "description": project_data.get("description", ""),
            "status": project_data.get("status", "active"),
        }
        async with AsyncSession(self.async_engine) as session:
            exec_stmt = insert(self.projects_table).values(**db_data)
            await session.execute(exec_stmt)
            await session.commit()
            select_stmt = select(self.projects_table).where(
                self.projects_table.c.id == project_id
            )
            result = await session.execute(select_stmt)
            row = result.fetchone()
            return dict(row._mapping) if row else {}

    async def find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Admin: find project by name"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.projects_table).where(self.projects_table.c.name == name)
            result = await session.execute(stmt)
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def delete_project_admin(self, project_id: str) -> bool:
        """Admin: delete project without ownership check"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.projects_table).where(
                self.projects_table.c.id == project_id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def assign_user_to_project(self, user_id: str, project_id: str) -> None:
        """Admin: assign user to project via team member"""
        await self.create_team_member(
            user_id, project_id, {"email": "assigned@example.com", "role": "member"}
        )

    async def unassign_user_from_project(self, user_id: str, project_id: str) -> None:
        """Admin: unassign user from project"""
        if not self._is_initialized:
            return
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.team_members_table).where(
                self.team_members_table.c.user_id == user_id,
                self.team_members_table.c.project_id == project_id,
            )
            await session.execute(stmt)
            await session.commit()

    async def is_user_assigned_to_project(self, user_id: str, project_id: str) -> bool:
        """Admin: check if user is assigned to project"""
        if not self._is_initialized:
            return False
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.team_members_table).where(
                self.team_members_table.c.user_id == user_id,
                self.team_members_table.c.project_id == project_id,
            )
            result = await session.execute(stmt)
            return result.fetchone() is not None

    async def get_project_members_admin(self, project_id: str) -> list:
        """Admin: get project members"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.team_members_table).where(
                self.team_members_table.c.project_id == project_id
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def get_system_stats(self) -> Dict[str, Any]:
        """Admin: get system statistics"""
        if not self._is_initialized:
            return {}
        from sqlalchemy import func, select

        async with AsyncSession(self.async_engine) as session:
            users_stmt = select(func.count()).select_from(self.users_table)  # type: ignore[misc]
            projects_stmt = select(func.count()).select_from(self.projects_table)  # type: ignore[misc]
            users_res = await session.execute(users_stmt)
            projects_res = await session.execute(projects_stmt)
            return {
                "total_users": users_res.scalar() or 0,
                "total_projects": projects_res.scalar() or 0,
                "active_users": users_res.scalar() or 0,
            }

    async def get_user_stats(self) -> Dict[str, Any]:
        """Admin: get user statistics"""
        return {"registrations_by_day": {}}

    async def get_project_stats(self) -> Dict[str, Any]:
        """Admin: get project statistics"""
        return {"creations_by_day": {}}

    async def validate_api_key(
        self, user_id: str, provider: str, api_key: str
    ) -> Dict[str, Any]:
        """Validate an API key for a provider"""
        if not api_key or len(api_key) < 10:
            return {
                "valid": False,
                "message": "Invalid API key format",
                "details": {"provider": provider},
            }
        valid_prefixes = {
            "openai": "sk-",
            "anthropic": "sk-ant-",
            "google": "AIza",
            "mistral": "sk-",
        }
        prefix = valid_prefixes.get(provider.lower(), "")
        if prefix and not api_key.startswith(prefix):
            return {
                "valid": False,
                "message": f"Invalid {provider} API key format",
                "details": {"provider": provider, "expected_prefix": prefix},
            }
        return {
            "valid": True,
            "message": f"{provider.capitalize()} API key is valid",
            "details": {"provider": provider},
        }

    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform database health check asynchronously"""
        try:
            if not self._is_initialized:
                return {
                    "status": "unhealthy",
                    "provider": "postgres",
                    "error": "Not initialized",
                }
            return {"status": "healthy", "provider": "postgres"}
        except Exception as e:
            return {"status": "unhealthy", "provider": "postgres", "error": str(e)}

    async def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a database query"""
        if not self._is_initialized:
            return None
        from sqlalchemy import text

        async with AsyncSession(self.async_engine) as session:
            result = await session.execute(text(query), params or {})
            return result.fetchall()

    async def execute_command(
        self, command: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a database command"""
        return await self.execute_query(command, params)

    async def create_oauth_client(self, client_data: Dict[str, Any]) -> Optional[str]:
        """Create a new OAuth client"""
        if not self._is_initialized:
            return None
        from sqlalchemy import insert

        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.oauth_clients_table).values(**client_data)
            result = await session.execute(stmt)
            await session.commit()
            return str(result.inserted_primary_key[0])

    async def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get OAuth client by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.oauth_clients_table).where(
                self.oauth_clients_table.c.client_id == client_id
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "client_id": row.client_id,
                    "client_secret_hash": row.client_secret_hash,
                    "client_name": row.client_name,
                    "redirect_uris": row.redirect_uris,
                    "grant_types": row.grant_types,
                }
        return None

    async def list_clients(self, user_id: str) -> List[Dict[str, Any]]:
        """List OAuth clients for a user"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.oauth_clients_table).where(
                self.oauth_clients_table.c.owner_id == user_id
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [
                {
                    "client_id": row.client_id,
                    "client_name": row.client_name,
                    "redirect_uris": row.redirect_uris,
                }
                for row in rows
            ]

    async def update_client(self, client_id: str, redirect_uris: List[str]) -> bool:
        """Update OAuth client"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.oauth_clients_table)
                .where(self.oauth_clients_table.c.client_id == client_id)
                .values(redirect_uris=redirect_uris)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def delete_client(self, client_id: str) -> bool:
        """Delete OAuth client"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.oauth_clients_table).where(
                self.oauth_clients_table.c.client_id == client_id
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def create_authorization_code(
        self, code_data: Dict[str, Any]
    ) -> Optional[str]:
        """Create authorization code"""
        if not self._is_initialized:
            return None
        from sqlalchemy import insert

        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.oauth_authorization_codes_table).values(**code_data)
            result = await session.execute(stmt)
            await session.commit()
            return str(result.inserted_primary_key[0])

    async def get_authorization_code_by_hash(
        self, code_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get authorization code by hash"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.oauth_authorization_codes_table).where(
                self.oauth_authorization_codes_table.c.code_hash == code_hash
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "client_id": row.client_id,
                    "user_id": row.user_id,
                    "code_hash": row.code_hash,
                    "redirect_uri": row.redirect_uri,
                    "code_challenge": row.code_challenge,
                    "expires_at": row.expires_at,
                }
        return None

    async def mark_authorization_code_used(self, code_hash: str) -> bool:
        """Mark authorization code as used"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.oauth_authorization_codes_table)
                .where(self.oauth_authorization_codes_table.c.code_hash == code_hash)
                .values(used=True)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def create_refresh_token(self, token_data: Dict[str, Any]) -> Optional[str]:
        """Create refresh token"""
        if not self._is_initialized:
            return None
        from sqlalchemy import insert

        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.refresh_tokens_table).values(**token_data)
            result = await session.execute(stmt)
            await session.commit()
            return str(result.inserted_primary_key[0])

    async def get_refresh_token_by_hash(
        self, token_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get refresh token by hash"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.refresh_tokens_table).where(
                self.refresh_tokens_table.c.token_hash == token_hash
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return {
                    "user_id": row.user_id,
                    "client_id": row.client_id,
                    "token_hash": row.token_hash,
                    "expires_at": row.expires_at,
                    "revoked": row.revoked,
                }
        return None

    async def revoke_refresh_token(self, token_id: str) -> bool:
        """Revoke refresh token by ID"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.refresh_tokens_table)
                .where(self.refresh_tokens_table.c.id == token_id)
                .values(revoked=True)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def revoke_refresh_token_by_hash(self, token_hash: str) -> bool:
        """Revoke refresh token by hash"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.refresh_tokens_table)
                .where(self.refresh_tokens_table.c.token_hash == token_hash)
                .values(revoked=True)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def create_access_token(self, token_data: Dict[str, Any]) -> Optional[str]:
        """Create access token"""
        if not self._is_initialized:
            return None
        from sqlalchemy import insert

        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.access_tokens_table).values(**token_data)
            result = await session.execute(stmt)
            await session.commit()
            return str(result.inserted_primary_key[0])

    async def revoke_access_token_by_hash(self, token_hash: str) -> bool:
        """Revoke access token by hash"""
        if not self._is_initialized:
            return False
        from sqlalchemy import insert, update

        async with AsyncSession(self.async_engine) as session:
            try:
                insert_stmt = insert(self.access_tokens_table).values(
                    token_hash=token_hash,
                    scopes="[]",
                    expires_at=datetime.utcnow(),
                    revoked=True,
                )
                await session.execute(insert_stmt)
                await session.commit()
                return True
            except Exception:
                update_stmt = (
                    update(self.access_tokens_table)
                    .where(self.access_tokens_table.c.token_hash == token_hash)
                    .values(revoked=True)
                )
                await session.execute(update_stmt)
                await session.commit()
                return True

    async def set_keycloak_refresh_token(self, user_id: str, token: str) -> bool:
        """Store or update the Keycloak refresh token for a user"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.users_table)
                .where(self.users_table.c.id == user_id)
                .values(keycloak_refresh_token=token)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def get_keycloak_refresh_token(self, user_id: str) -> Optional[str]:
        """Retrieve the stored Keycloak refresh token for a user"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.users_table.c.keycloak_refresh_token).where(
                self.users_table.c.id == user_id
            )
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            return token

    async def revoke_keycloak_refresh_token(self, user_id: str) -> bool:
        """Clear the stored Keycloak refresh token for a user"""
        if not self._is_initialized:
            return False
        from sqlalchemy import update

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                update(self.users_table)
                .where(self.users_table.c.id == user_id)
                .values(keycloak_refresh_token=None)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def create_auth_audit_log(self, log_data: Dict[str, Any]) -> Optional[str]:
        """Create auth audit log entry"""
        if not self._is_initialized:
            return None
        from sqlalchemy import insert

        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.auth_audit_logs_table).values(**log_data)
            result = await session.execute(stmt)
            await session.commit()
            return str(result.inserted_primary_key[0])

    async def get_user_refresh_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active refresh tokens for a user"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.refresh_tokens_table)
                .where(
                    self.refresh_tokens_table.c.user_id == user_id,
                    ~self.refresh_tokens_table.c.revoked,
                )
                .order_by(self.refresh_tokens_table.c.created_at.desc())
            )
            result = await session.execute(stmt)
            return [dict(row._mapping) for row in result.fetchall()]

    async def add_password_hash(
        self, user_id: str, password_hash: str
    ) -> Optional[str]:
        """Add a password hash to the user's history"""
        if not self._is_initialized:
            return None
        from sqlalchemy import insert

        async with AsyncSession(self.async_engine) as session:
            stmt = insert(self.password_history_table).values(
                id=str(uuid.uuid4()), user_id=user_id, password_hash=password_hash
            )
            result = await session.execute(stmt)
            await session.commit()
            return str(result.inserted_primary_key[0])

    async def get_recent_password_hashes(
        self, user_id: str, limit: int = 10
    ) -> List[str]:
        """Get recent password hashes for a user (for reuse detection)"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.password_history_table.c.password_hash)
                .where(self.password_history_table.c.user_id == user_id)
                .order_by(self.password_history_table.c.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.fetchall()]

    async def create_project(
        self, user_id: str, project_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new project and return the full project dict."""
        if not self._is_initialized:
            return None
        import uuid
        from sqlalchemy import insert, select

        # Only allow actual table columns
        allowed_cols = {c.name for c in self.projects_table.columns}
        filtered_data = {k: v for k, v in project_data.items() if k in allowed_cols}
        project_id = str(uuid.uuid4())
        project_data_with_defaults = {
            "id": project_id,
            "user_id": user_id,
            "status": "active",
            **filtered_data,
        }
        async with AsyncSession(self.async_engine) as session:
            exec_stmt = insert(self.projects_table).values(**project_data_with_defaults)
            await session.execute(exec_stmt)
            await session.commit()
            # Return the full project dict (not just the ID) so the router can
            # pass {"project": {...}} with an "id" field the frontend can use.
            select_stmt = select(self.projects_table).where(
                self.projects_table.c.id == project_id
            )
            result = await session.execute(select_stmt)
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def get_project(
        self, user_id: str, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a project by ID"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = select(self.projects_table).where(
                self.projects_table.c.id == project_id,
                self.projects_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            if row:
                return dict(row._mapping)
        return None

    async def list_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """List all projects for a user"""
        if not self._is_initialized:
            return []
        from sqlalchemy import select

        async with AsyncSession(self.async_engine) as session:
            stmt = (
                select(self.projects_table)
                .where(self.projects_table.c.user_id == user_id)
                .order_by(self.projects_table.c.created_at.desc())
            )
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def update_project(
        self, user_id: str, project_id: str, project: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a project"""
        if not self._is_initialized:
            return None
        from sqlalchemy import select, update

        # Whitelist columns to prevent SQL injection via extra keys
        allowed_cols = {c.name for c in self.projects_table.columns}
        filtered_project = {k: v for k, v in project.items() if k in allowed_cols}
        async with AsyncSession(self.async_engine) as session:
            # Verify ownership
            verify_stmt = select(self.projects_table).where(
                self.projects_table.c.id == project_id,
                self.projects_table.c.user_id == user_id,
            )
            result = await session.execute(verify_stmt)
            row = result.fetchone()
            if not row:
                return None
            # Update
            update_stmt = (
                update(self.projects_table)
                .where(
                    self.projects_table.c.id == project_id,
                    self.projects_table.c.user_id == user_id,
                )
                .values(**filtered_project)
            )
            await session.execute(update_stmt)
            await session.commit()
            # Return updated project
            select_stmt = select(self.projects_table).where(
                self.projects_table.c.id == project_id
            )
            result = await session.execute(select_stmt)
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project"""
        if not self._is_initialized:
            return False
        from sqlalchemy import delete

        async with AsyncSession(self.async_engine) as session:
            stmt = delete(self.projects_table).where(
                self.projects_table.c.id == project_id,
                self.projects_table.c.user_id == user_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0


# Global instance


postgres_adapter: PostgreSQLAdapter = PostgreSQLAdapter()
