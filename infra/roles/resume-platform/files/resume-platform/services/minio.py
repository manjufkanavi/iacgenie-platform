"""MinIO file storage service."""

from __future__ import annotations

import io
import logging
import os
from typing import Any

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

_client: Minio | None = None


def get_minio_client() -> Minio:
    """Get or create MinIO client singleton."""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "CHANGE_ME"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "CHANGE_ME"),
            secure=False,
        )
    return _client


def upload_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload file to MinIO and return the object key."""
    client = get_minio_client()
    bucket = "resume-files"
    object_name = f"resumes/{filename}"

    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
        logger.info(f"File uploaded to MinIO: {bucket}/{object_name}")
        return object_name
    except S3Error as e:
        logger.error(f"MinIO upload failed: {e}")
        raise


def download_file(object_key: str) -> bytes:
    """Download file from MinIO and return bytes."""
    client = get_minio_client()
    bucket = "resume-files"

    try:
        response = client.get_object(bucket_name=bucket, object_name=object_key)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        logger.error(f"MinIO download failed: {e}")
        raise


def delete_file(object_key: str) -> bool:
    """Delete file from MinIO."""
    client = get_minio_client()
    bucket = "resume-files"

    try:
        client.remove_object(bucket_name=bucket, object_name=object_key)
        logger.info(f"File deleted from MinIO: {bucket}/{object_key}")
        return True
    except S3Error as e:
        logger.error(f"MinIO delete failed: {e}")
        return False


def file_exists(object_key: str) -> bool:
    """Check if file exists in MinIO."""
    client = get_minio_client()
    bucket = "resume-files"

    try:
        client.stat_object(bucket_name=bucket, object_name=object_key)
        return True
    except S3Error:
        return False
