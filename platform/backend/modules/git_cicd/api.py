"""Internal API for Git & CI/CD integration."""

import logging

from fastapi import FastAPI, Depends, Request


from typing import Dict, Any, Optional

from .models import GitProvider

from .repo_manager import RepoManager

from .webhook_handler import WebhookHandler

from .cicd_providers.github_actions import GitHubActionsProvider


from db.db_provider import db_provider

logger = logging.getLogger(__name__)


def get_user_id(request: Request) -> str:
    """Extract user ID from request."""
    return request.headers.get("x-user-id", "anonymous")


router = FastAPI(prefix="/internal/git", tags=["Git"])

app = FastAPI()

# Initialize components

repo_manager = RepoManager(db_provider.adapter)

webhook_handler = WebhookHandler()


@router.post("/commit")
async def commit_code(
    session_id: str,
    repo_config_id: str,
    branch: str,
    files: Dict[str, str],
    commit_message: str,
    idempotency_key: str,
    request: Request,
    user_id: str = Depends(get_user_id),
) -> dict:
    """Commit code to a Git repository."""
    commit = await repo_manager.commit_code(
        session_id=session_id,
        repo_config_id=repo_config_id,
        branch=branch,
        files=files,
        commit_message=commit_message,
        idempotency_key=idempotency_key,
    )
    return {"commit": commit.to_dict()}


@router.post("/cicd/trigger")
async def trigger_workflow(
    session_id: str,
    repo_config_id: str,
    commit_sha: str,
    workflow_file: str,
    request: Request,
    inputs: Optional[Dict[str, Any]] = None,
    idempotency_key: str = "",
    user_id: str = Depends(get_user_id),
) -> dict:
    """Trigger CI/CD workflow."""
    # Get repo config (would query from database)
    repo_url = "https://github.com/user/repo"  # Placeholder
    provider = GitProvider.GITHUB
    # Route to appropriate CI/CD provider
    if provider == GitProvider.GITHUB:
        cicd_provider = GitHubActionsProvider()
    else:
        raise ValueError(f"Unsupported CI provider: {provider}")
    result = await cicd_provider.trigger_workflow(
        session_id=session_id,
        repo_url=repo_url,
        commit_sha=commit_sha,
        workflow_file=workflow_file,
        inputs=inputs,
        idempotency_key=idempotency_key,
    )
    return {"run": result.to_dict()}


# Health check endpoint


@router.get("/health")
async def health_check():
    """Health check for Git/CI-CD service."""
    return {"status": "healthy", "service": "git_cicd"}
