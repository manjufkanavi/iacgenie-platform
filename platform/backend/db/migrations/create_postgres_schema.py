#!/usr/bin/env python3

"""

PostgreSQL Database Schema Migration Script

This script creates all tables needed for the PostgreSQL backend migration.

"""

# nosemgrep: backend/db/migrations/create_postgres_schema.py — table names are controlled, not user input

import sys

import os

from datetime import datetime, timezone

# Add parent directory to path for imports

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from sqlalchemy import (
    create_engine,
    text,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    UUID,
    Float,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
)

from sqlalchemy.pool import QueuePool

from sqlalchemy.dialects.postgresql import JSONB

# Import database settings

from config.database import db_settings


def create_postgres_schema() -> bool:
    """Create all PostgreSQL tables for Iacgenie backend"""
    # Create engine
    engine = create_engine(
        db_settings.postgres_url,
        poolclass=QueuePool,
        pool_size=db_settings.DB_POOL_SIZE,
        max_overflow=db_settings.DB_MAX_OVERFLOW,
        pool_pre_ping=db_settings.DB_POOL_PRE_PING,
    )
    metadata = MetaData()
    # ============================================
    # Core Entity Tables
    # ============================================
    # Users table
    Table(
        "users",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("email", String(255), nullable=False, unique=True),
        Column("display_name", String(255)),
        Column("password_hash", String(255)),
        Column("role", String(50), default="user"),
        Column("is_active", Boolean, default=True),
        Column("email_verified", Boolean, default=False),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        Column("last_login_at", DateTime),
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
    )
    # Projects table
    Table(
        "projects",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("description", Text),
        Column("status", String(50), default="active"),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        Column("last_activity_at", DateTime),
        ForeignKey("users.id", ondelete="CASCADE"),
        Index("idx_projects_user_id", "user_id"),
        Index("idx_projects_status", "status"),
    )
    # Project Members table (for team collaboration)
    Table(
        "project_members",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("project_id", UUID(as_uuid=True), nullable=False),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("role", String(50), default="member"),
        Column("joined_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        ForeignKey("projects.id", ondelete="CASCADE"),
        ForeignKey("users.id", ondelete="CASCADE"),
        UniqueConstraint("project_id", "user_id", name="uq_project_members"),
        Index("idx_project_members_project_id", "project_id"),
        Index("idx_project_members_user_id", "user_id"),
    )
    # ============================================
    # Configuration Tables
    # ============================================
    # Model Configurations table
    Table(
        "model_configs",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("project_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("model", String(255), nullable=False),
        Column("provider", String(100), nullable=False),
        Column("config", JSONB, nullable=False, default={}),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        ForeignKey("projects.id", ondelete="CASCADE"),
        Index("idx_model_configs_user_id", "user_id"),
        Index("idx_model_configs_project_id", "project_id"),
        Index("idx_model_configs_provider", "provider"),
    )
    # Git Repositories table
    Table(
        "git_repositories",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("project_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("url", String(500), nullable=False),
        Column("branch", String(100), default="main"),
        Column("provider", String(50), default="github"),
        Column("credentials_ref", String(255)),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        ForeignKey("projects.id", ondelete="CASCADE"),
        Index("idx_git_repositories_user_id", "user_id"),
        Index("idx_git_repositories_project_id", "project_id"),
        Index("idx_git_repositories_provider", "provider"),
    )
    # Cloud Credentials table
    Table(
        "cloud_credentials",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("project_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("provider", String(100), nullable=False),
        Column("credentials", JSONB, nullable=False),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        ForeignKey("projects.id", ondelete="CASCADE"),
        Index("idx_cloud_credentials_user_id", "user_id"),
        Index("idx_cloud_credentials_project_id", "project_id"),
        Index("idx_cloud_credentials_provider", "provider"),
    )
    # Integrations table
    Table(
        "integrations",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("project_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("type", String(100), nullable=False),
        Column("config", JSONB, nullable=False, default={}),
        Column("status", String(50), default="active"),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        ForeignKey("projects.id", ondelete="CASCADE"),
        Index("idx_integrations_user_id", "user_id"),
        Index("idx_integrations_project_id", "project_id"),
        Index("idx_integrations_type", "type"),
        Index("idx_integrations_status", "status"),
    )
    # ============================================
    # API Keys Table
    # ============================================
    # API Keys table
    Table(
        "api_keys",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("key_hash", String(255), nullable=False, unique=True),
        Column("key_prefix", String(20), nullable=False),
        Column("scopes", JSONB, default=[]),
        Column("expires_at", DateTime),
        Column("last_used_at", DateTime),
        Column("is_active", Boolean, default=True),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        ForeignKey("users.id", ondelete="CASCADE"),
        Index("idx_api_keys_user_id", "user_id"),
        Index("idx_api_keys_key_hash", "key_hash"),
        Index("idx_api_keys_is_active", "is_active"),
    )
    # ============================================
    # Audit Logs Table
    # ============================================
    # Audit Logs table
    Table(
        "audit_logs",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("action", String(100), nullable=False),
        Column("resource_type", String(100), nullable=False),
        Column("resource_id", String(255)),
        Column("details", JSONB, default={}),
        Column("ip_address", String(45)),
        Column("user_agent", String(500)),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        ForeignKey("users.id", ondelete="CASCADE"),
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_resource_type", "resource_type"),
        Index("idx_audit_logs_created_at", "created_at"),
    )
    # ============================================
    # Billing Records Table
    # ============================================
    # Billing Records table
    Table(
        "billing_records",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("invoice_id", String(255)),
        Column("amount", Float, nullable=False),
        Column("currency", String(3), default="USD"),
        Column("status", String(50), default="pending"),
        Column("description", Text),
        Column("metadata", JSONB, default={}),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        Index("idx_billing_records_user_id", "user_id"),
        Index("idx_billing_records_status", "status"),
        Index("idx_billing_records_created_at", "created_at"),
    )
    # ============================================
    # Webhooks Tables
    # ============================================
    # Webhooks table
    Table(
        "webhooks",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("url", String(500), nullable=False),
        Column("events", JSONB, default=[]),
        Column("secret", String(255)),
        Column("is_active", Boolean, default=True),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        Index("idx_webhooks_user_id", "user_id"),
        Index("idx_webhooks_is_active", "is_active"),
    )
    # Webhook Logs table
    Table(
        "webhook_logs",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("webhook_id", UUID(as_uuid=True), nullable=False),
        Column("event_type", String(100), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("response_code", Integer),
        Column("response_body", Text),
        Column("attempted_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column("success", Boolean, default=False),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        Index("idx_webhook_logs_webhook_id", "webhook_id"),
        Index("idx_webhook_logs_attempted_at", "attempted_at"),
        Index("idx_webhook_logs_success", "success"),
    )
    # Webhook Events table (for incoming webhooks)
    Table(
        "webhook_events",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("webhook_id", UUID(as_uuid=True), nullable=False),
        Column("event_type", String(100), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("headers", JSONB, default={}),
        Column("processed", Boolean, default=False),
        Column("processed_at", DateTime),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        Index("idx_webhook_events_webhook_id", "webhook_id"),
        Index("idx_webhook_events_event_type", "event_type"),
        Index("idx_webhook_events_processed", "processed"),
        Index("idx_webhook_events_created_at", "created_at"),
    )
    # ============================================
    # Generations Table
    # ============================================
    # Generations table
    Table(
        "generations",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("project_id", UUID(as_uuid=True), nullable=False),
        Column("prompt", Text, nullable=False),
        Column("model", String(255), nullable=False),
        Column("provider", String(100), nullable=False),
        Column("status", String(50), default="pending"),
        Column("result", JSONB, default={}),
        Column("error", Text),
        Column("tokens_used", Integer, default=0),
        Column("cost", Float, default=0.0),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        Column("completed_at", DateTime),
        ForeignKey("users.id", ondelete="CASCADE"),
        ForeignKey("projects.id", ondelete="CASCADE"),
        Index("idx_generations_user_id", "user_id"),
        Index("idx_generations_project_id", "project_id"),
        Index("idx_generations_status", "status"),
        Index("idx_generations_created_at", "created_at"),
    )
    # ============================================
    # Deployments Table
    # ============================================
    # Deployments table
    Table(
        "deployments",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False),
        Column("project_id", UUID(as_uuid=True), nullable=False),
        Column("name", String(255), nullable=False),
        Column("environment", String(50), default="production"),
        Column("status", String(50), default="pending"),
        Column("config", JSONB, default={}),
        Column("metadata", JSONB, default={}),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        Column("deployed_at", DateTime),
        ForeignKey("users.id", ondelete="CASCADE"),
        ForeignKey("projects.id", ondelete="CASCADE"),
        Index("idx_deployments_user_id", "user_id"),
        Index("idx_deployments_project_id", "project_id"),
        Index("idx_deployments_status", "status"),
        Index("idx_deployments_environment", "environment"),
    )
    # ============================================
    # Persistence Layer Tables
    # ============================================
    # Session States table
    Table(
        "session_states",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("build_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("prompt", Text, nullable=True),
        Column("status", String(50), default="CREATED"),
        Column("current_iteration", Integer, default=0),
        Column("git_repo_url", String(500), nullable=True),
        Column("git_branch", String(100), nullable=True),
        Column("git_commit_sha", String(255), nullable=True),
        Column("ci_provider", String(50), nullable=True),
        Column("ci_run_id", String(255), nullable=True),
        Column("deployment_status", String(50), default="pending"),
        Column("version", Integer, default=1),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        Index("idx_session_states_build_id", "build_id"),
        Index("idx_session_states_user_id", "user_id"),
        Index("idx_session_states_status", "status"),
    )
    # Iterations table
    Table(
        "iterations",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("session_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("iteration_num", Integer, nullable=False),
        Column("error", Text, nullable=True),
        Column("artifacts", JSONB, nullable=True, default=[]),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        ForeignKey("session_states.id", ondelete="CASCADE"),
        Index("idx_iterations_session_id", "session_id"),
        Index("idx_iterations_iteration_num", "iteration_num"),
    )
    # Artifacts table
    Table(
        "artifacts",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("session_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("iteration_num", Integer, nullable=False),
        Column("type", String(50), nullable=False),
        Column("storage_path", String(500), nullable=False),
        Column("content_type", String(100), nullable=False),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        ForeignKey("session_states.id", ondelete="CASCADE"),
        Index("idx_artifacts_session_id", "session_id"),
        Index("idx_artifacts_type", "type"),
    )
    # User Repo Configs table
    Table(
        "user_repo_configs",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("repo_url", String(500), nullable=False),
        Column("default_branch", String(100), default="main"),
        Column("git_provider", String(50), default="github"),
        Column("credentials_ref", String(255), nullable=True),
        Column("ci_provider", String(50), nullable=True),
        Column("ci_workflow_id", String(255), nullable=True),
        Column("ci_inputs", JSONB, nullable=True, default={}),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        ForeignKey("users.id", ondelete="CASCADE"),
        Index("idx_user_repo_configs_user_id", "user_id"),
        Index("idx_user_repo_configs_repo_url", "repo_url"),
    )
    # Processed Events (Idempotency) table
    Table(
        "processed_events",
        metadata,
        Column("idempotency_key", String(255), primary_key=True),
        Column("result", JSONB, nullable=True),
        Column("expires_at", DateTime, nullable=False),
        Index("idx_processed_events_expires_at", "expires_at"),
    )
    # ============================================
    # Create all tables
    # ============================================
    try:
        metadata.create_all(engine)
        print("[MIGRATION] Successfully created all PostgreSQL tables:")
        print("\nCore Entity Tables:")
        print("  - users")
        print("  - projects")
        print("  - project_members")
        print("\nConfiguration Tables:")
        print("  - model_configs")
        print("  - git_repositories")
        print("  - cloud_credentials")
        print("  - integrations")
        print("\nAPI Keys Table:")
        print("  - api_keys")
        print("\nAudit Logs Table:")
        print("  - audit_logs")
        print("\nBilling Records Table:")
        print("  - billing_records")
        print("\nWebhooks Tables:")
        print("  - webhooks")
        print("  - webhook_logs")
        print("  - webhook_events")
        print("\nGenerations Table:")
        print("  - generations")
        print("\nDeployments Table:")
        print("  - deployments")
        print("\nPersistence Layer Tables:")
        print("  - session_states")
        print("  - iterations")
        print("  - artifacts")
        print("  - user_repo_configs")
        print("  - processed_events")
        return True
    except Exception as e:
        print(f"[MIGRATION] Error creating tables: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def drop_all_tables() -> bool:
    """Drop all PostgreSQL tables (for rollback)"""
    engine = create_engine(
        db_settings.postgres_url,
        poolclass=QueuePool,
        pool_size=db_settings.DB_POOL_SIZE,
        max_overflow=db_settings.DB_MAX_OVERFLOW,
    )
    metadata = MetaData()
    metadata.reflect(bind=engine)
    # Drop tables in reverse order (due to foreign key constraints)
    table_names = [
        "processed_events",
        "user_repo_configs",
        "artifacts",
        "iterations",
        "session_states",
        "deployments",
        "generations",
        "webhook_events",
        "webhook_logs",
        "webhooks",
        "billing_records",
        "audit_logs",
        "api_keys",
        "integrations",
        "cloud_credentials",
        "git_repositories",
        "model_configs",
        "project_members",
        "projects",
        "users",
    ]
    try:
        with engine.connect() as conn:
            for table_name in reversed(table_names):
                if table_name in metadata.tables:
                    # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            conn.commit()
        print("[MIGRATION] Successfully dropped all PostgreSQL tables")
        return True
    except Exception as e:
        print(f"[MIGRATION] Error dropping tables: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main() -> None:
    """Main entry point"""
    print("=" * 70)
    print("PostgreSQL Database Schema Migration")
    print("=" * 70)
    print()
    # Check if tables already exist
    engine = create_engine(db_settings.postgres_url)
    with engine.connect() as conn:
        # Check for users table
        result = conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            )
        ).fetchone()
        if result and result[0]:
            print("[WARNING] Tables already exist in the database!")
            response = input("Drop existing tables and recreate? (yes/no): ")
            if response.lower() == "yes":
                print()
                print("Dropping existing tables...")
                drop_all_tables()
            else:
                print("Aborting migration")
                return
    print()
    print("Creating all PostgreSQL tables...")
    success = create_postgres_schema()
    if success:
        print()
        print("=" * 70)
        print("Migration completed successfully!")
        print("=" * 70)
    else:
        print()
        print("=" * 70)
        print("Migration failed!")
        print("=" * 70)


if __name__ == "__main__":
    main()
