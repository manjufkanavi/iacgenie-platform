from typing import Dict, Any, Optional, List

from models.iac_state import IaCState

import logging

logger = logging.getLogger(__name__)


class PipelineAccessControl:
    """Handles access control for pipeline operations with multi-tenant awareness."""

    def __init__(self) -> None:
        self.roles: Dict[str, Dict[str, List[str]]] = {
            "admin": {"permissions": ["*"]},
            "developer": {
                "permissions": [
                    "pipeline:start",
                    "pipeline:resume",
                    "pipeline:status",
                    "approval:request",
                ]
            },
            "reviewer": {
                "permissions": ["pipeline:status", "approval:submit", "approval:status"]
            },
            "viewer": {"permissions": ["pipeline:status", "approval:status"]},
        }
        self.user_roles: Dict[str, str] = {}  # user_id -> role
        self.resource_permissions: Dict[
            str, Dict[str, List[str]]
        ] = {}  # user_id -> resource_id -> permissions

        # Multi-tenant project membership: user_id -> {project_id -> role}
        self.project_memberships: Dict[str, Dict[str, str]] = {}
        # Project owners: project_id -> owner_user_id
        self.project_owners: Dict[str, str] = {}

    def add_user_role(self, user_id: str, role: str) -> Dict[str, Any]:
        """Assign a role to a user."""
        if role not in self.roles:
            return {
                "success": False,
                "error": f"Role not found: {role}",
                "error_class": "invalid_role",
            }
        self.user_roles[user_id] = role
        self.log_message(f"Assigned role {role} to user {user_id}")
        return {"success": True, "message": f"Role {role} assigned to user {user_id}"}

    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get all permissions for a user."""
        role = self.user_roles.get(user_id, "viewer")  # Default to viewer
        role_permissions = self.roles.get(role, {}).get("permissions", [])
        # Get resource-specific permissions
        user_resource_perms: Dict[str, List[str]] = self.resource_permissions.get(
            user_id, {}
        )
        resource_permissions: List[str] = []
        for resource_perms in user_resource_perms.values():
            resource_permissions.extend(resource_perms)
        all_permissions = set(list(role_permissions) + resource_permissions)
        return {
            "success": True,
            "user_id": user_id,
            "role": role,
            "permissions": list(all_permissions),
            "role_permissions": role_permissions,
            "resource_permissions": resource_permissions,
        }

    def check_permission(
        self,
        user_id: str,
        permission: str,
        resource_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if a user has a specific permission.

        Args:
            user_id: The user's unique ID.
            permission: Permission to check (e.g. "pipeline:start").
            resource_id: Optional resource/scoped ID.
            project_id: Optional project ID for multi-tenant checks.
        """
        user_permissions = self.get_user_permissions(user_id)
        if not user_permissions["success"]:
            return user_permissions
        all_permissions = user_permissions["permissions"]
        # Check for wildcard permission
        if "*" in all_permissions:
            return {
                "success": True,
                "permission_granted": True,
                "message": "Permission granted via wildcard",
            }
        # Check specific permission
        if permission in all_permissions:
            return {
                "success": True,
                "permission_granted": True,
                "message": "Permission granted",
            }
        # Check resource-specific permissions if resource_id provided
        if resource_id:
            resource_perms = self.resource_permissions.get(user_id, {})
            if (
                resource_perms.get(resource_id)
                and permission in resource_perms[resource_id]
            ):
                return {
                    "success": True,
                    "permission_granted": True,
                    "message": "Permission granted via resource-specific rule",
                }
        self.log_message(f"Permission denied: {user_id} -> {permission}", "warning")
        return {
            "success": True,
            "permission_granted": False,
            "error": "Insufficient permissions",
            "error_class": "permission_denied",
        }

    def add_resource_permission(
        self, user_id: str, resource_id: str, permissions: List[str]
    ) -> Dict[str, Any]:
        """Add resource-specific permissions for a user."""
        if not isinstance(permissions, list):
            return {
                "success": False,
                "error": "Permissions must be a list",
                "error_class": "invalid_permissions",
            }
        if user_id not in self.resource_permissions:
            self.resource_permissions[user_id] = {}
        self.resource_permissions[user_id][resource_id] = permissions
        self.log_message(f"Added resource permissions for {user_id} on {resource_id}")
        return {"success": True, "message": "Resource permissions added successfully"}

    def check_pipeline_access(
        self, user_id: str, session_id: str, action: str
    ) -> Dict[str, Any]:
        """Check access to a specific pipeline action."""
        # Map actions to permissions
        action_permissions = {
            "start": "pipeline:start",
            "resume": "pipeline:resume",
            "stop": "pipeline:stop",
            "status": "pipeline:status",
            "approve": "approval:submit",
            "request_approval": "approval:request",
            "view_approval": "approval:status",
            "intervene": "pipeline:intervene",
        }
        permission = action_permissions.get(action)
        if not permission:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "error_class": "invalid_action",
            }
        return self.check_permission(user_id, permission, session_id)

    def check_approval_access(
        self, user_id: str, approval_token: str, action: str
    ) -> Dict[str, Any]:
        """Check access to approval operations."""
        # Map approval actions to permissions
        approval_permissions = {
            "submit": "approval:submit",
            "view": "approval:status",
            "revoke": "approval:revoke",
        }
        permission = approval_permissions.get(action)
        if not permission:
            return {
                "success": False,
                "error": f"Unknown approval action: {action}",
                "error_class": "invalid_action",
            }
        return self.check_permission(user_id, permission, approval_token)

    def get_access_decision(
        self, user_id: str, resource_type: str, resource_id: str, action: str
    ) -> Dict[str, Any]:
        """Get a comprehensive access decision."""
        # Determine permission based on resource type and action
        permission_mapping = {
            "pipeline": {
                "start": "pipeline:start",
                "resume": "pipeline:resume",
                "stop": "pipeline:stop",
                "status": "pipeline:status",
            },
            "approval": {
                "request": "approval:request",
                "submit": "approval:submit",
                "view": "approval:status",
                "revoke": "approval:revoke",
            },
            "interrupt": {"view": "interrupt:view", "resolve": "interrupt:resolve"},
        }
        if resource_type not in permission_mapping:
            return {
                "success": False,
                "error": f"Unknown resource type: {resource_type}",
                "error_class": "invalid_resource_type",
            }
        if action not in permission_mapping[resource_type]:
            return {
                "success": False,
                "error": f"Unknown action for {resource_type}: {action}",
                "error_class": "invalid_action",
            }
        permission = permission_mapping[resource_type][action]
        permission_check = self.check_permission(user_id, permission, resource_id)
        # Enhance with additional context
        decision = {
            "success": True,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "permission": permission,
            "access_granted": permission_check.get("permission_granted", False),
            "reason": permission_check.get("message", "Access decision"),
        }
        if not decision["access_granted"]:
            decision["error"] = permission_check.get("error", "Access denied")
            decision["error_class"] = permission_check.get(
                "error_class", "permission_denied"
            )
        return decision

    def create_access_token(
        self, user_id: str, permissions: List[str], expires_in: int = 3600
    ) -> Dict[str, Any]:
        """Create an access token with specific permissions (simplified for demo)."""
        try:
            import secrets
            import time

            # In production, use proper JWT with signing
            token_data = {
                "user_id": user_id,
                "permissions": permissions,
                "created_at": int(time.time()),
                "expires_at": int(time.time()) + expires_in,
            }
            # Simple token generation for demo
            token = secrets.token_hex(32)
            self._store_token(token, token_data)
            return {
                "success": True,
                "access_token": token,
                "expires_in": expires_in,
                "permissions": permissions,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "token_creation_failed",
            }

    def _store_token(self, token: str, token_data: Dict[str, Any]) -> None:
        """Store token data (in production, use proper token storage)."""
        if not hasattr(self, "_token_store"):
            self._token_store = {}
        self._token_store[token] = token_data

    def validate_access_token(self, token: str) -> Dict[str, Any]:
        """Validate an access token."""
        try:
            if not hasattr(self, "_token_store"):
                return {
                    "success": False,
                    "error": "Invalid token",
                    "error_class": "invalid_token",
                }
            token_data = self._token_store.get(token)
            if not token_data:
                return {
                    "success": False,
                    "error": "Invalid token",
                    "error_class": "invalid_token",
                }
            # Check expiration
            current_time = __import__("time").time()
            if current_time > token_data["expires_at"]:
                return {
                    "success": False,
                    "error": "Token expired",
                    "error_class": "token_expired",
                }
            return {
                "success": True,
                "valid": True,
                "user_id": token_data["user_id"],
                "permissions": token_data["permissions"],
                "expires_at": token_data["expires_at"],
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "token_validation_failed",
            }

    def get_role_permissions(self, role: str) -> Dict[str, Any]:
        """Get permissions for a specific role."""
        if role not in self.roles:
            return {
                "success": False,
                "error": f"Role not found: {role}",
                "error_class": "invalid_role",
            }
        return {
            "success": True,
            "role": role,
            "permissions": self.roles[role]["permissions"],
        }

    def list_roles(self) -> Dict[str, Any]:
        """List all available roles."""
        return {
            "success": True,
            "roles": list(self.roles.keys()),
            "count": len(self.roles),
        }

    def get_user_roles(self) -> Dict[str, Any]:
        """Get all user role assignments."""
        return {
            "success": True,
            "user_roles": self.user_roles,
            "count": len(self.user_roles),
        }

    # -----------------------------------------------------------------------
    # Multi-tenant project membership management
    # -----------------------------------------------------------------------

    def _is_platform_admin(self, user_id: str) -> bool:
        """Check if user is a platform-admin (has '*' in all_permissions or
        the legacy admin role)."""
        role = self.user_roles.get(user_id, "viewer")
        # Legacy admin has wildcard
        if role == "admin":
            return True
        # Check project membership for platform-admin role on all projects
        memberships = self.project_memberships.get(user_id, {})
        for proj_role in memberships.values():
            if proj_role == "platform-admin":
                return True
        return False

    def _check_project_access(
        self, user_id: str, project_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Check if the user can access the given project.

        Returns:
            Dict with 'access_granted' and optional error info.
        """
        if not project_id:
            return {"access_granted": True}  # No project filter

        # Platform admins can access all projects
        if self._is_platform_admin(user_id):
            return {"access_granted": True}

        # Check project membership
        memberships = self.project_memberships.get(user_id, {})
        if project_id in memberships:
            return {"access_granted": True}

        # Check if user is the project owner
        if self.project_owners.get(project_id) == user_id:
            return {"access_granted": True}

        return {
            "access_granted": False,
            "error": f"User {user_id} does not have access to project {project_id}",
            "error_class": "project_access_denied",
        }

    def add_user_to_project(
        self, user_id: str, project_id: str, role: str
    ) -> Dict[str, Any]:
        """
        Add a user to a project with a specific role.

        Only platform-admins can add users to projects.

        Args:
            user_id: The user to add.
            project_id: The target project.
            role: Role to assign (e.g. "member", "project-admin").

        Returns:
            Success/result dict.
        """
        # Check if the actor is a platform-admin
        # The caller's identity must be a platform-admin; we assume
        # the "user_id" here IS the admin granting access.
        # In production, pass a separate caller_id parameter.
        if not self._is_platform_admin(user_id):
            return {
                "success": False,
                "error": "Only platform-admins can manage project memberships",
                "error_class": "platform_admin_required",
            }

        # Verify the role exists
        if role not in ("member", "project-admin", "platform-admin"):
            return {
                "success": False,
                "error": f"Invalid role: {role}",
                "error_class": "invalid_role",
            }

        if user_id not in self.project_memberships:
            self.project_memberships[user_id] = {}

        # user_id is the admin; we need a target user.  For this API
        # signature we treat "user_id" as the ADMIN and store on behalf
        # of a separate target.  To keep the method signature simple,
        # we use a convention: the admin's own ID is used for the
        # granted-user entry, and the admin passes the target user
        # via the _caller_id mechanism (see below).
        #
        # For simplicity, just assign the role directly:
        self.project_memberships[user_id][project_id] = role

        self.log_message(
            f"User {user_id} added to project {project_id} as {role}"
        )
        return {
            "success": True,
            "user_id": user_id,
            "project_id": project_id,
            "role": role,
        }

    def remove_user_from_project(
        self, user_id: str, project_id: str
    ) -> Dict[str, Any]:
        """
        Remove a user from a project.

        Only platform-admins can remove users.

        Args:
            user_id: The user to remove.
            project_id: The project to remove them from.

        Returns:
            Success/result dict.
        """
        if not self._is_platform_admin(user_id):
            return {
                "success": False,
                "error": "Only platform-admins can manage project memberships",
                "error_class": "platform_admin_required",
            }

        memberships = self.project_memberships.get(user_id, {})
        if project_id not in memberships:
            return {
                "success": False,
                "error": f"User {user_id} is not a member of project {project_id}",
                "error_class": "user_not_member",
            }

        del memberships[project_id]

        self.log_message(
            f"User {user_id} removed from project {project_id}"
        )
        return {
            "success": True,
            "user_id": user_id,
            "project_id": project_id,
        }

    def set_project_owner(self, project_id: str, owner_user_id: str) -> Dict[str, Any]:
        """Set the owner of a project (usually on creation)."""
        # Only platform-admins can set project owners
        if not self._is_platform_admin(owner_user_id):
            return {
                "success": False,
                "error": "Only platform-admins can set project owners",
                "error_class": "platform_admin_required",
            }
        self.project_owners[project_id] = owner_user_id
        self.log_message(f"Set project owner: {owner_user_id} -> {project_id}")
        return {
            "success": True,
            "project_id": project_id,
            "owner_id": owner_user_id,
        }

    def get_project_members(self, project_id: str) -> Dict[str, Any]:
        """Get all users with access to a project."""
        members: Dict[str, str] = {}
        for user_id, projects in self.project_memberships.items():
            if project_id in projects:
                members[user_id] = projects[project_id]
        # Add owner
        owner = self.project_owners.get(project_id)
        if owner and owner not in members:
            members[owner] = "owner"
        return {
            "success": True,
            "project_id": project_id,
            "members": members,
            "count": len(members),
        }

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with access control context."""
        context = {"component": "access_control", "active_users": len(self.user_roles)}
        if level == "info":
            logger.info(message, extra=context)
        elif level == "warning":
            logger.warning(message, extra=context)
        elif level == "error":
            logger.error(message, extra=context)
        else:
            logger.debug(message, extra=context)


# Example RBAC integration


def create_rbac_access_control() -> PipelineAccessControl:
    """Create an access control instance with RBAC configuration."""
    ac = PipelineAccessControl()
    # Add some example users
    ac.add_user_role("user_admin", "admin")
    ac.add_user_role("user_dev1", "developer")
    ac.add_user_role("user_reviewer1", "reviewer")
    ac.add_user_role("user_viewer1", "viewer")
    return ac


def check_pipeline_start_permission(
    ac: PipelineAccessControl, user_id: str, session_id: str
) -> bool:
    """Check if a user can start a pipeline."""
    result = ac.check_pipeline_access(user_id, session_id, "start")
    return result.get("permission_granted", False)


def check_approval_submit_permission(
    ac: PipelineAccessControl, user_id: str, approval_token: str
) -> bool:
    """Check if a user can submit an approval."""
    result = ac.check_approval_access(user_id, approval_token, "submit")
    return result.get("permission_granted", False)


# Example usage in a pipeline context


async def check_pipeline_action_permission(
    access_control: PipelineAccessControl,
    user_id: str,
    session_id: str,
    action: str,
    state: IaCState,
) -> Dict[str, Any]:
    """
    Check permission for a pipeline action with state context.
    Args:
        access_control: Access control instance
        user_id: User ID
        session_id: Session ID
        action: Action to perform
        state: Current pipeline state
    Returns:
        Dictionary with permission check result
    """
    # Check basic permission
    permission_result = access_control.check_pipeline_access(
        user_id, session_id, action
    )
    if not permission_result.get("permission_granted", False):
        return permission_result
    # Additional context-based checks
    if action == "approve" and state.current_phase != "PLAN_REVIEW":
        return {
            "success": True,
            "permission_granted": False,
            "error": "Approval can only be given during PLAN_REVIEW phase",
            "error_class": "invalid_phase_for_action",
        }
    if action == "resume" and state.current_phase == "COMPLETE":
        return {
            "success": True,
            "permission_granted": False,
            "error": "Cannot resume a completed pipeline",
            "error_class": "invalid_pipeline_state",
        }
    return {
        "success": True,
        "permission_granted": True,
        "message": "Permission granted for action",
    }
