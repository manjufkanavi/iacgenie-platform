from celery import Celery

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables

load_dotenv()

logger = logging.getLogger(__name__)

# Celery configuration

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("iacgenie", broker=redis_url, backend=redis_url)

# Celery settings

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800")),  # 30 min default
    task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "1500")),
    task_routes={
        "celery_worker.execute_pipeline_phase": {"queue": "pipeline_phases"},
        "celery_worker.generate_code_as_celery_task": {"queue": "generations"},
    },
    # Per-task retry config
    task_annotations={
        "celery_worker.generate_code_as_celery_task": {
            "rate_limit": "10/m",
        },
    },
)

# Readable timeout for the asyncio pipeline
GENERATION_TIMEOUT_SECONDS = int(os.getenv("GENERATION_TIMEOUT_SECONDS", "120"))


def _is_transient_error(error_msg: str) -> bool:
    """Classify errors as transient (retryable) or permanent."""
    error_lower = error_msg.lower()
    transient_patterns = [
        "rate limit",
        "429",
        "timeout",
        "oom",
        "memory",
        "connection refused",
        "econnrefused",
        "etimedout",
        "503",
        "service unavailable",
        "too many requests",
        "quota",
        "api limit",
    ]
    return any(pat in error_lower for pat in transient_patterns)


# Import tasks

celery_app.autodiscover_tasks()


# ── Helpers used inside generate_code_as_celery_task ──────────────


def _make_log_entry(stage: str, status: str, message: str) -> Dict[str, Any]:
    """Create a standardized log entry."""
    return {
        "stage": stage,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }


