"""
Multi-Tenant Middleware — Project-Level Tenant Isolation

Enhances the base tenant_middleware with:
  - project_id extraction from JWT claims and X-Project-ID header
  - group/tenant isolation: users can only access their project's resources
  - Cross-project access check: only platform-admins can access all projects
  - Middleware dependency that returns (user_info, project_id) tuple

The middleware also injects X-Project-ID response headers for debugging.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi import HTTPException, Request, Response, status

from middleware.auth_middleware import get_user_id
from middleware.jwt_validator import get_current_user_info, require_platform_admin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROJECT_ID = "__all__"  # platform-admin "all projects" marker


# ---------------------------------------------------------------------------
# Dependency — returns (user_info, project_id) tuple
# ---------------------------------------------------------------------------


async def get_project_context(
    request: Request,
    x_project_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    FastAPI dependency that extracts both user info and project_id.

    1. If a valid JWT (Bearer token) is present, validates it via
       Keycloak JWKS and extracts project_id from JWT claims or the
       X-Project-ID header.
    2. Falls back to the request.state if already set by auth_middleware.

    Returns:
        (user_info_dict, project_id_str)
    """
    # --- Try JWT-based extraction first ---
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            claims = await get_current_user_info(request, x_project_id)
            user_info: Dict[str, Any] = claims
            project_id: str = getattr(request.state, "project_id", "") or ""
            return user_info, project_id
        except Exception as exc:
            logger.debug(
                "JWT validation failed (fallback to basic auth): %s", exc
            )

    # --- Fallback: use existing request.state user ---
    user = getattr(request.state, "user", None)
    if user:
        uid = get_user_id(user)
        user_info = {
            "uid": uid,
            "email": user.get("email", ""),
            "role": user.get("role", "member"),
        }
        project_id = getattr(request.state, "project_id", "") or ""
        return user_info, project_id

    # --- Public/unauthenticated ---
    return {}, ""


async def require_project_context(
    request: Request,
    x_project_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Same as get_project_context but raises 401 if no authenticated user
    and no explicit project_id is provided.
    """
    user_info, project_id = await get_project_context(request, x_project_id)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "Authentication required for project-scoped access",
                "code": "MISSING_TOKEN",
            },
        )
    return user_info, project_id


# ---------------------------------------------------------------------------
# Project isolation helpers
# ---------------------------------------------------------------------------


def check_project_access(
    user_info: Dict[str, Any],
    project_id: str,
    allow_all: bool = False,
) -> bool:
    """
    Check if the user has access to the given project.

    Rules:
      - platform-admins always have access (allow_all=True is implicit).
      - Users must have the project_id in their JWT claims, OR
        the project_id must match their assigned project.
      - Users with an empty/missing project_id are assumed to belong
        to a single project identified by their user ID (UID = project).

    Args:
        user_info: Decoded user claims dict.
        project_id: Target project ID.
        allow_all: If True, only platform-admins can access.

    Returns:
        True if access is granted.
    """
    if not project_id:
        return True  # No project filter — allow

    role = user_info.get("role", "member")
    realm_roles: list = user_info.get("realm_roles", [])

    # Platform-admin bypass
    if role == "platform-admin" or "platform-admin" in realm_roles:
        return True

    # Check if user's JWT claims contain the project_id
    user_project = user_info.get("project_id", "")
    if user_project and project_id in (user_project, ""):
        return True

    # For members with a single project (UID-based)
    if role == "member" and user_info.get("uid"):
        if project_id == user_info["uid"]:
            return True

    # Developer / reviewer can access projects they are assigned to
    if role in ("developer", "reviewer"):
        assigned_projects = user_info.get("assigned_projects", [])
        if project_id in assigned_projects:
            return True
        # Or if project_id matches their UID (single project)
        if user_info.get("uid") == project_id:
            return True

    return False


async def enforce_project_isolation(
    request: Request,
    call_next: Callable[..., Any],
) -> Response:
    """
    ASGI-style middleware that enforces project-level isolation.

    For each request:
      1. Extracts user_info and project_id from JWT / headers.
      2. If project_id is provided and the user lacks access, returns 403.
      3. If allow_all is not True and user is not platform-admin,
         cross-project access is blocked.
      4. Injects X-Project-ID header into the response.
    """
    try:
        x_project_id = request.headers.get("X-Project-ID")
        user_info, project_id = await get_project_context(request, x_project_id)

        # Enforce isolation
        if project_id:
            if user_info and not check_project_access(user_info, project_id):
                logger.warning(
                    "Project access denied: user=%s project=%s",
                    user_info.get("uid"),
                    project_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "PROJECT_ACCESS_DENIED",
                        "message": f"User does not have access to project '{project_id}'",
                        "code": "PROJECT_ACCESS_DENIED",
                        "project_id": project_id,
                        "user_id": user_info.get("uid"),
                    },
                )

        # Ensure state is set for downstream handlers
        request.state.user_info = user_info
        request.state.project_id = project_id

        response = await call_next(request)

        # Inject project header
        if project_id:
            response.headers["X-Project-ID"] = project_id
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Project isolation middleware error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing project context",
        )


# ---------------------------------------------------------------------------
# Tenant isolation filter — filter queries by project_id
# ---------------------------------------------------------------------------


def tenant_isolation_filter(
    query: Dict[str, Any],
    user_info: Dict[str, Any],
    project_id: str,
    resource_field: str = "project_id",
) -> Dict[str, Any]:
    """
    Add project_id filter to a database query dictionary.

    Platform-admins are exempt from filtering (their query is returned
    unchanged).  Other users get ``{resource_field: project_id}`` added.

    Args:
        query: Original query dict.
        user_info: User claims.
        project_id: Project to scope to.
        resource_field: DB column name for the project foreign key.

    Returns:
        Modified query dict with project scope.
    """
    if not project_id:
        return query

    role = user_info.get("role", "member")
    realm_roles: list = user_info.get("realm_roles", [])

    # Platform-admins bypass
    if role == "platform-admin" or "platform-admin" in realm_roles:
        return query

    filtered = dict(query)
    filtered[resource_field] = project_id
    return filtered


# ---------------------------------------------------------------------------
# Backwards-compatible alias
# ---------------------------------------------------------------------------

get_tenant_project_context = get_project_context
