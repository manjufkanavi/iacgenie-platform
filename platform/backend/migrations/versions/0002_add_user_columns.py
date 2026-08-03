"""Add missing columns to users table

Revision ID: 0002

Revises: 0001

Create Date: 2026-03-24

"""

from alembic import op

# revision identifiers, used by Alembic.

revision = "0002"

down_revision = "0001"

branch_labels = None

depends_on = None


def upgrade() -> None:
    # Add email_verified column to users table
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='email_verified'
            ) THEN
                ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false;
                ALTER TABLE users ALTER COLUMN email_verified SET DEFAULT false;
            END IF;
        END $$;
    """)
    # Add password_hash column to users table
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='password_hash'
            ) THEN
                ALTER TABLE users ADD COLUMN password_hash VARCHAR;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop the added columns
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email_verified")
