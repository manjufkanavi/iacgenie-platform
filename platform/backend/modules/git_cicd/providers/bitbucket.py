"""Bitbucket provider implementation."""

import logging

from typing import Dict

from datetime import datetime

from uuid import uuid4

from modules.git_cicd.models import GitProvider, GitCommit, CommitStatus

from modules.git_cicd.config import config

import requests

from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class BitbucketProvider:
    """Bitbucket provider for Git operations."""

    def __init__(self) -> None:
        self.url = config.BITBUCKET_URL
        self.username = config.BITBUCKET_USERNAME
        self.app_password = config.BITBUCKET_APP_PASSWORD
        self.base_url: str | None = None
        # Initialize Bitbucket API client (mock mode if no credentials)
        if self.url and self.username and self.app_password:
            self.base_url = f"{self.url}/rest/api/1.0"

    async def create_commit(
        self,
        session_id: str,
        repo_url: str,
        branch: str,
        files: Dict[str, str],
        commit_message: str,
        idempotency_key: str,
    ) -> GitCommit:
        """
        Create a commit in a Bitbucket repository.
        """
        logger.info(
            "Creating commit",
            extra={
                "session_id": session_id,
                "repo_url": repo_url,
                "branch": branch,
                "commit_message": commit_message,
            },
        )
        try:
            # Mock mode if no credentials
            if self.base_url is None:
                return GitCommit(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.BITBUCKET,
                    repo_url=repo_url,
                    branch=branch,
                    status=CommitStatus.SUCCESS,
                    message="Mock commit created (no Bitbucket credentials configured)",
                    created_at=datetime.utcnow(),
                    files=files,
                    commit_sha=str(uuid4()),
                )
            # Parse repo URL
            parts = repo_url.rstrip("/").split("/")
            owner = parts[-2]
            repo_name = parts[-1]
            # Get repository information
            response = requests.get(
                f"{self.base_url}/projects/{owner}/repos/{repo_name}",
                auth=HTTPBasicAuth(self.username, self.app_password),
            )
            if response.status_code != 200:
                logger.error(
                    f"Failed to get repository info: {response.status_code} - {response.text}"
                )
                return GitCommit(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.BITBUCKET,
                    repo_url=repo_url,
                    branch=branch,
                    status=CommitStatus.FAILED,
                    message=f"Failed to get repository info: {response.status_code} - {response.text}",
                    created_at=datetime.utcnow(),
                    files={},
                )
            # Get branch information
            response = requests.get(
                f"{self.base_url}/projects/{owner}/repos/{repo_name}/branches",
                auth=HTTPBasicAuth(self.username, self.app_password),
            )
            if response.status_code != 200:
                logger.error(
                    f"Failed to get branch list: {response.status_code} - {response.text}"
                )
                return GitCommit(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.BITBUCKET,
                    repo_url=repo_url,
                    branch=branch,
                    status=CommitStatus.FAILED,
                    message=f"Failed to get branch list: {response.status_code} - {response.text}",
                    created_at=datetime.utcnow(),
                    files={},
                )
            # Check if branch exists
            branch_exists = False
            for branch_data in response.json()["values"]:
                if branch_data["displayId"] == branch:
                    branch_exists = True
                    break
            # Create branch if it doesn't exist
            if not branch_exists:
                try:
                    # Create branch from default branch
                    default_branch = None
                    for branch_data in response.json()["values"]:
                        if (
                            branch_data["type"] == "BRANCH"
                            and branch_data["name"] == "main"
                        ):
                            default_branch = branch_data["name"]
                            break
                        elif (
                            branch_data["type"] == "BRANCH"
                            and branch_data["name"] == "master"
                        ):
                            default_branch = branch_data["name"]
                            break
                    if not default_branch:
                        logger.error("Default branch not found in repository")
                        return GitCommit(
                            id=str(uuid4()),
                            session_id=session_id,
                            provider=GitProvider.BITBUCKET,
                            repo_url=repo_url,
                            branch=branch,
                            status=CommitStatus.FAILED,
                            message="Default branch not found in repository",
                            created_at=datetime.utcnow(),
                            files={},
                        )
                    # Create new branch
                    response = requests.post(
                        f"{self.base_url}/projects/{owner}/repos/{repo_name}/branches",
                        auth=HTTPBasicAuth(self.username, self.app_password),
                        json={"name": branch, "from": default_branch},
                    )
                    if response.status_code != 201:
                        logger.error(
                            f"Failed to create branch {branch}: {response.status_code} - {response.text}"
                        )
                        return GitCommit(
                            id=str(uuid4()),
                            session_id=session_id,
                            provider=GitProvider.BITBUCKET,
                            repo_url=repo_url,
                            branch=branch,
                            status=CommitStatus.FAILED,
                            message=f"Failed to create branch {branch}: {response.status_code} - {response.text}",
                            created_at=datetime.utcnow(),
                            files={},
                        )
                except Exception as e:
                    logger.error(f"Failed to create branch {branch}: {str(e)}")
                    return GitCommit(
                        id=str(uuid4()),
                        session_id=session_id,
                        provider=GitProvider.BITBUCKET,
                        repo_url=repo_url,
                        branch=branch,
                        status=CommitStatus.FAILED,
                        message=f"Failed to create branch {branch}: {str(e)}",
                        created_at=datetime.utcnow(),
                        files={},
                    )
            # Create files
            for path, content in files.items():
                try:
                    # Get repository's default branch
                    response = requests.get(
                        f"{self.base_url}/projects/{owner}/repos/{repo_name}/default-branch",
                        auth=HTTPBasicAuth(self.username, self.app_password),
                    )
                    if response.status_code != 200:
                        logger.error(
                            f"Failed to get default branch: {response.status_code} - {response.text}"
                        )
                        return GitCommit(
                            id=str(uuid4()),
                            session_id=session_id,
                            provider=GitProvider.BITBUCKET,
                            repo_url=repo_url,
                            branch=branch,
                            status=CommitStatus.FAILED,
                            message=f"Failed to get default branch: {response.status_code} - {response.text}",
                            created_at=datetime.utcnow(),
                            files={},
                        )
                    # Get the current commit SHA for the default branch
                    response = requests.get(
                        f"{self.base_url}/projects/{owner}/repos/{repo_name}/commits/{response.json()['displayId']}",
                        auth=HTTPBasicAuth(self.username, self.app_password),
                    )
                    if response.status_code != 200:
                        logger.error(
                            f"Failed to get commit SHA: {response.status_code} - {response.text}"
                        )
                        return GitCommit(
                            id=str(uuid4()),
                            session_id=session_id,
                            provider=GitProvider.BITBUCKET,
                            repo_url=repo_url,
                            branch=branch,
                            status=CommitStatus.FAILED,
                            message=f"Failed to get commit SHA: {response.status_code} - {response.text}",
                            created_at=datetime.utcnow(),
                            files={},
                        )
                    # Create file
                    response = requests.put(
                        f"{self.base_url}/projects/{owner}/repos/{repo_name}/browse/{path}?branch={branch}",
                        auth=HTTPBasicAuth(self.username, self.app_password),
                        json={
                            "message": commit_message,
                            "content": content,
                            "encoding": "utf-8",
                        },
                    )
                    if response.status_code != 201:
                        logger.error(
                            f"Failed to create file {path}: {response.status_code} - {response.text}"
                        )
                        return GitCommit(
                            id=str(uuid4()),
                            session_id=session_id,
                            provider=GitProvider.BITBUCKET,
                            repo_url=repo_url,
                            branch=branch,
                            status=CommitStatus.FAILED,
                            message=f"Failed to create file {path}: {response.status_code} - {response.text}",
                            created_at=datetime.utcnow(),
                            files={},
                        )
                except Exception as e:
                    logger.error(f"Failed to create file {path}: {str(e)}")
                    return GitCommit(
                        id=str(uuid4()),
                        session_id=session_id,
                        provider=GitProvider.BITBUCKET,
                        repo_url=repo_url,
                        branch=branch,
                        status=CommitStatus.FAILED,
                        message=f"Failed to create file {path}: {str(e)}",
                        created_at=datetime.utcnow(),
                        files={},
                    )
            return GitCommit(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.BITBUCKET,
                repo_url=repo_url,
                branch=branch,
                status=CommitStatus.SUCCESS,
                message="Commit created successfully",
                created_at=datetime.utcnow(),
                files=files,
            )
        except Exception as e:
            logger.error(f"Bitbucket commit failed: {str(e)}")
            return GitCommit(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.BITBUCKET,
                repo_url=repo_url,
                branch=branch,
                status=CommitStatus.FAILED,
                message=f"Commit failed: {str(e)}",
                created_at=datetime.utcnow(),
                files={},
            )
