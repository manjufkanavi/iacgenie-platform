import logging

from typing import List, Dict, Any

from datetime import datetime

from fastapi import APIRouter, Depends

from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field

from db.db_provider import db_provider
from utils.serialization import prepare_api_response

from middleware.auth_middleware import verify_access_token

import secrets

import hashlib

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])

# Pydantic models


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., description="API key name")
    permissions: List[str] = Field(
        default=["read", "write"], description="API key permissions"
    )


class ApiKeyUpdateRequest(BaseModel):
    name: str = Field(..., description="API key name")
    isActive: bool = Field(..., description="Whether the key is active")


class ApiKeyResponse(BaseModel):
    id: str
    userId: str
    projectId: str
    name: str
    tokenPreview: str
    permissions: List[str]
    isActive: bool
    lastUsed: str | None = None
    createdAt: str
    updatedAt: str


class ApiKeyListResponse(BaseModel):
    keys: List[ApiKeyResponse]
    total: int


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    token: str
    tokenPreview: str
    createdAt: str


# Service layer


class ApiKeyService:
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return f"tg_{secrets.token_urlsafe(32)}"

    @staticmethod
    def get_token_preview(token: str) -> str:
        """Get a preview of the token for display"""
        return f"{token[:8]}...{token[-4:]}"

    @staticmethod
    def _map_to_ui(key_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map postgres snake_case fields to UI camelCase fields"""
        if not key_data:
            return {}
        return {
            "id": key_data.get("id"),
            "userId": key_data.get("user_id"),
            "name": key_data.get("name"),
            "tokenPreview": key_data.get("tokenPreview"),
            "permissions": key_data.get("scopes", []),
            "isActive": key_data.get("is_active", True),
            "lastUsed": key_data.get("last_used_at"),
            "expiresAt": key_data.get("expires_at"),
            "createdAt": key_data.get("created_at"),
            "updatedAt": key_data.get("updated_at"),
        }

    @staticmethod
    async def list_api_keys(uid: str) -> List[Dict[str, Any]]:
        """List all API keys for a user"""
        try:
            keys_data = await db_provider.list_api_keys(uid)
            return [ApiKeyService._map_to_ui(k) for k in keys_data]
        except Exception as e:
            logger.error(f"Error listing API keys: {str(e)}")
            raise e

    @staticmethod
    async def create_api_key(uid: str, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new API key"""
        try:
            key_id = await db_provider.create_api_key(
                uid,
                {
                    "name": key_data["name"],
                    "scopes": key_data.get("permissions", ["read", "write"]),
                    "is_active": True,
                    "metadata": {
                        "expiryDays": key_data.get("expiryDays"),
                    },
                },
            )
            if not key_id:
                raise ValueError("Failed to create API key")
            created = await db_provider.get_api_key(uid, key_id)
            if not created:
                raise ValueError("Failed to retrieve created API key")
            result = ApiKeyService._map_to_ui(created)
            result["token"] = created.get("token")
            return result
        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            raise e

    @staticmethod
    async def update_api_key(
        uid: str, key_id: str, key_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing API key"""
        try:
            existing = await db_provider.get_api_key(uid, key_id)
            if not existing:
                raise ValueError("API key not found")
            update_fields: Dict[str, Any] = {}
            if "name" in key_data:
                update_fields["name"] = key_data["name"]
            if "scopes" in key_data:
                update_fields["scopes"] = key_data["scopes"]
            if "isActive" in key_data:
                update_fields["is_active"] = key_data["isActive"]
            if not update_fields:
                return ApiKeyService._map_to_ui(existing)
            success = await db_provider.update_api_key(uid, key_id, update_fields)
            if not success:
                raise ValueError("Failed to update API key")
            updated = await db_provider.get_api_key(uid, key_id)
            return ApiKeyService._map_to_ui(updated or existing)
        except Exception as e:
            logger.error(f"Error updating API key: {str(e)}")
            raise e

    @staticmethod
    async def delete_api_key(uid: str, key_id: str) -> Dict[str, Any]:
        """Delete an API key"""
        try:
            existing = await db_provider.get_api_key(uid, key_id)
            if not existing:
                raise ValueError("API key not found")
            success = await db_provider.delete_api_key(uid, key_id)
            if not success:
                raise ValueError("Failed to delete API key")
            return {
                "success": True,
                "message": "API key deleted successfully",
                "key_id": key_id,
            }
        except Exception as e:
            logger.error(f"Error deleting API key: {str(e)}")
            raise e

    @staticmethod
    async def validate_api_key(token: str) -> Dict[str, Any] | None:
        """Validate an API key and return user info"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            all_keys = await db_provider.list_api_keys(None)  # type: ignore[arg-type]
            for key_data in all_keys:
                if key_data.get("key_hash") == token_hash and key_data.get("is_active"):
                    # Update last used
                    await db_provider.update_api_key(
                        key_data.get("user_id", ""),  # type: ignore[arg-type]
                        key_data["id"],
                        {"last_used_at": datetime.now().isoformat()},
                    )
                    metadata = key_data.get("metadata") or {}
                    return {
                        "userId": key_data.get("user_id"),
                        "name": key_data.get("name"),
                        "permissions": key_data.get("scopes", ["read"]),
                        "keyId": key_data.get("id"),
                        "token": metadata.get("token"),
                    }
            return None
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return None


# Initialize service


api_key_service = ApiKeyService()

# API Endpoints


@router.get("/{project_id}", response_model=ApiKeyListResponse)
async def list_api_keys(
    project_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """List all API keys for a project"""
    try:
        if not user.get("uid"):
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        keys_data = await api_key_service.list_api_keys(user["uid"])
        keys = [ApiKeyResponse(**key_data) for key_data in keys_data]
        return ApiKeyListResponse(keys=keys, total=len(keys))
    except Exception as e:
        logger.error(f"Failed to list API keys: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Failed to list API keys: {str(e)}"},
        )


@router.post("/{project_id}", response_model=ApiKeyCreateResponse)
async def create_api_key(
    project_id: str, key: ApiKeyCreateRequest, user: Any = Depends(verify_access_token)
) -> Any:
    """Create a new API key"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await api_key_service.create_api_key(
            uid, {**key.model_dump(), "expiryDays": 90}
        )
        return ApiKeyCreateResponse(
            id=result["id"],
            name=result["name"],
            token=result["token"],
            tokenPreview=result["tokenPreview"],
            createdAt=result["createdAt"],
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to create API key: {str(e)}",
            },
        )


@router.put("/{project_id}/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    project_id: str,
    key_id: str,
    key: ApiKeyUpdateRequest,
    user: Any = Depends(verify_access_token),
) -> Any:
    """Update an API key"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await api_key_service.update_api_key(uid, key_id, key.model_dump())
        return ApiKeyResponse(**result)
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to update API key: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to update API key: {str(e)}",
            },
        )


@router.delete("/{project_id}/{key_id}")
async def delete_api_key(
    project_id: str, key_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Delete an API key"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await api_key_service.delete_api_key(uid, key_id)
        return JSONResponse(status_code=200, content=prepare_api_response(result))
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to delete API key: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to delete API key: {str(e)}",
            },
        )


@router.post("/{project_id}/validate")
async def validate_api_key(project_id: str, token: str) -> Any:
    """Validate an API key (for external API access)"""
    try:
        result = await api_key_service.validate_api_key(token)
        if result:
            return JSONResponse(status_code=200, content=prepare_api_response(result))
        else:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid API key"},
            )
    except Exception as e:
        logger.error(f"Failed to validate API key: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to validate API key: {str(e)}",
            },
        )
