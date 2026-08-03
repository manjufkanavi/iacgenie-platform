"""
test_isolation.py — Redis multi-database isolation test.

Verifies that iacgenie (db 0) and lightsrp (db 1) cannot read each other's data.
"""

import pytest


class TestRedisCrossDBIsolation:
    """Cross-database isolation guarantees in Redis."""

    def test_iacgenie_writes_only_to_db0(self, redis_ia):
        """Write a value to db 0 and confirm it's in db 0."""
        key = "test_unified:isolation:iacgenie_key"
        value = f"iacgenie_{str(int(__import__('time').time()))}"

        redis_ia.set(key, value, ex=30)
        result = redis_ia.get(key)
        assert result == value, f"Expected {value}, got {result}"

    def test_lightsrp_writes_only_to_db1(self, redis_ls):
        """Write a value to db 1 and confirm it's in db 1."""
        key = "test_unified:isolation:lightsrp_key"
        value = f"lightsrp_{str(int(__import__('time').time()))}"

        redis_ls.set(key, value, ex=30)
        result = redis_ls.get(key)
        assert result == value, f"Expected {value}, got {result}"

    def test_db0_cannot_read_db1(self, redis_ia, redis_ls):
        """Verify db 0 does NOT see data written to db 1."""
        db1_key = "test_unified:isolation:db1_value"
        db1_val = "secret_from_db1"
        db0_key = "test_unified:isolation:db0_value"
        db0_val = "secret_from_db0"

        # Write to each db
        redis_ls.set(db1_key, db1_val, ex=30)
        redis_ia.set(db0_key, db0_val, ex=30)

        # Verify cross-reads fail
        db1_in_db0 = redis_ia.get(db1_key)
        assert db1_in_db0 is None, \
            f"DB0 read DB1 data: {db1_in_db0} (expected None)"

        db0_in_db1 = redis_ls.get(db0_key)
        assert db0_in_db1 is None, \
            f"DB1 read DB0 data: {db0_in_db1} (expected None)"

    def test_both_dbs_alive_independently(self, redis_ia, redis_ls):
        """Both Redis databases must be independently operational."""
        db0_ping = redis_ia.ping()
        db1_ping = redis_ls.ping()

        assert db0_ping, "Redis db 0 (iacgenie) is not responding"
        assert db1_ping, "Redis db 1 (lightsrp) is not responding"

    def test_redis_server_info(self, redis_ia):
        """Check Redis server-level info."""
        info = redis_ia.info()
        assert info["redis_version"]
        assert info["connected_clients"] >= 0
        assert info["used_memory"] > 0
