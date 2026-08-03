"""

Secret Store API

Internal HTTP API for secret operations (requires X-Tenant-ID header).

"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from .config import SecretStoreConfig

from .exceptions import SecretNotFoundError, SecretAccessError, TenantIdMissingError

from .models import SecretAccessRequest, SecretAccessResponse, SecretOperation

from .secret_manager import SecretManager

from .audit_logger import AuditLogger

from .token_generator import TokenGenerator

# Create router

router = APIRouter(prefix="/secrets", tags=["Secret Store"])


def get_secret_manager() -> SecretManager:
    """Get a configured SecretManager instance."""
    config = SecretStoreConfig.from_env()
    return SecretManager(config)


def get_audit_logger() -> AuditLogger:
    """Get a configured AuditLogger instance."""
    config = SecretStoreConfig.from_env()
    return AuditLogger(config)


def get_token_generator() -> TokenGenerator:
    """Get a configured TokenGenerator instance."""
    config = SecretStoreConfig.from_env()
    return TokenGenerator(config)


@router.post("/get")
async def get_secret(
    request: SecretAccessRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> SecretAccessResponse:
    """
    Get a secret value.
    Args:
        request: The secret access request.
        x_tenant_id: Tenant ID from header (required).
    Returns:
        The secret value with metadata.
    Raises:
        HTTPException: If tenant ID is missing or secret not found.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        secret_manager = get_secret_manager()
        audit_logger = get_audit_logger()
        # Get the secret
        response = secret_manager.get_secret(
            request=SecretAccessRequest(
                session_id=request.session_id,
                secret_name=request.secret_name,
                user_id=x_tenant_id,
                context=request.context,
                operation=SecretOperation.ACCESS,
            )
        )
        # Audit log
        audit_logger.log_secret_access(
            user_id=x_tenant_id,
            secret_name=request.secret_name,
            operation=SecretOperation.ACCESS.value,
            session_id=request.session_id,
            build_id=request.context.get("build_id"),
            repo_url=request.context.get("repo_url"),
            success=True,
        )
        return response
    except SecretNotFoundError as e:
        audit_logger = get_audit_logger()
        audit_logger.log_secret_access(
            user_id=x_tenant_id,
            secret_name=request.secret_name,
            operation=SecretOperation.ACCESS.value,
            session_id=request.session_id,
            build_id=request.context.get("build_id"),
            repo_url=request.context.get("repo_url"),
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except SecretAccessError as e:
        audit_logger = get_audit_logger()
        audit_logger.log_secret_access(
            user_id=x_tenant_id,
            secret_name=request.secret_name,
            operation=SecretOperation.ACCESS.value,
            session_id=request.session_id,
            build_id=request.context.get("build_id"),
            repo_url=request.context.get("repo_url"),
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/generate/git-token")
async def generate_git_token(
    user_id: str,
    repo_url: str,
    ttl_minutes: int = 60,
    scopes: Optional[list[str]] = None,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> SecretAccessResponse:
    """
    Generate a just-in-time Git token.
    Args:
        user_id: User ID.
        repo_url: Repository URL.
        ttl_minutes: Token TTL in minutes (default: 60).
        scopes: List of scopes (optional).
        x_tenant_id: Tenant ID from header (required).
    Returns:
        The generated token response.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        token_generator = get_token_generator()
        audit_logger = get_audit_logger()
        response = token_generator.generate_git_token(
            user_id=user_id,
            repo_url=repo_url,
            ttl_minutes=ttl_minutes,
            scopes=scopes,
        )
        # Audit log
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"git_token_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id="",
            success=True,
        )
        return response
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"git_token_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/ci-pat")
async def generate_ci_pat(
    user_id: str,
    ci_provider: str,
    ttl_minutes: int = 60,
    scopes: Optional[list[str]] = None,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> SecretAccessResponse:
    """
    Generate a just-in-time CI PAT.
    Args:
        user_id: User ID.
        ci_provider: CI provider (e.g., 'github', 'gitlab').
        ttl_minutes: Token TTL in minutes (default: 60).
        scopes: List of scopes (optional).
        x_tenant_id: Tenant ID from header (required).
    Returns:
        The generated token response.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        token_generator = get_token_generator()
        audit_logger = get_audit_logger()
        response = token_generator.generate_ci_pat(
            user_id=user_id,
            ci_provider=ci_provider,
            ttl_minutes=ttl_minutes,
            scopes=scopes,
        )
        # Audit log
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"ci_pat_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id="",
            success=True,
        )
        return response
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"ci_pat_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/llm-api-key")
async def generate_llm_api_key(
    user_id: str,
    model_name: str,
    ttl_minutes: int = 60,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> SecretAccessResponse:
    """
    Generate a just-in-time LLM API key.
    Args:
        user_id: User ID.
        model_name: Model name.
        ttl_minutes: Token TTL in minutes (default: 60).
        x_tenant_id: Tenant ID from header (required).
    Returns:
        The generated token response.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        token_generator = get_token_generator()
        audit_logger = get_audit_logger()
        response = token_generator.generate_llm_api_key(
            user_id=user_id,
            model_name=model_name,
            ttl_minutes=ttl_minutes,
        )
        # Audit log
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"llm_api_key_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id="",
            success=True,
        )
        return response
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"llm_api_key_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/sandbox-credentials")
async def generate_sandbox_credentials(
    user_id: str,
    session_id: str,
    ttl_minutes: int = 60,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> SecretAccessResponse:
    """
    Generate ephemeral credentials for sandbox execution.
    Args:
        user_id: User ID.
        session_id: Session ID.
        ttl_minutes: Token TTL in minutes (default: 60).
        x_tenant_id: Tenant ID from header (required).
    Returns:
        The generated token response.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        token_generator = get_token_generator()
        audit_logger = get_audit_logger()
        response = token_generator.generate_sandbox_credentials(
            user_id=user_id,
            session_id=session_id,
            ttl_minutes=ttl_minutes,
        )
        # Audit log
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"sandbox_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id=session_id,
            success=True,
        )
        return response
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log_token_generation(
            user_id=x_tenant_id,
            secret_name=f"sandbox_{user_id}",
            ttl_minutes=ttl_minutes,
            session_id=session_id,
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotate")
async def rotate_secret(
    user_id: str,
    secret_name: str,
    ttl_minutes: int = 60,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> SecretAccessResponse:
    """
    Rotate a secret.
    Args:
        user_id: User ID.
        secret_name: Name of the secret to rotate.
        ttl_minutes: New token TTL in minutes (default: 60).
        x_tenant_id: Tenant ID from header (required).
    Returns:
        The rotated secret response.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        secret_manager = get_secret_manager()
        audit_logger = get_audit_logger()
        response = secret_manager.rotate_secret(
            tenant_id=user_id,
            secret_name=secret_name,
            ttl_minutes=ttl_minutes,
        )
        # Audit log
        audit_logger.log_secret_update(
            user_id=x_tenant_id,
            secret_name=secret_name,
            session_id="",
            success=True,
        )
        return response
    except SecretNotFoundError as e:
        audit_logger = get_audit_logger()
        audit_logger.log_secret_update(
            user_id=x_tenant_id,
            secret_name=secret_name,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log_secret_update(
            user_id=x_tenant_id,
            secret_name=secret_name,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{secret_name}")
async def delete_secret(
    secret_name: str,
    user_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> dict[str, str]:
    """
    Delete a secret.
    Args:
        secret_name: Name of the secret to delete.
        user_id: User ID.
        x_tenant_id: Tenant ID from header (required).
    Returns:
        Deletion confirmation.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        secret_manager = get_secret_manager()
        audit_logger = get_audit_logger()
        secret_manager.delete_secret(
            tenant_id=user_id,
            secret_name=secret_name,
        )
        # Audit log
        audit_logger.log_secret_delete(
            user_id=x_tenant_id,
            secret_name=secret_name,
            session_id="",
            success=True,
        )
        return {"message": f"Secret '{secret_name}' deleted successfully"}
    except SecretNotFoundError as e:
        audit_logger = get_audit_logger()
        audit_logger.log_secret_delete(
            user_id=x_tenant_id,
            secret_name=secret_name,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log_secret_delete(
            user_id=x_tenant_id,
            secret_name=secret_name,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store")
async def store_secret(
    user_id: str,
    secret_name: str,
    secret_value: str,
    secret_type: str = "generic",
    ttl_minutes: int = 60,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID", description="Tenant ID"),
) -> SecretAccessResponse:
    """
    Store a new secret.
    Args:
        user_id: User ID.
        secret_name: Name of the secret.
        secret_value: The secret value to store.
        secret_type: Type of secret (default: 'generic').
        ttl_minutes: Token TTL in minutes (default: 60).
        x_tenant_id: Tenant ID from header (required).
    Returns:
        The stored secret response.
    """
    if not x_tenant_id:
        raise TenantIdMissingError()
    try:
        secret_manager = get_secret_manager()
        audit_logger = get_audit_logger()
        response = secret_manager.store_secret(
            tenant_id=user_id,
            secret_name=secret_name,
            secret_value=secret_value,
            secret_type=secret_type,
            ttl_minutes=ttl_minutes,
        )
        # Audit log
        audit_logger.log_secret_create(
            user_id=x_tenant_id,
            secret_name=secret_name,
            secret_type=secret_type,
            session_id="",
            success=True,
        )
        return response
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log_secret_create(
            user_id=x_tenant_id,
            secret_name=secret_name,
            secret_type=secret_type,
            session_id="",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))
