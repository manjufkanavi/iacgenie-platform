"""Initial database schema

Revision ID: 0001

Revises:

Create Date: 2025-07-13 07:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.

revision = "0001"

down_revision = None

branch_labels = None

depends_on = None


def upgrade() -> None:
    # Create users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR NOT NULL,
            email VARCHAR NOT NULL,
            name VARCHAR,
            role VARCHAR,
            is_active BOOLEAN,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            metadata JSON,
            PRIMARY KEY (id),
            UNIQUE (email)
        )
    """)
    # Create projects table
    op.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            description VARCHAR,
            status VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            metadata JSON,
            PRIMARY KEY (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create ai_generations table
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_generations (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            project_id VARCHAR,
            model VARCHAR NOT NULL,
            prompt VARCHAR NOT NULL,
            response VARCHAR,
            status VARCHAR,
            tokens_used INTEGER,
            duration_ms INTEGER,
            created_at TIMESTAMP,
            metadata JSON,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create deployments table
    op.execute("""
        CREATE TABLE IF NOT EXISTS deployments (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            platform VARCHAR NOT NULL,
            status VARCHAR,
            url VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            metadata JSON,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create model_configs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_configs (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            model_name VARCHAR NOT NULL,
            base_url VARCHAR,
            api_key_encrypted VARCHAR NOT NULL,
            secure BOOLEAN,
            max_tokens INTEGER,
            temperature DOUBLE PRECISION,
            timeout INTEGER,
            retry_attempts INTEGER,
            retry_delay DOUBLE PRECISION,
            headers JSON,
            metadata JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create git_repositories table
    op.execute("""
        CREATE TABLE IF NOT EXISTS git_repositories (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            url VARCHAR NOT NULL,
            branch VARCHAR,
            token_encrypted VARCHAR,
            ssh_key_encrypted VARCHAR,
            metadata JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create cloud_credentials table
    op.execute("""
        CREATE TABLE IF NOT EXISTS cloud_credentials (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            region VARCHAR,
            access_key_encrypted VARCHAR,
            secret_key_encrypted VARCHAR,
            credentials_encrypted VARCHAR,
            metadata JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create team_members table
    op.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            email VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            role VARCHAR NOT NULL,
            permissions JSON,
            status VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create api_keys table
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            key_encrypted VARCHAR NOT NULL,
            permissions JSON,
            status VARCHAR,
            last_used TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create audit_logs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            action VARCHAR NOT NULL,
            resource_type VARCHAR NOT NULL,
            resource_id VARCHAR,
            details JSON,
            ip_address VARCHAR,
            user_agent VARCHAR,
            created_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Create billing_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS billing_records (
            id VARCHAR NOT NULL,
            user_id VARCHAR NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            currency VARCHAR,
            description VARCHAR,
            status VARCHAR,
            metadata JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.execute("DROP TABLE IF EXISTS billing_records")
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS api_keys")
    op.execute("DROP TABLE IF EXISTS team_members")
    op.execute("DROP TABLE IF EXISTS cloud_credentials")
    op.execute("DROP TABLE IF EXISTS git_repositories")
    op.execute("DROP TABLE IF EXISTS model_configs")
    op.execute("DROP TABLE IF EXISTS deployments")
    op.execute("DROP TABLE IF EXISTS ai_generations")
    op.execute("DROP TABLE IF EXISTS projects")
    op.execute("DROP TABLE IF EXISTS users")
