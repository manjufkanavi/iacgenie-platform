"""GitLab provider implementation."""

import logging

from typing import Dict

from datetime import datetime

from uuid import uuid4

from modules.git_cicd.models import GitProvider, GitCommit, CommitStatus

from modules.git_cicd.config import config

from gitlab import Gitlab

from gitlab.exceptions import (
    GitlabAuthenticationError,
    GitlabConnectionError,
    GitlabError,
)

logger = logging.getLogger(__name__)


class GitLabProvider:
    """GitLab provider for Git operations."""

    def __init__(self) -> None:
        self.url = config.GITLAB_URL
        self.token = config.GITLAB_TOKEN
        self.gl: Gitlab | None = None
        # Initialize GitLab client (mock mode if no credentials)
        if self.url and self.token:
            self.gl = Gitlab(self.url, private_token=self.token)

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
        Create a commit in a GitLab repository.
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
            # Parse repo URL
            parts = repo_url.rstrip("/").split("/")
            owner = parts[-2]
            repo_name = parts[-1]
            # Get project (mock mode if no auth)
            if self.gl is None:
                return GitCommit(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.GITLAB,
                    repo_url=repo_url,
                    branch=branch,
                    status=CommitStatus.SUCCESS,
                    message="Mock commit created (no GitLab credentials configured)",
                    created_at=datetime.utcnow(),
                    files=files,
                    commit_sha=str(uuid4()),
                )
            project = self.gl.projects.get(f"{owner}/{repo_name}")
            # Create branch if it doesn't exist
            try:
                project.branches.create(
                    {"branch_name": branch, "ref": project.default_branch}
                )
            except GitlabError as e:
                if (
                    getattr(e, "status_code", 500) != 409
                ):  # 409 means branch already exists
                    logger.error(f"Failed to create branch {branch}: {e}")
                    return GitCommit(
                        id=str(uuid4()),
                        session_id=session_id,
                        provider=GitProvider.GITLAB,
                        repo_url=repo_url,
                        branch=branch,
                        status=CommitStatus.FAILED,
                        message=f"Failed to create branch {branch}: {str(e)}",
                        created_at=datetime.utcnow(),
                        files={},
                    )
                # Branch already exists, continue with commit
            # Create files
            for path, content in files.items():
                try:
                    # Create file
                    project.files.create(
                        {
                            "file_path": path,
                            "branch": branch,
                            "content": content,
                            "commit_message": commit_message,
                            "encoding": "base64",  # GitLab API expects base64-encoded content
                        }
                    )
                except GitlabError as e:
                    logger.error(f"Failed to create file {path}: {e}")
                    return GitCommit(
                        id=str(uuid4()),
                        session_id=session_id,
                        provider=GitProvider.GITLAB,
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
                provider=GitProvider.GITLAB,
                repo_url=repo_url,
                branch=branch,
                status=CommitStatus.SUCCESS,
                message="Commit created successfully",
                created_at=datetime.utcnow(),
                files=files,
            )
        except GitlabAuthenticationError:
            logger.error("GitLab authentication failed")
            return GitCommit(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.GITLAB,
                repo_url=repo_url,
                branch=branch,
                status=CommitStatus.FAILED,
                message="GitLab authentication failed",
                created_at=datetime.utcnow(),
                files={},
            )
        except GitlabConnectionError:
            logger.error("GitLab connection failed")
            return GitCommit(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.GITLAB,
                repo_url=repo_url,
                branch=branch,
                status=CommitStatus.FAILED,
                message="GitLab connection failed",
                created_at=datetime.utcnow(),
                files={},
            )
        except Exception as e:
            logger.error(f"GitLab commit failed: {str(e)}")
            return GitCommit(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.GITLAB,
                repo_url=repo_url,
                branch=branch,
                status=CommitStatus.FAILED,
                message=f"Commit failed: {str(e)}",
                created_at=datetime.utcnow(),
                files={},
            )
