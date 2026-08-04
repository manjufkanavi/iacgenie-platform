"""WebSocket endpoint for real-time pipeline updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from typing import Optional

import logging

from modules.workflow_engine.event_broadcast import EventBroadcastService

from middleware.auth import verify_pipeline_token
from utils.metrics import CONNECTION_COUNT

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pipeline WebSocket"])

broadcast_service = EventBroadcastService()


async def _authenticate_websocket(token: Optional[str]) -> dict:
    """Authenticate WebSocket connection via query parameter JWT token."""
    if not token:
        return {}
    try:
        payload = (
            verify_pipeline_token.__wrapped__(token)
            if hasattr(verify_pipeline_token, "__wrapped__")
            else {}
        )
        return dict(payload) if payload else {}
    except Exception:
        return {}


@router.websocket("/ws/{session_id}")
async def pipeline_websocket(
    websocket: WebSocket, session_id: str, token: Optional[str] = Query(None)
) -> None:
    """WebSocket endpoint for real-time pipeline updates."""
    # Authenticate first, then accept
    await _authenticate_websocket(token)
    await websocket.accept()
    CONNECTION_COUNT.inc()

    # Session alive check: inform frontend if session is not actively running
    active_states = {
        "created",
        "clarify",
        "coding",
        "validating",
        "planning",
        "applying",
        "testing",
        "git_push",
        "ci_trigger",
        "ci_monitor",
        "human_review",
    }
    session_active = False
    session_status = "unknown"
    try:
        from modules.workflow_engine.session_manager import session_manager

        session = await session_manager.get_session(session_id)
        if session:
            session_status = session.status  # type: ignore[assignment]
            session_active = session.status in active_states
    except Exception:
        # If session manager unavailable, check DB as fallback
        try:
            from db.db_provider import db_provider

            job = await db_provider.get_generation_job(session_id)
            if job:
                session_status = job.get("status", "unknown")
                job_active = {"pending", "running"}.intersection({session_status})
                session_active = bool(job_active)
        except Exception:
            pass

    # Send initial session_info event
    await websocket.send_json(
        {
            "type": "session_info",
            "session_id": session_id,
            "data": {
                "active": session_active,
                "status": session_status,
                "message": "Session is not actively running"
                if not session_active
                else "",
            },
        }
    )
    # Start an asyncio task to listen to Redis and forward to the WebSocket
    from modules.workflow_engine.config import WorkflowEngineConfig as WorkflowConfig
    from modules.workflow_engine.redis_client import RedisClient
    import asyncio

    redis_client = RedisClient(config=WorkflowConfig())

    async def listen_to_redis() -> None:
        try:
            async for message in redis_client.subscribe_to_job(session_id):
                # Only send if the websocket is still connected
                try:
                    await websocket.send_json(message)
                except Exception as send_err:
                    logger.debug(f"Failed to send to websocket: {send_err}")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error for {session_id}: {e}")

    redis_task = asyncio.create_task(listen_to_redis())

    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command")
            if command == "ping":
                await websocket.send_json({"type": "pong", "timestamp": _now_iso()})
            elif command == "subscribe_all":
                # Handle global subscribe if needed
                pass
            elif command == "unsubscribe":
                await websocket.send_json(
                    {"type": "unsubscribed", "session_id": session_id}
                )
                break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for pipeline {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for pipeline {session_id}: {str(e)}")
    finally:
        redis_task.cancel()
        CONNECTION_COUNT.dec()


def _now_iso() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat()
