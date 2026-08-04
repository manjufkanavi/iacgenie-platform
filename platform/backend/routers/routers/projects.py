"""

Projects Router

Handles project-related operations with Keycloak authentication

"""

from fastapi import APIRouter, HTTPException, Request, Body

from fastapi.responses import JSONResponse

from typing import Dict, Any


import logging

import traceback

from middleware.auth_middleware import verify_access_token

from db.db_provider import db_provider

from middleware.validation import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Projects"])

# Mock database for testing (replace with actual PostgreSQL)

projects_db: Dict[str, Any] = {}


@router.get("/projects")
async def list_projects(request: Request) -> Dict[str, Any]:
    """List projects for authenticated user"""
    print("DEBUG: list_projects endpoint called")
    logging.info("DEBUG: list_projects endpoint called")
    try:
        # Get user from token using PostgreSQL authentication
        user = await verify_access_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        db = db_provider.adapter
        if db is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        projects = await db.list_projects(user["uid"])
        # Return projects in the format expected by frontend
        return {"projects": projects}
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/projects")
async def create_project(request: Request, body: ProjectCreate = Body(...)) -> Any:
    """Create a new project for authenticated user"""
    print("DEBUG: create_project endpoint called")
    logging.info("DEBUG: create_project endpoint called")
    try:
        # Get user from token using PostgreSQL authentication
        user = await verify_access_token(request)
        if not user or "uid" not in user:
            raise HTTPException(status_code=401, detail="Invalid token or user")
        db = db_provider.adapter
        if db is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        project = await db.create_project(user["uid"], body.dict())
        if project and project.get("id"):
            # Auto-assign creator as owner in team_members so hasProjectEditAccess works
            try:
                await db.create_team_member(
                    user["uid"],
                    project["id"],
                    {
                        "email": user.get("email", ""),
                        "role": "owner",
                        "is_active": True,
                    },
                )
            except Exception as tm_err:
                logging.warning(
                    f"Could not add creator as team member (non-critical): {tm_err}"
                )
        # Return project in the format expected by frontend
        return {"project": project}
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logging.error(f"Error in create_project: {e}")
        logging.error(f"Error type: {type(e)}")
        logging.error(f"Error args: {e.args}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            status_code=500, content={"detail": f"Internal server error: {str(e)}"}
        )


@router.get("/projects/test")
async def test_projects() -> Dict[str, Any]:
    """Test endpoint to verify the router is working"""
    return {"message": "Projects router is working!", "status": "success"}


@router.get("/projects/{project_id}")
async def get_project(project_id: str, request: Request) -> Dict[str, Any]:
    """Get a specific project"""
    try:
        # Get user from token using PostgreSQL authentication
        user = await verify_access_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        db = db_provider.adapter
        if db is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        project = await db.get_project(user["uid"], project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        # Return project in the format expected by frontend
        return {"project": project}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str, request: Request, body: ProjectUpdate = Body(...)
) -> Dict[str, Any]:
    """Update a project (owner or admin only)"""
    try:
        # Get user from token using PostgreSQL authentication
        user = await verify_access_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        db = db_provider.adapter
        if db is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        # Check if project exists and user owns it or is admin
        project = await db.get_project(user["uid"], project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        # Check project-level RBAC: owner or admin
        if not hasattr(db, "get_project_team_members"):
            raise NotImplementedError(
                "get_project_team_members is not implemented on db adapter"
            )
        team_members = await db.get_project_team_members(project_id)
        user_role = None
        for member in team_members:
            if member["userId"] == user["uid"]:
                user_role = member.get("role")
                break
        if project["ownerId"] != user["uid"] and user_role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: must be owner or admin",
            )
        # Update project
        updated_project = await db.update_project(
            user["uid"], project_id, body.dict(exclude_unset=True)
        )
        return {"project": updated_project}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, request: Request) -> Dict[str, Any]:
    """Delete a project"""
    try:
        # Get user from token using PostgreSQL authentication
        user = await verify_access_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        db = db_provider.adapter
        if db is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        # Check if project exists and user owns it
        project = await db.get_project(user["uid"], project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        # Delete project
        await db.delete_project(user["uid"], project_id)
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/projects/{project_id}/roles")
async def get_user_project_role(project_id: str, request: Request) -> Dict[str, Any]:
    """Get the current user's role for a given project and their global role"""
    user = await verify_access_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    roles = user.get("roles", {})
    project_role = roles.get("projects", {}).get(project_id, "viewer")
    global_role = roles.get("global", "user")
    return {
        "project_id": project_id,
        "project_role": project_role,
        "global_role": global_role,
    }
