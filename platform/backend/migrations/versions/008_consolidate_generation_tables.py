"""Consolidate generation_jobs and ai_generations tables

Revision ID: 008

Revises: 007

Adds user_id, model_config_id, and metadata columns to generation_jobs,
then drops the redundant ai_generations table.

"""

from alembic import op


# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to generation_jobs
    op.execute(
        "ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS user_id VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS model_config_id VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb"
    )

    # Migrate existing ai_generations data into generation_jobs where user_id is NULL
    op.execute("""
        UPDATE generation_jobs
        SET user_id = ag.user_id,
            metadata = ag.metadata::jsonb
        FROM ai_generations ag
        WHERE generation_jobs.user_id IS NULL
          AND generation_jobs.project_id = ag.project_id
          AND ABS(EXTRACT(EPOCH FROM (generation_jobs.created_at - ag.created_at))) < 2
          AND ag.status IN ('completed', 'failed')
    """)

    # Index for user-based queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_generation_jobs_user_id ON generation_jobs (user_id)"
    )

    # Drop the redundant table
    op.execute("DROP TABLE IF EXISTS ai_generations")


def downgrade() -> None:
    # Recreate ai_generations table
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_generations (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            project_id VARCHAR(255),
            model VARCHAR(255) NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT,
            status VARCHAR(50) DEFAULT 'pending',
            tokens_used INTEGER,
            duration_ms INTEGER,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)

    # Migrate data back from generation_jobs to ai_generations
    op.execute("""
        INSERT INTO ai_generations (id, user_id, project_id, model, prompt,
            status, created_at, metadata)
        SELECT id, user_id, project_id, model, prompt,
               status, created_at,
               COALESCE(metadata, '{}'::jsonb)
        FROM generation_jobs
        WHERE user_id IS NOT NULL
    """)

    # Drop new columns from generation_jobs
    op.execute("ALTER TABLE generation_jobs DROP COLUMN IF EXISTS user_id")
    op.execute("ALTER TABLE generation_jobs DROP COLUMN IF EXISTS model_config_id")
    op.execute("ALTER TABLE generation_jobs DROP COLUMN IF EXISTS metadata")
