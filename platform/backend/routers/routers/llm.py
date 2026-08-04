"""
LLM Proxy Router

API endpoints for LLM proxy operations.
Uses LiteLLM Router for unified LLM routing with fallback chains.
"""

import logging
import time

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request

from pydantic import BaseModel, Field

from modules.llm_proxy.service import LLMService, CompletionResult, get_llm_service
from modules.llm_proxy.models import LLMRequest, LLMMessage
from modules.llm_proxy.exceptions import (
    ProviderError,
    ProviderRateLimitError,
    SecurityError,
    ValidationError as LLMValidationError,
)
from middleware.auth_middleware import get_user_id
from middleware.rate_limiting import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM Proxy"])

rate_limiter = RateLimiter()

# Global LLM service instance (singleton)

_llm_service: Optional[LLMService] = None


def get_llm_service_instance() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = get_llm_service()
    return _llm_service


# ============================================================================
# Request Models
# ============================================================================


class CompletionRequest(BaseModel):
    """Request for LLM completion."""

    model: str = Field(..., description="Model name")
    prompt: Optional[str] = Field(None, description="Prompt text")
    messages: Optional[List[Dict[str, str]]] = Field(None, description="Messages list")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Temperature")
    max_tokens: Optional[int] = Field(2000, ge=1, le=20000, description="Max tokens")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Top P")
    frequency_penalty: Optional[float] = Field(
        0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    stream: Optional[bool] = Field(False, description="Stream responses")
    session_id: Optional[str] = Field(None, description="Session ID for tracing")
    build_id: Optional[str] = Field(None, description="Build ID for tracing")


class ModelsRequest(BaseModel):
    """Request to list available models."""

    provider: Optional[str] = Field(None, description="Filter by provider")


class ChatCompletionRequest(BaseModel):
    """Request for chat completion."""

    model: str = Field(..., description="Model name")
    messages: List[Dict[str, str]] = Field(..., description="Messages list")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Temperature")
    max_tokens: Optional[int] = Field(2000, ge=1, le=20000, description="Max tokens")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Top P")
    frequency_penalty: Optional[float] = Field(
        0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    stream: Optional[bool] = Field(False, description="Stream responses")
    session_id: Optional[str] = Field(None, description="Session ID for tracing")
    build_id: Optional[str] = Field(None, description="Build ID for tracing")


# ============================================================================
# Response Models
# ============================================================================


class CompletionResponse(BaseModel):
    """Response for LLM completion."""

    id: str = Field(..., description="Completion ID")
    object: str = Field("text_completion", description="Object type")
    created: int = Field(..., description="Timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Dict[str, Any]] = Field(..., description="Generated choices")
    usage: Dict[str, int] = Field(..., description="Token usage")
    model_used: str = Field(..., description="Actual model used by LiteLLM Router")
    total_cost: float = Field(0.0, description="Estimated cost in USD")
    cached: bool = Field(False, description="Whether response was served from cache")


class ChatCompletionResponse(BaseModel):
    """Response for chat completion."""

    id: str = Field(..., description="Completion ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Dict[str, Any]] = Field(..., description="Generated choices")
    usage: Dict[str, int] = Field(..., description="Token usage")
    model_used: str = Field(..., description="Actual model used by LiteLLM Router")
    total_cost: float = Field(0.0, description="Estimated cost in USD")
    cached: bool = Field(False, description="Whether response was served from cache")


class ModelInfo(BaseModel):
    """Information about an available model."""

    id: str = Field(..., description="Model ID")
    object: str = Field("model", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    owned_by: str = Field(..., description="Provider")
    context_length: Optional[int] = Field(None, description="Max context tokens")
    fallback_group: Optional[str] = Field(None, description="LiteLLM fallback group")


class ModelsResponse(BaseModel):
    """Response for available models."""

    object: str = Field("list", description="Object type")
    data: List[ModelInfo] = Field(..., description="Available models")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: Dict[str, Any] = Field(..., description="Error details")


# ============================================================================
# Helper: Convert request to LLMRequest
# ============================================================================


def _to_llm_request(
    model: str,
    prompt: Optional[str],
    messages: Optional[List[Dict[str, str]]],
    temperature: Optional[float],
    max_tokens: Optional[int],
    top_p: Optional[float],
    frequency_penalty: Optional[float],
    presence_penalty: Optional[float],
    stop: Optional[List[str]],
    session_id: Optional[str],
    build_id: Optional[str],
) -> LLMRequest:
    """Convert API request to internal LLMRequest format."""
    llm_messages = None
    if messages:
        llm_messages = [
            LLMMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in messages
        ]
    return LLMRequest(
        model=model,
        prompt=prompt,
        messages=llm_messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stop=stop,
        stream=False,
        session_id=session_id,
        build_id=build_id,
        metadata=None,
    )


def _build_usage_dict(result: CompletionResult) -> Dict[str, int]:
    """Build usage dict from CompletionResult."""
    return {
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
    }


def _build_response_data(result: CompletionResult, object_type: str) -> Dict[str, Any]:
    """Build response dict from CompletionResult."""
    choices = [c.model_dump() for c in result.response.choices]
    usage = _build_usage_dict(result)
    return {
        "id": result.response.id,
        "object": object_type,
        "created": result.response.created,
        "model": result.response.model,
        "choices": choices,
        "usage": usage,
        "model_used": result.model_used,
        "total_cost": result.total_cost,
        "cached": result.cached,
    }


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    http_request: Request,
    user_id: str = Depends(get_user_id),
) -> CompletionResponse:
    """
    Generate a completion using LiteLLM Router.
    Automatically routes to lowest-latency model and handles failover.
    """
    try:
        rate_limiter.check_rate_limit(http_request, endpoint="llm/completions")
        llm_service = get_llm_service_instance()
        llm_request = _to_llm_request(
            model=request.model,
            prompt=request.prompt,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stop=request.stop,
            session_id=request.session_id,
            build_id=request.build_id,
        )
        result = await llm_service.generate_completion(
            request=llm_request,
            tenant_id=user_id,
            session_id=request.session_id,
            build_id=request.build_id,
        )
        response_data = _build_response_data(result, "text_completion")
        response = CompletionResponse(**response_data)

        logger.info(
            "LLM completion generated",
            extra={
                "user_id": user_id,
                "requested_model": request.model,
                "model_used": result.model_used,
                "cached": result.cached,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_cost": result.total_cost,
                "latency_ms": round(result.latency_ms, 2),
                "session_id": request.session_id,
            },
        )
        return response

    except ProviderRateLimitError as e:
        logger.warning(f"Rate limit exceeded for user {user_id}: {e}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                }
            },
        )
    except SecurityError as e:
        logger.error(f"Security error for user {user_id}: {e}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": str(e),
                    "type": "security_error",
                    "code": "security_violation",
                }
            },
        )
    except LLMValidationError as e:
        logger.warning(f"Validation error for user {user_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": str(e),
                    "type": "validation_error",
                    "code": "invalid_request",
                }
            },
        )
    except ProviderError as e:
        logger.error(f"LLM provider error for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "provider_error",
                    "code": "internal_error",
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in completion for user {user_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    user_id: str = Depends(get_user_id),
) -> ChatCompletionResponse:
    """
    Generate a chat completion using LiteLLM Router.
    Supports multi-turn conversations with automatic model routing.
    """
    try:
        rate_limiter.check_rate_limit(http_request, endpoint="llm/chat/completions")
        llm_service = get_llm_service_instance()
        llm_request = _to_llm_request(
            model=request.model,
            prompt=None,
            messages=[dict(m) for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stop=request.stop,
            session_id=request.session_id,
            build_id=request.build_id,
        )
        result = await llm_service.generate_completion(
            request=llm_request,
            tenant_id=user_id,
            session_id=request.session_id,
            build_id=request.build_id,
        )
        response_data = _build_response_data(result, "chat.completion")
        response = ChatCompletionResponse(**response_data)

        logger.info(
            "LLM chat completion generated",
            extra={
                "user_id": user_id,
                "requested_model": request.model,
                "model_used": result.model_used,
                "cached": result.cached,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_cost": result.total_cost,
                "latency_ms": round(result.latency_ms, 2),
                "session_id": request.session_id,
            },
        )
        return response

    except ProviderRateLimitError as e:
        logger.warning(f"Rate limit exceeded for user {user_id}: {e}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                }
            },
        )
    except SecurityError as e:
        logger.error(f"Security error for user {user_id}: {e}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": str(e),
                    "type": "security_error",
                    "code": "security_violation",
                }
            },
        )
    except LLMValidationError as e:
        logger.warning(f"Validation error for user {user_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": str(e),
                    "type": "validation_error",
                    "code": "invalid_request",
                }
            },
        )
    except ProviderError as e:
        logger.error(f"LLM provider error for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "provider_error",
                    "code": "internal_error",
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in chat completion for user {user_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    provider: Optional[str] = None,
    user_id: str = Depends(get_user_id),
) -> ModelsResponse:
    """
    List available LLM models from LiteLLM Router.
    """
    try:
        llm_service = get_llm_service_instance()
        router_engine = llm_service.router

        # Read model list from LiteLLM Router config
        model_list = getattr(router_engine, "model_list", [])

        models: List[ModelInfo] = []
        for model_info in model_list:
            model_name = getattr(model_info, "model_name", None) or getattr(
                model_info, "model", None
            )
            if not model_name:
                continue
            if provider:
                litellm_params = getattr(model_info, "litellm_params", {})
                provider_prefix = str(litellm_params.get("model", "")).split("/")[0]
                if provider_prefix != provider:
                    continue
            models.append(
                ModelInfo(
                    id=model_name,
                    object="model",
                    created=int(time.time()),
                    owned_by=provider or "unknown",
                    context_length=None,
                    fallback_group=None,
                )
            )

        logger.info(
            "Listed available models",
            extra={
                "user_id": user_id,
                "provider": provider,
                "count": len(models),
            },
        )
        return ModelsResponse(object="list", data=models)

    except Exception as e:
        logger.error(f"Error listing models for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for LLM proxy service.
    Checks LiteLLM Router status and downstream provider health.
    """
    try:
        llm_service = get_llm_service_instance()
        router_engine = llm_service.router

        model_count = 0
        healthy_models = 0
        model_list = getattr(router_engine, "model_list", [])
        for m in model_list:
            model_count += 1
            health = getattr(m, "health", None)
            if health is not False:
                healthy_models += 1

        return {
            "status": "healthy",
            "service": "llm_proxy",
            "router_type": "litellm.Router",
            "models_configured": model_count,
            "models_healthy": healthy_models,
            "cache_enabled": True,
            "rate_limiting_enabled": True,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "llm_proxy",
            "error": str(e),
        }
