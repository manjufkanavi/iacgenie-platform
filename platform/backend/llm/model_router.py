from typing import Dict, Any, Optional

from enum import Enum

import logging

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Types of models available for routing."""

    CLARIFY = "clarify"
    GENERATE = "generate"
    REVIEW = "review"
    ANALYSIS = "analysis"
    GENERAL = "general"


class ModelRouter:
    """Routes requests to appropriate LLM models based on task requirements."""

    def __init__(self) -> None:
        # Default model configurations
        self.model_configurations: Dict[ModelType, Dict[str, Any]] = {
            ModelType.CLARIFY: {
                "primary": "claude-sonnet-4-20250514",
                "fallback": "llama3.1:70b",
                "max_tokens": 4096,
                "temperature": 0.3,
            },
            ModelType.GENERATE: {
                "primary": "qwen2.5-coder-32b",
                "fallback": "gpt-4o",
                "max_tokens": 8192,
                "temperature": 0.2,
            },
            ModelType.REVIEW: {
                "primary": "phi-3-mini",
                "fallback": "phi-3-mini",
                "max_tokens": 2048,
                "temperature": 0.1,
            },
            ModelType.ANALYSIS: {
                "primary": "gpt-4o",
                "fallback": "llama3.1:70b",
                "max_tokens": 4096,
                "temperature": 0.0,
            },
            ModelType.GENERAL: {
                "primary": "gpt-4o",
                "fallback": "gpt-4o",
                "max_tokens": 2048,
                "temperature": 0.5,
            },
        }
        # Performance tracking
        self.performance_metrics: Dict[str, Dict[str, Any]] = {
            model: {"success": 0, "failures": 0, "latency": []}
            for config in self.model_configurations.values()
            for model in [config["primary"], config["fallback"]]
        }

    def route_request(
        self, task_type: ModelType, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route a request to the appropriate model based on task type.
        Args:
            task_type: Type of task being performed
            context: Additional context about the request
        Returns:
            Dictionary with model routing information
        """
        if task_type not in self.model_configurations:
            task_type = ModelType.GENERAL
        config = self.model_configurations[task_type]
        # Select model (primary with fallback)
        model_info = {
            "model_type": task_type.value,
            "primary_model": config["primary"],
            "fallback_model": config["fallback"],
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
            "context": context or {},
        }
        self.log_message(f"Routed {task_type.value} request to {config['primary']}")
        return model_info

    def record_performance(
        self, model_name: str, success: bool, latency_ms: float
    ) -> None:
        """
        Record performance metrics for a model.
        Args:
            model_name: Name of the model
            success: Whether the request was successful
            latency_ms: Request latency in milliseconds
        """
        if model_name not in self.performance_metrics:
            self.performance_metrics[model_name] = {
                "success": 0,
                "failures": 0,
                "latency": [],
            }
        metrics = self.performance_metrics[model_name]
        if success:
            metrics["success"] += 1
        else:
            metrics["failures"] += 1
        metrics["latency"].append(latency_ms)
        if len(metrics["latency"]) > 100:  # Keep last 100 measurements
            metrics["latency"] = metrics["latency"][-100:]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all models."""
        return {
            "performance_metrics": self.performance_metrics,
            "model_configurations": self.model_configurations,
        }

    def update_model_configuration(
        self, task_type: ModelType, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update model configuration for a specific task type.
        Args:
            task_type: Task type to update
            updates: Configuration updates
        Returns:
            Dictionary with update result
        """
        if task_type not in self.model_configurations:
            return {
                "success": False,
                "error": f"Unknown task type: {task_type}",
                "error_class": "invalid_task_type",
            }
        # Validate updates
        valid_keys = ["primary", "fallback", "max_tokens", "temperature"]
        for key in updates:
            if key not in valid_keys:
                return {
                    "success": False,
                    "error": f"Invalid configuration key: {key}",
                    "error_class": "invalid_configuration",
                }
        # Apply updates
        self.model_configurations[task_type].update(updates)
        self.log_message(f"Updated {task_type.value} model configuration")
        return {
            "success": True,
            "message": "Model configuration updated successfully",
            "updated_config": self.model_configurations[task_type],
        }

    def get_model_for_task(self, task_type: ModelType) -> str:
        """
        Get the primary model for a specific task type.
        Args:
            task_type: Task type
        Returns:
            Primary model name
        """
        if task_type not in self.model_configurations:
            return self.model_configurations[ModelType.GENERAL]["primary"]
        return self.model_configurations[task_type]["primary"]

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with model router context."""
        context = {
            "component": "model_router",
            "configured_models": len(self.model_configurations),
        }
        if level == "info":
            logger.info(message, extra=context)
        elif level == "warning":
            logger.warning(message, extra=context)
        elif level == "error":
            logger.error(message, extra=context)
        else:
            logger.debug(message, extra=context)


# Example usage


def create_model_router() -> ModelRouter:
    """Create a model router instance."""
    return ModelRouter()


def get_model_for_clarification() -> str:
    """Get the model for clarification tasks."""
    router = create_model_router()
    return router.get_model_for_task(ModelType.CLARIFY)


def get_model_for_generation() -> str:
    """Get the model for code generation tasks."""
    router = create_model_router()
    return router.get_model_for_task(ModelType.GENERATE)
