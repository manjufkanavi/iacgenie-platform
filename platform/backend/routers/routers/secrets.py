"""

Secret Store Router

API endpoints for secret store operations.

Integrates with Keycloak authentication and Vault.

Replaces X-Tenant-ID header with authenticated user ID.

"""

import logging

from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from pydantic import BaseModel, Field

from modules.secret_store.secret_manager import SecretManager

from modules.secret_store.token_generator import TokenGenerator

from modules.secret_store.audit_logger import AuditLogger

from modules.secret_store.exceptions import (
    SecretNotFoundError,
    SecretAccessError,
    VaultConnectionError,
    SecretTooLargeError,
    SecretAlreadyExistsError,
)

from modules.secret_store.models import SecretAccessRequest

from middleware.auth_middleware import get_user_id, require_admin

from middleware.error_handling import create_success_response

logger = logging.getLogger(__name__)

# Create router

router = APIRouter(prefix="/api/secrets", tags=["Secret Store"])

# Global instances

_secret_manager: Optional[SecretManager] = None

_audit_logger: Optional[AuditLogger] = None

_token_generator: Optional[TokenGenerator] = None


def get_secret_manager() -> SecretManager:
    """Get the global SecretManager instance."""
    global _secret_manager
    if _secret_manager is None:
        from modules.secret_store.config import SecretStoreConfig

        config = SecretStoreConfig.from_env()
        _secret_manager = SecretManager(config)
    return _secret_manager


def get_audit_logger() -> AuditLogger:
    """Get the global AuditLogger instance."""
    global _audit_logger
    if _audit_logger is None:
        from modules.secret_store.config import SecretStoreConfig

        config = SecretStoreConfig.from_env()
        _audit_logger = AuditLogger(config)
    return _audit_logger


def get_token_generator() -> TokenGenerator:
    """Get the global TokenGenerator instance."""
    global _token_generator
    if _token_generator is None:
        from modules.secret_store.config import SecretStoreConfig

        config = SecretStoreConfig.from_env()
        _token_generator = TokenGenerator(config)
    return _token_generator


# ============================================================================

# Request Models

# ============================================================================


class GetSecretRequest(BaseModel):
    """Request to get a secret."""

    secret_name: str = Field(..., description="Name of the secret to retrieve")
    session_id: Optional[str] = Field(None, description="Session ID for tracing")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class SetSecretRequest(BaseModel):
    """Request to set a secret."""

    secret_name: str = Field(..., description="Name of the secret")
    secret_value: str = Field(..., description="Value of the secret")
    secret_type: str = Field(
        "generic", description="Type of secret (generic, git_token, ci_pat)"
    )
    expires_in: Optional[int] = Field(
        None, description="Expiration time in seconds (None for no expiration)"
    )
    session_id: Optional[str] = Field(None, description="Session ID for tracing")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class DeleteSecretRequest(BaseModel):
    """Request to delete a secret."""

    secret_name: str = Field(..., description="Name of the secret to delete")
    session_id: Optional[str] = Field(None, description="Session ID for tracing")


class GenerateGitTokenRequest(BaseModel):
    """Request to generate a Git token."""

    repo_url: str = Field(..., description="Repository URL")
    provider: str = Field(
        "github", description="Git provider (github, gitlab, bitbucket)"
    )
    permissions: Optional[str] = Field(
        "read", description="Token permissions (read, write, admin)"
    )
    expires_in: Optional[int] = Field(3600, description="Expiration time in seconds")
    session_id: Optional[str] = Field(None, description="Session ID for tracing")


class GenerateCIPATRequest(BaseModel):
    """Request to generate a CI/CD PAT."""

    ci_provider: str = Field(
        "github_actions",
        description="CI provider (github_actions, gitlab_ci, circleci)",
    )
    repo_url: str = Field(..., description="Repository URL")
    workflow_file: Optional[str] = Field(None, description="Specific workflow file")
    expires_in: Optional[int] = Field(3600, description="Expiration time in seconds")
    session_id: Optional[str] = Field(None, description="Session ID for tracing")


# ============================================================================

# Response Models

# ============================================================================


class SecretResponse(BaseModel):
    """Response for secret operations."""

    secret_name: str = Field(..., description="Name of the secret")
    secret_value: str = Field(..., description="Value of the secret (may be masked)")
    secret_type: str = Field(..., description="Type of secret")
    vault_path: str = Field(..., description="Path in Vault")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")


class TokenResponse(BaseModel):
    """Response for token generation."""

    token: str = Field(..., description="Generated token")
    token_type: str = Field(..., description="Type of token")
    expires_at: str = Field(..., description="Expiration timestamp")
    permissions: str = Field(..., description="Token permissions")


# ============================================================================

# Endpoints

# ============================================================================


