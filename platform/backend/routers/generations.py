import logging

from typing import List, Dict, Any, Optional

from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks

from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field

from utils.serialization import prepare_api_response
from db.db_provider import db_provider
from fastapi import Response

from middleware.auth_middleware import verify_access_token

from src.llm_proxy.service import get_llm_service
from src.llm_proxy.models import LLMRequest

from db.adapters.postgres_adapter import postgres_adapter
from models.domain.generation_metrics import GenerationMetrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generations", tags=["generations"])

# Pydantic models


class GenerationRequest(BaseModel):
    model_config = {"extra": "ignore"}

    prompt: str = Field(..., description="Infrastructure generation prompt")
    model: Optional[str] = Field(None, description="AI model to use")
    modelId: Optional[str] = Field(
        None, alias="modelId", description="AI model ID (alias for model)"
    )
    provider: str = Field(..., description="Cloud provider (aws, gcp, azure)")
    projectId: Optional[str] = Field(None, description="Project identifier")

    @property
    def resolved_model(self) -> str:
        """Return the effective model name from either model or modelId field."""
        if self.model:
            return self.model
        if self.modelId:
            return self.modelId
        raise ValueError("Either 'model' or 'modelId' must be provided")


class GenerationResponse(BaseModel):
    id: str
    userId: str
    projectId: str
    prompt: str
    model: str
    provider: str
    status: str
    jobId: str
    files: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]
    createdAt: str
    updatedAt: str


class GenerationListResponse(BaseModel):
    generations: List[GenerationResponse]
    total: int


# Service layer


class GenerationService:
    @staticmethod
    def _map_to_ui(gen_data: dict) -> dict:
        if not gen_data:
            return {}
        meta = gen_data.get("metadata") or {}
        return {
            "id": gen_data.get("id"),
            "userId": gen_data.get("user_id"),
            "projectId": gen_data.get("project_id"),
            "prompt": gen_data.get("prompt"),
            "model": gen_data.get("model"),
            "provider": meta.get("provider", ""),
            "status": gen_data.get("status"),
            "jobId": meta.get("jobId", ""),
            "files": meta.get("files", []),
            "logs": meta.get("logs", []),
            "createdAt": gen_data.get("created_at"),
            "updatedAt": meta.get("updatedAt", gen_data.get("created_at")),
            "tokensUsed": gen_data.get("tokens_used"),
            "durationMs": gen_data.get("duration_ms"),
        }

    @staticmethod
    async def list_generations(uid: str, project_id: str) -> list:
        db_gens = await db_provider.list_generations(uid, project_id)
        return [GenerationService._map_to_ui(g) for g in db_gens]

    @staticmethod
    async def create_generation(uid: str, project_id: str, gen_data: dict) -> dict:
        now = datetime.now().isoformat()
        metadata = {
            "provider": gen_data.get("provider"),
            "jobId": gen_data.get("jobId", ""),
            "files": gen_data.get("files", []),
            "logs": gen_data.get("logs", []),
            "updatedAt": now,
        }
        db_input = {
            "prompt": gen_data["prompt"],
            "model": gen_data["model"],
            "status": "pending",
            "metadata": metadata,
        }
        gen_id = await db_provider.create_generation(uid, project_id, db_input)
        if not gen_id:
            raise Exception("Failed to create generation in DB")
        db_gen = await db_provider.get_generation(uid, project_id, gen_id)
        return GenerationService._map_to_ui(db_gen or {})

    @staticmethod
    async def update_generation(
        uid: str, project_id: str, gen_id: str, gen_data: dict
    ) -> dict:
        now = datetime.now().isoformat()
        existing = await db_provider.get_generation(uid, project_id, gen_id)
        if not existing:
            raise ValueError("Generation not found")
        if existing.get("user_id") != uid:
            raise ValueError("Unauthorized access to generation")

        meta = existing.get("metadata") or {}
        if "files" in gen_data:
            meta["files"] = gen_data["files"]
        if "logs" in gen_data:
            meta["logs"] = gen_data["logs"]
        meta["updatedAt"] = now

        db_update = {"metadata": meta}
        if "status" in gen_data:
            db_update["status"] = gen_data["status"]
        if "modelUsed" in gen_data:
            meta["modelUsed"] = gen_data["modelUsed"]
        if "totalCost" in gen_data:
            meta["totalCost"] = gen_data["totalCost"]
        if "promptTokens" in gen_data:
            meta["promptTokens"] = gen_data["promptTokens"]
        if "completionTokens" in gen_data:
            meta["completionTokens"] = gen_data["completionTokens"]
        if "totalTokens" in gen_data:
            db_update["tokens_used"] = gen_data["totalTokens"]
            meta["totalTokens"] = gen_data["totalTokens"]
        if "cached" in gen_data:
            meta["cached"] = gen_data["cached"]
        if "failoverFrom" in gen_data:
            meta["failoverFrom"] = gen_data["failoverFrom"]
        if "failoverTo" in gen_data:
            meta["failoverTo"] = gen_data["failoverTo"]

        await db_provider.update_generation(uid, project_id, gen_id, db_update)
        updated = await db_provider.get_generation(uid, project_id, gen_id)
        return GenerationService._map_to_ui(updated or {})

    @staticmethod
    async def delete_generation(uid: str, project_id: str, gen_id: str) -> dict:
        existing = await db_provider.get_generation(uid, project_id, gen_id)
        if not existing:
            raise ValueError("Generation not found")
        if existing.get("user_id") != uid:
            raise ValueError("Unauthorized access to generation")
        success = await db_provider.delete_generation(uid, project_id, gen_id)
        if not success:
            raise Exception("Failed to delete generation")
        return {
            "success": True,
            "message": "Generation deleted successfully",
            "gen_id": gen_id,
        }


