"""

Secret Store Service

Business logic orchestration for the Secret Store module.

"""

from typing import Optional

from .config import SecretStoreConfig

from .exceptions import (
    SecretValidationError,
    TenantIdMissingError,
)

from .models import (
    SecretAccessRequest,
    SecretAccessResponse,
    SecretOperation,
    SecretMetadata,
)

from .secret_manager import SecretManager

from .audit_logger import AuditLogger

from .token_generator import TokenGenerator

from .observability import (
    trace_secret_access,
    record_secret_access_metric,
)


class SecretStoreService:
    """
    Secret Store Service - orchestrates secret operations.
    Features:
    - Secret CRUD operations
    - Just-in-time token generation
    - Audit logging
    - Observability integration
    """

    def __init__(self, config: Optional[SecretStoreConfig] = None) -> None:
        """
        Initialize the SecretStoreService.
        Args:
            config: SecretStoreConfig instance. If None, uses environment variables.
        """
        self.config = config or SecretStoreConfig.from_env()
        self.secret_manager = SecretManager(self.config)
        self.audit_logger = AuditLogger(self.config)
        self.token_generator = TokenGenerator(self.config)

    @trace_secret_access
    def get_secret(
        self,
        user_id: str,
        secret_name: str,
        session_id: str,
        build_id: Optional[str] = None,
        repo_url: Optional[str] = None,
        operation: SecretOperation = SecretOperation.ACCESS,
    ) -> SecretAccessResponse:
        """
        Get a secret value.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
            repo_url: Repository URL for context.
            operation: The operation being performed.
        Returns:
            The secret value with metadata.
        Raises:
            SecretNotFoundError: If the secret is not found.
            SecretAccessError: If access to the secret is denied.
        """
        # Validate inputs
        self._validate_inputs(user_id, secret_name, session_id)
        # Get the secret
        response = self.secret_manager.get_secret(
            request=SecretAccessRequest(
                session_id=session_id,
                secret_name=secret_name,
                user_id=user_id,
                context={
                    "build_id": build_id,
                    "repo_url": repo_url,
                }
                if build_id or repo_url
                else {},
                operation=operation,
            )
        )
        # Audit log
        self.audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=secret_name,
            operation=operation.value,
            session_id=session_id,
            build_id=build_id,
            repo_url=repo_url,
            success=True,
        )
        # Record metrics
        record_secret_access_metric(
            user_id=user_id,
            secret_name=secret_name,
            operation=operation.value,
            success=True,
        )
        return response

    @trace_secret_access
    def store_secret(
        self,
        user_id: str,
        secret_name: str,
        secret_value: str,
        secret_type: str = "generic",
        ttl_minutes: int = 60,
        session_id: str = "",
        build_id: Optional[str] = None,
    ) -> SecretAccessResponse:
        """
        Store a new secret.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            secret_value: The secret value to store.
            secret_type: Type of secret (default: 'generic').
            ttl_minutes: Token TTL in minutes (default: 60).
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
        Returns:
            The stored secret response.
        Raises:
            SecretValidationError: If the secret value is invalid.
            SecretAccessError: If storage fails.
        """
        # Validate inputs
        self._validate_inputs(user_id, secret_name, session_id)
        # Validate secret value
        self._validate_secret_value(secret_value, secret_type)
        # Store the secret
        response = self.secret_manager.store_secret(
            tenant_id=user_id,
            secret_name=secret_name,
            secret_value=secret_value,
            secret_type=secret_type,
            ttl_minutes=ttl_minutes,
        )
        # Audit log
        self.audit_logger.log_secret_create(
            user_id=user_id,
            secret_name=secret_name,
            secret_type=secret_type,
            session_id=session_id,
            success=True,
        )
        # Record metrics
        record_secret_access_metric(
            user_id=user_id,
            secret_name=secret_name,
            operation=SecretOperation.CREATE.value,
            success=True,
        )
        return response

    @trace_secret_access
    def rotate_secret(
        self,
        user_id: str,
        secret_name: str,
        ttl_minutes: int = 60,
        session_id: str = "",
        build_id: Optional[str] = None,
    ) -> SecretAccessResponse:
        """
        Rotate a secret.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret to rotate.
            ttl_minutes: New token TTL in minutes (default: 60).
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
        Returns:
            The rotated secret response.
        Raises:
            SecretNotFoundError: If the secret is not found.
            SecretAccessError: If rotation fails.
        """
        # Validate inputs
        self._validate_inputs(user_id, secret_name, session_id)
        # Rotate the secret
        response = self.secret_manager.rotate_secret(
            tenant_id=user_id,
            secret_name=secret_name,
            ttl_minutes=ttl_minutes,
        )
        # Audit log
        self.audit_logger.log_secret_update(
            user_id=user_id,
            secret_name=secret_name,
            session_id=session_id,
            success=True,
        )
        # Record metrics
        record_secret_access_metric(
            user_id=user_id,
            secret_name=secret_name,
            operation=SecretOperation.UPDATE.value,
            success=True,
        )
        return response

    @trace_secret_access
    def delete_secret(
        self,
        user_id: str,
        secret_name: str,
        session_id: str = "",
        build_id: Optional[str] = None,
    ) -> None:
        """
        Delete a secret.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret to delete.
            session_id: Session ID for tracing.
            build_id: Build ID for tracing.
        Raises:
            SecretNotFoundError: If the secret is not found.
            SecretAccessError: If deletion fails.
        """
        # Validate inputs
        self._validate_inputs(user_id, secret_name, session_id)
        # Delete the secret
        self.secret_manager.delete_secret(
            tenant_id=user_id,
            secret_name=secret_name,
        )
        # Audit log
        self.audit_logger.log_secret_delete(
            user_id=user_id,
            secret_name=secret_name,
            session_id=session_id,
            success=True,
        )
        # Record metrics
        record_secret_access_metric(
            user_id=user_id,
            secret_name=secret_name,
            operation=SecretOperation.DELETE.value,
            success=True,
        )

    def generate_git_token(
        self,
        user_id: str,
        repo_url: str,
        ttl_minutes: int = 60,
        scopes: Optional[list[str]] = None,
        session_id: str = "",
    ) -> SecretAccessResponse:
        """
        Generate a just-in-time Git token.
        Args:
            user_id: The tenant/user ID.
            repo_url: The repository URL.
            ttl_minutes: Token TTL in minutes (default: 60).
            scopes: List of scopes/permissions (optional).
            session_id: Session ID for tracing.
        Returns:
            The generated token response.
        """
        return self.token_generator.generate_git_token(
            user_id=user_id,
            repo_url=repo_url,
            ttl_minutes=ttl_minutes,
            scopes=scopes,
        )

    def generate_ci_pat(
        self,
        user_id: str,
        ci_provider: str,
        ttl_minutes: int = 60,
        scopes: Optional[list[str]] = None,
        session_id: str = "",
    ) -> SecretAccessResponse:
        """
        Generate a just-in-time CI PAT.
        Args:
            user_id: The tenant/user ID.
            ci_provider: The CI provider (e.g., 'github', 'gitlab').
            ttl_minutes: Token TTL in minutes (default: 60).
            scopes: List of scopes/permissions (optional).
            session_id: Session ID for tracing.
        Returns:
            The generated token response.
        """
        return self.token_generator.generate_ci_pat(
            user_id=user_id,
            ci_provider=ci_provider,
            ttl_minutes=ttl_minutes,
            scopes=scopes,
        )

    def generate_llm_api_key(
        self,
        user_id: str,
        model_name: str,
        ttl_minutes: int = 60,
        session_id: str = "",
    ) -> SecretAccessResponse:
        """
        Generate a just-in-time LLM API key.
        Args:
            user_id: The tenant/user ID.
            model_name: The model name.
            ttl_minutes: Token TTL in minutes (default: 60).
            session_id: Session ID for tracing.
        Returns:
            The generated token response.
        """
        return self.token_generator.generate_llm_api_key(
            user_id=user_id,
            model_name=model_name,
            ttl_minutes=ttl_minutes,
        )

    def generate_sandbox_credentials(
        self,
        user_id: str,
        session_id: str,
        ttl_minutes: int = 60,
    ) -> SecretAccessResponse:
        """
        Generate ephemeral credentials for sandbox execution.
        Args:
            user_id: The tenant/user ID.
            session_id: The session ID.
            ttl_minutes: Token TTL in minutes (default: 60).
        Returns:
            The generated token response.
        """
        return self.token_generator.generate_sandbox_credentials(
            user_id=user_id,
            session_id=session_id,
            ttl_minutes=ttl_minutes,
        )

    def _validate_inputs(
        self,
        user_id: str,
        secret_name: str,
        session_id: str,
    ) -> None:
        """
        Validate input parameters.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            session_id: Session ID.
        Raises:
            TenantIdMissingError: If user_id is missing.
            SecretValidationError: If validation fails.
        """
        if not user_id:
            raise TenantIdMissingError()
        if not secret_name:
            raise SecretValidationError("Secret name is required")
        if not session_id:
            raise SecretValidationError("Session ID is required")

    def _validate_secret_value(
        self,
        secret_value: str,
        secret_type: str,
    ) -> None:
        """
        Validate secret value.
        Args:
            secret_value: The secret value.
            secret_type: The type of secret.
        Raises:
            SecretValidationError: If validation fails.
        """
        # Check secret size
        max_size = self.config.max_secret_size_bytes
        if len(secret_value.encode("utf-8")) > max_size:
            raise SecretValidationError(
                f"Secret value exceeds maximum size of {max_size} bytes"
            )
        # Check for sensitive keywords in secret value (security)
        if "password" in secret_value.lower() or "secret" in secret_value.lower():
            raise SecretValidationError(
                "Secret value must not contain sensitive keywords"
            )

    def get_secret_metadata(
        self,
        user_id: str,
        secret_name: str,
        session_id: str = "",
    ) -> SecretMetadata:
        """
        Get secret metadata without the value.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            session_id: Session ID for tracing.
        Returns:
            The secret metadata.
        Raises:
            SecretNotFoundError: If the secret is not found.
        """
        return self.secret_manager.get_secret_metadata(
            tenant_id=user_id,
            secret_name=secret_name,
        )

    def list_secrets(
        self,
        user_id: str,
        session_id: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[SecretMetadata]:
        """
        List secrets for a user.
        Args:
            user_id: The tenant/user ID.
            session_id: Session ID for tracing.
            limit: Maximum number of secrets to return.
            offset: Offset for pagination.
        Returns:
            List of secret metadata.
        """
        return self.secret_manager.list_secrets_paginated(
            tenant_id=user_id,
            limit=limit,
            offset=offset,
        )
