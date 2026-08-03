"""

Git/CI-CD Router

API endpoints for Git operations and CI/CD integration.

Integrates with Keycloak authentication and existing git_repositories router.

"""

import asyncio

import json

import logging

import hashlib

import hmac

from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Header, Request

from pydantic import BaseModel, Field

from src.git_cicd.repo_manager import RepoManager

from src.git_cicd.webhook_handler import WebhookHandler

from src.git_cicd.cicd_providers.github_actions import GitHubActionsProvider

from src.git_cicd.digger_agent import DiggerAgentService, get_digger_service

from src.git_cicd.models import GitOpsRunType

from middleware.auth_middleware import get_user_id

from db.db_provider import db_provider

logger = logging.getLogger(__name__)

# Create router

router = APIRouter(prefix="/api/git", tags=["Git/CI-CD"])

# Global instances

_repo_manager: Optional[RepoManager] = None

_webhook_handler: Optional[WebhookHandler] = None

_github_actions_provider: Optional[GitHubActionsProvider] = None


def get_repo_manager() -> RepoManager:
    """Get the global RepoManager instance."""
    global _repo_manager
    if _repo_manager is None:
        _repo_manager = RepoManager(db_provider.adapter)
    return _repo_manager


def get_webhook_handler() -> WebhookHandler:
    """Get the global WebhookHandler instance."""
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = WebhookHandler()
    return _webhook_handler


def get_github_actions_provider() -> GitHubActionsProvider:
    """Get the global GitHub Actions provider instance."""
    global _github_actions_provider
    if _github_actions_provider is None:
        _github_actions_provider = GitHubActionsProvider()
    return _github_actions_provider


_digger_service: Optional[DiggerAgentService] = None


async def get_digger_agent_service() -> DiggerAgentService:
    """Get the global DiggerAgentService instance."""
    global _digger_service
    if _digger_service is None:
        _digger_service = await get_digger_service(db_provider.adapter)
    return _digger_service


# ============================================================================

# Request Models

# ============================================================================


