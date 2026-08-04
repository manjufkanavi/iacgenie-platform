import os

import hashlib

import subprocess

from typing import Dict, Any, List

from models.iac_state import IaCState

from models.error_classes import ErrorClass

from models.pipeline_phases import PipelinePhase

from .base_agent import BaseAgent

import logging

logger = logging.getLogger(__name__)


class ApplyAgent(BaseAgent):
    """Agent responsible for applying Terraform changes with drift detection and rollback."""

    def __init__(self):
        super().__init__("apply_agent")
        self.approved_plan_hash = None
        self.workspace_dir = None

    async def initialize(self, state: IaCState) -> bool:
        """Initialize the apply agent."""
        await super().initialize(state)
        # Verify we have a workspace
        if not state.work_dir:
            raise ValueError("No workspace directory specified for apply operation")
        self.workspace_dir = state.work_dir
        # Verify the workspace exists
        if not os.path.exists(self.workspace_dir):
            raise ValueError(
                f"Workspace directory does not exist: {self.workspace_dir}"
            )
        # Calculate hash of the approved plan file
        self.approved_plan_hash = await self._calculate_plan_hash()
        return True

    async def execute(self) -> Dict[str, Any]:
        """
        Execute the apply agent logic with drift detection.
        Returns:
            Dictionary with execution results including:
            - success: bool
            - output: apply output
            - next_phase: next pipeline phase
            - error: optional error details
        """
        try:
            # Check if plan approval is given
            if not self._is_plan_approved():
                error_msg = "Plan not approved - cannot apply"
                self.log_message(error_msg, "error")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_class": ErrorClass.HUMAN_REQUIRED,
                    "next_phase": PipelinePhase.ESCALATE,
                }
            # Verify plan file exists
            plan_file = os.path.join(self.workspace_dir or ".", "tfplan")
            if not os.path.exists(plan_file):
                error_msg = "Plan file not found - cannot apply"
                self.log_message(error_msg, "error")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_class": ErrorClass.FATAL,
                    "next_phase": PipelinePhase.ESCALATE,
                }
            # Check for drift (compare current plan with approved plan)
            if not await self._check_for_drift():
                error_msg = "Drift detected - current plan differs from approved plan"
                self.log_message(error_msg, "error")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_class": ErrorClass.HUMAN_REQUIRED,
                    "next_phase": PipelinePhase.ESCALATE,
                }
            # Execute the apply
            result = await self._execute_apply()
            if not result["success"]:
                # Apply failed - attempt rollback
                rollback_result = await self._attempt_rollback()
                if rollback_result["success"]:
                    self.log_message("Apply failed but rollback succeeded", "warning")
                    return {
                        "success": False,
                        "error": result["error"],
                        "error_class": ErrorClass.FATAL,
                        "next_phase": PipelinePhase.ESCALATE,
                        "rollback_status": "success",
                    }
                else:
                    self.log_message("Apply failed and rollback also failed", "error")
                    return {
                        "success": False,
                        "error": f"Apply failed: {result['error']}. Rollback also failed: {rollback_result['error']}",
                        "error_class": ErrorClass.FATAL,
                        "next_phase": PipelinePhase.ESCALATE,
                        "rollback_status": "failed",
                    }
            # Apply succeeded
            self.log_message("Apply completed successfully")
            # Update state
            self.state.completed_at = __import__("datetime").datetime.utcnow()  # type: ignore[union-attr]
            return {
                "success": True,
                "next_phase": PipelinePhase.COMPLETE,
                "result": {
                    "output": result["output"],
                    "message": "Apply completed successfully",
                    "resources_created": self._parse_created_resources(
                        result["output"]
                    ),
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

    def _is_plan_approved(self) -> bool:
        """Check if the plan has been approved."""
        return bool(self.state.approvals.get("plan_approved", False))  # type: ignore[union-attr]

    async def _calculate_plan_hash(self) -> str:
        """Calculate SHA256 hash of the plan file."""
        plan_file = os.path.join(self.workspace_dir or ".", "tfplan")
        if not os.path.exists(plan_file):
            raise FileNotFoundError(f"Plan file not found: {plan_file}")
        hash_sha256 = hashlib.sha256()
        with open(plan_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def _check_for_drift(self) -> bool:
        """Check for drift by comparing current plan with approved plan."""
        try:
            # Calculate current plan hash
            current_hash = await self._calculate_plan_hash()
            # Compare with approved plan hash
            if current_hash != self.approved_plan_hash:
                self.log_message(
                    f"Drift detected: current hash {current_hash} != approved hash {self.approved_plan_hash}",
                    "warning",
                )
                return False
            self.log_message("No drift detected - plan matches approved version")
            return True
        except Exception as e:
            self.log_message(f"Failed to check for drift: {str(e)}", "error")
            return False

    async def _execute_apply(self) -> Dict[str, Any]:
        """Execute the terraform apply command."""
        try:
            command = ["tofu", "apply", "-auto-approve", "tfplan"]
            self.log_message(f"Executing apply command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )
            output = result.stdout
            error = result.stderr
            if output:
                self.log_message(f"Apply output: {output}", "debug")
            if error:
                self.log_message(f"Apply error: {error}", "debug")
            return {
                "success": result.returncode == 0,
                "output": output,
                "error": error if result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Apply command timed out after 600 seconds",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": "tofu binary not found - cannot execute apply",
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Failed to execute apply: {str(e)}",
            }

    async def _attempt_rollback(self) -> Dict[str, Any]:
        """Attempt to rollback by destroying created resources."""
        try:
            self.log_message("Attempting rollback by destroying created resources")
            # Try to destroy resources
            command = ["tofu", "destroy", "-auto-approve"]
            result = subprocess.run(
                command,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            output = result.stdout
            error = result.stderr
            if output:
                self.log_message(f"Rollback output: {output}", "debug")
            if error:
                self.log_message(f"Rollback error: {error}", "debug")
            return {
                "success": result.returncode == 0,
                "output": output,
                "error": error if result.returncode != 0 else None,
            }
        except Exception as e:
            self.log_message(f"Rollback failed: {str(e)}", "error")
            return {
                "success": False,
                "output": "",
                "error": f"Rollback failed: {str(e)}",
            }

    def _parse_created_resources(self, output: str) -> List[str]:
        """Parse the apply output to extract created resources."""
        created_resources = []
        # Look for lines indicating resource creation
        lines = output.split("\n")
        for line in lines:
            if "will be created" in line.lower() or "created" in line.lower():
                # Extract resource name
                parts = line.split()
                for part in parts:
                    if "." in part and "will" not in part and "be" not in part:
                        created_resources.append(part)
        return created_resources

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors specific to the apply agent."""
        error_class = self.classify_error(error)
        # Custom error handling for apply operations
        error_message = str(error)
        if "drift" in error_message.lower():
            error_class = ErrorClass.HUMAN_REQUIRED
        elif "permission" in error_message.lower() or "access" in error_message.lower():
            error_class = ErrorClass.HUMAN_REQUIRED
        elif "quota" in error_message.lower() or "limit" in error_message.lower():
            error_class = ErrorClass.HUMAN_REQUIRED
        return {
            "error_class": error_class,
            "message": f"Apply error: {error_message}",
            "can_retry": False,  # Apply errors generally require human intervention
            "retry_feedback": f"Apply failed: {error_message}",
        }

    async def cleanup(self) -> None:
        """Clean up after apply operation."""
        # For successful applies, we might want to archive the workspace
        # For failed applies, we might want to keep it for debugging
        # In this implementation, we'll keep the workspace for observability
        self.log_message(f"Keeping workspace for observability: {self.workspace_dir}")