@router.post("/get", response_model=SecretResponse)
async def get_secret(
    request: GetSecretRequest, user_id: str = Depends(get_user_id)
) -> SecretResponse:
    """
    Get a secret value.
    Args:
        request: Secret access request
        user_id: Authenticated user ID (replaces X-Tenant-ID)
    Returns:
        SecretResponse with secret value
    Raises:
        HTTPException: If secret not found or access denied
    """
    try:
        secret_manager = get_secret_manager()
        audit_logger = get_audit_logger()
        # Build access request
        access_request = SecretAccessRequest(
            session_id=request.session_id or "",
            secret_name=request.secret_name,
            user_id=user_id,
            context=request.context or {},
        )
        # Get the secret (synchronous, not async)
        result = secret_manager.get_secret(access_request)
        # Audit log
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="read",
            session_id=request.session_id or "",
            success=True,
        )
        logger.info(
            "Secret retrieved",
            extra={
                "user_id": user_id,
                "secret_name": request.secret_name,
                "session_id": request.session_id,
            },
        )
        return SecretResponse(
            secret_name=request.secret_name,
            secret_value=result.value,
            secret_type="generic",
            vault_path=result.vault_path or "",
            created_at="",
            expires_at=result.expires_at.isoformat() if result.expires_at else None,
        )
    except SecretNotFoundError as e:
        logger.warning(f"Secret not found for user {user_id}: {e}")
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="read",
            session_id=request.session_id or "",
            success=False,
            error_message="Secret not found",
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": e.message,
                    "type": "secret_not_found",
                    "code": "not_found",
                }
            },
        )
    except SecretTooLargeError as e:
        logger.error(f"Secret too large for user {user_id}: {e}")
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="read",
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "message": str(e),
                    "type": "secret_too_large",
                    "code": "payload_too_large",
                }
            },
        )
    except SecretAccessError as e:
        logger.error(f"Secret access error for user {user_id}: {e}")
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="read",
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": str(e),
                    "type": "access_denied",
                    "code": "access_denied",
                }
            },
        )
    except VaultConnectionError as e:
        logger.error(f"Vault connection error: {e}")
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="read",
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": "Vault service unavailable",
                    "type": "service_unavailable",
                    "code": "vault_error",
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Unexpected error getting secret for user {user_id}: {e}", exc_info=True
        )
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="read",
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/set")
async def set_secret(
    request: SetSecretRequest, admin: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Set a secret value (admin only).
    Args:
        request: Secret set request
        admin: Admin token (replaces user_id auth)
    Returns:
        Success response
    Raises:
        HTTPException: If secret cannot be stored
    """
    try:
        user_id: str = str(admin.get("uid") or "")
        secret_manager = get_secret_manager()
        audit_logger = get_audit_logger()
        # Convert expires_in to ttl_minutes
        ttl_minutes = None
        if request.expires_in is not None:
            ttl_minutes = request.expires_in // 60
        # Set the secret (synchronous, uses store_secret method)
        result = secret_manager.store_secret(
            tenant_id=user_id or "",
            secret_name=request.secret_name,
            secret_value=request.secret_value,
            secret_type=request.secret_type,
            ttl_minutes=ttl_minutes,
            metadata=request.context,
        )
        # Audit log
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="create",
            session_id=request.session_id or "",
            success=True,
        )
        logger.info(
            "Secret stored",
            extra={
                "user_id": user_id,
                "secret_name": request.secret_name,
                "secret_type": request.secret_type,
                "session_id": request.session_id,
            },
        )
        return create_success_response(
            data={
                "secret_name": request.secret_name,
                "vault_path": result.vault_path or "",
                "expires_at": result.expires_at.isoformat()
                if result.expires_at
                else None,
            },
            message="Secret stored successfully",
        )
    except SecretAlreadyExistsError as e:
        logger.error(f"Secret already exists for user {user_id}: {e}")
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="create",
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "message": e.message,
                    "type": "secret_already_exists",
                    "code": "conflict",
                }
            },
        )
    except SecretTooLargeError as e:
        logger.error(f"Secret too large for user {user_id}: {e}")
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="create",
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "message": str(e),
                    "type": "secret_too_large",
                    "code": "payload_too_large",
                }
            },
        )
    except Exception as e:
        logger.error(f"Error setting secret for user {user_id}: {e}", exc_info=True)
        audit_logger.log_secret_access(
            user_id=user_id,
            secret_name=request.secret_name,
            operation="create",
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to store secret",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/delete")
async def delete_secret(
    request: DeleteSecretRequest, admin: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Delete a secret (admin only).
    Args:
        request: Secret delete request
        admin: Admin token (replaces user_id auth)
    Returns:
        Success response
    Raises:
        HTTPException: If secret cannot be deleted
    """
    try:
        user_id: str = str(admin.get("uid") or "")
        secret_manager = get_secret_manager()
        audit_logger = get_audit_logger()
        # Delete the secret (sync, no session_id param)
        secret_manager.delete_secret(
            tenant_id=user_id or "",
            secret_name=request.secret_name,
        )
        # Audit log
        audit_logger.log_secret_delete(
            user_id=user_id,
            secret_name=request.secret_name,
            session_id=request.session_id or "",
            success=True,
        )
        logger.info(
            "Secret deleted",
            extra={
                "user_id": user_id,
                "secret_name": request.secret_name,
                "session_id": request.session_id,
            },
        )
        return create_success_response(
            data={"secret_name": request.secret_name},
            message="Secret deleted successfully",
        )
    except SecretNotFoundError as e:
        logger.warning(f"Secret not found for user {user_id}: {e}")
        audit_logger.log_secret_delete(
            user_id=user_id,
            secret_name=request.secret_name,
            session_id=request.session_id or "",
            success=False,
            error_message="Secret not found",
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": e.message,
                    "type": "secret_not_found",
                    "code": "not_found",
                }
            },
        )
    except Exception as e:
        logger.error(f"Error deleting secret for user {user_id}: {e}", exc_info=True)
        audit_logger.log_secret_delete(
            user_id=user_id,
            secret_name=request.secret_name,
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to delete secret",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/git-token", response_model=TokenResponse)
async def generate_git_token(
    request: GenerateGitTokenRequest, user_id: str = Depends(get_user_id)
) -> TokenResponse:
    """
    Generate a Git access token.
    Args:
        request: Git token generation request
        user_id: Authenticated user ID (replaces X-Tenant-ID)
    Returns:
        TokenResponse with generated token
    Raises:
        HTTPException: If token generation fails
    """
    try:
        token_generator = get_token_generator()
        audit_logger = get_audit_logger()
        # Generate Git token (sync, params: user_id, repo_url, ttl_minutes, scopes)
        result = token_generator.generate_git_token(
            user_id=user_id,
            repo_url=request.repo_url,
            ttl_minutes=request.expires_in or 3600,
            scopes=[request.permissions] if request.permissions else None,
        )
        # Audit log
        audit_logger.log_token_generation(
            user_id=user_id,
            secret_name=request.repo_url,
            ttl_minutes=request.expires_in or 3600,
            session_id=request.session_id or "",
            success=True,
        )
        logger.info(
            "Git token generated",
            extra={
                "user_id": user_id,
                "provider": request.provider,
                "repo_url": request.repo_url,
                "session_id": request.session_id,
            },
        )
        return TokenResponse(
            token=result.value,
            token_type="git_token",
            expires_at=result.expires_at.isoformat() if result.expires_at else "",
            permissions=request.permissions or "read",
        )
    except Exception as e:
        logger.error(
            f"Error generating Git token for user {user_id}: {e}", exc_info=True
        )
        audit_logger.log_token_generation(
            user_id=user_id,
            secret_name=request.repo_url,
            ttl_minutes=request.expires_in or 3600,
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to generate Git token",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/ci-pat", response_model=TokenResponse)
async def generate_ci_pat(
    request: GenerateCIPATRequest, user_id: str = Depends(get_user_id)
) -> TokenResponse:
    """
    Generate a CI/CD Personal Access Token.
    Args:
        request: CI PAT generation request
        user_id: Authenticated user ID (replaces X-Tenant-ID)
    Returns:
        TokenResponse with generated token
    Raises:
        HTTPException: If token generation fails
    """
    try:
        token_generator = get_token_generator()
        audit_logger = get_audit_logger()
        # Generate CI PAT (sync, params: user_id, ci_provider, ttl_minutes, scopes)
        result = token_generator.generate_ci_pat(
            user_id=user_id,
            ci_provider=request.ci_provider,
            ttl_minutes=request.expires_in or 3600,
            scopes=[request.repo_url] if request.repo_url else None,
        )
        # Audit log
        audit_logger.log_token_generation(
            user_id=user_id,
            secret_name=request.ci_provider,
            ttl_minutes=request.expires_in or 3600,
            session_id=request.session_id or "",
            success=True,
        )
        logger.info(
            "CI PAT generated",
            extra={
                "user_id": user_id,
                "ci_provider": request.ci_provider,
                "repo_url": request.repo_url,
                "session_id": request.session_id,
            },
        )
        return TokenResponse(
            token=result.value,
            token_type="ci_pat",
            expires_at=result.expires_at.isoformat() if result.expires_at else "",
            permissions="read_write",
        )
    except Exception as e:
        logger.error(f"Error generating CI PAT for user {user_id}: {e}", exc_info=True)
        audit_logger.log_token_generation(
            user_id=user_id,
            secret_name=request.ci_provider,
            ttl_minutes=request.expires_in or 3600,
            session_id=request.session_id or "",
            success=False,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to generate CI PAT",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for secret store service.
    Returns:
        Health status of the secret store service
    """
    try:
        secret_manager = get_secret_manager()
        token_generator = get_token_generator()
        audit_logger = get_audit_logger()
        return {
            "status": "healthy",
            "service": "secret_store",
            "vault_connected": secret_manager.vault_client is not None
            if secret_manager
            else False,
            "audit_logging_enabled": audit_logger is not None,
            "token_generation_enabled": token_generator is not None,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "service": "secret_store", "error": str(e)}
