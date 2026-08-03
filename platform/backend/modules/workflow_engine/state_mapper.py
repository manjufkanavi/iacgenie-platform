"""Bidirectional conversion between WorkflowState and IaCState."""

from typing import Dict, Any

from modules.workflow_engine.graph_state import WorkflowState
from models.iac_state import IaCState


def workflow_state_to_iac_state(
    workflow_state: WorkflowState,
) -> IaCState:
    """Convert a LangGraph WorkflowState to an IaCState for agent consumption."""
    messages = []
    for msg in workflow_state.get("messages", []):
        if hasattr(msg, "content"):
            messages.append({"role": msg.type or "human", "content": msg.content})
        elif isinstance(msg, dict):
            messages.append(
                {
                    "role": msg.get("role", "human"),
                    "content": msg.get("content", ""),
                }
            )

    return IaCState(  # type: ignore[call-arg]
        user_request=workflow_state.get("prompt", ""),
        refined_spec=workflow_state.get("metadata", {}).get("refined_spec"),
        hcl_code=workflow_state.get("generated_code"),
        retry_counts=workflow_state.get("metadata", {}).get("retry_counts", {}),
        retry_feedback=workflow_state.get("metadata", {}).get("retry_feedback"),
        messages=messages,
    )


def iac_state_to_workflow_update(
    iac_state: IaCState,
    agent_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert an IaC agent execution result into a WorkflowState update dict."""
    update: Dict[str, Any] = {}

    # Propagate generated code if produced by the agent
    if agent_result.get("result") and isinstance(agent_result["result"], dict):
        output = agent_result["result"].get("output", "")
        if output:
            update["generated_code"] = output

    # Track validation results
    if agent_result.get("result") and isinstance(agent_result["result"], dict):
        result_data = agent_result["result"]
        if "validation_results" in result_data:
            update["validation_results"] = result_data["validation_results"]

    # Track retry counts in metadata
    if iac_state.retry_counts:
        existing_metadata = update.get("metadata", {})
        existing_metadata["retry_counts"] = iac_state.retry_counts
        existing_metadata["retry_feedback"] = iac_state.retry_feedback
        update["metadata"] = existing_metadata

    # Track status
    if agent_result.get("success"):
        next_phase = agent_result.get("next_phase")
        if next_phase:
            update["status"] = next_phase.value
    else:
        error_msg = agent_result.get("error", "Unknown error")
        update["error_message"] = error_msg

    return update
