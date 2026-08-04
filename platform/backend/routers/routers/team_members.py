"""

Team Members Router

Provides API endpoints for managing team members within projects.

"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr

from db.db_provider import db_provider
from utils.serialization import prepare_api_response
from middleware.auth_middleware import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/team-members", tags=["team-members"])

# Pydantic models


class TeamMemberRequest(BaseModel):
    email: EmailStr = Field(..., description="Member email address")
    name: str = Field(..., description="Member name")
    role: str = Field(..., description="Member role (owner, admin, editor, viewer)")
    avatarUrl: str = Field(default="", description="Avatar URL")


class TeamMemberResponse(BaseModel):
    id: str
    userId: str
    projectId: str
    email: str
    name: str
    role: str
    avatarUrl: str
    status: str
    createdAt: str
    updatedAt: str


class TeamMemberListResponse(BaseModel):
    members: List[TeamMemberResponse]
    total: int


# Service layer


class TeamMembersService:
    @staticmethod
    def _map_to_ui(member_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map postgres snake_case fields to UI camelCase fields"""
        if not member_data:
            return {}
        return {
            "id": member_data.get("id"),
            "userId": member_data.get("user_id"),
            "projectId": member_data.get("project_id"),
            "email": member_data.get("email"),
            "name": member_data.get("name", ""),
            "role": member_data.get("role"),
            "avatarUrl": member_data.get("avatarUrl", ""),
            "status": member_data.get("status", "active"),
            "createdAt": member_data.get("created_at"),
            "updatedAt": member_data.get("updated_at"),
        }

    @staticmethod
    async def list_team_members(uid: str, project_id: str) -> List[Dict[str, Any]]:
        """List all team members for a user's project"""
        try:
            members_data = await db_provider.list_team_members(uid, project_id)
            return [TeamMembersService._map_to_ui(m) for m in members_data]
        except Exception as e:
            logger.error(f"Error listing team members: {str(e)}")
            raise

    @staticmethod
    async def invite_team_member(
        uid: str, project_id: str, member_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invite a new team member to the project"""
        try:
            if (
                not member_data.get("email")
                or not member_data.get("name")
                or not member_data.get("role")
            ):
                raise ValueError("Email, name, and role are required")

            valid_roles = ["owner", "admin", "editor", "viewer"]
            if member_data["role"] not in valid_roles:
                raise ValueError(
                    f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                )

            # Check for duplicate email
            existing = await TeamMembersService.list_team_members(uid, project_id)
            for existing_member in existing:
                if existing_member["email"].lower() == member_data["email"].lower():
                    raise ValueError(
                        f"Team member with email '{member_data['email']}' already exists"
                    )

            result = await db_provider.create_team_member(
                uid,
                project_id,
                {
                    "email": member_data["email"].lower().strip(),
                    "name": member_data["name"].strip(),
                    "role": member_data["role"].strip(),
                    "avatarUrl": member_data.get("avatarUrl", "").strip(),
                    "permissions": [],
                    "is_active": True,
                    "status": "invited",
                    "metadata": {},
                },
            )
            if not result:
                raise ValueError("Failed to create team member")

            mapped = TeamMembersService._map_to_ui(result)
            logger.info(
                f"Team member invited for user {uid}, project {project_id}, email {member_data['email']}"
            )
            return mapped
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error inviting team member: {str(e)}")
            raise ValueError(f"Failed to invite team member: {str(e)}")

    @staticmethod
    async def update_team_member(
        uid: str, project_id: str, member_id: str, member_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing team member"""
        try:
            existing = await db_provider.get_team_member(uid, project_id, member_id)
            if not existing:
                raise ValueError("Team member not found")

            updates: Dict[str, Any] = {}
            if "role" in member_data:
                valid_roles = ["owner", "admin", "editor", "viewer"]
                if member_data["role"] not in valid_roles:
                    raise ValueError(
                        f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                    )
                updates["role"] = member_data["role"].strip()
            if "name" in member_data:
                updates["name"] = member_data["name"].strip()
            if "avatarUrl" in member_data:
                updates["avatarUrl"] = member_data["avatarUrl"].strip()
            if "status" in member_data:
                updates["status"] = member_data["status"]
            if "email" in member_data:
                new_email = member_data["email"].lower().strip()
                # Check for duplicate email (excluding current member)
                existing_members = await TeamMembersService.list_team_members(
                    uid, project_id
                )
                for existing_member in existing_members:
                    if (
                        existing_member["id"] != member_id
                        and existing_member["email"].lower() == new_email
                    ):
                        raise ValueError(
                            f"Team member with email '{new_email}' already exists"
                        )
                updates["email"] = new_email

            if not updates:
                return TeamMembersService._map_to_ui(existing)

            success = await db_provider.update_team_member(
                uid, project_id, member_id, updates
            )
            if not success:
                raise ValueError("Failed to update team member")

            updated = await db_provider.get_team_member(uid, project_id, member_id)
            return TeamMembersService._map_to_ui(updated or existing)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating team member: {str(e)}")
            raise ValueError(f"Failed to update team member: {str(e)}")

    @staticmethod
    async def remove_team_member(
        uid: str, project_id: str, member_id: str
    ) -> Dict[str, Any]:
        """Remove a team member from the project"""
        try:
            existing = await db_provider.get_team_member(uid, project_id, member_id)
            if not existing:
                raise ValueError("Team member not found")

            # Prevent removing the last owner
            if existing.get("role") == "owner":
                existing_members = await TeamMembersService.list_team_members(
                    uid, project_id
                )
                owners = [m for m in existing_members if m["role"] == "owner"]
                if len(owners) <= 1:
                    raise ValueError("Cannot remove the last owner from the project")

            success = await db_provider.delete_team_member(uid, project_id, member_id)
            if not success:
                raise ValueError("Failed to delete team member")

            logger.info(
                f"Team member removed for user {uid}, project {project_id}, member {member_id}"
            )
            return {
                "success": True,
                "message": "Team member removed successfully",
                "member_id": member_id,
            }
        except Exception as e:
            logger.error(f"Error removing team member: {str(e)}")
            raise


# Initialize service

team_members_service = TeamMembersService()

# API Endpoints


@router.get("/{project_id}", response_model=TeamMemberListResponse)
async def list_team_members(
    project_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """List all team members for a project"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        members_data = await team_members_service.list_team_members(uid, project_id)
        members = [TeamMemberResponse(**m) for m in members_data]
        response = TeamMemberListResponse(members=members, total=len(members))
        return response
    except Exception as e:
        logger.error(f"Failed to list team members: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to list team members: {str(e)}",
            },
        )


@router.post("/{project_id}")
async def invite_team_member(
    project_id: str, member: TeamMemberRequest, user: Any = Depends(verify_access_token)
) -> Any:
    """Invite a new team member to the project"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await team_members_service.invite_team_member(
            uid, project_id, member.model_dump()
        )
        response_content = {"success": True, "result": result}
        return JSONResponse(
            status_code=201, content=prepare_api_response(response_content)
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to invite team member: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to invite team member: {str(e)}",
            },
        )


@router.put("/{project_id}/{member_id}")
async def update_team_member(
    project_id: str,
    member_id: str,
    member: TeamMemberRequest,
    user: Any = Depends(verify_access_token),
) -> Any:
    """Update an existing team member"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await team_members_service.update_team_member(
            uid, project_id, member_id, member.model_dump()
        )
        response_content = {"success": True, "result": result}
        return JSONResponse(
            status_code=200, content=prepare_api_response(response_content)
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to update team member: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to update team member: {str(e)}",
            },
        )


@router.delete("/{project_id}/{member_id}")
async def remove_team_member(
    project_id: str, member_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Remove a team member from the project"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await team_members_service.remove_team_member(
            uid, project_id, member_id
        )
        response_content = {"success": True, "result": result}
        return JSONResponse(
            status_code=200, content=prepare_api_response(response_content)
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to remove team member: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to remove team member: {str(e)}",
            },
        )
