"""
Workflow Engine Redis Client

Redis client for workflow engine.
Handles Redis operations for task queues and caching.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .config import WorkflowConfig
from .exceptions import RedisError

logger = logging.getLogger(__name__)


class QueueType(Enum):
    """Queue type for tasks."""

    CODER = "coder_tasks"
    VALIDATOR = "validator_tasks"
    PLANNER = "planner_tasks"
    APPLIER = "applier_tasks"
    TESTER = "tester_tasks"
    WORKFLOW = "workflow_tasks"
    DEAD_LETTER = "dead_letter_queue"
    SAGA = "saga_tasks"


@dataclass
class TaskMessage:
    """Message in a Redis queue."""

    task_id: str
    queue_name: str
    payload: Dict[str, Any]
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    idempotency_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "queue_name": self.queue_name,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": (
                self.scheduled_at.isoformat() if self.scheduled_at else None
            ),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskMessage:
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            queue_name=data["queue_name"],
            payload=data["payload"],
            created_at=datetime.fromisoformat(data["created_at"]),
            scheduled_at=(
                datetime.fromisoformat(data["scheduled_at"])
                if data.get("scheduled_at")
                else None
            ),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error_message=data.get("error_message"),
            idempotency_key=data.get("idempotency_key"),
        )


@dataclass
class RedisClient:
    """
    Redis client for workflow engine.
    Provides:
    - Queue operations for task distribution
    - Caching for session state
    - Pub/Sub for event broadcasting
    - Lock management
    """

    config: WorkflowConfig
    _client: Any = None  # Redis client
    _connected: bool = False

    def __post_init__(self) -> None:
        """Initialize after dataclass fields are set."""
        self._client = None
        self._connected = False

    def connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis

            # Setup real Redis connection pooling
            self._pool = redis.ConnectionPool.from_url(  # type: ignore[no-untyped-call]
                self.config.redis_url, max_connections=50, decode_responses=True
            )
            self._client = redis.Redis(connection_pool=self._pool)
            self._client.ping()
            self._connected = True
            logger.info(
                "Connected to real Redis with connection pooling (url=%s)",
                self.config.redis_url,
            )
        except Exception as e:
            logger.error("Failed to connect to Redis pool: %s", str(e))
            self._connected = False
            raise RedisError(f"Failed to connect to Redis: {e}")

    def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            self._client = None
            if hasattr(self, "_pool"):
                self._pool.disconnect()
            self._connected = False
            logger.info("Disconnected from Redis")

    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected

    def enqueue(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        scheduled_at: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
    ) -> TaskMessage:
        task_id = str(uuid.uuid4())
        message = TaskMessage(
            task_id=task_id,
            queue_name=queue_name,
            payload=payload,
            created_at=datetime.utcnow(),
            scheduled_at=scheduled_at,
            retry_count=0,
            max_retries=self.config.max_retry_attempts,
            idempotency_key=idempotency_key,
        )
        if self._client:
            self._client.lpush(queue_name, json.dumps(message.to_dict()))
        logger.debug(
            "Task enqueued to Redis: task_id=%s queue=%s",
            task_id,
            queue_name,
        )
        return message

    def dequeue(
        self,
        queue_name: str,
        timeout: int = 0,
    ) -> Optional[TaskMessage]:
        if not self._client:
            return None
        try:
            if timeout > 0:
                res = self._client.brpop(queue_name, timeout=timeout)
                raw = res[1] if res else None
            else:
                raw = self._client.rpop(queue_name)

            if raw:
                data = json.loads(raw)
                return TaskMessage.from_dict(data)
        except Exception as e:
            logger.error(
                "Failed to dequeue from Redis queue=%s: %s", queue_name, str(e)
            )
        return None

    def publish(
        self,
        channel: str,
        payload: Any,
    ) -> int:
        if self._client:
            # If payload is already a string (e.g. pre-serialized JSON), pass it through
            if isinstance(payload, str):
                return self._client.publish(channel, payload)
            return self._client.publish(channel, json.dumps(payload))
        return 0

    def subscribe(
        self,
        channel: str,
        callback: "Callable[[], None]",
    ) -> None:
        if self._client:
            pubsub = self._client.pubsub()
            pubsub.subscribe(**{channel: lambda msg: callback()})
            pubsub.run_in_thread(daemon=True)

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        if self._client:
            val_str = json.dumps(value)
            return bool(self._client.set(key, val_str, ex=ttl_seconds))
        return False

    def get(
        self,
        key: str,
    ) -> Optional[Any]:
        if self._client:
            raw = self._client.get(key)
            if raw:
                try:
                    return json.loads(raw)
                except Exception:
                    return raw
        return None

    def delete(self, key: str) -> bool:
        if self._client:
            return bool(self._client.delete(key))
        return False

    def lock(
        self,
        key: str,
        ttl_seconds: int = 30,
    ) -> Optional[str]:
        if not self._client:
            return None
        token = str(uuid.uuid4())
        lock_key = f"lock:{key}"
        if self._client.set(lock_key, token, nx=True, ex=ttl_seconds):
            return token
        return None

    def unlock(self, key: str, token: str) -> bool:
        if not self._client:
            return False
        lock_key = f"lock:{key}"
        # Lua script to release lock if token matches
        lua = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return bool(self._client.eval(lua, 1, lock_key, token))

    def get_queue_length(
        self,
        queue_name: str,
    ) -> int:
        if not self._client:
            return 0
        length = self._client.llen(queue_name)
        logger.debug("Queue length retrieved: queue=%s length=%d", queue_name, length)
        return length

    def clear_queue(self, queue_name: str) -> int:
        if not self._client:
            return 0
        count = self._client.delete(queue_name)
        logger.debug("Queue cleared: queue=%s count=%d", queue_name, count)
        return count

    def add_to_set(
        self,
        key: str,
        *values: str,
    ) -> int:
        if not self._client:
            return 0
        count = self._client.sadd(key, *values)
        logger.debug("Values added to set: key=%s count=%d", key, count)
        return count

    def get_set_members(
        self,
        key: str,
    ) -> List[str]:
        if not self._client:
            return []
        members = self._client.smembers(key)
        logger.debug("Set members retrieved: key=%s count=%d", key, len(members))
        return list(members)

    def remove_from_set(
        self,
        key: str,
        *values: str,
    ) -> int:
        if not self._client:
            return 0
        count = self._client.srem(key, *values)
        logger.debug("Values removed from set: key=%s count=%d", key, count)
        return count

    def get_all_queues(self) -> List[str]:
        if not self._client:
            return []
        queues = []
        try:
            for key in self._client.scan_iter(match="*_tasks"):
                queues.append(key)
        except Exception:
            pass
        return queues

    def get_all_keys(self, pattern: str = "*") -> List[str]:
        if not self._client:
            return []
        keys = []
        try:
            for key in self._client.scan_iter(match=pattern):
                keys.append(key)
        except Exception:
            pass
        return keys

    def ping(self) -> bool:
        """Ping Redis server. Returns True if Redis is available."""
        return self._connected

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        return {
            "connected": self._connected,
            "queues": self.get_all_queues(),
            "keys": len(self.get_all_keys()),
        }
