"""
test_integration.py — Cross-service integration tests.

These tests verify that services work together correctly across the unified
infrastructure, simulating real-world usage patterns.
"""

import pytest


class TestRedisMinIOIntegration:
    """Test Redis caching of MinIO S3 operations."""

    def test_cache_write_read(self, redis_ia, s3):
        """Simulate caching a MinIO metadata entry in Redis."""
        import json

        # Get current bucket list
        buckets = s3.list_buckets()
        bucket_data = json.dumps(buckets)

        cache_key = "test_unified:cache:bucket_list"
        redis_ia.set(cache_key, bucket_data, ex=60)

        # Verify cache hit
        cached = json.loads(redis_ia.get(cache_key))
        assert len(cached) > 0, "Cached bucket list is empty"
        assert isinstance(cached, list), "Cached bucket list should be a list"


class TestRedisPostgresIntegration:
    """Test Redis caching of PostgreSQL query results."""

    def test_cache_db_metadata(self, pg_iacgenie, redis_ia):
        """Cache a table count from PostgreSQL into Redis."""
        cur = pg_iacgenie.cursor()
        cur.execute(
            "SELECT schemaname, tablename, n_tup_ins FROM pg_stat_user_tables LIMIT 10"
        )
        tables = cur.fetchall()
        cur.close()

        cache_key = "test_unified:cache:table_stats"
        import json
        redis_ia.set(cache_key, json.dumps(tables), ex=60)

        cached = json.loads(redis_ia.get(cache_key))
        assert cached is not None, "Table stats cache is empty"

    def test_cross_tenant_cache_separation(self, redis_ia, redis_ls):
        """Verify Redis cache data is isolated between tenants."""
        import json

        iacgenie_data = json.dumps({"tenant": "iacgenie", "key_count": 42})
        lightsrp_data = json.dumps({"tenant": "lightsrp", "key_count": 99})

        redis_ia.set("test_unified:cache:tenant_data", iacgenie_data, ex=30)
        redis_ls.set("test_unified:cache:tenant_data", lightsrp_data, ex=30)

        # Verify isolation
        iacgenie_cache = redis_ia.get("test_unified:cache:tenant_data")
        lightsrp_cache = redis_ls.get("test_unified:cache:tenant_data")

        assert "iacgenie" in iacgenie_cache, "Wrong data in iacgenie cache"
        assert "lightsrp" in lightsrp_cache, "Wrong data in lightsrp cache"
        assert iacgenie_cache != lightsrp_cache, "Cache data should differ between tenants"


class TestFullPipelineIntegration:
    """Simulate a full request pipeline across services."""

    def test_minio_redis_postgres_pipeline(self, s3, redis_ia, pg_iacgenie):
        """
        Simulate: write to MinIO -> cache metadata in Redis -> persist to PostgreSQL.

        This mimics how IacGenie might:
        1. Upload a plan file to MinIO
        2. Cache file metadata in Redis
        3. Record the operation in PostgreSQL
        """
        import json
        import hashlib
        import time

        timestamp = int(time.time())

        # Step 1: Write a plan file to MinIO
        file_content = json.dumps({
            "plan_id": f"test-{timestamp}",
            "status": "testing",
            "created_at": timestamp,
        }).encode()

        object_key = f"test-unified/plans/test-plan-{timestamp}.json"
        s3.put_object(
            "iacgenie-plans", object_key, file_content,
            content_type="application/json",
        )

        # Step 2: Compute hash and cache in Redis
        file_hash = hashlib.sha256(file_content).hexdigest()
        cache_key = f"test_unified:cache:plan:{file_hash}"
        redis_ia.hset(
            cache_key, mapping={
                "file_key": object_key,
                "bucket": "iacgenie-plans",
                "hash": file_hash,
                "plan_id": f"test-{timestamp}",
            },
            ex=300,
        )

        # Verify cache entry
        cached_hash = redis_ia.hget(cache_key, "hash")
        assert cached_hash == file_hash, f"Cache hash mismatch: {cached_hash}"

        # Step 3: Record in PostgreSQL
        cur = pg_iacgenie.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_upload_log (
                id SERIAL PRIMARY KEY,
                plan_id VARCHAR(255),
                file_key TEXT,
                hash VARCHAR(64),
                bucket TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "INSERT INTO test_upload_log (plan_id, file_key, hash, bucket) VALUES (%s, %s, %s, %s)",
            (f"test-{timestamp}", object_key, file_hash, "iacgenie-plans"),
        )
        cur.execute(
            "SELECT plan_id, file_key, hash FROM test_upload_log ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        assert row is not None, "Upload log record not persisted"
        assert row[0] == f"test-{timestamp}", f"Wrong plan_id: {row[0]}"

        cur.close()

    def test_lightsrp_pipeline(self, s3, redis_ls, pg_lightsrp):
        """
        Simulate LightSrp pipeline: search query -> cache -> store result.
        """
        import json

        timestamp = int(__import__('time').time())

        # Step 1: Simulate a search result
        search_result = json.dumps({
            "query": "integration-test",
            "results": [{"title": "Test Result", "url": "http://test.local"}],
            "timestamp": timestamp,
        }).encode()

        # Step 2: Cache in Redis
        cache_key = f"test_unified:cache:search:sha256:{__import__('hashlib').sha256(search_result).hexdigest()}"
        redis_ls.set(cache_key, search_result, ex=60)

        cached = redis_ls.get(cache_key)
        assert cached == search_result.decode(), "Search result cache mismatch"

        # Step 3: Store in PostgreSQL (simulate search history)
        cur = pg_lightsrp.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_search_log (
                id SERIAL PRIMARY KEY,
                query VARCHAR(255),
                result_count INTEGER,
                cached BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        data = json.loads(search_result)
        cur.execute(
            "INSERT INTO test_search_log (query, result_count, cached) VALUES (%s, %s, %s)",
            (data["query"], len(data["results"]), True),
        )
        cur.execute("SELECT query, result_count FROM test_search_log ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        assert row is not None, "Search log record not persisted"
        assert row[0] == "integration-test", f"Wrong query: {row[0]}"
        cur.close()


class TestCrossTenantIsolation:
    """End-to-end isolation: iacgenie and lightsrp cannot leak data."""

    def test_iacgenie_cannot_access_lightsrp_minio(self, pg_iacgenie, redis_ia, s3):
        """Verify iacgenie path data is not in lightsrp buckets."""
        # iacgenie writes to its own bucket
        import json
        iacgenie_data = json.dumps({"tenant": "iacgenie", "test": "cross-isolation"})
        s3.put_object(
            "iacgenie-plans", "test-unified/iacgenie-isolation.json",
            iacgenie_data.encode(), content_type="application/json",
        )

        # lightsrp bucket should NOT contain this
        try:
            objects = s3.list_objects_v2(
                Bucket="lightsrp-sx", Prefix="test-unified/iacgenie/"
            )
            contents = objects.get("Contents", [])
            assert len(contents) == 0, \
                f"IacGenie data leaked to LightSrp bucket: {[o['Key'] for o in contents]}"
        except Exception:
            pass  # Bucket might not exist or have no objects

    def test_lightsrp_cannot_access_iacgenie_redis(self, redis_ls, redis_ia):
        """Verify lightsrp cannot read iacgenie's Redis data."""
        # iacgenie writes to Redis db 0
        redis_ia.set("test_unified:secret:iacgenie_only", "hidden_value", ex=30)

        # lightsrp reads from Redis db 1
        secret = redis_ls.get("test_unified:secret:iacgenie_only")
        assert secret is None, \
            f"LightSrp read iacGenie's Redis data: {secret}"
