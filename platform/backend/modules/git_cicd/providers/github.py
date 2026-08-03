"""GitHub provider implementation."""

import logging

from typing import Dict, Optional

from datetime import datetime

from uuid import uuid4

from modules.git_cicd.models import GitProvider, GitCommit, CommitStatus

from modules.git_cicd.config import config

import github

from github import Github, Auth

logger = logging.getLogger(__name__)


class GitHubProvider:
    """GitHub provider for Git operations."""

    def __init__(self) -> None:
        self.app_id: Optional[str] = config.GITHUB_APP_ID
        self.private_key: Optional[str] = config.GITHUB_PRIVATE_KEY
        self.installation_id: Optional[str] = config.GITHUB_INSTALLATION_ID
        # Authenticate with GitHub App
        if self.app_id and self.private_key:
            self.github: Optional[Github] = Github(
                auth=Auth.AppAuth(
                    app_id=self.app_id,
                    private_key=self.private_key,
                ),
            )
        else:
            # Mock mode - no authentication
            self.github = None

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
        Create a commit in a GitHub repository.
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
            # Get repository (mock mode if no auth)
            if self.github is None:
                return GitCommit(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.GITHUB,
                    repo_url=repo_url,
                    branch=branch,
                    status=CommitStatus.SUCCESS,
                    message="Mock commit created (no GitHub credentials configured)",
                    created_at=datetime.utcnow(),
                    files=files,
                    commit_sha=str(uuid4()),
                )
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            # Create branch if it doesn't exist
            try:
                default_branch = repo.default_branch
                repo.create_git_ref(f"refs/heads/{branch}", default_branch)
            except github.GithubException:
                pass  # Branch may already exist
            # Create blobs for all files
            tree_elements = []
            blob_shas = {}
            for path, content in files.items():
                try:
                    # Create blob (PyGithub expects str content with encoding)
                    blob = repo.create_git_blob(content=content, encoding="utf-8")
                    blob_shas[path] = blob.sha
                    tree_elements.append(
                        github.InputGitTreeElement(
                            path=path, mode="100644", type="blob", sha=blob.sha
                        )
                    )
                except github.GithubException as e:
                    logger.error(f"Failed to create blob {path}: {e}")
                    return GitCommit(
                        id=str(uuid4()),
                        session_id=session_id,
                        provider=GitProvider.GITHUB,
                        repo_url=repo_url,
                        branch=branch,
                        status=CommitStatus.FAILED,
                        message=f"Failed to create blob {path}: {str(e)}",
                        created_at=datetime.utcnow(),
                        files={},
                    )
            # Create tree
            try:
                git_tree = repo.create_git_tree(tree_elements)
            except github.GithubException as e:
                logger.error(f"Failed to create tree: {e}")
                return GitCommit(
                    id=str(uuid4()),
                    session_id=session_id,
                    provider=GitProvider.GITHUB,
                    repo_url=repo_url,
                    branch=branch,
                    status=CommitStatus.FAILED,
                    message=f"Failed to create tree: {str(e)}",
                    created_at=datetime.utcnow(),
                    files={},
                )
            # Create commit (parents required; use default branch HEAD if available)
            try:
                default_ref = repo.get_git_ref(f"heads/{default_branch}")
                parents = [repo.get_git_commit(default_ref.object.sha)]
            except github.GithubException:
                parents = []
            commit = repo.create_git_commit(
                message=commit_message, tree=git_tree, parents=parents
            )
            return GitCommit(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.GITHUB,
                repo_url=repo_url,
                branch=branch,
                commit_sha=commit.sha,
                status=CommitStatus.SUCCESS,
                message="Commit created successfully",
                created_at=datetime.utcnow(),
                files=files,
            )
        except Exception as e:
            logger.error(f"GitHub commit failed: {str(e)}")
            return GitCommit(
                id=str(uuid4()),
                session_id=session_id,
                provider=GitProvider.GITHUB,
                repo_url=repo_url,
                branch=branch,
                status=CommitStatus.FAILED,
                message=f"Commit failed: {str(e)}",
                created_at=datetime.utcnow(),
                files={},
            )