# ── Core Celery task ──────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="celery_worker.generate_code_as_celery_task",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
)
def generate_code_as_celery_task(
    self: Any,
    job_id: str,
    prompt: str,
    model: str,
    provider: str,
    project_id: Optional[str] = None,
    user_id: str = "default-user-id",
    base_job_id: Optional[str] = None,
    model_config_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous Celery task that mirrors the old generate_code_task.

    Creates a per-task AgentExecutor and EventBroadcastService so that
    no global state leaks between workers.
    """
    from utils.metrics import GENERATION_COUNT, GENERATION_DURATION, ACTIVE_GENERATIONS
    from utils.tracing import get_tracer

    ACTIVE_GENERATIONS.inc()
    start_time = time.time()
    generation_status = "completed"

    tracer = get_tracer(__name__)
    span = tracer.start_span("generate_code_as_celery_task")

    # Per-task imports
    from src.workflow_engine.config import WorkflowConfig
    from src.workflow_engine.redis_client import RedisClient
    from modules.workflow_engine.event_broadcast import (
        EventType,
        EventBroadcastService,
        WorkflowEvent,
    )
    from modules.workflow_engine.orchestrator import WorkflowOrchestrator
    from db.db_provider import db_provider as db_provider_singleton
    from src.agent_executor.main import AgentExecutor

    redis_client = RedisClient(config=WorkflowConfig())
    redis_client.connect()

    broadcast = EventBroadcastService(
        redis_client=redis_client
    )  # per-task, not shared global

    def _push_to_dlq(job_id: str, error: str) -> None:
        """Push a permanently failed job to the dead letter queue."""
        try:
            from src.workflow_engine.redis_client import QueueType

            dlq_message = {
                "job_id": job_id,
                "prompt": prompt,
                "model": model,
                "provider": provider,
                "project_id": project_id,
                "error": error,
                "retry_count": self.request.retries,
                "failed_at": datetime.now().isoformat(),
            }
            redis_client.enqueue(QueueType.DEAD_LETTER.value, dlq_message)
            logger.info(
                f"Job {job_id} pushed to DLQ after {self.request.retries} retries"
            )
        except Exception as dlq_err:
            logger.warning(f"Failed to push job {job_id} to DLQ: {dlq_err}")

    def _publish(entry: Dict[str, Any]) -> None:
        try:
            broadcast.broadcast(
                WorkflowEvent(
                    event_type=EventType.LOG_ENTRY, session_id=job_id, data=entry
                )
            )
        except Exception as e:
            logger.warning(f"Failed to publish log event: {e}")

    def _publish_status(status: str) -> None:
        pass  # Rely on Phase Transitions already in the pipeline

    # ── async pipeline (run in a new event loop) ────────────────────

    async def _run_pipeline() -> Dict[str, Any]:
        nonlocal generation_status
        nonlocal prompt
        import time as _time

        last_heartbeat = _time.time()
        HEARTBEAT_INTERVAL = 60  # seconds

        try:
            if not getattr(db_provider_singleton, "_is_initialized", False):
                await db_provider_singleton.initialize()
            from db.adapters.persistence_adapter import (
                persistence_adapter as pg_adapter,
            )

            if not pg_adapter.is_initialized:
                await pg_adapter.initialize()
            # Update job status to running
            _publish(
                _make_log_entry(
                    "generate", "running", f"Starting code generation with {model}..."
                )
            )
            _publish_status("running")

            # Send webhook notification for generation started
            if project_id:
                try:
                    from services.webhook_service import (
                        get_webhook_service,
                        WebhookEventType,
                    )

                    webhook_service = await get_webhook_service(
                        db_provider_singleton.adapter
                    )
                    await webhook_service.send_webhook(
                        WebhookEventType.GENERATION_STARTED.value,
                        {
                            "job_id": job_id,
                            "prompt": prompt,  # type: ignore[used-before-def]  # noqa: F823
                            "model": model,
                            "provider": provider,
                            "project_id": project_id,
                        },
                        user_id,
                        project_id,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to send generation started webhook: {str(e)}"
                    )

            model_config: Optional[Dict[str, Any]] = None
            if model_config_id:
                try:
                    model_config = await db_provider_singleton.adapter.get_model_config(
                        user_id, project_id, model_config_id
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get model config by ID {model_config_id}: {str(e)}"
                    )

            if not model_config and project_id:
                try:
                    configs = await db_provider_singleton.adapter.list_model_configs(
                        user_id, project_id
                    )
                    for cfg in configs:
                        if (
                            cfg.get("provider") == provider
                            and cfg.get("model_name") == model
                        ):
                            model_config = cfg
                            break
                except Exception as e:
                    logger.warning(
                        f"Failed to get model config from database: {str(e)}"
                    )

            # Normalize model_config loaded from the DB
            if model_config:
                if not model_config.get("base_url"):
                    prov = model_config.get("provider", "custom")
                    llm_provider = prov.lower() if prov else "custom"
                    base_url = os.getenv(f"{llm_provider.upper()}_API_BASE", "")
                    if not base_url:
                        if llm_provider == "lmstudio":
                            base_url = "http://127.0.0.1:1234/v1"
                        elif llm_provider == "ollama":
                            base_url = "http://localhost:1234"
                        else:
                            base_url = "http://127.0.0.1:1234/v1"
                    model_config["base_url"] = base_url

                if not model_config.get("api_key"):
                    model_config["api_key"] = "dummy"

                if not model_config.get("model_name") and model_config.get("model"):
                    model_config["model_name"] = model_config["model"]

            if not model_config:
                # Use request provider as default, detect from model name as fallback
                llm_provider = provider.lower() if provider else "custom"
                clean_model_name = model
                if "(" in model and ")" in model:
                    extracted = model.split("(")[1].split(")")[0].strip()
                    if extracted:
                        llm_provider = extracted.lower()
                        clean_model_name = model.split("(")[0].strip()
                elif "mlx" in clean_model_name.lower() or "mlx" in model.lower():
                    if llm_provider == "custom":
                        llm_provider = "lmstudio"
                elif "mistral" in model.lower():
                    if llm_provider == "custom":
                        llm_provider = "mistral"
                elif "ollama" in model.lower():
                    if llm_provider == "custom":
                        llm_provider = "ollama"

                # Determine base_url
                base_url = os.getenv(f"{llm_provider.upper()}_API_BASE", "")
                if not base_url and llm_provider == "lmstudio":
                    base_url = "http://localhost:1234/v1/chat/completions"
                elif not base_url and llm_provider == "ollama":
                    base_url = "http://localhost:1234"

                model_config = {
                    "provider": llm_provider,
                    "model_name": clean_model_name,
                    "api_key": os.getenv(f"{llm_provider.upper()}_API_KEY", "dummy")
                    or "dummy",
                    "base_url": base_url,
                    "max_tokens": 8192,
                    "temperature": 0.1,
                    "timeout": 120,
                }

            # Handle iterative prompting
            if base_job_id:
                try:
                    base_job = await db_provider_singleton.get_generation_job(
                        base_job_id
                    )
                    if (
                        base_job
                        and base_job.get("status") == "completed"
                        and base_job.get("code")
                    ):
                        base_files = base_job.get("code")
                        if not base_files:
                            raise ValueError("No code found in previous generation")
                        file_context = "\n".join(
                            [
                                f"--- {f.get('name')} ---\n{f.get('content')}"
                                for f in base_files
                                if isinstance(f, dict)
                            ]
                        )
                        original_prompt = prompt  # noqa: F823  # type: ignore[used-before-def]
                        update_prompt = (
                            f"Update the following existing infrastructure code "
                            f"based on this request: {original_prompt}\n\n"
                            f"Existing Code:\n{file_context}"
                        )
                        prompt = update_prompt
                        _publish(
                            _make_log_entry(
                                "generate",
                                "success",
                                "Loaded previous generation for iterative update",
                            )
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch base job {base_job_id} for iteration: {e}"
                    )

            # ── Generation pipeline (single path: WorkflowOrchestrator) ──
            generated_files: List[Any] = []

            # Finalizer delegates post-workflow cleanup to the Celery worker.
            # This prevents the orchestrator from doing its own finalization
            # (DB update + MinIO upload + event broadcast) which would race
            # with the Celery worker's own tracking (model_config_id update).
            async def _celery_finalizer(
                session_id: str, final_state: Dict[str, Any]
            ) -> None:
                # Built-in finalization: upload to MinIO, update DB with status,
                # broadcast session_complete event
                await orchestrator._finalize(session_id, final_state)  # type: ignore[attr-defined]
                # Celery-specific cleanup: update model_config_id
                if project_id:
                    try:
                        mc_id = model_config.get("id") if model_config else None
                        await db_provider_singleton.update_generation_job(
                            session_id, {"model_config_id": mc_id}
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to update generation job metadata: {str(e)}"
                        )

            orchestrator = WorkflowOrchestrator(
                agent_executor=AgentExecutor(),
                event_broadcast=broadcast,
                finalizer=_celery_finalizer,
            )

            # Periodic heartbeat to DB so frontend can detect stalled jobs
            async def _heartbeat_loop() -> None:
                nonlocal last_heartbeat
                try:
                    while True:
                        now = _time.time()
                        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                            await db_provider_singleton.update_generation_job(
                                job_id,
                                {
                                    "metadata": {
                                        "last_heartbeat": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                        "status": "running",
                                    }
                                },
                            )
                            last_heartbeat = now
                        await asyncio.sleep(5)
                except asyncio.CancelledError:
                    pass

            # Fetch the actual job to preserve refined_spec and skip clarify if already done
            job_record = await db_provider_singleton.get_generation_job(job_id)
            skip_clarify = False
            refined_spec = None
            if job_record:
                refined_spec = job_record.get("refined_spec")
                if refined_spec:
                    # Parse json string if needed
                    if isinstance(refined_spec, str):
                        try:
                            refined_spec = json.loads(refined_spec)
                        except Exception:
                            pass
                    skip_clarify = True

            hb_task = asyncio.create_task(_heartbeat_loop())
            try:
                result = await orchestrator.run(
                    session_id=job_id,
                    prompt=prompt,
                    build_id=job_id,
                    user_id=user_id,
                    metadata={
                        "model": model,
                        "provider": provider,
                        "project_id": project_id,
                        "model_config": model_config,
                        "skip_clarify": skip_clarify,
                        "refined_spec": refined_spec,
                    },
                )
            finally:
                hb_task.cancel()

            # Extract file metadata from orchestrator result
            # (orchestrator's finalizer already handled MinIO upload, DB status,
            #  and SESSION_COMPLETE broadcast via the finalizer callback)
            workflow_state = result.get("state", {})

            # Check if orchestrator failed internally and returned FAILED state
            from modules.workflow_engine.state_machine import SessionState

            if workflow_state.get("status") in (
                "fail",
                "failed",
                SessionState.FAILED.value,
            ):
                error_msg = (
                    workflow_state.get("error_message")
                    or workflow_state.get("error")
                    or "Workflow execution failed internally"
                )
                raise Exception(error_msg)

            if workflow_state.get("status") == SessionState.HUMAN_REVIEW.value:
                logger.info(
                    "Pipeline paused for human review (clarification questions)"
                )
                _publish(
                    _make_log_entry(
                        "generate", "running", "Waiting for human clarification..."
                    )
                )
            else:
                generated_files = workflow_state.get("generated_files", [])
                logger.info(
                    f"Code generation via WorkflowOrchestrator: "
                    f"{len(generated_files)} files"
                )
                _publish(
                    _make_log_entry(
                        "generate", "success", "Code generation completed successfully"
                    )
                )

        except Exception as e:
            error_str = str(e)
            _publish(
                _make_log_entry(
                    "generate", "error", f"Code generation failed: {error_str}"
                )
            )

            # Retry transient errors via Celery's retry mechanism
            if _is_transient_error(error_str):
                if self.request.retries < self.max_retries:
                    delay = self.request.retries * 60
                    logger.info(
                        "Transient error detected (%s), retrying in %ds "
                        "(attempt %d/%d)",
                        error_str[:100],
                        delay,
                        self.request.retries + 1,
                        self.max_retries,
                    )
                    # Update DB so frontend shows retrying state
                    await db_provider_singleton.update_generation_job(
                        job_id,
                        {
                            "status": "running",
                            "metadata": {
                                "last_heartbeat": datetime.now(
                                    timezone.utc
                                ).isoformat(),
                                "retry_count": self.request.retries,
                                "retry_delay": delay,
                            },
                        },
                    )
                    raise self.RetriableError(error_str)
                else:
                    logger.warning(
                        "Transient error but max retries exhausted (%d), "
                        "marking as permanent failure",
                        self.max_retries,
                    )

            # Permanent failure or max retries exhausted — finalise the job
            generation_status = "failed"
            logger.error(f"Code generation failed: {error_str}")
            logger.info(
                f"Attempting to persist FAILED state for job {job_id}, "
                f"initialized={getattr(db_provider_singleton, '_is_initialized', False)}"
            )
            await db_provider_singleton.update_generation_job(
                job_id, {"status": "failed"}
            )

            try:
                broadcast.broadcast(
                    WorkflowEvent(
                        event_type=EventType.SESSION_FAILED,
                        session_id=job_id,
                        data={"error": error_str, "job_id": job_id},
                    )
                )
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast generation failure: {str(ws_err)}")

            _push_to_dlq(job_id, error_str)

            if project_id:
                try:
                    from services.webhook_service import (
                        get_webhook_service,
                        WebhookEventType,
                    )

                    webhook_service = await get_webhook_service(
                        db_provider_singleton.adapter
                    )
                    await webhook_service.send_webhook(
                        WebhookEventType.GENERATION_FAILED.value,
                        {
                            "job_id": job_id,
                            "prompt": prompt,
                            "model": model,
                            "provider": provider,
                            "project_id": project_id,
                            "error": error_str,
                            "status": "failed",
                        },
                        user_id,
                        project_id,
                    )
                except Exception as webhook_error:
                    logger.warning(
                        f"Failed to send generation failed webhook: {str(webhook_error)}"
                    )

        return {"generation_status": generation_status, "files": generated_files}

    # ── Run async pipeline in a new event loop ──────────────────────
    global _worker_loop
    if "_worker_loop" not in globals() or _worker_loop is None:
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)

    try:
        result = _worker_loop.run_until_complete(_run_pipeline())
        generation_status = result.get("generation_status", "completed")
    except asyncio.TimeoutError:
        generation_status = "failed"
        _worker_loop.run_until_complete(
            db_provider_singleton.update_generation_job(job_id, {"status": "failed"})
        )
        broadcast.broadcast(
            WorkflowEvent(
                event_type=EventType.SESSION_FAILED,
                session_id=job_id,
                data={
                    "error": f"Generation timed out after {GENERATION_TIMEOUT_SECONDS}s"
                },
            )
        )
        _push_to_dlq(
            job_id, f"Generation timed out after {GENERATION_TIMEOUT_SECONDS}s"
        )
        raise
    except Exception:
        # Ensure DB is updated on failure even if event loop crashes
        try:
            _worker_loop.run_until_complete(
                db_provider_singleton.update_generation_job(
                    job_id, {"status": "failed"}
                )
            )
        except Exception:
            pass
        try:
            broadcast.broadcast(
                WorkflowEvent(
                    event_type=EventType.SESSION_FAILED,
                    session_id=job_id,
                    data={"error": "Celery worker process error during execution"},
                )
            )
        except Exception:
            pass
        _push_to_dlq(job_id, "Celery worker process error during execution")
        raise

    duration = time.time() - start_time
    GENERATION_COUNT.labels(provider=provider, status=generation_status).inc()
    GENERATION_DURATION.labels(provider=provider).observe(duration)
    ACTIVE_GENERATIONS.dec()

    span.set_attribute("status", generation_status)
    span.end()

    return {
        "status": generation_status,
        "job_id": job_id,
        "provider": provider,
    }


# ── Existing tasks ────────────────────────────────────────────────


@celery_app.task(bind=True, name="celery_worker.execute_pipeline_phase", max_retries=3)
def execute_pipeline_phase(self: Any, session_id: str, phase: str) -> Dict[str, Any]:
    """Execute a single pipeline phase as a background Celery task."""
    try:
        from models.domain.pipeline_models import PipelinePhase

        # Validate phase
        if phase not in [p.value for p in PipelinePhase]:
            raise ValueError(f"Invalid phase: {phase}")
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "status": f"Starting phase: {phase}",
            },
        )
        # Import and execute the pipeline engine for this phase
        from pipeline.pipeline_engine import AgenticPipeline
        from repositories.state_repository import StateRepository

        repo = StateRepository()
        pipeline = AgenticPipeline(state_repository=repo)
        # Load state and execute the current phase
        state = repo.load_state(session_id)
        if not state:
            raise ValueError(f"Pipeline state not found for session: {session_id}")
        # Execute just this phase
        raw_result = pipeline._execute_current_phase()
        if hasattr(raw_result, "__await__"):
            from asgiref.sync import async_to_sync

            async def _await_result() -> Any:
                return await raw_result

            result: Any = async_to_sync(_await_result)()
        else:
            result = raw_result
        self.update_state(
            state="SUCCESS" if result.get("success") else "FAILURE",
            meta={
                "current": 100,
                "total": 100,
                "status": f"Phase {phase} {'completed' if result.get('success') else 'failed'}",
                "result": result,
            },
        )
        return {"session_id": session_id, "phase": phase, "result": result}
    except self.RetriableError as exc:
        raise self.retry(
            exc=exc, countdown=self.retry_backoff * (self.request.retries + 1)
        )
    except Exception as exc:
        raise self.retry(
            exc=exc, countdown=self.retry_backoff * (self.request.retries + 1)
        )


@celery_app.task(bind=True)
def generate_infrastructure_code(
    self: Any, prompt: str, model: str, provider: str, job_id: str
) -> Dict[str, Any]:
    """
    Background task to generate infrastructure code using AI.
    Uses ai_service directly to avoid circular imports from main.py.
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Starting code generation..."},
        )
        # Use ai_service directly — no circular import from main.py
        from services.ai_service import ai_service
        from asgiref.sync import async_to_sync

        generated_files = async_to_sync(ai_service.generate_infrastructure)(
            prompt=prompt,
            provider=provider,
            model_name=model,
        )
        valid_files: List[Any] = []
        # Handle different return formats
        if isinstance(generated_files, dict):
            files = generated_files.get("files", [])
        elif isinstance(generated_files, list):
            files = generated_files
        else:
            files = []

        for f in files:
            if hasattr(f, "content") and f.content.strip():
                valid_files.append(f)
            elif isinstance(f, dict) and f.get("content", "").strip():
                valid_files.append(f)

        if not valid_files:
            raise Exception("No valid files generated")

        self.update_state(
            state="SUCCESS",
            meta={
                "current": 100,
                "total": 100,
                "status": f"Successfully generated {len(valid_files)} files",
                "files": valid_files,
            },
        )
        return {
            "status": "success",
            "files": valid_files,
            "job_id": job_id,
        }
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"current": 0, "total": 100, "status": f"Generation failed: {str(e)}"},
        )
        raise


