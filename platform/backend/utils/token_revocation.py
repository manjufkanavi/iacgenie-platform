"""

Access Token Revocation Store

Manages a revocation list for access tokens using Redis (primary) with

PostgreSQL fallback. Each revoked token's jti is stored with a TTL matching

the token's expiration, so entries auto-expire.

Design:

  - Redis: sorted set keyed by jti, scored by expiration timestamp
    - Lookup: ZSCORE key jti (O(1))
    - Cleanup: automatic via TTL per member (stored as score = expiration)
  - PostgreSQL: revoked_tokens table for no-Redis deployments
    - Column: jti (PK), expires_at (indexed), created_at
    - Cleanup: periodic DELETE WHERE expires_at < NOW()
"""

import os

import uuid

import time


import logging

from typing import Any, Optional

import redis
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------

# Redis-backed store

# ---------------------------------------------------------------------------


class _RedisRevocationStore:
    """Redis-backed access-token revocation store."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: Optional[Any] = None
        self._init()

    def _init(self) -> None:
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
            self.client.ping()
            logger.info("Token revocation store connected to Redis")
        except Exception as e:
            logger.warning(
                f"Redis connection failed for token revocation: {e}. Using DB fallback."
            )
            self.client = None

    def _key(self) -> str:
        return "revoked_tokens"

    async def is_revoked(self, jti: str) -> bool:
        if not self.client:
            return False
        try:
            # ZSCORE returns the score if member exists in the sorted set
            result = self.client.zscore(self._key(), jti)
            return result is not None
        except Exception as e:
            logger.error(f"Redis revocation check failed: {e}")
            return False

    async def revoke(
        self, jti: str, expires_at_timestamp: Optional[float] = None
    ) -> None:
        """
        Revoke a token identified by its jti.
        Args:
            jti: JWT ID (UUID string)
            expires_at_timestamp: Expiration as Unix timestamp (seconds).
                Stored as the sorted-set score so Redis can query by range.
                Also sets TTL via EXPIRE on the key for safety.
        """
        if not self.client:
            return
        try:
            ts = expires_at_timestamp or (time.time() + 3600)
            self.client.zadd(self._key(), {jti: ts})
            ttl = int(ts - time.time()) + 60  # buffer
            if ttl > 0:
                self.client.expire(self._key(), ttl)
        except Exception as e:
            logger.error(f"Redis revocation failed: {e}")

    async def revoke_bulk(self, entries: list) -> None:
        """
        Revoke multiple tokens atomically.
        Args:
            entries: list of (jti, user_id, expires_at_timestamp) tuples
                     (user_id is ignored for Redis, kept for API consistency)
        """
        if not self.client or not entries:
            return
        try:
            pipe = self.client.pipeline()
            for jti, _, ts in entries:
                pipe.zadd(self._key(), {jti: ts})
            if entries:
                max_ts = max(ts for _, _, ts in entries)
                ttl = int(max_ts - time.time()) + 60
                if ttl > 0:
                    pipe.expire(self._key(), ttl)
            pipe.execute()
        except Exception as e:
            logger.error(f"Redis bulk revocation failed: {e}")

    def close(self) -> None:
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------

# PostgreSQL-backed store

# ---------------------------------------------------------------------------


class _PostgresRevocationStore:
    """PostgreSQL-backed access-token revocation store."""

    def __init__(self, db_provider: Any) -> None:
        self.db = db_provider
        self._table_created = False

    async def _ensure_table(self) -> None:
        """Create the revoked_tokens table if it doesn't exist."""
        if self._table_created:
            return
        try:
            if not self.db._is_initialized or not self.db.adapter:
                self._table_created = True  # skip future attempts
                return
            query = """
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    jti TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """
            await self.db.adapter.execute_command(query)
            # Add index for expiration-based cleanup
            await self.db.adapter.execute_command(
                "CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires "
                "ON revoked_tokens(expires_at)"
            )
            self._table_created = True
            logger.info("revoked_tokens table ensured in PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to create revoked_tokens table: {e}")
            self._table_created = True  # don't retry on error

    async def is_revoked(self, jti: str) -> bool:
        await self._ensure_table()
        try:
            if not self.db._is_initialized or not self.db.adapter:
                return False
            query = "SELECT 1 FROM revoked_tokens WHERE jti = :jti AND expires_at > NOW() LIMIT 1"
            result = await self.db.adapter.execute_query(query, {"jti": jti})
            return result is not None and len(result) > 0
        except Exception as e:
            logger.error(f"PostgreSQL revocation check failed: {e}")
            return False

    async def revoke(
        self, jti: str, user_id: str, expires_at_timestamp: Optional[float] = None
    ) -> None:
        await self._ensure_table()
        try:
            if not self.db._is_initialized or not self.db.adapter:
                return
            exp_dt = (
                datetime.fromtimestamp(expires_at_timestamp, tz=timezone.utc)
                if expires_at_timestamp
                else datetime.now(timezone.utc)
            )
            query = """
                INSERT INTO revoked_tokens (jti, user_id, expires_at)
                VALUES (:jti, :user_id, :expires_at)
                ON CONFLICT (jti) DO NOTHING
            """
            await self.db.adapter.execute_command(
                query,
                {"jti": jti, "user_id": user_id, "expires_at": exp_dt.isoformat()},
            )
        except Exception as e:
            logger.error(f"PostgreSQL revocation failed: {e}")

    async def revoke_bulk(self, entries: list) -> None:
        """
        Revoke multiple tokens.
        Args:
            entries: list of (jti, user_id, expires_at_timestamp) tuples
        """
        if not entries:
            return
        await self._ensure_table()
        try:
            if not self.db._is_initialized or not self.db.adapter:
                return
            for jti, user_id, ts in entries:
                exp_dt = (
                    datetime.fromtimestamp(ts, tz=timezone.utc)
                    if ts
                    else datetime.now(timezone.utc)
                )
                query = """
                    INSERT INTO revoked_tokens (jti, user_id, expires_at)
                    VALUES (:jti, :user_id, :expires_at)
                    ON CONFLICT (jti) DO NOTHING
                """
                await self.db.adapter.execute_command(
                    query,
                    {"jti": jti, "user_id": user_id, "expires_at": exp_dt.isoformat()},
                )
        except Exception as e:
            logger.error(f"PostgreSQL bulk revocation failed: {e}")

    def close(self) -> None:
        pass  # no-op for DB connection

    async def cleanup_expired(self) -> int:
        """Delete expired entries. Returns count of deleted rows."""
        await self._ensure_table()
        try:
            if not self.db._is_initialized or not self.db.adapter:
                return 0
            query = "DELETE FROM revoked_tokens WHERE expires_at <= NOW()"
            await self.db.adapter.execute_command(query)
            return 0  # execute_command returns None; count not easily available
        except Exception as e:
            logger.error(f"PostgreSQL cleanup failed: {e}")
            return 0


