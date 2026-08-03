"""
In-Memory Checkpoint Saver for LangGraph

Uses MemorySaver for workflow session checkpoints. Sufficient for
synchronous Celery execution where checkpoint persistence across
process restarts is not required.
"""

import logging
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_checkpointer: Optional[MemorySaver] = None


def get_checkpointer(postgres_url: Optional[str] = None) -> MemorySaver:
    """Return a singleton MemorySaver instance.

    The postgres_url parameter is accepted for API compatibility but
    is ignored since MemorySaver does not use a database.
    """
    global _checkpointer
    if _checkpointer is None:
        logger.info("Initializing LangGraph MemorySaver")
        _checkpointer = MemorySaver()
        logger.info("MemorySaver initialized")
    if _checkpointer is None:
        raise RuntimeError("Checkpointer initialization failed")
    return _checkpointer


def reset_checkpointer() -> None:
    """Reset the singleton (useful for testing)."""
    global _checkpointer
    _checkpointer = None


def cleanup_checkpointer() -> None:
    """Cleanup hook — release internal resources."""
    global _checkpointer
    logger.info("Cleaning up LangGraph MemorySaver")
    _checkpointer = None
