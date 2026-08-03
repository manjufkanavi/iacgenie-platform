"""

LLM Proxy Service

Provides unified interface for multiple AI model providers with routing,

caching, and rate limiting.

CRITICAL FIX: Fixed recursive call bug in get_llm_service() function.

The function now uses a proper singleton pattern instead of calling itself.

"""

import time

import logging

from typing import Any, Dict, Optional

from dataclasses import dataclass

from config.llm_config import llm_config

from .models import LLMRequest, LLMResponse, Usage, Choice

from .exceptions import (
    ProviderError,
    ProviderRateLimitError,
    ValidationError,
    CircuitBreakerError,
    SSRFError,
)

logger = logging.getLogger(__name__)


@dataclass
class CompletionResult:
    """Result of a completion request."""

    response: LLMResponse
    cached: bool = False
    provider: str = ""
    duration_ms: float = 0.0


class LLMService:
    """
    LLM Proxy service for multi-provider AI model access.
    Features:
    - Provider routing and load balancing
    - Request caching
    - Rate limiting per provider
    - Security validation (SSRF prevention)
    - Circuit breaker pattern
    """

    def __init__(self) -> None:
        self._providers: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._initialize_providers()
        logger.info("LLM Service initialized")

    def _initialize_providers(self) -> None:
        """Initialize all configured providers."""
        # Import existing AI service from backend
        try:
            from services.ai_service import AIService

            self._existing_ai_service = AIService()
            logger.info("Using existing AI service for providers")
        except ImportError:
            logger.warning(
                "Existing AI service not available, using standalone providers"
            )
            self._existing_ai_service = None  # type: ignore[assignment]

    async def generate_completion(
        self,
        request: LLMRequest,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        build_id: Optional[str] = None,
    ) -> CompletionResult:
        """
        Generate a completion using the configured provider.
        Args:
            request: LLM request
            tenant_id: Optional tenant ID for rate limiting
            session_id: Optional session ID for tracing
            build_id: Optional build ID for tracing
        Returns:
            CompletionResult with response and metadata
        Raises:
            ProviderError: If provider fails
            ProviderRateLimitError: If rate limit exceeded
            SecurityError: If request violates security rules
        """
        start_time = time.time()
        # Validate request
        self._validate_request(request)
        # Check cache
        cache_key = self._get_cache_key(request)
        if cache_key in self._cache:
            logger.info(f"Cache hit for key: {cache_key}")
            return CompletionResult(
                response=self._cache[cache_key],
                cached=True,
                provider="cache",
                duration_ms=(time.time() - start_time) * 1000,
            )
        # Check rate limit
        if tenant_id and not self._check_rate_limit(tenant_id):
            raise ProviderRateLimitError(
                f"Rate limit exceeded for tenant {tenant_id}",
                provider="rate_limit",
                retry_after=self._get_retry_after(tenant_id),
            )
        # Check circuit breaker
        provider = request.get_provider()
        if not self._check_circuit_breaker(provider):
            raise CircuitBreakerError(
                f"Circuit breaker open for provider {provider}", provider=provider
            )
        # Generate completion
        try:
            # Use existing AI service if available
            if self._existing_ai_service:
                response = await self._generate_with_existing_service(
                    request, tenant_id, session_id, build_id
                )
            else:
                response = await self._generate_with_standalone_provider(
                    request, provider
                )
            duration_ms = (time.time() - start_time) * 1000
            # Cache response
            self._cache[cache_key] = response
            # Update rate limit
            if tenant_id:
                self._update_rate_limit(tenant_id)
            # Reset circuit breaker
            self._reset_circuit_breaker(provider)
            return CompletionResult(
                response=response,
                cached=False,
                provider=provider,
                duration_ms=duration_ms,
            )
        except ProviderRateLimitError:
            # Update circuit breaker on rate limit
            self._trigger_circuit_breaker(provider)
            raise
        except Exception as e:
            # Trigger circuit breaker on error
            self._trigger_circuit_breaker(provider)
            raise ProviderError(
                f"Provider {provider} failed: {str(e)}", provider=provider
            ) from e

    async def _generate_with_existing_service(
        self,
        request: LLMRequest,
        tenant_id: Optional[str],
        session_id: Optional[str],
        build_id: Optional[str],
    ) -> LLMResponse:
        """Generate completion using existing AI service."""
        # Map request to existing AI service format
        # This integrates with the existing backend's AI service
        # For now, return a mock response
        return LLMResponse(
            id=f"cmpl-{int(time.time())}",
            object="text_completion",
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    text="Generated infrastructure code...",
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=100, completion_tokens=500, total_tokens=600),
            error=None,
            metadata=None,
        )

    async def _generate_with_standalone_provider(
        self, request: LLMRequest, provider: str
    ) -> LLMResponse:
        """Generate completion using standalone provider implementation."""
        # Placeholder for standalone provider implementation
        # In production, this would call the actual provider API
        return LLMResponse(
            id=f"cmpl-{int(time.time())}",
            object="text_completion",
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    text=f"Generated code using {provider} provider...",
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=100, completion_tokens=500, total_tokens=600),
            error=None,
            metadata=None,
        )

    def _validate_request(self, request: LLMRequest) -> None:
        """Validate request parameters."""
        # Check SSRF
        if request.metadata and "url" in request.metadata:
            url = request.metadata["url"]
            for blocked in llm_config.SSRF_BLOCKLIST:
                if blocked in url:
                    raise SSRFError(
                        f"Blocked URL detected: {url}",
                        details={"url": url, "blocked_pattern": blocked},
                    )
        # Validate model
        if not request.model or not request.model.strip():
            raise ValidationError("Model cannot be empty")
        # Validate temperature
        if request.temperature is not None and (
            request.temperature < 0.0 or request.temperature > 2.0
        ):
            raise ValidationError("Temperature must be between 0.0 and 2.0")
        # Validate max_tokens
        if request.max_tokens is not None and (
            request.max_tokens < 1 or request.max_tokens > 32000
        ):
            raise ValidationError("Max tokens must be between 1 and 32000")

    def _get_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request."""
        # Simple cache key based on model and prompt/messages
        if request.messages:
            content = str([m.dict() for m in request.messages])
        else:
            content = request.prompt or ""
        return f"{request.model}:{hash(content)}"

    def _check_rate_limit(self, tenant_id: str) -> bool:
        """Check if tenant has exceeded rate limit."""
        if tenant_id not in self._rate_limits:
            self._rate_limits[tenant_id] = {
                "requests": 0,
                "reset_at": time.time()
                + llm_config.RATE_LIMIT_REQUESTS_PER_MINUTE * 60,
            }
        limits = self._rate_limits[tenant_id]
        if time.time() > limits["reset_at"]:
            # Reset limits
            limits["requests"] = 0
            limits["reset_at"] = (
                time.time() + llm_config.RATE_LIMIT_REQUESTS_PER_MINUTE * 60
            )
        return limits["requests"] < llm_config.RATE_LIMIT_REQUESTS_PER_MINUTE

    def _update_rate_limit(self, tenant_id: str) -> None:
        """Update rate limit counter for tenant."""
        if tenant_id in self._rate_limits:
            self._rate_limits[tenant_id]["requests"] += 1

    def _get_retry_after(self, tenant_id: str) -> int:
        """Get seconds until rate limit resets."""
        if tenant_id in self._rate_limits:
            return int(self._rate_limits[tenant_id]["reset_at"] - time.time())
        return 60

    def _check_circuit_breaker(self, provider: str) -> bool:
        """Check if circuit breaker is open for provider."""
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = {
                "failures": 0,
                "last_failure": None,
                "open": False,
            }
        breaker = self._circuit_breakers[provider]
        if breaker["open"]:
            return False
        # Check if we should open the breaker
        failures_over = (
            breaker["failures"] >= llm_config.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        )
        last_fail = breaker["last_failure"]
        time_ok = last_fail and (
            time.time() - last_fail < llm_config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
        )
        if failures_over and time_ok:
            return True
        return False

    def _trigger_circuit_breaker(self, provider: str) -> None:
        """Trigger circuit breaker for provider."""
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = {
                "failures": 0,
                "last_failure": None,
                "open": False,
            }
        self._circuit_breakers[provider]["failures"] += 1
        self._circuit_breakers[provider]["last_failure"] = time.time()
        if (
            self._circuit_breakers[provider]["failures"]
            >= llm_config.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        ):
            self._circuit_breakers[provider]["open"] = True
            logger.warning(f"Circuit breaker opened for provider {provider}")

    def _reset_circuit_breaker(self, provider: str) -> None:
        """Reset circuit breaker for provider."""
        if provider in self._circuit_breakers:
            self._circuit_breakers[provider]["failures"] = 0
            self._circuit_breakers[provider]["open"] = False
            logger.info(f"Circuit breaker reset for provider {provider}")

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
        logger.info("Cache cleared")


# Global service instance (singleton pattern)


_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get the global LLM service instance.
    CRITICAL FIX: This function now uses a proper singleton pattern
    instead of calling itself recursively.
    Returns:
        LLMService instance
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance


def set_llm_service(service: LLMService) -> None:
    """
    Set the global LLM service instance.
    Use this for testing or dependency injection.
    Args:
        service: LLMService instance to set as global
    """
    global _llm_service_instance
    _llm_service_instance = service
