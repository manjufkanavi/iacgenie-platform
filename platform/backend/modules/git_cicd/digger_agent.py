"""Digger agent service for running plan/apply operations."""

import asyncio
import dataclasses
import os
import tempfile
import hashlib
from pathlib import Path
from typing import Any, Optional

from datetime import datetime
from uuid import uuid4

import docker

from modules.git_cicd.models import (
    GitOpsRun,
    GitOpsRunType,
    GitOpsRunStatus,
    GitProvider,
    PrComment,
)
from modules.observability import log_info, log_error
from db.db_provider import db_provider


class DiggerAgentService:
    """Service that executes Digger plan/apply operations in isolated Docker containers."""

    DOCKER_IMAGE = os.environ.get("DIGGER_DOCKER_IMAGE", "diggerhq/digger:latest")
    GIT_IMAGE = os.environ.get("DIGGER_GIT_IMAGE", "alpine/git:latest")

    def __init__(self, db_adapter: Optional[Any] = None) -> None:
        self.db = db_adapter or db_provider.adapter
        self.docker_client: Optional["docker.DockerClient"] = None  # type: ignore
        try:
            self.docker_client = docker.from_env()  # type: ignore
            log_info("Docker client initialized for DiggerAgentService")
        except Exception as e:
            log_error(f"Failed to initialize Docker client: {str(e)}")
            self.docker_client = None

    def _get_docker_client(self) -> "docker.DockerClient":  # type: ignore
        if not self.docker_client:
            self.docker_client = docker.from_env()  # type: ignore
        return self.docker_client

    async def run_plan(
        self,
        repo_config_id: str,
        session_id: str = "",
        commit_sha: str = "",
        triggered_by: str = "",
        trigger_method: str = "manual",
        branch: str = "main",
    ) -> GitOpsRun:
        """Execute a Digger plan for the given repository."""
        run_id = str(uuid4())
        now = datetime.utcnow()
        run = GitOpsRun(
            id=run_id,
            repo_config_id=repo_config_id,
            session_id=session_id,
            run_type=GitOpsRunType.PLAN,
            status=GitOpsRunStatus.QUEUED,
            commit_sha=commit_sha,
            branch=branch,
            triggered_by=triggered_by,
            trigger_method=trigger_method,
            created_at=now,
        )

        # Save initial run record to DB
        try:
            await self._save_gitops_run(run)
        except Exception as e:
            log_error(f"Failed to save run record: {str(e)}")

        run = dataclasses.replace(run, status=GitOpsRunStatus.RUNNING, started_at=now)

        try:
            if not self.docker_client:
                raise RuntimeError("Docker client not available")

            repo_config = await self.db.get_repo_config(repo_config_id)
            if not repo_config:
                raise ValueError(f"Repository config not found: {repo_config_id}")

            repo_url = repo_config["url"]
            token = repo_config.get("token_encrypted", "")

            with tempfile.TemporaryDirectory() as tmpdir:
                log_info(
                    "Starting digger plan",
                    extra={"run_id": run_id, "repo": repo_url, "branch": branch},
                )

                # Clone repo inside working directory
                clone_dir = Path(tmpdir) / "repo"
                clone_cmd = [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    _sanitize_repo_url(repo_url, token),
                    str(clone_dir),
                ]
                clone_result = await _run_command(clone_cmd, timeout=300)
                if clone_result["exit_code"] != 0:
                    raise RuntimeError(f"Git clone failed: {clone_result['stderr']}")

                # Run digger plan
                plan_cmd = [
                    "sh",
                    "-c",
                    "digger plan --project default --yes 2>&1 || true",
                ]
                plan_result = await _run_command_in_docker(
                    client=self._get_docker_client(),
                    image=self.DOCKER_IMAGE,
                    working_dir=str(clone_dir),
                    command=plan_cmd,
                    env={
                        "HOME": "/root",
                        "WORKSPACE_DIR": "/workspace",
                    },
                    timeout=1800,
                )

                plan_diff = (plan_result.get("stdout") or "") + (
                    plan_result.get("stderr") or ""
                )

                # Save plan diff to a file in the repo for later reference
                plan_file = clone_dir / ".digger_plan_output.txt"
                plan_file.write_text(plan_diff)

                # Commit plan output if it's not empty
                if plan_diff.strip():
                    commit_cmd = [
                        "sh",
                        "-c",
                        f"cd {clone_dir} && "
                        f"git add .digger_plan_output.txt && "
                        f'git commit -m "digger: save plan output [{run_id[:8]}]" && '
                        f"git push origin {branch}",
                    ]
                    await _run_command(commit_cmd, timeout=120)

                run = dataclasses.replace(
                    run,
                    status=GitOpsRunStatus.COMPLETED,
                    commit_sha=commit_sha,
                    plan_diff=plan_diff[:100_000],  # Cap at 100K chars
                    completed_at=datetime.utcnow(),
                )

                log_info(
                    "Digger plan completed",
                    extra={"run_id": run_id, "status": "completed"},
                )

        except Exception as e:
            log_error(
                "Digger plan failed",
                extra={"run_id": run_id, "error": str(e)},
            )
            run = dataclasses.replace(
                run,
                status=GitOpsRunStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.utcnow(),
            )

        # Persist final run state
        try:
            await self._save_gitops_run(run)
        except Exception as e:
            log_error(f"Failed to persist run state: {str(e)}")

        return run

    async def run_apply(
        self,
        repo_config_id: str,
        session_id: str = "",
        commit_sha: str = "",
        triggered_by: str = "",
        trigger_method: str = "manual",
        branch: str = "main",
    ) -> GitOpsRun:
        """Execute a Digger apply for the given repository."""
        run_id = str(uuid4())
        now = datetime.utcnow()
        run = GitOpsRun(
            id=run_id,
            repo_config_id=repo_config_id,
            session_id=session_id,
            run_type=GitOpsRunType.APPLY,
            status=GitOpsRunStatus.QUEUED,
            commit_sha=commit_sha,
            branch=branch,
            triggered_by=triggered_by,
            trigger_method=trigger_method,
            created_at=now,
        )

        try:
            await self._save_gitops_run(run)
        except Exception as e:
            log_error(f"Failed to save run record: {str(e)}")

        run = dataclasses.replace(run, status=GitOpsRunStatus.RUNNING, started_at=now)

        try:
            if not self.docker_client:
                raise RuntimeError("Docker client not available")

            repo_config = await self.db.get_repo_config(repo_config_id)
            if not repo_config:
                raise ValueError(f"Repository config not found: {repo_config_id}")

            repo_url = repo_config["url"]
            token = repo_config.get("token_encrypted", "")

            with tempfile.TemporaryDirectory() as tmpdir:
                log_info(
                    "Starting digger apply",
                    extra={"run_id": run_id, "repo": repo_url, "branch": branch},
                )

                clone_dir = Path(tmpdir) / "repo"
                clone_cmd = [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    _sanitize_repo_url(repo_url, token),
                    str(clone_dir),
                ]
                clone_result = await _run_command(clone_cmd, timeout=300)
                if clone_result["exit_code"] != 0:
                    raise RuntimeError(f"Git clone failed: {clone_result['stderr']}")

                # Run digger apply
                apply_cmd = [
                    "sh",
                    "-c",
                    "digger apply --project default 2>&1 || true",
                ]
                apply_result = await _run_command_in_docker(
                    client=self._get_docker_client(),
                    image=self.DOCKER_IMAGE,
                    working_dir=str(clone_dir),
                    command=apply_cmd,
                    env={
                        "HOME": "/root",
                        "WORKSPACE_DIR": "/workspace",
                    },
                    timeout=1800,
                )

                apply_diff = (apply_result.get("stdout") or "") + (
                    apply_result.get("stderr") or ""
                )

                # Commit apply output
                plan_file = clone_dir / ".digger_apply_output.txt"
                plan_file.write_text(apply_diff)
                if apply_diff.strip():
                    commit_cmd = [
                        "sh",
                        "-c",
                        f"cd {clone_dir} && "
                        f"git add .digger_apply_output.txt && "
                        f'git commit -m "digger: save apply output [{run_id[:8]}]" && '
                        f"git push origin {branch}",
                    ]
                    await _run_command(commit_cmd, timeout=120)

                run = dataclasses.replace(
                    run,
                    status=GitOpsRunStatus.COMPLETED,
                    commit_sha=commit_sha,
                    apply_diff=apply_diff[:100_000],
                    completed_at=datetime.utcnow(),
                )

                log_info(
                    "Digger apply completed",
                    extra={"run_id": run_id, "status": "completed"},
                )

        except Exception as e:
            log_error(
                "Digger apply failed",
                extra={"run_id": run_id, "error": str(e)},
            )
            run = dataclasses.replace(
                run,
                status=GitOpsRunStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.utcnow(),
            )

        try:
            await self._save_gitops_run(run)
        except Exception as e:
            log_error(f"Failed to persist run state: {str(e)}")

        return run

    async def cancel_run(self, run_id: str) -> Optional[GitOpsRun]:
        """Cancel a running GitOps run."""
        try:
            run = await self._get_gitops_run(run_id)
            if not run:
                return None
            if run.status in (
                GitOpsRunStatus.COMPLETED,
                GitOpsRunStatus.FAILED,
                GitOpsRunStatus.CANCELLED,
            ):
                return run
            run = dataclasses.replace(
                run,
                status=GitOpsRunStatus.CANCELLED,
                completed_at=datetime.utcnow(),
                error_message="Run cancelled by user",
            )
            await self._save_gitops_run(run)
            return run
        except Exception as e:
            log_error(f"Failed to cancel run {run_id}: {str(e)}")
            return None

    async def get_run(self, run_id: str) -> Optional[GitOpsRun]:
        """Get a GitOps run by ID."""
        try:
            return await self._get_gitops_run(run_id)
        except Exception as e:
            log_error(f"Failed to get run {run_id}: {str(e)}")
            return None

    async def list_runs(
        self,
        repo_config_id: str,
        run_type: Optional[GitOpsRunType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """List GitOps runs for a repository."""
        try:
            return await self._list_gitops_runs(repo_config_id, run_type, limit, offset)
        except Exception as e:
            log_error(f"Failed to list runs for {repo_config_id}: {str(e)}")
            return []

    async def post_plan_comment(
        self,
        repo_config_id: str,
        pr_number: int,
        run: GitOpsRun,
    ) -> Optional[PrComment]:
        """Post Digger plan result as a comment on the PR."""
        try:
            repo_config = await self.db.get_repo_config(repo_config_id)
            if not repo_config:
                return None

            provider_name = repo_config.get("provider", "github")
            provider = GitProvider(provider_name)
            repo_url = repo_config["url"]

            parts = repo_url.rstrip("/").split("/")
            owner = parts[-2]
            repo_name = parts[-1]

            # Format plan diff as markdown comment
            comment_body = _format_pr_comment(run, "plan")

            # Compute content hash for deduplication
            content_hash = hashlib.sha256(comment_body.encode()).hexdigest()[:16]

            # Post comment via provider API
            comment_url = await _post_pr_comment(
                provider=provider,
                owner=owner,
                repo_name=repo_name,
                pr_number=pr_number,
                comment=comment_body,
                token=repo_config.get("token_encrypted", ""),
            )

            comment = PrComment(
                id=str(uuid4()),
                repo_config_id=repo_config_id,
                pr_number=pr_number,
                provider=provider,
                comment_url=comment_url or "",
                content_hash=content_hash,
                run_id=run.id,
            )

            await self._save_pr_comment(comment)
            return comment

        except Exception as e:
            log_error(f"Failed to post PR comment: {str(e)}")
            return None

    async def _save_gitops_run(self, run: GitOpsRun) -> None:
        """Persist a GitOps run to the database."""
        try:
            await self.db.create_audit_log(
                user_id=run.triggered_by or "system",
                log_data={
                    "entity_type": "gitops_run",
                    "entity_id": run.id,
                    "repo_config_id": run.repo_config_id,
                    "run_type": run.run_type.value,
                    "status": run.status.value,
                    "commit_sha": run.commit_sha,
                    "branch": run.branch,
                    "plan_diff": run.plan_diff[:1000] if run.plan_diff else "",
                    "apply_diff": run.apply_diff[:1000] if run.apply_diff else "",
                    "error_message": run.error_message,
                    "trigger_method": run.trigger_method,
                    "started_at": run.started_at.isoformat()
                    if run.started_at
                    else None,
                    "completed_at": run.completed_at.isoformat()
                    if run.completed_at
                    else None,
                    "created_at": run.created_at.isoformat(),
                    "session_id": run.session_id,
                },
            )
        except Exception:
            # Audit log failure should not block run persistence
            log_error(f"Failed to save gitops run to audit log: {run.id}")

    async def _get_gitops_run(self, run_id: str) -> Optional[GitOpsRun]:
        """Retrieve a GitOps run from audit logs."""
        try:
            logs = await self.db.get_audit_logs(
                user_id="system",
                limit=100,
                offset=0,
            )
            for log_entry in logs:
                entity_id = log_entry.get("entity_id", "")
                entity_type = log_entry.get("entity_type", "")
                if entity_id == run_id and entity_type == "gitops_run":
                    data = log_entry.get("log_data", {})
                    return GitOpsRun(
                        id=run_id,
                        repo_config_id=data.get("repo_config_id", ""),
                        session_id=data.get("session_id", ""),
                        run_type=GitOpsRunType(data.get("run_type", "plan")),
                        status=GitOpsRunStatus(data.get("status", "queued")),
                        commit_sha=data.get("commit_sha", ""),
                        branch=data.get("branch", "main"),
                        plan_diff=data.get("plan_diff", ""),
                        apply_diff=data.get("apply_diff", ""),
                        triggered_by=data.get("triggered_by", ""),
                        trigger_method=data.get("trigger_method", "manual"),
                        started_at=datetime.fromisoformat(data["started_at"])
                        if data.get("started_at")
                        else None,
                        completed_at=datetime.fromisoformat(data["completed_at"])
                        if data.get("completed_at")
                        else None,
                        error_message=data.get("error_message"),
                        created_at=datetime.fromisoformat(data.get("created_at", "")),
                    )
            return None
        except Exception as e:
            log_error(f"Failed to get run {run_id}: {str(e)}")
            return None

    async def _list_gitops_runs(
        self,
        repo_config_id: str,
        run_type: Optional[GitOpsRunType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """List GitOps runs for a repository from audit logs."""
        try:
            logs = await self.db.get_audit_logs(
                user_id="system",
                limit=limit + 1,  # fetch one extra to check if there are more
                offset=offset,
            )
            runs = []
            for log_entry in logs:
                data = log_entry.get("log_data", {})
                if data.get("repo_config_id") != repo_config_id:
                    continue
                if run_type and data.get("run_type") != run_type.value:
                    continue
                entity_id = log_entry.get("entity_id", "")
                run = GitOpsRun(
                    id=entity_id,
                    repo_config_id=data.get("repo_config_id", ""),
                    session_id=data.get("session_id", ""),
                    run_type=GitOpsRunType(data.get("run_type", "plan")),
                    status=GitOpsRunStatus(data.get("status", "queued")),
                    commit_sha=data.get("commit_sha", ""),
                    branch=data.get("branch", "main"),
                    plan_diff=data.get("plan_diff", ""),
                    apply_diff=data.get("apply_diff", ""),
                    triggered_by=data.get("triggered_by", ""),
                    trigger_method=data.get("trigger_method", "manual"),
                    started_at=datetime.fromisoformat(data["started_at"])
                    if data.get("started_at")
                    else None,
                    completed_at=datetime.fromisoformat(data["completed_at"])
                    if data.get("completed_at")
                    else None,
                    error_message=data.get("error_message"),
                    created_at=datetime.fromisoformat(data.get("created_at", "")),
                )
                runs.append(run)
                if len(runs) >= limit:
                    break
            return runs
        except Exception as e:
            log_error(f"Failed to list runs: {str(e)}")
            return []

    async def _save_pr_comment(self, comment: PrComment) -> None:
        """Persist PR comment to audit log."""
        try:
            await self.db.create_audit_log(
                user_id="system",
                log_data={
                    "entity_type": "pr_comment",
                    "entity_id": comment.id,
                    "repo_config_id": comment.repo_config_id,
                    "pr_number": comment.pr_number,
                    "provider": comment.provider.value,
                    "comment_url": comment.comment_url,
                    "content_hash": comment.content_hash,
                    "run_id": comment.run_id,
                    "created_at": comment.created_at.isoformat(),
                },
            )
        except Exception:
            log_error(f"Failed to save PR comment: {comment.id}")


def _sanitize_repo_url(repo_url: str, token: str) -> str:
    """Inject authentication token into repo URL for HTTPS access."""
    if not token:
        return repo_url
    try:
        import re

        # Match https://github.com/owner/repo.git pattern and inject token
        pattern = r"(https://)([^@]+@)?(.*)"
        match = re.match(pattern, repo_url)
        if match:
            return f"{match.group(1)}{token}@{match.group(3)}"
    except Exception:
        pass
    return repo_url


async def _run_command(cmd: list, timeout: int = 300) -> dict:
    """Run a system command asynchronously."""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return {
            "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
            "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
            "exit_code": process.returncode,
        }
    except asyncio.TimeoutError:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "exit_code": -1,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}


async def _run_command_in_docker(
    client: "docker.DockerClient",  # type: ignore
    image: str,
    working_dir: str,
    command: list,
    env: Optional[dict] = None,
    timeout: int = 300,
) -> dict:
    """Run a command inside a Digger Docker container."""
    try:
        container = client.containers.run(
            image,
            command,
            volumes={working_dir: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            environment=env,
            detach=True,
            remove=True,
        )
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", -1)
        logs = container.logs(stdout=True, stderr=True).decode(
            "utf-8", errors="replace"
        )
        container.remove()
        return {
            "stdout": logs,
            "stderr": "",
            "exit_code": exit_code if isinstance(exit_code, int) else 0,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}


def _format_pr_comment(run: GitOpsRun, comment_type: str) -> str:
    """Format a GitOps run result as a GitHub-flavored markdown comment."""
    status_emoji = {
        GitOpsRunStatus.COMPLETED: ":white_check_mark:",
        GitOpsRunStatus.FAILED: ":x:",
        GitOpsRunStatus.CANCELLED: ":stop_sign:",
        GitOpsRunStatus.RUNNING: ":hourglass_flowing:",
        GitOpsRunStatus.QUEUED: ":inbox_tray:",
    }
    emoji = status_emoji.get(run.status, ":speech_balloon:")
    run_type_label = "Plan" if run.run_type == GitOpsRunType.PLAN else "Apply"
    status_label = run.status.value.upper()

    lines = [
        f"## {emoji} Digger {run_type_label} Result",
        "",
        f"**Status:** `{status_label}`",
        f"**Branch:** `{run.branch}`",
    ]
    if run.triggered_by:
        lines.append(f"**Triggered by:** `{run.triggered_by}`")
    if run.started_at:
        lines.append(
            f"**Started at:** {run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
    if run.completed_at:
        lines.append(
            f"**Completed at:** {run.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

    diff = run.plan_diff if comment_type == "plan" else run.apply_diff
    if diff:
        lines.append(
            f"\n<details><summary>{run_type_label} Output</summary>\n\n```terraform\n"
        )
        lines.append(diff[:50_000])  # Cap comment body at 50K chars
        lines.append("\n```\n\n</details>")
    if run.error_message:
        lines.append(f"\n> :warning: **Error:** {run.error_message}")

    return "\n".join(lines)


async def _post_pr_comment(
    provider: GitProvider,
    owner: str,
    repo_name: str,
    pr_number: int,
    comment: str,
    token: str = "",
) -> Optional[str]:
    """Post a comment to a PR via the Git provider API."""
    import httpx

    if provider == GitProvider.GITHUB:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/issues/{pr_number}/comments",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "Authorization": f"Bearer {token}",
                },
                json={"body": comment},
                timeout=30,
            )
            if resp.status_code == 201:
                return resp.json().get("html_url")
            log_error(
                f"Failed to post GitHub PR comment: {resp.status_code} - {resp.text[:200]}"
            )
    elif provider == GitProvider.GITLAB:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://gitlab.com/api/v4/projects/{owner}%2F{repo_name}/issues",
                headers={"PRIVATE-TOKEN": token},
                json={
                    "issue_id": pr_number,
                    "body": comment,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                return resp.json().get("web_url")
            log_error(
                f"Failed to post GitLab comment: {resp.status_code} - {resp.text[:200]}"
            )
    elif provider == GitProvider.BITBUCKET:
        async with httpx.AsyncClient() as client:
            from httpx_auth import Basic

            auth = Basic("", token)  # Bitbucket uses app password as token
            resp = await client.post(
                f"https://api.bitbucket.org/2.0/repositories/{owner}/{repo_name}/pullrequests/{pr_number}/comments",
                auth=auth,
                json={"content": {"raw": comment}},
                timeout=30,
            )
            if resp.status_code == 201:
                return resp.json().get("links", {}).get("html", {}).get("href")
            log_error(
                f"Failed to post Bitbucket comment: {resp.status_code} - {resp.text[:200]}"
            )

    return None


# Global singleton instance
digger_service: Optional[DiggerAgentService] = None


async def get_digger_service(db_adapter: Optional[Any] = None) -> DiggerAgentService:
    """Get or create DiggerAgentService singleton."""
    global digger_service
    if digger_service is None:
        digger_service = DiggerAgentService(db_adapter=db_adapter)
    return digger_service
