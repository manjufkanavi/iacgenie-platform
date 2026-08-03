import re

from typing import Dict, Any, List

from models.iac_state import IaCState

from models.error_classes import ErrorClass

from models.pipeline_phases import PipelinePhase

from .base_agent import BaseAgent

import logging

logger = logging.getLogger(__name__)


class StaticAnalysisAgent(BaseAgent):
    """Agent responsible for performing static analysis on generated HCL code."""

    def __init__(self) -> None:
        super().__init__("static_analysis_agent")
        self.hard_violations: List[str] = []
        self.soft_violations: List[str] = []

    async def initialize(self, state: IaCState) -> bool:
        """Initialize the static analysis agent."""
        await super().initialize(state)
        self.hard_violations = []  # noqa: E501
        self.soft_violations = []  # noqa: E501
        return True

    async def execute(self) -> Dict[str, Any]:
        """
        Execute the static analysis agent logic.
        Returns:
            Dictionary with execution results including:
            - success: bool
            - violations: list of found violations
            - next_phase: next pipeline phase
            - error: optional error details
        """
        try:
            if self.state is None or not self.state.hcl_code:
                error_msg = "No HCL code available for analysis"
                self.log_message(error_msg, "error")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_class": ErrorClass.FATAL,
                    "next_phase": PipelinePhase.ESCALATE,
                }
            # Perform static analysis
            await self._perform_static_analysis()
            # Check for hard violations (immediate failures)
            if self.hard_violations:
                error_details = "\n".join(self.hard_violations)
                self.log_message(f"Hard violations found: {error_details}", "error")
                # Store violations in state for observability
                if self.state is not None:
                    self.state.command_outputs["static_analysis"] = {  # type: ignore[assignment]
                        "hard_violations": self.hard_violations,
                        "soft_violations": self.soft_violations,
                    }
                return {
                    "success": False,
                    "error": f"Hard violations found: {error_details}",
                    "error_class": ErrorClass.FATAL,
                    "next_phase": PipelinePhase.ESCALATE,
                    "violations": {
                        "hard": self.hard_violations,
                        "soft": self.soft_violations,
                    },
                }
            # Check for soft violations (warnings)
            if self.soft_violations:
                warning_details = "\n".join(self.soft_violations)
                self.log_message(f"Soft violations found: {warning_details}", "warning")
                # Store violations in state for observability
                if self.state is not None:
                    self.state.command_outputs["static_analysis"] = {  # type: ignore[assignment]
                        "hard_violations": [],
                        "soft_violations": self.soft_violations,
                    }
                # Continue to next phase but with warnings
                return {
                    "success": True,
                    "next_phase": PipelinePhase.INIT,
                    "warnings": self.soft_violations,
                    "violations": {"hard": [], "soft": self.soft_violations},
                }
            self.log_message(
                "Static analysis completed successfully - no violations found"
            )
            return {
                "success": True,
                "next_phase": PipelinePhase.INIT,
                "result": {"message": "Static analysis passed"},
            }
        except Exception as e:
            error_result = await self.handle_error(e)
            return {
                "success": False,
                "error": str(e),
                "error_class": error_result["error_class"],
                "next_phase": PipelinePhase.ESCALATE,
            }

    async def _perform_static_analysis(self) -> None:
        """Perform comprehensive static analysis on HCL code."""
        assert self.state is not None
        hcl_code = self.state.hcl_code
        if hcl_code is None:
            return
        # Run hard-coded security rules
        await self._run_security_rules(hcl_code)
        # Run LLM-based code review (simulated)
        await self._run_llm_review(hcl_code)

    async def _run_security_rules(self, hcl_code: str) -> None:
        """Run hard-coded security rules that result in immediate failures."""
        self.hard_violations = []
        self.soft_violations = []
        # Rule 1: Check for wildcard IAM actions
        if re.search(r"[\s\"]\*[\s\"]", hcl_code, re.IGNORECASE):
            self.hard_violations.append(
                "SECURITY: Wildcard (*) found in IAM policy - this is not allowed"
            )
        # Rule 2: Check for public S3 buckets
        if re.search(r'acl\s*=\s*["\']public-read["\']', hcl_code, re.IGNORECASE):
            self.hard_violations.append(
                "SECURITY: Public S3 bucket ACL found - this is not allowed"
            )
        # Rule 3: Check for unencrypted EBS volumes
        if re.search(r'resource\s+"aws_ebs_volume"\s+', hcl_code) and not re.search(
            r"encrypted\s*=\s*true", hcl_code, re.IGNORECASE
        ):
            self.hard_violations.append(
                "SECURITY: Unencrypted EBS volume detected - encryption is required"
            )
        # Rule 4: Check for missing tags (soft violation)
        if not re.search(r"tags\s*=", hcl_code):
            self.soft_violations.append(
                "BEST_PRACTICE: No tags found - consider adding resource tags"
            )
        # Rule 5: Check for hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']*["\']',
            r'secret\s*=\s*["\'][^"\']*["\']',
            r'access_key\s*=\s*["\'][^"\']*["\']',
            r'secret_key\s*=\s*["\'][^"\']*["\']',
        ]
        for pattern in secret_patterns:
            if re.search(pattern, hcl_code, re.IGNORECASE):
                self.hard_violations.append(
                    "SECURITY: Potential hardcoded secret detected"
                )
        # Rule 6: Check for missing version constraints
        if not re.search(r"required_version", hcl_code):
            self.soft_violations.append(
                "BEST_PRACTICE: No Terraform version constraint specified"
            )

    async def _run_llm_review(self, hcl_code: str) -> None:
        """Run LLM-based code review (simulated)."""
        # In a real implementation, this would call an LLM with:
        # - System prompt from reviewer_system.txt
        # - HCL code
        # - Refined specification for context
        # For simulation, we'll add some common review findings
        review_findings = self._simulate_llm_review()
        for finding in review_findings:
            if finding["severity"] == "CRITICAL":
                self.hard_violations.append(f"LLM_REVIEW: {finding['message']}")
            else:
                self.soft_violations.append(f"LLM_REVIEW: {finding['message']}")

    def _simulate_llm_review(self) -> List[Dict[str, str]]:
        """Simulate LLM-based code review findings."""
        findings: List[Dict[str, str]] = []
        assert self.state is not None
        hcl_code_raw = self.state.hcl_code
        if hcl_code_raw is None:
            return findings
        hcl_code = hcl_code_raw.lower()
        # Check for common anti-patterns
        if "t3.micro" in hcl_code:
            findings.append(
                {
                    "severity": "MEDIUM",
                    "message": "Consider using a more appropriate instance type for production workloads",
                }
            )
        if "us-west-2" in hcl_code and "region" in hcl_code:
            findings.append(
                {
                    "severity": "LOW",
                    "message": "Consider specifying multiple regions for high availability",
                }
            )
        if len(hcl_code.split("\n")) < 20:
            findings.append(
                {
                    "severity": "LOW",
                    "message": "Configuration is very minimal - ensure all required resources are included",
                }
            )
        # Add a critical finding if we detect potential resource conflicts
        if hcl_code.count("resource") > 1:
            findings.append(
                {
                    "severity": "MEDIUM",
                    "message": "Multiple resources detected - ensure proper dependencies are configured",
                }
            )
        return findings

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors specific to the static analysis agent."""
        error_class = self.classify_error(error)
        # Custom error handling for static analysis
        error_message = str(error)
        if "security" in error_message.lower():
            error_class = ErrorClass.FATAL
        elif "review" in error_message.lower():
            error_class = ErrorClass.CLARIFICATION
        return {
            "error_class": error_class,
            "message": f"Static analysis error: {error_message}",
            "can_retry": error_class == ErrorClass.RETRYABLE,
            "retry_feedback": f"Analysis error: {error_message}",
        }
