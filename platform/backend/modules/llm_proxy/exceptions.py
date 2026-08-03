"""

LLM Proxy Exceptions

Custom exception classes for LLM Proxy operations.

"""

from typing import Any, Optional


class LLMProxyError(Exception):
    """Base exception for all LLM Proxy errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        self.message = message
        self.details = kwargs
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format exception message."""
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ProviderError(LLMProxyError):
    """Exception raised for provider-related errors."""

    pass


class ProviderConnectionError(ProviderError):
    """Exception raised when provider connection fails."""

    def __init__(self, message: str, provider: Optional[str] = None) -> None:
        self.provider = provider
        super().__init__(message, provider=provider)


class ProviderRateLimitError(ProviderError):
    """Exception raised when provider rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(message, provider=provider, retry_after=retry_after)


class SecurityError(LLMProxyError):
    """Exception raised for security-related errors."""

    pass


class ValidationError(LLMProxyError):
    """Exception raised for input validation errors."""

    pass


class CacheError(LLMProxyError):
    """Exception raised for cache-related errors."""

    pass


class CircuitBreakerError(LLMProxyError):
    """Exception raised when circuit breaker is open."""

    pass


class SSRFError(SecurityError):
    """Exception raised for SSRF (Server-Side Request Forgery) attempts."""

    pass
