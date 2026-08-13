"""
Secrets Bootstrap — Load all required secrets from OpenBao at startup.

This module connects to OpenBao using the service token and populates
os.environ for backward compatibility with existing configuration code.

Usage:
    from src.config.secrets_bootstrap import bootstrap_secrets
    bootstrap_secrets()  # Call once at application startup
"""

import os
import sys
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _read_openbao_secret(addr: str, token: str, path: str) -> Optional[Dict]:
    """Read a secret from OpenBao KV-v2 engine."""
    import requests
    try:
        resp = requests.get(
            f"{addr}/v1/{path}",
            headers={"X-Vault-Token": token},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("data", {})
        logger.warning("OpenBao read %s returned %d", path, resp.status_code)
        return None
    except Exception as e:
        logger.warning("OpenBao read %s failed: %s", path, e)
        return None


def bootstrap_secrets() -> None:
    """
    Load secrets from OpenBao and inject into os.environ.
    
    Only sets env vars that are not already set, preserving any
    explicit overrides from the environment.
    """
    addr = os.environ.get("OPENBAO_ADDR", "http://127.0.0.1:8200")
    token = os.environ.get("OPENBAO_TOKEN") or os.environ.get("VAULT_TOKEN", "")
    mount = os.environ.get("OPENBAO_MOUNT_PATH", "iacgenie/kv")
    
    if not token:
        logger.info("No OPENBAO_TOKEN set — skipping OpenBao bootstrap")
        return
    
    logger.info("Bootstrapping secrets from OpenBao at %s (mount: %s)", addr, mount)
    
    # Map: OpenBao path → list of (env_var_name, secret_key)
    secret_map = {
        f"{mount}/data/postgres": [
            ("POSTGRES_PASSWORD", "password"),
            ("POSTGRES_HOST", "host"),
            ("POSTGRES_PORT", "port"),
            ("POSTGRES_USER", "username"),
        ],
        f"{mount}/data/redis": [
            ("REDIS_PASSWORD", "password"),
        ],
        f"{mount}/data/minio": [
            ("STORAGE_MINIO_ACCESS_KEY", "access_key"),
            ("STORAGE_MINIO_SECRET_KEY", "secret_key"),
            ("STORAGE_MINIO_ENDPOINT", "endpoint"),
        ],
        f"{mount}/data/keycloak": [
            ("KEYCLOAK_ADMIN_USER", "admin_user"),
            ("KEYCLOAK_ADMIN_PASSWORD", "admin_password"),
        ],
        f"{mount}/data/jwt": [
            ("JWT_SECRET", "secret"),
        ],
        f"{mount}/data/smtp": [
            ("SMTP2GO_API_KEY", "api_key"),
            ("SMTP_SERVER", "server"),
            ("SMTP_PORT", "port"),
            ("EMAIL_FROM_ADDRESS", "from_address"),
        ],
        f"{mount}/data/llm": [
            ("GEMINI_API_KEY", "gemini_api_key"),
            ("ANTHROPIC_API_KEY", "anthropic_api_key"),
            ("OPENAI_API_KEY", "openai_api_key"),
            ("LLM_PROXY_BASE_URL", "llm_proxy_base_url"),
        ],
    }
    
    loaded = 0
    for path, mappings in secret_map.items():
        data = _read_openbao_secret(addr, token, path)
        if data is None:
            continue
        for env_var, secret_key in mappings:
            if env_var not in os.environ and secret_key in data:
                os.environ[env_var] = str(data[secret_key])
                loaded += 1
    
    # Build DATABASE_URL if components are available
    if "DATABASE_URL" not in os.environ:
        pg_user = os.environ.get("POSTGRES_USER", "")
        pg_pass = os.environ.get("POSTGRES_PASSWORD", "")
        pg_host = os.environ.get("POSTGRES_HOST", "localhost")
        pg_port = os.environ.get("POSTGRES_PORT", "5432")
        pg_db = os.environ.get("POSTGRES_DATABASE", "iacgenie")
        if pg_user and pg_pass:
            os.environ["DATABASE_URL"] = (
                f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
            )
            loaded += 1
    
    # Build REDIS_URL if password is available
    if "REDIS_URL" not in os.environ:
        redis_pass = os.environ.get("REDIS_PASSWORD", "")
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = os.environ.get("REDIS_PORT", "6379")
        if redis_pass:
            os.environ["REDIS_URL"] = (
                f"redis://:{redis_pass}@{redis_host}:{redis_port}/0"
            )
            loaded += 1
    
    logger.info("OpenBao bootstrap complete — loaded %d environment variables", loaded)
