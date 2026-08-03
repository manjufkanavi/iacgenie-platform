"""Add LangGraph checkpointing tables

Revision ID: 005
Revises: 004
Create Date: 2026-05-25 00:00:00.000000

"""

from alembic import op

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # checkpoint_checkpoints table
    op.execute("""
        CREATE TABLE IF NOT EXISTS checkpoint_checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT,
            checkpoint BYTEA NOT NULL,
            metadata BYTEA NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        )
    """)

    # checkpoint_writes table
    op.execute("""
        CREATE TABLE IF NOT EXISTS checkpoint_writes (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            channel TEXT NOT NULL,
            type TEXT NOT NULL,
            value BYTEA NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
        )
    """)

    # checkpoint_blobs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS checkpoint_blobs (
            blob_id UUID PRIMARY KEY,
            blob BYTEA
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS checkpoint_blobs")
    op.execute("DROP TABLE IF EXISTS checkpoint_writes")
    op.execute("DROP TABLE IF EXISTS checkpoint_checkpoints")
