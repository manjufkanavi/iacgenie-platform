"""Add module tables for workflow engine, artifacts, secrets, and git operations

Revision ID: 0002

Revises: 0001

Create Date: 2026-03-18

"""

import logging

from alembic import op

import sqlalchemy as sa

logger = logging.getLogger(__name__)


def upgrade():
    """Add module tables for new backend functionality."""
    # Artifact store tables
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("iteration_num", sa.Integer(), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),  # type: ignore[misc]
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Index("idx_session_iteration", "session_id", "iteration_num"),
    )
    logger.info("Created artifacts table")
    # Secret store tables
    op.create_table(
        "secrets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("secret_name", sa.String(255), nullable=False, index=True),
        sa.Column("vault_path", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),  # type: ignore[misc]
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),  # type: ignore[misc]
            onupdate=sa.func.now(),  # type: ignore[misc]
        ),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
        sa.Column("access_count", sa.Integer(), default=0),
        sa.Index("idx_user_secret", "user_id", "secret_name"),
    )
    logger.info("Created secrets table")
    # Git/CI-CD tables
    op.create_table(
        "git_commits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("repo_url", sa.String(500), nullable=False),
        sa.Column("branch", sa.String(100), nullable=False),
        sa.Column("commit_sha", sa.String(100), nullable=True),
        sa.Column("commit_message", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(100), unique=True, index=True),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),  # type: ignore[misc]
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),  # type: ignore[misc]
            onupdate=sa.func.now(),  # type: ignore[misc]
        ),
        sa.Index("idx_session_id", "session_id"),
        sa.Index("idx_idempotency_key", "idempotency_key"),
    )
    logger.info("Created git_commits table")
    op.create_table(
        "ci_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("git_commit_id", sa.String(36), nullable=True, index=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("run_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("workflow_file", sa.String(255), nullable=True),
        sa.Column("inputs", sa.JSON(), nullable=True),
        sa.Column("output_url", sa.String(500), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),  # type: ignore[misc]
        sa.Index("idx_session_id", "session_id"),
        sa.Index("idx_git_commit_id", "git_commit_id"),
    )
    logger.info("Created ci_runs table")
    # Workflow engine enhancements
    # Add version column to session_states for optimistic locking
    op.add_column(
        "session_states",
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
    )
    logger.info("Added version column to session_states")
    # Add state history table
    op.create_table(
        "state_transitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("from_state", sa.String(50), nullable=False),
        sa.Column("to_state", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now()),  # type: ignore[misc]
        sa.Index("idx_session_id", "session_id"),
        sa.Index("idx_timestamp", "timestamp"),
    )
    logger.info("Created state_transitions table")


def downgrade():
    """Remove module tables."""
    # Drop tables in reverse order of creation
    op.drop_table("state_transitions")
    logger.info("Dropped state_transitions table")
    # Remove version column from session_states
    op.drop_column("session_states", "version")
    logger.info("Removed version column from session_states")
    op.drop_table("ci_runs")
    logger.info("Dropped ci_runs table")
    op.drop_table("git_commits")
    logger.info("Dropped git_commits table")
    op.drop_table("secrets")
    logger.info("Dropped secrets table")
    op.drop_table("artifacts")
    logger.info("Dropped artifacts table")
