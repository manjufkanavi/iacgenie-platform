"""
LangGraph Workflow Orchestrator

Builds a StateGraph DAG from the existing state machine VALID_TRANSITIONS,
providing LangGraph-powered execution alongside the existing state machine.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from langgraph.graph import StateGraph, START, END

from modules.workflow_engine.checkpoint_saver import get_checkpointer
from modules.workflow_engine.graph_state import WorkflowState
from modules.workflow_engine.state_machine import SessionState
from .event_broadcast import EventBroadcastService
from models.iac_state import IaCState
from models.error_classes import ErrorClass
from agents.command_agents import CommandAgent, CommandType
from agents.clarify_agent import ClarifyAgent

from src.agent_executor.models import AgentType
from agents.git_agent import GitAgent
from agents.ci_agent import CICIAgent

logger = logging.getLogger(__name__)

# Map SessionState values to LangGraph node names

_STATE_TO_NODE: Dict[SessionState, str] = {
    SessionState.CREATED: "start",
    SessionState.CLARIFY: "clarify",
    SessionState.CODING: "coding",
    SessionState.VALIDATING: "validating",
    SessionState.PLANNING: "planning",
    SessionState.APPLYING: "applying",
    SessionState.TESTING: "testing",
    SessionState.GIT_PUSH: "git_push",
    SessionState.CI_TRIGGER: "ci_trigger",
    SessionState.CI_MONITOR: "ci_monitor",
    SessionState.COMPLETED: "end",
    SessionState.FAILED: "fail",
    SessionState.HUMAN_REVIEW: "human_review",
}


# ---------------------------------------------------------------------------
# Node functions — wired to real agents
# ---------------------------------------------------------------------------


def _make_iac_state(state: WorkflowState) -> IaCState:
    """Convert WorkflowState fields to IaCState for agent consumption."""
    import json

    metadata = state.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    refined_spec_val = metadata.get("refined_spec")
    if isinstance(refined_spec_val, dict):
        refined_str = json.dumps(refined_spec_val)
    elif refined_spec_val is None:
        refined_str = None
    else:
        refined_str = str(refined_spec_val)

    return IaCState(  # type: ignore[call-arg]
        session_id=state.get("id", ""),
        user_request=state.get("prompt", ""),
        refined_spec=refined_str,
        hcl_code=state.get("generated_code"),
        retry_counts=metadata.get("retry_counts", {}),
        retry_feedback=metadata.get("retry_feedback"),
        clarification_history=metadata.get("clarification_history", []),
        expected_clarification_questions=metadata.get(
            "expected_clarification_questions"
        ),
    )


def _apply_agent_result(
    state: WorkflowState,
    agent_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Map a CommandAgent/GitAgent result into a WorkflowState update dict."""
    update: Dict[str, Any] = {}
    metadata_patch: Dict[str, Any] = {}

    if not agent_result.get("success"):
        update["error_message"] = agent_result.get("error", "Unknown error")
        update["retry_count"] = state.get("retry_count", 0) + 1
        update["status"] = SessionState.FAILED.value
        return update

    # Propagate generated code
    result_data = agent_result.get("result", {})
    if isinstance(result_data, dict):
        output = result_data.get("output")
        if output:
            update["generated_code"] = output

    # Propagate next phase as status update
    next_phase = agent_result.get("next_phase")
    if next_phase:
        update["status"] = (
            next_phase.value if hasattr(next_phase, "value") else str(next_phase)
        )

    # Track retry info
    if isinstance(state.get("metadata"), dict):
        metadata_patch["retry_counts"] = {}
        metadata_patch["retry_feedback"] = agent_result.get("retry_feedback")

    if metadata_patch:
        existing_meta = state.get("metadata", {})
        if not isinstance(existing_meta, dict):
            existing_meta = {}
        existing_meta.update(metadata_patch)
        update["metadata"] = existing_meta

    return update


