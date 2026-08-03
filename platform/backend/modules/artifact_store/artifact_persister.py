"""

Artifact Persister Service

Handles artifact upload and management with MinIO and PostgreSQL.

"""

import logging

from typing import List, Optional, Dict, Any

from datetime import datetime, timedelta

from .minio_client import MinIOClient

from .metadata_manager import MetadataManager

from config.storage_config import storage_config

logger = logging.getLogger(__name__)


class ArtifactPersister:
    """
    Service for uploading and managing artifacts.
    Features:
    - Upload to MinIO with PostgreSQL metadata
    - Metadata tracking
    - Access control based on tenant/user
    - TTL management
    """

    def __init__(
        self,
        minio_client: MinIOClient,
        postgres_client: Optional[Any] = None,
        metadata_manager: Optional[Any] = None,
    ) -> None:
        self.minio_client = minio_client
        self.postgres_client = postgres_client
        self.metadata_manager = metadata_manager or MetadataManager()
        logger.info("Artifact persister initialized")

    async def upload_artifact(
        self,
        session_id: str,
        iteration_num: int,
        artifact_type: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload an artifact to MinIO with PostgreSQL metadata.
        Args:
            session_id: Session identifier
            iteration_num: Iteration number
            artifact_type: Type (code, log, plan, output)
            filename: Original filename
            content: Binary content to upload
            content_type: MIME type
            metadata: Optional metadata dictionary
            tenant_id: Optional tenant ID for access control
        Returns:
            Dictionary with storage_path, url, and expiration
        """
        # Validate inputs
        if not session_id:
            raise ValueError("session_id cannot be empty")
        if not filename:
            raise ValueError("filename cannot be empty")
        if not content or len(content) == 0:
            raise ValueError("content cannot be empty")
        if len(content) > storage_config.ARTIFACT_MAX_SIZE:
            raise ValueError(
                f"Artifact size exceeds maximum of {storage_config.ARTIFACT_MAX_SIZE} bytes"
            )
        # Validate artifact type
        valid_types = {"code", "log", "plan", "output"}
        if artifact_type not in valid_types:
            raise ValueError(
                f"Invalid artifact type: {artifact_type}. Must be one of {valid_types}"
            )
        # Build storage path
        storage_path = f"sessions/{session_id}/iter_{iteration_num}/{filename}"
        # Build metadata — MinIO encodes these as HTTP headers, so values must be
        # plain ASCII strings. None values or lists cause "unsigned headers" errors.
        raw_metadata: Dict[str, Any] = {
            "description": metadata.get("description") if metadata else None,
            "format": metadata.get("format") if metadata else None,
            "version": metadata.get("version") if metadata else None,
            "session_id": session_id,
            "iteration_num": str(iteration_num),
            "tenant_id": str(tenant_id) if tenant_id else "",
            "created_at": datetime.now().isoformat(),
        }
        # Filter out None/empty values and ensure all values are strings
        artifact_metadata: Dict[str, str] = {
            k: str(v) for k, v in raw_metadata.items() if v is not None and v != ""
        }
        # Upload to MinIO
        minio_path = await self.minio_client.upload_artifact(
            bucket_name=storage_config.MINIO_ARTIFACTS_BUCKET,
            object_name=storage_path,
            data=content,
            content_type=content_type,
            metadata=artifact_metadata,
        )
        # Store metadata in PostgreSQL
        if self.postgres_client:
            artifact_id = await self.postgres_client.create_artifact(
                session_id=session_id,
                iteration_num=iteration_num,
                artifact_type=artifact_type,
                filename=filename,
                storage_path=minio_path,
                content_type=content_type,
                size=len(content),
                metadata=artifact_metadata,
            )
        else:
            # Fallback: generate UUID for artifact ID
            import uuid

            artifact_id = str(uuid.uuid4())
        # Calculate expiration
        expires_at = datetime.now() + timedelta(
            seconds=storage_config.ARTIFACT_DEFAULT_TTL
        )
        logger.info(
            f"Uploaded artifact {artifact_id} for session {session_id}",
            extra={
                "artifact_id": artifact_id,
                "session_id": session_id,
                "iteration_num": iteration_num,
                "type": artifact_type,
                "size": len(content),
            },
        )
        return {
            "storage_path": minio_path,
            "url": f"{storage_config.MINIO_ENDPOINT}/{minio_path}",
            "artifact_id": artifact_id,
            "expires_at": expires_at.isoformat(),
        }

    async def get_artifact(
        self, artifact_id: str, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get artifact information.
        Args:
            artifact_id: Artifact identifier
            tenant_id: Optional tenant ID for access control
        Returns:
            Artifact data or None if not found
        """
        # Get from PostgreSQL
        if not self.postgres_client:
            return None
        artifact_data = await self.postgres_client.get_artifact(artifact_id)
        if not artifact_data:
            return None
        # Check access control
        if tenant_id and artifact_data.get("session_id") != tenant_id:
            logger.warning(
                f"Access denied: artifact {artifact_id} belongs to another tenant",
                extra={"artifact_id": artifact_id, "tenant_id": tenant_id},
            )
            return None
        # Get MinIO URL
        artifact_data.get("storage_path", "")
        logger.info(f"Retrieved artifact {artifact_id}")
        return artifact_data

    async def list_artifacts(
        self,
        session_id: str,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List artifacts for a session.
        Args:
            session_id: Session identifier
            tenant_id: Optional tenant ID for access control
            limit: Maximum number to return
            offset: Offset for pagination
        Returns:
            List of artifact data
        """
        # Get from PostgreSQL
        if not self.postgres_client:
            return []
        artifacts = await self.postgres_client.list_artifacts(
            session_id=session_id, limit=limit, offset=offset
        )
        # Filter by tenant if specified
        if tenant_id:
            artifacts = [a for a in artifacts if a.get("session_id") == tenant_id]
        # Add MinIO URLs
        for artifact in artifacts:
            minio_path = artifact.get("storage_path", "")
            artifact["url"] = f"{storage_config.MINIO_ENDPOINT}/{minio_path}"
        logger.info(f"Listed {len(artifacts)} artifacts for session {session_id}")
        return artifacts

    async def delete_artifact(
        self, artifact_id: str, tenant_id: Optional[str] = None
    ) -> bool:
        """
        Delete an artifact.
        Args:
            artifact_id: Artifact identifier
            tenant_id: Optional tenant ID for access control
        Returns:
            True if deleted, False otherwise
        """
        # Get artifact data
        if not self.postgres_client:
            return False
        artifact_data = await self.postgres_client.get_artifact(artifact_id)
        if not artifact_data:
            return False
        # Check access control
        if tenant_id and artifact_data.get("session_id") != tenant_id:
            logger.warning(
                f"Access denied: artifact {artifact_id} belongs to another tenant",
                extra={"artifact_id": artifact_id, "tenant_id": tenant_id},
            )
            return False
        # Delete from PostgreSQL
        await self.postgres_client.delete_artifact(artifact_id)
        # Delete from MinIO
        minio_path = artifact_data.get("storage_path", "")
        await self.minio_client.delete_artifact(
            bucket_name=storage_config.MINIO_ARTIFACTS_BUCKET, object_name=minio_path
        )
        logger.info(f"Deleted artifact {artifact_id}")
        return True


# Get MinIO client for the global instance


from .minio_client import minio_client

# Global persister instance with required minio_client argument

artifact_persister = ArtifactPersister(minio_client=minio_client)
