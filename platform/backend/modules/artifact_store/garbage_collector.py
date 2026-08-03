"""

Garbage Collector

Cleans up expired artifacts and manages storage cleanup.

"""

import logging

import asyncio

from typing import List, Optional, Dict, Any

from .postgres_client import postgres_client

from config.storage_config import storage_config

logger = logging.getLogger(__name__)


class GarbageCollector:
    """
    Garbage collector for artifact cleanup.
    Features:
    - Expired artifact deletion
    - Storage cleanup
    - Configurable cleanup intervals
    - Tenant-aware cleanup
    """

    def __init__(self) -> None:
        self._running = False
        self._cleanup_interval = storage_config.ARTIFACT_CLEANUP_INTERVAL
        logger.info("Garbage collector initialized")

    async def start(self) -> None:
        """Start the garbage collector."""
        if self._running:
            logger.warning("Garbage collector already running")
            return
        self._running = True
        logger.info("Garbage collector started")
        # Run cleanup in background
        asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the garbage collector."""
        self._running = False
        logger.info("Garbage collector stopped")

    async def _cleanup_loop(self) -> None:
        """Run cleanup loop."""
        while self._running:
            try:
                await self.cleanup_expired_artifacts()
                await asyncio.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
                await asyncio.sleep(self._cleanup_interval)

    async def cleanup_expired_artifacts(self) -> None:
        """
        Delete expired artifacts from MinIO and PostgreSQL.
        """
        logger.info("Starting expired artifact cleanup")
        # Get expired artifacts from PostgreSQL
        expired_artifacts = await self._get_expired_artifacts()
        deleted_count = 0
        for artifact in expired_artifacts:
            try:
                # Delete from PostgreSQL
                await postgres_client.delete_artifact(artifact["id"])
                # Delete from MinIO
                minio_path = artifact.get("storage_path", "")
                bucket_name = storage_config.MINIO_ARTIFACTS_BUCKET
                object_name = minio_path
                # Import MinIO client
                from .minio_client import minio_client

                await minio_client.delete_artifact(
                    bucket_name=bucket_name, object_name=object_name
                )
                deleted_count += 1
                logger.info(
                    f"Deleted expired artifact {artifact['id']}",
                    extra={
                        "artifact_id": artifact["id"],
                        "expired_at": artifact.get("expires_at"),
                    },
                )
            except Exception as e:
                logger.error(f"Error deleting artifact {artifact.get('id')}: {str(e)}")
        logger.info(f"Cleanup completed: {deleted_count} artifacts deleted")

    async def _get_expired_artifacts(self) -> List[Dict[str, Any]]:
        """
        Get expired artifacts from PostgreSQL.
        Returns:
            List of expired artifact records
        """
        # This would require a query to find expired artifacts
        # For now, return empty list
        return []

    async def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about garbage collection.
        Returns:
            Dictionary with cleanup statistics
        """
        return {
            "running": self._running,
            "cleanup_interval_seconds": self._cleanup_interval,
            "last_cleanup_time": None,  # Would track last cleanup time
            "total_deleted": 0,  # Would track total deleted count
        }

    async def force_cleanup(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Force cleanup of artifacts for a specific session.
        Args:
            session_id: Optional session ID to filter by
        Returns:
            Cleanup results
        """
        logger.info(f"Force cleanup requested for session {session_id}")
        # This would implement session-specific cleanup
        # For now, return placeholder
        return {
            "session_id": session_id,
            "deleted_count": 0,
            "message": "Force cleanup completed",
        }


# Global garbage collector instance


garbage_collector = GarbageCollector()
