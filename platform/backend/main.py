"""Iacgenie API — entry point.

App construction lives in app_factory.py to break circular imports
and enable per-process instantiation.  This module re-exports the app
plus a few legacy singletons so existing ``from main import ...``
statements continue to work.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
from datetime import datetime
from models.error_classes import ErrorClass

from dotenv import load_dotenv
from config.storage_config import storage_config

load_dotenv()

# ── App factory ─────────────────────────────────────────────────────
from app_factory import create_app

from contextlib import asynccontextmanager


@asynccontextmanager
async def app_lifespan(fastapi_app: FastAPI) -> Any:
    # --- STARTUP ---
    await initialize_database_on_startup()
    await _init_broadcast()
    try:
        import app_factory

        await app_factory.global_broadcast.start_listening()
        logger.info("Redis broadcast service started")
    except Exception as e:
        logger.warning(f"Redis broadcast service failed to start: {e}")

    async def run_garbage_collector() -> None:
        from src.sandbox_manager.garbage_collector import GarbageCollector

        gc = GarbageCollector()  # type: ignore[no-untyped-call]
        while True:
            try:
                await gc.collect_garbage()
            except Exception as e:
                logger.error(f"Sandbox GC error: {str(e)}")
            await asyncio.sleep(300)

    global gc_task
    gc_task = asyncio.create_task(run_garbage_collector())

    yield

    # --- SHUTDOWN ---
    try:
        await db_provider.close()
        logger.info("Database closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    try:
        from modules.workflow_engine.checkpoint_saver import cleanup_checkpointer

        cleanup_checkpointer()
        logger.info("LangGraph checkpointer cleaned up successfully")
    except Exception as e:
        logger.warning(f"Error cleaning up checkpointer: {str(e)}")
    try:
        import app_factory

        await app_factory.global_broadcast.stop_listening()
        logger.info("Redis broadcast service stopped")
    except Exception as e:
        logger.warning(f"Error stopping Redis broadcast service: {e}")
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
                    import app_factory

                    app_factory.global_broadcast.broadcast_session_failed(
                        session.id, "Server shutting down"
                    )
                except Exception:
                    logger.exception("Failed to notify session %s", session.id)
    except Exception:
        logger.exception("Error during graceful shutdown")


app: FastAPI = create_app(lifespan_handler=app_lifespan)

# Re-export legacy singletons for backward-compat (routers/workflow.py)
from app_factory import limiter, db_provider, agent_executor, global_broadcast  # noqa: F401

from modules.workflow_engine.event_broadcast import EventBroadcastService
from modules.workflow_engine.event_broadcast import WorkflowEvent, EventType
from modules.workflow_engine.orchestrator import WorkflowOrchestrator

# ── Redis broadcast init (called at startup) ───────────────────────────


async def _init_broadcast() -> None:
    """Create global_broadcast with a live RedisClient at startup time.

    Runs the synchronous Redis connect() in a thread pool with a short
    timeout so a slow or unavailable Redis server never blocks startup
    or event processing.
    """
    from modules.workflow_engine.event_broadcast import (
        EventBroadcastService as RedisBroadcast,
    )
    from src.workflow_engine.redis_client import RedisClient
    from src.workflow_engine.config import WorkflowConfig

    try:
        config = WorkflowConfig.from_env()
        rc = RedisClient(config=config)
        # Run sync connect() in a thread pool with a 3-second timeout
        await asyncio.wait_for(asyncio.to_thread(rc.connect), timeout=3.0)
        logger.info("Redis connected — wiring into EventBroadcastService")
        import app_factory

        new_bc = RedisBroadcast(redis_client=rc)  # type: ignore
        app_factory.global_broadcast = new_bc
    except (Exception, asyncio.TimeoutError) as e:
        # Graceful degradation — event bus will drop events but app stays up
        import app_factory

        logger.warning(
            f"Redis unavailable — broadcast service running in degraded mode: {e}"
        )
        new_bc = RedisBroadcast(redis_client=None)
        app_factory.global_broadcast = new_bc

    # Update the local binding so startup_event uses the new instance
    globals()["global_broadcast"] = new_bc


# ── Remaining imports ────────────────────────────────────────────────

from middleware.auth_middleware import verify_access_token, require_admin
from services.webhook_service import get_webhook_service, WebhookEventType
from services.download_service import DownloadService
from utils.structured_logger import get_logger, correlation_id_var
from middleware.error_handling import (
    create_success_response,
    error_handler,
)

logger = get_logger("main")

# ── gc_task reference ────────────────────────────────────────────────

gc_task: Optional["asyncio.Task[None]"] = None

# ── Pydantic models (used by main.py endpoints) ─────────────────────


class GenerationRequest(BaseModel):
    prompt: str = Field(
        ..., description="The prompt describing the infrastructure to generate"
    )
    model: str = Field(
        ..., description="AI model to use for generation (e.g., gpt-4, claude-3)"
    )
    provider: str = Field(
        ..., description="AI provider (e.g., openai, anthropic, mistral)"
    )
    project_id: Optional[str] = Field(
        None, description="Project ID to associate with generation"
    )
    base_job_id: Optional[str] = Field(
        None, description="Previous generation job ID to iterate upon"
    )
    model_config_id: Optional[str] = Field(
        None, description="ID of the selected model configuration"
    )


class GenerationStartResponse(BaseModel):
    success: bool = Field(True, description="Operation success status")
    message: str = Field(
        "Code generation started successfully", description="Success message"
    )
    data: Dict[str, str] = Field(..., description="Response data containing job_id")
    timestamp: str = Field(..., description="ISO timestamp of response")


class GeneratedFile(BaseModel):
    name: str = Field(..., description="File name")
    language: str = Field(..., description="Programming language")
    content: str = Field(..., description="File content")


class ValidationStepLog(BaseModel):
    stage: str = Field(..., description="Processing stage")
    status: str = Field(..., description="Status (running, success, error, retrying)")
    message: str = Field(..., description="Log message")
    timestamp: str = Field(..., description="ISO timestamp")


class GenerationStatusResponse(BaseModel):
    job_id: str = Field(..., description="Generation job ID")
    status: str = Field(
        ..., description="Job status (pending, running, completed, failed)"
    )
    logs: List[ValidationStepLog] = Field(..., description="Processing logs")
    code: Optional[List[GeneratedFile]] = Field(
        None, description="Generated code files"
    )


class DeployRequest(BaseModel):
    job_id: str = Field(..., description="Generation job ID to deploy")
    project_name: str = Field(..., description="Project name for deployment")


class GitHubRequest(BaseModel):
    job_id: str = Field(..., description="Generation job ID to push")
    repo_name: str = Field(..., description="GitHub repository name")
    description: str = Field(..., description="Commit description")


class ClarifyAnswerRequest(BaseModel):
    job_id: str = Field(..., description="Clarification job ID")
    answers: Optional[List[str]] = Field(
        None, description="Legacy field for array of answers"
    )
    message: Optional[str] = Field(
        None, description="User's single conversational reply"
    )
    selected_option_value: Optional[str] = Field(
        None, description="User's selected option value if they clicked a button"
    )


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="Authentication token")
    token_type: str = Field("bearer", description="Token type")
    user: dict[str, Any] = Field(..., description="User information")


class ApiKeyValidationRequest(BaseModel):
    api_key: str = Field(..., description="API key to validate")
    provider: str = Field(..., description="Provider (openai, anthropic, etc.)")


class ApiKeyValidationResponse(BaseModel):
    success: bool = Field(..., description="Validation success status")
    message: str = Field(..., description="Validation message")
    data: Dict[str, Any] = Field(..., description="Validation details")


class HealthResponse(BaseModel):
    success: bool = Field(True, description="Health check success")
    message: str = Field("Service is healthy", description="Health message")
    data: Dict[str, Any] = Field(..., description="Health information")
    timestamp: str = Field(..., description="ISO timestamp")


class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Operation success status")
    error: Dict[str, Any] = Field(..., description="Error details")


# ── Startup / Shutdown ──────────────────────────────────────────────


async def initialize_database_on_startup() -> None:
    """Initialize database on startup"""
    try:
        success = await db_provider.initialize()
        if success:
            logger.info("Database initialized successfully")
            try:
                from db.adapters.persistence_adapter import persistence_adapter

                await persistence_adapter.initialize()
                logger.info("Persistence database adapter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize persistence adapter: {e}")
            try:
                from scripts.create_admin_user import create_admin_user

                await create_admin_user()  # type: ignore
                logger.info("Admin user seeded successfully")
            except Exception as e:
                logger.error(f"Failed to seed admin user: {e}")
        else:
            logger.error("Failed to initialize database")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")


# ── Generation endpoints (non-blocking) ─────────────────────────────


@app.post("/api/generate", response_model=GenerationStartResponse, tags=["Generations"])
@limiter.limit("10/minute")
async def start_generation(
    request: Request,
    gen_request: GenerationRequest,
    background_tasks: BackgroundTasks,
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Start code generation with webhook integration
    Initiates an AI-powered code generation job that creates infrastructure-as-code
    based on the provided prompt. The generation runs asynchronously and sends
    webhook notifications for status updates.
    **Authentication Required**: JWT token in Authorization header
    **Rate Limit**: 10 requests per minute
    """
    try:
        from utils.prompt_sanitizer import sanitize_prompt

        sanitized_prompt = sanitize_prompt(gen_request.prompt)

        # Deduplication: check for recent running job with same prompt
        recent_running = await db_provider.find_recent_running_jobs(
            sanitized_prompt, max_age_minutes=5
        )
        if recent_running:
            existing_job = recent_running[0]
            return create_success_response(
                data={
                    "job_id": existing_job["id"],
                    "session_id": existing_job["id"],
                    "duplicate": True,
                },
                message="Returning existing in-progress generation",
            )

        job_id = str(uuid.uuid4())

        correlation_id = correlation_id_var.get()
        logger.info(
            "Generation started",
            extra={
                "correlation_id": correlation_id,
                "extra_fields": {"job_id": job_id},
            },
        )

        user_id = user.get("uid", "default-user-id")

        job_data = {
            "id": job_id,
            "prompt": sanitized_prompt,
            "model": gen_request.model,
            "provider": gen_request.provider,
            "project_id": gen_request.project_id or "",
            "user_id": user_id,
            "model_config_id": gen_request.model_config_id,
            "status": "pending",
            "metadata": {},
        }
        created_job_id = await db_provider.create_generation_job(job_data)
        if not created_job_id:
            raise RuntimeError("Failed to create generation job in database")

        # Register workflow session so WebSocket can find it
        try:
            from modules.workflow_engine.session_manager import session_manager

            await session_manager.create_session(
                session_id=job_id,
                build_id=job_id,
                user_id=user_id,
                prompt=sanitized_prompt,
            )
            logger.info(f"Registered workflow session: id={job_id}")
        except Exception as e:
            logger.warning(
                f"Failed to register workflow session (will still dispatch Celery): {e}"
            )

        # Offload generation to Celery worker
        background_tasks.add_task(
            _dispatch_generation,
            job_id,
            gen_request.prompt,
            gen_request.model,
            gen_request.provider,
            gen_request.project_id,
            user_id,
            gen_request.base_job_id,
            gen_request.model_config_id,
        )

        return create_success_response(
            data={"job_id": job_id, "session_id": job_id},
            message="Code generation started successfully",
        )
    except Exception as e:
        logger.error(f"Failed to start generation: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to start code generation",
            error_code="INTERNAL_ERROR",
            status_code=500,
            details={"original_error": str(e)},
        )
        raise HTTPException(status_code=500, detail=error_response)


