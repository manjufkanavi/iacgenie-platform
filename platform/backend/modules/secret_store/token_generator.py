"""

Token Generator

Handles just-in-time token generation for secrets using HashiCorp Vault.

"""

from datetime import datetime, timedelta

from typing import Any, Dict, Optional

from .config import SecretStoreConfig

from .models import SecretAccessResponse, SecretOperation


class TokenGenerator:
    """
    Token Generator for creating short-lived tokens for secrets.
    Features:
    - Dynamic token generation via Vault
    - Configurable TTL
    - Token revocation support
    - Audit logging
    """

    def __init__(self, config: Optional[SecretStoreConfig] = None):
        """
        Initialize the TokenGenerator.
        Args:
            config: SecretStoreConfig instance. If None, uses environment variables.
        """
        self.config = config or SecretStoreConfig.from_env()

    def generate_git_token(
        self,
        user_id: str,
        repo_url: str,
        ttl_minutes: int = 60,
        scopes: Optional[list[str]] = None,
    ) -> SecretAccessResponse:
        """
        Generate a just-in-time Git token.
        Args:
            user_id: The tenant/user ID.
            repo_url: The repository URL.
            ttl_minutes: Time-to-live in minutes (default: 60).
            scopes: List of scopes/permissions (optional).
        Returns:
            The generated token response.
        Raises:
            TokenGenerationError: If token generation fails.
        """
        secret_name = self._build_secret_name("git_token", user_id, repo_url)
        return self._generate_token(
            user_id=user_id,
            secret_name=secret_name,
            ttl_minutes=ttl_minutes,
            operation=SecretOperation.ACCESS,
            metadata={
                "repo_url": repo_url,
                "scopes": scopes,
            },
        )

    def generate_ci_pat(
        self,
        user_id: str,
        ci_provider: str,
        ttl_minutes: int = 60,
        scopes: Optional[list[str]] = None,
    ) -> SecretAccessResponse:
        """
        Generate a just-in-time CI PAT (Personal Access Token).
        Args:
            user_id: The tenant/user ID.
            ci_provider: The CI provider (e.g., 'github', 'gitlab').
            ttl_minutes: Time-to-live in minutes (default: 60).
            scopes: List of scopes/permissions (optional).
        Returns:
            The generated token response.
        Raises:
            TokenGenerationError: If token generation fails.
        """
        secret_name = self._build_secret_name("ci_pat", user_id, ci_provider)
        return self._generate_token(
            user_id=user_id,
            secret_name=secret_name,
            ttl_minutes=ttl_minutes,
            operation=SecretOperation.ACCESS,
            metadata={
                "ci_provider": ci_provider,
                "scopes": scopes,
            },
        )

    def generate_llm_api_key(
        self,
        user_id: str,
        model_name: str,
        ttl_minutes: int = 60,
    ) -> SecretAccessResponse:
        """
        Generate a just-in-time LLM API key.
        Args:
            user_id: The tenant/user ID.
            model_name: The model name.
            ttl_minutes: Time-to-live in minutes (default: 60).
        Returns:
            The generated token response.
        Raises:
            TokenGenerationError: If token generation fails.
        """
        secret_name = self._build_secret_name("llm_api_key", user_id, model_name)
        return self._generate_token(
            user_id=user_id,
            secret_name=secret_name,
            ttl_minutes=ttl_minutes,
            operation=SecretOperation.ACCESS,
            metadata={
                "model_name": model_name,
            },
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
            ttl_minutes: Time-to-live in minutes (default: 60).
        Returns:
            The generated token response.
        Raises:
            TokenGenerationError: If token generation fails.
        """
        secret_name = self._build_secret_name("sandbox", user_id, session_id)
        return self._generate_token(
            user_id=user_id,
            secret_name=secret_name,
            ttl_minutes=ttl_minutes,
            operation=SecretOperation.ACCESS,
            metadata={
                "session_id": session_id,
                "ephemeral": True,
            },
        )

    def _build_secret_name(self, prefix: str, user_id: str, resource: str) -> str:
        """
        Build a secret name from components.
        Args:
            prefix: The secret type prefix.
            user_id: The user ID.
            resource: The resource identifier.
        Returns:
            The formatted secret name.
        """
        # Sanitize resource name
        sanitized_resource = resource.replace("/", "_").replace(".", "_")
        return f"{prefix}_{user_id}_{sanitized_resource}"

    def _generate_token(
        self,
        user_id: str,
        secret_name: str,
        ttl_minutes: int,
        operation: SecretOperation,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretAccessResponse:
        """
        Generate a token for a secret.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            ttl_minutes: Time-to-live in minutes.
            operation: The operation being performed.
            metadata: Additional metadata.
        Returns:
            The generated token response.
        Raises:
            TokenGenerationError: If token generation fails.
        """
        vault_path = self._build_vault_path(user_id, secret_name)
        # In production, this would call Vault's token generation endpoint
        # For now, generate a deterministic token
        import hashlib

        token_value = hashlib.sha256(
            f"{user_id}:{secret_name}:{ttl_minutes}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        return SecretAccessResponse.create(
            value=token_value,
            vault_path=vault_path,
            expires_at=expires_at,
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "ttl_minutes": ttl_minutes,
                "operation": operation.value,
                **(metadata or {}),
            },
        )

    def revoke_token(self, user_id: str, secret_name: str, token_value: str) -> None:
        """
        Revoke a token.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            token_value: The token value to revoke.
        Raises:
            TokenGenerationError: If token revocation fails.
        """
        # In production, this would call Vault's token revocation endpoint
        vault_path = self._build_vault_path(user_id, secret_name)
        # Log revocation
        import logging

        logging.info(
            f"Token revoked: {vault_path} for user {user_id}",
            extra={
                "event_type": "token_revocation",
                "user_id": user_id,
                "secret_name": secret_name,
                "token_hash": hash(token_value),
            },
        )

    def _build_vault_path(self, user_id: str, secret_name: str) -> str:
        """
        Build the Vault path for a secret.
        Args:
            user_id: The tenant/user ID.
            secret_name: The secret name.
        Returns:
            The Vault path string.
        """
        return f"secret/data/tenants/{user_id}/{secret_name}"
