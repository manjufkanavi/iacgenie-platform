"""

PostgreSQL Client for Artifact Store

Provides database access for artifact metadata tracking.

"""

import logging

import asyncpg

from typing import Optional, List, Dict, Any

from config.storage_config import storage_config

logger = logging.getLogger(__name__)


class PostgresClient:
    """
    PostgreSQL client for artifact metadata.
    Features:
    - Async connection pool
    - Artifact CRUD operations
    - Metadata tracking
    - Expiration management
    """

    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None
        logger.info("PostgreSQL client initialized")

    async def _get_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=storage_config.POSTGRES_HOST,
                port=storage_config.POSTGRES_PORT,
                database=storage_config.POSTGRES_DATABASE,
                user=storage_config.POSTGRES_USER,
                password=storage_config.POSTGRES_PASSWORD,
                min_size=storage_config.DB_POOL_SIZE,
                max_overflow=storage_config.DB_MAX_OVERFLOW,
            )
        return await self._pool.acquire()

    async def create_artifact(
        self,
        session_id: str,
        iteration_num: int,
        artifact_type: str,
        filename: str,
        storage_path: str,
        content_type: str,
        size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create an artifact record.
        Args:
            session_id: Session identifier
            iteration_num: Iteration number
            artifact_type: Type (code, log, plan, output)
            filename: Original filename
            storage_path: MinIO object path
            content_type: MIME type
            size: Optional file size
            metadata: Optional metadata dictionary
        Returns:
            Artifact ID
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO artifacts "
                    "(session_id, iteration_num, type, filename, storage_path, "
                    "content_type, size, metadata, created_at, updated_at) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW()) "
                    "RETURNING id",
                    session_id,
                    iteration_num,
                    artifact_type,
                    filename,
                    storage_path,
                    content_type,
                    size,
                    metadata or {},
                )
                artifact_id = await cursor.fetchone()
            await conn.commit()
            logger.info(
                f"Created artifact {artifact_id}",
                extra={
                    "artifact_id": artifact_id,
                    "session_id": session_id,
                    "iteration_num": iteration_num,
                    "type": artifact_type,
                },
            )
            return artifact_id
        except Exception as e:
            logger.error(f"Failed to create artifact: {str(e)}")
            raise

    async def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an artifact by ID.
        Args:
            artifact_id: Artifact identifier
        Returns:
            Artifact data or None if not found
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, session_id, iteration_num, type, filename, "
                    "storage_path, content_type, size, metadata, "
                    "created_at, updated_at FROM artifacts WHERE id = $1",
                    (artifact_id,),
                )
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "session_id": row[1],
                        "iteration_num": row[2],
                        "type": row[3],
                        "filename": row[4],
                        "storage_path": row[5],
                        "content_type": row[6],
                        "size": row[7],
                        "metadata": row[8],
                        "created_at": row[9].isoformat(),
                        "updated_at": row[10].isoformat(),
                    }
            logger.info(f"Retrieved artifact {artifact_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get artifact {artifact_id}: {str(e)}")
            raise

    async def list_artifacts(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List artifacts for a session.
        Args:
            session_id: Session identifier
            limit: Maximum number to return
            offset: Offset for pagination
        Returns:
            List of artifact data
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, session_id, iteration_num, type, filename, "
                    "storage_path, created_at FROM artifacts "
                    "WHERE session_id = $1 ORDER BY created_at DESC "
                    "LIMIT $2 OFFSET $3",
                    (session_id, limit, offset),
                )
                rows = await cursor.fetchall()
                artifacts = [
                    {
                        "id": row[0],
                        "session_id": row[1],
                        "iteration_num": row[2],
                        "type": row[3],
                        "filename": row[4],
                        "storage_path": row[5],
                        "created_at": row[6].isoformat(),
                    }
                    for row in rows
                ]
            logger.info(f"Listed {len(artifacts)} artifacts for session {session_id}")
            return artifacts
        except Exception as e:
            logger.error(f"Failed to list artifacts for session {session_id}: {str(e)}")
            raise

    async def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete an artifact by ID.
        Args:
            artifact_id: Artifact identifier
        Returns:
            True if deleted, False otherwise
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM artifacts WHERE id = $1", (artifact_id,)
                )
                await conn.commit()
            logger.info(f"Deleted artifact {artifact_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete artifact {artifact_id}: {str(e)}")
            return False

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")


# Global client instance


postgres_client = PostgresClient()
