from typing import Dict, Any, Optional

from pydantic import ConfigDict, BaseModel, Field


class AgentConfiguration(BaseModel):
    """Configuration for an individual agent."""

    agent_type: str = Field(..., description="Type of agent")
    model_routing: Dict[str, str] = Field(
        default_factory=dict, description="Model routing configuration"
    )
    timeout_seconds: int = Field(300, description="Maximum execution time in seconds")
    retry_limit: int = Field(3, description="Maximum number of retries")


class PipelineConfiguration(BaseModel):
    """Configuration for the agentic pipeline."""

    agent_configurations: Dict[str, AgentConfiguration] = Field(
        default_factory=dict, description="Agent-specific configurations"
    )
    phase_transitions: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Phase transition rules"
    )
    global_timeout_seconds: int = Field(
        3600, description="Global pipeline timeout in seconds"
    )
    state_checkpoint_interval: int = Field(
        60, description="State checkpoint interval in seconds"
    )
    enable_observability: bool = Field(
        True, description="Enable observability features"
    )
    model_config = ConfigDict(extra="forbid")


class PipelineConfigManager:
    """Manages pipeline configuration with validation."""

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        self.config = self._load_default_config()
        if config_data:
            self.config = PipelineConfiguration(**config_data)

    def _load_default_config(self) -> PipelineConfiguration:
        """Load the default pipeline configuration."""
        default_config = {
            "agent_configurations": {
                "clarify": {
                    "agent_type": "clarify",
                    "model_routing": {
                        "primary": "claude-sonnet-4-20250514",
                        "fallback": "llama3.1:70b",
                    },
                    "timeout_seconds": 600,
                    "retry_limit": 2,
                },
                "generate": {
                    "agent_type": "generate",
                    "model_routing": {
                        "primary": "qwen2.5-coder-32b",
                        "fallback": "gpt-4o",
                    },
                    "timeout_seconds": 900,
                    "retry_limit": 3,
                },
                "static_analysis": {
                    "agent_type": "static_analysis",
                    "model_routing": {
                        "primary": "phi-3-mini",
                        "fallback": "phi-3-mini",
                    },
                    "timeout_seconds": 300,
                    "retry_limit": 1,
                },
                "command": {
                    "agent_type": "command",
                    "timeout_seconds": 600,
                    "retry_limit": 2,
                },
                "apply": {
                    "agent_type": "apply",
                    "timeout_seconds": 1200,
                    "retry_limit": 1,
                },
            },
            "phase_transitions": {
                "clarify": {
                    "on_success": "generate",
                    "on_failure": "escalate",
                    "on_clarification_needed": "escalate",
                },
                "generate": {
                    "on_success": "format",
                    "on_failure": "escalate",
                    "on_retryable_error": "generate",
                },
                "format": {"on_success": "static_analysis", "on_failure": "escalate"},
                "static_analysis": {
                    "on_success": "init",
                    "on_failure": "escalate",
                    "on_violations": "escalate",
                },
                "init": {
                    "on_success": "validate",
                    "on_failure": "escalate",
                    "on_retryable_error": "init",
                },
                "validate": {
                    "on_success": "plan_review",
                    "on_failure": "escalate",
                    "on_retryable_error": "generate",
                },
                "plan_review": {"on_success": "apply_review", "on_failure": "escalate"},
                "apply_review": {
                    "on_success": "apply",
                    "on_failure": "escalate",
                    "on_approval_needed": "escalate",
                },
                "apply": {"on_success": "complete", "on_failure": "escalate"},
            },
            "global_timeout_seconds": 7200,
            "state_checkpoint_interval": 30,
            "enable_observability": True,
        }
        return PipelineConfiguration(**default_config)  # type: ignore[arg-type]

    def get_agent_config(self, agent_type: str) -> Optional[AgentConfiguration]:
        """Get configuration for a specific agent type."""
        return self.config.agent_configurations.get(agent_type)

    def get_phase_transition(self, phase: str, outcome: str) -> Optional[str]:
        """Get the next phase for a given phase and outcome."""
        phase_config = self.config.phase_transitions.get(phase, {})
        return phase_config.get(outcome)

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate the current configuration."""
        errors = []
        # Check that all required agents have configurations
        required_agents = ["clarify", "generate", "static_analysis", "command", "apply"]
        for agent in required_agents:
            if agent not in self.config.agent_configurations:
                errors.append(f"Missing configuration for required agent: {agent}")
        # Check phase transitions
        required_phases = [
            "clarify",
            "generate",
            "format",
            "static_analysis",
            "init",
            "validate",
            "plan_review",
            "apply_review",
            "apply",
        ]
        for phase in required_phases:
            if phase not in self.config.phase_transitions:
                errors.append(f"Missing transition rules for phase: {phase}")
        if errors:
            return {"valid": False, "errors": errors}
        return {"valid": True, "message": "Configuration is valid"}

    def update_configuration(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update the pipeline configuration."""
        try:
            # Update the configuration
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                elif key in self.config.agent_configurations:
                    self.config.agent_configurations[key].update(value)  # type: ignore[attr-defined]
                elif key in self.config.phase_transitions:
                    self.config.phase_transitions[key].update(value)
            # Validate the updated configuration
            validation = self.validate_configuration()
            if not validation["valid"]:
                return validation
            return {"success": True, "message": "Configuration updated successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_model_routing(self, agent_type: str) -> Dict[str, str]:
        """Get model routing configuration for an agent."""
        agent_config = self.get_agent_config(agent_type)
        if agent_config and agent_config.model_routing:
            return agent_config.model_routing
        # Default model routing
        return {"primary": "gpt-4o", "fallback": "gpt-4o"}

    def get_timeout(self, agent_type: str) -> int:
        """Get timeout configuration for an agent."""
        agent_config = self.get_agent_config(agent_type)
        if agent_config:
            return agent_config.timeout_seconds
        return 300  # Default 5 minutes

    def get_retry_limit(self, agent_type: str) -> int:
        """Get retry limit for an agent."""
        agent_config = self.get_agent_config(agent_type)
        if agent_config:
            return agent_config.retry_limit
        return 3  # Default 3 retries
