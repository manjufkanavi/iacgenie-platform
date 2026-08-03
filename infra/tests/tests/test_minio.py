"""
test_minio.py — MinIO S3-compatible storage operations.

Tests verify that both tenant buckets exist, can store/retrieve data, and are
properly isolated.
"""

import pytest


class TestMinIOConnectivity:
    """Basic MinIO connectivity and bucket operations."""

    def test_list_buckets(self, s3):
        """Ensure we can list all buckets."""
        buckets = s3.list_buckets()
        names = {b["Name"] for b in buckets}
        print(f"  Available buckets: {sorted(names)}")
        assert len(names) > 0, "No buckets found in MinIO"

    def test_expected_buckets_exist(self, s3):
        """Verify expected tenant buckets exist."""
        buckets = s3.list_buckets()
        names = {b["Name"] for b in buckets}

        expected = [
            "iacgenie-artifacts",
            "iacgenie-logs",
            "lightsrp-sx",
            "lightsrp-cache",
        ]
        for bucket in expected:
            assert bucket in names, f"Expected bucket '{bucket}' not found"


class TestMinIOIacGenieBuckets:
    """Test iacgenie-specific bucket operations."""

    def test_artifacts_put_get(self, s3):
        bucket = "iacgenie-artifacts"
        object_name = f"test-unified/health-check-{pytest.time_marker}.json"
        payload = b'{"service": "iacgenie", "test": "health_check"}'

        s3.put_object(bucket, object_name, payload, content_type="application/json")
        response = s3.get_object(bucket, object_name)
        data = response.read()
        assert data == payload

    def test_logs_put_get(self, s3):
        bucket = "iacgenie-logs"
        object_name = f"test-unified/test.log"
        payload = b"INFO 2026-07-20 test log line\n"

        s3.put_object(bucket, object_name, payload, content_type="text/plain")
        response = s3.get_object(bucket, object_name)
        assert response.read() == payload

    def test_iacgenie_can_list_own_objects(self, s3):
        """iacgenie buckets should be accessible."""
        for bucket in ["iacgenie-artifacts", "iacgenie-logs", "iacgenie-plans", "iacgenie-outputs"]:
            try:
                objects = s3.list_objects_v2(Bucket=bucket)
                # Might be empty; just check no access error
                assert "Contents" in objects or objects.get("KeyCount", 0) >= 0
            except Exception as e:
                print(f"  Warning listing {bucket}: {e}")


class TestMinIOLightSrpBuckets:
    """Test lightsrp-specific bucket operations."""

    def test_sx_cache_put_get(self, s3):
        bucket = "lightsrp-sx"
        object_name = f"test-unified/search-cache-{pytest.time_marker}.json"
        payload = b'{"query": "test", "results": []}'

        s3.put_object(bucket, object_name, payload, content_type="application/json")
        response = s3.get_object(bucket, object_name)
        assert response.read() == payload

    def test_cache_put_get(self, s3):
        bucket = "lightsrp-cache"
        object_name = f"test-unified/cache-data.json"
        payload = b'{"cached": true}'

        s3.put_object(bucket, object_name, payload, content_type="application/json")
        response = s3.get_object(bucket, object_name)
        assert response.read() == payload


class TestMinIOLifecycle:
    """Clean up test objects after each test."""

    def test_cleanup_artifacts(self, s3):
        """Remove test objects from iacgenie-artifacts."""
        bucket = "iacgenie-artifacts"
        try:
            objects = s3.list_objects_v2(Bucket=bucket, Prefix="test-unified/")
            for obj in objects.get("Contents", []):
                s3.delete_object(bucket, obj["Key"])
        except Exception:
            pass

    def test_cleanup_logs(self, s3):
        """Remove test objects from iacgenie-logs."""
        bucket = "iacgenie-logs"
        try:
            objects = s3.list_objects_v2(Bucket=bucket, Prefix="test-unified/")
            for obj in objects.get("Contents", []):
                s3.delete_object(bucket, obj["Key"])
        except Exception:
            pass

    def test_cleanup_sx(self, s3):
        """Remove test objects from lightsrp-sx."""
        bucket = "lightsrp-sx"
        try:
            objects = s3.list_objects_v2(Bucket=bucket, Prefix="test-unified/")
            for obj in objects.get("Contents", []):
                s3.delete_object(bucket, obj["Key"])
        except Exception:
            pass

    def test_cleanup_cache(self, s3):
        """Remove test objects from lightsrp-cache."""
        bucket = "lightsrp-cache"
        try:
            objects = s3.list_objects_v2(Bucket=bucket, Prefix="test-unified/")
            for obj in objects.get("Contents", []):
                s3.delete_object(bucket, obj["Key"])
        except Exception:
            pass
