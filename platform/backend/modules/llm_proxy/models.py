"""

Data models for LLM Proxy.

This module defines Pydantic models for API request/response bodies

and domain models for business logic.

"""

from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from enum import Enum


class ProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    MISTRAL = "mistral"
    GEMINI = "gemini"
    CUSTOM = "custom"


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Choice(BaseModel):
    """A single choice in a completion response."""

    index: int = 0
    message: Optional[Dict[str, str]] = None
    text: Optional[str] = None
    finish_reason: Optional[str] = None
    logprobs: Optional[List[float]] = None


class LLMMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Message content")

    def validate_role(cls, v):
        """Validate message role."""
        valid_roles = {"system", "user", "assistant", "tool"}
        if v.lower() not in valid_roles:
            raise ValueError(f"Invalid role: {v}. Must be one of {valid_roles}")
        return v.lower()


class LLMRequest(BaseModel):
    """Request model for LLM API calls."""

    model: str = Field(
        ...,
        description="Model identifier (e.g., 'openai/gpt-4', 'gemini/gemini-1.5-pro')",
    )
    prompt: Optional[str] = Field(None, description="Prompt text (legacy format)")
    messages: Optional[List[LLMMessage]] = Field(
        None, description="Conversation messages"
    )
    temperature: Optional[float] = Field(None, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(None, description="Top-p sampling value")
    frequency_penalty: Optional[float] = Field(None, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, description="Presence penalty")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    stream: bool = Field(False, description="Whether to stream the response")
    session_id: Optional[str] = Field(None, description="Session ID for tracing")
    build_id: Optional[str] = Field(None, description="Build ID for tracing")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    def validate_model(cls, v):
        """Validate model identifier format."""
        if not v or not v.strip():
            raise ValueError("Model cannot be empty")
        return v.strip()

    def validate_temperature(cls, v):
        """Validate temperature."""
        if v is not None and (v < 0.0 or v > 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    def validate_max_tokens(cls, v):
        """Validate max tokens."""
        if v is not None and (v < 1 or v > 32000):
            raise ValueError("Max tokens must be between 1 and 32000")
        return v

    def validate_top_p(cls, v):
        """Validate top_p."""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Top_p must be between 0.0 and 1.0")
        return v

    def validate_frequency_penalty(cls, v):
        """Validate frequency penalty."""
        if v is not None and (v < -2.0 or v > 2.0):
            raise ValueError("Frequency penalty must be between -2.0 and 2.0")
        return v

    def validate_presence_penalty(cls, v):
        """Validate presence penalty."""
        if v is not None and (v < -2.0 or v > 2.0):
            raise ValueError("Presence penalty must be between -2.0 and 2.0")
        return v

    def get_provider(self) -> str:
        """Extract provider from model identifier."""
        if "/" in self.model:
            return self.model.split("/")[0].lower()
        return "openai"  # Default provider


class LLMResponse(BaseModel):
    """Response model for LLM API calls."""

    id: str = Field(..., description="Response ID")
    object: str = Field("text_completion", description="Object type")
    created: int = Field(..., description="Unix timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Choice] = Field(..., description="Response choices")
    usage: Optional[Usage] = Field(None, description="Token usage")
    error: Optional[str] = Field(None, description="Error message if any")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class LLMError(BaseModel):
    """Error response model."""

    error: Dict[str, Any] = Field(..., description="Error details")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    param: Optional[str] = Field(None, description="Parameter that caused error")


class CompletionRequest(BaseModel):
    """Legacy completion request (for backward compatibility)."""

    model: str = Field(..., description="Model identifier")
    prompt: str = Field(..., description="Prompt text")
    temperature: Optional[float] = Field(None, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
