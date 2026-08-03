"""

LLM Proxy Configuration

Configuration settings for the LLM proxy including provider settings,

rate limiting, caching, and security parameters.

"""

from pydantic_settings import SettingsConfigDict, BaseSettings

from typing import Optional, List, Dict


class LLMConfig(BaseSettings):
    """Configuration for LLM proxy service."""

    # Provider Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_BASE_URL: str = "https://api.mistral.ai/v1"
    MISTRAL_MODEL: str = "mistral-large-latest"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL: str = "gemini-1.5-pro"
    # Custom Provider Configuration
    CUSTOM_PROVIDERS: Dict[str, str] = {}  # name -> config JSON
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 1000
    RATE_LIMIT_BURST: int = 10
    # Caching
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    CACHE_MAX_SIZE: int = 1000
    # Security
    SSRF_BLOCKLIST: List[str] = [
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
        "169.254.169.254",  # Azure metadata
        "10.0.0.0/8",  # Private networks
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.1",
        "localhost",
    ]
    MAX_PROMPT_LENGTH: int = 100000
    MAX_RESPONSE_LENGTH: int = 10000
    MAX_TOKENS: int = 8192
    # Timeout
    REQUEST_TIMEOUT: int = 120  # seconds
    CONNECT_TIMEOUT: int = 30
    # Circuit Breaker
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60  # seconds
    # Observability
    ENABLE_TRACING: bool = True
    ENABLE_METRICS: bool = True
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="LLM_", case_sensitive=True, extra="ignore"
    )


# Global configuration instance


llm_config = LLMConfig()
