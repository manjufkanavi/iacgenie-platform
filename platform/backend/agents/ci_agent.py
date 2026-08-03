"""CI agent for triggering and monitoring CI pipelines."""

import httpx
import logging
from typing import Dict, Any

from models.iac_state import IaCState
from models.error_classes import ErrorClass
from models.pipeline_phases import PipelinePhase
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# CI provider API base URLs
GITHUB_API_URL = "https://api.github.com"
GITLAB_API_URL = "https://gitlab.com/api/v4"


class CICIAgent(BaseAgent):
    """Agent responsible for triggering and monitoring CI pipelines via provider APIs."""

    def __init__(self, mode: str = "trigger"):
        """
        Initialize the CI agent.
        Args:
            mode: Either 'trigger' to start a CI pipeline or 'monitor' to check its status.
        """
        super().__init__(f"ci_agent_{mode}")
        self.mode = mode
        self.git_repo_url: str = ""
        self.git_branch: str = "main"
        self.ci_provider: str = "github"  # github, gitlab

    async def initialize(self, state: IaCState) -> bool:
        """Initialize the CI agent with CI context from state."""
        await super().initialize(state)
        self.git_repo_url = getattr(state, "git_repo_url", "") or ""
        self.git_branch = getattr(state, "git_branch", "main") or "main"
        self.ci_provider = getattr(state, "ci_provider", "github") or "github"
        return True

    async def execute(self) -> Dict[str, Any]:
        """Execute CI trigger or monitor logic."""
        if not self.git_repo_url:
            return {
                "success": False,
                "error": "No git repository URL configured",
                "error_class": ErrorClass.CLARIFICATION,
                "next_phase": PipelinePhase.ESCALATE,
            }

        if self.mode == "trigger":
            return await self._trigger_ci_pipeline()
        elif self.mode == "monitor":
            return await self._monitor_ci_pipeline()
        else:
            return {
                "success": False,
                "error": f"Unknown CI agent mode: {self.mode}",
                "error_class": ErrorClass.FATAL,
                "next_phase": PipelinePhase.ESCALATE,
            }

    async def _trigger_ci_pipeline(self) -> Dict[str, Any]:
        """Trigger a CI pipeline via the provider API."""
        try:
            self.log_message(
                f"Triggering CI pipeline for {self.ci_provider} repo: {self.git_repo_url}"
            )

            if self.ci_provider == "github":
                return await self._trigger_github_actions()
            elif self.ci_provider == "gitlab":
                return await self._trigger_gitlab_ci()
            else:
                return {
                    "success": False,
                    "error": f"Unsupported CI provider: {self.ci_provider}",
                    "error_class": ErrorClass.CLARIFICATION,
                    "next_phase": PipelinePhase.ESCALATE,
                }
        except Exception as e:
            error_result = await self.handle_error(e)
            return {
                "success": False,
                "error": str(e),
                "error_class": error_result["error_class"],
                "next_phase": PipelinePhase.CI_MONITOR,
            }

    async def _trigger_github_actions(self) -> Dict[str, Any]:
        """Trigger a GitHub Actions workflow run."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{GITHUB_API_URL}/repos/{self.git_repo_url}/actions/runs",
                    json={"ref": self.git_branch},
                    headers={
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                response.raise_for_status()
                data = response.json()
                run_id = data.get("id", "unknown")
                self.log_message(f"GitHub Actions run triggered: {run_id}")
                return {
                    "success": True,
                    "next_phase": PipelinePhase.CI_MONITOR,
                    "result": {
                        "ci_run_id": run_id,
                        "ci_url": data.get("html_url", ""),
                        "message": "GitHub Actions pipeline triggered",
                    },
                }
        except httpx.ReadTimeout:
            return {
                "success": False,
                "error": "GitHub API call timed out",
                "error_class": ErrorClass.RETRYABLE,
                "next_phase": PipelinePhase.CI_MONITOR,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to trigger GitHub Actions: {str(e)}",
                "error_class": ErrorClass.HUMAN_REQUIRED,
                "next_phase": PipelinePhase.CI_MONITOR,
            }

    async def _trigger_gitlab_ci(self) -> Dict[str, Any]:
        """Trigger a GitLab CI pipeline."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{GITLAB_API_URL}/projects/{self.git_repo_url}/pipeline",
                    json={"ref": self.git_branch},
                    headers={
                        "PRIVATE-TOKEN": self._get_gitlab_token(),
                    },
                )
                response.raise_for_status()
                data = response.json()
                pipeline_id = data.get("id", "unknown")
                self.log_message(f"GitLab CI pipeline triggered: {pipeline_id}")
                return {
                    "success": True,
                    "next_phase": PipelinePhase.CI_MONITOR,
                    "result": {
                        "ci_run_id": pipeline_id,
                        "ci_url": data.get("web_url", ""),
                        "message": "GitLab CI pipeline triggered",
                    },
                }
        except httpx.ReadTimeout:
            return {
                "success": False,
                "error": "GitLab API call timed out",
                "error_class": ErrorClass.RETRYABLE,
                "next_phase": PipelinePhase.CI_MONITOR,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to trigger GitLab CI: {str(e)}",
                "error_class": ErrorClass.HUMAN_REQUIRED,
                "next_phase": PipelinePhase.CI_MONITOR,
            }

    async def _monitor_ci_pipeline(self) -> Dict[str, Any]:
        """Monitor CI pipeline status."""
        try:
            if not hasattr(self.state, "ci_run_id") or not self.state.ci_run_id:  # type: ignore[union-attr]
                return {
                    "success": False,
                    "error": "No CI run ID available for monitoring",
                    "error_class": ErrorClass.CLARIFICATION,
                    "next_phase": PipelinePhase.ESCALATE,
                }

            if self.ci_provider == "github":
                return await self._monitor_github_actions()
            elif self.ci_provider == "gitlab":
                return await self._monitor_gitlab_ci()
            else:
                return {
                    "success": False,
                    "error": f"Unsupported CI provider: {self.ci_provider}",
                    "error_class": ErrorClass.CLARIFICATION,
                    "next_phase": PipelinePhase.ESCALATE,
                }
        except Exception as e:
            error_result = await self.handle_error(e)
            return {
                "success": False,
                "error": str(e),
                "error_class": error_result["error_class"],
                "next_phase": PipelinePhase.ESCALATE,
            }

    async def _monitor_github_actions(self) -> Dict[str, Any]:
        """Check GitHub Actions workflow run status."""
        try:
            run_id = self.state.ci_run_id  # type: ignore[union-attr]
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{GITHUB_API_URL}/repos/{self.git_repo_url}/actions/runs/{run_id}",
                    headers={
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                response.raise_for_status()
                data = response.json()
                conclusion = data.get("conclusion")

                if conclusion == "success":
                    self.log_message(f"GitHub Actions run {run_id} succeeded")
                    return {
                        "success": True,
                        "next_phase": PipelinePhase.COMPLETE,
                        "result": {"message": "CI pipeline passed"},
                    }
                elif conclusion in ("failure", "cancelled", "skipped", "timed_out"):
                    self.log_message(
                        f"GitHub Actions run {run_id} failed: {conclusion}", "warning"
                    )
                    return {
                        "success": False,
                        "error": f"CI pipeline failed: {conclusion}",
                        "error_class": ErrorClass.CLARIFICATION,
                        "next_phase": PipelinePhase.ESCALATE,
                    }
                # Still running
                self.log_message(
                    f"GitHub Actions run {run_id} in progress: {data.get('status')}"
                )
                return {
                    "success": False,
                    "error": f"CI still running: {conclusion}",
                    "error_class": ErrorClass.RETRYABLE,
                    "next_phase": PipelinePhase.CI_MONITOR,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to monitor GitHub Actions: {str(e)}",
                "error_class": ErrorClass.RETRYABLE,
                "next_phase": PipelinePhase.CI_MONITOR,
            }

    async def _monitor_gitlab_ci(self) -> Dict[str, Any]:
        """Check GitLab CI pipeline status."""
        try:
            pipeline_id = self.state.ci_run_id  # type: ignore[union-attr]
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{GITLAB_API_URL}/projects/{self.git_repo_url}/pipelines",
                    params={"per_page": 1, "page": 1},
                    headers={"PRIVATE-TOKEN": self._get_gitlab_token()},
                )
                response.raise_for_status()
                pipelines = response.json()
                if not pipelines:
                    return {
                        "success": False,
                        "error": "No pipeline found",
                        "error_class": ErrorClass.CLARIFICATION,
                        "next_phase": PipelinePhase.ESCALATE,
                    }
                latest = pipelines[0]
                status = latest.get("status")

                if status == "success":
                    self.log_message(f"GitLab CI pipeline {pipeline_id} succeeded")
                    return {
                        "success": True,
                        "next_phase": PipelinePhase.COMPLETE,
                        "result": {"message": "CI pipeline passed"},
                    }
                elif status in ("failed", "canceled", "skipped"):
                    self.log_message(
                        f"GitLab CI pipeline {pipeline_id} failed: {status}", "warning"
                    )
                    return {
                        "success": False,
                        "error": f"CI pipeline failed: {status}",
                        "error_class": ErrorClass.CLARIFICATION,
                        "next_phase": PipelinePhase.ESCALATE,
                    }
                # Still running
                self.log_message(
                    f"GitLab CI pipeline {pipeline_id} in progress: {status}"
                )
                return {
                    "success": False,
                    "error": f"CI still running: {status}",
                    "error_class": ErrorClass.RETRYABLE,
                    "next_phase": PipelinePhase.CI_MONITOR,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to monitor GitLab CI: {str(e)}",
                "error_class": ErrorClass.RETRYABLE,
                "next_phase": PipelinePhase.CI_MONITOR,
            }

    def _get_gitlab_token(self) -> str:
        """Get the GitLab API token from state or environment."""
        import os

        if self.state and hasattr(self.state, "ci_inputs"):
            return self.state.ci_inputs.get("gitlab_token", "")
        return os.environ.get("GITLAB_TOKEN", "")

    async def cleanup(self) -> None:
        """No cleanup needed for CI operations."""
        pass

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle CI-specific errors."""
        error_class = self.classify_error(error)
        error_message = str(error)
        if (
            "permission" in error_message.lower()
            or "authentication" in error_message.lower()
        ):
            error_class = ErrorClass.HUMAN_REQUIRED
        elif (
            "timeout" in error_message.lower() or "connection" in error_message.lower()
        ):
            error_class = ErrorClass.RETRYABLE
        return {
            "error_class": error_class,
            "message": f"CI operation error: {error_message}",
            "can_retry": error_class == ErrorClass.RETRYABLE,
            "retry_feedback": f"CI operation failed: {error_message}",
        }