class CommitCodeRequest(BaseModel):
    """Request to commit code to a Git repository."""

    session_id: str = Field(..., description="Session ID for tracing")
    repo_config_id: str = Field(..., description="Repository configuration ID")
    branch: str = Field("main", description="Branch to commit to")
    files: Dict[str, str] = Field(..., description="Files to commit (path -> content)")
    commit_message: str = Field(..., description="Commit message")
    idempotency_key: str = Field(
        ..., description="Idempotency key to prevent duplicate commits"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TriggerCIRequest(BaseModel):
    """Request to trigger a CI/CD workflow."""

    session_id: str = Field(..., description="Session ID for tracing")
    repo_config_id: str = Field(..., description="Repository configuration ID")
    commit_sha: str = Field(..., description="Commit SHA to trigger workflow for")
    workflow_file: str = Field(..., description="Workflow file name (e.g., deploy.yml)")
    inputs: Optional[Dict[str, Any]] = Field(None, description="Workflow inputs")
    idempotency_key: str = Field(
        ..., description="Idempotency key to prevent duplicate triggers"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WebhookRequest(BaseModel):
    """Request model for webhook validation."""

    x_hub_signature: str = Header(
        ..., alias="X-Hub-Signature", description="GitHub webhook signature"
    )
    x_gitlab_token: Optional[str] = Header(
        None, alias="X-Gitlab-Token", description="GitLab webhook token"
    )
    x_bitbucket_signature: Optional[str] = Header(
        None, alias="X-Hub-Signature", description="Bitbucket webhook signature"
    )


# ============================================================================

# Response Models

# ============================================================================


class CommitResponse(BaseModel):
    """Response for Git commit."""

    commit_id: str = Field(..., description="Commit ID")
    commit_sha: str = Field(..., description="Commit SHA")
    branch: str = Field(..., description="Branch")
    repo_url: str = Field(..., description="Repository URL")
    created_at: str = Field(..., description="Creation timestamp")


class CIRunResponse(BaseModel):
    """Response for CI/CD run."""

    run_id: str = Field(..., description="Run ID")
    workflow_file: str = Field(..., description="Workflow file")
    status: str = Field(..., description="Run status")
    commit_sha: str = Field(..., description="Commit SHA")
    created_at: str = Field(..., description="Creation timestamp")
    run_url: Optional[str] = Field(None, description="Run URL")


class WebhookResponse(BaseModel):
    """Response for webhook processing."""

    success: bool = Field(..., description="Whether webhook was processed successfully")
    message: str = Field(..., description="Status message")
    event_type: Optional[str] = Field(None, description="Type of event received")


# ============================================================================

# GitOps Request/Response Models

# ============================================================================


class PlanRequest(BaseModel):
    """Request to trigger a Digger plan."""

    session_id: str = Field(..., description="Session ID for tracing")
    commit_sha: str = Field("", description="Commit SHA to plan")
    branch: str = Field("main", description="Branch to plan")
    trigger_method: str = Field(
        "manual", description="Trigger method: manual, webhook, scheduled"
    )


class ApplyRequest(BaseModel):
    """Request to trigger a Digger apply."""

    session_id: str = Field(..., description="Session ID for tracing")
    commit_sha: str = Field("", description="Commit SHA to apply")
    branch: str = Field("main", description="Branch to apply")
    trigger_method: str = Field(
        "manual", description="Trigger method: manual, webhook, scheduled"
    )


class GitOpsRunResponse(BaseModel):
    """Response for a GitOps run."""

    run_id: str = Field(..., description="Run ID")
    repo_config_id: str = Field(..., description="Repository config ID")
    run_type: str = Field(..., description="Plan or apply")
    status: str = Field(..., description="Run status")
    commit_sha: str = Field("", description="Commit SHA")
    branch: str = Field("main", description="Branch")
    plan_diff: str = Field("", description="Plan output diff")
    apply_diff: str = Field("", description="Apply output diff")
    triggered_by: str = Field("", description="User who triggered the run")
    trigger_method: str = Field("manual", description="How the run was triggered")
    error_message: Optional[str] = Field(None, description="Error if failed")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    created_at: str = Field(..., description="Creation timestamp")


class ListRunsResponse(BaseModel):
    """Response for listing GitOps runs."""

    runs: list = Field(..., description="List of GitOps run responses")
    total: int = Field(0, description="Total number of runs")


# ============================================================================

# Endpoints

# ============================================================================


@router.post("/commit", response_model=CommitResponse)
async def commit_code(
    request: CommitCodeRequest,
    http_request: Request,
    user_id: str = Depends(get_user_id),
) -> CommitResponse:
    """
    Commit code to a Git repository.
    Args:
        request: Commit request parameters
        http_request: FastAPI request object
        user_id: Authenticated user ID from auth middleware
    Returns:
        CommitResponse with commit details
    Raises:
        HTTPException: If commit fails
    """
    try:
        repo_manager = get_repo_manager()
        # Check for duplicate commits using idempotency key
        # This would be implemented in the repo_manager
        # Commit code
        commit = await repo_manager.commit_code(
            session_id=request.session_id,
            repo_config_id=request.repo_config_id,
            branch=request.branch,
            files=request.files,
            commit_message=request.commit_message,
            idempotency_key=request.idempotency_key,
            user_id=user_id,  # Authenticated user ID replaces X-Tenant-ID
        )
        logger.info(
            "Code committed to repository",
            extra={
                "user_id": user_id,
                "session_id": request.session_id,
                "repo_config_id": request.repo_config_id,
                "branch": request.branch,
                "commit_sha": commit.commit_sha,
            },
        )
        return CommitResponse(
            commit_id=commit.id,
            commit_sha=commit.commit_sha,
            branch=request.branch,
            repo_url=commit.repo_url,
            created_at=commit.created_at.isoformat()
            if hasattr(commit.created_at, "isoformat")
            else str(commit.created_at),
        )
    except Exception as e:
        logger.error(f"Error committing code for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to commit code",
                    "type": "commit_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/cicd/trigger", response_model=CIRunResponse)
async def trigger_workflow(
    request: TriggerCIRequest,
    http_request: Request,
    user_id: str = Depends(get_user_id),
) -> CIRunResponse:
    """
    Trigger a CI/CD workflow.
    Args:
        request: CI trigger request parameters
        http_request: FastAPI request object
        user_id: Authenticated user ID from auth middleware
    Returns:
        CIRunResponse with run details
    Raises:
        HTTPException: If workflow trigger fails
    """
    try:
        github_actions_provider = get_github_actions_provider()
        # Get repository URL from repo config (would query from database)
        repo_url = "https://github.com/user/repo"  # Placeholder
        # Check for duplicate triggers using idempotency key
        # This would be implemented in the provider
        # Trigger workflow
        result = await github_actions_provider.trigger_workflow(
            session_id=request.session_id,
            repo_url=repo_url,
            commit_sha=request.commit_sha,
            workflow_file=request.workflow_file,
            inputs=request.inputs,
            idempotency_key=request.idempotency_key,
            user_id=user_id,  # Authenticated user ID replaces X-Tenant-ID
        )
        logger.info(
            "CI/CD workflow triggered",
            extra={
                "user_id": user_id,
                "session_id": request.session_id,
                "repo_config_id": request.repo_config_id,
                "workflow_file": request.workflow_file,
                "run_id": result.run_id,
            },
        )
        return CIRunResponse(
            run_id=result.run_id,
            workflow_file=request.workflow_file,
            status=result.status,
            commit_sha=request.commit_sha,
            created_at=result.created_at or "",
            run_url=result.run_url,
        )
    except Exception as e:
        logger.error(f"Error triggering CI/CD for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to trigger workflow",
                    "type": "ci_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(
    request: Request,
    x_hub_signature: str = Header(
        ..., alias="X-Hub-Signature", description="GitHub webhook signature"
    ),
    x_gitlab_token: Optional[str] = Header(
        None, alias="X-Gitlab-Token", description="GitLab webhook token"
    ),
    x_bitbucket_signature: Optional[str] = Header(
        None, alias="X-Hub-Signature", description="Bitbucket webhook signature"
    ),
) -> WebhookResponse:
    """
    Handle Git webhook events.
    Args:
        request: FastAPI request object
        x_hub_signature: GitHub webhook signature
        x_gitlab_token: GitLab webhook token
        x_bitbucket_signature: Bitbucket webhook signature
    Returns:
        WebhookResponse with processing status
    Raises:
        HTTPException: If webhook processing fails
    """
    try:
        webhook_handler = get_webhook_handler()
        # Get request body
        body = await request.body()
        # Determine provider based on headers
        if x_hub_signature:
            provider = "github"
            signature = x_hub_signature
            secret = await _get_github_webhook_secret()
        elif x_gitlab_token:
            provider = "gitlab"
            signature = x_gitlab_token
            secret = await _get_gitlab_webhook_secret()
        elif x_bitbucket_signature:
            provider = "bitbucket"
            signature = x_bitbucket_signature
            secret = await _get_bitbucket_webhook_secret()
        else:
            logger.warning("Webhook received without provider signature")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": "Missing provider signature",
                        "type": "validation_error",
                        "code": "missing_signature",
                    }
                },
            )
        # Verify signature
        if not await _verify_webhook_signature(body, signature, secret, provider):
            logger.warning(f"Invalid webhook signature for provider {provider}")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "Invalid webhook signature",
                        "type": "security_error",
                        "code": "invalid_signature",
                    }
                },
            )
        # Process webhook (verifies signature, checks replay, parses payload)
        await webhook_handler.handle_webhook(provider=provider, request=request)
        # Dispatch to Digger if this is a plan-triggering event
        digger_result = await webhook_handler.process_event(provider=provider)

        logger.info(
            "Webhook processed",
            extra={
                "provider": provider,
                "digger_triggered": digger_result.get("digger_triggered", False),
                "run_id": digger_result.get("run_id"),
                "run_type": digger_result.get("run_type"),
            },
        )
        return WebhookResponse(
            success=True,
            message="Webhook processed successfully",
            event_type=json.dumps(digger_result).encode().decode("unicode_escape")
            if digger_result
            else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to process webhook",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


async def _get_github_webhook_secret() -> str:
    """Get GitHub webhook secret from environment or secret store."""
    import os

    return os.getenv("GITHUB_WEBHOOK_SECRET", "")


async def _get_gitlab_webhook_secret() -> str:
    """Get GitLab webhook secret from environment or secret store."""
    import os

    return os.getenv("GITLAB_WEBHOOK_SECRET", "")


async def _get_bitbucket_webhook_secret() -> str:
    """Get Bitbucket webhook secret from environment or secret store."""
    import os

    return os.getenv("BITBUCKET_WEBHOOK_SECRET", "")


async def _verify_webhook_signature(
    body: bytes, signature: str, secret: str, provider: str
) -> bool:
    """
    Verify webhook signature.
    Args:
        body: Request body bytes
        signature: Signature from header
        secret: Webhook secret
        provider: Git provider name
    Returns:
        True if signature is valid, False otherwise
    """
    if provider == "github":
        # GitHub uses HMAC-SHA1
        expected_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha1
        ).hexdigest()
        return hmac.compare_digest(
            expected_signature.encode("utf-8"), signature.encode("utf-8")
        )
    elif provider == "gitlab":
        # GitLab uses HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(
            expected_signature.encode("utf-8"), signature.encode("utf-8")
        )
    elif provider == "bitbucket":
        # Bitbucket uses HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(
            expected_signature.encode("utf-8"), signature.encode("utf-8")
        )
    else:
        return False


