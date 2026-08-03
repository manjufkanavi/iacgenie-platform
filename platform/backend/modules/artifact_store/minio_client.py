"""

MinIO Client for Artifact Store

Provides S3-compatible client for MinIO object storage.

"""

import io

import logging

from datetime import timedelta

from typing import Optional, Dict, Any

from minio import Minio, S3Error

from config.storage_config import storage_config

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    MinIO client wrapper for artifact storage.
    Features:
    - S3-compatible API
    - Bucket management
    - Object upload/download
    - Error handling and retry
    """

    def __init__(self) -> None:
        """Initialize MinIO client."""
        self.client = Minio(
            endpoint=storage_config.MINIO_ENDPOINT.replace("http://", "").replace(
                "https://", ""
            ),
            access_key=storage_config.MINIO_ACCESS_KEY,
            secret_key=storage_config.MINIO_SECRET_KEY,
            secure=storage_config.MINIO_SECURE,
        )
        logger.info(f"MinIO client initialized: {storage_config.MINIO_ENDPOINT}")

    async def ensure_bucket(self, bucket_name: str) -> bool:
        """
        Ensure a bucket exists, creating if necessary.
        Args:
            bucket_name: Name of the bucket
        Returns:
            True if bucket exists or was created, False otherwise
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Error ensuring bucket {bucket_name}: {str(e)}")
            return False

    async def upload_artifact(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Upload an artifact to MinIO.
        Args:
            bucket_name: Name of the bucket
            object_name: Object name (path)
            data: Binary data to upload
            content_type: MIME type
            metadata: Optional metadata dictionary
        Returns:
            Object path (bucket/object)
        Raises:
            Exception: If upload fails
        """
        try:
            await self.ensure_bucket(bucket_name)
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
                metadata=metadata or {},
            )
            logger.info(
                f"Uploaded artifact: {bucket_name}/{object_name}",
                extra={"bucket": bucket_name, "object": object_name, "size": len(data)},
            )
            return f"{bucket_name}/{object_name}"
        except Exception as e:
            logger.error(
                f"Failed to upload artifact {bucket_name}/{object_name}: {str(e)}"
            )
            raise

    async def download_artifact(self, bucket_name: str, object_name: str) -> bytes:
        """
        Download an artifact from MinIO.
        Args:
            bucket_name: Name of the bucket
            object_name: Object name (path)
        Returns:
            Binary data
        Raises:
            Exception: If download fails
        """
        try:
            response = self.client.get_object(
                bucket_name=bucket_name, object_name=object_name
            )
            logger.info(
                f"Downloaded artifact: {bucket_name}/{object_name}",
                extra={
                    "bucket": bucket_name,
                    "object": object_name,
                    "size": len(response.data),
                },
            )
            return response.data
        except Exception as e:
            logger.error(
                f"Failed to download artifact {bucket_name}/{object_name}: {str(e)}"
            )
            raise

    async def delete_artifact(self, bucket_name: str, object_name: str) -> bool:
        """
        Delete an artifact from MinIO.
        Args:
            bucket_name: Name of the bucket
            object_name: Object name (path)
        Returns:
            True if deleted, False otherwise
        Raises:
            Exception: If deletion fails
        """
        try:
            self.client.remove_object(bucket_name=bucket_name, object_name=object_name)
            logger.info(f"Deleted artifact: {bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to delete artifact {bucket_name}/{object_name}: {str(e)}"
            )
            return False

    async def list_artifacts(
        self, bucket_name: str, prefix: Optional[str] = None, limit: int = 1000
    ) -> list:
        """
        List artifacts in a bucket.
        Args:
            bucket_name: Name of the bucket
            prefix: Optional prefix filter
            limit: Maximum number of objects to return
        Returns:
            List of object information
        Raises:
            Exception: If listing fails
        """
        try:
            objects_iter = self.client.list_objects(
                bucket_name=bucket_name, prefix=prefix
            )
            objects = list(objects_iter)[:limit]
            logger.info(
                f"Listed {len(objects)} artifacts in {bucket_name}",
                extra={"bucket": bucket_name, "prefix": prefix, "count": len(objects)},
            )
            return objects
        except Exception as e:
            logger.error(f"Failed to list artifacts in {bucket_name}: {str(e)}")
            raise

    async def get_presigned_url(
        self, bucket_name: str, object_name: str, expires_in_seconds: int = 3600
    ) -> str:
        """
        Generate a presigned URL for artifact download.
        Args:
            bucket_name: Name of the bucket
            object_name: Object name (path)
            expires_in_seconds: URL expiration time
        Returns:
            Presigned URL string
        Raises:
            Exception: If URL generation fails
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires_in_seconds),
            )
            logger.info(
                f"Generated presigned URL for {bucket_name}/{object_name}",
                extra={
                    "bucket": bucket_name,
                    "object": object_name,
                    "expires_in": expires_in_seconds,
                },
            )
            return url
        except Exception as e:
            logger.error(
                f"Failed to generate presigned URL: {bucket_name}/{object_name}: {str(e)}"
            )
            raise


# Global client instance


minio_client = MinIOClient()
