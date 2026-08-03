import json

import sqlite3

from typing import Optional, Dict, Any

from models.iac_state import IaCState

import logging

logger = logging.getLogger(__name__)


class StateRepository:
    """Repository for persisting and retrieving IaC pipeline states."""

    def __init__(self, db_path: str = "pipeline_states.db") -> None:
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_states (
                    session_id TEXT PRIMARY KEY,
                    state_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1
                )
            """)
            conn.commit()

    def save_state(self, state: IaCState) -> bool:
        """Save the current state to the repository."""
        try:
            checkpoint_data = state.checkpoint()
            state_json = json.dumps(checkpoint_data)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO pipeline_states (session_id, state_data)
                    VALUES (?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        state_data = excluded.state_data,
                        updated_at = CURRENT_TIMESTAMP,
                        version = version + 1
                """,
                    (state.session_id, state_json),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save state {state.session_id}: {e}")
            return False

    def load_state(self, session_id: str) -> Optional[IaCState]:
        """Load a state from the repository."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT state_data FROM pipeline_states
                    WHERE session_id = ?
                    ORDER BY version DESC
                    LIMIT 1
                """,
                    (session_id,),
                )
                result = cursor.fetchone()
                if result:
                    state_data = json.loads(result[0])
                    return IaCState.restore_from_checkpoint(state_data)
                return None
        except Exception as e:
            logger.error(f"Failed to load state {session_id}: {e}")
            return None

    def update_state(self, state: IaCState) -> bool:
        """Update an existing state in the repository."""
        return self.save_state(state)  # Same as save for SQLite

    def delete_state(self, session_id: str) -> bool:
        """Delete a state from the repository."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM pipeline_states WHERE session_id = ?
                """,
                    (session_id,),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete state {session_id}: {e}")
            return False

    def get_state_version(self, session_id: str) -> Optional[int]:
        """Get the current version of a state."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT version FROM pipeline_states
                    WHERE session_id = ?
                    ORDER BY version DESC
                    LIMIT 1
                """,
                    (session_id,),
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get state version {session_id}: {e}")
            return None

    def rollback_state(self, session_id: str, version: int) -> Optional[IaCState]:
        """Rollback to a specific version of a state."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT state_data FROM pipeline_states
                    WHERE session_id = ? AND version = ?
                """,
                    (session_id, version),
                )
                result = cursor.fetchone()
                if result:
                    state_data = json.loads(result[0])
                    return IaCState.restore_from_checkpoint(state_data)
                return None
        except Exception as e:
            logger.error(
                f"Failed to rollback state {session_id} to version {version}: {e}"
            )
            return None

    def list_sessions(self) -> Dict[str, Any]:
        """List all active sessions with metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, version, created_at, updated_at
                    FROM pipeline_states
                    ORDER BY updated_at DESC
                """)
                results = cursor.fetchall()
                sessions = []
                for row in results:
                    sessions.append(
                        {
                            "session_id": row[0],
                            "version": row[1],
                            "created_at": row[2],
                            "updated_at": row[3],
                        }
                    )
                return {"sessions": sessions, "count": len(sessions)}
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return {"sessions": [], "count": 0}
