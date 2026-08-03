"""

AI Service with Multi-Model Support

Provides a unified interface for AI model interactions with support for multiple providers.

"""

import os

import json

import logging

from typing import Dict, Any, Optional

from models.registry import ModelRegistry

from models.base import ModelConfig, ModelError


from db.db_provider import db_provider

from dotenv import load_dotenv

# Load environment variables

load_dotenv()

logger = logging.getLogger(__name__)


class AIService:
    """AI Service with multi-model support and BYOM capabilities"""

    def __init__(self) -> None:
        self.registry = ModelRegistry()
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize all configured providers from environment variables"""
        # Placeholder values to skip
        placeholder_values = [
            "your_mistral_api_key_here",
            "your_gemini_api_key_here",
            "your_openai_api_key_here",
            "placeholder",
            "",
        ]
        # Mistral via OpenRouter (default)
        mistral_api_key = os.getenv("MISTRAL_API_KEY")
        if mistral_api_key and mistral_api_key.lower() not in [
            pv.lower() for pv in placeholder_values
        ]:
            mistral_config = ModelConfig(
                name="mistral-openrouter",
                provider="mistral",
                api_key=mistral_api_key,
                base_url="https://openrouter.ai/api/v1/chat/completions",
                model_name="mistralai/mistral-7b-instruct",
                max_tokens=8192,
                temperature=0.1,
                timeout=120,
                headers={
                    "HTTP-Referer": "https://iacgenie.ai",
                    "X-Title": "IaCGenie AI",
                },
            )
            self.registry.register_provider("mistral-openrouter", mistral_config)
            logger.info("Registered Mistral provider via OpenRouter")
        elif not mistral_api_key:
            logger.warning(
                "MISTRAL_API_KEY not set - Mistral provider will be unavailable"
            )
        # Direct Mistral API
        direct_mistral_key = os.getenv("DIRECT_MISTRAL_API_KEY")
        if direct_mistral_key and direct_mistral_key.lower() not in [
            pv.lower() for pv in placeholder_values
        ]:
            direct_mistral_config = ModelConfig(
                name="mistral-direct",
                provider="mistral",
                api_key=direct_mistral_key,
                base_url="https://api.mistral.ai/v1/chat/completions",
                model_name="mistral-large-latest",
                max_tokens=8192,
                temperature=0.1,
                timeout=120,
            )
            self.registry.register_provider("mistral-direct", direct_mistral_config)
            logger.info("Registered direct Mistral provider")
        elif not direct_mistral_key:
            logger.warning(
                "DIRECT_MISTRAL_API_KEY not set - Direct Mistral provider will be unavailable"
            )
        # Google Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key and gemini_api_key.lower() not in [
            pv.lower() for pv in placeholder_values
        ]:
            gemini_config = ModelConfig(
                name="gemini",
                provider="gemini",
                api_key=gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/models",
                model_name="gemini-1.5-pro",
                max_tokens=8192,
                temperature=0.1,
                timeout=120,
            )
            self.registry.register_provider("gemini", gemini_config)
            logger.info("Registered Gemini provider")
        elif not gemini_api_key:
            logger.warning(
                "GEMINI_API_KEY not set - Gemini provider will be unavailable"
            )
        # Anthropic Claude
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        if claude_api_key and claude_api_key.lower() not in [
            pv.lower() for pv in placeholder_values
        ]:
            claude_config = ModelConfig(
                name="claude",
                provider="claude",
                api_key=claude_api_key,
                base_url="https://api.anthropic.com/v1/messages",
                model_name="claude-3-sonnet-20240229",
                max_tokens=8192,
                temperature=0.1,
                timeout=120,
            )
            self.registry.register_provider("claude", claude_config)
            logger.info("Registered Claude provider")
        elif not claude_api_key:
            logger.warning(
                "CLAUDE_API_KEY not set - Claude provider will be unavailable"
            )
        # OpenAI GPT-4
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key and openai_api_key.lower() not in [
            pv.lower() for pv in placeholder_values
        ]:
            openai_config = ModelConfig(
                name="openai",
                provider="openai",
                api_key=openai_api_key,
                base_url="https://api.openai.com/v1/chat/completions",
                model_name="gpt-4-turbo-preview",
                max_tokens=8192,
                temperature=0.1,
                timeout=120,
            )
            self.registry.register_provider("openai", openai_config)
            logger.info("Registered OpenAI provider")
        elif not openai_api_key:
            logger.warning(
                "OPENAI_API_KEY not set - OpenAI provider will be unavailable"
            )
        # Custom BYOM providers
        self._load_custom_providers()
        # Ollama local LLM
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:1234")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        ollama_config = ModelConfig(
            name="ollama",
            provider="ollama",
            api_key="",
            base_url=ollama_url,
            model_name=ollama_model,
            max_tokens=4096,
            temperature=0.1,
            timeout=120,
        )
        try:
            self.registry.register_provider("ollama", ollama_config)
            logger.info("Registered Ollama local LLM provider")
        except Exception as e:
            logger.warning(f"Failed to register Ollama provider: {e}")
        # Set fallback order
        if self.registry.providers:
            fallback_order = list(self.registry.providers.keys())
            self.registry.set_fallback_order(fallback_order)
            logger.info(f"Set fallback order: {fallback_order}")
        else:
            logger.warning("No AI providers configured!")

    def _load_custom_providers(self) -> None:
        """Load custom BYOM providers from environment variables"""
        # Look for custom provider configurations
        custom_providers = {}
        # Parse environment variables for custom providers
        for key, value in os.environ.items():
            if key.startswith("CUSTOM_PROVIDER_") and key.endswith("_CONFIG"):
                provider_name = (
                    key.replace("CUSTOM_PROVIDER_", "").replace("_CONFIG", "").lower()
                )
                try:
                    config_data = json.loads(value)
                    custom_providers[provider_name] = config_data
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in {key}")
        # Register custom providers
        for name, config_data in custom_providers.items():
            try:
                custom_config = ModelConfig(
                    name=name,
                    provider="custom",
                    api_key=config_data.get("api_key", ""),
                    base_url=config_data.get("base_url", ""),
                    model_name=config_data.get("model_name", "custom"),
                    max_tokens=config_data.get("max_tokens", 8192),
                    temperature=config_data.get("temperature", 0.1),
                    timeout=config_data.get("timeout", 120),
                    headers=config_data.get("headers"),
                    metadata=config_data.get("metadata", {}),
                )
                self.registry.register_provider(name, custom_config)
                logger.info(f"Registered custom provider: {name}")
            except Exception as e:
                logger.error(f"Failed to register custom provider {name}: {e}")

    async def load_model_config_from_db(
        self, project_id: str, config_id: str
    ) -> Optional[ModelConfig]:
        """Load a model configuration from PostgreSQL and convert it to a ModelConfig object"""
        try:
            config_data = await db_provider.get_model_config("", project_id, config_id)
            if not config_data:
                logger.error(
                    f"Model configuration {config_id} not found in project {project_id}"
                )
                return None
            # postgres adapter already decrypts api_key
            model_config = ModelConfig(
                name=config_data.get("name", config_id),
                provider=config_data.get("provider", "custom"),
                api_key=config_data.get("api_key", ""),
                base_url="",
                model_name=config_data.get("model", ""),
                max_tokens=config_data.get("max_tokens", 8192),
                temperature=float(config_data.get("temperature", 0)) / 100.0
                if config_data.get("temperature")
                else 0.1,
                timeout=config_data.get("timeout", 120),
                retry_attempts=config_data.get("retry_attempts", 3),
                retry_delay=config_data.get("retry_delay", 1.0),
                headers=config_data.get("headers"),
                metadata=config_data.get("metadata"),
            )
            logger.info(
                f"Loaded model config from DB: {config_id} ({
                    config_data.get('provider')
                }:{config_data.get('model')})"
            )
            return model_config
        except Exception as e:
            logger.error(f"Failed to load model config {config_id} from DB: {e}")
            return None

    async def generate_infrastructure(
        self,
        prompt: str,
        provider: str = "aws",
        model_name: Optional[str] = None,
        project_id: Optional[str] = None,
        model_config_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate infrastructure code with the specified or best available model"""
        from utils.tracing import get_tracer
        from opentelemetry.trace import SpanKind
        from utils.metrics import TOKEN_USAGE

        tracer = get_tracer()
        span = tracer.start_span("generate_infrastructure", kind=SpanKind.SERVER)
        try:
            logger.info(f"INIT: Starting infrastructure generation for {provider}")
            # Add provider context to prompt
            enhanced_prompt = (
                f"You are an Infrastructure-as-Code generator.\n"
                f"Generate {provider.upper()} infrastructure for the following request:\n"
                f"{prompt}\n\n"
                f"IMPORTANT: You MUST respond ONLY with the infrastructure files using the following XML-like tag format for EACH file. Do not output the files inside a JSON object.\n"
                f"CRITICAL INSTRUCTIONS:\n"
                f'1. Wrap each file completely inside `<file name="FILENAME">...</file>` tags.\n'
                f"2. Put the FULL, UNABBREVIATED code inside the tags. DO NOT use `...` or truncate anything.\n"
                f"3. Do not wrap the `<file>` tags inside markdown code blocks.\n"
                f'4. You may include directory paths in the "name" attribute (e.g., `<file name="modules/vpc/main.tf">`).\n\n'
                f"Example Output Format:\n"
                f'<file name="main.tf">\n'
                f'provider "aws" {{\n'
                f'  region = "us-west-2"\n'
                f"}}\n"
                f"</file>\n\n"
                f'<file name="variables.tf">\n'
                f'variable "vpc_cidr" {{\n'
                f"  type = string\n"
                f"}}\n"
                f"</file>"
            )

            # If a model_config_dict is provided (e.g. from postgres), use it directly
            if model_config_dict:
                # Check for expiration
                expires_at = model_config_dict.get("expires_at")
                if expires_at:
                    from datetime import datetime, timezone

                    if isinstance(expires_at, str):
                        try:
                            expires_at = datetime.fromisoformat(
                                expires_at.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass
                    if isinstance(expires_at, datetime) and expires_at.replace(
                        tzinfo=timezone.utc
                    ) < datetime.now(timezone.utc):
                        raise RuntimeError(
                            f"API key for model configuration {model_name} has expired"
                        )

                logger.info(
                    f"GENERATE: Using provided model_config_dict for {model_name}"
                )
                # Ensure the provider string matches one of our supported bases if it's not custom
                base_url = model_config_dict.get("base_url") or ""
                prov = model_config_dict.get("provider", "custom")
                if prov == "lmstudio":
                    prov = "custom"
                if not base_url:
                    if prov == "ollama":
                        base_url = "http://localhost:1234"
                    else:
                        base_url = "http://localhost:1234"

                actual_model_name = (
                    model_config_dict.get("model_name") or model_name or ""
                )

                temp_config = ModelConfig(
                    name=f"temp_{model_name or 'custom'}",
                    provider=prov,
                    api_key=model_config_dict.get("api_key", ""),
                    base_url=base_url,
                    model_name=actual_model_name,
                    max_tokens=model_config_dict.get("max_tokens", 8192),
                    temperature=model_config_dict.get("temperature", 0.1),
                    timeout=model_config_dict.get("timeout", 300),
                    headers=model_config_dict.get("headers", {}),
                    metadata=model_config_dict.get("metadata", {}),
                )
                temp_provider_name = f"temp_{model_name or 'custom'}"
                self.registry.register_provider(temp_provider_name, temp_config)
                try:
                    response = await self.registry.generate_with_provider(
                        temp_provider_name, enhanced_prompt, provider=provider
                    )
                finally:
                    if temp_provider_name in self.registry.providers:
                        del self.registry.providers[temp_provider_name]
                        if temp_provider_name in self.registry.provider_configs:
                            del self.registry.provider_configs[temp_provider_name]

            # If model_name looks like a UUID and we have a project_id, try to load it from DB
            elif (
                model_name
                and project_id
                and len(model_name) >= 32
                and "-" in model_name
                and model_name.count("-") >= 4  # Simple UUID heuristic
            ):
                logger.info(f"GENERATE: Loading model config from DB: {model_name}")
                model_config = await self.load_model_config_from_db(
                    project_id, model_name
                )
                if model_config:
                    # Register this config temporarily for this generation
                    temp_provider_name = f"temp_{model_name}"
                    self.registry.register_provider(temp_provider_name, model_config)
                    try:
                        logger.info(f"GENERATE: Using DB model config {model_name}")
                        response = await self.registry.generate_with_provider(
                            temp_provider_name, enhanced_prompt, provider=provider
                        )
                    finally:
                        # Clean up temporary provider
                        if temp_provider_name in self.registry.providers:
                            del self.registry.providers[temp_provider_name]
                            if temp_provider_name in self.registry.provider_configs:
                                del self.registry.provider_configs[temp_provider_name]
                else:
                    logger.warning(
                        f"GENERATE: Failed to load model config {model_name} "
                        f"from DB, falling back to available providers"
                    )
                    response = await self.registry.generate_with_fallback(
                        enhanced_prompt, provider=provider
                    )
            # Use specific model if requested and it exists in registry
            elif model_name and model_name in self.registry.providers:
                logger.info(f"GENERATE: Using specific model {model_name}")
                response = await self.registry.generate_with_provider(
                    model_name, enhanced_prompt, provider=provider
                )
            else:
                logger.info("GENERATE: Using best available model with fallback")
                response = await self.registry.generate_with_fallback(
                    enhanced_prompt, provider=provider
                )
            # Parse the response
            try:
                content = response.content.strip()
                logger.info(f"RAW LLM RESPONSE BEFORE EXTRACTION:\n{content}")
                files = self._parse_llm_response(content)
                if not isinstance(files, list):
                    raise ValueError(
                        f"Response is not a list of files. Got: {type(files)}"
                    )
                if not files:
                    raise ValueError("LLM response parsed to an empty list of files")
                logger.info(f"SUCCESS: Generated {len(files)} files")

                if response.tokens_used:
                    TOKEN_USAGE.labels(type="total").observe(response.tokens_used)

                return {
                    "success": True,
                    "files": files,
                    "model": response.model,
                    "provider": response.provider,
                    "tokens_used": response.tokens_used,
                    "response_time": response.response_time,
                }
            except Exception as e:
                logger.error(f"ERROR: Failed to process response: {e}")
                logger.error(f"RAW CONTENT WAS: {response.content}")
                raise ModelError(
                    f"Failed to process AI response: {e}",
                    response.provider,
                    response.model,
                    retryable=False,
                )
        except ModelError as e:
            logger.error(f"ERROR: Model error - {e.message}")
            raise
        except Exception as e:
            logger.error(f"ERROR: Unexpected error during generation: {e}")
            raise ModelError(
                f"Unexpected error: {str(e)}", "unknown", "unknown", retryable=True
            )
        finally:
            span.end()

    def _parse_llm_response(self, content: str) -> list:
        """Parse files from LLM response, prioritizing XML <file> tags with a fallback to JSON."""
        content = content.strip()
        import re

        # Strip out <think> blocks (DeepSeek/Qwen)
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        import json

        files = []
        # 1. Try to parse XML <file name="...">...</file> format
        file_pattern = re.compile(
            r'<file\s+name="([^"]+)">\s*(.*?)\s*</file>', re.DOTALL
        )
        matches = file_pattern.findall(content)
        if matches:
            for name, file_content in matches:
                files.append({"name": name, "content": file_content})
            return files

        # 2. Fallback to extracting JSON
        # First try to find explicit ```json blocks
        json_str = None
        json_matches = re.findall(r"```json\s*\n(.*?)```", content, re.DOTALL)
        if json_matches:
            json_str = json_matches[-1].strip()
        else:
            # Then try to find any code blocks that look like JSON (start with { or [)
            all_matches = re.findall(r"```(?:.*?)\s*\n(.*?)```", content, re.DOTALL)
            for match in reversed(all_matches):
                match_stripped = match.strip()
                if match_stripped.startswith("{") or match_stripped.startswith("["):
                    json_str = match_stripped
                    break

            # If no code blocks, check if the content itself is JSON
            if not json_str and (content.startswith("{") or content.startswith("[")):
                json_str = content

        if json_str:
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    result = parsed.get("files", parsed.get("code", []))
                    return result if isinstance(result, list) else []
                elif isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        return files

    async def get_available_models(self) -> Dict[str, Any]:
        """Get information about available models"""
        await self.registry._update_health_cache()
        return self.registry.get_provider_info()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all providers"""
        available_providers = await self.registry.get_available_providers()
        total_providers = len(self.registry.providers)
        return {
            "status": "healthy" if available_providers else "unhealthy",
            "available_providers": len(available_providers),
            "total_providers": total_providers,
            "providers": self.registry.get_provider_info(),
        }

    async def close(self) -> None:
        """Clean up resources"""
        await self.registry.close_all()


# Global AI service instance


ai_service = AIService()
