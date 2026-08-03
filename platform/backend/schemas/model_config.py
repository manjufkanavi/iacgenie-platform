"""

Pydantic models for model configuration API

"""

from pydantic import BaseModel, Field

from typing import Dict, Any, Optional

from datetime import datetime

import re


class ModelConfigRequest(BaseModel):
    """Request model for saving/updating model configuration"""

    provider: str = Field(
        ..., description="AI provider (Mistral, Google, OpenAI, Anthropic, etc.)"
    )
    model_name: str = Field(..., description="Model name/identifier")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key for the model")
    max_tokens: int = Field(8192, description="Maximum tokens for generation")
    temperature: float = Field(
        0.1, ge=0.0, le=2.0, description="Temperature for generation"
    )
    timeout: int = Field(120, description="Request timeout in seconds")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Additional headers"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def validate_provider(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Provider cannot be empty")
        # Normalize provider name (case-insensitive)
        normalized = v.strip().lower()
        # Map common provider names to standardized ones
        provider_mapping = {
            "mistral": "mistral",
            "google": "gemini",
            "gemini": "gemini",
            "openai": "openai",
            "gpt": "openai",
            "anthropic": "claude",
            "claude": "claude",
            "meta": "llama",
            "llama": "llama",
            "cohere": "cohere",
            "custom": "custom",
            "groq": "groq",
            "deepseek": "deepseek",
            "xai": "xai",
            "perplexity": "perplexity",
            "azure-openai": "azure-openai",
            "aws-bedrock": "aws-bedrock",
            "fireworks": "fireworks",
            "together": "together",
            "openrouter": "openrouter",
            "ollama": "ollama",
            "lmstudio": "lmstudio",
        }
        if normalized in provider_mapping:
            return provider_mapping[normalized]
        # If not in mapping, allow it but warn
        return v.strip()

    def validate_api_key(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("API key cannot be empty")
        # Basic API key format validation
        key = v.strip()
        if len(key) < 10:
            raise ValueError("API key appears to be too short")
        # Check for common API key prefixes
        valid_prefixes = [
            "sk-",
            "sk_proj_",
            "gsk_",
            "claude-",
            "mistral-",
            "cohere-",
            "pplx-",
            "fw-",
            "sk-or-",
            "AIza",
        ]
        if not any(key.startswith(prefix) for prefix in valid_prefixes):
            # Allow other formats but warn
            pass
        return key

    def validate_base_url(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Base URL cannot be empty")
        url = v.strip()
        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        # Check for valid URL structure
        try:
            # Basic URL structure check
            if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", url):
                raise ValueError("Invalid URL format")
        except Exception:
            raise ValueError("Invalid URL format")
        return url

    def validate_model_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Model name cannot be empty")
        model = v.strip()
        # Basic model name validation
        if len(model) < 2:
            raise ValueError("Model name is too short")
        # Check for invalid characters
        if re.search(r'[<>:"/\\|?*]', model):
            raise ValueError("Model name contains invalid characters")
        return model

    def validate_max_tokens(cls, v):
        if v < 1:
            raise ValueError("Max tokens must be at least 1")
        if v > 100000:
            raise ValueError("Max tokens cannot exceed 100,000")
        return v

    def validate_temperature(cls, v):
        if v < 0.0 or v > 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    def validate_timeout(cls, v):
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        if v > 600:
            raise ValueError("Timeout cannot exceed 600 seconds")
        return v

    def validate_retry_attempts(cls, v):
        if v < 0:
            raise ValueError("Retry attempts cannot be negative")
        if v > 10:
            raise ValueError("Retry attempts cannot exceed 10")
        return v

    def validate_retry_delay(cls, v):
        if v < 0.0:
            raise ValueError("Retry delay cannot be negative")
        if v > 60.0:
            raise ValueError("Retry delay cannot exceed 60 seconds")
        return v


class ModelConfigResponse(BaseModel):
    """Response model for model configuration"""

    provider: str
    model_name: str
    base_url: str
    max_tokens: int
    temperature: float
    timeout: int
    retry_attempts: int
    retry_delay: float
    headers: Dict[str, str]
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ModelConfigTestRequest(BaseModel):
    """Request model for testing model configuration"""

    project_id: str = Field(..., description="Project ID to test")


class ModelConfigTestResponse(BaseModel):
    """Response model for model configuration test"""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None


class ProjectInfo(BaseModel):
    """Model for project information"""

    project_id: str
    project_name: str
    provider: Optional[str] = None
    model_name: Optional[str] = None
    updated_at: Optional[datetime] = None


class ModelConfigListResponse(BaseModel):
    """Response model for listing user projects with model configs"""

    projects: Optional[list[ProjectInfo]] = None
    configs: Optional[list[ModelConfigResponse]] = None
    total: int


class ModelConfigDeleteResponse(BaseModel):
    """Response model for deleting model configuration"""

    success: bool
    message: str
    deleted: bool


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