async def _dispatch_generation(
    job_id: str,
    prompt: str,
    model: str,
    provider: str,
    project_id: Optional[str],
    user_id: str,
    base_job_id: Optional[str],
    model_config_id: Optional[str] = None,
) -> None:
    """Dispatch code generation to the Celery worker."""
    try:
        logger.info(f"Dispatching task to Celery for job_id: {job_id}")
        from celery_worker import generate_code_as_celery_task

        result = generate_code_as_celery_task.delay(
            job_id=job_id,
            prompt=prompt,
            model=model,
            provider=provider,
            project_id=project_id,
            user_id=user_id,
            base_job_id=base_job_id,
            model_config_id=model_config_id,
        )
        logger.info(f"Dispatched task to Celery! AsyncResult ID: {result.id}")
    except Exception as e:
        logger.error(f"Failed to dispatch generation to Celery: {str(e)}")
        # Fallback: mark job as failed in DB
        await db_provider.update_generation_job(job_id, {"status": "failed"})


@app.get(
    "/api/generate/status/{job_id}",
    response_model=GenerationStatusResponse,
    tags=["Generations"],
)
async def get_generation_status(
    job_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """
    Get generation status
    Retrieves the current status and results of a code generation job.
    Returns detailed logs and generated code files if the job is completed.
    **Authentication Required**: Requires a valid JWT token
    """
    try:
        job = await db_provider.get_generation_job(job_id)
        if not job:
            error_response = error_handler.create_error_response(
                message="Job not found", error_code="RECORD_NOT_FOUND", status_code=404
            )
            raise HTTPException(status_code=404, detail=error_response)
        raw_logs = job.get("logs") or []
        job_logs: List[ValidationStepLog] = []
        for entry in raw_logs:
            if isinstance(entry, dict):
                job_logs.append(
                    ValidationStepLog(
                        stage=entry.get("stage", ""),
                        status=entry.get("status", ""),
                        message=entry.get("message", ""),
                        timestamp=entry.get("timestamp", ""),
                    )
                )
            elif isinstance(entry, ValidationStepLog):
                job_logs.append(entry)
        raw_code = job.get("code") or []
        job_code: Optional[List[GeneratedFile]] = None
        if raw_code:
            job_code = []
            for f in raw_code:
                if isinstance(f, dict):
                    job_code.append(
                        GeneratedFile(
                            name=f.get("name", ""),
                            language=f.get("language", ""),
                            content=f.get("content", ""),
                        )
                    )
                elif isinstance(f, GeneratedFile):
                    job_code.append(f)
        return GenerationStatusResponse(
            job_id=job_id,
            status=job["status"],
            logs=job_logs,
            code=job_code,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get generation status: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get generation status",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/clarify/answer", tags=["Clarification"])
async def submit_clarify_answer(
    request: ClarifyAnswerRequest,
    background_tasks: BackgroundTasks,
    user: Any = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Submit a conversational reply to clarification questions. Re-runs LLM analysis."""
    try:
        # 1. Get the job from DB
        job = await db_provider.get_generation_job(request.job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=error_handler.create_error_response(
                    message="Job not found",
                    error_code="RECORD_NOT_FOUND",
                    status_code=404,
                ),
            )

        # 2. Extract message and append to history
        user_message = request.message
        if not user_message and request.selected_option_value:
            user_message = f"I select: {request.selected_option_value}"
        if not user_message and request.answers and len(request.answers) > 0:
            user_message = request.answers[0]
        if not user_message:
            user_message = "No input provided."

        metadata = job.get("metadata", {}) or {}
        history = metadata.get("clarification_history", [])

        # Only initialize history if empty
        if not history:
            history.append(
                {
                    "role": "assistant",
                    "content": (
                        "Hello! I am reviewing your request. "
                        "To ensure a robust architecture, I need a few more details."
                    ),
                }
            )

        history.append({"role": "user", "content": user_message})

        # Save updated history back to DB
        metadata["clarification_history"] = history
        await db_provider.update_generation_job(
            request.job_id,
            {
                "status": "clarifying",
                "metadata": metadata,
            },
        )

        # 3. Build IaCState and run ClarifyAgent with accumulated history
        from agents.clarify_agent import ClarifyAgent
        from models.iac_state import IaCState

        acs = IaCState(  # type: ignore
            session_id=request.job_id,
            user_request=job.get("prompt", ""),
            refined_spec=job.get("refined_spec"),
            clarification_history=history,
        )

        # Retrieve model_config so that ClarifyAgent uses the configured model
        model_config = None
        model_config_id = job.get("model_config_id")
        if model_config_id:
            project_id = job.get("project_id", "")
            job_user_id = job.get("user_id", user.get("uid", ""))
            try:
                model_config = await db_provider.get_model_config(
                    job_user_id, project_id, model_config_id
                )
            except Exception as e:
                logger.warning(f"Failed to load model_config for clarify: {e}")

        agent = ClarifyAgent()
        await agent.initialize(acs, model_config=model_config)
        try:
            result = await asyncio.wait_for(agent.execute(), timeout=120)
        except asyncio.TimeoutError:
            await db_provider.update_generation_job(
                request.job_id,
                {
                    "status": "failed",
                    "error": "Clarification timed out after 120s",
                },
            )
            raise HTTPException(status_code=504, detail="Clarification timed out")

        # 4. Process result
        if not result.get("success"):
            # Check if this is a true failure/error (not a clarification request)
            if result.get("error_class") != ErrorClass.CLARIFICATION:
                error_msg = result.get("error", "Clarification failed")
                await db_provider.update_generation_job(
                    request.job_id,
                    {
                        "status": "failed",
                        "error": error_msg,
                    },
                )
                return create_success_response(
                    data={"status": "failed", "error": error_msg},
                    message="Clarification failed",
                )

            # Genuine clarification questions
            agent_message = (
                result.get("message")
                or "Could you provide more specific technical details about your desired architecture?"
            )
            options = result.get("options", [])

            # Append the AI's question to the chat history and save
            history.append(
                {"role": "assistant", "content": agent_message, "options": options}
            )
            metadata["clarification_history"] = history

            await db_provider.update_generation_job(
                request.job_id,
                {
                    "metadata": metadata,
                    "status": "pending_human",
                },
            )
            # The global broadcast expects the old structure, or we can send the new structure
            # The client uses WebSockets, we'll broadcast the message and options.
            global_broadcast.broadcast_clarify_question(
                request.job_id, [agent_message], options=options
            )
            return create_success_response(
                data={
                    "status": "questions",
                    "message": agent_message,
                    "options": options,
                },
                message="Additional clarification needed",
            )

        # 5. Clarification succeeded — pause for human review of the plan
        refined_spec = result.get("result", {}).get("refined_spec")

        # Clear out clarification history since we are done
        metadata.pop("clarification_history", None)

        await db_provider.update_generation_job(
            request.job_id,
            {
                "refined_spec": json.dumps(refined_spec) if refined_spec else None,
                "status": "pending_human",
                "metadata": metadata,
            },
        )
        global_broadcast.broadcast_clarify_complete(
            request.job_id, has_spec=bool(refined_spec)
        )

        # Broadcast human_review_requested WITH the refined_spec so the
        # frontend can display it in the InlineReviewPanel.
        # The user must click "Approve" which triggers the approve endpoint
        # to dispatch the Celery generation task.
        global_broadcast.broadcast_human_review(
            request.job_id,
            "Review the infrastructure plan and approve to proceed with code generation.",
            refined_spec=refined_spec,
        )

        return create_success_response(
            data={"status": "review", "refined_spec": refined_spec},
            message="Clarification complete — awaiting human approval of plan",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process clarification answer: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to process clarification answer",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# ── Remaining endpoints ─────────────────────────────────────────────


@app.post("/api/deploy", tags=["Deployments"])
async def deploy_infrastructure(
    request: DeployRequest, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Deploy infrastructure with webhook integration
    Initiates deployment of generated infrastructure code to cloud providers.
    Sends webhook notifications for deployment status updates.
    **Authentication Required**: JWT token in Authorization header
    **Rate Limit**: 20 requests per hour
    """
    try:
        user_id = user.get("uid", "default-user-id")
        db = db_provider.adapter
        try:
            webhook_service = await get_webhook_service(db)
            await webhook_service.send_webhook(
                WebhookEventType.DEPLOYMENT_STARTED.value,
                {
                    "job_id": request.job_id,
                    "project_name": request.project_name,
                    "user_id": user_id,
                },
                user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to send deployment started webhook: {str(e)}")
        deployment_id = str(uuid.uuid4())
        # Look up project config for real credentials
        provider = "aws"
        region = "us-west-2"
        credentials_id = "default-credentials"
        try:
            project = await db.get_project_by_user(user_id, request.project_name)
            if project:
                provider_config = project.get("provider_config", {})
                provider = provider_config.get("provider", provider)
                region = provider_config.get("region", region)
                credentials_id = provider_config.get("credentialsId", credentials_id)
        except Exception:
            pass  # Fall back to defaults
        await db.create_deployment(
            user_id,
            request.project_name,
            {
                "generationId": request.job_id,
                "provider": provider,
                "region": region,
                "credentialsId": credentials_id,
                "status": "pending",
                "deploymentId": deployment_id,
            },
        )

        # Trigger Celery task
        from celery_worker import deploy_infrastructure as deploy_infrastructure_task

        deploy_infrastructure_task.delay(request.job_id, request.project_name)

        return create_success_response(
            data={
                "deployment_id": deployment_id,
                "job_id": request.job_id,
                "project_name": request.project_name,
                "status": "pending",
            },
            message="Deployment started successfully",
        )
    except Exception as e:
        logger.error(f"Failed to start deployment: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to start deployment",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/github", tags=["GitHub Integration"])
async def push_to_github(
    request: GitHubRequest, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Push code to GitHub with webhook integration
    Pushes generated infrastructure code to a GitHub repository.
    Sends webhook notifications for GitHub operations.
    **Authentication Required**: JWT token in Authorization header
    **Rate Limit**: 50 requests per hour
    """
    try:
        user_id = user.get("uid", "default-user-id")
        db = db_provider.adapter
        try:
            webhook_service = await get_webhook_service(db)
            await webhook_service.send_webhook(
                "github.push",
                {
                    "job_id": request.job_id,
                    "repo_name": request.repo_name,
                    "description": request.description,
                    "user_id": user_id,
                },
                user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to send GitHub push webhook: {str(e)}")

        # Look up GitHub config from project
        repo_url = request.repo_name
        github_token = ""
        try:
            project = await db.get_project_by_user(user_id, "")
            if project:
                git_config = project.get("git_config", {})
                repo_url = git_config.get("repo_url", repo_url)
                github_token = git_config.get("token", "")
        except Exception:
            pass

        if not github_token:
            return error_handler.create_error_response(
                message="GitHub token not configured. Set git_config.token in project settings.",
                error_code="BAD_REQUEST",
                status_code=400,
            )

        # Trigger Celery task
        from celery_worker import push_to_github as github_task

        github_task.delay(request.job_id, repo_url, github_token, request.description)

        return create_success_response(
            data={
                "job_id": request.job_id,
                "repo_name": request.repo_name,
                "status": "pushed",
            },
            message="GitHub push started",
        )
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to push to GitHub",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/logs/{job_id}", tags=["Logs"])
async def get_logs(
    job_id: str, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """
    Get job logs
    Retrieves detailed logs for a specific job.
    **Authentication Required**: Requires a valid JWT token
    """
    try:
        job = await db_provider.get_generation_job(job_id)
        if not job:
            error_response = error_handler.create_error_response(
                message="Job not found", error_code="RECORD_NOT_FOUND", status_code=404
            )
            raise HTTPException(status_code=404, detail=error_response)
        raw_logs = job.get("logs") or []
        log_entries: List[Dict[str, Any]] = raw_logs if raw_logs else []
        return create_success_response(
            data={"logs": log_entries}, message="Logs retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get logs: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get logs", error_code="INTERNAL_ERROR", status_code=500
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/download/{job_id}", tags=["Downloads"])
async def download_project(
    job_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """
    Download generated project as ZIP
    **Authentication Required**: Requires a valid JWT token
    """
    try:
        job = await db_provider.get_generation_job(job_id)
        if not job or job.get("status") != "completed":
            error_response = error_handler.create_error_response(
                message="Job not found or not completed",
                error_code="RECORD_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response)
        generated_files = job.get("code") or []
        if not generated_files:
            error_response = error_handler.create_error_response(
                message="No generated files found",
                error_code="RECORD_NOT_FOUND",
                status_code=404,
            )
            raise HTTPException(status_code=404, detail=error_response)
        zip_bytes = DownloadService.create_zip_archive(generated_files)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=project_{job_id}.zip"
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download project: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to download project",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/generate/{job_id}/download", tags=["Downloads"])
async def download_generated_project(
    job_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """.. deprecated:: 1.0.0 Use GET /api/download/{job_id} instead."""
    logger.warning(
        f"Deprecated endpoint GET /api/generate/{job_id}/download called. Redirecting to /api/download/{job_id}."
    )
    return RedirectResponse(url=f"/api/download/{job_id}", status_code=307)


@app.get("/api/sessions/{session_id}/file/{filename:path}", tags=["Downloads"])
async def get_generated_file(
    session_id: str,
    filename: str,
    user: Any = Depends(verify_access_token),
) -> Any:
    """Download a specific generated file from MinIO."""
    try:
        from modules.artifact_store.minio_client import minio_client

        object_name = f"sessions/{session_id}/files/{filename}"
        content = await minio_client.download_artifact(
            bucket_name=storage_config.MINIO_ARTIFACTS_BUCKET,
            object_name=object_name,
        )
        # Detect content type from extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        ext_to_mime: Dict[str, str] = {
            "tf": "text/hcl",
            "hcl": "text/hcl",
            "py": "text/x-python",
            "yaml": "text/yaml",
            "yml": "text/yaml",
            "json": "application/json",
            "sh": "text/x-shellscript",
            "md": "text/markdown",
            "toml": "text/toml",
        }
        media_type = ext_to_mime.get(ext, "text/plain")
        return Response(
            content=content,
            media_type=media_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to download file {filename} for session {session_id}: {str(e)}"
        )
        error_response = error_handler.create_error_response(
            message="Failed to download file",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/sessions/{session_id}/resume", tags=["Workflows"])
async def resume_workflow(
    session_id: str,
    payload: Dict[str, Any],
    user: Any = Depends(verify_access_token),
) -> Any:
    """Resume a paused workflow after human review / clarification.

    Expects JSON body:
    {
      "answers": ["answer 1", "answer 2", ...]   // user answers to clarify questions
    }
    """
    try:
        answers = payload.get("answers", [])
        if not answers:
            return error_handler.create_error_response(
                message="No answers provided",
                error_code="BAD_REQUEST",
                status_code=400,
            )

        # Store answers in session metadata as retry_feedback
        await db_provider.update_generation_job(
            session_id,
            {
                "metadata": {"retry_feedback": json.dumps(answers)},
            },
        )

        # Build a broadcast service for this session
        bc = EventBroadcastService()
        bc.broadcast(
            WorkflowEvent(
                event_type=EventType.AGENT_START,
                session_id=session_id,
                data={"agent": "ClarifyAgent (resume)"},
            )
        )

        # Create and resume the workflow
        from src.agent_executor.main import AgentExecutor

        orchestrator = WorkflowOrchestrator(
            postgres_url=None,
            event_broadcast=bc,
            agent_executor=AgentExecutor(),
        )
        result = await orchestrator.resume(session_id)

        if result.get("error"):
            return error_handler.create_error_response(
                message=result.get("error", "Resume failed"),
                error_code="RESUME_FAILED",
                status_code=500,
            )

        bc.broadcast(
            WorkflowEvent(
                event_type=EventType.AGENT_COMPLETE,
                session_id=session_id,
                data={"agent": "ClarifyAgent (resume)", "success": True},
            )
        )

        return create_success_response(
            message="Workflow resumed",
            data={"session_id": session_id},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume workflow for session {session_id}: {str(e)}")
        return error_handler.create_error_response(
            message="Failed to resume workflow",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )


# ── Dead Letter Queue & Heartbeat endpoints (Fix 7 + Fix 10) ──────────


@app.get("/api/dlq/jobs", tags=["Operations"])
async def list_dead_letter_jobs(user: dict = Depends(require_admin)) -> Any:
    """List jobs in the dead letter queue."""
    try:
        from src.workflow_engine.config import WorkflowConfig
        from src.workflow_engine.redis_client import RedisClient

        rc = RedisClient(config=WorkflowConfig())
        rc.connect()
        entries = []
        for key in rc.get_all_keys(match="dead_letter_queue*"):  # type: ignore[call-arg]
            data = rc.get(key)
            if data:
                entries.append(data)
        rc.disconnect()
        return create_success_response(
            data={"dlq_jobs": entries, "count": len(entries)}
        )
    except Exception as e:
        return error_handler.create_error_response(
            error_code="DLQ_ERROR",
            message=f"Failed to read DLQ: {str(e)}",
            status_code=500,
        )


@app.post("/api/dlq/retry/{job_id}", tags=["Operations"])
async def retry_dead_letter_job(
    job_id: str, user: dict = Depends(require_admin)
) -> Any:
    """Re-dispatch a DLQ job for retry."""
    try:
        from src.workflow_engine.config import WorkflowConfig
        from src.workflow_engine.redis_client import RedisClient
        from modules.workflow_engine.event_broadcast import (
            EventType,
            EventBroadcastService,
            WorkflowEvent,
        )

        rc = RedisClient(config=WorkflowConfig())
        rc.connect()
        # Find the DLQ entry for this job
        dlq_entry = None
        for key in rc.get_all_keys(match="dead_letter_queue*"):  # type: ignore[call-arg]
            data = rc.get(key)
            if data and isinstance(data, dict) and data.get("job_id") == job_id:
                dlq_entry = data
                rc.delete(key)
                break

        if not dlq_entry:
            return error_handler.create_error_response(
                error_code="NOT_FOUND",
                message=f"Job {job_id} not found in DLQ",
                status_code=404,
            )

        rc.disconnect()

        # Re-dispatch to Celery
        from celery_worker import generate_code_as_celery_task

        generate_code_as_celery_task.delay(
            job_id=dlq_entry["job_id"],
            prompt=dlq_entry["prompt"],
            model=dlq_entry["model"],
            provider=dlq_entry["provider"],
            project_id=dlq_entry.get("project_id"),
            user_id=dlq_entry.get("user_id", "default-user-id"),
        )

        # Broadcast that retry is in progress
        bc = EventBroadcastService()
        bc.broadcast(
            WorkflowEvent(
                event_type=EventType.SESSION_UPDATED,
                session_id=job_id,
                data={"message": "Job re-queued for retry from DLQ"},
            )
        )

        return create_success_response(
            data={"job_id": job_id, "message": "Job re-queued for retry"}
        )
    except Exception as e:
        return error_handler.create_error_response(
            error_code="DLQ_RETRY_ERROR",
            message=f"Failed to retry job: {str(e)}",
            status_code=500,
        )


@app.get("/api/generate/job/{job_id}", tags=["Operations"])
async def get_generation_job_status(
    job_id: str, user: dict = Depends(verify_access_token)
) -> Any:
    """Get the current status of a generation job (for frontend reconciliation)."""
    try:
        job = await db_provider.get_generation_job(job_id)
        if not job:
            return error_handler.create_error_response(
                error_code="NOT_FOUND",
                message="Job not found",
                status_code=404,
            )
        return create_success_response(
            data={
                "job_id": job_id,
                "status": job.get("status"),
                "metadata": job.get("metadata", {}),
            }
        )
    except Exception as e:
        return error_handler.create_error_response(
            error_code="INTERNAL_ERROR",
            message="Failed to fetch job status",
            status_code=500,
            details={"original_error": str(e)},
        )


@app.get("/api/generate/heartbeat/{job_id}", tags=["Operations"])
async def get_generation_heartbeat(
    job_id: str, user: dict = Depends(verify_access_token)
) -> Any:
    """Check if a generation job is alive (received recent heartbeat)."""
    try:
        job = await db_provider.get_generation_job(job_id)
        if not job:
            return error_handler.create_error_response(
                error_code="NOT_FOUND",
                message="Job not found",
                status_code=404,
            )
        meta = job.get("metadata", {})
        hb = meta.get("last_heartbeat")
        return create_success_response(
            data={
                "job_id": job_id,
                "alive": hb is not None,
                "last_heartbeat": hb,
                "status": job.get("status"),
                "retry_count": meta.get("retry_count", 0),
            }
        )
    except Exception as e:
        return error_handler.create_error_response(
            error_code="HEARTBEAT_ERROR",
            message=f"Failed to get heartbeat: {str(e)}",
            status_code=500,
        )


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    **No Authentication Required**: Public health check endpoint
    """
    try:
        from services.health_service import health_service

        health_data = await health_service.check_system_health()
        logger.info(
            f"health_check status={health_data['status']} duration_ms={health_data['duration_ms']}"
        )
        return create_success_response(
            data=health_data, message="Service health check completed"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Service is unhealthy",
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
            details={"error": str(e)},
        )
        raise HTTPException(status_code=503, detail=error_response)


@app.get("/api/health/summary", tags=["Health"])
async def health_summary() -> Dict[str, Any]:
    """Health check summary endpoint."""
    try:
        from services.health_service import health_service

        summary = await health_service.get_health_summary()
        return create_success_response(data=summary, message="Health summary retrieved")
    except Exception as e:
        logger.error(f"Health summary failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Health summary unavailable")


@app.get("/api/metrics/generations", tags=["Monitoring"])
async def get_generation_metrics() -> Any:
    """Get generation metrics."""
    try:
        metrics = await db_provider.get_generation_metrics()
        return create_success_response(
            data=metrics, message="Generation metrics retrieved"
        )
    except Exception as e:
        logger.error(f"Failed to get generation metrics: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get generation metrics",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/metrics", tags=["Monitoring"])
async def metrics() -> Any:
    """Prometheus metrics endpoint."""
    try:
        from services.metrics_service import metrics_service

        return Response(
            content=metrics_service.get_metrics(),
            media_type=metrics_service.get_metrics_content_type(),
        )
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Metrics unavailable")


@app.get("/api/monitoring/dashboard", tags=["Monitoring"])
async def monitoring_dashboard(response: Response) -> Dict[str, Any]:
    response.headers["X-Deprecation"] = "true"
    """Monitoring dashboard data."""
    try:
        from services.health_service import health_service
        from services.alerting_service import alerting_service

        health_data = await health_service.check_system_health()
        alerts = await alerting_service.check_health_alerts(health_data)
        for alert in alerts:
            await alerting_service.send_alert(alert)
        alert_summary = alerting_service.get_alert_summary(hours=24)
        dashboard_data = {
            "health": health_data,
            "alerts": {"current": alerts, "summary": alert_summary},
            "timestamp": datetime.utcnow().isoformat(),
        }
        return create_success_response(
            data=dashboard_data, message="Monitoring dashboard data retrieved"
        )
    except Exception as e:
        logger.error(f"Monitoring dashboard failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Monitoring data unavailable")


@app.get("/api/monitoring/alerts", tags=["Monitoring"])
async def get_alerts(
    response: Response, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    response.headers["X-Deprecation"] = "true"
    """Get alert history."""
    try:
        from services.alerting_service import alerting_service

        alerts = alerting_service.get_alert_history(hours=24)
        summary = alerting_service.get_alert_summary(hours=24)
        return create_success_response(
            data={"alerts": alerts, "summary": summary},
            message="Alert history retrieved",
        )
    except Exception as e:
        logger.error(f"Alert history failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Alert history unavailable")


@app.get("/api/database/health", response_model=HealthResponse, tags=["Health"])
async def database_health_check() -> Dict[str, Any]:
    """Database health check endpoint."""
    try:
        health = await db_provider.health_check()
        return create_success_response(
            data=health, message="Database health check completed"
        )
    except Exception as e:
        error_response = error_handler.create_error_response(
            message="Database is unhealthy",
            error_code="DB_CONNECTION_ERROR",
            status_code=503,
            details={"error": str(e)},
        )
        raise HTTPException(status_code=503, detail=error_response)


@app.get("/api/database/info", tags=["System"])
async def database_info() -> Dict[str, Any]:
    """Get database information."""
    try:
        info = {
            "provider": db_provider.provider,
            "adapter": db_provider.adapter.__class__.__name__
            if db_provider.adapter
            else "None",
            "initialized": db_provider._is_initialized,
            "timestamp": datetime.now().isoformat(),
        }
        return create_success_response(
            data=info, message="Database information retrieved"
        )
    except Exception as e:
        logger.error(f"Failed to get database info: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get database information",
            error_code="DB_CONNECTION_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/debug/database", tags=["Debug"])
async def debug_database(user: Any = Depends(require_admin)) -> Dict[str, Any]:
    """Debug database connection."""
    try:
        test_data = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "message": "Database connection test",
        }
        health_result = await db_provider.health_check()
        if health_result.get("status") == "healthy":
            return create_success_response(
                data={
                    "connection": "successful",
                    "health_check": health_result,
                    "test_data": test_data,
                },
                message="Database connection test successful",
            )
        else:
            error_response = error_handler.create_error_response(
                message="Database health check failed",
                error_code="DB_CONNECTION_ERROR",
                status_code=500,
            )
            raise HTTPException(status_code=500, detail=error_response)
    except Exception as e:
        logger.error(f"Database debug failed: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Database connection test failed",
            error_code="DB_CONNECTION_ERROR",
            status_code=500,
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/debug/create-test-config", tags=["Debug"])
async def create_test_config(user: Any = Depends(require_admin)) -> Dict[str, Any]:
    """Create a test model configuration."""
    try:
        user_id = user.get("uid", "default-user-id")
        db = db_provider.adapter
        config_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "api_key": "sk-test-key",
            "max_tokens": 4000,
            "temperature": 0.7,
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "headers": {},
            "metadata": {"test": True},
        }
        result = await db.create_model_config(user_id, "demo_project_001", config_data)
        try:
            webhook_service = await get_webhook_service(db)
            await webhook_service.send_webhook(
                WebhookEventType.MODEL_CONFIG_CREATED.value,
                {
                    "config_id": result.get("id"),
                    "provider": config_data["provider"],
                    "model_name": config_data["model_name"],
                    "project_id": "demo_project_001",
                },
                user_id,
                "demo_project_001",
            )
        except Exception as e:
            logger.warning(f"Failed to send model config created webhook: {str(e)}")
        return create_success_response(
            data=result, message="Test configuration created successfully"
        )
    except Exception as e:
        logger.error(f"Failed to create test config: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to create test configuration",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/models", tags=["Models"])
async def get_available_models() -> Dict[str, Any]:
    """Get available AI models."""
    try:
        models = {
            "openai": {"models": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]},
            "anthropic": {
                "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
            },
            "google": {"models": ["gemini-pro", "gemini-pro-vision"]},
            "mistral": {"models": ["mistral-large", "mistral-medium", "mistral-small"]},
        }
        return create_success_response(
            data={"models": models}, message="Available models retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get models: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to get available models",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/models/health", tags=["Models"])
async def get_models_health() -> Dict[str, Any]:
    """Check health of AI models."""
    try:
        health_status = {"status": "success", "models": []}
        return create_success_response(
            data=health_status, message="Model health check completed"
        )
    except Exception as e:
        logger.error(f"Failed to check model health: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to check model health",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=500,
        )
        raise HTTPException(status_code=500, detail=error_response)


# DEPRECATED: Legacy login endpoints removed
# Use POST /auth/token for authentication instead


import fastapi


async def get_current_user(authorization: str = fastapi.Header(None)) -> dict:
    return {"uid": "test-user-id", "email": "test@example.com"}


@app.get("/api/protected", tags=["Authentication"])
def protected_route(user: Any = Depends(verify_access_token)) -> Dict[str, Any]:
    """Protected route example."""
    return create_success_response(
        data={"message": "This is a protected route", "user": user},
        message="Protected route accessed successfully",
    )


@app.post(
    "/api/validate-key",
    response_model=ApiKeyValidationResponse,
    tags=["Authentication"],
)
async def validate_api_key(
    key_data: ApiKeyValidationRequest, user: Any = Depends(verify_access_token)
) -> Dict[str, Any]:
    """Validate API key format."""
    try:
        api_key = key_data.api_key
        provider = key_data.provider
        if provider == "openai" and api_key.startswith("sk-"):
            return create_success_response(
                data={
                    "valid": True,
                    "provider": "openai",
                    "message": "openai API key format is valid",
                },
                message="API key validation successful",
            )
        elif provider == "anthropic" and api_key.startswith("sk-ant-"):
            return create_success_response(
                data={
                    "valid": True,
                    "provider": "anthropic",
                    "message": "anthropic API key format is valid",
                },
                message="API key validation successful",
            )
        else:
            return create_success_response(
                data={
                    "valid": False,
                    "provider": provider,
                    "message": f"Invalid {provider} API key format",
                },
                message="API key validation failed",
            )
    except Exception as e:
        logger.error(f"Failed to validate API key: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Failed to validate API key",
            error_code="VALIDATION_ERROR",
            status_code=400,
        )
        raise HTTPException(status_code=400, detail=error_response)


# DEPRECATED: Legacy model config endpoints removed
# Use /api/model-configs/{project_id}/ endpoints with authentication instead

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