# ============================================================================

# GitOps Endpoints

# ============================================================================


def _run_response_from_run(run: Any) -> dict:
    """Convert a GitOpsRun dataclass to a response dict."""
    return {
        "run_id": run.id,
        "repo_config_id": run.repo_config_id,
        "run_type": run.run_type.value,
        "status": run.status.value,
        "commit_sha": run.commit_sha,
        "branch": run.branch,
        "plan_diff": run.plan_diff,
        "apply_diff": run.apply_diff,
        "triggered_by": run.triggered_by,
        "trigger_method": run.trigger_method,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat(),
    }


@router.post("/gitops/{repo_config_id}/plan", response_model=GitOpsRunResponse)
async def trigger_plan(
    repo_config_id: str,
    request: PlanRequest,
    user_id: str = Depends(get_user_id),
) -> GitOpsRunResponse:
    """
    Trigger a Digger plan for a repository.
    Args:
        repo_config_id: Repository configuration ID
        request: Plan request parameters
        user_id: Authenticated user ID from auth middleware
    Returns:
        GitOpsRunResponse with run details
    Raises:
        HTTPException: If plan trigger fails
    """
    try:
        # Validate repo config exists
        db = db_provider.adapter
        repo_config = await db.get_repo_config(repo_config_id)
        if not repo_config:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Repository config not found: {repo_config_id}",
                        "type": "validation_error",
                        "code": "repo_not_found",
                    }
                },
            )

        digger_service = await get_digger_agent_service()
        run = await digger_service.run_plan(
            repo_config_id=repo_config_id,
            session_id=request.session_id,
            commit_sha=request.commit_sha,
            triggered_by=user_id,
            trigger_method=request.trigger_method,
            branch=request.branch,
        )
        logger.info(
            "Digger plan triggered",
            extra={
                "user_id": user_id,
                "repo_config_id": repo_config_id,
                "run_id": run.id,
                "branch": request.branch,
            },
        )
        return GitOpsRunResponse(**_run_response_from_run(run))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering plan for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to trigger plan",
                    "type": "gitops_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/gitops/{repo_config_id}/apply", response_model=GitOpsRunResponse)
