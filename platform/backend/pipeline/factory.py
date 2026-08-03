from typing import Optional, Dict, Any

from .pipeline_engine import AgenticPipeline

from .config import PipelineConfigManager

from repositories.state_repository import StateRepository


class PipelineFactory:
    """Factory for creating and configuring agentic pipelines."""

    def __init__(self) -> None:
        self.config_manager = PipelineConfigManager()

    def create_pipeline(
        self,
        config: Optional[Dict[str, Any]] = None,
        state_repository: Optional[StateRepository] = None,
    ) -> AgenticPipeline:
        """Create a new pipeline instance with optional configuration."""
        # Apply configuration if provided
        if config:
            self.config_manager.update_configuration(config)
        # Create pipeline with state repository
        pipeline = AgenticPipeline(state_repository=state_repository)
        # Inject configuration into pipeline (this would be more sophisticated in a real implementation)
        pipeline.config_manager = self.config_manager  # type: ignore[attr-defined]
        return pipeline

    def create_pipeline_from_config_file(
        self, config_file_path: str
    ) -> AgenticPipeline:
        """Create a pipeline from a configuration file."""
        try:
            import json

            with open(config_file_path, "r") as f:
                config_data = json.load(f)
            return self.create_pipeline(config_data)
        except Exception as e:
            raise ValueError(f"Failed to load pipeline configuration: {str(e)}")

    def validate_pipeline_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a pipeline configuration before creating a pipeline."""
        try:
            # Create a temporary config manager to validate
            temp_config_manager = PipelineConfigManager(config)
            return temp_config_manager.validate_configuration()
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_default_configuration(self) -> Dict[str, Any]:
        """Get the default pipeline configuration."""
        return self.config_manager._load_default_config().dict()

    def create_pipeline_with_custom_repository(self, db_path: str) -> AgenticPipeline:
        """Create a pipeline with a custom state repository."""
        custom_repository = StateRepository(db_path)
        return self.create_pipeline(state_repository=custom_repository)

    def configure_pipeline_for_environment(self, environment: str) -> Dict[str, Any]:
        """Get configuration optimized for a specific environment."""
        base_config = self.get_default_configuration()
        if environment == "development":
            # Development configuration - faster, more lenient
            config_updates = {
                "agent_configurations": {
                    "clarify": {"timeout_seconds": 300},
                    "generate": {"timeout_seconds": 450},
                    "command": {"timeout_seconds": 300},
                },
                "global_timeout_seconds": 3600,
            }
        elif environment == "production":
            # Production configuration - more robust, higher timeouts
            config_updates = {
                "agent_configurations": {
                    "clarify": {"timeout_seconds": 900},
                    "generate": {"timeout_seconds": 1200},
                    "command": {"timeout_seconds": 900},
                    "apply": {"timeout_seconds": 1800},
                },
                "global_timeout_seconds": 10800,
                "state_checkpoint_interval": 15,
            }
        elif environment == "testing":
            # Testing configuration - very fast timeouts
            config_updates = {
                "agent_configurations": {
                    "clarify": {"timeout_seconds": 60},
                    "generate": {"timeout_seconds": 120},
                    "command": {"timeout_seconds": 60},
                },
                "global_timeout_seconds": 600,
            }
        else:
            # Default configuration
            config_updates = {}
        # Merge updates with base config
        self._deep_merge_configs(base_config, config_updates)
        return base_config

    def _deep_merge_configs(
        self, base: Dict[str, Any], updates: Dict[str, Any]
    ) -> None:
        """Deep merge configuration dictionaries."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge_configs(base[key], value)
            else:
                base[key] = value

    def create_mock_pipeline(self) -> AgenticPipeline:
        """Create a pipeline configured for testing/mocking."""
        mock_config = self.configure_pipeline_for_environment("testing")
        # Add mock-specific configurations
        mock_config["agent_configurations"]["generate"]["model_routing"] = {
            "primary": "mock-llm",
            "fallback": "mock-llm",
        }
        return self.create_pipeline(mock_config)

    def get_pipeline_health_check_config(self) -> Dict[str, Any]:
        """Get configuration for pipeline health checks."""
        health_config = self.get_default_configuration()
        # Optimize for health checks
        health_config["agent_configurations"]["clarify"]["timeout_seconds"] = 30
        health_config["agent_configurations"]["generate"]["timeout_seconds"] = 60
        health_config["global_timeout_seconds"] = 180
        return health_config
