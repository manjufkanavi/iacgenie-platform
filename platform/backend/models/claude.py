"""

Anthropic Claude Provider Implementation

"""

from typing import Any

from .base import BaseModelProvider, ModelResponse, ModelStatus


class ClaudeProvider(BaseModelProvider):
    """Anthropic Claude model provider"""

    def format_prompt(self, prompt: str, provider: str) -> str:
        """Format prompt for Claude models"""
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
        """Generate response from Claude model"""
        formatted_prompt = self.format_prompt(prompt, kwargs.get("provider", "aws"))
        payload = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": formatted_prompt}],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }
        response_data = await self._make_request(self.config.base_url, payload, headers)
        content = response_data["content"][0]["text"]
        input_tokens = response_data.get("usage", {}).get("input_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("output_tokens", 0)
        return ModelResponse(
            content=content,
            model=self.config.model_name,
            provider=self.config.provider,
            tokens_used=input_tokens + output_tokens,
            metadata=response_data,
        )

    async def health_check(self) -> ModelStatus:
        """Check if Claude model is available"""
        try:
            test_prompt = "Hello"
            payload = {
                "model": self.config.model_name,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": test_prompt}],
            }
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
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
