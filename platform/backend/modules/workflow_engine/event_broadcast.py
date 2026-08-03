"""Real-time event broadcasting via Redis pub/sub for workflow state changes."""

import json
import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standardised event type strings matching frontend expectations."""

    PHASE_TRANSITION = "phase_transition"
    LOG_ENTRY = "log_entry"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    SESSION_COMPLETE = "session_complete"
    SESSION_FAILED = "session_failed"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    CLARIFY_QUESTION = "clarify_question"
    CLARIFY_ANSWER = "clarify_answer"
    CLARIFY_COMPLETE = "clarify_complete"
    HEARTBEAT = "heartbeat"


@dataclass
class WorkflowEvent:
    """Event payload sent over Redis pub/sub and WebSocket."""

    event_type: EventType
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type,
            "session_id": self.session_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventBroadcastService:
    """Broadcasts workflow events via Redis pub/sub.

    Each session gets its own channel:  workflow:{session_id}
    A global channel forwards cross-session events: workflow:global
    """

    CHANNEL_PREFIX = "workflow:"
    GLOBAL_CHANNEL = "workflow:global"

    def __init__(self, redis_client: Optional[RedisClient] = None):
        self._redis = redis_client
        self._subscribers: Dict[str, List[Callable]] = {}
        self._pubsub: Any = None
        self._listening = False
        self._listen_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def broadcast(self, event: WorkflowEvent) -> int:
        """Publish an event to the session channel and the global channel."""
        if not self._redis or not self._redis.is_connected():
            logger.warning("Redis not connected — event dropped: %s", event.event_type)
            return 0

        session_channel = f"{self.CHANNEL_PREFIX}{event.session_id}"
        payload = event.to_dict()

        # Publish to session-specific channel
        session_count = self._redis.publish(session_channel, payload)

        # Also publish to global channel for listeners that want all events
        global_count = self._redis.publish(self.GLOBAL_CHANNEL, payload)

        logger.debug(
            "Event broadcast: type=%s session=%s session_subs=%s global_subs=%s",
            event.event_type,
            event.session_id,
            session_count,
            global_count,
        )
        return session_count

    def broadcast_phase_transition(
        self, session_id: str, from_state: str, to_state: str
    ) -> int:
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.PHASE_TRANSITION,
                session_id=session_id,
                data={"from_state": from_state, "to_state": to_state},
            )
        )

    def broadcast_agent_start(self, session_id: str, agent_name: str) -> int:
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.AGENT_START,
                session_id=session_id,
                data={"agent": agent_name},
            )
        )

    def broadcast_agent_complete(
        self, session_id: str, agent_name: str, success: bool
    ) -> int:
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.AGENT_COMPLETE,
                session_id=session_id,
                data={"agent": agent_name, "success": success},
            )
        )

    def broadcast_agent_error(
        self, session_id: str, agent_name: str, error: str
    ) -> int:
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.AGENT_ERROR,
                session_id=session_id,
                data={"agent": agent_name, "error": error},
            )
        )

    def broadcast_session_complete(
        self,
        session_id: str,
        status: str,
        files: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        data: Dict[str, Any] = {"status": status}
        if files:
            data["files"] = files
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.SESSION_COMPLETE,
                session_id=session_id,
                data=data,
            )
        )

    def broadcast_session_failed(self, session_id: str, error: str) -> int:
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.SESSION_FAILED,
                session_id=session_id,
                data={"error": error},
            )
        )

    def broadcast_human_review(
        self, session_id: str, reason: str, refined_spec: Optional[str] = None
    ) -> int:
        data: Dict[str, Any] = {"reason": reason}
        if refined_spec:
            data["refined_spec"] = refined_spec
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.HUMAN_REVIEW_REQUESTED,
                session_id=session_id,
                data=data,
            )
        )

    def broadcast_clarify_question(
        self,
        session_id: str,
        questions: List[str],
        options: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        data: Dict[str, Any] = {"questions": questions}
        if options:
            data["options"] = options
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.CLARIFY_QUESTION,
                session_id=session_id,
                data=data,
            )
        )

    def broadcast_clarify_complete(self, session_id: str, has_spec: bool) -> int:
        return self.broadcast(
            WorkflowEvent(
                event_type=EventType.CLARIFY_COMPLETE,
                session_id=session_id,
                data={"has_refined_spec": has_spec},
            )
        )

    # ------------------------------------------------------------------
    # Subscription (for in-process listeners, e.g. WebSocket handler)
    # ------------------------------------------------------------------

    def subscribe(self, channel: str, callback: Callable) -> None:
        """Register an in-process callback for events on a channel."""
        self._subscribers.setdefault(channel, [])
        if callback not in self._subscribers[channel]:
            self._subscribers[channel].append(callback)

    def unsubscribe(self, channel: str, callback: Callable) -> None:
        if channel in self._subscribers:
            self._subscribers[channel] = [
                cb for cb in self._subscribers[channel] if cb != callback
            ]
            if not self._subscribers[channel]:
                del self._subscribers[channel]

    async def start_listening(self) -> None:
        """Start a background Redis pub/sub listener that dispatches to in-process callbacks."""
        if self._listening:
            return
        if not self._redis or not self._redis.is_connected():
            return

        self._pubsub = self._redis._client.pubsub()
        self._pubsub.subscribe(self.GLOBAL_CHANNEL)
        self._listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop_listening(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        self._listening = False
        self._subscribers.clear()

    async def _listen_loop(self) -> None:
        """Background loop reading pub/sub messages and dispatching to callbacks."""
        try:
            while self._listening:
                message = await asyncio.to_thread(
                    self._pubsub.get_message,
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message and message.get("type") == "message":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    self._dispatch(channel, data)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Error in event listener loop")

    def _on_message(self, message: Dict[str, Any]) -> None:
        """Handle a Redis pubsub message and dispatch to callbacks."""
        channel = message.get("channel", "")
        if isinstance(channel, bytes):
            channel = channel.decode()
        data = message.get("data", "")
        if isinstance(data, bytes):
            data = data.decode()
        self._dispatch(channel, data)

    def _dispatch(self, channel: str, raw_payload: str) -> None:
        """Dispatch a raw payload to registered callbacks for the channel."""
        # Collect callbacks for the specific channel + global subscribers
        callbacks = self._subscribers.get(channel, []) + self._subscribers.get(
            self.GLOBAL_CHANNEL, []
        )
        # Global events also fan out to all session channel subscribers
        if channel == self.GLOBAL_CHANNEL:
            for ch, ch_cbs in self._subscribers.items():
                if ch != self.GLOBAL_CHANNEL:
                    callbacks = callbacks + ch_cbs
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(channel, raw_payload))
                else:
                    cb(channel, raw_payload)
            except Exception:
                logger.exception(
                    "Error dispatching event to callback on channel %s", channel
                )

    @property
    def is_listening(self) -> bool:
        return self._listening
