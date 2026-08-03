import os

import tempfile

import shutil

import uuid

from typing import Dict, Any, Optional

import logging

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages isolated workspaces for pipeline execution."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or tempfile.gettempdir()
        self.active_workspaces: Dict[str, str] = {}  # session_id -> workspace_path
        self.workspace_quotas = {
            "max_workspaces": 100,
            "max_size_mb": 1000,  # 1GB per workspace
            "max_age_days": 7,  # Auto-cleanup after 7 days
        }

    def create_workspace(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new isolated workspace.
        Args:
            session_id: Optional session ID (will generate if not provided)
        Returns:
            Dictionary with workspace creation result
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            # Check quota limits
            if len(self.active_workspaces) >= self.workspace_quotas["max_workspaces"]:
                return {
                    "success": False,
                    "error": f"Maximum workspaces limit reached: {self.workspace_quotas['max_workspaces']}",
                    "error_class": "quota_exceeded",
                }
            # Create workspace directory
            workspace_name = f"workspace_{session_id}"
            workspace_path = os.path.join(self.base_dir, workspace_name)
            # Ensure base directory exists
            os.makedirs(self.base_dir, exist_ok=True)
            # Create the workspace
            os.makedirs(workspace_path, exist_ok=True)
            # Initialize workspace structure
            self._initialize_workspace_structure(workspace_path)
            # Register the workspace
            self.active_workspaces[session_id] = workspace_path
            self.log_message(f"Created workspace: {workspace_path}")
            return {
                "success": True,
                "session_id": session_id,
                "workspace_path": workspace_path,
                "message": "Workspace created successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "workspace_creation_failed",
            }

    def _initialize_workspace_structure(self, workspace_path: str) -> None:
        """Initialize the standard workspace structure."""
        # Create standard directories
        dirs = ["config", "logs", "outputs", "temp"]
        for dir_name in dirs:
            os.makedirs(os.path.join(workspace_path, dir_name), exist_ok=True)
        # Create standard files
        with open(os.path.join(workspace_path, "README.txt"), "w") as f:
            f.write(
                f"TerraGenius Pipeline Workspace\nSession: {os.path.basename(workspace_path)}\n"
            )

    def get_workspace(self, session_id: str) -> Dict[str, Any]:
        """
        Get workspace information.
        Args:
            session_id: Session ID
        Returns:
            Dictionary with workspace information
        """
        workspace_path = self.active_workspaces.get(session_id)
        if not workspace_path:
            return {
                "success": False,
                "error": f"Workspace not found: {session_id}",
                "error_class": "workspace_not_found",
            }
        # Get workspace stats
        stats = self._get_workspace_stats(workspace_path)
        return {
            "success": True,
            "session_id": session_id,
            "workspace_path": workspace_path,
            "stats": stats,
            "message": "Workspace retrieved successfully",
        }

    def _get_workspace_stats(self, workspace_path: str) -> Dict[str, Any]:
        """Get statistics about a workspace."""
        stats = {
            "file_count": 0,
            "directory_count": 0,
            "total_size_bytes": 0,
            "created_at": 0.0,
            "last_modified": 0.0,
        }
        try:
            # Count files and directories
            for root, dirs, files in os.walk(workspace_path):
                stats["file_count"] += len(files)
                stats["directory_count"] += len(dirs)
            # Get creation and modification times
            stats["created_at"] = os.path.getctime(workspace_path)
            stats["last_modified"] = os.path.getmtime(workspace_path)
            # Calculate total size
            for root, dirs, files in os.walk(workspace_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        stats["total_size_bytes"] += os.path.getsize(file_path)
                    except Exception:
                        pass
        except Exception as e:
            self.log_message(f"Failed to get workspace stats: {str(e)}", "warning")
        return stats

    def cleanup_workspace(self, session_id: str) -> Dict[str, Any]:
        """
        Clean up a workspace.
        Args:
            session_id: Session ID
        Returns:
            Dictionary with cleanup result
        """
        workspace_path = self.active_workspaces.get(session_id)
        if not workspace_path:
            return {
                "success": False,
                "error": f"Workspace not found: {session_id}",
                "error_class": "workspace_not_found",
            }
        try:
            # Remove the workspace directory
            shutil.rmtree(workspace_path)
            # Remove from active workspaces
            del self.active_workspaces[session_id]
            self.log_message(f"Cleaned up workspace: {workspace_path}")
            return {"success": True, "message": "Workspace cleaned up successfully"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "workspace_cleanup_failed",
            }

    def list_workspaces(self) -> Dict[str, Any]:
        """List all active workspaces."""
        workspace_list = []
        for session_id, workspace_path in self.active_workspaces.items():
            stats = self._get_workspace_stats(workspace_path)
            workspace_list.append(
                {
                    "session_id": session_id,
                    "workspace_path": workspace_path,
                    "stats": stats,
                }
            )
        return {
            "success": True,
            "workspaces": workspace_list,
            "count": len(workspace_list),
            "quota_usage": {
                "current": len(self.active_workspaces),
                "max": self.workspace_quotas["max_workspaces"],
            },
        }

    def validate_workspace(self, session_id: str) -> Dict[str, Any]:
        """
        Validate a workspace meets requirements.
        Args:
            session_id: Session ID
        Returns:
            Dictionary with validation result
        """
        workspace_path = self.active_workspaces.get(session_id)
        if not workspace_path:
            return {
                "success": False,
                "error": f"Workspace not found: {session_id}",
                "error_class": "workspace_not_found",
            }
        # Check workspace exists
        if not os.path.exists(workspace_path):
            return {
                "success": False,
                "error": f"Workspace directory does not exist: {workspace_path}",
                "error_class": "workspace_invalid",
            }
        # Check required structure
        required_dirs = ["config", "logs", "outputs"]
        missing_dirs = []
        for dir_name in required_dirs:
            dir_path = os.path.join(workspace_path, dir_name)
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_name)
        if missing_dirs:
            return {
                "success": False,
                "error": f"Missing required directories: {', '.join(missing_dirs)}",
                "error_class": "workspace_invalid",
                "missing_dirs": missing_dirs,
            }
        # Check workspace size
        stats = self._get_workspace_stats(workspace_path)
        max_size_bytes = self.workspace_quotas["max_size_mb"] * 1024 * 1024
        if stats["total_size_bytes"] > max_size_bytes:
            return {
                "success": False,
                "error": f"Workspace exceeds size limit: {stats['total_size_bytes']} > {max_size_bytes} bytes",
                "error_class": "workspace_quota_exceeded",
                "current_size_mb": stats["total_size_bytes"] / (1024 * 1024),
                "max_size_mb": self.workspace_quotas["max_size_mb"],
            }
        return {"success": True, "message": "Workspace is valid", "stats": stats}

    def set_workspace_quota(self, quota_type: str, value: int) -> Dict[str, Any]:
        """
        Set a workspace quota.
        Args:
            quota_type: Type of quota to set (max_workspaces, max_size_mb, max_age_days)
            value: New quota value
        Returns:
            Dictionary with quota update result
        """
        if quota_type not in self.workspace_quotas:
            return {
                "success": False,
                "error": f"Invalid quota type: {quota_type}",
                "error_class": "invalid_quota_type",
            }
        if value <= 0:
            return {
                "success": False,
                "error": "Quota value must be positive",
                "error_class": "invalid_quota_value",
            }
        self.workspace_quotas[quota_type] = value
        self.log_message(f"Updated quota {quota_type} to {value}")
        return {
            "success": True,
            "message": f"Quota {quota_type} updated to {value}",
            "current_quotas": self.workspace_quotas,
        }

    def get_workspace_quotas(self) -> Dict[str, Any]:
        """Get current workspace quotas."""
        return {
            "success": True,
            "quotas": self.workspace_quotas,
            "current_usage": {
                "active_workspaces": len(self.active_workspaces),
                "estimated_total_size_mb": sum(
                    self._get_workspace_stats(path)["total_size_bytes"] / (1024 * 1024)
                    for path in self.active_workspaces.values()
                ),
            },
        }

    async def cleanup_old_workspaces(self) -> Dict[str, Any]:
        """Clean up workspaces older than max_age_days."""
        try:
            cutoff_time = __import__("time").time() - (
                self.workspace_quotas["max_age_days"] * 24 * 60 * 60
            )
            cleaned_count = 0
            sessions_to_clean = []
            for session_id, workspace_path in self.active_workspaces.items():
                try:
                    created_time = os.path.getctime(workspace_path)
                    if created_time < cutoff_time:
                        sessions_to_clean.append(session_id)
                except Exception:
                    continue
            for session_id in sessions_to_clean:
                cleanup_result = self.cleanup_workspace(session_id)
                if cleanup_result["success"]:
                    cleaned_count += 1
                else:
                    self.log_message(
                        f"Failed to cleanup old workspace {session_id}: {cleanup_result['error']}",
                        "warning",
                    )
            self.log_message(f"Cleaned up {cleaned_count} old workspaces")
            return {
                "success": True,
                "message": f"Cleaned up {cleaned_count} old workspaces",
                "cleaned_count": cleaned_count,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "workspace_cleanup_failed",
            }

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with workspace manager context."""
        context = {
            "component": "workspace_manager",
            "active_workspaces": len(self.active_workspaces),
        }
        if level == "info":
            logger.info(message, extra=context)
        elif level == "warning":
            logger.warning(message, extra=context)
        elif level == "error":
            logger.error(message, extra=context)
        else:
            logger.debug(message, extra=context)


# Example workspace validation handlers


def validate_terraform_workspace(workspace_path: str) -> Dict[str, Any]:
    """Validate a workspace for Terraform operations."""
    required_files = ["main.tf"]
    missing_files = []
    for file_name in required_files:
        file_path = os.path.join(workspace_path, file_name)
        if not os.path.exists(file_path):
            missing_files.append(file_name)
    if missing_files:
        return {
            "valid": False,
            "error": f"Missing required Terraform files: {', '.join(missing_files)}",
            "missing_files": missing_files,
        }
    return {"valid": True, "message": "Terraform workspace is valid"}


def validate_security_workspace(workspace_path: str) -> Dict[str, Any]:
    """Validate a workspace for security requirements."""
    # Check for sensitive files that shouldn't be present
    sensitive_files = [".env", "secrets.json", "credentials.txt"]
    found_sensitive = []
    for root, dirs, files in os.walk(workspace_path):
        for file in files:
            if any(sensitive in file.lower() for sensitive in sensitive_files):
                found_sensitive.append(os.path.join(root, file))
    if found_sensitive:
        return {
            "valid": False,
            "error": f"Found sensitive files that should be removed: {', '.join(found_sensitive)}",
            "sensitive_files": found_sensitive,
        }
    return {"valid": True, "message": "Workspace meets security requirements"}
