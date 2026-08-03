"""

OpenAI Provider Implementation

"""

import logging

from typing import Any

from .base import BaseModelProvider, ModelResponse, ModelStatus

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseModelProvider):
    """OpenAI model provider"""

    def format_prompt(self, prompt: str, provider: str) -> str:
        """Format prompt for OpenAI models"""
        return f"""
        Generate production-ready {provider.upper()} infrastructure code based on this request: {prompt}
        Requirements:
        1. Create a complete OpenTofu configuration
        2. Include main.tf, variables.tf, outputs.tf, and README.md
        3. Use best practices and security standards
        4. Include proper documentation and comments
        5. Make it production-ready with proper naming conventions
        6. Use the latest provider versions
        7. Include proper variable definitions and outputs
        Return the response as a JSON object with a "files" array:
        {{
          "files": [
              {{"name": "main.tf", "language": "hcl", "content": "terraform code here"}},
              {{"name": "variables.tf", "language": "hcl", "content": "variables code here"}},
              {{"name": "outputs.tf", "language": "hcl", "content": "outputs code here"}},
              {{"name": "README.md", "language": "markdown", "content": "documentation here"}}
          ]
        }}
        Only return the JSON object, no additional text or explanations.
        """

    async def generate(self, prompt: str, **kwargs: Any) -> ModelResponse:
        """Generate response from OpenAI model"""
        formatted_prompt = self.format_prompt(prompt, kwargs.get("provider", "aws"))
        payload = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        response_data = await self._make_request(self.config.base_url, payload, headers)
        content = response_data["choices"][0]["message"]["content"]
        return ModelResponse(
            content=content,
            model=self.config.model_name,
            provider=self.config.provider,
            tokens_used=response_data.get("usage", {}).get("total_tokens"),
            metadata=response_data,
        )

    async def health_check(self) -> ModelStatus:
        """Check if OpenAI model is available"""
        # Skip health check for placeholder/invalid API keys
        api_key = self.config.api_key or ""
        if api_key.lower() in [
            "your_openai_api_key_here",
            "placeholder",
            "",
            "sk-placeholder-key-for-testing",
        ]:
            logger.warning("OpenAI health check skipped - using placeholder API key")
            return ModelStatus.UNAVAILABLE
        try:
            test_prompt = "Hello"
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 10,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            }
            await self._make_request(self.config.base_url, payload, headers)
            return ModelStatus.AVAILABLE
        except Exception as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                return ModelStatus.UNAVAILABLE
            elif "429" in str(e) or "rate limit" in str(e).lower():
                return ModelStatus.RATE_LIMITED
            else:
                return ModelStatus.ERROR
