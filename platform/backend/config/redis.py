"""Redis connection management for pipeline task queue and pub/sub."""

import os

from typing import Optional

import redis.asyncio as _redis_async_mod

from typing import Any

redis: Any
redis = _redis_async_mod

from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisConfig(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    pipeline_channel_prefix: str = "pipeline:"
    heartbeat_interval: int = 15
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def channel_prefix(self) -> str:
        return self.pipeline_channel_prefix


_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        cfg = RedisConfig()
        _redis_client = redis.from_url(
            cfg.redis_url,
            max_connections=cfg.redis_max_connections,
            decode_responses=False,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")
