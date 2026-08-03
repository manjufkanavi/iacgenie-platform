"""Webhook handler for Git & CI/CD integration."""

import hmac

import hashlib

import json


import logging

from datetime import datetime, timedelta

from typing import Dict, Any

from fastapi import Request, HTTPException

from .config import config

from .models import GitProvider

from db.db_provider import db_provider

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles incoming webhooks from Git providers."""

    # Events that should trigger Digger plan/apply
    DIGGER_EVENTS = {
        "push",
        "pull_request",
        "pull_request_target",
        "pull_request_review",
    }

    def __init__(self) -> None:
        self.provider_secrets = {
            GitProvider.GITHUB: config.WEBHOOK_SIGNATURE_SECRET,
            GitProvider.GITLAB: config.GITLAB_TOKEN,
            GitProvider.BITBUCKET: config.BITBUCKET_APP_PASSWORD,
        }
        self.replay_cache: Dict[str, Any] = {}
        self.replay_cache_max_size = 10000
        self.replay_protection_window = timedelta(
            minutes=config.WEBHOOK_REPLAY_PROTECTION_WINDOW_MINUTES
        )
        self._payload: Dict[str, Any] = {}
        self._raw_body: bytes = b""

    def verify_signature(self, provider: str, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.
        """
        # Get provider secret
        secret = self.provider_secrets.get(provider)  # type: ignore[call-overload]
        if not secret:
            logger.error(f"Missing webhook secret for provider: {provider}")
            return False
        # Compute expected signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    def _cleanup_replay_cache(self) -> None:
        """Evict stale entries older than the replay protection window."""
        now = datetime.utcnow()
        stale = [
            k
            for k, v in self.replay_cache.items()
            if (now - v) > self.replay_protection_window
        ]
        for k in stale:
            del self.replay_cache[k]
        # Bound the cache size
        if len(self.replay_cache) > self.replay_cache_max_size:
            sorted_keys = sorted(self.replay_cache, key=lambda k: self.replay_cache[k])
            for k in sorted_keys[
                : len(self.replay_cache) - self.replay_cache_max_size // 2
            ]:
                del self.replay_cache[k]

    def is_replay_attack(self, delivery_id: str) -> bool:
        """
        Check if this is a replay attack using the delivery UUID.
        GitHub/GitLab/Bitbucket each provide a unique delivery ID per webhook event.
        """
        if not delivery_id:
            logger.debug("Rejecting webhook: missing delivery ID")
            return True
        if delivery_id in self.replay_cache:
            logger.debug(f"Rejecting webhook: duplicate delivery ID: {delivery_id}")
            return True
        return False

    async def _parse_payload(self, request: Request) -> Dict[str, Any]:
        """Parse the webhook payload and store it for event processing."""
        self._raw_body = await request.body()
        try:
            self._payload = json.loads(self._raw_body.decode("utf-8"))
        except Exception:
            self._payload = {}
        return self._payload

    def _extract_event_info(self) -> Dict[str, Any]:
        """Extract relevant info from the stored payload for Digger triggering."""
        event_type = self._payload.get("zen") or ""
        info: Dict[str, Any] = {"raw_event": event_type}

        if "pull_request" in self._payload:
            pr = self._payload["pull_request"]
            info["action"] = self._payload.get("action", "")
            info["pr_number"] = pr.get("number")
            info["branch"] = pr.get("head", {}).get("ref", "")
            info["base_branch"] = pr.get("base", {}).get("ref", "")
            head_ref = pr.get("head", {})
            info["commit_sha"] = head_ref.get("sha", "")
        elif "push" in self._payload:
            push = self._payload["push"]
            ref = push.get("ref", "refs/heads/main")
            info["branch"] = ref.replace("refs/heads/", "")
            info["commit_sha"] = push.get("after", "")
            info["action"] = "push"

        # Get repo URL
        repo = self._payload.get("repository", {})
        info["repo_url"] = repo.get("clone_url") or repo.get("html_url", "")
        info["repo_name"] = repo.get("name", "")
        info["repo_owner"] = (
            repo.get("owner", {}).get("name") or repo.get("full_name", "").split("/")[0]
        )

        if "pr_number" not in info:
            info["pr_number"] = None

        return info

    def should_trigger_digger(self) -> bool:
        """Determine if this webhook should trigger Digger."""
        has_push = "push" in self._payload
        has_pr = "pull_request" in self._payload
        has_pr_review = "pull_request_review" in self._payload

        if has_pr:
            action = self._payload.get("action", "")
            return action in ("opened", "synchronize", "ready_for_review")
        if has_pr_review:
            action = self._payload.get("action", "")
            return action in ("submitted")
        if has_push:
            return True
        return False

    async def process_event(self, provider: str) -> Dict[str, Any]:
        """
        Process a validated webhook event and trigger Digger if applicable.
        This is called after signature verification and replay protection.
        """
        if not self.should_trigger_digger():
            logger.info(
                "Webhook event does not require Digger action",
                extra={"provider": provider},
            )
            return {"status": "processed", "digger_triggered": False}

        event_info = self._extract_event_info()
        logger.info(
            "Processing Digger-triggering webhook event",
            extra={
                "provider": provider,
                "event_info": event_info,
            },
        )

        repo_url = event_info.get("repo_url", "")
        if not repo_url:
            logger.error("No repository URL in webhook payload")
            return {"status": "processed", "digger_triggered": False}

        # Resolve repo_config_id from the database
        repo_config_id = await self._resolve_repo_config_id(repo_url)
        if not repo_config_id:
            logger.error(
                f"Could not find repo config for URL: {repo_url}",
                extra={"repo_url": repo_url},
            )
            return {"status": "processed", "digger_triggered": False}

        # Dispatch to Digger
        from .digger_agent import get_digger_service

        try:
            digger = await get_digger_service(self._get_db())
            pr_number = event_info.get("pr_number")
            commit_sha = event_info.get("commit_sha", "")
            branch = event_info.get("branch", "main")
            session_id = f"webhook-{provider}-{event_info.get('repo_name', '')}"

            if pr_number:
                # PR event: run plan and post comment
                run = await digger.run_plan(
                    repo_config_id=repo_config_id,
                    session_id=session_id,
                    commit_sha=commit_sha,
                    triggered_by="webhook",
                    trigger_method="webhook",
                    branch=branch,
                )
                await digger.post_plan_comment(
                    repo_config_id=repo_config_id,
                    pr_number=pr_number,
                    run=run,
                )
                logger.info(
                    "Digger plan triggered from webhook + PR comment posted",
                    extra={"pr_number": pr_number, "run_id": run.id},
                )
                return {
                    "status": "processed",
                    "digger_triggered": True,
                    "run_id": run.id,
                    "run_type": "plan",
                    "pr_number": pr_number,
                }
            else:
                # Push event: run plan
                run = await digger.run_plan(
                    repo_config_id=repo_config_id,
                    session_id=session_id,
                    commit_sha=commit_sha,
                    triggered_by="webhook",
                    trigger_method="webhook",
                    branch=branch,
                )
                logger.info(
                    "Digger plan triggered from push webhook",
                    extra={"branch": branch, "run_id": run.id},
                )
                return {
                    "status": "processed",
                    "digger_triggered": True,
                    "run_id": run.id,
                    "run_type": "plan",
                }
        except Exception as e:
            logger.error(
                "Failed to trigger Digger from webhook",
                extra={"provider": provider, "error": str(e)},
            )
            return {
                "status": "processed",
                "digger_triggered": False,
                "error": str(e),
            }

    def _get_db(self) -> Any:
        """Get the database adapter."""
        try:
            from db.db_provider import db_provider

            return db_provider.adapter
        except Exception:
            return None

    async def _resolve_repo_config_id(self, repo_url: str) -> str:
        """Resolve a repo_config_id from the database using the repo URL.

        Uses db_provider.find_repo_by_url which normalizes URLs
        (case-insensitive, token-stripped, trailing-slash-removed).
        """
        try:
            repo = await db_provider.find_repo_by_url(repo_url)
            if repo:
                return repo.get("id", "")
        except Exception as e:
            logger.debug(f"Repo lookup failed: {str(e)}")
        return ""

    async def handle_webhook(
        self,
        provider: str,
        request: Request,
    ) -> Dict[str, Any]:
        """
        Handle incoming webhook from Git provider.
        Performs signature verification and replay protection only.
        Use process_event() to trigger Digger actions.
        """
        # Parse payload
        payload = await self._parse_payload(request)
        # Get signature from headers
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not signature:
            raise HTTPException(status_code=401, detail="Missing signature")
        # Get raw body
        body = await request.body()
        # Verify signature
        if not self.verify_signature(provider, body, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
        # Check for replay attack using delivery UUID
        delivery_id = request.headers.get("X-GitHub-Delivery", "")
        if self.is_replay_attack(delivery_id):
            raise HTTPException(status_code=403, detail="Replay attack detected")
        # Cache delivery ID to prevent duplicate processing
        self.replay_cache[delivery_id] = datetime.utcnow()
        # Periodic cleanup of stale entries
        self._cleanup_replay_cache()
        # Log receipt
        logger.info(
            f"Webhook received from {provider}",
            extra={"event_type": payload.get("type"), "delivery_id": delivery_id},
        )
        return {"status": "processed"}
