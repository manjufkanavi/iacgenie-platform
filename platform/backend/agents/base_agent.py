from abc import ABC, abstractmethod

from typing import Optional, Dict, Any

from models.iac_state import IaCState

from models.error_classes import ErrorClass

import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents in the agentic pipeline."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.state: Optional[IaCState] = None

    @abstractmethod
    async def initialize(self, state: IaCState) -> bool:
        """Initialize the agent with the current state."""
        self.state = state
        return True

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the agent's main logic.
        Returns:
            Dictionary containing:
            - success: bool indicating success
            - result: any result data
            - next_phase: optional next phase to transition to
            - error: optional error details
            - error_class: optional ErrorClass
        """
        pass

    @abstractmethod
    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Handle errors that occur during execution.
        Returns:
            Dictionary containing error handling result with:
            - error_class: ErrorClass
            - message: error message
            - can_retry: bool
            - retry_feedback: optional feedback for retry
        """
        pass

    async def cleanup(self) -> None:
        """Clean up any resources used by the agent."""
        pass

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with agent context."""
        context = {
            "agent": self.agent_name,
            "session_id": self.state.session_id if self.state else "no_state",
            "phase": self.state.current_phase.value if self.state else "unknown",
        }
        if level == "info":
            logger.info(message, extra=context)
        elif level == "warning":
            logger.warning(message, extra=context)
        elif level == "error":
            logger.error(message, extra=context)
        else:
            logger.debug(message, extra=context)

    def add_state_message(self, role: str, content: str) -> None:
        """Add a message to the state's conversation history."""
        if self.state:
            self.state.add_message(role, content)

    def classify_error(self, exception: Exception) -> ErrorClass:
        """
        Classify an exception into an ErrorClass.
        Can be overridden by specific agents for custom classification.
        """
        error_type = type(exception).__name__
        # Default classification logic
        if "Timeout" in error_type or "Connection" in error_type:
            return ErrorClass.RETRYABLE
        elif "Validation" in error_type or "Syntax" in error_type:
            return ErrorClass.CLARIFICATION
        elif "Permission" in error_type or "Access" in error_type:
            return ErrorClass.HUMAN_REQUIRED
        else:
            return ErrorClass.FATAL
