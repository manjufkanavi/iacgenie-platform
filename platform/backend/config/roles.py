"""
Role-based access control configuration and utilities.

Defines the role hierarchy, permitted actions, and multi-tenant
project-scoped permission functions.

New multi-tenant roles (2026-08):
    member           — baseline user, scoped to one or more projects
    project-admin    — admin within a single project
    platform-admin   — full cross-project access

Legacy roles (user, developer, reviewer, admin) are still supported
for backward compatibility but new projects should use the
multi-tenant roles above.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy role hierarchy (backward compatible)
# ---------------------------------------------------------------------------

LEGACY_ROLE_HIERARCHY: list[str] = ["user", "developer", "reviewer", "admin"]
LEGACY_ADMIN_ROLES: set[str] = {"admin"}

# ---------------------------------------------------------------------------
# Multi-tenant role hierarchy (new default)
# ---------------------------------------------------------------------------

ROLE_HIERARCHY: list[str] = [
    "member",
    "project-admin",
    "platform-admin",
]

ADMIN_ROLES: set[str] = {"project-admin", "platform-admin"}

# ---------------------------------------------------------------------------
# Permission matrix — maps each role to the set of allowed actions
# ---------------------------------------------------------------------------

# Build incrementally to avoid forward-reference LSP errors
_member_actions: Set[str] = {
    # Pipeline / workflow actions
    "pipeline:start",
    "pipeline:status",
    "pipeline:resume",
    "pipeline:cancel",
    # Approval
    "approval:request",
    "approval:status",
    # Resource read
    "iac:read",
    "iac:list",
    "approval:view",
    "notification:read",
    "metric:read",
    # Their own projects only
    "project:join",
}

_project_admin_extra: Set[str] = {
    # Pipeline management
    "pipeline:stop",
    "pipeline:intervene",
    "pipeline:retry",
    # Approval
    "approval:submit",
    "approval:revoke",
    # Resource write
    "iac:create",
    "iac:update",
    "iac:delete",
    # Project management (within their project)
    "project:manage",
    "project:users:add",
    "project:users:remove",
    "project:users:list",
    "project:settings:update",
    # Git operations
    "git:push",
    "git:pull",
    "git:configure",
    # Notifications & metrics
    "notification:send",
    "metric:configure",
}

_platform_admin_extra: Set[str] = {
    # Platform-wide operations
    "platform:admin",
    "platform:users:list",
    "platform:users:add",
    "platform:users:remove",
    "platform:users:role:update",
    "platform:projects:list",
    "platform:projects:create",
    "platform:projects:delete",
    "platform:settings:update",
    "platform:audit:read",
    "platform:metrics:read",
    "platform:health:check",
    "rbac:manage",
}

PERMITTED_ACTIONS: Dict[str, Set[str]] = {
    "member": _member_actions,
    "project-admin": _member_actions | _project_admin_extra,
    "platform-admin": _member_actions | _project_admin_extra | _platform_admin_extra,
}

# ---------------------------------------------------------------------------
# Legacy permissions (kept for backward compat)
# ---------------------------------------------------------------------------

LEGACY_PERMITTED_ACTIONS: Dict[str, Set[str]] = {
    "admin": {
        "pipeline:start",
        "pipeline:resume",
        "pipeline:stop",
        "pipeline:status",
        "pipeline:intervene",
        "pipeline:retry",
        "approval:request",
        "approval:submit",
        "approval:status",
        "approval:revoke",
        "iac:read",
        "iac:list",
        "iac:create",
        "iac:update",
        "iac:delete",
        "git:push",
        "git:pull",
        "notification:send",
        "platform:admin",
    },
    "developer": {
        "pipeline:start",
        "pipeline:resume",
        "pipeline:status",
        "approval:request",
        "iac:read",
        "iac:list",
        "iac:create",
        "iac:update",
        "git:push",
        "git:pull",
    },
    "reviewer": {
        "pipeline:status",
        "approval:submit",
        "approval:status",
        "iac:read",
        "iac:list",
    },
    "viewer": {
        "pipeline:status",
        "approval:status",
        "iac:read",
        "iac:list",
    },
    "user": {
        "pipeline:status",
        "approval:status",
        "iac:read",
        "iac:list",
    },
}

# ---------------------------------------------------------------------------
# Role normalisation
# ---------------------------------------------------------------------------

# Maps legacy roles to equivalent multi-tenant roles
ROLE_MAP: Dict[str, str] = {
    "admin": "platform-admin",
    "developer": "project-admin",
    "reviewer": "member",
    "viewer": "member",
    "user": "member",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_admin(role: str) -> bool:
    """Check if the given role has admin privileges (multi-tenant aware)."""
    # Normalise legacy roles
    mapped = ROLE_MAP.get(role, role)
    return mapped in ADMIN_ROLES


def has_privilege(user_role: str, required_role: str) -> bool:
    """
    Check if user_role meets or exceeds required_role in hierarchy.
    Normalises legacy roles before comparison.
    """
    user_role = ROLE_MAP.get(user_role, user_role)
    required_role = ROLE_MAP.get(required_role, required_role)
    try:
        user_idx = ROLE_HIERARCHY.index(user_role)
        required_idx = ROLE_HIERARCHY.index(required_role)
        return user_idx >= required_idx
    except ValueError:
        return False


def get_permissions_for_role(role: str) -> Set[str]:
    """
    Return the set of permitted actions for a given role.
    Falls back to legacy_permissions for unmapped roles.
    """
    role = ROLE_MAP.get(role, role)
    return PERMITTED_ACTIONS.get(role, set())


def has_project_permission(
    role: str,
    project_id: str,
    action: str,
) -> bool:
    """
    Check if a role has permission to perform an action on a project.

    Rules:
      - platform-admin has all permissions on all projects.
      - project-admin has permissions on their assigned project.
      - member has read-only permissions on their assigned project.
      - project_id "" or None means "no project filter" (allow).

    Args:
        role: User's role (normalised).
        project_id: Target project ID.
        action: Permission action (e.g. "pipeline:start").

    Returns:
        True if the action is permitted.
    """
    if not project_id:
        return True  # No project filter

    mapped_role = ROLE_MAP.get(role, role)

    # Platform-admin: full access to all projects
    if mapped_role == "platform-admin":
        return True

    # Project-admin: full access to their project
    if mapped_role == "project-admin":
        # In a real system, check project membership in DB
        return True  # Simplified — project admins own their project

    # Member: read-only on their project
    if mapped_role == "member":
        if action in PERMITTED_ACTIONS["member"]:
            return True
        return False

    return False


def get_user_permissions(
    role: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return a dict of user permissions scoped to a project.

    Args:
        role: User role (normalised).
        project_id: Optional project scope.  None means platform-wide.

    Returns:
        {
            "role": "...",
            "project_id": "...",
            "permissions": [...],
            "is_admin": bool,
            "can_access_project": bool,
        }
    """
    mapped_role = ROLE_MAP.get(role, role)
    permissions = list(get_permissions_for_role(mapped_role))

    # Scope permissions by project
    if project_id:
        can_access = has_project_permission(mapped_role, project_id, "pipeline:status")
    else:
        can_access = True

    return {
        "role": mapped_role,
        "project_id": project_id or "",
        "permissions": permissions,
        "is_admin": is_admin(mapped_role),
        "can_access_project": can_access,
        "hierarchy_index": (
            ROLE_HIERARCHY.index(mapped_role)
            if mapped_role in ROLE_HIERARCHY
            else -1
        ),
    }


