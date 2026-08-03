#!/usr/bin/env python3

"""

Data Migration Script: Migrate Existing Sessions to New Persistence Layer

This script migrates existing session data from the old system (in-memory jobs dict

or ai_generations table) to the new persistence layer.

Usage:
    python -m db.migrations.migrate_sessions
"""

import sys

from typing import Dict, Any, Optional

# Add parent directory to path for imports

sys.path.insert(0, "/Users/manjunathkanavi/workspace/git_workspace/iacgenie")

from sqlalchemy import create_engine, text

from sqlalchemy.pool import QueuePool

# Import database settings and adapters

from config.database import db_settings

from db.adapters.persistence_adapter import persistence_adapter


class SessionMigrator:
    """Migrate existing sessions to new persistence layer"""

    def __init__(self):
        self.engine = create_engine(
            db_settings.postgres_url,
            poolclass=QueuePool,
            pool_size=db_settings.DB_POOL_SIZE,
            max_overflow=db_settings.DB_MAX_OVERFLOW,
        )

    def get_existing_sessions(self, limit: int = 100, offset: int = 0) -> list:
        """Get existing sessions from ai_generations table"""
        with self.engine.connect() as conn:
            # Try to get from ai_generations table
            result = conn.execute(
                text("""
                SELECT id, user_id, project_id, prompt, response, status, created_at
                FROM ai_generations
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
                {"limit": limit, "offset": offset},
            )
            sessions = []
            for row in result.fetchall():
                sessions.append(
                    {
                        "id": str(row[0]),
                        "user_id": str(row[1]) if row[1] else None,
                        "project_id": str(row[2]) if row[2] else None,
                        "prompt": row[3],
                        "response": row[4],
                        "status": row[5],
                        "created_at": row[6],
                    }
                )
            return sessions

    def get_existing_generations(self, limit: int = 100, offset: int = 0) -> list:
        """Get existing generations from ai_generations table"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT id, user_id, project_id, model, prompt, response, status, tokens_used, duration_ms, created_at
                FROM ai_generations
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
                {"limit": limit, "offset": offset},
            )
            generations = []
            for row in result.fetchall():
                generations.append(
                    {
                        "id": str(row[0]),
                        "user_id": str(row[1]) if row[1] else None,
                        "project_id": str(row[2]) if row[2] else None,
                        "model": row[3],
                        "prompt": row[4],
                        "response": row[5],
                        "status": row[6],
                        "tokens_used": row[7],
                        "duration_ms": row[8],
                        "created_at": row[9],
                    }
                )
            return generations

    def migrate_generation_to_session(
        self, generation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Migrate a single generation to new session format"""
        # Map status
        status_map = {
            "pending": "CREATED",
            "running": "CODING",
            "completed": "COMPLETED",
            "failed": "FAILED",
        }
        new_status = status_map.get(generation.get("status", ""), "CREATED")
        session_data = {
            "build_id": generation["id"],
            "user_id": generation.get("user_id", "default-user-id"),
            "prompt": generation.get("prompt", ""),
            "status": new_status,
            "current_iteration": 0,
            "git_repo_url": None,
            "git_branch": None,
            "git_commit_sha": None,
            "ci_provider": None,
            "ci_run_id": None,
            "deployment_status": "pending",
            "version": 1,
        }
        # Create session in new persistence layer
        session = persistence_adapter.create_session(**session_data)
        if session:
            # Create initial iteration
            persistence_adapter.create_iteration(
                session_id=session["id"], iteration_num=0, error=None, artifacts=[]
            )
            # Create artifact for response
            if generation.get("response"):
                persistence_adapter.create_artifact(
                    session_id=session["id"],
                    iteration_num=0,
                    artifact_type="output",
                    storage_path=f"generations/{generation['id']}/response.txt",
                    content_type="text/plain",
                )
            return session
        return None

    def migrate_all(self, batch_size: int = 100) -> Dict[str, Any]:
        """Migrate all existing sessions"""
        total_migrated = 0
        total_failed = 0
        batch = 0
        while True:
            print(f"[MIGRATION] Processing batch {batch}...")
            generations = self.get_existing_generations(
                limit=batch_size, offset=batch * batch_size
            )
            if not generations:
                break
            for generation in generations:
                try:
                    session = self.migrate_generation_to_session(generation)
                    if session:
                        total_migrated += 1
                        print(f"  [OK] Migrated generation {generation['id']}")
                    else:
                        total_failed += 1
                        print(
                            f"  [FAIL] Failed to migrate generation {generation['id']}"
                        )
                except Exception as e:
                    total_failed += 1
                    print(
                        f"  [ERROR] Error migrating generation {generation['id']}: {str(e)}"
                    )
            batch += 1
        return {"total_migrated": total_migrated, "total_failed": total_failed}


def main():
    """Main entry point"""
    print("=" * 60)
    print("Data Migration: Migrate Existing Sessions to New Layer")
    print("=" * 60)
    print()
    # Check if persistence adapter is initialized
    if (
        not hasattr(persistence_adapter, "is_initialized")
        or not persistence_adapter.is_initialized
    ):
        print("[ERROR] Persistence adapter not initialized!")
        print("Please run create_tables.py first to create new tables.")
        return
    # Confirm migration
    response = input(
        "This will migrate all existing sessions to new persistence layer. Continue? (yes/no): "
    )
    if response.lower() != "yes":
        print("Aborting migration")
        return
    print()
    # Run migration
    migrator = SessionMigrator()
    result = migrator.migrate_all(batch_size=100)
    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Total migrated: {result['total_migrated']}")
    print(f"Total failed: {result['total_failed']}")
    if result["total_failed"] > 0:
        print()
        print("[WARNING] Some migrations failed. Check logs for details.")
    else:
        print()
        print("Migration completed successfully!")


if __name__ == "__main__":
    main()
