import json

from typing import Any, Callable, Dict, Optional, Union

from models.iac_state import IaCState

from models.error_classes import ErrorClass

from models.pipeline_phases import PipelinePhase

from repositories.state_repository import StateRepository

from agents.base_agent import BaseAgent

from agents.clarify_agent import ClarifyAgent

from agents.generator_agent import GeneratorAgent

from agents.static_analysis_agent import StaticAnalysisAgent

from agents.command_agents import CommandType, CommandAgentFactory

from agents.apply_agent import ApplyAgent

import logging

logger = logging.getLogger(__name__)

AgentFactory = Union[type, Callable[[], BaseAgent], None]


class AgenticPipeline:
    """Orchestrates the execution of the agentic IaC pipeline."""

    def __init__(self, state_repository: Optional[StateRepository] = None):
        self.state_repository = state_repository or StateRepository()
        self.state: Optional[IaCState] = None
        self.current_agent: Optional[BaseAgent] = None
        self.phase_handlers: Dict[PipelinePhase, AgentFactory] = (
            self._initialize_phase_handlers()
        )
        self.running = False

    def _initialize_phase_handlers(self) -> Dict[PipelinePhase, AgentFactory]:
        """Initialize the mapping of pipeline phases to agent handlers."""
        return {
            PipelinePhase.CLARIFY: ClarifyAgent,
            PipelinePhase.GENERATE: GeneratorAgent,
            PipelinePhase.FORMAT: lambda: CommandAgentFactory.create_agent(
                CommandType.FORMAT
            ),
            PipelinePhase.STATIC_ANALYSIS: StaticAnalysisAgent,
            PipelinePhase.INIT: lambda: CommandAgentFactory.create_agent(
                CommandType.INIT
            ),
            PipelinePhase.VALIDATE: lambda: CommandAgentFactory.create_agent(
                CommandType.VALIDATE
            ),
            PipelinePhase.PLAN_REVIEW: lambda: CommandAgentFactory.create_agent(
                CommandType.PLAN
            ),
            PipelinePhase.APPLY_REVIEW: ApplyAgent,
            PipelinePhase.APPLY: ApplyAgent,
            PipelinePhase.ESCALATE: None,
            PipelinePhase.COMPLETE: None,
        }

    async def start_pipeline(
        self, user_request: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a new pipeline with the given user request."""
        try:
            # Create initial state
            state_data: Dict[str, Any] = {
                "user_request": user_request,
                "current_phase": PipelinePhase.CLARIFY,
            }
            if session_id:
                state_data["session_id"] = session_id
            self.state = IaCState(**state_data)
            # Save initial state
            if not self.state_repository.save_state(self.state):
                return {
                    "success": False,
                    "error": "Failed to save initial pipeline state",
                    "error_class": ErrorClass.FATAL,
                }
            self.log_message("Pipeline started")
            self.running = True
            # Start the pipeline execution
            result = await self._execute_current_phase()
            self.running = False
            return result
        except Exception as e:
            self.running = False
            return {"success": False, "error": str(e), "error_class": ErrorClass.FATAL}

    async def resume_pipeline(self, session_id: str) -> Dict[str, Any]:
        """Resume an existing pipeline from a checkpoint."""
        try:
            # Load state from repository
            self.state = self.state_repository.load_state(session_id)
            if not self.state:
                return {
                    "success": False,
                    "error": f"Pipeline state not found for session: {session_id}",
                    "error_class": ErrorClass.FATAL,
                }
            self.log_message(f"Resumed pipeline from session: {session_id}")
            self.running = True
            # Continue execution from current phase
            result = await self._execute_current_phase()
            self.running = False
            return result
        except Exception as e:
            self.running = False
            return {"success": False, "error": str(e), "error_class": ErrorClass.FATAL}

    async def _execute_current_phase(self) -> Dict[str, Any]:
        """Execute the current phase of the pipeline."""
        if not self.state:
            return {
                "success": False,
                "error": "No pipeline state available",
                "error_class": ErrorClass.FATAL,
            }
        current_phase = self.state.current_phase
        self.log_message(f"Executing phase: {current_phase.value}")
        # Handle terminal phases
        if current_phase == PipelinePhase.COMPLETE:
            return {
                "success": True,
                "result": {"message": "Pipeline completed successfully"},
            }
        if current_phase == PipelinePhase.ESCALATE:
            return await self._handle_escalation()
        # Get the agent for the current phase
        agent_factory = self.phase_handlers.get(current_phase)
        if not agent_factory:
            error_msg = f"No agent configured for phase: {current_phase.value}"
            self.log_message(error_msg, "error")
            return {
                "success": False,
                "error": error_msg,
                "error_class": ErrorClass.FATAL,
                "next_phase": PipelinePhase.ESCALATE,
            }
        # Create and initialize the agent
        try:
            if callable(agent_factory) and not isinstance(agent_factory, type):
                self.current_agent = agent_factory()
            elif isinstance(agent_factory, type):
                self.current_agent = agent_factory()
            else:
                error_msg = f"No agent configured for phase: {current_phase.value}"
                self.log_message(error_msg, "error")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_class": ErrorClass.FATAL,
                    "next_phase": PipelinePhase.ESCALATE,
                }
            assert self.current_agent is not None
            if not await self.current_agent.initialize(self.state):
                error_msg = (
                    f"Failed to initialize agent for phase: {current_phase.value}"
                )
                self.log_message(error_msg, "error")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_class": ErrorClass.FATAL,
                    "next_phase": PipelinePhase.ESCALATE,
                }
        except Exception as e:
            error_msg = f"Error initializing agent: {str(e)}"
            self.log_message(error_msg, "error")
            return {
                "success": False,
                "error": error_msg,
                "error_class": ErrorClass.FATAL,
                "next_phase": PipelinePhase.ESCALATE,
            }
        # Execute the agent
        assert self.current_agent is not None
        result = await self.current_agent.execute()
        # Handle the result
        return await self._handle_agent_result(result)

    async def _handle_agent_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the result from an agent execution."""
        assert self.state, "Pipeline state must be set"
        if not result.get("success", False):
            # Agent failed - handle error
            return await self._handle_agent_error(result)
        # Agent succeeded - transition to next phase
        next_phase = result.get("next_phase")
        if not next_phase:
            error_msg = "No next phase specified in agent result"
            self.log_message(error_msg, "error")
            return {
                "success": False,
                "error": error_msg,
                "error_class": ErrorClass.FATAL,
                "next_phase": PipelinePhase.ESCALATE,
            }
        # Update state and save
        self.state.current_phase = next_phase
        # Save state checkpoint
        if not self.state_repository.save_state(self.state):
            self.log_message("Failed to save state checkpoint", "warning")
        # Log phase transition
        self.log_message(f"Transitioning to phase: {next_phase.value}")
        # Continue execution if not in terminal phase
        if next_phase not in [PipelinePhase.COMPLETE, PipelinePhase.ESCALATE]:
            return await self._execute_current_phase()
        # Return final result
        return {
            "success": True,
            "result": result.get("result", {}),
            "next_phase": next_phase,
        }

    async def _handle_agent_error(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors from agent execution."""
        assert self.state, "Pipeline state must be set"
        error = result.get("error", "Unknown error")
        error_class = result.get("error_class", ErrorClass.FATAL)
        next_phase = result.get("next_phase", PipelinePhase.ESCALATE)
        self.log_message(f"Agent error: {error} (class: {error_class.value})", "error")
        # Update state with error information
        self.state.last_error = error
        self.state.last_error_class = error_class
        # Save error state
        if not self.state_repository.save_state(self.state):
            self.log_message("Failed to save error state", "warning")
        # Return error result
        return {
            "success": False,
            "error": error,
            "error_class": error_class,
            "next_phase": next_phase,
            "retry_feedback": result.get("retry_feedback"),
        }

    async def _handle_escalation(self) -> Dict[str, Any]:
        """Handle the escalation phase."""
        assert self.state, "Pipeline state must be set"
        self.log_message("Entering escalation phase")
        # In a real implementation, this would:
        # 1. Checkpoint the current state
        # 2. Notify human operators (Slack, PagerDuty, etc.)
        # 3. Wait for human intervention
        # 4. Resume with updated state
        # For simulation, we'll just mark as escalated
        return {
            "success": False,
            "error": "Pipeline requires human intervention",
            "error_class": ErrorClass.HUMAN_REQUIRED,
            "next_phase": PipelinePhase.ESCALATE,
            "escalation_info": {
                "session_id": self.state.session_id,
                "current_phase": self.state.current_phase.value,
                "last_error": self.state.last_error,
                "error_class": self.state.last_error_class.value
                if self.state.last_error_class
                else "unknown",
            },
        }

    async def approve_plan(self, session_id: str) -> Dict[str, Any]:
        """Approve a plan for execution."""
        try:
            state = self.state_repository.load_state(session_id)
            if not state:
                return {
                    "success": False,
                    "error": f"Pipeline state not found: {session_id}",
                    "error_class": ErrorClass.FATAL,
                }
            # Mark plan as approved
            state.approvals["plan_approved"] = True
            # Save updated state
            if not self.state_repository.save_state(state):
                return {
                    "success": False,
                    "error": "Failed to save approval state",
                    "error_class": ErrorClass.FATAL,
                }
            self.log_message(f"Plan approved for session: {session_id}")
            return {
                "success": True,
                "result": {"message": "Plan approved successfully"},
            }
        except Exception as e:
            return {"success": False, "error": str(e), "error_class": ErrorClass.FATAL}

    async def handle_human_intervention(
        self, session_id: str, intervention_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle human intervention and resume pipeline."""
        try:
            # Load the state
            state = self.state_repository.load_state(session_id)
            if not state:
                return {
                    "success": False,
                    "error": f"Pipeline state not found: {session_id}",
                    "error_class": ErrorClass.FATAL,
                }
            # Apply the intervention
            if "hcl_code" in intervention_data:
                state.hcl_code = intervention_data["hcl_code"]
                state.retry_feedback = "Human intervention: Updated HCL code"
            if "refined_spec" in intervention_data:
                state.refined_spec = json.dumps(intervention_data["refined_spec"])
                state.retry_feedback = (
                    "Human intervention: Updated refined specification"
                )
            if "answers" in intervention_data:
                state.retry_feedback = json.dumps(intervention_data["answers"])
            # Clear last error if this is a correction
            if intervention_data.get("clear_error", False):
                state.last_error = None
                state.last_error_class = None
            # Save updated state
            if not self.state_repository.save_state(state):
                return {
                    "success": False,
                    "error": "Failed to save intervention state",
                    "error_class": ErrorClass.FATAL,
                }
            self.log_message(f"Human intervention applied to session: {session_id}")
            # Resume the pipeline
            return await self.resume_pipeline(session_id)
        except Exception as e:
            return {"success": False, "error": str(e), "error_class": ErrorClass.FATAL}

    async def stop_pipeline(self) -> Dict[str, Any]:
        """Stop the currently running pipeline."""
        if not self.running:
            return {
                "success": False,
                "error": "No pipeline is currently running",
                "error_class": ErrorClass.FATAL,
            }
        self.running = False
        self.log_message("Pipeline stopped by user request")
        if self.current_agent:
            try:
                await self.current_agent.cleanup()
            except Exception as e:
                self.log_message(f"Error during agent cleanup: {str(e)}", "warning")
        return {"success": True, "result": {"message": "Pipeline stopped successfully"}}

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with pipeline context."""
        context = {
            "pipeline": "agentic_loop",
            "session_id": self.state.session_id if self.state else "no_state",
            "phase": self.state.current_phase.value if self.state else "unknown",
        }
        if level == "info":
            logger.info(message, extra=context)
        elif level == "warning":
            logger.warning(message, extra=context)
        elif level == "error":
            logger.error(message, extra=context)
        else:
            logger.debug(message, extra=context)

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get the current status of the pipeline."""
        if not self.state:
            return {"status": "not_started", "error": "No pipeline state available"}
        return {
            "status": "running" if self.running else "paused",
            "session_id": self.state.session_id,
            "current_phase": self.state.current_phase.value,
            "started_at": self.state.started_at.isoformat(),
            "completed_at": self.state.completed_at.isoformat()
            if self.state.completed_at
            else None,
            "last_error": self.state.last_error,
            "error_class": self.state.last_error_class.value
            if self.state.last_error_class
            else None,
            "retry_counts": self.state.retry_counts,
            "approvals": self.state.approvals,
        }