# Initialize service


generation_service = GenerationService()


async def record_generation_metrics_bg(
    project_id: str, uid: str, gen_id: str, requested_model: str, completion: Any
) -> None:
    """Background task to insert telemetry into Postgres without blocking."""
    try:
        from sqlalchemy import insert

        if not postgres_adapter._is_initialized:
            return
        metrics_data = {
            "project_id": project_id,
            "tenant_id": uid,
            "generation_id": gen_id,
            "requested_model": requested_model,
            "model_used": completion.model_used,
            "provider": getattr(completion, "provider", "unknown"),
            "prompt_tokens": completion.prompt_tokens,
            "completion_tokens": completion.completion_tokens,
            "total_tokens": completion.total_tokens,
            "total_cost": completion.total_cost,
            "latency_ms": getattr(completion, "latency_ms", 0.0),
            "is_cached": getattr(completion, "cached", False),
            "failover_occurred": bool(completion.failover_from),
            "failover_from": completion.failover_from,
        }
        async with postgres_adapter.async_session_factory() as session:  # type: ignore[misc]
            stmt = insert(GenerationMetrics).values(**metrics_data)
            await session.execute(stmt)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to record generation metrics to Postgres: {str(e)}")


# API Endpoints


@router.get("/{project_id}", response_model=GenerationListResponse)
async def list_generations(
    project_id: str, response: Response, user: Any = Depends(verify_access_token)
) -> Any:
    response.headers["X-Deprecation"] = "true"
    response.headers["X-Deprecation-URL"] = "/api/pipeline/runs"
    """List all generations for a project"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        # Get generations from database
        generations_data = await generation_service.list_generations(uid, project_id)
        # Convert to Pydantic models
        generations = []
        for gen_data in generations_data:
            generations.append(GenerationResponse(**gen_data))
        resp_body = GenerationListResponse(
            generations=generations, total=len(generations)
        )
        return resp_body
    except Exception as e:
        logger.error(f"Failed to list generations: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to list generations: {str(e)}",
            },
        )


@router.post("/{project_id}")
async def create_generation(
    project_id: str,
    gen: GenerationRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    user: Any = Depends(verify_access_token),
) -> Any:
    response.headers["X-Deprecation"] = "true"
    response.headers["X-Deprecation-URL"] = "/api/pipeline/runs"
    """Create a new generation record with LLM proxy integration."""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )

        # 1. Create the generation record (status: pending)
        gen_dict = {
            "prompt": gen.prompt,
            "model": gen.resolved_model,
            "provider": gen.provider,
        }
        result = await generation_service.create_generation(uid, project_id, gen_dict)

        # 2. Call LLM proxy to get gateway metadata (model_used, cost, failover, tokens)
        llm_service = get_llm_service()
        llm_request = LLMRequest(
            model=gen.resolved_model,
            prompt=gen.prompt,
            messages=None,
            temperature=0.7,
            max_tokens=2000,
            top_p=None,
            frequency_penalty=None,
            presence_penalty=None,
            stop=None,
            stream=False,
            session_id=None,
            build_id=None,
            metadata=None,
        )

        try:
            completion = await llm_service.generate_completion(
                request=llm_request,
                tenant_id=uid,
                cache_enabled=True,
                rate_limit_enabled=True,
            )

            # 3. Update the generation record with LLM proxy metadata
            gateway_data = {
                "status": "completed",
                "files": [
                    {
                        "name": f"generation_{result.get('id', '')}",
                        "language": "text",
                        "content": completion.response.choices[0].text
                        if completion.response.choices
                        else "",
                    }
                ],
                "logs": [
                    {
                        "stage": "llm_proxy",
                        "status": "success",
                        "message": f"Completed via {completion.model_used}",
                        "timestamp": datetime.now().isoformat(),
                    }
                ],
                "modelUsed": completion.model_used,
                "totalCost": completion.total_cost,
                "promptTokens": completion.prompt_tokens,
                "completionTokens": completion.completion_tokens,
                "totalTokens": completion.total_tokens,
                "cached": completion.cached,
                "failoverFrom": completion.failover_from,
                "failoverTo": completion.failover_to,
            }
            result = await generation_service.update_generation(
                uid, project_id, result["id"], gateway_data
            )

            # Fire off background telemetry to Postgres
            background_tasks.add_task(
                record_generation_metrics_bg,
                project_id,
                uid,
                result["id"],
                gen.resolved_model,
                completion,
            )

            logger.info(
                "Generation created with LLM proxy",
                extra={
                    "gen_id": result.get("id"),
                    "project_id": project_id,
                    "requested_model": gen.resolved_model,
                    "model_used": completion.model_used,
                    "total_cost": completion.total_cost,
                    "cached": completion.cached,
                    "failover_from": completion.failover_from,
                    "failover_to": completion.failover_to,
                    "latency_ms": round(completion.latency_ms, 2),
                },
            )
        except Exception as llm_err:
            # LLM proxy failure is non-fatal — keep the generation record
            logger.warning(
                "LLM proxy call failed for generation, record kept with pending status",
                extra={"gen_id": result.get("id"), "error": str(llm_err)},
            )
            # Update status to failed
            try:
                await generation_service.update_generation(
                    uid,
                    project_id,
                    result["id"],
                    {
                        "status": "failed",
                        "logs": [
                            {
                                "stage": "llm_proxy",
                                "status": "error",
                                "message": f"LLM proxy failed: {str(llm_err)}",
                                "timestamp": datetime.now().isoformat(),
                            }
                        ],
                    },
                )
            except Exception:
                pass

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
        logger.error(f"Failed to create generation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to create generation: {str(e)}",
            },
        )


@router.put("/{project_id}/{gen_id}")
async def update_generation(
    project_id: str,
    gen_id: str,
    gen: GenerationRequest,
    user: Any = Depends(verify_access_token),
) -> Any:
    """Update an existing generation record"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        # Update the generation record
        result = await generation_service.update_generation(
            uid, project_id, gen_id, gen.dict()
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
        logger.error(f"Failed to update generation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to update generation: {str(e)}",
            },
        )


@router.delete("/{project_id}/{gen_id}")
async def delete_generation(
    project_id: str, gen_id: str, user: Any = Depends(verify_access_token)
) -> Any:
    """Delete a generation record"""
    try:
        uid = user.get("uid")
        if not uid:
            logger.error("Invalid user token: UID missing")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )
        # Delete the generation record
        result = await generation_service.delete_generation(uid, project_id, gen_id)
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
        logger.error(f"Failed to delete generation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Failed to delete generation: {str(e)}",
            },
        )
