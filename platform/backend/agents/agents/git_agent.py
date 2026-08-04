"""Git agent for performing git operations in sandboxes."""

import logging
from typing import Dict, Any, Optional

from models.iac_state import IaCState
from models.error_classes import ErrorClass
from models.pipeline_phases import PipelinePhase
from .base_agent import BaseAgent
# sandbox_manager module not found - ContainerProvisioner, Any

logger = logging.getLogger(__name__)


class GitAgent(BaseAgent):
    """Agent responsible for executing git operations (init, add, commit, push) in a sandbox."""

    def __init__(
        self,
        provisioner: Optional[Any] = None,
        executor: Optional[Any] = None,
    ):
        super().__init__("git_agent")
        self.provisioner = provisioner or None
        self.executor = executor or Any()
        self.sandbox_id: Optional[str] = None
        self.container_id: Optional[str] = None
        self.session_id: str = ""
        self.branch: str = "main"
        self.commit_msg: str = "Auto-commit IaC changes"

    async def initialize(self, state: IaCState) -> bool:
        """Initialize the git agent and get sandbox context."""
        await super().initialize(state)
        if hasattr(state, "session_id") and state.session_id:
            self.session_id = state.session_id
        if hasattr(state, "sandbox_id") and state.sandbox_id:
            self.sandbox_id = state.sandbox_id
            self.container_id = getattr(state, "container_id", None)
            if self.container_id:
                self.branch = getattr(state, "git_branch", "main") or "main"
                self.commit_msg = (
                    getattr(state, "git_commit_msg", "Auto-commit IaC changes")
                    or "Auto-commit IaC changes"
                )
        return True

    async def execute(self) -> Dict[str, Any]:
        """Execute git push workflow."""
        try:
            if not self.container_id:
                return {
                    "success": False,
                    "error": "No container ID available for git operations",
                    "error_class": ErrorClass.FATAL,
                    "next_phase": PipelinePhase.ESCALATE,
                }

            result = await self._execute_git_push()

            if not result["success"]:
                return {
                    "success": False,
                    "error": result["error"],
                    "error_class": ErrorClass.CLARIFICATION,
                    "next_phase": PipelinePhase.ESCALATE,
                }

            self.log_message("Git push completed successfully")
            return {
                "success": True,
                "next_phase": PipelinePhase.CI_TRIGGER,
                "result": {
                    "message": "Code pushed to remote repository",
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

    async def _execute_git_push(self) -> Dict[str, Any]:
        """Execute git init, add, commit, and push in the sandbox."""
        if not self.container_id:
            return {
                "success": False,
                "error": "No container ID available for git operations",
                "error_class": ErrorClass.FATAL,
                "next_phase": PipelinePhase.ESCALATE,
            }
        try:
            cmd = [
                "sh",
                "-c",
                f"cd /workspace && "
                f"git init && "
                f"git add . && "
                f'git commit -m "{self.commit_msg}" && '
                f"git push origin {self.branch}",
            ]
            self.log_message(f"Executing git push in container {self.container_id}")

            result = await self.executor.execute_command(
                container_id=self.container_id,
                command=cmd,
            )

            output = result.get("stdout", "")
            error = result.get("stderr", "")
            exit_code = result.get("exit_code", -1)

            if output:
                self.log_message(f"Git output: {output}", "debug")
            if error:
                self.log_message(f"Git error: {error}", "debug")

            return {
                "success": exit_code == 0,
                "output": output,
                "error": error if exit_code != 0 else None,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Git push failed: {str(e)}",
            }

    async def cleanup(self) -> None:
        """No cleanup needed for git operations."""
        pass

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle git-specific errors."""
        error_class = self.classify_error(error)
        error_message = str(error)
        if (
            "permission" in error_message.lower()
            or "authentication" in error_message.lower()
        ):
            error_class = ErrorClass.HUMAN_REQUIRED
        return {
            "error_class": error_class,
            "message": f"Git operation error: {error_message}",
            "can_retry": error_class == ErrorClass.RETRYABLE,
            "retry_feedback": f"Git operation failed: {error_message}",
        }
