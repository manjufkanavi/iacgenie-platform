import tempfile

import subprocess

from typing import Dict, Any, Optional

from models.iac_state import IaCState

from models.error_classes import ErrorClass

from models.pipeline_phases import PipelinePhase

from .base_agent import BaseAgent

import logging

logger = logging.getLogger(__name__)


class GeneratorAgent(BaseAgent):
    """Agent responsible for generating HCL code from refined specifications."""

    def __init__(self) -> None:
        super().__init__("generator_agent")
        self.max_retries = 3

    async def initialize(
        self, state: IaCState, model_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Initialize the generator agent."""
        await super().initialize(state)
        self._model_config = model_config
        return True

    async def execute(self) -> Dict[str, Any]:
        """
        Execute the generator agent logic.
        Returns:
            Dictionary with execution results including:
            - success: bool
            - hcl_code: generated HCL code
            - next_phase: next pipeline phase
            - error: optional error details
        """
        try:
            # Check if we already have HCL code and this is not a retry
            if (
                self.state is not None
                and self.state.hcl_code
                and not self.state.retry_feedback
            ):
                self.log_message("HCL code already exists, proceeding to next phase")
                return {
                    "success": True,
                    "next_phase": PipelinePhase.FORMAT,
                    "result": {"message": "Using existing HCL code"},
                }
            # Generate HCL code
            hcl_code = await self._generate_hcl_code()
            if not hcl_code:
                error_msg = "Failed to generate HCL code"
                self.log_message(error_msg, "error")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_class": ErrorClass.FATAL,
                    "next_phase": PipelinePhase.ESCALATE,
                }
            # Store the generated HCL code
            if self.state is not None:
                self.state.hcl_code = hcl_code
            self.log_message("HCL code generated successfully")
            return {
                "success": True,
                "next_phase": PipelinePhase.FORMAT,
                "result": {"hcl_code": hcl_code, "message": "HCL generation completed"},
            }
        except Exception as e:
            error_result = await self.handle_error(e)
            return {
                "success": False,
                "error": str(e),
                "error_class": error_result["error_class"],
                "next_phase": PipelinePhase.ESCALATE,
            }

    async def _generate_hcl_code(self) -> Optional[str]:
        """Generate HCL code from the refined specification."""
        try:
            from services.ai_service import ai_service
            import json

            # Parse the refined spec
            if self.state is None or not self.state.refined_spec:
                raise ValueError(
                    "No refined specification available for HCL generation"
                )

            refined_spec = json.loads(self.state.refined_spec)
            provider = refined_spec.get("provider", "aws")

            prompt = self.state.user_request or ""
            spec_str = json.dumps(refined_spec, indent=2)
            prompt += f"\n\nHere are the established architectural decisions:\n```json\n{spec_str}\n```\n\nPlease strictly follow these preferences."

            model_name = "default"
            model_config = getattr(self, "_model_config", None)
            if model_config:
                model_name = model_config.get("model_name", "default")

            ai_result = await ai_service.generate_infrastructure(
                prompt=prompt,
                provider=provider,
                model_name=model_name,
                model_config_dict=getattr(self, "_model_config", None),
            )

            parsed_files = ai_result.get("files", [])
            hcl_code = ""
            for file_entry in parsed_files:
                if isinstance(file_entry, dict):
                    content = file_entry.get("content", "")
                    if content:
                        hcl_code += content + "\n\n"
                elif isinstance(file_entry, tuple) and len(file_entry) >= 2:
                    content = file_entry[1]
                    if content:
                        hcl_code += content + "\n\n"

            if not hcl_code.strip():
                raise ValueError("No HCL code generated from AI service")

            # Validate the generated HCL syntax
            if not self._validate_hcl_syntax(hcl_code):
                error_msg = "Generated HCL has syntax errors"
                self.log_message(error_msg, "error")
                raise ValueError(error_msg)
            return hcl_code
        except Exception as e:
            self.log_message(f"HCL generation failed: {str(e)}", "error")
            return None

    def _validate_hcl_syntax(self, hcl_code: str) -> bool:
        """Validate HCL syntax using tofu fmt."""
        try:
            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".tf", delete=False) as f:
                f.write(hcl_code)
                temp_file = f.name
            # Try to format with tofu (OpenTofu)
            try:
                result = subprocess.run(
                    ["tofu", "fmt", "-check", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.returncode == 0
            except FileNotFoundError:
                # tofu not available, do basic syntax check
                self.log_message(
                    "tofu binary not found, performing basic syntax check", "warning"
                )
                return self._basic_hcl_syntax_check(hcl_code)
            except subprocess.TimeoutExpired:
                self.log_message("HCL syntax validation timed out", "warning")
                return False
            finally:
                # Clean up temp file
                import os

                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
        except Exception as e:
            self.log_message(f"HCL syntax validation error: {str(e)}", "error")
            return False

    def _basic_hcl_syntax_check(self, hcl_code: str) -> bool:
        """Perform basic HCL syntax checking."""
        # Check for balanced braces
        open_braces = hcl_code.count("{")
        close_braces = hcl_code.count("}")
        if open_braces != close_braces:
            self.log_message(
                f"Unbalanced braces: {open_braces} open, {close_braces} close", "error"
            )
            return False
        # Check for basic structure
        required_elements = ["terraform", "provider", "resource"]
        for element in required_elements:
            if element not in hcl_code.lower():
                self.log_message(f"Missing required element: {element}", "warning")
        return True

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors specific to the generator agent."""
        error_class = self.classify_error(error)
        # Custom error handling for generation
        error_message = str(error)
        if "syntax" in error_message.lower():
            error_class = ErrorClass.CLARIFICATION
        elif "timeout" in error_message.lower():
            error_class = ErrorClass.RETRYABLE
        # Prepare retry feedback if applicable
        retry_feedback = None
        if error_class == ErrorClass.RETRYABLE:
            retry_feedback = (
                f"Generation error: {error_message}. Please correct HCL syntax."
            )
        return {
            "error_class": error_class,
            "message": f"Generation error: {error_message}",
            "can_retry": error_class == ErrorClass.RETRYABLE,
            "retry_feedback": retry_feedback,
        }
