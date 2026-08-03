"""GitHub Actions provider for CI/CD operations."""

import logging

from typing import Dict, Any, Optional

from datetime import datetime

from uuid import uuid4

from modules.git_cicd.models import GitProvider, CIRun

from .base import BaseCICDProvider

from modules.git_cicd.config import config

import requests

from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class GitHubActionsProvider(BaseCICDProvider):
    """GitHub Actions provider for CI/CD operations."""

    def __init__(self) -> None:
        self.app_id = config.GITHUB_APP_ID
        self.private_key = config.GITHUB_PRIVATE_KEY
        self.installation_id = config.GITHUB_INSTALLATION_ID
        # Mock mode if no credentials
        self.auth = None
        if self.app_id and self.private_key:
            self.auth = HTTPBasicAuth(self.app_id, self.private_key)

    async def trigger_workflow(
        self,
        session_id: str,
        repo_url: str,
        commit_sha: str,
        workflow_file: str,
        inputs: Optional[Dict[str, Any]] = None,
        idempotency_key: str | None = None,
    ) -> CIRun:
        """
        Trigger a GitHub Actions workflow.
        """
        logger.info(
            "Triggering workflow",
            extra={
                "session_id": session_id,
                "repo_url": repo_url,
                "workflow_file": workflow_file,
                "commit_sha": commit_sha,
            },
        )
        try:
            # Mock mode if no credentials
            if self.auth is None:
                return CIRun(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.GITHUB,
                    repo_url=repo_url,
                    run_id=str(uuid4()),
                    status="in_progress",
                    workflow_file=workflow_file,
                    started_at=datetime.utcnow(),
                    logs_url=None,
                    completed_at=datetime.utcnow(),
                )
            # Parse repo URL
            parts = repo_url.rstrip("/").split("/")
            owner = parts[-2]
            repo_name = parts[-1]
            # Get repository
            response = requests.get(
                f"https://api.github.com/repos/{owner}/{repo_name}", auth=self.auth
            )
            if response.status_code != 200:
                logger.error(
                    f"Failed to get repository info: {response.status_code} - {response.text}"
                )
                return CIRun(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.GITHUB,
                    repo_url=repo_url,
                    run_id="",
                    status="failed",
                    workflow_file=workflow_file,
                    started_at=datetime.utcnow(),
                    logs_url=None,
                )
            # Get the workflow file
            response = requests.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/contents/{workflow_file}",
                auth=self.auth,
            )
            if response.status_code != 200:
                logger.error(
                    f"Failed to get workflow file: {response.status_code} - {response.text}"
                )
                return CIRun(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.GITHUB,
                    repo_url=repo_url,
                    run_id="",
                    status="failed",
                    workflow_file=workflow_file,
                    started_at=datetime.utcnow(),
                    logs_url=None,
                )
            # Trigger workflow
            response = requests.post(
                (
                    f"https://api.github.com/repos/{owner}/{repo_name}"
                    f"/actions/workflows/{workflow_file.split('/')[-1]}/dispatches"
                ),
                auth=self.auth,
                json={"ref": commit_sha, "inputs": inputs or {}},
            )
            if response.status_code != 204:
                logger.error(
                    f"Failed to trigger workflow: {response.status_code} - {response.text}"
                )
                return CIRun(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.GITHUB,
                    repo_url=repo_url,
                    run_id="",
                    status="failed",
                    workflow_file=workflow_file,
                    started_at=datetime.utcnow(),
                    logs_url=None,
                )
            return CIRun(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.GITHUB,
                repo_url=repo_url,
                run_id=str(uuid4()),
                status="in_progress",
                workflow_file=workflow_file,
                started_at=datetime.utcnow(),
                logs_url=f"https://github.com/{owner}/{repo_name}/actions/runs/{response.json()['id']}",
            )
        except Exception as e:
            logger.error(f"GitHub Actions trigger failed: {str(e)}")
            return CIRun(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.GITHUB,
                repo_url=repo_url,
                run_id="",
                status="failed",
                workflow_file=workflow_file,
                started_at=datetime.utcnow(),
                logs_url=None,
            )
