"""

Model Registry

Manages multiple AI model providers with fallback and load balancing capabilities.

"""

from typing import Dict, List, Any

from .base import BaseModelProvider, ModelConfig, ModelStatus, ModelError

from .mistral import MistralProvider

from .gemini import GeminiProvider

from .claude import ClaudeProvider

from .openai import OpenAIProvider

from .custom import CustomProvider

from .ollama import OllamaProvider

import asyncio

import logging

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry for managing multiple AI model providers"""

    def __init__(self) -> None:
        self.providers: Dict[str, BaseModelProvider] = {}
        self.provider_configs: Dict[str, ModelConfig] = {}
        self.fallback_order: List[str] = []
        self._health_cache: Dict[str, ModelStatus] = {}
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes

    def register_provider(self, name: str, config: ModelConfig) -> None:
        """Register a new model provider"""
        try:
            if config.provider == "mistral":
                provider: BaseModelProvider = MistralProvider(config)
            elif config.provider == "gemini":
                provider = GeminiProvider(config)
            elif config.provider == "claude":
                provider = ClaudeProvider(config)
            elif config.provider == "openai":
                provider = OpenAIProvider(config)
            elif config.provider == "custom":
                provider = CustomProvider(config)
            elif config.provider == "ollama":
                provider = OllamaProvider(config)
            else:
                raise ValueError(f"Unknown provider type: {config.provider}")
            self.providers[name] = provider
            self.provider_configs[name] = config
            self.fallback_order.append(name)
            logger.info(
                f"Registered provider: {name} ({config.provider}:{config.model_name})"
            )
        except Exception as e:
            logger.error(f"Failed to register provider {name}: {e}")
            raise

    def unregister_provider(self, name: str) -> None:
        """Unregister a model provider"""
        if name in self.providers:
            provider = self.providers[name]
            asyncio.create_task(provider.close())
            del self.providers[name]
            del self.provider_configs[name]
            if name in self.fallback_order:
                self.fallback_order.remove(name)
            if name in self._health_cache:
                del self._health_cache[name]
            logger.info(f"Unregistered provider: {name}")

    def set_fallback_order(self, order: List[str]) -> None:
        """Set the fallback order for providers"""
        # Validate that all providers in order exist
        for name in order:
            if name not in self.providers:
                raise ValueError(f"Provider {name} not found in registry")
        self.fallback_order = order
        logger.info(f"Set fallback order: {order}")

    async def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        await self._update_health_cache()
        return [
            name
            for name, status in self._health_cache.items()
            if status == ModelStatus.AVAILABLE
        ]

    async def generate_with_fallback(self, prompt: str, **kwargs: Any) -> Any:
        """Generate response with automatic fallback to available providers"""
        available_providers = await self.get_available_providers()
        if not available_providers:
            raise ModelError(
                "No available AI providers", "registry", "unknown", retryable=False
            )
        # Try providers in fallback order
        for provider_name in self.fallback_order:
            if provider_name in available_providers:
                try:
                    provider = self.providers[provider_name]
                    logger.info(f"Generating with provider: {provider_name}")
                    # Format prompt for the provider
                    formatted_prompt = provider.format_prompt(prompt, provider_name)
                    response = await provider.generate(formatted_prompt, **kwargs)
                    logger.info(f"Successfully generated with {provider_name}")
                    return response
                except Exception as e:
                    logger.warning(f"Provider {provider_name} failed: {e}")
                    # Mark provider as unavailable temporarily
                    self._health_cache[provider_name] = ModelStatus.ERROR
                    continue
        # If we get here, all providers failed
        raise ModelError(
            "All AI providers failed", "registry", "unknown", retryable=True
        )

    async def generate_with_provider(
        self, provider_name: str, prompt: str, **kwargs: Any
    ) -> Any:
        """Generate response with a specific provider"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not found")
        provider = self.providers[provider_name]
        # Check health
        status = await provider.health_check()
        if status != ModelStatus.AVAILABLE:
            raise ModelError(
                f"Provider {provider_name} is not available (status: {status})",
                provider_name,
                provider.config.model_name,
                retryable=False,
            )
        logger.info(f"Generating with specific provider: {provider_name}")
        # Format prompt for the provider
        provider_name_for_prompt = kwargs.get("provider", provider_name)
        formatted_prompt = provider.format_prompt(prompt, provider_name_for_prompt)
        response = await provider.generate(formatted_prompt, **kwargs)
        logger.info(f"Successfully generated with {provider_name}")
        return response

    async def _update_health_cache(self) -> None:
        """Update health cache for all providers"""
        import time

        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return
        logger.debug("Updating provider health cache")
        health_tasks = []
        for name, provider in self.providers.items():
            health_tasks.append(self._check_provider_health(name, provider))
        # Run health checks concurrently
        results = await asyncio.gather(*health_tasks, return_exceptions=True)
        for name, result in zip(self.providers.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Health check failed for {name}: {result}")
                self._health_cache[name] = ModelStatus.ERROR
            elif isinstance(result, ModelStatus):
                self._health_cache[name] = result
            else:
                self._health_cache[name] = ModelStatus.ERROR
        self._last_health_check = int(current_time)

    async def _check_provider_health(
        self, name: str, provider: BaseModelProvider
    ) -> ModelStatus:
        """Check health of a specific provider"""
        try:
            return await provider.health_check()
        except Exception as e:
            logger.warning(f"Health check failed for {name}: {e}")
            return ModelStatus.ERROR

    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered providers"""
        info = {}
        for name, config in self.provider_configs.items():
            status = self._health_cache.get(name, ModelStatus.ERROR)
            info[name] = {
                "provider": config.provider,
                "model": config.model_name,
                "status": status.value if hasattr(status, "value") else str(status),
                "base_url": config.base_url,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            }
        return info

    async def close_all(self) -> None:
        """Close all providers"""
        close_tasks = []
        for provider in self.providers.values():
            close_tasks.append(provider.close())
        await asyncio.gather(*close_tasks, return_exceptions=True)
        logger.info("Closed all providers")

    def __len__(self) -> int:
        return len(self.providers)

    def __contains__(self, name: str) -> bool:
        return name in self.providers
