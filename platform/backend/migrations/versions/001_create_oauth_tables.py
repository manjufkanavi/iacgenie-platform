"""

OAuth 2.0 Database Migration

Creates tables for OAuth clients, tokens, and authorization codes.

Tables created:

- oauth_clients: Store registered OAuth client applications

- refresh_tokens: Refresh tokens with rotation support

- oauth_authorization_codes: Authorization codes with PKCE support

- access_tokens: Access tokens for revocation tracking

- auth_audit_logs: Security event logging

Revision ID: 001_create_oauth_tables

Revises:

Create Date: 2026-03-24

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.

revision: str = "001_create_oauth_tables"

down_revision: Union[str, None] = "0002"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create OAuth 2.0 tables (idempotent)"""
    # Create oauth_clients table
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_clients (
            id VARCHAR NOT NULL PRIMARY KEY,
            client_id VARCHAR(255) NOT NULL UNIQUE,
            client_secret_hash TEXT NOT NULL,
            client_name VARCHAR(255) NOT NULL,
            redirect_uris JSON NOT NULL,
            grant_types JSON DEFAULT '["authorization_code", "refresh_token"]',
            scope VARCHAR(255) DEFAULT 'openid profile email',
            owner_id VARCHAR,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_clients_client_id ON oauth_clients (client_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_clients_owner_id ON oauth_clients (owner_id)"
    )
    # Create refresh_tokens table
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id VARCHAR NOT NULL PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            client_id VARCHAR NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            rotated_from_id VARCHAR,
            revoked BOOLEAN DEFAULT false,
            created_at TIMESTAMP
        )
    """)
    # Create indexes for refresh tokens
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_client_id ON refresh_tokens (client_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens (token_hash)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens (expires_at)"
    )
    # Create oauth_authorization_codes table
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
            id VARCHAR NOT NULL PRIMARY KEY,
            client_id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            code_hash TEXT NOT NULL UNIQUE,
            redirect_uri VARCHAR(1024) NOT NULL,
            code_challenge VARCHAR(128),
            code_challenge_method VARCHAR(10) DEFAULT 'S256',
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT false,
            created_at TIMESTAMP
        )
    """)
    # Create indexes for authorization codes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_authorization_codes_user_id ON oauth_authorization_codes (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_authorization_codes_client_id ON oauth_authorization_codes (client_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_authorization_codes_code_hash ON oauth_authorization_codes (code_hash)"
    )
    # Create access_tokens table
    op.execute("""
        CREATE TABLE IF NOT EXISTS access_tokens (
            id VARCHAR NOT NULL PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            client_id VARCHAR NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            scopes JSON DEFAULT '["openid"]',
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP
        )
    """)
    # Create indexes for access tokens
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_access_tokens_user_id ON access_tokens (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_access_tokens_client_id ON access_tokens (client_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_access_tokens_token_hash ON access_tokens (token_hash)"
    )
    # Create auth_audit_logs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth_audit_logs (
            id VARCHAR NOT NULL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            user_id VARCHAR,
            client_id VARCHAR,
            ip_address VARCHAR(45),
            user_agent TEXT,
            details JSON,
            success BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP
        )
    """)
    # Create indexes for auth audit logs
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_logs_event_type ON auth_audit_logs (event_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_logs_user_id ON auth_audit_logs (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_logs_client_id ON auth_audit_logs (client_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_logs_created_at ON auth_audit_logs (created_at)"
    )


def downgrade() -> None:
    """Drop OAuth 2.0 tables"""
    op.execute("DROP TABLE IF EXISTS auth_audit_logs")
    op.execute("DROP TABLE IF EXISTS access_tokens")
    op.execute("DROP TABLE IF EXISTS oauth_authorization_codes")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
    op.execute("DROP TABLE IF EXISTS oauth_clients")
