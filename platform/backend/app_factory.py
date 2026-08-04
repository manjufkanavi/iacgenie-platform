"""Application factory for the Iacgenie FastAPI application.

Extracts app construction (middleware, routers, lifecycle) from main.py
to break circular imports and enable per-process instantiation.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import middleware
from middleware.correlation_id import CorrelationIDMiddleware
from middleware.error_handling import error_handling_middleware
from middleware.logging_middleware import logging_middleware
from middleware.rate_limiting import rate_limit_middleware
from middleware.tenant_middleware import tenant_middleware

# Import tracing
from utils.tracing import init_tracing

init_tracing()

# Load environment variables
load_dotenv()

# Allow specific application domains via environment variable
from config.cors import ALLOWED_ORIGINS

# =====================
# Shared singletons
# =====================

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Database provider (singleton imported from db_provider module)
from db.db_provider import db_provider  # noqa: F401  # re-exported for main.py

# AgentExecutor placeholder — real instance created per-Celery-task.
# Kept here so routers/workflow.py can import it without circular deps.
# Routers that need a real instance should create one locally or use Celery.
from modules.agent_executor.main import AgentExecutor  # noqa: F401  # re-exported for main.py

agent_executor: Any = None

# Redis broadcast service — created at startup in main.py with a live RedisClient
global_broadcast: Any = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan: startup and graceful shutdown."""
    # Startup: nothing to do here (broadcast is created in main.py)
    logger.info("Iacgenie API starting up")
    yield
    # Shutdown: broadcast session_failed for any active sessions
    logger.info("Iacgenie API shutting down — notifying active sessions")
    try:
        from modules.workflow_engine.session_manager import session_manager

        active_states = {
            "created",
            "clarify",
            "coding",
            "validating",
            "planning",
            "applying",
            "testing",
            "git_push",
            "ci_trigger",
            "ci_monitor",
            "human_review",
        }
        sessions = await session_manager.list_sessions()
        active = [s for s in sessions if s.status in active_states]
        if active:
            logger.info("Notifying %d active session(s) of shutdown", len(active))
            for session in active:
                try:
                    global_broadcast.broadcast_session_failed(
                        session.id, "Server shutting down"
                    )
                except Exception:
                    logger.exception("Failed to notify session %s", session.id)
    except Exception:
        logger.exception("Error during graceful shutdown")


