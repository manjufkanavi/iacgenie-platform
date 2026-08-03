"""Base class for CI/CD providers."""

from abc import ABC, abstractmethod

from typing import Dict, Any, Optional

from modules.git_cicd.models import CIRun


class BaseCICDProvider(ABC):
    """Abstract base class for CI/CD providers."""

    @abstractmethod
    async def trigger_workflow(
        self,
        session_id: str,
        repo_url: str,
        commit_sha: str,
        workflow_file: str,
        inputs: Optional[Dict[str, Any]] = None,
        idempotency_key: str | None = None,
    ) -> CIRun:
        """Trigger a CI/CD workflow."""
        pass