async def trigger_apply(
    repo_config_id: str,
    request: ApplyRequest,
    user_id: str = Depends(get_user_id),
) -> GitOpsRunResponse:
    """
    Trigger a Digger apply for a repository.
    Args:
        repo_config_id: Repository configuration ID
        request: Apply request parameters
        user_id: Authenticated user ID from auth middleware
    Returns:
        GitOpsRunResponse with run details
    Raises:
        HTTPException: If apply trigger fails
    """
    try:
        # Validate repo config exists
        db = db_provider.adapter
        repo_config = await db.get_repo_config(repo_config_id)
        if not repo_config:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Repository config not found: {repo_config_id}",
                        "type": "validation_error",
                        "code": "repo_not_found",
                    }
                },
            )

        digger_service = await get_digger_agent_service()
        run = await digger_service.run_apply(
            repo_config_id=repo_config_id,
            session_id=request.session_id,
            commit_sha=request.commit_sha,
            triggered_by=user_id,
            trigger_method=request.trigger_method,
            branch=request.branch,
        )
        logger.info(
            "Digger apply triggered",
            extra={
                "user_id": user_id,
                "repo_config_id": repo_config_id,
                "run_id": run.id,
                "branch": request.branch,
            },
        )
        return GitOpsRunResponse(**_run_response_from_run(run))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering apply for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to trigger apply",
                    "type": "gitops_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/gitops/{repo_config_id}/runs", response_model=ListRunsResponse)