async def _node_coding(
    state: WorkflowState,
    agent_executor: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generate code via AgentExecutor, then run format and init commands."""
    session_id = state.get("id", "")
    prompt = state.get("prompt", "")
    logger.info("Node: coding — generating code for session %s", session_id)

    # Step 1: Generate code via AgentExecutor if available
    if agent_executor and prompt:
        import asyncio

        max_retries = 3
        retry_delays = [2, 5, 10]
        agent_result = None
        for attempt in range(max_retries):
            try:
                agent_result = await agent_executor.run_agent_task(
                    agent_type=AgentType.CODER,
                    session_id=session_id,
                    build_id=session_id,
                    iteration=1,
                    context={
                        "prompt": prompt,
                        "provider": state.get("metadata", {}).get("provider", "aws"),
                        "model": state.get("metadata", {}).get("model", "default"),
                        "refined_spec": state.get("metadata", {}).get("refined_spec"),
                        "model_config": state.get("metadata", {}).get("model_config"),
                    },
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "Agent task attempt %d failed, retrying in %ds: %s",
                        attempt + 1,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Agent task failed after %d attempts: %s",
                        max_retries,
                        e,
                        exc_info=True,
                    )
                    return _apply_agent_result(
                        state, {"success": False, "error": str(e)}
                    )

        if agent_result:
            if (
                not agent_result.get("success", True)
                or agent_result.get("status") == "failed"
            ):
                error_msg = agent_result.get(
                    "error", "Agent task failed with unknown error"
                )
                logger.error(
                    f"AgentExecutor failed for session {session_id}: {error_msg}"
                )
                return _apply_agent_result(
                    state, {"success": False, "error": error_msg}
                )

            files = agent_result.get("result", {}).get("files", [])
            if files:
                state["generated_code"] = json.dumps(files)
                logger.info(
                    "AgentExecutor generated %d files for session %s",
                    len(files),
                    session_id,
                )
            else:
                logger.warning(
                    "AgentExecutor returned no files for session %s", session_id
                )
                return _apply_agent_result(
                    state, {"success": False, "error": "Agent returned no files"}
                )

    # Coding successful — return next phase for routing
    return {
        "generated_code": state.get("generated_code", ""),
        "status": SessionState.COMPLETED.value,
        "retry_count": state.get("retry_count", 0),
        "error_message": None,  # clear any prior error from a previous attempt
    }


async def _node_validating(state: WorkflowState) -> Dict[str, Any]:
    """Validate generated code with tofu validate."""
    logger.info("Node: validating session %s", state.get("id"))
    acs = _make_iac_state(state)

    agent = CommandAgent(CommandType.VALIDATE)
    await agent.initialize(acs)
    result = await agent.execute()
    await agent.cleanup()

    if not result["success"]:
        return _apply_agent_result(state, result)

    return {
        "status": SessionState.VALIDATING.value,
        "validation_results": {
            "passed": True,
            "output": result.get("result", {}).get("output", ""),
        },
    }


async def _node_planning(state: WorkflowState) -> Dict[str, Any]:
    """Create deployment plan with tofu plan."""
    logger.info("Node: planning session %s", state.get("id"))
    acs = _make_iac_state(state)

    agent = CommandAgent(CommandType.PLAN)
    await agent.initialize(acs)
    result = await agent.execute()
    await agent.cleanup()

    if not result["success"]:
        return _apply_agent_result(state, result)

    return {
        "status": SessionState.PLANNING.value,
        "plan": result.get("result", {}).get("output", ""),
    }


async def _node_applying(state: WorkflowState) -> Dict[str, Any]:
    """Apply infrastructure with tofu apply."""
    logger.info("Node: applying session %s", state.get("id"))
    acs = _make_iac_state(state)

    agent = CommandAgent(CommandType.APPLY)
    await agent.initialize(acs)
    result = await agent.execute()
    # Don't cleanup after apply — workspace may be needed

    if not result["success"]:
        return _apply_agent_result(state, result)

    return {"status": SessionState.APPLYING.value}


async def _node_testing(state: WorkflowState) -> Dict[str, Any]:
    """Run post-apply validation."""
    logger.info("Node: testing session %s", state.get("id"))
    # Testing phase — run a validate to confirm state is still consistent
    acs = _make_iac_state(state)

    agent = CommandAgent(CommandType.VALIDATE)
    await agent.initialize(acs)
    result = await agent.execute()
    await agent.cleanup()

    if not result["success"]:
        return _apply_agent_result(state, result)

    return {"status": SessionState.TESTING.value}


async def _node_git_push(state: WorkflowState) -> Dict[str, Any]:
    """Push generated code to git repository."""
    logger.info("Node: git_push session %s", state.get("id"))
    acs = _make_iac_state(state)

    agent = GitAgent()
    await agent.initialize(acs)
    result = await agent.execute()
    await agent.cleanup()

    if not result["success"]:
        return _apply_agent_result(state, result)

    # Git push succeeded — move to CI trigger
    return {"status": SessionState.GIT_PUSH.value}


async def _node_ci_trigger(state: WorkflowState) -> Dict[str, Any]:
    """Trigger CI pipeline via provider API."""
    logger.info("Node: ci_trigger session %s", state.get("id"))
    acs = _make_iac_state(state)

    agent = CICIAgent(mode="trigger")
    await agent.initialize(acs)
    result = await agent.execute()

    if not result["success"]:
        return _apply_agent_result(state, result)

    # Store the CI run ID for monitoring
    ci_run_id = result.get("result", {}).get("ci_run_id")
    update: Dict[str, Any] = {"status": SessionState.CI_TRIGGER.value}
    if ci_run_id:
        if not isinstance(state.get("metadata"), dict):
            update["metadata"] = {}
        else:
            update["metadata"] = dict(state.get("metadata", {}))
        update["metadata"]["ci_run_id"] = ci_run_id
    return update


async def _node_ci_monitor(state: WorkflowState) -> Dict[str, Any]:
    """Monitor CI pipeline results."""
    logger.info("Node: ci_monitor session %s", state.get("id"))
    acs = _make_iac_state(state)

    # Get the CI run ID from metadata
    metadata = state.get("metadata", {})
    if isinstance(metadata, dict):
        acs.retry_feedback = metadata.get("ci_run_id")  # reuse for transport

    agent = CICIAgent(mode="monitor")
    await agent.initialize(acs)
    result = await agent.execute()

    if not result["success"]:
        error_class = result.get("error_class")
        if error_class == ErrorClass.RETRYABLE:
            # CI still running — signal to retry monitoring
            return {"status": SessionState.CI_MONITOR.value}
        return _apply_agent_result(state, result)

    return {"status": SessionState.CI_MONITOR.value}


async def _node_human_review(state: WorkflowState) -> Dict[str, Any]:
    """Escalate to human reviewer."""
    logger.info("Node: human_review session %s", state.get("id"))
    return {"status": SessionState.HUMAN_REVIEW.value}


async def _node_clarify(
    state: WorkflowState,
    event_broadcast: Optional["EventBroadcastService"] = None,
) -> Dict[str, Any]:
    """Run ClarifyAgent — LLM analyzes prompt, asks questions or produces spec."""
    session_id = state.get("id", "")
    logger.info("Node: clarify session %s", session_id)
    acs = _make_iac_state(state)

    # Extract model_config from state metadata if available
    model_config = (
        state.get("metadata", {}).get("model_config")
        if isinstance(state.get("metadata"), dict)
        else None
    )

    # If model_config is missing or doesn't have an API key, try to load from DB
    if (
        not model_config
        or not model_config.get("api_key")
        or model_config.get("api_key") == "dummy"
    ):
        try:
            from app_factory import db_provider

            user_id = state.get("user_id")
            metadata = state.get("metadata", {})
            if isinstance(metadata, dict):
                project_id = metadata.get("project_id")
                provider = metadata.get("provider", "openai")
                fallback_model = metadata.get("model", "Qwen3.6-27B-UD-MLX-4bit")

                if user_id and project_id is not None:
                    configs = await db_provider.list_model_configs(user_id, project_id)
                    for cfg in configs:
                        if cfg.get("provider") == provider:
                            config_dict = cfg.get("config", {})
                            temp = float(cfg.get("temperature", 70)) / 100.0
                            model_config = {
                                "provider": cfg.get("provider", "custom"),
                                "model_name": cfg.get("model_name", fallback_model),
                                "api_key": cfg.get("api_key", "dummy"),
                                "base_url": config_dict.get(
                                    "base_url", "http://127.0.0.1:1234/v1"
                                ),
                                "max_tokens": cfg.get("max_tokens", 8192),
                                "temperature": temp,
                                "timeout": cfg.get("timeout", 120),
                            }
                            break
        except Exception as e:
            logger.warning(
                f"Failed to fetch model config from DB in _node_clarify: {e}"
            )

    agent = ClarifyAgent()
    await agent.initialize(acs, model_config=model_config)
    result = await agent.execute()
    await agent.cleanup()

    if not result.get("success"):
        # Check if failure is due to clarification questions (not an error)
        questions = result.get("questions")
        message = result.get("message")
        options = result.get("options", [])
        if questions or message:
            if event_broadcast:
                event_broadcast.broadcast_clarify_question(
                    session_id, questions or [message], options=options
                )
            meta = state.get("metadata", {}) or {}
            if not isinstance(meta, dict):
                meta = {}

            # Add the first generated question to clarification_history so it's not lost
            history = meta.get("clarification_history", [])
            history.append(
                {
                    "role": "assistant",
                    "content": message or (questions[0] if questions else ""),
                    "options": options,
                }
            )
            meta["clarification_history"] = history

            meta["retry_feedback"] = json.dumps(
                {
                    "message": message or (questions[0] if questions else ""),
                    "options": options,
                }
            )
            return {"status": SessionState.HUMAN_REVIEW.value, "metadata": meta}
        return _apply_agent_result(state, result)

    # Store refined spec in metadata for downstream nodes
    spec = result.get("result", {}).get("refined_spec")
    update: Dict[str, Any] = {"status": SessionState.HUMAN_REVIEW.value}
    if spec:
        meta = state.get("metadata", {}) or {}
        if not isinstance(meta, dict):
            meta = {}
        meta["refined_spec"] = spec
        update["metadata"] = meta
    if event_broadcast:
        event_broadcast.broadcast_clarify_complete(session_id, has_spec=bool(spec))
        if spec:
            event_broadcast.broadcast_human_review(
                session_id,
                reason="Please review the generated specification",
                refined_spec=spec,
            )

    return update


async def _node_fail(state: WorkflowState) -> Dict[str, Any]:
    """Terminal failure state."""
    logger.warning("Node: fail — session %s", state.get("id"))
    return {"status": SessionState.FAILED.value}


# Routing functions — return the next node name based on current state value


def _route_after_coding(state: WorkflowState) -> str:
    """After coding, go to validating or retry."""
    if state.get("retry_count", 0) >= state.get("max_iterations", 5):
        return "fail"
    return "validating"


def _route_after_validating(state: WorkflowState) -> str:
    """After validating, go to planning or back to coding."""
    if state.get("retry_count", 0) >= state.get("max_iterations", 5):
        return "fail"
    return "planning"


def _route_after_planning(state: WorkflowState) -> str:
    """After planning, go to applying or back to coding."""
    if state.get("retry_count", 0) >= state.get("max_iterations", 5):
        return "fail"
    return "applying"


def _route_after_applying(state: WorkflowState) -> str:
    """After applying, go to testing or back to coding."""
    if state.get("retry_count", 0) >= state.get("max_iterations", 5):
        return "fail"
    return "testing"


def _route_after_testing(state: WorkflowState) -> str:
    """After testing, go to git_push, human_review, or back to coding."""
    if state.get("retry_count", 0) >= state.get("max_iterations", 5):
        return "fail"
    return "git_push"


def _route_after_clarify(state: WorkflowState) -> str:
    """After clarify, go to human_review (questions), coding (spec ready), or fail."""
    status = state.get("status", "")
    if status == SessionState.HUMAN_REVIEW.value:
        return "human_review"
    if status == SessionState.FAILED.value:
        return "fail"
    return "coding"


def _route_after_git_push(state: WorkflowState) -> str:
    """After git_push, go to ci_trigger or retry."""
    if state.get("retry_count", 0) >= state.get("max_iterations", 5):
        return "fail"
    return "ci_trigger"


def _route_after_ci_trigger(state: WorkflowState) -> str:
    """After ci_trigger, go to ci_monitor or retry."""
    if state.get("retry_count", 0) >= state.get("max_iterations", 5):
        return "fail"
    return "ci_monitor"


def _route_after_ci_monitor(state: WorkflowState) -> str:
    """After ci_monitor, go to completed, fail, or human_review."""
    # Default happy path; can be overridden by ci_result in state
    if state.get("status") == SessionState.FAILED.value:
        return "fail"
    return "end"


# Node dispatch table

_NODE_MAP = {
    "clarify": _node_clarify,
    "coding": _node_coding,
    "validating": _node_validating,
    "planning": _node_planning,
    "applying": _node_applying,
    "testing": _node_testing,
    "git_push": _node_git_push,
    "ci_trigger": _node_ci_trigger,
    "ci_monitor": _node_ci_monitor,
    "human_review": _node_human_review,
    "fail": _node_fail,
}

# Conditional edge map: (after_node, possible_next) -> routing_func

_CONDITIONAL_EDGES = {
    ("start", "coding"): lambda state: (
        "coding" if state.get("status") != SessionState.FAILED.value else "fail"
    ),
    ("coding", "validating"): _route_after_coding,
    ("validating", "planning"): _route_after_validating,
    ("planning", "applying"): _route_after_planning,
    ("applying", "testing"): _route_after_applying,
    ("testing", "git_push"): _route_after_testing,
    ("git_push", "ci_trigger"): _route_after_git_push,
    ("ci_trigger", "ci_monitor"): _route_after_ci_trigger,
    ("ci_monitor", "end"): _route_after_ci_monitor,
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    reraise=True,
    retry=retry_if_exception_type(Exception),
)
async def _retry_upload_artifact(**kwargs: Any) -> None:
    """Upload a single artifact to MinIO with retry.

    Decorated with tenacity so transient MinIO/network failures
    are retried automatically before propagating the exception.
    """
    persister = kwargs.pop("persister")
    await persister.upload_artifact(**kwargs)


class WorkflowOrchestrator:
    """LangGraph-based workflow orchestrator.

    Builds a StateGraph DAG from the existing state machine VALID_TRANSITIONS
    and provides run() and resume() methods for workflow execution with
    checkpoint persistence via PostgresSaver.
    """

    def __init__(
        self,
        postgres_url: Optional[str] = None,
        event_broadcast: Optional[EventBroadcastService] = None,
        agent_executor: Optional[Any] = None,
        finalizer: Optional[Callable] = None,
    ):
        self._broadcast = event_broadcast or EventBroadcastService()
        self._agent_executor = agent_executor
        self._graph = self._build_graph()
        self._checkpoint_url = postgres_url
        self._finalizer = finalizer

    # ------------------------------------------------------------------
    # Node wrapper — broadcasts phase transitions
    # ------------------------------------------------------------------

    def _wrap_node(self, node_func: Any, node_name: str) -> Any:
        """Wrap a node function to broadcast status transitions."""

        async def _wrapped(state: WorkflowState) -> Dict[str, Any]:
            old_status = state.get("status")
            updates = await node_func(state)
            new_status = updates.get("status", old_status)
            session_id = state.get("id", "")

            error_message = updates.get("error_message")
            if error_message:
                self._broadcast.broadcast_session_failed(session_id, error_message)

            if old_status and new_status and old_status != new_status:
                self._broadcast.broadcast_phase_transition(
                    session_id,
                    old_status,
                    new_status,
                )
                logger.debug(
                    "Broadcast phase_transition: %s → %s (session %s)",
                    old_status,
                    new_status,
                    session_id,
                )

            return updates

        return _wrapped

    def _wrap_coding_node(
        self,
        node_func: Callable,
        agent_executor: Optional[Any],
    ) -> Callable:
        """Wrap the coding node with agent_executor injected."""

        async def _wrapped(state: WorkflowState) -> Dict[str, Any]:
            old_status = state.get("status")
            updates = await node_func(state, agent_executor=agent_executor)
            new_status = updates.get("status", old_status)
            session_id = state.get("id", "")

            if old_status and new_status and old_status != new_status:
                self._broadcast.broadcast_phase_transition(
                    session_id,
                    old_status,
                    new_status,
                )
                logger.debug(
                    "Broadcast phase_transition: %s → %s (session %s)",
                    old_status,
                    new_status,
                    session_id,
                )

            return updates

        return _wrapped

    def _wrap_clarify_node(
        self,
        node_func: Callable,
        event_broadcast: Optional["EventBroadcastService"],
    ) -> Callable:
        """Wrap the clarify node with event_broadcast injected."""

        async def _wrapped(state: WorkflowState) -> Dict[str, Any]:
            old_status = state.get("status") or "CREATED"
            session_id = state.get("id", "")

            # Proactively broadcast transition to CLARIFY phase
            if self._broadcast:
                try:
                    self._broadcast.broadcast_phase_transition(
                        session_id,
                        old_status,
                        "CLARIFY",
                    )
                    logger.debug(
                        "Broadcast proactive phase_transition: %s → CLARIFY (session %s)",
                        old_status,
                        session_id,
                    )
                except Exception:
                    pass

            updates = await node_func(state, event_broadcast=event_broadcast)
            new_status = updates.get("status", old_status)

            if new_status and "CLARIFY" != new_status:
                self._broadcast.broadcast_phase_transition(
                    session_id,
                    "CLARIFY",
                    new_status,
                )
                logger.debug(
                    "Broadcast phase_transition: CLARIFY → %s (session %s)",
                    new_status,
                    session_id,
                )

            return updates

        return _wrapped

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph from VALID_TRANSITIONS."""
        graph = StateGraph(WorkflowState)

        # Add nodes
        for node_func in _NODE_MAP.values():
            name = node_func.__name__.replace("_node_", "")
            if name == "coding":
                graph.add_node(
                    name,
                    self._wrap_coding_node(node_func, self._agent_executor),  # type: ignore[arg-type]
                )
            elif name == "clarify":
                graph.add_node(
                    name,
                    self._wrap_clarify_node(node_func, self._broadcast),  # type: ignore[arg-type]
                )
            else:
                graph.add_node(name, self._wrap_node(node_func, name))

        # START -> conditionally route to clarify or coding
        def _route_start(state: WorkflowState) -> str:
            metadata = state.get("metadata", {})
            if isinstance(metadata, dict) and metadata.get("skip_clarify"):
                return "coding"
            return "clarify"

        graph.add_conditional_edges(
            START, _route_start, {"clarify": "clarify", "coding": "coding"}
        )

        # Conditional edges for all non-terminal states
        _wire_conditional_edges(graph)

        print("DEBUG EDGES:", graph.edges, graph.branches)

        return graph

    def _default_route(self, node: str) -> str:
        """Return the natural next node after a given node on the happy path."""
        _next = {
            "start": "clarify",
            "clarify": "coding",
            "coding": END,
            "validating": "planning",
            "planning": "applying",
            "applying": "testing",
            "testing": "git_push",
            "git_push": "ci_trigger",
            "ci_trigger": "ci_monitor",
            "ci_monitor": END,
        }
        return _next.get(node, "fail")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(
        self,
        session_id: str,
        prompt: str,
        model_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a new workflow from START to a terminal state.

        Args:
            session_id: Session UUID.
            prompt: User's natural language request.
            model_config: Model configuration dict (provider, model_name, api_key, etc.).
            **kwargs: Additional state fields (build_id, user_id, git_repo_url, etc.)
        """
        initial_state: Dict[str, Any] = {
            "id": session_id,
            "prompt": prompt,
            "status": SessionState.CREATED.value,
            "current_iteration": 0,
            "max_iterations": kwargs.get("max_iterations", 5),
            "retry_count": 0,
            **{k: v for k, v in kwargs.items() if k in WorkflowState.__annotations__},
        }

        if model_config:
            if "metadata" not in initial_state:
                initial_state["metadata"] = {}
            initial_state["metadata"]["model_config"] = model_config

        app = self._graph.compile(checkpointer=get_checkpointer(self._checkpoint_url))
        config: Dict[str, Any] = {"configurable": {"thread_id": session_id}}

        try:
            result = await app.ainvoke(initial_state, config=config)  # type: ignore[call-overload]
            logger.info(
                "Workflow run completed for session %s: status=%s",
                session_id,
                result.get("status"),
            )
            # Finalize: delegate to external finalizer if provided, else use built-in
            if self._finalizer:
                await self._finalizer(session_id, result)
            else:
                await self._finalize(session_id, result)
            return {"session_id": session_id, "state": result}
        except Exception:
            logger.exception("Workflow run failed for session %s", session_id)
            # Do NOT call _finalize on failure — the Celery worker's fallback
            # path will update the DB with the correct status.  Writing
            # status=failed here races with the fallback's status=completed.
            return {
                "session_id": session_id,
                "state": {
                    "status": SessionState.FAILED.value,
                    "error": "execution_failed",
                },
            }

    async def resume(
        self, session_id: str, thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resume a workflow from its last checkpoint.

        Args:
            session_id: Session UUID (used as thread_id by default).
            thread_id: Optional override for checkpoint lookup.
        """
        tid = thread_id or session_id
        app = self._graph.compile(checkpointer=get_checkpointer(self._checkpoint_url))
        config: Dict[str, Any] = {"configurable": {"thread_id": tid}}

        try:
            # Get the latest state from checkpoint
            result = await app.aget_state(config=config)  # type: ignore[arg-type]
            if not result.values:
                return {"session_id": session_id, "error": "no_checkpoint_found"}

            logger.info(
                "Resuming workflow for session %s (thread_id=%s)", session_id, tid
            )
            # Resume execution from saved state
            final_state = await app.ainvoke(result.values, config=config)  # type: ignore[call-overload]
            logger.info(
                "Workflow resumed for session %s: status=%s",
                session_id,
                final_state.get("status"),
            )
            if self._finalizer:
                await self._finalizer(session_id, final_state)
            else:
                await self._finalize(session_id, final_state)
            return {"session_id": session_id, "state": final_state}
        except Exception:
            logger.exception("Workflow resume failed for session %s", session_id)
            return {"session_id": session_id, "error": "resume_failed"}

    def _reconstruct_state(self, persisted: Dict[str, Any]) -> Dict[str, Any]:
        """Bridge persistence layer state to LangGraph WorkflowState."""
        return {
            "messages": [],
            "id": persisted.get("id") or "",
            "build_id": persisted.get("build_id") or "",
            "user_id": persisted.get("user_id") or "",
            "prompt": persisted.get("prompt") or "",
            "status": persisted.get("status") or "",
            "current_iteration": persisted.get("current_iteration", 0),
            "max_iterations": persisted.get("max_iterations", 5),
            "retry_count": persisted.get("retry_count", 0),
            "git_repo_url": persisted.get("git_repo_url") or "",
            "git_branch": persisted.get("git_branch") or "",
            "ci_provider": persisted.get("ci_provider") or "",
            "ci_inputs": persisted.get("ci_inputs") or {},
            "generated_code": persisted.get("generated_code") or "",
            "validation_results": persisted.get("validation_results") or {},
            "plan": persisted.get("plan") or "",
            "metadata": persisted.get("metadata") or {},
        }

    def _parse_generated_code_to_files(self, generated_code: str) -> list:
        """Convert WorkflowState.generated_code (string) to generation_jobs.code format.

        If generated_code is a JSON array string, parse it directly.
        If raw text, wrap as [{name: 'main.tf', content: text, language: 'hcl'}].
        """
        if not generated_code:
            return []
        try:
            parsed = json.loads(generated_code)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        # Wrap raw text as single file
        return [{"name": "main.tf", "content": generated_code, "language": "hcl"}]

    async def _finalize(
        self,
        session_id: str,
        final_state: Dict[str, Any],
    ) -> None:
        """Update session status, write code to MinIO, emit events.

        Generated code is stored as objects in the MinIO 'artifacts' bucket.
        File content and metadata are persisted to the DB so the frontend
        status endpoint can serve them back.
        File metadata is stored back into final_state so the Celery worker
        can include it in its SESSION_COMPLETE broadcast.
        """
        status = final_state.get("status", SessionState.FAILED.value)
        generated_code = final_state.get("generated_code", "")

        logger.info(
            "Finalizing session %s with status=%s",
            session_id,
            status,
        )

        file_list: List[Dict[str, Any]] = []
        if generated_code:
            files = self._parse_generated_code_to_files(generated_code)

            # Upload each file to MinIO with retry
            try:
                from modules.artifact_store.artifact_persister import (
                    artifact_persister as persister,
                )

                for file_obj in files:
                    filepath = file_obj["name"]  # e.g. "modules/eks/main.tf"
                    content_bytes = file_obj["content"].encode("utf-8")
                    await _retry_upload_artifact(
                        persister=persister,
                        session_id=session_id,
                        iteration_num=1,
                        artifact_type="code",
                        filename=filepath,
                        content=content_bytes,
                    )
                    # Keep full file objects (with content) so the DB and
                    # frontend can serve them without a MinIO round-trip.
                    file_list.append(
                        {
                            "name": filepath,
                            "content": file_obj["content"],
                            "language": file_obj.get("language", "hcl"),
                            "size": len(content_bytes),
                        }
                    )
                logger.info(
                    "Uploaded %d file(s) to MinIO for session %s",
                    len(files),
                    session_id,
                )
            except Exception:
                logger.exception(
                    "Failed to upload artifacts to MinIO for session %s after retries",
                    session_id,
                )
                # Even if MinIO failed, still persist file content to DB
                for file_obj in files:
                    file_list.append(
                        {
                            "name": file_obj["name"],
                            "content": file_obj["content"],
                            "language": file_obj.get("language", "hcl"),
                        }
                    )

        # Update DB with status and full file objects (including content)
        try:
            from db.db_provider import db_provider
            from modules.workflow_engine.session_manager import session_manager

            error_msg = final_state.get("error_message")
            # Only propagate error to session state when the workflow actually failed.
            # MinIO upload failures during a COMPLETED workflow should not mark the
            # session as errored (the code is still saved to DB).
            is_failed = status not in (
                SessionState.COMPLETED.value,
                SessionState.HUMAN_REVIEW.value,
            )
            if error_msg and is_failed:
                try:
                    await session_manager.set_error(session_id, error_msg)
                except Exception as e:
                    logger.warning(
                        "Failed to set error on session %s: %s", session_id, str(e)
                    )

            # Force update the in-memory session status so WebSocket endpoint detects the terminal state
            try:
                session = await session_manager.get_session(session_id)
                if session:
                    if isinstance(status, str):
                        status_upper = status.upper()
                        if status_upper in ("COMPLETED", "COMPLETE"):
                            session.status = SessionState.COMPLETED
                        elif status_upper in ("FAILED", "FAIL"):
                            session.status = SessionState.FAILED
                        elif status_upper in SessionState.__members__:
                            session.status = SessionState[status_upper]
                        else:
                            session.status = SessionState.FAILED
                    elif isinstance(status, SessionState):
                        session.status = status
                    else:
                        session.status = SessionState.FAILED
            except Exception as e:
                logger.warning("Failed to update in-memory session status: %s", e)

            db_payload: Dict[str, Any] = {"status": status}
            if status == SessionState.COMPLETED.value and file_list:
                db_payload["code"] = file_list
            if error_msg:
                db_payload["error"] = error_msg

            meta = final_state.get("metadata")
            if isinstance(meta, dict) and meta:
                db_payload["metadata"] = meta

            await db_provider.update_generation_job(
                session_id,
                db_payload,
            )
        except Exception:
            logger.warning(
                "DB update failed during finalize for session %s", session_id
            )

        # Store file list in final_state for Celery worker to pick up
        final_state["generated_files"] = file_list

        # Emit completion/failure/review event to Redis pub/sub
        if status == SessionState.COMPLETED.value:
            self._broadcast.broadcast_session_complete(
                session_id, "success", files=file_list
            )
        elif status == SessionState.HUMAN_REVIEW.value:
            meta = final_state.get("metadata", {})
            refined_spec = meta.get("refined_spec") if isinstance(meta, dict) else None
            self._broadcast.broadcast_human_review(
                session_id,
                final_state.get("error_message", "Waiting for human review"),
                refined_spec=refined_spec,
            )
        else:
            self._broadcast.broadcast_session_failed(
                session_id, final_state.get("error_message", "Workflow failed")
            )


def _wire_conditional_edges(graph: StateGraph) -> StateGraph:  # noqa: ANN201
    """Add conditional edges from each node to its possible next states."""
    # Each node maps to its possible outputs based on VALID_TRANSITIONS
    _node_outcomes: Dict[str, list] = {
        "clarify": ["coding", "human_review"],
        "coding": [END],
        "validating": ["planning"],
        "planning": ["applying"],
        "applying": ["testing"],
        "testing": ["git_push"],
        "git_push": ["ci_trigger"],
        "ci_trigger": ["ci_monitor"],
        "ci_monitor": [END],
    }

    for node, outcomes in _node_outcomes.items():
        if len(outcomes) == 1:
            # Single default outcome with conditional routing for error paths
            mapping = {outcomes[0]: outcomes[0], "fail": "fail"}
            graph.add_conditional_edges(
                node, lambda s, n=node: _route_failover(s, n), mapping
            )
        else:
            mapping = {o: o for o in outcomes}
            mapping["fail"] = "fail"
            graph.add_conditional_edges(
                node,
                lambda s, outcomes=outcomes, n=node: _route_multiple(s, n, outcomes),
                mapping,
            )

    return graph


def _get_status_str(state: WorkflowState) -> str:
    """Helper to safely extract the string value of the status."""
    status = state.get("status", "")
    return status.value if hasattr(status, "value") else str(status)


def _route_multiple(state: WorkflowState, node: str, outcomes: list[str]) -> str:
    """Route to a specific outcome based on status, or fail."""
    status_str = _get_status_str(state)
    if status_str == "FAILED":
        return "fail"
    for o in outcomes:
        if o == "fail":
            continue
        try:
            # Try to look up the enum value by upper-casing o (e.g. 'coding' -> 'CODING')
            val = SessionState(o.upper()).value
        except ValueError:
            val = None
        if status_str == o or (val and status_str == val):
            return o
    # Default: first non-fail outcome
    return outcomes[0] if outcomes else "fail"


def _route_outcomes(state: WorkflowState, outcomes: list[str]) -> str:
    """Default outcome router for add_conditional_edges."""
    return outcomes[0] if outcomes else "fail"


def _route_failover(state: WorkflowState, node: str) -> str:
    """Route to fail or the default next node based on error state."""
    if _get_status_str(state) == SessionState.FAILED.value:
        return "fail"
    _next = {
        "start": "clarify",
        "clarify": "coding",
        "coding": END,
        "validating": "planning",
        "planning": "applying",
        "applying": "testing",
        "testing": "git_push",
        "git_push": "ci_trigger",
        "ci_trigger": "ci_monitor",
        "ci_monitor": END,
    }
    return _next.get(node, "fail")