@celery_app.task(bind=True)
def deploy_infrastructure(self: Any, job_id: str, project_name: str) -> Dict[str, Any]:
    """
    Background task to deploy infrastructure using Terraform
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Starting deployment..."},
        )

        import os
        import subprocess
        from asgiref.sync import async_to_sync

        working_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "workspace",
            "sandboxes",
            job_id,
        )
        os.makedirs(working_dir, exist_ok=True)

        async def _run_deploy_async() -> None:
            from app_factory import db_provider
            from src.sandbox_manager.container_provisioner import ContainerProvisioner

            if not getattr(db_provider, "_is_initialized", False):
                await db_provider.initialize()

            job = await db_provider.get_generation_job(job_id)
            if not job or not job.get("code"):
                raise ValueError("No generated code found for this job")

            files = job["code"]
            for f in files:
                path = (
                    f.get("path") or f.get("name")
                    if isinstance(f, dict)
                    else getattr(f, "path", getattr(f, "name", ""))
                )
                content = (
                    f.get("content")
                    if isinstance(f, dict)
                    else getattr(f, "content", "")
                )
                if path and content:
                    file_path = os.path.join(working_dir, os.path.basename(path))
                    with open(file_path, "w") as f_out:
                        f_out.write(content)

            provisioner = ContainerProvisioner()
            sandbox = await provisioner.provision_container(
                session_id=job_id, resources={"memory": "1g", "cpu": 1.0}
            )
            return sandbox.id

        sandbox_id = async_to_sync(_run_deploy_async)()

        env = os.environ.copy()
        env.update(
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_DEFAULT_REGION": "us-east-1",
                "AWS_REGION": "us-east-1",
                "AWS_ENDPOINT_URL": "http://localhost:4566",
                "AWS_ENDPOINT_URL_S3": "http://s3.localhost.localstack.cloud:4566",
            }
        )

        self.update_state(
            state="PROGRESS",
            meta={"current": 25, "total": 100, "status": "Initializing Terraform..."},
        )
        init_result = subprocess.run(
            ["terraform", "init"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if init_result.returncode != 0:
            raise Exception(f"Terraform init failed: {init_result.stderr}")

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 50,
                "total": 100,
                "status": "Planning Terraform changes...",
            },
        )
        plan_result = subprocess.run(
            ["terraform", "plan", "-out=tfplan"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if plan_result.returncode != 0:
            raise Exception(f"Terraform plan failed: {plan_result.stderr}")

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 75,
                "total": 100,
                "status": "Applying Terraform changes...",
            },
        )
        apply_result = subprocess.run(
            ["terraform", "apply", "-auto-approve", "tfplan"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if apply_result.returncode != 0:
            raise Exception(f"Terraform apply failed: {apply_result.stderr}")

        async def _stop_sandbox_async() -> None:
            from src.sandbox_manager.container_provisioner import ContainerProvisioner

            provisioner = ContainerProvisioner()
            await provisioner.stop_container(sandbox_id)

        async_to_sync(_stop_sandbox_async)()

        self.update_state(
            state="SUCCESS",
            meta={
                "current": 100,
                "total": 100,
                "status": "Deployment completed successfully!",
            },
        )
        return {
            "status": "success",
            "message": "Deployment completed successfully",
            "job_id": job_id,
        }
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"current": 0, "total": 100, "status": f"Deployment failed: {str(e)}"},
        )
        # Attempt cleanup if sandbox was created
        if "sandbox_id" in locals():
            try:
                from asgiref.sync import async_to_sync

                async def _cleanup() -> None:
                    from src.sandbox_manager.container_provisioner import (
                        ContainerProvisioner,
                    )

                    await ContainerProvisioner().stop_container(sandbox_id)

                async_to_sync(_cleanup)()
            except Exception:
                pass
        raise


@celery_app.task(name="celery_worker.push_to_github")
def push_to_github(
    self: Any, job_id: str, repo_url: str, github_token: str, description: str
) -> Dict[str, Any]:
    """Clone repo, copy generated files, commit, and push."""
    try:
        import os
        import subprocess
        import tempfile

        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Cloning repository..."},
        )

        # Get generated code from DB
        from app_factory import db_provider
        from asgiref.sync import async_to_sync

        if not getattr(db_provider, "_is_initialized", False):
            async_to_sync(db_provider.initialize)()

        job = async_to_sync(db_provider.get_generation_job)(job_id)
        if not job or not job.get("code"):
            raise ValueError("No generated code found for this job")

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = os.path.join(tmpdir, "repo")
            subprocess.run(
                ["git", "clone", f"{github_token}@{repo_url}", repo_dir],
                check=True,
                capture_output=True,
                text=True,
            )

            # Copy generated files into repo
            files = job["code"]
            for f in files:
                if isinstance(f, dict):
                    filepath = f.get("name") or f.get("path", "")
                else:
                    filepath = getattr(f, "name", getattr(f, "path", ""))
                if not filepath:
                    continue
                dest = os.path.join(repo_dir, filepath)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                # Read content from MinIO/artifact store
                try:
                    content_bytes = None
                    if isinstance(f, dict) and f.get("content"):
                        content_val = f.get("content")
                        content_bytes = (
                            content_val.encode("utf-8")
                            if isinstance(content_val, str)
                            else content_val
                        )

                    if not content_bytes:
                        from modules.artifact_store.artifact_persister import (
                            artifact_persister as persister,
                        )
                        from config.storage_config import storage_config

                        storage_path = f"sessions/{job_id}/iter_1/{filepath}"
                        content_bytes = async_to_sync(
                            persister.minio_client.download_artifact
                        )(
                            bucket_name=storage_config.MINIO_ARTIFACTS_BUCKET,
                            object_name=storage_path,
                        )

                    if content_bytes:
                        with open(dest, "wb") as fh:
                            fh.write(content_bytes)
                    else:
                        raise ValueError("No content found")
                except Exception as e:
                    logger.warning(
                        "Could not retrieve file %s from artifact store: %s",
                        filepath,
                        e,
                    )

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 60,
                    "total": 100,
                    "status": "Committing and pushing...",
                },
            )
            subprocess.run(
                ["git", "-C", repo_dir, "add", "."], check=True, capture_output=True
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    repo_dir,
                    "commit",
                    "-m",
                    description or "Auto-generated by Iacgenie",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", repo_dir, "push"], check=True, capture_output=True
            )

        self.update_state(
            state="SUCCESS",
            meta={
                "current": 100,
                "total": 100,
                "status": "Pushed to GitHub successfully!",
            },
        )
        return {"status": "success", "message": "Pushed to GitHub", "job_id": job_id}
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={
                "current": 0,
                "total": 100,
                "status": f"GitHub push failed: {str(e)}",
            },
        )
        raise


# ── Celery signal handlers for crash recovery ───────────────────────

try:
    from celery.signals import worker_shutdown, task_failure

    @worker_shutdown.connect
    def handle_worker_shutdown(sender: Any, **kwargs: Any) -> None:
        """When worker shuts down, mark all in-flight running jobs as failed."""
        try:
            from db.db_provider import db_provider as _db
            from modules.workflow_engine.event_broadcast import (
                EventType,
                EventBroadcastService,
                WorkflowEvent,
            )
            from src.workflow_engine.config import WorkflowConfig
            from src.workflow_engine.redis_client import RedisClient

            async def _mark_stale_jobs() -> None:
                if not getattr(_db, "_is_initialized", False):
                    await _db.initialize()
                jobs = (
                    await _db.list_all_running_jobs()
                    if hasattr(_db, "list_all_running_jobs")
                    else []
                )
                for job in jobs:
                    job_id = (
                        job.get("id")
                        if isinstance(job, dict)
                        else getattr(job, "id", None)
                    )
                    if not job_id:
                        continue
                    await _db.update_generation_job(
                        job_id, {"status": "failed", "error": "worker_shutdown"}
                    )
                    try:
                        rc = RedisClient(config=WorkflowConfig())
                        rc.connect()
                        bc = EventBroadcastService(redis_client=rc)
                        bc.broadcast(
                            WorkflowEvent(
                                event_type=EventType.SESSION_FAILED,
                                session_id=job_id,
                                data={"error": "Celery worker shut down unexpectedly"},
                            )
                        )
                        rc.disconnect()
                    except Exception:
                        pass

            asyncio.run(_mark_stale_jobs())
            logger.info("Marked all in-flight generation jobs as failed on shutdown")
        except Exception:
            logger.exception("Error during worker shutdown cleanup")

    @task_failure.connect
    def handle_task_failure(
        sender: Any, exception: Any, task_id: str, *args: Any, **kwargs: Any
    ) -> None:
        """When a generation task fails at Celery level, broadcast session_failed."""
        try:
            from src.workflow_engine.config import WorkflowConfig
            from src.workflow_engine.redis_client import RedisClient
            from modules.workflow_engine.event_broadcast import (
                EventType,
                EventBroadcastService,
                WorkflowEvent,
            )

            # Only handle generate_code_as_celery_task
            if "generate_code" not in str(sender.name):
                return
            # Extract job_id from args - Celery passes positional args
            job_id = args[0] if args else None
            if not job_id:
                return
            rc = RedisClient(config=WorkflowConfig())
            rc.connect()
            bc = EventBroadcastService(redis_client=rc)
            bc.broadcast(
                WorkflowEvent(
                    event_type=EventType.SESSION_FAILED,
                    session_id=job_id,
                    data={"error": f"Celery task failed: {exception}"},
                )
            )
            rc.disconnect()
            logger.info(
                f"Broadcast SESSION_FAILED for task {task_id} (job_id={job_id})"
            )
        except Exception:
            logger.exception("Error in task_failure signal handler")
except ImportError:
    # Celery signals may not be available in all environments
    pass


if __name__ == "__main__":
    celery_app.start()