async def list_gitops_runs(
    repo_config_id: str,
    run_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_user_id),
) -> ListRunsResponse:
    """
    List GitOps runs for a repository.
    Args:
        repo_config_id: Repository configuration ID
        run_type: Filter by plan or apply
        limit: Max results
        offset: Pagination offset
        user_id: Authenticated user ID from auth middleware
    Returns:
        ListRunsResponse with run details
    Raises:
        HTTPException: If repo config not found
    """
    try:
        db = db_provider.adapter
        repo_config = await db.get_repo_config(repo_config_id)
        if not repo_config:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Repository config not found: {repo_config_id}",
                        "type": "validation_error",
                        "code": "repo_not_found",
                    }
                },
            )

        digger_service = await get_digger_agent_service()
        run_type_filter = GitOpsRunType(run_type) if run_type else None
        runs = await digger_service.list_runs(
            repo_config_id=repo_config_id,
            run_type=run_type_filter,
            limit=limit,
            offset=offset,
        )
        return ListRunsResponse(
            runs=[_run_response_from_run(r) for r in runs],
            total=len(runs),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing runs for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to list runs",
                    "type": "gitops_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/gitops/runs/{run_id}", response_model=GitOpsRunResponse)
async def get_gitops_run(
    run_id: str,
    user_id: str = Depends(get_user_id),
) -> GitOpsRunResponse:
    """
    Get a GitOps run by ID.
    Args:
        run_id: Run ID
        user_id: Authenticated user ID from auth middleware
    Returns:
        GitOpsRunResponse with run details
    Raises:
        HTTPException: If run not found
    """
    try:
        digger_service = await get_digger_agent_service()
        run = await digger_service.get_run(run_id)
        if not run:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Run not found: {run_id}",
                        "type": "validation_error",
                        "code": "run_not_found",
                    }
                },
            )
        return GitOpsRunResponse(**_run_response_from_run(run))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to get run",
                    "type": "gitops_error",
                    "code": "internal_error",
                }
            },
        )


@router.delete("/gitops/runs/{run_id}", response_model=GitOpsRunResponse)
async def cancel_gitops_run(
    run_id: str,
    user_id: str = Depends(get_user_id),
) -> GitOpsRunResponse:
    """
    Cancel a running GitOps run.
    Args:
        run_id: Run ID
        user_id: Authenticated user ID from auth middleware
    Returns:
        GitOpsRunResponse with updated run details
    Raises:
        HTTPException: If run not found
    """
    try:
        digger_service = await get_digger_agent_service()
        run = await digger_service.cancel_run(run_id)
        if not run:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Run not found: {run_id}",
                        "type": "validation_error",
                        "code": "run_not_found",
                    }
                },
            )
        logger.info(
            "GitOps run cancelled",
            extra={"user_id": user_id, "run_id": run_id},
        )
        return GitOpsRunResponse(**_run_response_from_run(run))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling run for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to cancel run",
                    "type": "gitops_error",
                    "code": "internal_error",
                }
            },
        )


class WebhookTestRequest(BaseModel):
    """Request to test a webhook URL."""

    url: str = Field(..., description="Webhook URL to test")
    secret: str = Field(..., description="Webhook secret for signature")


class WebhookTestResponse(BaseModel):
    """Response for webhook URL test."""

    success: bool = Field(..., description="Whether the test succeeded")
    status_code: Optional[int] = Field(None, description="HTTP status code received")
    response_time: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error details if failed")


