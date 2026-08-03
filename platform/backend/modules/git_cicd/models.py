"""Data models for Git & CI/CD integration."""

from dataclasses import dataclass, field

from datetime import datetime

from enum import Enum

from typing import Optional, Dict, Any


class GitProvider(Enum):
    """Git provider types."""

    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class CommitStatus(Enum):
    """Status of a commit operation."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class GitCommit:
    """Represents a Git commit."""

    id: str
    session_id: str
    provider: GitProvider
    repo_url: str
    branch: str
    commit_sha: str = ""
    status: CommitStatus = CommitStatus.SUCCESS
    message: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert commit to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "provider": self.provider.value,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "status": self.status.value,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "files": self.files,
        }


@dataclass
class CIRun:
    """Represents a CI/CD run."""

    id: str
    session_id: str
    provider: GitProvider
    repo_url: str
    run_id: str
    status: str
    workflow_file: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    logs_url: Optional[str] = None
    created_at: Optional[str] = None
    run_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert CI run to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "provider": self.provider.value,
            "repo_url": self.repo_url,
            "run_id": self.run_id,
            "status": self.status,
            "workflow_file": self.workflow_file,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "logs_url": self.logs_url,
        }


class GitOpsRunType(Enum):
    """Type of GitOps operation."""

    PLAN = "plan"
    APPLY = "apply"


class GitOpsRunStatus(Enum):
    """Status of a GitOps run."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GitOpsRun:
    """Represents a Digger plan/apply run."""

    id: str
    repo_config_id: str
    session_id: str
    run_type: GitOpsRunType
    status: GitOpsRunStatus
    commit_sha: str = ""
    branch: str = "main"
    plan_diff: str = ""
    apply_diff: str = ""
    triggered_by: str = ""
    trigger_method: str = "manual"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert run to dictionary."""
        return {
            "id": self.id,
            "repo_config_id": self.repo_config_id,
            "session_id": self.session_id,
            "run_type": self.run_type.value,
            "status": self.status.value,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "plan_diff": self.plan_diff,
            "apply_diff": self.apply_diff,
            "triggered_by": self.triggered_by,
            "trigger_method": self.trigger_method,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PrComment:
    """Represents a Digger comment posted on a PR."""

    id: str
    repo_config_id: str
    pr_number: int
    provider: GitProvider
    comment_url: str = ""
    content_hash: str = ""
    run_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert PR comment to dictionary."""
        return {
            "id": self.id,
            "repo_config_id": self.repo_config_id,
            "pr_number": self.pr_number,
            "provider": self.provider.value,
            "comment_url": self.comment_url,
            "content_hash": self.content_hash,
            "run_id": self.run_id,
            "created_at": self.created_at.isoformat(),
        }
