"""
LangGraph Workflow State Schema

TypedDict-based state schema for IaCGenie LangGraph workflows.
Combines LangGraph's AgentState with IaCGenie session context fields.
"""

from typing import Any, Dict, List, NotRequired, TypedDict


class WorkflowState(TypedDict):
    """
    LangGraph workflow state combining agent messaging with IaCGenie session context.

    All fields from the existing Session dataclass plus LangGraph AgentState
    capabilities. Uses NotRequired for optional fields so LangGraph only
    requires fields that are explicitly set at each step.
    """

    # LangGraph built-in: messages with add_messages reducer
    messages: Any  # Annotated[list, add_messages]

    # Session identity (mirrors Session dataclass fields)
    id: NotRequired[str]  # Session UUID
    build_id: NotRequired[str]  # Build UUID
    user_id: NotRequired[str]  # User UUID
    prompt: NotRequired[str]  # User's natural language request

    # Git context
    git_repo_url: NotRequired[str]
    git_branch: NotRequired[str]
    git_commit_sha: NotRequired[str]

    # CI context
    ci_provider: NotRequired[str]
    ci_inputs: NotRequired[Dict[str, Any]]

    # Execution control
    status: NotRequired[str]  # SessionState string value
    current_iteration: NotRequired[int]
    max_iterations: NotRequired[int]

    # Error handling
    error_message: NotRequired[str]
    retry_count: NotRequired[int]

    # Outputs
    generated_code: NotRequired[str]
    validation_results: NotRequired[Dict[str, Any]]
    plan: NotRequired[str]
    artifacts: NotRequired[List[Any]]

    # Metadata and history
    metadata: NotRequired[Dict[str, Any]]
    state_history: NotRequired[List[Dict[str, Any]]]

    # Clarification
    clarification_history: NotRequired[List[Dict[str, str]]]
    clarification_status: NotRequired[str]
