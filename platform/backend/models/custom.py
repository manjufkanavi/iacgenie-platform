"""

Custom Model Provider Implementation

Supports any custom model via REST API endpoint (BYOM - Bring Your Own Model)

"""

from typing import Dict, Any, Optional

from .base import BaseModelProvider, ModelResponse, ModelStatus


class CustomProvider(BaseModelProvider):
    """Custom model provider for BYOM (Bring Your Own Model)"""

    def format_prompt(self, prompt: str, provider: str) -> str:
        """Format prompt for custom models"""
        return f"""
        Generate production-ready {provider.upper()} infrastructure code based on this request: {prompt}
        Requirements:
        1. Create a complete Terraform configuration
        2. Include main.tf, variables.tf, outputs.tf, and README.md
        3. Use best practices and security standards
        4. Include proper documentation and comments
        5. Make it production-ready with proper naming conventions
        6. Use the latest provider versions
        7. Include proper variable definitions and outputs
        Return the requested files using the following XML-like tag format for EACH file. Do not output the files inside a JSON object. This is a strict requirement.
        
        CRITICAL INSTRUCTIONS:
        1. Wrap each file completely inside `<file name="FILENAME">...</file>` tags.
        2. Put the FULL, UNABBREVIATED code inside the tags. DO NOT use `...` or truncate anything.
        3. Do not wrap the `<file>` tags inside markdown code blocks.
        4. You may include directory paths in the "name" attribute (e.g., `<file name="modules/vpc/main.tf">`).
        
        Example Output Format:
        <file name="main.tf">
        provider "aws" {{
          region = "us-west-2"
        }}
        </file>
        
        <file name="variables.tf">
        variable "vpc_cidr" {{
          type = string
        }}
        </file>
        """

    async def generate(self, prompt: str, **kwargs: Any) -> ModelResponse:
        """Generate response from custom model"""
        formatted_prompt = self.format_prompt(prompt, kwargs.get("provider", "aws"))
        # Get custom payload format from config metadata
        metadata = self.config.metadata or {}
        payload_format = metadata.get("payload_format", "openai")

        model_id = self.config.model_name
        # Decouple local models from explicit loading
        if self.config.base_url and any(
            h in self.config.base_url for h in ["localhost", "127.0.0.1", "0.0.0.0"]
        ):
            model_id = "-1"

        if payload_format == "openai":
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": formatted_prompt}],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
        elif payload_format == "anthropic":
            payload = {
                "model": model_id,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": [{"role": "user", "content": formatted_prompt}],
            }
        elif payload_format == "gemini":
            payload = {
                "contents": [{"parts": [{"text": formatted_prompt}]}],
                "generationConfig": {
                    "temperature": self.config.temperature,
                    "maxOutputTokens": self.config.max_tokens,
                },
            }
        else:
            # Custom format - use the format specified in metadata
            payload = metadata.get("custom_payload", {})
            # Replace placeholders
            payload = self._replace_placeholders(
                payload,
                {
                    "prompt": formatted_prompt,
                    "model": model_id,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                },
            )
        # Get custom headers from config
        headers = {"Content-Type": "application/json"}
        # Add authorization header based on config
        auth_type = metadata.get("auth_type", "bearer")
        if auth_type == "bearer" and self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif auth_type == "api_key" and self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        elif auth_type == "custom":
            custom_headers = metadata.get("custom_headers", {})
            headers.update(custom_headers)
        if self.config.headers:
            headers.update(self.config.headers)
        response_data = await self._make_request(self.config.base_url, payload, headers)
        print("LM STUDIO RESPONSE:", response_data)
        # Extract content based on response format
        response_format = metadata.get("response_format", "openai")
        if response_format == "openai":
            content = response_data["choices"][0]["message"]["content"]
        elif response_format == "anthropic":
            content = response_data["content"][0]["text"]
        elif response_format == "gemini":
            content = response_data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            # Custom format - use the path specified in metadata
            content_path = metadata.get("content_path", "choices.0.message.content")
            content = self._extract_nested_value(response_data, content_path)
        return ModelResponse(
            content=content,
            model=self.config.model_name,
            provider=self.config.provider,
            tokens_used=self._extract_tokens_used(response_data, response_format),
            metadata=response_data,
        )

    def _replace_placeholders(
        self, payload: Dict[str, Any], replacements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Replace placeholders in custom payload format"""
        import json

        payload_str = json.dumps(payload)
        for key, value in replacements.items():
            placeholder = f"${{{key}}}"
            payload_str = payload_str.replace(placeholder, str(value))
        return json.loads(payload_str)

    def _extract_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Extract value from nested dictionary using dot notation"""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise ValueError(f"Path {path} not found in response")
        return current

    def _extract_tokens_used(
        self, response_data: Dict[str, Any], format_type: str
    ) -> Optional[int]:
        """Extract token usage from response based on format"""
        try:
            if format_type == "openai":
                return response_data.get("usage", {}).get("total_tokens")
            elif format_type == "anthropic":
                usage = response_data.get("usage", {})
                return usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            elif format_type == "gemini":
                return response_data.get("usageMetadata", {}).get("totalTokenCount")
            else:
                # Custom format
                metadata = self.config.metadata or {}
                tokens_path = metadata.get("tokens_path")
                if tokens_path:
                    return self._extract_nested_value(response_data, tokens_path)
                return None
        except Exception:
            return None

    async def health_check(self) -> ModelStatus:
        """Check if custom model is available"""
        try:
            metadata = self.config.metadata or {}
            # Use a simple health check endpoint or make a minimal request
            health_endpoint = metadata.get("health_endpoint")
            if health_endpoint:
                # Use dedicated health check endpoint
                response = await self.client.get(health_endpoint)
                if response.status_code == 200:
                    return ModelStatus.AVAILABLE
                else:
                    return ModelStatus.ERROR
            else:
                # Make a minimal generation request
                test_prompt = "Hello"
                payload_format = metadata.get("payload_format", "openai")
                if payload_format == "openai":
                    payload = {
                        "model": self.config.model_name,
                        "messages": [{"role": "user", "content": test_prompt}],
                        "max_tokens": 10,
                    }
                else:
                    # Use minimal custom payload
                    payload = metadata.get(
                        "health_payload", {"prompt": test_prompt, "max_tokens": 10}
                    )
                headers = {"Content-Type": "application/json"}
                auth_type = metadata.get("auth_type", "bearer")
                if auth_type == "bearer" and self.config.api_key:
                    headers["Authorization"] = f"Bearer {self.config.api_key}"
                elif auth_type == "api_key" and self.config.api_key:
                    headers["X-API-Key"] = self.config.api_key
                await self._make_request(self.config.base_url, payload, headers)
                return ModelStatus.AVAILABLE
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Health check failed for {self.config.name}: {e}", exc_info=True
            )
            if "401" in str(e) or "authentication" in str(e).lower():
                return ModelStatus.UNAVAILABLE
            elif "429" in str(e) or "rate limit" in str(e).lower():
                return ModelStatus.RATE_LIMITED
            else:
                return ModelStatus.ERROR
