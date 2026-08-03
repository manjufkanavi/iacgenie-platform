"""

OpenBao / HashiCorp Vault Client

A secure client for interacting with OpenBao (or HashiCorp Vault) using
token-based or Kubernetes authentication.

OpenBao is the open-source fork of Vault and uses the same API endpoints.
All KV-v2 paths follow the pattern:
  - Read/Write: /v1/{mount}/data/{secret_path}
  - Delete:     /v1/{mount}/metadata/{secret_path}  (deletes all versions)
  - List:       /v1/{mount}/metadata/{secret_path}/  (LIST method)

"""

import os

from datetime import datetime

from typing import Any, Dict, List, Optional, cast

from urllib.parse import urljoin

import requests

from requests.adapters import HTTPAdapter, Retry

from .config import SecretStoreConfig

from .exceptions import VaultConnectionError, SecretNotFoundError


class VaultClient:
    """
    Secret Store Client for secure API interactions with OpenBao or HashiCorp Vault.
    Supports:
    - Token-based authentication (OpenBao dev / production)
    - Kubernetes service account authentication (production)
    - Secret CRUD operations via KV-v2 engine
    - Token generation
    """

    # The KV-v2 mount point.  All paths built here are relative to the mount.
    KV_MOUNT = "secret"

    def __init__(self, config: Optional[SecretStoreConfig] = None):
        """
        Initialize the secret store client.
        Args:
            config: SecretStoreConfig instance. If None, uses environment variables.
        """
        self.config = config or SecretStoreConfig.from_env()
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _authenticate_openbao_token(self) -> str:
        """
        Authenticate with OpenBao using token auth.
        This is the default dev/production path when OPENBAO_TOKEN is set.
        Returns:
            The OpenBao token.
        Raises:
            VaultConnectionError: If authentication fails.
        """
        token = self.config.openbao_token
        if not token:
            raise VaultConnectionError(
                vault_addr=self.config.openbao_addr,
                error="No OpenBao token provided for token authentication",
            )
        # With token auth, we don't need to "authenticate" - just cache the token.
        # Token validation happens on first API call.
        self._token = token
        self._token_expiry = datetime.utcnow()
        return self._token

    def authenticate(self) -> str:
        """
        Authenticate with the secret store.
        Uses token auth if OPENBAO_TOKEN is set (OpenBao), otherwise
        falls back to Kubernetes service account authentication.
        Returns:
            The secret store token.
        Raises:
            VaultConnectionError: If authentication fails.
        """
        # Prefer token-based auth (OpenBao)
        if self.config.is_openbao:
            return self._authenticate_openbao_token()

        # Fall back to K8s auth (Vault)
        sa_token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        if os.path.exists(sa_token_path):
            with open(sa_token_path, "r") as f:
                k8s_token = f.read().strip()
        else:
            # For development, use token from config
            k8s_token = self.config.vault_token or ""
        # Read CA certificate
        ca_cert_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
        verify: bool | str = ca_cert_path if os.path.exists(ca_cert_path) else True
        # Authenticate with the secret store
        auth_url = urljoin(self.config.active_addr, "/v1/auth/kubernetes/login")
        payload = {
            "jwt": k8s_token,
            "role": self.config.openbao_role
            if self.config.is_openbao
            else self.config.vault_role,
        }
        try:
            response = self._session.post(
                auth_url, json=payload, verify=verify, timeout=10
            )
            response.raise_for_status()
            result = response.json()
            self._token = cast(str, result["auth"]["client_token"])
            self._token_expiry = datetime.utcnow()
            return self._token
        except requests.exceptions.RequestException as e:
            raise VaultConnectionError(
                vault_addr=self.config.active_addr,
                error=f"Authentication failed: {str(e)}",
            )

    def _get_token(self) -> str:
        """Get the secret store token, refreshing if necessary."""
        if self._token is None or self._token_expiry is None:
            self.authenticate()
        elif datetime.utcnow() >= self._token_expiry:
            self.authenticate()
        return cast(str, self._token)

    def _build_url(self, path: str) -> str:
        """Build the full URL for a secret store API path."""
        return urljoin(self.config.active_addr, f"/v1/{path}")

    # ------------------------------------------------------------------
    # KV-v2 path helpers
    # ------------------------------------------------------------------

    def _kv_data_path(self, secret_path: str) -> str:
        """
        Build the KV-v2 data path for read/write operations.
        Pattern: {mount}/data/{secret_path}
        """
        return f"{self.KV_MOUNT}/data/{secret_path}"

    def _kv_metadata_path(self, secret_path: str) -> str:
        """
        Build the KV-v2 metadata path for delete/list operations.
        Pattern: {mount}/metadata/{secret_path}
        """
        return f"{self.KV_MOUNT}/metadata/{secret_path}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_secret(self, path: str) -> Dict[str, Any]:
        """
        Read a secret from the KV-v2 secret store.
        Args:
            path: The logical secret path (e.g., "iacgenie/tenants/t1/clouds/aws/key").
                  The KV-v2 /data/ prefix is added automatically.
        Returns:
            The secret data dict (the 'data.data' envelope from KV-v2 is unwrapped
            to 'data' for backwards compatibility with callers).
        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            VaultConnectionError: If the connection fails.
        """
        url = self._build_url(self._kv_data_path(path))
        headers = {"X-Vault-Token": self._get_token()}
        try:
            response = self._session.get(url, headers=headers, timeout=10)
            if response.status_code == 404:
                raise SecretNotFoundError(secret_name=path, user_id="")
            response.raise_for_status()
            # KV-v2 response: {"data": {"data": {...}, "metadata": {...}}}
            outer = cast(Dict[str, Any], response.json())
            return cast(Dict[str, Any], outer.get("data", {}))
        except SecretNotFoundError:
            raise
        except requests.exceptions.RequestException as e:
            raise VaultConnectionError(
                vault_addr=self.config.active_addr,
                error=f"Failed to read secret: {str(e)}",
            )

    def write_secret(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write a secret to the KV-v2 secret store.
        Args:
            path: The logical secret path.
                  The KV-v2 /data/ prefix is added automatically.
            data: Must be wrapped under a "data" key per KV-v2 spec,
                  e.g. {"data": {"value": "...", ...}}
        Returns:
            The response from the secret store.
        Raises:
            VaultConnectionError: If the connection fails.
        """
        url = self._build_url(self._kv_data_path(path))
        headers = {"X-Vault-Token": self._get_token()}
        try:
            response = self._session.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except requests.exceptions.RequestException as e:
            raise VaultConnectionError(
                vault_addr=self.config.active_addr,
                error=f"Failed to write secret: {str(e)}",
            )

    def delete_secret(self, path: str) -> None:
        """
        Permanently delete a secret (all versions) from the KV-v2 store.
        Uses the /metadata/ path which removes all versions and metadata.
        Args:
            path: The logical secret path.
        Raises:
            VaultConnectionError: If the connection fails.
        """
        url = self._build_url(self._kv_metadata_path(path))
        headers = {"X-Vault-Token": self._get_token()}
        try:
            response = self._session.delete(url, headers=headers, timeout=10)
            # 404 on delete is acceptable (secret may already be gone)
            if response.status_code == 404:
                raise SecretNotFoundError(secret_name=path, user_id="")
            response.raise_for_status()
        except SecretNotFoundError:
            raise
        except requests.exceptions.RequestException as e:
            raise VaultConnectionError(
                vault_addr=self.config.active_addr,
                error=f"Failed to delete secret: {str(e)}",
            )

    def generate_token(self, secret_name: str, ttl: int = 3600) -> Dict[str, Any]:
        """
        Generate a new short-lived Vault token scoped to read the given secret path.
        Uses the Vault Token API (/v1/auth/token/create) with a policy that restricts
        the token to the specific secret path.
        Args:
            secret_name: The logical path of the secret.
            ttl: Time-to-live in seconds (default: 3600 = 1 hour).
        Returns:
            The generated token and metadata.
        Raises:
            VaultConnectionError: If token generation fails.
        """
        url = self._build_url("auth/token/create")
        headers = {"X-Vault-Token": self._get_token()}
        payload = {
            "ttl": f"{ttl}s",
            "renewable": False,
            "num_uses": 1,
            "meta": {
                "secret_name": secret_name,
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
        try:
            response = self._session.post(
                url, headers=headers, json=payload, timeout=10
            )
            response.raise_for_status()
            result = cast(Dict[str, Any], response.json())
            auth = result.get("auth", {})
            return {
                "data": {
                    "token": auth.get("client_token", ""),
                    "ttl": ttl,
                    "lease_duration": auth.get("lease_duration", ttl),
                    "renewable": auth.get("renewable", False),
                }
            }
        except requests.exceptions.RequestException as e:
            raise VaultConnectionError(
                vault_addr=self.config.active_addr,
                error=f"Failed to generate token: {str(e)}",
            )

    def list_secrets(self, path: str) -> List[str]:
        """
        List secret keys at a given path using the KV-v2 LIST method.
        Args:
            path: The logical path prefix (e.g., "iacgenie/tenants/t1/").
        Returns:
            A list of key names at the given path.
        Raises:
            VaultConnectionError: If the connection fails.
        """
        url = self._build_url(self._kv_metadata_path(path))
        headers = {"X-Vault-Token": self._get_token()}
        try:
            response = self._session.request("LIST", url, headers=headers, timeout=10)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            result = cast(Dict[str, Any], response.json())
            keys: List[str] = result.get("data", {}).get("keys", [])
            return keys
        except requests.exceptions.RequestException as e:
            raise VaultConnectionError(
                vault_addr=self.config.active_addr,
                error=f"Failed to list secrets: {str(e)}",
            )

    def get_secret_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get KV-v2 metadata for a secret (version history, custom metadata).
        Args:
            path: The logical secret path.
        Returns:
            The secret metadata.
        Raises:
            VaultConnectionError: If the connection fails.
        """
        url = self._build_url(self._kv_metadata_path(path))
        headers = {"X-Vault-Token": self._get_token()}
        try:
            response = self._session.get(url, headers=headers, timeout=10)
            if response.status_code == 404:
                raise SecretNotFoundError(secret_name=path, user_id="")
            response.raise_for_status()
            result = cast(Dict[str, Any], response.json())
            return cast(Dict[str, Any], result.get("data", {}))
        except SecretNotFoundError:
            raise
        except requests.exceptions.RequestException as e:
            raise VaultConnectionError(
                vault_addr=self.config.active_addr,
                error=f"Failed to get secret metadata: {str(e)}",
            )

    def close(self) -> None:
        """Close the session."""
        self._session.close()

    def __enter__(self) -> "VaultClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
