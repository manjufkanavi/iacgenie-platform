"""Utility functions for Agent Executor."""

import os

import uuid

from datetime import datetime

from typing import Optional


def create_session_workspace(session_id: Optional[str] = None) -> str:
    """
    Create a workspace directory for a session.
    Args:
        session_id: Optional session ID. If not provided, a new UUID will be generated.
    Returns:
        str: Path to the created workspace directory
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    # Get workspace root from environment or use default
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/workspace/sandboxes")
    # Create session-specific workspace path
    workspace_path = os.path.join(workspace_root, str(session_id))
    # Create directory if it doesn't exist
    os.makedirs(workspace_path, exist_ok=True)
    return workspace_path


def validate_command_args(args: list) -> bool:
    """
    Validate command arguments for security (shell injection prevention).
    Args:
        args: List of command arguments
    Returns:
        bool: True if arguments are valid, False otherwise
    """
    if not args:
        return True
    shell_metacharacters = [
        ";",
        "|",
        "&",
        "$",
        "`",
        "(",
        ")",
        "{",
        "}",
        ">",
        "<",
        "*",
        "?",
        "[",
        "]",
        "'",
        '"',
        "\\",
        " ",
    ]
    for arg in args:
        for meta in shell_metacharacters:
            if meta in arg:
                return False
    return True


def validate_path_traversal(path: str, workspace_root: str) -> bool:
    """
    Validate that a path does not attempt directory traversal.
    Args:
        path: Path to validate
        workspace_root: Root directory of the workspace
    Returns:
        bool: True if path is safe, False otherwise
    """
    # Normalize the path
    normalized_path = os.path.normpath(path)
    # Check if path is within workspace root
    if not normalized_path.startswith(os.path.normpath(workspace_root)):
        return False
    return True


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def generate_task_id() -> str:
    """Generate a unique task ID."""
    return str(uuid.uuid4())


def get_agent_type_from_queue(queue_name: str) -> str:
    """
    Extract agent type from queue name.
    Args:
        queue_name: Name of the Redis queue
    Returns:
        str: Agent type extracted from queue name
    """
    queue_mapping = {
        "coder_tasks": "coder",
        "validator_tasks": "validator",
        "planner_tasks": "planner",
        "applier_tasks": "applier",
        "tester_tasks": "tester",
    }
    return queue_mapping.get(queue_name, "unknown")


def format_error_message(error: Exception, context: Optional[dict] = None) -> dict:
    """
    Format an error message with context.
    Args:
        error: The exception that occurred
        context: Optional context dictionary
    Returns:
        dict: Formatted error information
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": get_timestamp(),
    }
    if context:
        error_info["context"] = str(context)
    return error_info


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.
    Args:
        value: String to validate
    Returns:
        bool: True if valid UUID, False otherwise
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def sanitize_string(value: str) -> str:
    """
    Sanitize a string to prevent injection attacks.
    Args:
        value: String to sanitize
    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
    # Remove potentially dangerous characters
    dangerous_chars = [";", "|", "&", "`", "$", ">", "<"]
    sanitized = value
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")
    return sanitized


__all__ = [
    "create_session_workspace",
    "validate_command_args",
    "validate_path_traversal",
    "get_timestamp",
    "generate_task_id",
    "get_agent_type_from_queue",
    "format_error_message",
    "is_valid_uuid",
    "sanitize_string",
]
