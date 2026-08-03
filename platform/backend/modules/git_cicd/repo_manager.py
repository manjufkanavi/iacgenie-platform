"""Repository manager for Git operations."""

import logging

from typing import Any, Dict

from .models import GitProvider, GitCommit

from .providers.github import GitHubProvider

from .providers.gitlab import GitLabProvider

from .providers.bitbucket import BitbucketProvider

logger = logging.getLogger(__name__)


class RepoManager:
    """Manager for Git repository operations."""

    def __init__(self, adapter: Any = None) -> None:
        self.providers = {
            GitProvider.GITHUB: GitHubProvider(),
            GitProvider.GITLAB: GitLabProvider(),
            GitProvider.BITBUCKET: BitbucketProvider(),
        }

    async def commit_code(
        self,
        session_id: str,
        repo_config_id: str,
        branch: str,
        files: Dict[str, str],
        commit_message: str,
        idempotency_key: str,
    ) -> GitCommit:
        """
        Commit code to a repository using the appropriate provider.
        """
        # Get repo config (would query from database)
        repo_url = "https://github.com/user/repo"  # Placeholder
        provider = GitProvider.GITHUB
        logger.info(
            "Committing code to repository",
            extra={
                "session_id": session_id,
                "repo_config_id": repo_config_id,
                "branch": branch,
                "commit_message": commit_message,
            },
        )
        # Route to appropriate provider
        if provider not in self.providers:
            raise ValueError(f"Unsupported Git provider: {provider}")
        provider_instance = self.providers[provider]
        return await provider_instance.create_commit(  # type: ignore[attr-defined]
            session_id=session_id,
            repo_url=repo_url,
            branch=branch,
            files=files,
            commit_message=commit_message,
            idempotency_key=idempotency_key,
        )