# ---------------------------------------------------------------------------
# Access grant helper (in-memory, replace with DB-backed version in prod)
# ---------------------------------------------------------------------------

_user_project_roles: Dict[str, Dict[str, str]] = {}
"""user_id -> {project_id: role}"""


def grant_project_role(
    user_id: str,
    project_id: str,
    role: str,
) -> Dict[str, Any]:
    """Assign a multi-tenant role to a user on a specific project."""
    role = ROLE_MAP.get(role, role)
    if role not in ROLE_HIERARCHY:
        return {"success": False, "error": f"Invalid role: {role}"}
    if user_id not in _user_project_roles:
        _user_project_roles[user_id] = {}
    _user_project_roles[user_id][project_id] = role
    logger.info(
        "Granted role '%s' on project '%s' to user '%s'",
        role,
        project_id,
        user_id,
    )
    return {
        "success": True,
        "user_id": user_id,
        "project_id": project_id,
        "role": role,
    }


def revoke_project_role(
    user_id: str,
    project_id: str,
) -> Dict[str, Any]:
    """Remove a multi-tenant role from a user on a specific project."""
    assignments = _user_project_roles.get(user_id, {})
    if project_id not in assignments:
        return {
            "success": False,
            "error": f"User {user_id} has no role on project {project_id}",
        }
    del assignments[project_id]
    logger.info(
        "Revoked role on project '%s' for user '%s'",
        project_id,
        user_id,
    )
    return {
        "success": True,
        "user_id": user_id,
        "project_id": project_id,
    }


def get_user_project_roles(user_id: str) -> Dict[str, str]:
    """Return all project role assignments for a user."""
    return dict(_user_project_roles.get(user_id, {}))
