"""

Integrations Router

Provides API endpoints for managing integrations (Slack, Discord, Email, Webhook).

"""

import logging
import json
from typing import List, Dict, Any
from datetime import datetime

import httpx

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from db.db_provider import db_provider
from utils.serialization import prepare_api_response
from utils.crypto import encrypt_key, decrypt_key
from middleware.auth_middleware import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# Pydantic models


class IntegrationRequest(BaseModel):
    name: str = Field(..., description="Integration name")
    type: str = Field(
        ..., description="Integration type (slack, discord, email, webhook)"
    )
    config: Dict[str, Any] = Field(..., description="Integration configuration")
    isActive: bool = Field(default=True, description="Whether integration is active")


class IntegrationResponse(BaseModel):
    id: str
    userId: str
    projectId: str
    name: str
    type: str
    isActive: bool
    createdAt: str
    updatedAt: str


class IntegrationListResponse(BaseModel):
    integrations: List[IntegrationResponse]
    total: int


class IntegrationTestResponse(BaseModel):
    success: bool
    message: str
    details: Dict[str, Any] = {}


# Service layer


class IntegrationsService:
    @staticmethod
    def _map_to_ui(integration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map postgres snake_case fields to UI camelCase fields"""
        if not integration_data:
            return {}
        return {
            "id": integration_data.get("id"),
            "userId": integration_data.get("user_id"),
            "projectId": integration_data.get("project_id"),
            "name": integration_data.get("name"),
            "type": integration_data.get("type"),
            "isActive": integration_data.get("is_active", True),
            "createdAt": integration_data.get("created_at"),
            "updatedAt": integration_data.get("updated_at"),
        }

    @staticmethod
    async def list_integrations(uid: str, project_id: str) -> List[Dict[str, Any]]:
        """List all integrations for a user's project"""
        try:
            integrations_data = await db_provider.list_integrations(uid, project_id)
            return [IntegrationsService._map_to_ui(i) for i in integrations_data]
        except Exception as e:
            logger.error(f"Error listing integrations: {str(e)}")
            raise

    @staticmethod
    async def create_integration(
        uid: str, project_id: str, integration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new integration configuration"""
        try:
            if (
                not integration_data.get("name")
                or not integration_data.get("type")
                or not integration_data.get("config")
            ):
                raise ValueError("Name, type, and config are required")

            valid_types = ["slack", "discord", "email", "webhook"]
            if integration_data["type"] not in valid_types:
                raise ValueError(
                    f"Invalid integration type. Must be one of: {', '.join(valid_types)}"
                )

            # Check for duplicate integration name
            existing = await IntegrationsService.list_integrations(uid, project_id)
            for existing_integration in existing:
                if existing_integration["name"] == integration_data["name"]:
                    raise ValueError(
                        f"Integration with name '{integration_data['name']}' already exists"
                    )

            # Encrypt sensitive configuration data
            try:
                config_json = json.dumps(integration_data["config"])
                encrypted_config = encrypt_key(config_json)
            except Exception as e:
                logger.error(f"Failed to encrypt config: {str(e)}")
                raise ValueError("Failed to encrypt configuration")

            result = await db_provider.create_integration(
                uid,
                project_id,
                {
                    "name": integration_data["name"].strip(),
                    "type": integration_data["type"].strip(),
                    "configuration": encrypted_config,
                    "is_active": integration_data.get("isActive", True),
                    "metadata": {},
                },
            )
            if not result:
                raise ValueError("Failed to create integration")

            mapped = IntegrationsService._map_to_ui(result)
            logger.info(
                f"Integration created for user {uid}, project {project_id}, name {integration_data['name']}"
            )
            return mapped
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating integration: {str(e)}")
            raise ValueError(f"Failed to create integration: {str(e)}")

    @staticmethod
    async def update_integration(
        uid: str, project_id: str, integration_id: str, integration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing integration configuration"""
        try:
            existing = await db_provider.get_integration(
                uid, project_id, integration_id
            )
            if not existing:
                raise ValueError("Integration configuration not found")

            updates: Dict[str, Any] = {}
            if "name" in integration_data:
                updates["name"] = integration_data["name"].strip()
            if "type" in integration_data:
                updates["type"] = integration_data["type"].strip()
            if "isActive" in integration_data:
                updates["is_active"] = integration_data["isActive"]

            if "config" in integration_data:
                try:
                    config_json = json.dumps(integration_data["config"])
                    encrypted_config = encrypt_key(config_json)
                    updates["configuration"] = encrypted_config
                except Exception as e:
                    logger.error(f"Failed to encrypt config: {str(e)}")
                    raise ValueError("Failed to encrypt configuration")

            if not updates:
                return IntegrationsService._map_to_ui(existing)

            success = await db_provider.update_integration(
                uid, project_id, integration_id, updates
            )
            if not success:
                raise ValueError("Failed to update integration")

            updated = await db_provider.get_integration(uid, project_id, integration_id)
            return IntegrationsService._map_to_ui(updated or existing)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating integration: {str(e)}")
            raise ValueError(f"Failed to update integration: {str(e)}")

    @staticmethod
    async def delete_integration(
        uid: str, project_id: str, integration_id: str
    ) -> Dict[str, Any]:
        """Delete an integration configuration"""
        try:
            existing = await db_provider.get_integration(
                uid, project_id, integration_id
            )
            if not existing:
                raise ValueError("Integration configuration not found")

            success = await db_provider.delete_integration(
                uid, project_id, integration_id
            )
            if not success:
                raise ValueError("Failed to delete integration")

            logger.info(
                f"Integration deleted for user {uid}, project {project_id}, integration {integration_id}"
            )
            return {
                "success": True,
                "message": "Integration configuration deleted successfully",
                "integration_id": integration_id,
            }
        except Exception as e:
            logger.error(f"Error deleting integration: {str(e)}")
            raise

    @staticmethod
    async def test_integration(
        uid: str, project_id: str, integration_id: str
    ) -> Dict[str, Any]:
        """Test an integration configuration"""
        try:
            integration = await db_provider.get_integration(
                uid, project_id, integration_id
            )
            if not integration:
                raise ValueError("Integration configuration not found")

            encrypted_config = integration.get("configuration")
            if not encrypted_config:
                return {
                    "success": False,
                    "message": "No configuration found for this integration",
                    "details": {
                        "type": integration.get("type", "unknown"),
                        "name": integration.get("name", "unknown"),
                    },
                    "statusCode": 400,
                }

            # Decrypt the configuration
            try:
                decrypted_config_json = decrypt_key(encrypted_config)
                config = json.loads(decrypted_config_json)
            except Exception as e:
                logger.error(f"Failed to decrypt config: {str(e)}")
                raise ValueError("Failed to decrypt configuration")

            integration_type = integration.get("type", "webhook")
            name = integration.get("name", "unknown")

            if integration_type == "slack":
                return await IntegrationsService._test_slack_integration(config, name)
            elif integration_type == "discord":
                return await IntegrationsService._test_discord_integration(config, name)
            elif integration_type == "webhook":
                return await IntegrationsService._test_webhook_integration(config, name)
            elif integration_type == "email":
                return await IntegrationsService._test_email_integration(config, name)
            else:
                raise ValueError(f"Unsupported integration type: {integration_type}")
        except Exception as e:
            logger.error(f"Error testing integration: {str(e)}")
            integration_type = "unknown"
            name = "unknown"
            return {
                "success": False,
                "message": f"Test failed: {str(e)}",
                "details": {"type": integration_type, "name": name},
                "statusCode": None,
            }

    @staticmethod
    async def _test_slack_integration(
        config: Dict[str, Any], name: str
    ) -> Dict[str, Any]:
        """Test Slack integration by sending a test message"""
        try:
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                return {
                    "success": False,
                    "message": "Slack webhook URL is required",
                    "details": {
                        "type": "slack",
                        "name": name,
                        "error": "Missing webhook_url in config",
                    },
                    "statusCode": 400,
                }
            test_message = {
                "text": f"🧪 Test message from IACGenie integration '{name}'",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Test Message*\n"
                                f"This is a test message from your "
                                f"IACGenie integration '{name}'. "
                                f"If you see this, your Slack integration is "
                                f"working correctly! ✅"
                            ),
                        },
                    }
                ],
            }
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(webhook_url, json=test_message)
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Slack integration test successful",
                        "details": {
                            "type": "slack",
                            "name": name,
                            "response": response.text,
                        },
                        "statusCode": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Slack integration test failed: HTTP {response.status_code}",
                        "details": {
                            "type": "slack",
                            "name": name,
                            "error_response": response.text,
                        },
                        "statusCode": response.status_code,
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"Slack integration test failed: {str(e)}",
                "details": {"type": "slack", "name": name, "error": str(e)},
                "statusCode": 500,
            }

    @staticmethod
    async def _test_discord_integration(
        config: Dict[str, Any], name: str
    ) -> Dict[str, Any]:
        """Test Discord integration by sending a test message"""
        try:
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                return {
                    "success": False,
                    "message": "Discord webhook URL is required",
                    "details": {
                        "type": "discord",
                        "name": name,
                        "error": "Missing webhook_url in config",
                    },
                    "statusCode": 400,
                }
            test_message = {
                "content": f"🧪 Test message from IACGenie integration '{name}'",
                "embeds": [
                    {
                        "title": "Test Message",
                        "description": (
                            f"This is a test message from your "
                            f"IACGenie integration '{name}'. "
                            f"If you see this, your Discord integration is "
                            f"working correctly! ✅"
                        ),
                        "color": 0x00FF00,
                    }
                ],
            }
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(webhook_url, json=test_message)
                if response.status_code == 204:
                    return {
                        "success": True,
                        "message": "Discord integration test successful",
                        "details": {
                            "type": "discord",
                            "name": name,
                            "response": "Message sent successfully",
                        },
                        "statusCode": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Discord integration test failed: HTTP {response.status_code}",
                        "details": {
                            "type": "discord",
                            "name": name,
                            "error_response": response.text,
                        },
                        "statusCode": response.status_code,
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"Discord integration test failed: {str(e)}",
                "details": {"type": "discord", "name": name, "error": str(e)},
                "statusCode": 500,
            }

    @staticmethod
    async def _test_webhook_integration(
        config: Dict[str, Any], name: str
    ) -> Dict[str, Any]:
        """Test webhook integration by sending a test payload"""
        try:
            webhook_url = config.get("url")
            if not webhook_url:
                return {
                    "success": False,
                    "message": "Webhook URL is required",
                    "details": {
                        "type": "webhook",
                        "name": name,
                        "error": "Missing url in config",
                    },
                    "statusCode": 400,
                }
            test_payload = {
                "event": "test",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "iacgenie",
                "message": f"Test message from Iacgenie integration '{name}'",
                "data": {"integration_name": name, "test": True},
            }
            headers = config.get("headers", {})
            method = config.get("method", "POST").upper()
            async with httpx.AsyncClient(timeout=30) as client:
                if method == "POST":
                    response = await client.post(
                        webhook_url, json=test_payload, headers=headers
                    )
                elif method == "PUT":
                    response = await client.put(
                        webhook_url, json=test_payload, headers=headers
                    )
                else:
                    return {
                        "success": False,
                        "message": f"Unsupported HTTP method: {method}",
                        "details": {
                            "type": "webhook",
                            "name": name,
                            "error": f"Method {method} not supported",
                        },
                        "statusCode": 400,
                    }
                if response.status_code in [200, 201, 202, 204]:
                    return {
                        "success": True,
                        "message": "Webhook integration test successful",
                        "details": {
                            "type": "webhook",
                            "name": name,
                            "method": method,
                            "status_code": response.status_code,
                            "response": response.text[:500],
                        },
                        "statusCode": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Webhook integration test failed: HTTP {response.status_code}",
                        "details": {
                            "type": "webhook",
                            "name": name,
                            "method": method,
                            "error_response": response.text[:500],
                        },
                        "statusCode": response.status_code,
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"Webhook integration test failed: {str(e)}",
                "details": {"type": "webhook", "name": name, "error": str(e)},
                "statusCode": 500,
            }

    @staticmethod
    async def _test_email_integration(
        config: Dict[str, Any], name: str
    ) -> Dict[str, Any]:
        """Test email integration by validating the configuration"""
        try:
            required_fields = [
                "smtp_host",
                "smtp_port",
                "username",
                "password",
                "from_email",
            ]
            missing_fields = [
                field for field in required_fields if not config.get(field)
            ]
            if missing_fields:
                return {
                    "success": False,
                    "message": f"Email integration configuration incomplete. Missing: {', '.join(missing_fields)}",
                    "details": {
                        "type": "email",
                        "name": name,
                        "error": f"Missing required fields: {missing_fields}",
                    },
                    "statusCode": 400,
                }
            return {
                "success": True,
                "message": "Email integration configuration is valid",
                "details": {
                    "type": "email",
                    "name": name,
                    "smtp_host": config.get("smtp_host"),
                    "smtp_port": config.get("smtp_port"),
                    "from_email": config.get("from_email"),
                    "note": "Configuration validated. Test email would be sent in production.",
                },
                "statusCode": 200,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Email integration test failed: {str(e)}",
                "details": {"type": "email", "name": name, "error": str(e)},
                "statusCode": 500,
            }


