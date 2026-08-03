#!/usr/bin/env python3

"""

PostgreSQL Database Initialization Script

This script initializes the PostgreSQL database for IaCGenie backend.

"""

# nosemgrep: backend/db/migrations/init_postgres.py — DB names from env config, not user input

import sys

import os

import asyncio

from datetime import datetime, timezone

# Add parent directory to path for imports

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from sqlalchemy import create_engine, text

from sqlalchemy.pool import QueuePool

# Import database settings

from config.database import db_settings


async def create_database_if_not_exists() -> bool:
    """Create the database if it doesn't exist"""
    # Connect to the default 'postgres' database to create the target database
    default_db_url = db_settings.postgres_url.replace(
        f"/{db_settings.POSTGRES_DATABASE}", "/postgres"
    )
    engine = create_engine(default_db_url)
    try:
        with engine.connect() as conn:
            # Check if database exists
            _db_name = db_settings.POSTGRES_DATABASE
            result = conn.execute(
                # nosemgrep: avoid-sqlalchemy-text
                text(f"SELECT 1 FROM pg_database WHERE datname='{_db_name}'")
            ).fetchone()
            if not result:
                # Create database
                conn.execute(text("COMMIT"))
                _db_name = db_settings.POSTGRES_DATABASE
                conn.execute(
                    # nosemgrep: avoid-sqlalchemy-text
                    text(
                        f"CREATE DATABASE {_db_name} ENCODING 'UTF8' "
                        f"LC_COLLATE='en_US.UTF-8' "
                        f"LC_CTYPE='en_US.UTF-8' TEMPLATE=template0"
                    )
                )
                conn.commit()
                print(f"[INIT] Created database: {db_settings.POSTGRES_DATABASE}")
            else:
                print(
                    f"[INIT] Database already exists: {db_settings.POSTGRES_DATABASE}"
                )
        return True
    except Exception as e:
        print(f"[INIT] Error creating database: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        engine.dispose()


async def create_extensions() -> bool:
    """Create required PostgreSQL extensions"""
    engine = create_engine(
        db_settings.postgres_url,
        poolclass=QueuePool,
        pool_size=db_settings.DB_POOL_SIZE,
        max_overflow=db_settings.DB_MAX_OVERFLOW,
    )
    try:
        with engine.connect() as conn:
            # Create uuid-ossp extension for UUID generation
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            # Create pgcrypto for cryptographic functions
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
            conn.commit()
            print("[INIT] Created required PostgreSQL extensions")
        return True
    except Exception as e:
        print(f"[INIT] Error creating extensions: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        engine.dispose()


async def seed_initial_data() -> bool:
    """Seed the database with initial data"""
    import uuid

    engine = create_engine(
        db_settings.postgres_url,
        poolclass=QueuePool,
        pool_size=db_settings.DB_POOL_SIZE,
        max_overflow=db_settings.DB_MAX_OVERFLOW,
    )
    try:
        with engine.connect() as conn:
            # Check if admin user already exists
            result = conn.execute(
                text("SELECT 1 FROM users WHERE email = 'admin@iacgenie.ai'")
            ).fetchone()
            if not result:
                # Create admin user
                admin_user_id = str(uuid.uuid4())
                from utils.password_utils import hash_password

                admin_password_hash = hash_password(
                    "admin123"
                )  # Change this in production!
                conn.execute(
                    text("""
                    INSERT INTO users
                        (id, email, display_name, password_hash, role,
                         is_active, email_verified, created_at, updated_at)
                    VALUES (:id, :email, :display_name, :password_hash,
                            :role, :is_active, :email_verified,
                            :created_at, :updated_at)
                """),
                    {
                        "id": admin_user_id,
                        "email": "admin@iacgenie.ai",
                        "display_name": "System Administrator",
                        "password_hash": admin_password_hash,
                        "role": "admin",
                        "is_active": True,
                        "email_verified": True,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    },
                )
                print(
                    "[INIT] Created admin user: admin@iacgenie.ai (password: admin123)"
                )
                print("[WARNING] Please change the admin password in production!")
            else:
                print("[INIT] Admin user already exists")
            conn.commit()
        return True
    except Exception as e:
        print(f"[INIT] Error seeding initial data: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        engine.dispose()


async def run_schema_migration() -> bool:
    """Run the schema migration script"""
    print("[INIT] Running schema migration...")
    # Import and run the schema migration
    from db.migrations.create_postgres_schema import create_postgres_schema

    success = create_postgres_schema()
    if success:
        print("[INIT] Schema migration completed successfully")
    else:
        print("[INIT] Schema migration failed")
    return success


async def verify_database() -> bool:
    """Verify that the database is properly initialized"""
    engine = create_engine(
        db_settings.postgres_url,
        poolclass=QueuePool,
        pool_size=db_settings.DB_POOL_SIZE,
        max_overflow=db_settings.DB_MAX_OVERFLOW,
    )
    try:
        with engine.connect() as conn:
            # Check for core tables
            tables_to_check = [
                "users",
                "projects",
                "model_configs",
                "git_repositories",
                "cloud_credentials",
                "integrations",
                "api_keys",
                "audit_logs",
                "billing_records",
                "webhooks",
                "webhook_logs",
                "webhook_events",
                "generations",
                "deployments",
                "session_states",
                "iterations",
                "artifacts",
                "user_repo_configs",
                "processed_events",
            ]
            existing_tables = []
            missing_tables = []
            for table_name in tables_to_check:
                query = text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
                )
                result = conn.execute(query, {"table_name": table_name}).fetchone()
                if result and result[0]:
                    existing_tables.append(table_name)
                else:
                    missing_tables.append(table_name)
            print("\n[INIT] Database verification:")
            print(f"  - Existing tables: {len(existing_tables)}/{len(tables_to_check)}")
            print(f"  - Missing tables: {len(missing_tables)}")
            if missing_tables:
                print(f"\n[WARNING] Missing tables: {', '.join(missing_tables)}")
                return False
            else:
                print("\n[INIT] All required tables exist")
                return True
    except Exception as e:
        print(f"[INIT] Error verifying database: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        engine.dispose()


async def main() -> bool:
    """Main initialization function"""
    print("=" * 70)
    print("PostgreSQL Database Initialization")
    print("=" * 70)
    print()
    # Step 1: Create database if it doesn't exist
    print("Step 1: Creating database (if needed)...")
    if not await create_database_if_not_exists():
        print("[INIT] Failed to create database")
        return False
    # Step 2: Create extensions
    print("\nStep 2: Creating PostgreSQL extensions...")
    if not await create_extensions():
        print("[INIT] Failed to create extensions")
        return False
    # Step 3: Run schema migration
    print("\nStep 3: Running schema migration...")
    if not await run_schema_migration():
        print("[INIT] Failed to run schema migration")
        return False
    # Step 4: Seed initial data
    print("\nStep 4: Seeding initial data...")
    seed_data = input("Seed initial data (create admin user)? (yes/no): ").lower()
    if seed_data == "yes":
        if not await seed_initial_data():
            print("[INIT] Failed to seed initial data")
            return False
    # Step 5: Verify database
    print("\nStep 5: Verifying database...")
    if not await verify_database():
        print("[INIT] Database verification failed")
        return False
    print("\n" + "=" * 70)
    print("Database initialization completed successfully!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Update your .env file with PostgreSQL credentials")
    print("  2. Start the backend server: python -m uvicorn main:app --reload")
    print("  3. Access the API at: http://localhost:8000")
    print()
    return True


if __name__ == "__main__":
    asyncio.run(main())