@router.post("/gitops/webhooks/test-url", response_model=WebhookTestResponse)
async def test_webhook_url(
    request: WebhookTestRequest,
    user_id: str = Depends(get_user_id),
) -> WebhookTestResponse:
    """
    Test a webhook URL by firing a test payload.
    Verifies that the endpoint is reachable and validates the signature.
    """
    try:
        import aiohttp

        # Fire a test webhook payload
        test_payload = {
            "zen": "Webhook connection test from IaC Genie",
            "repository": {"name": "test", "html_url": "", "clone_url": ""},
        }
        secret_bytes = request.secret.encode("utf-8")
        signature = hmac.new(
            secret_bytes, json.dumps(test_payload).encode(), hashlib.sha256
        ).hexdigest()

        import time

        async with aiohttp.ClientSession() as session:
            start = time.monotonic()
            async with session.post(
                request.url,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": f"sha256={signature}",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                elapsed_ms = round((time.monotonic() - start) * 1000, 1)
                if resp.status >= 200 and resp.status < 300:
                    return WebhookTestResponse(
                        success=True,
                        status_code=resp.status,
                        response_time=elapsed_ms,
                        message="Webhook endpoint is reachable and accepted the test payload",
                        error=None,
                    )
                else:
                    body = await resp.text()
                    return WebhookTestResponse(
                        success=False,
                        status_code=resp.status,
                        response_time=elapsed_ms,
                        message=f"Webhook endpoint returned status {resp.status}",
                        error=body[:500],
                    )
    except aiohttp.ClientConnectorError:
        return WebhookTestResponse(
            success=False,
            status_code=None,
            response_time=None,
            message="Unable to connect to the webhook endpoint",
            error="The URL is not reachable. Check that the URL is correct and the endpoint is running.",
        )
    except asyncio.TimeoutError:
        return WebhookTestResponse(
            success=False,
            status_code=None,
            response_time=None,
            message="Webhook endpoint did not respond in time",
            error="The endpoint did not respond within 10 seconds.",
        )
    except Exception as e:
        logger.error(f"Webhook test failed: {e}", exc_info=True)
        return WebhookTestResponse(
            success=False,
            status_code=None,
            response_time=None,
            message="Webhook test failed",
            error=str(e),
        )


class GitRepoConfigRequest(BaseModel):
    name: str = Field(..., description="Repository name")
    provider: str = Field(
        "github", description="Git provider (github, gitlab, bitbucket, etc.)"
    )
    url: str = Field(..., description="Repository URL")
    branch: str = Field("main", description="Default branch")
    accessToken: Optional[str] = Field(
        None, description="Access token for private repository authentication"
    )
    token: Optional[str] = Field(None, description="Alternative field for access token")


@router.post("/repos/{project_id}")
async def create_project_git_repo(
    project_id: str,
    repo_data: GitRepoConfigRequest,
    user_id: str = Depends(get_user_id),
) -> Dict[str, Any]:
    """
    Persist Git Repository Configuration for a specific project.
    """
    try:
        db = db_provider.adapter
        if not db:
            raise HTTPException(status_code=500, detail="Database not initialized")
        project = await db.get_project(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project {project_id} not found"
            )
        repo_payload = {
            "name": repo_data.name,
            "provider": repo_data.provider,
            "url": repo_data.url,
            "branch": repo_data.branch,
            "token_encrypted": repo_data.accessToken or repo_data.token or "",
        }
        result = await db.create_git_repository(user_id, project_id, repo_payload)
        return {"success": True, "repository": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create git repository configuration: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Internal database error: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for Git/CI-CD service.
    Returns:
        Health status of the Git/CI-CD service
    """
    try:
        repo_manager = get_repo_manager()
        webhook_handler = get_webhook_handler()
        github_actions_provider = get_github_actions_provider()
        return {
            "status": "healthy",
            "service": "git_cicd",
            "repo_manager_initialized": repo_manager is not None,
            "webhook_handler_initialized": webhook_handler is not None,
            "github_actions_initialized": github_actions_provider is not None,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "service": "git_cicd", "error": str(e)}