# Initialize service

integrations_service = IntegrationsService()

# API Endpoints


@router.get("/{project_id}", response_model=IntegrationListResponse)
async def list_integrations(
    project_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """List all integrations for a project"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        integrations_data = await integrations_service.list_integrations(
            uid, project_id
        )
        integrations = [IntegrationResponse(**i) for i in integrations_data]
        response = IntegrationListResponse(
            integrations=integrations, total=len(integrations)
        )
        return response
    except Exception as e:
        logger.error(f"Failed to list integrations: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to list integrations: {str(e)}",
            },
        )


@router.post("/{project_id}")
async def create_integration(
    project_id: str,
    integration: IntegrationRequest,
    user: Any = Depends(verify_access_token),
) -> Any:
    """Create a new integration configuration"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await integrations_service.create_integration(
            uid, project_id, integration.model_dump()
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
        logger.error(f"Failed to create integration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to create integration: {str(e)}",
            },
        )


@router.put("/{project_id}/{integration_id}")
async def update_integration(
    project_id: str,
    integration_id: str,
    integration: IntegrationRequest,
    user: Any = Depends(verify_access_token),
) -> Any:
    """Update an existing integration configuration"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await integrations_service.update_integration(
            uid, project_id, integration_id, integration.model_dump()
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
        logger.error(f"Failed to update integration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to update integration: {str(e)}",
            },
        )


@router.delete("/{project_id}/{integration_id}")
async def delete_integration(
    project_id: str, integration_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Delete an integration configuration"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await integrations_service.delete_integration(
            uid, project_id, integration_id
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
        logger.error(f"Failed to delete integration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to delete integration: {str(e)}",
            },
        )


@router.post("/{project_id}/{integration_id}/test")
async def test_integration(
    project_id: str, integration_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Test an integration configuration"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        result = await integrations_service.test_integration(
            uid, project_id, integration_id
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
        logger.error(f"Failed to test integration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to test integration: {str(e)}",
            },
        )
