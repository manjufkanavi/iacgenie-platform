import logging
import uuid
from typing import Dict, Any, List, Optional
from enum import Enum

from models.iac_state import IaCState
from models.error_classes import ErrorClass
from models.pipeline_phases import PipelinePhase
from .base_agent import BaseAgent
from src.sandbox_manager import ContainerProvisioner, CommandExecutor

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Types of commands that can be executed."""

    FORMAT = "format"
    INIT = "init"
    VALIDATE = "validate"
    PLAN = "plan"
    APPLY = "apply"
    GIT_PUSH = "git_push"
    CI_TRIGGER = "ci_trigger"
    CI_MONITOR = "ci_monitor"


class CommandAgentFactory:
    """Factory for creating command execution agents."""

    @staticmethod
    def create_agent(
        command_type: CommandType,
        provisioner: Optional[ContainerProvisioner] = None,
        executor: Optional[CommandExecutor] = None,
    ) -> "CommandAgent":
        """Create a command agent for the specified command type."""
        return CommandAgent(
            command_type,
            provisioner=provisioner,
            executor=executor,
        )


class CommandAgent(BaseAgent):
    """Agent responsible for executing Terraform/OpenTofu commands via the Sandbox Manager."""

    def __init__(
        self,
        command_type: CommandType,
        provisioner: Optional[ContainerProvisioner] = None,
        executor: Optional[CommandExecutor] = None,
    ):
        self.command_type = command_type
        super().__init__(f"{command_type.value}_agent")
        self.max_retries = 3
        self.sandbox_id: Optional[str] = None
        self.container_id: Optional[str] = None
        self.session_id: str = ""
        self.provisioner = provisioner or ContainerProvisioner()
        self.executor = executor or CommandExecutor()

    async def initialize(self, state: IaCState) -> bool:
        """Initialize the command agent and provision a sandbox."""
        await super().initialize(state)
        # Use existing session ID or create a new one
        if hasattr(state, "session_id") and state.session_id:
            self.session_id = state.session_id
        else:
            self.session_id = str(uuid.uuid4())
            state.session_id = self.session_id

        if hasattr(state, "sandbox_id") and state.sandbox_id:
            self.sandbox_id = state.sandbox_id
            self.container_id = getattr(state, "container_id", None)
        else:
            # Defer sandbox creation to _prepare_workspace to handle errors properly within execute() flow
            pass

        return True

    async def execute(self) -> Dict[str, Any]:
        """
        Execute the command agent logic locally.
        """
        try:
            # Files are already written by AgentExecutor to the workspace directory.
            # We just need to find the workspace directory.
            from src.sandbox_manager.config import config

            workspace_dir = f"{config.WORKSPACE_ROOT}/{self.session_id}"

            # Ensure provider config exists for init
            if self.command_type == CommandType.INIT:
                await self._ensure_provider_configuration_local(workspace_dir)

            # Execute the command locally
            result = await self._execute_command_local(workspace_dir)

            if not result["success"]:
                # Command failed - classify error and determine next steps
                error_class = self._classify_command_error(result["error"])
                if error_class == ErrorClass.RETRYABLE and self.state is not None:
                    retry_count = self.state.retry_counts.get(
                        self.command_type.value, 0
                    )
                    if retry_count < self.max_retries:
                        # Prepare feedback for retry
                        retry_feedback = f"{self.command_type.value} failed: {result['error']}. Please correct."
                        self.state.retry_counts[self.command_type.value] = (
                            retry_count + 1
                        )
                        self.state.retry_feedback = retry_feedback
                        self.log_message(
                            f"Retrying {self.command_type.value} (attempt {retry_count + 1})",
                            "warning",
                        )
                        return {
                            "success": False,
                            "error": result["error"],
                            "error_class": error_class,
                            "next_phase": PipelinePhase.GENERATE,  # Go back to generation for correction
                            "retry_feedback": retry_feedback,
                        }
                # Non-retryable or max retries exceeded - escalate
                return {
                    "success": False,
                    "error": result["error"],
                    "error_class": error_class,
                    "next_phase": PipelinePhase.ESCALATE,
                }

            # Command succeeded
            self.log_message(f"{self.command_type.value} command executed successfully")

            # Determine next phase based on command type
            next_phase = self._get_next_phase_after_success()
            return {
                "success": True,
                "next_phase": next_phase,
                "result": {
                    "output": result["output"],
                    "message": f"{self.command_type.value} completed successfully",
                },
            }
        except Exception as e:
            error_result = await self.handle_error(e)
            return {
                "success": False,
                "error": str(e),
                "error_class": error_result["error_class"],
                "next_phase": PipelinePhase.ESCALATE,
            }

    async def _ensure_provider_configuration_local(self, workspace_dir: str) -> bool:
        """Ensure provider configuration exists for init command."""
        try:
            import os

            # Parse refined spec to get provider requirements
            if self.state is None or not self.state.refined_spec:
                self.log_message(
                    "No refined spec available for provider configuration", "warning"
                )
                return True
            import json

            refined_spec = json.loads(self.state.refined_spec)
            provider = refined_spec.get("provider", "aws")
            region = refined_spec.get("region", "us-west-2")

            # Create provider.tf content
            provider_content = f'provider "{provider}" {{\n  region = "{region}"\n}}\n'

            os.makedirs(workspace_dir, exist_ok=True)
            with open(os.path.join(workspace_dir, "provider.tf"), "w") as f:
                f.write(provider_content)
            return True

        except Exception as e:
            self.log_message(
                f"Failed to ensure provider configuration: {str(e)}", "warning"
            )
            return True

    async def _execute_command_local(self, workspace_dir: str) -> Dict[str, Any]:
        """Execute the specific command locally."""
        try:
            import asyncio

            # Build the command
            command = self._build_command()
            self.log_message(
                f"Executing command locally in {workspace_dir}: {' '.join(command)}"
            )

            # Setup Redis client for streaming if we have a deployment ID or session ID
            stream_callback = None
            redis_client = None
            try:
                from backend.src.workflow_engine.config import WorkflowConfig
                from backend.src.workflow_engine.redis_client import RedisClient

                try:
                    redis_config = WorkflowConfig()
                except ImportError:
                    import sys
                    import os

                    sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
                    from src.workflow_engine.config import WorkflowConfig as WC

                    redis_config = WC()

                redis_client = RedisClient(config=redis_config)
                redis_client.connect()

                channel_id = f"deployment:logs:{self.session_id}"
                if hasattr(self.state, "metadata") and self.state.metadata:  # type: ignore[union-attr]
                    dep_id = self.state.metadata.get("deploymentId")  # type: ignore[union-attr]
                    if dep_id:
                        channel_id = f"deployment:logs:{dep_id}"

                def _stream_callback(line: str) -> None:
                    if line.strip() and redis_client and redis_client.is_connected():
                        payload = {"log": line, "command": self.command_type.value}
                        redis_client.publish(channel_id, payload)

                stream_callback = _stream_callback
            except Exception as e:
                self.log_message(
                    f"Failed to initialize Redis streaming: {str(e)}", "warning"
                )

            # Run using asyncio.create_subprocess_exec
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_dir,
            )

            stdout_chunks: List[str] = []
            stderr_chunks: List[str] = []

            async def read_stream(
                stream: Optional[asyncio.StreamReader], chunks_list: List[str], cb: Any
            ) -> None:
                if not stream:
                    return
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    chunks_list.append(text)
                    if cb:
                        cb(text)

            await asyncio.gather(
                read_stream(process.stdout, stdout_chunks, stream_callback),
                read_stream(process.stderr, stderr_chunks, stream_callback),
            )

            exit_code = await process.wait()

            try:
                if redis_client and redis_client.is_connected():
                    redis_client.disconnect()
            except Exception:
                pass

            output = "".join(stdout_chunks)
            error = "".join(stderr_chunks)

            # Log command output
            if output:
                self.log_message(f"Command output: {output}", "debug")
            if error:
                self.log_message(f"Command error: {error}", "debug")

            return {
                "success": exit_code == 0,
                "output": output,
                "error": error if exit_code != 0 else None,
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Failed to execute {self.command_type.value} command: {str(e)}",
            }

    def _build_command(self) -> List[str]:
        """Build the command to execute based on command type."""
        if self.command_type == CommandType.FORMAT:
            return ["tofu", "fmt", "-recursive"]
        elif self.command_type == CommandType.INIT:
            return ["tofu", "init", "-upgrade"]
        elif self.command_type == CommandType.VALIDATE:
            return ["tofu", "validate"]
        elif self.command_type == CommandType.PLAN:
            return ["tofu", "plan", "-out=tfplan"]
        elif self.command_type == CommandType.APPLY:
            return ["tofu", "apply", "-auto-approve", "tfplan"]
        elif self.command_type == CommandType.GIT_PUSH:
            import shlex

            state_ref: Dict[str, Any] = self.state.model_dump() if self.state else {}
            branch = (
                state_ref.get("git_branch", "main")
                if isinstance(state_ref, dict)
                else getattr(state_ref, "git_branch", "main")
            )
            commit_msg = (
                state_ref.get("git_commit_msg", "Auto-commit IaC changes")
                if isinstance(state_ref, dict)
                else getattr(state_ref, "git_commit_msg", "Auto-commit IaC changes")
            )
            safe_branch = shlex.quote(branch)
            safe_msg = shlex.quote(commit_msg)
            return [
                "sh",
                "-c",
                f"git add . && git commit -m {safe_msg} && git push origin {safe_branch}",
            ]
        else:
            raise ValueError(f"Unknown command type: {self.command_type}")

    def _classify_command_error(self, error: str) -> ErrorClass:
        """Classify command errors."""
        if not error:
            return ErrorClass.FATAL
        error_lower = error.lower()
        # Retryable errors
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "failed to install provider",
            "plugin initialization",
            "locking",
        ]
        for pattern in retryable_patterns:
            if pattern in error_lower:
                return ErrorClass.RETRYABLE
        # Clarification needed
        clarification_patterns = [
            "invalid",
            "syntax",
            "argument",
            "parameter",
            "configuration",
        ]
        for pattern in clarification_patterns:
            if pattern in error_lower:
                return ErrorClass.CLARIFICATION
        # Human required
        human_patterns = ["permission", "access", "authentication", "quota", "limit"]
        for pattern in human_patterns:
            if pattern in error_lower:
                return ErrorClass.HUMAN_REQUIRED
        # Default to fatal
        return ErrorClass.FATAL

    def _get_next_phase_after_success(self) -> PipelinePhase:
        """Determine the next phase after successful command execution."""
        command_phase_map = {
            CommandType.FORMAT: PipelinePhase.STATIC_ANALYSIS,
            CommandType.INIT: PipelinePhase.VALIDATE,
            CommandType.VALIDATE: PipelinePhase.PLAN_REVIEW,
            CommandType.PLAN: PipelinePhase.APPLY_REVIEW,
            CommandType.APPLY: PipelinePhase.COMPLETE,
            CommandType.GIT_PUSH: PipelinePhase.CI_TRIGGER,
            CommandType.CI_TRIGGER: PipelinePhase.CI_MONITOR,
            CommandType.CI_MONITOR: PipelinePhase.COMPLETE,
        }
        return command_phase_map.get(self.command_type, PipelinePhase.ESCALATE)

    async def cleanup(self) -> None:
        """Clean up sandbox if needed."""
        # For apply commands, we might want to keep the workspace
        # For other commands, clean up if not needed
        if self.command_type != CommandType.APPLY and self.container_id:
            try:
                await self.provisioner.stop_container(self.container_id)
                self.log_message(f"Cleaned up sandbox container: {self.container_id}")
            except Exception as e:
                self.log_message(
                    f"Failed to clean up sandbox container: {str(e)}", "warning"
                )

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors specific to command agents."""
        error_class = self.classify_error(error)
        # Custom error handling for commands
        error_message = str(error)
        if "timeout" in error_message.lower():
            error_class = ErrorClass.RETRYABLE
        elif "permission" in error_message.lower():
            error_class = ErrorClass.HUMAN_REQUIRED
        return {
            "error_class": error_class,
            "message": f"Command execution error: {error_message}",
            "can_retry": error_class == ErrorClass.RETRYABLE,
            "retry_feedback": f"Command failed: {error_message}",
        }