# ---------------------------------------------------------------------------

# Manager (chooses best backend)

# ---------------------------------------------------------------------------


class TokenRevocationStore:
    """
    High-level token revocation store that picks the best backend.
    Priority: Redis (if available) > PostgreSQL.
    Falls back gracefully when primary backend is unavailable.
    """

    def __init__(self) -> None:
        self._redis_store: Optional[_RedisRevocationStore] = None
        self._db_store: Optional[_PostgresRevocationStore] = None
        self._use_redis = False
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # Try Redis first
        try:
            self._redis_store = _RedisRevocationStore(redis_url)
            if self._redis_store.client:
                self._use_redis = True
                logger.info("Using Redis as primary token revocation store")
            else:
                logger.info(
                    "Redis unavailable for token revocation, using PostgreSQL fallback"
                )
        except Exception as e:
            logger.warning(f"Redis init failed for token revocation: {e}")
        # Always prepare PostgreSQL fallback
        try:
            from db.db_provider import db_provider

            self._db_store = _PostgresRevocationStore(db_provider)
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL revocation store: {e}")

    async def is_revoked(self, jti: str) -> bool:
        """Check if a token (identified by jti) has been revoked."""
        if not jti:
            return False
        if self._use_redis and self._redis_store:
            if await self._redis_store.is_revoked(jti):
                return True
        if self._db_store:
            return await self._db_store.is_revoked(jti)
        return False

    async def revoke(
        self, jti: str, user_id: str, expires_at_timestamp: Optional[float] = None
    ) -> None:
        """Revoke a single token by its jti."""
        if self._use_redis and self._redis_store:
            await self._redis_store.revoke(jti, expires_at_timestamp)
        if self._db_store:
            await self._db_store.revoke(jti, user_id, expires_at_timestamp)

    async def revoke_bulk(self, entries: list) -> None:
        """
        Revoke multiple tokens atomically.
        Args:
            entries: list of (jti, user_id, expires_at_timestamp) tuples
        """
        if self._use_redis and self._redis_store:
            await self._redis_store.revoke_bulk(entries)
        if self._db_store:
            await self._db_store.revoke_bulk(entries)

    async def revoke_by_user(self, user_id: str, jti_user_pairs: list) -> None:
        """Revoke all tokens for a user (bulk logout).
        Args:
            user_id: The user whose tokens should be revoked
            jti_user_pairs: list of (jti, expires_at_timestamp) tuples
        """
        await self.revoke_bulk([(j, ts) for j, ts in jti_user_pairs])

    def close(self) -> None:
        if self._redis_store:
            self._redis_store.close()
        if self._db_store:
            self._db_store.close()

    @property
    def enabled(self) -> bool:
        return self._use_redis or self._db_store is not None


# Global singleton


_revocation_store: Optional[TokenRevocationStore] = None


def get_revocation_store() -> TokenRevocationStore:
    """Get (or create) the global token revocation store singleton."""
    global _revocation_store
    if _revocation_store is None:
        _revocation_store = TokenRevocationStore()
    return _revocation_store


def generate_jti() -> str:
    """Generate a cryptographically random jti (JWT ID) as a UUID v4."""
    return str(uuid.uuid4())
