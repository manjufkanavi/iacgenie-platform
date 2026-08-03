"""Add pipeline state management tables

Revision ID: 004

Revises: 003

Create Date: 2026-05-12 00:00:00.000000

Creates three tables for pipeline state management:

- pipelines: Main pipeline state tracking

- pipeline_phase_history: Per-phase execution history

- pipeline_logs: Structured log entries

"""

from alembic import op


# revision identifiers

revision = "004"

down_revision = "003"

branch_labels = None

depends_on = None


def upgrade() -> None:
    # pipelines table
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipelines (
            id UUID PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL UNIQUE,
            tenant_id UUID NOT NULL,
            workspace_id UUID,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            phase VARCHAR(32) NOT NULL DEFAULT 'clarify',
            status VARCHAR(16) NOT NULL DEFAULT 'running',
            current_phase_progress INTEGER NOT NULL DEFAULT 0,
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            error_count INTEGER NOT NULL DEFAULT 0,
            refined_spec JSONB,
            generated_files_s3_key VARCHAR(500),
            error_message TEXT,
            error_phase VARCHAR(32),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            created_by VARCHAR(255)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pipelines_session_id ON pipelines (session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pipelines_tenant_id ON pipelines (tenant_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pipelines_status ON pipelines (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pipelines_tenant_status ON pipelines (tenant_id, status)"
    )
    # pipeline_phase_history table
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_phase_history (
            id UUID PRIMARY KEY,
            pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
            phase VARCHAR(32) NOT NULL,
            status VARCHAR(16) NOT NULL,
            duration_seconds INTEGER,
            started_at TIMESTAMP WITH TIME ZONE NOT NULL,
            completed_at TIMESTAMP WITH TIME ZONE,
            details JSONB,
            retry_number INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_phase_history_pipeline_id ON pipeline_phase_history (pipeline_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_phase_history_pipeline_phase ON pipeline_phase_history (pipeline_id, phase)"
    )
    # pipeline_logs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_logs (
            id UUID PRIMARY KEY,
            pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            phase VARCHAR(32),
            message TEXT NOT NULL,
            level VARCHAR(10) NOT NULL DEFAULT 'info',
            metadata JSONB
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pipeline_logs_pipeline_id ON pipeline_logs (pipeline_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pipeline_logs_pipeline_timestamp ON pipeline_logs (pipeline_id, timestamp)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pipeline_logs")
    op.execute("DROP TABLE IF EXISTS pipeline_phase_history")
    op.execute("DROP TABLE IF EXISTS pipelines")
