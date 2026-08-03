"""

Secret Manager

Handles secret lifecycle operations (create, read, update, delete) for the Secret Store.

"""

from datetime import datetime, timedelta

from typing import Any, Dict, Optional

from uuid import uuid4

from .config import SecretStoreConfig

from .exceptions import (
    SecretNotFoundError,
    SecretAlreadyExistsError,
    SecretTooLargeError,
)

from .models import (
    Secret,
    SecretMetadata,
    SecretAccessRequest,
    SecretAccessResponse,
    SecretType,
)

from .vault_client import VaultClient


class SecretManager:
    """
    Secret Manager for handling secret lifecycle operations.
    Provides CRUD operations for secrets while enforcing:
    - Secret size limits
    - Expiration policies
    - Audit logging
    - Vault integration
    """

    def __init__(self, config: Optional[SecretStoreConfig] = None):
        """
        Initialize the SecretManager.
        Args:
            config: SecretStoreConfig instance. If None, uses environment variables.
        """
        self.config = config or SecretStoreConfig.from_env()
        self.vault_client = VaultClient(self.config)

    def create_secret(
        self,
        tenant_id: str,
        secret_name: str,
        value: str,
        secret_type: str = "generic",
        metadata: Optional[Dict[str, Any]] = None,
        ttl_minutes: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> Secret:
        """
        Create a new secret.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret.
            value: The secret value.
            secret_type: Type of secret (git_token, ci_pat, llm_api_key, etc.).
            metadata: Additional metadata.
            ttl_minutes: Time-to-live in minutes (optional).
            provider: Cloud provider context (aws, gcp, azure).
        Returns:
            The created Secret object.
        Raises:
            SecretTooLargeError: If the secret exceeds maximum size.
            SecretAlreadyExistsError: If the secret already exists.
        """
        # Validate secret size
        if len(value.encode("utf-8")) > self.config.max_secret_size_bytes:
            raise SecretTooLargeError(
                secret_name=secret_name,
                user_id=tenant_id,
                size=len(value.encode("utf-8")),
                max_size=self.config.max_secret_size_bytes,
            )
        # Check if secret already exists
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        try:
            self.vault_client.read_secret(vault_path)
            raise SecretAlreadyExistsError(secret_name=secret_name, user_id=tenant_id)
        except SecretNotFoundError:
            pass  # Secret doesn't exist, proceed with creation
        # Generate expires_at if TTL provided
        expires_at = None
        if ttl_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        # Create secret
        secret = Secret.create(
            user_id=tenant_id,
            secret_name=secret_name,
            vault_path=vault_path,
            value=value,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        # Write to Vault
        secret_data = {
            "data": {
                "value": secret.value,
                "created_at": secret.created_at.isoformat()
                if secret.created_at
                else None,
                "expires_at": secret.expires_at.isoformat()
                if secret.expires_at
                else None,
                "metadata": secret.metadata,
                "provider": provider,
            },
        }
        self.vault_client.write_secret(vault_path, secret_data)
        return secret

    def read_secret(
        self, tenant_id: str, secret_name: str, provider: Optional[str] = None
    ) -> Secret:
        """
        Read a secret from Vault.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret.
            provider: Cloud provider context (aws, gcp, azure).
        Returns:
            The Secret object.
        Raises:
            SecretNotFoundError: If the secret doesn't exist.
        """
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        vault_data = self.vault_client.read_secret(vault_path)
        data = vault_data.get("data", {})
        return Secret(
            id=str(uuid4()),
            user_id=tenant_id,
            secret_name=secret_name,
            vault_path=vault_path,
            value=data.get("value", ""),
            created_at=datetime.fromisoformat(data.get("created_at"))
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data.get("updated_at"))
            if data.get("updated_at")
            else None,
            expires_at=datetime.fromisoformat(data.get("expires_at"))
            if data.get("expires_at")
            else None,
            metadata=data.get("metadata", {}),
        )

    def update_secret(
        self,
        tenant_id: str,
        secret_name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> Secret:
        """
        Update an existing secret.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret.
            value: The new secret value.
            metadata: Additional metadata to update.
            provider: Cloud provider context.
        Returns:
            The updated Secret object.
        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretTooLargeError: If the secret exceeds maximum size.
        """
        # Validate secret size
        if len(value.encode("utf-8")) > self.config.max_secret_size_bytes:
            raise SecretTooLargeError(
                secret_name=secret_name,
                user_id=tenant_id,
                size=len(value.encode("utf-8")),
                max_size=self.config.max_secret_size_bytes,
            )
        # Read existing secret
        secret = self.read_secret(tenant_id, secret_name, provider)
        # Update secret
        secret.update(value, metadata)
        # Write to Vault
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        secret_data = {
            "data": {
                "value": secret.value,
                "created_at": secret.created_at.isoformat()
                if secret.created_at
                else None,
                "expires_at": secret.expires_at.isoformat()
                if secret.expires_at
                else None,
                "metadata": secret.metadata,
                "provider": provider,
                "updated_at": secret.updated_at.isoformat()
                if secret.updated_at
                else None,
            },
        }
        self.vault_client.write_secret(vault_path, secret_data)
        return secret

    def delete_secret(
        self, tenant_id: str, secret_name: str, provider: Optional[str] = None
    ) -> None:
        """
        Delete a secret from Vault.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret.
            provider: Cloud provider context.
        Raises:
            SecretNotFoundError: If the secret doesn't exist.
        """
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        self.vault_client.delete_secret(vault_path)

    def get_secret(self, request: SecretAccessRequest) -> SecretAccessResponse:
        """
        Get a secret based on an access request.
        Args:
            request: The secret access request.
        Returns:
            The secret access response with the secret value.
        Raises:
            SecretNotFoundError: If the secret doesn't exist.
        """
        # Read secret from Vault
        provider = request.context.get("provider") if request.context else None
        vault_path = self._build_vault_path(
            request.user_id, request.secret_name, provider
        )
        vault_data = self.vault_client.read_secret(vault_path)
        data = vault_data.get("data", {})
        secret_value = data.get("value", "")
        # Check if secret has expired
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                raise SecretNotFoundError(
                    secret_name=request.secret_name, user_id=request.user_id
                )
        return SecretAccessResponse.create(
            value=secret_value,
            vault_path=vault_path,
            expires_at=expires_at,
            metadata={
                "operation": request.operation.value,
                "session_id": request.session_id,
            },
        )

    def generate_token(
        self,
        tenant_id: str,
        secret_name: str,
        ttl_minutes: int = 60,
        provider: Optional[str] = None,
    ) -> SecretAccessResponse:
        """
        Generate a just-in-time token for a secret.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret.
            ttl_minutes: Time-to-live in minutes (default: 60).
            provider: Cloud provider context.
        Returns:
            The generated token response.
        """
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        # Generate token with Vault
        ttl_seconds = ttl_minutes * 60
        token_data = self.vault_client.generate_token(secret_name, ttl=ttl_seconds)
        data = token_data.get("data", {})
        token_value = data.get("token", "")
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        return SecretAccessResponse.create(
            value=token_value,
            vault_path=vault_path,
            expires_at=expires_at,
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "ttl_minutes": ttl_minutes,
                "operation": "generate",
            },
        )

    def list_secrets(
        self, tenant_id: str, provider: Optional[str] = None
    ) -> list[SecretMetadata]:
        """
        List all secrets for a tenant, optionally scoped to a cloud provider.
        Args:
            tenant_id: The tenant ID.
            provider: Cloud provider context (optional). If None, lists all secrets for tenant.
        Returns:
            A list of secret metadata.
        """
        vault_path = self._build_vault_path(tenant_id, "", provider)
        keys = self.vault_client.list_secrets(vault_path)
        secrets = []
        for secret_name in keys:
            metadata = SecretMetadata(
                secret_name=secret_name,
                vault_path=self._build_vault_path(tenant_id, secret_name, provider),
                secret_type=SecretType.GENERIC,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            secrets.append(metadata)
        return secrets

    def _build_vault_path(
        self, tenant_id: str, secret_name: str, provider: Optional[str] = None
    ) -> str:
        """
        Build the Vault path for a secret with tenant and cloud provider isolation.
        Path format: iacgenie/tenants/{tenant_id}/clouds/{provider}/{secret_name}
        When provider is None: iacgenie/tenants/{tenant_id}/{secret_name}
        Args:
            tenant_id: The tenant ID.
            secret_name: The secret name.
            provider: Cloud provider (aws, gcp, azure).
        Returns:
            The Vault path string.
        """
        if provider:
            if secret_name:
                return f"iacgenie/tenants/{tenant_id}/clouds/{provider}/{secret_name}"
            return f"iacgenie/tenants/{tenant_id}/clouds/{provider}/"
        if secret_name:
            return f"iacgenie/tenants/{tenant_id}/{secret_name}"
        return f"iacgenie/tenants/{tenant_id}/"

    def store_secret(
        self,
        tenant_id: str,
        secret_name: str,
        secret_value: str,
        secret_type: str = "generic",
        ttl_minutes: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> SecretAccessResponse:
        """
        Store a new secret.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret.
            secret_value: The secret value to store.
            secret_type: Type of secret (default: 'generic').
            ttl_minutes: Time-to-live in minutes (optional).
            metadata: Additional metadata (optional).
            provider: Cloud provider context.
        Returns:
            The stored secret response.
        Raises:
            SecretTooLargeError: If the secret exceeds maximum size.
            SecretAlreadyExistsError: If the secret already exists.
        """
        # Validate secret size
        if len(secret_value.encode("utf-8")) > self.config.max_secret_size_bytes:
            raise SecretTooLargeError(
                secret_name=secret_name,
                user_id=tenant_id,
                size=len(secret_value.encode("utf-8")),
                max_size=self.config.max_secret_size_bytes,
            )
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        # Check if secret already exists
        try:
            self.vault_client.read_secret(vault_path)
            raise SecretAlreadyExistsError(secret_name=secret_name, user_id=tenant_id)
        except SecretNotFoundError:
            pass  # Secret doesn't exist, proceed with storage
        # Generate expires_at if TTL provided
        expires_at = None
        if ttl_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        # Create secret
        secret = Secret.create(
            user_id=tenant_id,
            secret_name=secret_name,
            vault_path=vault_path,
            value=secret_value,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        # Write to Vault
        secret_data = {
            "data": {
                "value": secret.value,
                "created_at": secret.created_at.isoformat()
                if secret.created_at
                else None,
                "expires_at": secret.expires_at.isoformat()
                if secret.expires_at
                else None,
                "metadata": secret.metadata,
                "secret_type": secret_type,
                "provider": provider,
            },
        }
        self.vault_client.write_secret(vault_path, secret_data)
        return SecretAccessResponse.create(
            value=secret.value,
            vault_path=vault_path,
            expires_at=expires_at,
            metadata={
                "secret_type": secret_type,
                "created_at": secret.created_at.isoformat()
                if secret.created_at
                else None,
                "operation": "store",
            },
        )

    def rotate_secret(
        self,
        tenant_id: str,
        secret_name: str,
        ttl_minutes: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> SecretAccessResponse:
        """
        Rotate a secret.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret to rotate.
            ttl_minutes: New token TTL in minutes (optional).
            provider: Cloud provider context.
        Returns:
            The rotated secret response.
        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretTooLargeError: If the new secret exceeds maximum size.
        """
        # Read existing secret
        secret = self.read_secret(tenant_id, secret_name, provider)
        # Generate new secret value
        import secrets

        new_value = secrets.token_urlsafe(32)
        # Validate secret size
        if len(new_value.encode("utf-8")) > self.config.max_secret_size_bytes:
            raise SecretTooLargeError(
                secret_name=secret_name,
                user_id=tenant_id,
                size=len(new_value.encode("utf-8")),
                max_size=self.config.max_secret_size_bytes,
            )
        # Update secret
        secret.update(new_value)
        # Generate expires_at if TTL provided
        expires_at = None
        if ttl_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        secret.expires_at = expires_at
        # Write to Vault
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        secret_data = {
            "data": {
                "value": secret.value,
                "created_at": secret.created_at.isoformat()
                if secret.created_at
                else None,
                "expires_at": secret.expires_at.isoformat()
                if secret.expires_at
                else None,
                "metadata": secret.metadata,
                "provider": provider,
                "updated_at": secret.updated_at.isoformat()
                if secret.updated_at
                else None,
            },
        }
        self.vault_client.write_secret(vault_path, secret_data)
        return SecretAccessResponse.create(
            value=new_value,
            vault_path=vault_path,
            expires_at=expires_at,
            metadata={
                "secret_name": secret_name,
                "operation": "rotate",
                "rotated_at": secret.updated_at.isoformat()
                if secret.updated_at
                else None,
            },
        )

    def get_secret_metadata(
        self, tenant_id: str, secret_name: str, provider: Optional[str] = None
    ) -> SecretMetadata:
        """
        Get secret metadata without the value.
        Args:
            tenant_id: The tenant ID.
            secret_name: The name of the secret.
            provider: Cloud provider context.
        Returns:
            The secret metadata.
        Raises:
            SecretNotFoundError: If the secret doesn't exist.
        """
        vault_path = self._build_vault_path(tenant_id, secret_name, provider)
        vault_data = self.vault_client.get_secret_metadata(vault_path)
        data = vault_data.get("data", {})
        created_at_str = data.get("created_at")
        updated_at_str = data.get("updated_at")
        expires_at_str = data.get("expires_at")
        created_at = (
            datetime.fromisoformat(created_at_str)
            if created_at_str
            else datetime.utcnow()
        )
        updated_at = (
            datetime.fromisoformat(updated_at_str)
            if updated_at_str
            else datetime.utcnow()
        )
        expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None
        return SecretMetadata(
            secret_name=secret_name,
            vault_path=vault_path,
            secret_type=SecretType(data.get("secret_type", "generic")),
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
            version=data.get("version", 1),
        )

    def delete_secret_by_path(self, vault_path: str) -> None:
        """
        Delete a secret by Vault path.
        Args:
            vault_path: The Vault path to delete.
        Raises:
            VaultConnectionError: If the connection fails.
        """
        self.vault_client.delete_secret(vault_path)

    def list_secrets_paginated(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        provider: Optional[str] = None,
    ) -> list[SecretMetadata]:
        """
        List secrets for a tenant with pagination.
        Args:
            tenant_id: The tenant ID.
            limit: Maximum number of secrets to return.
            offset: Offset for pagination.
            provider: Cloud provider context.
        Returns:
            A list of secret metadata.
        """
        vault_path = self._build_vault_path(tenant_id, "", provider)
        all_keys = self.vault_client.list_secrets(vault_path)
        paginated_keys = all_keys[offset : offset + limit]
        secrets = []
        for secret_name in paginated_keys:
            metadata = SecretMetadata(
                secret_name=secret_name,
                vault_path=self._build_vault_path(tenant_id, secret_name, provider),
                secret_type=SecretType.GENERIC,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            secrets.append(metadata)
        return secrets