def create_app(lifespan_handler: Any = None) -> FastAPI:
    """Build and configure the FastAPI application.

    This factory function centralises all app construction — middleware,
    routers, and top-level endpoints — so that ``main.py`` can import it
    without redefining anything and Celery workers avoid importing it.
    """

    app = FastAPI(
        title="Iacgenie API",
        lifespan=lifespan_handler,
        description="""
# Iacgenie API

A comprehensive API for generating and managing infrastructure-as-code using AI.

## Features

- **AI-Powered Code Generation**: Generate infrastructure code using various AI models

- **Project Management**: Organize and manage your infrastructure projects

- **Deployment Automation**: Deploy generated infrastructure to cloud providers

- **Webhook Integration**: Real-time notifications and external integrations

- **Team Collaboration**: Manage team members and permissions

- **Audit Logging**: Comprehensive audit trail for all operations

## Authentication

Most endpoints require authentication. Include your JWT token in the Authorization header:

```http

Authorization: Bearer <your-jwt-token>

```

## Rate Limiting

API endpoints are protected by rate limiting to ensure fair usage:

- **CRUD Operations**: 100 requests per hour

- **Code Generation**: 30 requests per hour

- **Admin Operations**: 10 requests per hour

- **Webhook Operations**: 50 requests per hour

## Response Format

All API responses follow a standardized format:

```json

{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... },
  "timestamp": "2025-07-06T17:00:00.000Z"
}

```

### Error Response

```json

{
  "success": false,
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE",
    "statusCode": 400,
    "details": { ... },
    "timestamp": "2025-07-06T17:00:00.000Z"
  }
}

```

## Webhooks

Iacgenie AI supports comprehensive webhook functionality for real-time notifications:

- **Outgoing Webhooks**: Send notifications to external services

- **Incoming Webhooks**: Receive webhooks from external services

- **Event Types**: 20+ supported event types

- **Security**: HMAC signature verification

- **Retry Logic**: Automatic retry with exponential backoff

For detailed webhook documentation, see the Webhooks section.
        """,
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        servers=[
            {"url": "http://localhost:8000", "description": "Development server"},
            {"url": "https://api.iacgenie.ai", "description": "Production server"},
        ],
    )

    app.state.limiter = limiter

    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from middleware.error_handling import error_handler

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        status_code = 422
        if request.url.path.startswith("/api/auth") or "/api/auth/" in request.url.path:
            errors = exc.errors()
            # If any error is a value_error and the input is not empty/None, return 400
            if any(
                err.get("type") == "value_error" and err.get("input") not in ("", None)
                for err in errors
            ):
                status_code = 400
        error_response = error_handler.create_error_response(
            message=str(exc.errors()),
            error_code="VALIDATION_ERROR",
            status_code=status_code,
        )
        return JSONResponse(
            status_code=status_code,
            content=error_response,
        )

    # =========================
    # Middleware registration
    # =========================

    # Correlation ID (registered once)
    app.add_middleware(CorrelationIDMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # HTTP-level middleware (order: logging, tenant, error, rate limit)
    app.middleware("http")(logging_middleware)
    app.middleware("http")(tenant_middleware)
    app.middleware("http")(error_handling_middleware)
    app.middleware("http")(rate_limit_middleware)

    # =========================
    # Router registration
    # =========================

    # Import routers
    from routers.auth import router as auth_router
    from routers.projects import router as projects_router
    from routers.crud import (
        team_members_router,
        integrations_router,
        api_keys_router,
        audit_logs_router,
        generations_router,
        deployments_router,
        billing_router as billing_router,
        model_configs_router,
        git_repositories_router,
        cloud_credentials_router,
    )
    from routers.artifacts import router as artifacts_router
    from routers.webhooks import webhooks_router
    from routers.persistence import router as persistence_router
    from routers.workflow import router as workflow_router
    from routers.llm import router as llm_router
    from routers.secrets import router as secrets_router
    from routers.git import router as git_router
    from routers.agents import router as agents_router
    from routers.sandbox import router as sandbox_router
    from routers.code import router as code_router
    from routers.pipeline import router as pipeline_router
    from routers.ws_pipeline import router as ws_pipeline_router
    from routers.database import router as database_router
    from routers.observability import router as observability_router
    from routers.metrics import router as metrics_router

    app.include_router(auth_router)
    app.include_router(team_members_router)
    app.include_router(integrations_router)
    app.include_router(api_keys_router)
    app.include_router(audit_logs_router)
    app.include_router(generations_router)
    app.include_router(deployments_router)
    app.include_router(billing_router)
    app.include_router(model_configs_router)
    app.include_router(git_repositories_router)
    app.include_router(cloud_credentials_router)
    app.include_router(webhooks_router)
    app.include_router(persistence_router)
    app.include_router(workflow_router)
    app.include_router(artifacts_router)
    app.include_router(llm_router)
    app.include_router(secrets_router)
    app.include_router(git_router)
    app.include_router(agents_router)
    app.include_router(sandbox_router)
    app.include_router(code_router)
    app.include_router(projects_router)
    app.include_router(pipeline_router)
    app.include_router(ws_pipeline_router)
    app.include_router(database_router)
    app.include_router(observability_router)
    app.include_router(metrics_router)

    # Prometheus metrics endpoint
    @app.get("/api/metrics", tags=["metrics"])
    async def prometheus_metrics():
        """Expose Prometheus metrics"""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Disable automatic redirects for trailing slashes
    app.router.redirect_slashes = False

    return app
