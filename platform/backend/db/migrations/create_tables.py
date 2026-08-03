#!/usr/bin/env python3

"""

Database Migration Script: Create New Persistence Tables

This script creates the new persistence layer tables (session_states, iterations,

"""

# nosemgrep: backend/db/migrations/create_tables.py — table names are controlled, not user input

import sys

from datetime import datetime, timezone

# Add parent directory to path for imports

sys.path.insert(0, "/Users/manjunathkanavi/workspace/git_workspace/iacgenie")

from sqlalchemy import (
    create_engine,
    text,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    UUID,
)

from sqlalchemy.pool import QueuePool

# Import database settings

from config.database import db_settings


def create_tables() -> bool:
    """Create new persistence layer tables"""
    # Create engine
    engine = create_engine(
        db_settings.postgres_url,
        poolclass=QueuePool,
        pool_size=db_settings.DB_POOL_SIZE,
        max_overflow=db_settings.DB_MAX_OVERFLOW,
    )
    metadata = MetaData()
    # Define new persistence tables
    # Session States table
    Table(
        "session_states",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("build_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("prompt", String, nullable=True),
        Column("status", String, default="CREATED"),
        Column("current_iteration", Integer, default=0),
        Column("git_repo_url", String, nullable=True),
        Column("git_branch", String, nullable=True),
        Column("git_commit_sha", String, nullable=True),
        Column("ci_provider", String, nullable=True),
        Column("ci_run_id", String, nullable=True),
        Column("deployment_status", String, default="pending"),
        Column("version", Integer, default=1),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
    )
    # Iterations table
    Table(
        "iterations",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("session_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("iteration_num", Integer, nullable=False),
        Column("error", String, nullable=True),
        Column("artifacts", JSON, nullable=True, default=[]),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    )
    # Artifacts table
    Table(
        "artifacts",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("session_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("iteration_num", Integer, nullable=False),
        Column("type", String, nullable=False),
        Column("storage_path", String, nullable=False),
        Column("content_type", String, nullable=False),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    )
    # User Repo Configs table
    Table(
        "user_repo_configs",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        Column("repo_url", String, nullable=False),
        Column("default_branch", String, default="main"),
        Column("git_provider", String, default="github"),
        Column("credentials_ref", String, nullable=True),
        Column("ci_provider", String, nullable=True),
        Column("ci_workflow_id", String, nullable=True),
        Column("ci_inputs", JSON, nullable=True, default={}),
        Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    )
    # Processed Events (Idempotency) table
    Table(
        "processed_events",
        metadata,
        Column("idempotency_key", String, primary_key=True),
        Column("result", JSON, nullable=True),
        Column("expires_at", DateTime, nullable=False),
    )
    # Create all tables
    try:
        metadata.create_all(engine)
        print("[MIGRATION] Successfully created new persistence tables:")
        print("  - session_states")
        print("  - iterations")
        print("  - artifacts")
        print("  - user_repo_configs")
        print("  - processed_events")
        return True
    except Exception as e:
        print(f"[MIGRATION] Error creating tables: {str(e)}")
        return False


def drop_tables() -> bool:
    """Drop new persistence layer tables (for rollback)"""
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
    ]
    try:
        with engine.connect() as conn:
            for table_name in reversed(table_names):
                if table_name in metadata.tables:
                    # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            conn.commit()
        print("[MIGRATION] Successfully dropped new persistence tables")
        return True
    except Exception as e:
        print(f"[MIGRATION] Error dropping tables: {str(e)}")
        return False


def main() -> None:
    """Main entry point"""
    print("=" * 60)
    print("Database Migration: Create New Persistence Tables")
    print("=" * 60)
    print()
    # Check if tables already exist
    engine = create_engine(db_settings.postgres_url)
    with engine.connect() as conn:
        # Check for session_states table
        result = conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'session_states')"
            )
        ).fetchone()
        if result and result[0]:
            print("[WARNING] session_states table already exists!")
            response = input("Drop existing tables and recreate? (yes/no): ")
            if response.lower() == "yes":
                print()
                print("Dropping existing tables...")
                drop_tables()
            else:
                print("Aborting migration")
                return
    print()
    print("Creating new persistence tables...")
    success = create_tables()
    if success:
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("Migration failed!")
        print("=" * 60)


if __name__ == "__main__":
    main()
