"""Add authentication columns to users table and create new tables

Revision ID: 003

Revises: 002

Create Date: 2026-05-09

Adds:

- provider_type, saml_subject_id, last_login_at columns to users table

- failed_login_attempts, locked_until columns for brute force protection

- refresh_tokens table (if not exists)

- auth_audit_logs table (if not exist)

- password_history table (if not exists)

"""

from alembic import op

revision = "003"

down_revision = "001_create_oauth_tables"


def upgrade():
    """Add new columns and tables for authentication hardening (idempotent)"""
    # Add new columns to users table
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='provider_type'
            ) THEN
                ALTER TABLE users ADD COLUMN provider_type VARCHAR DEFAULT 'local';
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='saml_subject_id'
            ) THEN
                ALTER TABLE users ADD COLUMN saml_subject_id VARCHAR;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='last_login_at'
            ) THEN
                ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='failed_login_attempts'
            ) THEN
                ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='locked_until'
            ) THEN
                ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;
            END IF;
        END $$;
    """)
    # Create refresh_tokens table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            rotated_from_id TEXT,
            revoked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create auth_audit_logs table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth_audit_logs (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            user_id TEXT,
            client_id TEXT,
            ip_address TEXT,
            user_agent TEXT,
            details TEXT,
            success BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create password_history table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS password_history (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)


def downgrade():
    """Remove added columns and tables"""
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "saml_subject_id")
    op.drop_column("users", "provider_type")
    op.execute("DROP TABLE IF EXISTS password_history")
    op.execute("DROP TABLE IF EXISTS auth_audit_logs")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
