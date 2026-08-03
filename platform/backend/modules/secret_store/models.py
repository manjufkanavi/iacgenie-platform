"""

Secret Store Data Models

Data models for the Secret Store module following the design document specifications.

"""

import uuid

from datetime import datetime

from enum import Enum

from typing import Any, Dict, Optional

from dataclasses import dataclass, field


class SecretType(Enum):
    """Types of secrets managed by the Secret Store."""

    GIT_TOKEN = "git_token"
    CI_PAT = "ci_pat"
    LLM_API_KEY = "llm_api_key"
    CLOUD_CREDENTIAL = "cloud_credential"
    GENERIC = "generic"


class SecretOperation(Enum):
    """Operations that can be performed on secrets."""

    READ = "read"
    WRITE = "write"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    GENERATE = "generate"
    ACCESS = "access"


@dataclass
class Secret:
    """Represents a secret in the Secret Store."""

    id: str
    user_id: str
    secret_name: str
    vault_path: str
    value: str
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        user_id: str,
        secret_name: str,
        vault_path: str,
        value: str,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Secret":
        """Create a new secret."""
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            secret_name=secret_name,
            vault_path=vault_path,
            value=value,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    def update(self, value: str, metadata: Optional[Dict[str, Any]] = None) -> "Secret":
        """Update an existing secret."""
        self.value = value
        self.updated_at = datetime.utcnow()
        if metadata:
            self.metadata.update(metadata)
        return self

    def is_expired(self) -> bool:
        """Check if the secret has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert secret to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "secret_name": self.secret_name,
            "vault_path": self.vault_path,
            "value": self.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }


@dataclass
class SecretAccessRequest:
    """Represents a request to access a secret."""

    session_id: str
    secret_name: str
    user_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    operation: SecretOperation = SecretOperation.READ
    idempotency_key: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecretAccessRequest":
        """Create a request from a dictionary."""
        return cls(
            session_id=data["session_id"],
            secret_name=data["secret_name"],
            user_id=data.get("user_id", ""),
            context=data.get("context", {}),
            operation=SecretOperation(data.get("operation", "read")),
            idempotency_key=data.get("idempotency_key"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary."""
        return {
            "session_id": self.session_id,
            "secret_name": self.secret_name,
            "user_id": self.user_id,
            "context": self.context,
            "operation": self.operation.value,
            "idempotency_key": self.idempotency_key,
        }


@dataclass
class SecretAccessResponse:
    """Represents the response to a secret access request."""

    value: str
    expires_at: Optional[datetime] = None
    vault_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        value: str,
        vault_path: str,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SecretAccessResponse":
        """Create a response."""
        return cls(
            value=value,
            vault_path=vault_path,
            expires_at=expires_at,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "value": self.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "vault_path": self.vault_path,
            "metadata": self.metadata,
        }


@dataclass
class AuditLogEntry:
    """Represents an audit log entry."""

    id: str
    user_id: str
    secret_name: str
    operation: SecretOperation
    vault_path: str
    session_id: str
    build_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        user_id: str,
        secret_name: str,
        operation: SecretOperation,
        vault_path: str,
        session_id: str,
        build_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> "AuditLogEntry":
        """Create a new audit log entry."""
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            secret_name=secret_name,
            operation=operation,
            vault_path=vault_path,
            session_id=session_id,
            build_id=build_id,
            success=success,
            error_message=error_message,
            timestamp=datetime.utcnow(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log entry to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "secret_name": self.secret_name,
            "operation": self.operation.value,
            "vault_path": self.vault_path,
            "session_id": self.session_id,
            "build_id": self.build_id,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class SecretMetadata:
    """Metadata for a secret."""

    secret_name: str
    vault_path: str
    secret_type: SecretType
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "secret_name": self.secret_name,
            "vault_path": self.vault_path,
            "secret_type": self.secret_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "version": self.version,
        }
