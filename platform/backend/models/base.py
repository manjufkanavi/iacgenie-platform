"""

Base Model Provider Interface

Defines the contract that all AI model providers must implement.

"""

from abc import ABC, abstractmethod

from typing import Any, Dict, Optional

from dataclasses import dataclass

from enum import Enum

import asyncio

import httpx

from datetime import datetime


class ModelStatus(Enum):
    """Model availability status"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class ModelResponse:
    """Standardized response from any AI model"""

    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelConfig:
    """Configuration for a model provider"""

    name: str
    provider: str
    api_key: str
    base_url: str
    model_name: str
    max_tokens: int = 8192
    temperature: float = 0.1
    timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0
    headers: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ModelError(Exception):
    """Base exception for model-related errors"""

    def __init__(
        self,
        message: str,
        provider: str,
        model: str,
        status_code: Optional[int] = None,
        retryable: bool = False,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(self.message)


class BaseModelProvider(ABC):
    """Abstract base class for all AI model providers"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        self._last_request_time = 0
        self._request_count = 0

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> ModelResponse:
        """Generate a response from the AI model"""
        pass

    @abstractmethod
    async def health_check(self) -> ModelStatus:
        """Check if the model is available and healthy"""
        pass

    @abstractmethod
    def format_prompt(self, prompt: str, provider: str) -> str:
        """Format the prompt for the specific model"""
        pass

    async def _make_request(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and exponential backoff"""
        headers = headers or {}
        if self.config.headers:
            headers.update(self.config.headers)
        for attempt in range(self.config.retry_attempts):
            try:
                start_time = datetime.now()
                # Create a new client per request to avoid asyncio event loop closure issues across tasks
                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                (datetime.now() - start_time).total_seconds()
                if response.status_code == 200:
                    return response.json()
                # Handle different error status codes
                if response.status_code == 401:
                    raise ModelError(
                        f"Authentication failed: {response.text}",
                        self.config.provider,
                        self.config.model_name,
                        response.status_code,
                        retryable=False,
                    )
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = (2**attempt) * self.config.retry_delay
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    # Server error - retryable
                    if attempt < self.config.retry_attempts - 1:
                        wait_time = (2**attempt) * self.config.retry_delay
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise ModelError(
                            f"Server error: {response.text}",
                            self.config.provider,
                            self.config.model_name,
                            response.status_code,
                            retryable=True,
                        )
                else:
                    raise ModelError(
                        f"Request failed: {response.text}",
                        self.config.provider,
                        self.config.model_name,
                        response.status_code,
                        retryable=False,
                    )
            except httpx.TimeoutException:
                if attempt < self.config.retry_attempts - 1:
                    wait_time = (2**attempt) * self.config.retry_delay
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ModelError(
                        "Request timeout",
                        self.config.provider,
                        self.config.model_name,
                        retryable=True,
                    )
            except httpx.RequestError as e:
                if attempt < self.config.retry_attempts - 1:
                    wait_time = (2**attempt) * self.config.retry_delay
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ModelError(
                        f"Network error: {str(e)}",
                        self.config.provider,
                        self.config.model_name,
                        retryable=True,
                    )
        raise ModelError(
            "Max retry attempts exceeded",
            self.config.provider,
            self.config.model_name,
            retryable=False,
        )

    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from model response, handling markdown formatting"""
        content = content.strip()
        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    async def close(self) -> None:
        """Clean up resources"""
        await self.client.aclose()

    def __str__(self):
        return f"{self.config.provider}:{self.config.model_name}"

    def __repr__(self):
        return f"<{self.__class__.__name__}({self})>"
