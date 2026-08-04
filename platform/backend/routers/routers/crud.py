"""

Unified CRUD routers for all database entities

Works with any database adapter through the database provider

"""

from fastapi import APIRouter, HTTPException, Depends, Query

from typing import Optional, Dict, Any

import logging

import json

from db.db_provider import db_provider

# Dependency function to get database adapter


async def get_db():
    """Get database adapter for dependency injection"""
    return db_provider.adapter


from db.adapters.base import IDatabaseAdapter

from middleware.auth_middleware import get_user_id, require_admin

from schemas.crud_schemas import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigRotate,
    GitRepositoryCreate,
    GitRepositoryUpdate,
    CloudCredentialsCreate,
    CloudCredentialsUpdate,
    TeamMemberCreate,
    TeamMemberUpdate,
    IntegrationCreate,
    IntegrationUpdate,
    ApiKeyCreate,
    ApiKeyUpdate,
    AuditLogCreate,
    GenerationCreate,
    GenerationUpdate,
    DeploymentCreate,
    DeploymentUpdate,
    BillingCreate,
    BillingUpdate,
)

logger = logging.getLogger(__name__)

# Create routers for each entity type

model_configs_router = APIRouter(
    prefix="/api/model-configs", tags=["Model Configurations"]
)

git_repositories_router = APIRouter(
    prefix="/api/git-repositories", tags=["Git Repositories"]
)

cloud_credentials_router = APIRouter(
    prefix="/api/cloud-credentials", tags=["Cloud Credentials"]
)

team_members_router = APIRouter(prefix="/api/team-members", tags=["Team Members"])

integrations_router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

projects_router = APIRouter(prefix="/api/projects", tags=["Projects"])

api_keys_router = APIRouter(prefix="/api/api-keys", tags=["API Keys"])

audit_logs_router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])

generations_router = APIRouter(prefix="/api/generations", tags=["Generations"])

deployments_router = APIRouter(prefix="/api/deployments", tags=["Deployments"])

billing_router = APIRouter(prefix="/api/billing", tags=["Billing"])
# Helper function to get current user ID


async def get_current_user_id(user_id: str = Depends(get_user_id)) -> str:
    """Get current user ID from authenticated token"""
    return user_id


async def check_admin_or_owner(
    project_id: str, current_user_id: str, db: IDatabaseAdapter
) -> None:
    """Ensure the user is the project owner or has admin role in the team members list"""
    try:
        # Check if user is the project owner
        project = await db.get_project(current_user_id, project_id)
        if project:
            return
    except Exception:
        pass
    try:
        # Check team members list for role
        members = await db.list_team_members(current_user_id, project_id)
        if members:
            user_email = None
            try:
                user = await db.get_user(current_user_id)
                if user:
                    user_email = user.get("email")
            except Exception:
                pass
            for member in members:
                if member.get("user_id") == current_user_id and member.get("role") in [
                    "owner",
                    "admin",
                ]:
                    return
                if (
                    user_email
                    and member.get("email") == user_email
                    and member.get("role") in ["owner", "admin"]
                ):
                    return
    except Exception:
        pass
    raise HTTPException(
        status_code=403,
        detail="Only project owners and admins can access or modify these settings",
    )


# Model Configurations CRUD


