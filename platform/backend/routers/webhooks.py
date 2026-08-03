"""

Enhanced Webhooks Router

Provides comprehensive webhook functionality with retry logic, security, and proper error handling

"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query

from typing import Any, Dict

import logging

from datetime import datetime

from db.db_provider import db_provider

# Dependency function to get database adapter


async def get_db() -> Any:
    """Get database adapter for dependency injection"""
    return db_provider.adapter


from db.adapters.base import IDatabaseAdapter

from middleware.auth_middleware import get_user_id

from services.webhook_service import get_webhook_service, WebhookEventType

from middleware.error_handling import error_handler, create_success_response

logger = logging.getLogger(__name__)

# Create webhooks router

webhooks_router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

# Helper function to get current user ID


async def get_current_user_id(user_id: str = Depends(get_user_id)) -> str:
    """Get current user ID from authenticated token"""
    return user_id


# Webhook CRUD Operations


@webhooks_router.post("/")
async def create_webhook(
    webhook_data: Dict[str, Any],
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new webhook with enhanced validation"""
    try:
        webhook_service = await get_webhook_service(db)
        result = await webhook_service.register_webhook(current_user_id, webhook_data)
        return create_success_response(
            data=result, message="Webhook created successfully"
        )
    except ValueError as e:
        error_response = error_handler.create_error_response(
            message=str(e), error_code="VALIDATION_ERROR", status_code=400
        )
        raise HTTPException(status_code=400, detail=error_response["error"])
    except Exception as e:
        logger.error(f"Failed to create webhook: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.get("/")
async def list_webhooks(
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """List all webhooks for the current user"""
    try:
        webhooks = await db.list_webhooks(current_user_id)
        return create_success_response(
            data={"webhooks": webhooks}, message="Webhooks retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to list webhooks: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


# /{webhook_id} routes moved to the end of file


@webhooks_router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Test a webhook by sending a test payload"""
    try:
        webhook_service = await get_webhook_service(db)
        result = await webhook_service.test_webhook(current_user_id, webhook_id)
        if result.success:
            return create_success_response(
                data={
                    "webhook_id": webhook_id,
                    "url": result.url,
                    "status_code": result.status_code,
                    "response_time": result.response_time,
                    "success": result.success,
                },
                message="Webhook test completed successfully",
            )
        else:
            return create_success_response(
                data={
                    "webhook_id": webhook_id,
                    "url": result.url,
                    "status_code": result.status_code,
                    "response_time": result.response_time,
                    "success": result.success,
                    "error_message": result.error_message,
                },
                message="Webhook test failed",
            )
    except Exception as e:
        logger.error(f"Failed to test webhook: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.get("/{webhook_id}/logs")
async def get_webhook_logs(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Get webhook delivery logs"""
    try:
        logs = await db.get_webhook_logs(current_user_id, webhook_id, limit)
        return create_success_response(
            data={"logs": logs}, message="Webhook logs retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get webhook logs: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


# Webhook Receiver (for incoming webhooks)


@webhooks_router.post("/receive/{webhook_id}")
async def receive_webhook(
    webhook_id: str, request: Request, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Receive incoming webhook with enhanced processing"""
    try:
        # Get webhook configuration
        db = await get_db()
        webhook = await db.get_webhook_by_id(webhook_id)
        if not webhook:
            error_response = error_handler.create_error_response(
                message="Webhook not found",
                error_code="WEBHOOK_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response["error"])
        if not webhook.get("isActive", True):
            error_response = error_handler.create_error_response(
                message="Webhook is inactive",
                error_code="WEBHOOK_INACTIVE",
                status_code=410,
            )
            raise HTTPException(status_code=410, detail=error_response["error"])
        # Get request body
        body = await request.body()
        try:
            payload = await request.json()
        except Exception:
            payload = body.decode("utf-8") if body else ""
        # Get client IP
        ip_address = request.client.host if request.client else "unknown"
        # Process webhook
        webhook_service = await get_webhook_service(db)
        result = await webhook_service.process_incoming_webhook(
            webhook_id, payload, dict(request.headers), ip_address
        )
        return create_success_response(
            data=result, message="Webhook processed successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process incoming webhook: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.get("/events")
async def list_webhook_events(
    limit: int = Query(50, ge=1, le=100),
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """List webhook events"""
    try:
        events = await db.list_webhook_events(current_user_id, limit)
        return create_success_response(
            data={"events": events}, message="Webhook events retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to list webhook events: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.get("/events/supported")
async def get_supported_events() -> Dict[str, Any]:
    """Get list of supported webhook events"""
    try:
        events = [
            {"value": event.value, "description": event.name.replace("_", " ").title()}
            for event in WebhookEventType
        ]
        return create_success_response(
            data={"events": events}, message="Supported events retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get supported events: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to retrieve supported events",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response["error"])


@webhooks_router.get("/events/{event_id}")
async def get_webhook_event(
    event_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Get a specific webhook event"""
    try:
        event = await db.get_webhook_event(current_user_id, event_id)
        if not event:
            error_response = error_handler.create_error_response(
                message="Webhook event not found",
                error_code="RECORD_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response["error"])
        return create_success_response(
            data=event, message="Webhook event retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook event: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.get("/stats")
async def get_webhook_stats(
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Get webhook statistics"""
    try:
        webhook_service = await get_webhook_service(db)
        stats = await webhook_service.get_webhook_stats(current_user_id)
        return create_success_response(
            data=stats, message="Webhook statistics retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get webhook stats: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.post("/trigger/{event_type}")
async def trigger_webhook_event(
    event_type: str,
    event_data: Dict[str, Any],
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger a webhook event (for testing)"""
    try:
        # Convert colon to dot for format compatibility
        event_type = event_type.replace(":", ".")
        # Validate event type
        valid_events = [event.value for event in WebhookEventType]
        if event_type not in valid_events:
            error_response = error_handler.create_error_response(
                message=f"Invalid event type. Supported events: {', '.join(valid_events)}",
                error_code="VALIDATION_ERROR",
                status_code=400,
            )
            raise HTTPException(status_code=400, detail=error_response["error"])
        # Send webhook
        webhook_service = await get_webhook_service(db)
        results = await webhook_service.send_webhook(
            event_type, event_data, current_user_id, event_data.get("project_id")
        )
        return create_success_response(
            data={
                "event_type": event_type,
                "results": [
                    {
                        "webhook_id": result.webhook_id,
                        "url": result.url,
                        "success": result.success,
                        "status_code": result.status_code,
                        "response_time": result.response_time,
                        "error_message": result.error_message,
                    }
                    for result in results
                ],
            },
            message=f"Webhook event '{event_type}' triggered successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger webhook event: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Get a specific webhook"""
    try:
        webhook = await db.get_webhook(current_user_id, webhook_id)
        if not webhook:
            error_response = error_handler.create_error_response(
                message="Webhook not found",
                error_code="WEBHOOK_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response["error"])
        return create_success_response(
            data=webhook, message="Webhook retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    webhook_data: Dict[str, Any],
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Update a webhook"""
    try:
        webhook_data["updated_at"] = datetime.utcnow().isoformat()
        result = await db.update_webhook(current_user_id, webhook_id, webhook_data)
        return create_success_response(
            data=result, message="Webhook updated successfully"
        )
    except ValueError as e:
        error_response = error_handler.create_error_response(
            message=str(e), error_code="VALIDATION_ERROR", status_code=400
        )
        raise HTTPException(status_code=400, detail=error_response["error"])
    except Exception as e:
        logger.error(f"Failed to update webhook: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])


@webhooks_router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: IDatabaseAdapter = Depends(get_db),
) -> Dict[str, Any]:
    """Delete a webhook"""
    try:
        success = await db.delete_webhook(current_user_id, webhook_id)
        if not success:
            error_response = error_handler.create_error_response(
                message="Webhook not found",
                error_code="WEBHOOK_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response["error"])
        return create_success_response(data={}, message="Webhook deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook: {str(e)}")
        error_dict = error_handler.handle_webhook_error(e)
        raise HTTPException(status_code=400, detail=error_dict["error"])
