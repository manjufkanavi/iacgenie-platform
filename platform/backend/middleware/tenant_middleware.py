"""
Tenant Middleware — Multi-Tenant Isolation

Extracts tenant/project information from authenticated requests and makes it
available to request handlers for multi-tenant isolation.

Enhanced features (2026-08):
  - project_id extraction from JWT claims and X-Project-ID header
  - X-Project-ID header injection in responses
  - Tenant isolation filter support for downstream handlers
"""

import logging

from fastapi import Request, HTTPException, Response

from typing import Optional, Callable, Any

from middleware.auth_middleware import get_user_id

logger = logging.getLogger(__name__)


async def tenant_middleware(
    request: Request, call_next: Callable[..., Any]
) -> Response:
    """
    Middleware to extract and validate tenant information from authenticated requests.
    This middleware:
    1. Extracts user ID from the authentication middleware
    2. Adds tenant_id and project_id to request state for use in handlers
    3. Injects X-Tenant-ID and X-Project-ID headers into responses
    4. Logs tenant information for audit purposes

    Args:
        request: The incoming HTTP request
        call_next: The next middleware/handler in the chain

    Returns:
        The response from the next handler
    """
    try:
        # Get user from auth middleware
        user = getattr(request.state, "user", None)
        if user:
            # Extract user ID as tenant ID
            tenant_id = get_user_id(user)
            if not tenant_id:
                logger.warning("User object present but no user ID found")
                raise HTTPException(
                    status_code=401, detail="Invalid authentication: user ID missing"
                )
            # Add tenant ID to request state
            request.state.tenant_id = tenant_id

            # Extract project_id from JWT claims or header
            project_id = getattr(request.state, "project_id", None)
            if not project_id:
                # Try from JWT custom claim in user object
                project_id = user.get("project_id", "") or ""
                if not project_id:
                    # Fall back to X-Project-ID header
                    project_id = request.headers.get("X-Project-ID", "") or ""
            request.state.project_id = project_id

            # Log tenant access
            logger.info(
                f"Tenant access: tenant_id={tenant_id}, project_id={project_id}",
                extra={
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "path": request.url.path,
                    "method": request.method,
                },
            )
        else:
            # For public endpoints, no tenant ID
            request.state.tenant_id = None
            request.state.project_id = None
            logger.debug("Public endpoint accessed (no tenant)")
        response = await call_next(request)
        # Add tenant/project IDs to response headers for debugging
        if getattr(request.state, "tenant_id", None):
            response.headers["X-Tenant-ID"] = request.state.tenant_id
        if getattr(request.state, "project_id", None):
            response.headers["X-Project-ID"] = request.state.project_id
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in tenant middleware: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing tenant information",
        )


def require_tenant(request: Request) -> str:
    """
    Dependency function to require tenant ID for an endpoint.
    Use this in FastAPI endpoints that require tenant authentication:
    ```python

    @router.get("/protected")

    async def protected_endpoint(tenant_id: str = Depends(require_tenant)):
        # tenant_id is guaranteed to be present
        pass
    ```

    Args:
        request: The incoming HTTP request

    Returns:
        The tenant ID from request state

    Raises:
        HTTPException: If tenant ID is not present
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return tenant_id


def get_optional_tenant(request: Request) -> Optional[str]:
    """
    Dependency function to get optional tenant ID for an endpoint.
    Use this in FastAPI endpoints that work with or without tenant:
    ```python

    @router.get("/public-or-private")

    async def endpoint(tenant_id: Optional[str] = Depends(get_optional_tenant)):
        if tenant_id:
            # Authenticated user
        else:
            # Public access
        pass
    ```

    Args:
        request: The incoming HTTP request

    Returns:
        The tenant ID from request state, or None if not present
    """
    return getattr(request.state, "tenant_id", None)


def require_project_id(request: Request) -> str:
    """
    Dependency function to require a project ID for an endpoint.

    Extracts project_id from request.state (set by tenant_middleware)
    or from the X-Project-ID header.

    Args:
        request: The incoming HTTP request

    Returns:
        The project ID string

    Raises:
        HTTPException: If project_id is not present
    """
    project_id = getattr(request.state, "project_id", None)
    if not project_id:
        project_id = request.headers.get("X-Project-ID", "")
    if not project_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "PROJECT_ID_REQUIRED",
                "message": "Project ID must be provided (via X-Project-ID header or in token claims)",
                "code": "MISSING_PROJECT_ID",
            },
        )
    return project_id


def get_optional_project_id(request: Request) -> Optional[str]:
    """
    Dependency function to get an optional project ID.

    Returns the project_id from request.state or X-Project-ID header,
    or None if neither is present.

    Args:
        request: The incoming HTTP request

    Returns:
        The project ID string, or None
    """
    project_id = getattr(request.state, "project_id", None)
    if project_id:
        return project_id
    header_project = request.headers.get("X-Project-ID", "")
    return header_project if header_project else None