@model_configs_router.get("/{project_id}")
async def list_model_configs(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all model configurations for a project"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        configs = await db.list_model_configs(current_user_id, project_id)
        return {"configs": configs}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list model configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@model_configs_router.post("/{project_id}")
async def create_model_config(
    project_id: str,
    config: ModelConfigCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new model configuration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.create_model_config(
            current_user_id, project_id, config.model_dump()
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create model config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@model_configs_router.get("/{project_id}/{config_id}")
async def get_model_config(
    project_id: str,
    config_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get a model configuration by ID"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        config = await db.get_model_config(current_user_id, project_id, config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Model configuration not found")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@model_configs_router.put("/{project_id}/{config_id}")
async def update_model_config(
    project_id: str,
    config_id: str,
    config: ModelConfigUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update a model configuration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.update_model_config(
            current_user_id,
            project_id,
            config_id,
            config.model_dump(exclude_unset=True),
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update model config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@model_configs_router.delete("/{project_id}/{config_id}")
async def delete_model_config(
    project_id: str,
    config_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a model configuration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        success = await db.delete_model_config(current_user_id, project_id, config_id)
        if not success:
            raise HTTPException(status_code=404, detail="Model configuration not found")
        return {"message": "Model configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete model config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@model_configs_router.post("/{project_id}/{config_id}/test")
async def test_model_config(
    project_id: str,
    config_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Test a model configuration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.test_model_config(current_user_id, project_id, config_id)
        return {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test model config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@model_configs_router.post("/{project_id}/{config_id}/rotate")
async def rotate_model_config_key(
    project_id: str,
    config_id: str,
    rotation: ModelConfigRotate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Rotate API key for a model configuration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)

        from datetime import datetime

        expires_at = None
        if rotation.expires_at:
            try:
                expires_at = datetime.fromisoformat(
                    rotation.expires_at.replace("Z", "+00:00")
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format for expires_at"
                )

        result = await db.update_model_config(
            current_user_id,
            project_id,
            config_id,
            {"api_key": rotation.api_key, "expires_at": expires_at},
        )
        if not result:
            raise HTTPException(status_code=404, detail="Model configuration not found")
        return {"message": "API key rotated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rotate model config key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Git Repositories CRUD


@git_repositories_router.get("/{project_id}")
async def list_git_repositories(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all git repositories for a project"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        repos = await db.list_git_repositories(current_user_id, project_id)
        return {"repositories": repos}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list git repositories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@git_repositories_router.post("/{project_id}")
async def create_git_repository(
    project_id: str,
    repo: GitRepositoryCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new git repository"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.create_git_repository(
            current_user_id, project_id, repo.model_dump()
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create git repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@git_repositories_router.get("/{project_id}/{repo_id}")
async def get_git_repository(
    project_id: str,
    repo_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get a git repository by ID"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        repo = await db.get_git_repository(current_user_id, project_id, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Git repository not found")
        return repo
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get git repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@git_repositories_router.put("/{project_id}/{repo_id}")
async def update_git_repository(
    project_id: str,
    repo_id: str,
    repo: GitRepositoryUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update a git repository"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.update_git_repository(
            current_user_id, project_id, repo_id, repo.model_dump(exclude_unset=True)
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update git repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@git_repositories_router.delete("/{project_id}/{repo_id}")
async def delete_git_repository(
    project_id: str,
    repo_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a git repository"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        success = await db.delete_git_repository(current_user_id, project_id, repo_id)
        if not success:
            raise HTTPException(status_code=404, detail="Git repository not found")
        return {"message": "Git repository deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete git repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@git_repositories_router.post("/{project_id}/{repo_id}/test")
async def test_git_repository(
    project_id: str,
    repo_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Test a git repository"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.test_git_repository(current_user_id, project_id, repo_id)
        return {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test git repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Cloud Credentials CRUD


@cloud_credentials_router.get("/{project_id}")
async def list_cloud_credentials(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all cloud credentials for a project"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        credentials = await db.list_cloud_credentials(current_user_id, project_id)
        return {"credentials": credentials}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list cloud credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@cloud_credentials_router.post("/{project_id}")
async def create_cloud_credentials(
    project_id: str,
    credentials: CloudCredentialsCreate,
    admin: Dict[str, Any] = Depends(require_admin),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create new cloud credentials (admin only)"""
    try:
        current_user_id = admin.get("uid")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID missing")
        result = await db.create_cloud_credentials(
            current_user_id, project_id, credentials.model_dump()
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create cloud credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@cloud_credentials_router.get("/{project_id}/{cred_id}")
async def get_cloud_credentials(
    project_id: str,
    cred_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get cloud credentials by ID"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        creds = await db.get_cloud_credentials(current_user_id, project_id, cred_id)
        if not creds:
            raise HTTPException(status_code=404, detail="Cloud credentials not found")
        return creds
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cloud credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@cloud_credentials_router.put("/{project_id}/{cred_id}")
async def update_cloud_credentials(
    project_id: str,
    cred_id: str,
    credentials: CloudCredentialsUpdate,
    admin: Dict[str, Any] = Depends(require_admin),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update cloud credentials (admin only)"""
    try:
        current_user_id = admin.get("uid")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID missing")
        result = await db.update_cloud_credentials(
            current_user_id,
            project_id,
            cred_id,
            credentials.model_dump(exclude_unset=True),
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update cloud credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@cloud_credentials_router.delete("/{project_id}/{cred_id}")
async def delete_cloud_credentials(
    project_id: str,
    cred_id: str,
    admin: Dict[str, Any] = Depends(require_admin),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete cloud credentials (admin only)"""
    try:
        current_user_id = admin.get("uid")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID missing")
        success = await db.delete_cloud_credentials(
            current_user_id, project_id, cred_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Cloud credentials not found")
        return {"message": "Cloud credentials deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete cloud credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@cloud_credentials_router.post("/{project_id}/{cred_id}/test")
async def test_cloud_credentials(
    project_id: str,
    cred_id: str,
    admin: Dict[str, Any] = Depends(require_admin),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Test cloud credentials (admin only)"""
    try:
        current_user_id = admin.get("uid")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID missing")
        result = await db.test_cloud_credentials(current_user_id, project_id, cred_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test cloud credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Team Members CRUD


@team_members_router.get("/{project_id}")
async def list_team_members(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all team members for a project"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        members = await db.list_team_members(current_user_id, project_id)
        return {"members": members}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list team members: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@team_members_router.post("/{project_id}")
async def create_team_member(
    project_id: str,
    member: TeamMemberCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new team member"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.create_team_member(
            current_user_id, project_id, member.model_dump()
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create team member: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@team_members_router.get("/{project_id}/{member_id}")
async def get_team_member(
    project_id: str,
    member_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get a team member by ID"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        member = await db.get_team_member(current_user_id, project_id, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Team member not found")
        return member
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get team member: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@team_members_router.put("/{project_id}/{member_id}")
async def update_team_member(
    project_id: str,
    member_id: str,
    member: TeamMemberUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update a team member"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.update_team_member(
            current_user_id,
            project_id,
            member_id,
            member.model_dump(exclude_unset=True),
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update team member: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@team_members_router.delete("/{project_id}/{member_id}")
async def delete_team_member(
    project_id: str,
    member_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a team member"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        success = await db.delete_team_member(current_user_id, project_id, member_id)
        if not success:
            raise HTTPException(status_code=404, detail="Team member not found")
        return {"message": "Team member deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete team member: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Integrations CRUD


@integrations_router.get("/{project_id}")
async def list_integrations(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all integrations for a project"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        integrations = await db.list_integrations(current_user_id, project_id)
        return {"integrations": integrations}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list integrations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@integrations_router.post("/{project_id}")
async def create_integration(
    project_id: str,
    integration: IntegrationCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new integration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.create_integration(
            current_user_id, project_id, integration.model_dump()
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@integrations_router.get("/{project_id}/{integration_id}")
async def get_integration(
    project_id: str,
    integration_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get an integration by ID"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        integration = await db.get_integration(
            current_user_id, project_id, integration_id
        )
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        return integration
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@integrations_router.put("/{project_id}/{integration_id}")
async def update_integration(
    project_id: str,
    integration_id: str,
    integration: IntegrationUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update an integration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.update_integration(
            current_user_id,
            project_id,
            integration_id,
            integration.model_dump(exclude_unset=True),
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@integrations_router.delete("/{project_id}/{integration_id}")
async def delete_integration(
    project_id: str,
    integration_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete an integration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        success = await db.delete_integration(
            current_user_id, project_id, integration_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Integration not found")
        return {"message": "Integration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@integrations_router.post("/{project_id}/{integration_id}/test")
async def test_integration(
    project_id: str,
    integration_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Test an integration"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.test_integration(current_user_id, project_id, integration_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Projects CRUD


@projects_router.get("/")
async def list_projects(
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all projects for the current user"""
    try:
        projects = await db.list_projects(current_user_id)
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Failed to list projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@projects_router.post("/")
async def create_project(
    project: Dict[str, Any],
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new project"""
    try:
        result = await db.create_project(current_user_id, project)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@projects_router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get a project by ID"""
    try:
        project = await db.get_project(current_user_id, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@projects_router.put("/{project_id}")
async def update_project(
    project_id: str,
    project: Dict[str, Any],
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update a project"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        result = await db.update_project(current_user_id, project_id, project)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@projects_router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a project"""
    try:
        await check_admin_or_owner(project_id, current_user_id, db)
        success = await db.delete_project(current_user_id, project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# API Keys CRUD


@api_keys_router.get("/")
async def list_api_keys(
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all API keys for the current user"""
    try:
        keys = await db.list_api_keys(current_user_id)
        return {"api_keys": keys}
    except Exception as e:
        logger.error(f"Failed to list API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_keys_router.post("/")
async def create_api_key(
    api_key: ApiKeyCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new API key"""
    try:
        result = await db.create_api_key(current_user_id, api_key.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_keys_router.get("/{key_id}")
async def get_api_key(
    key_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get an API key by ID"""
    try:
        key = await db.get_api_key(current_user_id, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="API key not found")
        return key
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_keys_router.put("/{key_id}")
async def update_api_key(
    key_id: str,
    api_key: ApiKeyUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update an API key"""
    try:
        result = await db.update_api_key(
            current_user_id, key_id, api_key.model_dump(exclude_unset=True)
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_keys_router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete an API key"""
    try:
        success = await db.delete_api_key(current_user_id, key_id)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        return {"message": "API key deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Audit Logs CRUD


@audit_logs_router.get("/")
async def list_audit_logs(
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List audit logs with optional filters"""
    try:
        parsed_filters = None
        if filters:
            try:
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filters JSON")
        logs = await db.list_audit_logs(current_user_id, parsed_filters)
        return {"audit_logs": logs}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@audit_logs_router.post("/")
async def create_audit_log(
    log: AuditLogCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new audit log entry"""
    try:
        result = await db.create_audit_log(current_user_id, log.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Generations CRUD


@generations_router.get("/{project_id}")
async def list_generations(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all generation jobs for a project"""
    try:
        generations = await db.list_generation_jobs(project_id)
        return {"generations": generations}
    except Exception as e:
        logger.error(f"Failed to list generations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@generations_router.post("/{project_id}")
async def create_generation(
    project_id: str,
    generation: GenerationCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new generation job"""
    try:
        job_data = {
            "prompt": generation.prompt,
            "model": generation.model,
            "provider": generation.provider,
            "project_id": project_id,
            "user_id": current_user_id,
            "model_config_id": generation.model_config_id,
            "status": generation.status,
            "metadata": generation.metadata,
        }
        job_id = await db.create_generation_job(job_data)
        return {"job_id": job_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create generation job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@generations_router.get("/{project_id}/{generation_id}")
async def get_generation(
    project_id: str,
    generation_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get a generation job by ID"""
    try:
        generation = await db.get_generation_job(generation_id)
        if not generation:
            raise HTTPException(status_code=404, detail="Generation not found")
        return generation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get generation job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@generations_router.put("/{project_id}/{generation_id}")
async def update_generation(
    project_id: str,
    generation_id: str,
    generation: GenerationUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update a generation job"""
    try:
        updates = generation.model_dump(exclude_unset=True)
        success = await db.update_generation_job(generation_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Generation job not found")
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update generation job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@generations_router.delete("/{project_id}/{generation_id}")
async def delete_generation(
    project_id: str,
    generation_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a generation job"""
    try:
        success = await db.delete_generation_job(generation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Generation not found")
        return {"message": "Generation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete generation job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Deployments CRUD


@deployments_router.get("/{project_id}")
async def list_deployments(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all deployments for a project"""
    try:
        deployments = await db.list_deployments(current_user_id, project_id)
        return {"deployments": deployments}
    except Exception as e:
        logger.error(f"Failed to list deployments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@deployments_router.post("/{project_id}")
async def create_deployment(
    project_id: str,
    deployment: DeploymentCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new deployment"""
    try:
        result = await db.create_deployment(
            current_user_id, project_id, deployment.model_dump()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create deployment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@deployments_router.get("/{project_id}/{deployment_id}")
async def get_deployment(
    project_id: str,
    deployment_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get a deployment by ID"""
    try:
        deployment = await db.get_deployment(current_user_id, project_id, deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        return deployment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deployment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@deployments_router.put("/{project_id}/{deployment_id}")
async def update_deployment(
    project_id: str,
    deployment_id: str,
    deployment: DeploymentUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update a deployment"""
    try:
        result = await db.update_deployment(
            current_user_id,
            project_id,
            deployment_id,
            deployment.model_dump(exclude_unset=True),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update deployment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@deployments_router.delete("/{project_id}/{deployment_id}")
async def delete_deployment(
    project_id: str,
    deployment_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a deployment"""
    try:
        success = await db.delete_deployment(current_user_id, project_id, deployment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Deployment not found")
        return {"message": "Deployment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete deployment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Billing CRUD


@billing_router.get("/")
async def list_billing_records(
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all billing records for the current user"""
    try:
        records = await db.list_billing_records(current_user_id)
        return {"billing_records": records}
    except Exception as e:
        logger.error(f"Failed to list billing records: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.post("/")
async def create_billing_record(
    billing: BillingCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new billing record"""
    try:
        result = await db.create_billing_record(current_user_id, billing.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create billing record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.get("/{billing_id}")
async def get_billing_record(
    billing_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Get a billing record by ID"""
    try:
        record = await db.get_billing_record(current_user_id, billing_id)
        if not record:
            raise HTTPException(status_code=404, detail="Billing record not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get billing record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.put("/{billing_id}")
async def update_billing_record(
    billing_id: str,
    billing: BillingUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update a billing record"""
    try:
        result = await db.update_billing_record(
            current_user_id, billing_id, billing.model_dump(exclude_unset=True)
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update billing record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.delete("/{billing_id}")
async def delete_billing_record(
    billing_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a billing record"""
    try:
        success = await db.delete_billing_record(current_user_id, billing_id)
        if not success:
            raise HTTPException(status_code=404, detail="Billing record not found")
        return {"message": "Billing record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete billing record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
