"""Add generation metrics table

Revision ID: 007

Revises: 006

Creates generation_metrics table for LLM analytics tracking.

"""

from alembic import op


# revision identifiers

revision = "007"

down_revision = "006"

branch_labels = None

depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS generation_metrics (
            id UUID PRIMARY KEY,
            project_id VARCHAR(255) NOT NULL,
            tenant_id VARCHAR(255) NOT NULL,
            generation_id VARCHAR(255) NOT NULL UNIQUE,
            requested_model VARCHAR(255) NOT NULL,
            model_used VARCHAR(255) NOT NULL,
            provider VARCHAR(255) NOT NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            total_cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            latency_ms DOUBLE PRECISION,
            is_cached BOOLEAN NOT NULL DEFAULT FALSE,
            failover_occurred BOOLEAN NOT NULL DEFAULT FALSE,
            failover_from VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_metrics_project_date ON generation_metrics (project_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_metrics_tenant_date ON generation_metrics (tenant_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS generation_metrics")
