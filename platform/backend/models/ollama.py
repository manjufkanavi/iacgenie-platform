"""Ollama provider for local LLM inference on port 1234."""

from datetime import datetime


import httpx

from typing import Any

from .base import BaseModelProvider, ModelConfig, ModelResponse, ModelStatus


class OllamaProvider(BaseModelProvider):
    """Provider for Ollama running locally at http://localhost:1234."""

    PROVIDER_NAME = "ollama"

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:1234"
        # Re-initialize client with the correct base_url since parent uses timeout only
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=config.timeout,
            headers={"Content-Type": "application/json"},
        )

    async def generate(self, prompt: str, **kwargs: Any) -> ModelResponse:
        """Call Ollama chat completions endpoint."""
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": "-1",  # Decoupled to just use the active local model
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature or 0.1,
            "max_tokens": self.config.max_tokens or 4096,
        }
        start_time = datetime.now()
        response_data = await self._make_request(url, payload)
        response_time = (datetime.now() - start_time).total_seconds()
        try:
            content = response_data["choices"][0]["message"]["content"]
            finish_reason = response_data["choices"][0].get("finish_reason", "stop")
        except (KeyError, IndexError) as e:
            from .base import ModelError

            raise ModelError(
                f"Unexpected response from Ollama: {response_data}",
                self.PROVIDER_NAME,
                self.config.model_name or "llama3",
                retryable=True,
            ) from e
        usage = response_data.get("usage", {})
        total_tokens = usage.get("total_tokens", 0) or (
            usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        )
        return ModelResponse(
            content=content,
            model=self.config.model_name or "llama3",
            provider=self.PROVIDER_NAME,
            tokens_used=total_tokens if total_tokens else None,
            response_time=response_time,
            metadata={"finish_reason": finish_reason},
        )

    async def health_check(self) -> ModelStatus:
        """Check if Ollama/OMLX is reachable."""
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.config.timeout
            ) as client:
                try:
                    # Try Ollama-specific endpoint first
                    resp = await client.get("/api/tags")
                    if resp.status_code == 200:
                        return ModelStatus.AVAILABLE
                except Exception:
                    pass
                # Fallback: OpenAI-compatible /v1/models (works with OMLX)
                try:
                    resp = await client.get("/v1/models")
                    return (
                        ModelStatus.AVAILABLE
                        if resp.status_code == 200
                        else ModelStatus.ERROR
                    )
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"Ollama health check failed: {e}"
                    )
                    return ModelStatus.ERROR
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Ollama client error: {e}")
            return ModelStatus.ERROR

    def format_prompt(self, prompt: str, provider: str) -> str:
        """Wrap infrastructure generation prompt for Ollama."""
        return f"""You MUST return a valid JSON object. No text before or after the JSON.

Generate production-ready {provider.upper()} infrastructure for: {prompt}

Return exactly this JSON structure (a JSON object with a "files" array):
{{
  "files": [
    {{"name": "main.tf", "language": "hcl", "content": "...terraform code..."}},
    {{"name": "variables.tf", "language": "hcl", "content": "...variables..."}},
    {{"name": "outputs.tf", "language": "hcl", "content": "...outputs..."}},
    {{"name": "README.md", "language": "markdown", "content": "...docs..."}}
  ]
}}

Rules:
- Output ONLY the JSON object. No explanation, no markdown, no code blocks.
- Each file has: name, language, content (string).
- content must contain complete, production-ready code.
- Start your response with {{ and end with }}."""

    async def close(self) -> None:
        """Cleanup HTTP client."""
        await self.client.aclose()
