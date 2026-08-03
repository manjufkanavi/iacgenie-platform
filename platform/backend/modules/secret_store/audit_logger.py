"""Audit logging for secret access."""

import json

import re

from datetime import datetime

from typing import Dict, Any, Optional

from .config import SecretStoreConfig


class AuditLogger:
    """Logs secret access with redaction."""

    def __init__(self, config: SecretStoreConfig):
        """
        Initialize the AuditLogger.
        Args:
            config: SecretStoreConfig instance.
        """
        self.config = config
        self.log_file = config.audit_log_file
        self._secret_patterns = config.redact_patterns

    def _redact_secrets(self, message: str) -> str:
        """Redact sensitive information from log messages."""
        redacted = message
        for pattern in self._secret_patterns:
            redacted = re.sub(
                rf'({pattern})\s*[:=]\s*[^"\'\s,}}]+',
                r"\1=[REDACTED]",
                redacted,
                flags=re.IGNORECASE,
            )
        return redacted

    def _build_log_entry(
        self,
        user_id: str,
        secret_name: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: str = "",
        build_id: Optional[str] = None,
        vault_path: str = "",
    ) -> Dict[str, Any]:
        """Build a log entry dictionary."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id,
            "secret_name": secret_name,
            "operation": operation,
            "success": success,
            "session_id": session_id,
            "vault_path": vault_path,
        }
        if build_id:
            entry["build_id"] = build_id
        if metadata:
            entry["metadata"] = self._redact_secrets(json.dumps(metadata))
        if error_message:
            entry["error_message"] = self._redact_secrets(error_message)
        return entry

    def log_secret_access(
        self,
        user_id: str,
        secret_name: str,
        operation: str,
        session_id: str = "",
        build_id: Optional[str] = None,
        repo_url: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log secret access with redaction.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            operation: The operation performed.
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
            repo_url: Repository URL for context.
            success: Whether the operation succeeded.
            error_message: Error message if operation failed.
        """
        metadata = {}
        if repo_url:
            metadata["repo_url"] = repo_url
        log_entry = self._build_log_entry(
            user_id=user_id,
            secret_name=secret_name,
            operation=operation,
            metadata=metadata,
            success=success,
            error_message=error_message,
            session_id=session_id,
            build_id=build_id,
        )
        self._write_log_entry(log_entry)

    def log_secret_create(
        self,
        user_id: str,
        secret_name: str,
        secret_type: str,
        session_id: str = "",
        build_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log secret creation.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            secret_type: Type of secret.
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
            success: Whether the operation succeeded.
            error_message: Error message if operation failed.
        """
        metadata = {"secret_type": secret_type}
        log_entry = self._build_log_entry(
            user_id=user_id,
            secret_name=secret_name,
            operation="create",
            metadata=metadata,
            success=success,
            error_message=error_message,
            session_id=session_id,
            build_id=build_id,
        )
        self._write_log_entry(log_entry)

    def log_secret_update(
        self,
        user_id: str,
        secret_name: str,
        session_id: str = "",
        build_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log secret update.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
            success: Whether the operation succeeded.
            error_message: Error message if operation failed.
        """
        log_entry = self._build_log_entry(
            user_id=user_id,
            secret_name=secret_name,
            operation="update",
            metadata={},
            success=success,
            error_message=error_message,
            session_id=session_id,
            build_id=build_id,
        )
        self._write_log_entry(log_entry)

    def log_secret_delete(
        self,
        user_id: str,
        secret_name: str,
        session_id: str = "",
        build_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log secret deletion.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
            success: Whether the operation succeeded.
            error_message: Error message if operation failed.
        """
        log_entry = self._build_log_entry(
            user_id=user_id,
            secret_name=secret_name,
            operation="delete",
            metadata={},
            success=success,
            error_message=error_message,
            session_id=session_id,
            build_id=build_id,
        )
        self._write_log_entry(log_entry)

    def log_token_generation(
        self,
        user_id: str,
        secret_name: str,
        ttl_minutes: int,
        session_id: str = "",
        build_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log token generation.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            ttl_minutes: Token TTL in minutes.
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
            success: Whether the operation succeeded.
            error_message: Error message if operation failed.
        """
        metadata = {"ttl_minutes": ttl_minutes}
        log_entry = self._build_log_entry(
            user_id=user_id,
            secret_name=secret_name,
            operation="token_generation",
            metadata=metadata,
            success=success,
            error_message=error_message,
            session_id=session_id,
            build_id=build_id,
        )
        self._write_log_entry(log_entry)

    def log_secret_revoke(
        self,
        user_id: str,
        secret_name: str,
        token_value: str,
        session_id: str = "",
        build_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log token revocation.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            token_value: The token value (will be redacted).
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
            success: Whether the operation succeeded.
            error_message: Error message if operation failed.
        """
        metadata = {"token_hash": hash(token_value)}
        log_entry = self._build_log_entry(
            user_id=user_id,
            secret_name=secret_name,
            operation="token_revocation",
            metadata=metadata,
            success=success,
            error_message=error_message,
            session_id=session_id,
            build_id=build_id,
        )
        self._write_log_entry(log_entry)

    def _write_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """
        Write a log entry to the audit log file.
        Args:
            log_entry: The log entry dictionary.
        """
        try:
            # Ensure log directory exists
            import os

            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            # Write log entry
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            # Don't raise errors during logging to avoid cascading failures
            import logging

            logging.error(f"Failed to write audit log entry: {e}")
