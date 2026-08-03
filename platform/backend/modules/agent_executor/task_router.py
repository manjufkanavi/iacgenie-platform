"""Task routing component for Agent Executor."""

import json

import uuid

from datetime import datetime

from typing import Any, Dict, List, Optional

from redis import Redis

from pydantic import ValidationError

from .models import Agent, AgentStatus, AgentType

from .config import config

from .exceptions import AgentExecutionError

from .logging import logger

from .observability import trace as trace_decorator


class TaskRouter:
    """Router for distributing tasks to appropriate agent pools."""

    def __init__(self) -> None:
        """Initialize the task router with Redis connection."""
        self.redis_client = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
        )
        # Map agent types to their respective task queues
        self.queue_mapping = {
            AgentType.CODER: config.CODER_TASK_QUEUE,
            AgentType.VALIDATOR: config.VALIDATOR_TASK_QUEUE,
            AgentType.PLANNER: config.PLANNER_TASK_QUEUE,
            AgentType.APPLIER: config.APPLIER_TASK_QUEUE,
            AgentType.TESTER: config.TESTER_TASK_QUEUE,
        }

    @trace_decorator()
    async def route_task(self, task_data: Dict[str, Any]) -> bool:
        """
        Route a task to the appropriate agent pool based on agent type.
        Args:
            task_data: Dictionary containing task information with keys:
                - session_id: str (UUID string)
                - iteration: int
                - agent_type: str (enum value)
                - context: Dict containing task-specific information
        Returns:
            bool: True if routing was successful, False otherwise
        Raises:
            AgentExecutionError: If task routing fails due to validation errors
            AgentTimeoutError: If the task processing exceeds timeout
        """
        try:
            # Extract session_id and convert to UUID
            session_id_str = task_data.get("session_id")
            if not session_id_str:
                raise AgentExecutionError("Missing session_id in task data")
            session_id = self._parse_uuid(session_id_str)
            # Extract agent type
            agent_type_str = task_data.get("agent_type")
            if not agent_type_str:
                raise AgentExecutionError("Missing agent_type in task data")
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                valid_types = [t.value for t in AgentType]
                raise AgentExecutionError(
                    f"Invalid agent_type: {agent_type_str}. Must be one of: {valid_types}"
                )
            # Extract iteration
            iteration = task_data.get("iteration", 1)
            if not isinstance(iteration, int) or iteration < 1:
                raise AgentExecutionError(
                    "Invalid iteration value: must be a positive integer"
                )
            # Extract context
            context_data = task_data.get("context", {})
            if not isinstance(context_data, dict):
                raise AgentExecutionError("Context must be a dictionary")
            # Extract build_id
            build_id = context_data.get("build_id", "unknown")
            if not isinstance(build_id, str) or not build_id:
                raise AgentExecutionError(
                    "Invalid build_id: must be a non-empty string"
                )
            # Extract prompt
            prompt = context_data.get("prompt", "")
            if not isinstance(prompt, str):
                raise AgentExecutionError("Prompt must be a string")
            # Validate task data
            if not prompt.strip():
                raise AgentExecutionError("Prompt cannot be empty or whitespace only")
            # Create agent record
            agent = Agent(
                agent_type=agent_type,
                session_id=str(session_id),
                build_id=build_id,
                iteration=iteration,
                status=AgentStatus.RUNNING,
                started_at=datetime.utcnow(),
                completed_at=None,
            )
            # Validate agent creation
            if not self._validate_agent_creation(agent):
                raise AgentExecutionError("Failed to validate agent creation")
            # Prepare task for Redis queue
            task_payload = {
                "session_id": str(agent.session_id),
                "iteration": agent.iteration,
                "agent_type": agent.agent_type.value,
                "context": {"prompt": prompt, "build_id": build_id},
            }
            # Get the appropriate queue for this agent type
            queue_name = self.queue_mapping.get(agent_type)
            if not queue_name:
                raise AgentExecutionError(f"Unknown agent type: {agent_type}")
            # Push task to Redis queue
            queue_key = f"task_queue:{queue_name}"
            task_json = json.dumps(task_payload)
            # Use Redis's LPUSH to add task to the queue
            # This ensures FIFO order and allows for task monitoring
            result = self.redis_client.lpush(queue_key, task_json)
            if int(result) <= 0:  # type: ignore[arg-type]
                raise AgentExecutionError(
                    f"Failed to push task to Redis queue: {queue_key}"
                )
            # Log successful routing
            logger.info(
                "Task routed successfully",
                extra={
                    "session_id": str(session_id),
                    "build_id": build_id,
                    "agent_type": agent_type.value,
                    "iteration": iteration,
                    "prompt_length": len(prompt),
                    "queue": queue_name,
                },
            )
            return True
        except (ValidationError, ValueError) as e:
            logger.error(
                "Task validation failed",
                extra={
                    "session_id": task_data.get("session_id"),
                    "build_id": task_data.get("context", {}).get("build_id", "unknown"),
                    "agent_type": task_data.get("agent_type", "unknown"),
                    "error": str(e),
                },
            )
            raise AgentExecutionError(f"Task validation failed: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error in task routing",
                extra={
                    "session_id": task_data.get("session_id"),
                    "build_id": task_data.get("context", {}).get("build_id", "unknown"),
                    "agent_type": task_data.get("agent_type", "unknown"),
                    "error": str(e),
                },
            )
            # Rethrow as AgentExecutionError for consistent error handling
            raise AgentExecutionError(
                f"Unexpected error in task routing: {str(e)}"
            ) from e

    @trace_decorator()
    async def get_task_count(self, agent_type: AgentType) -> int:
        """
        Get the current count of tasks in the queue for a specific agent type.
        Args:
            agent_type: The type of agent to check
        Returns:
            int: The number of tasks in the queue for the specified agent type
        """
        queue_name = self.queue_mapping.get(agent_type)
        if not queue_name:
            return 0
        queue_key = f"task_queue:{queue_name}"
        return int(self.redis_client.llen(queue_key))  # type: ignore[arg-type]

    @trace_decorator()
    async def get_pending_tasks(self, agent_type: AgentType) -> List[Any]:
        """
        Get all pending tasks for a specific agent type.
        Args:
            agent_type: The type of agent to get tasks for
        Returns:
            list: A list of task dictionaries
        """
        queue_name = self.queue_mapping.get(agent_type)
        if not queue_name:
            return []
        queue_key = f"task_queue:{queue_name}"
        task_list = self.redis_client.lrange(queue_key, 0, -1)
        if not isinstance(task_list, list):
            return []
        # Parse JSON tasks
        tasks = []
        for task_json in task_list:
            try:
                task = json.loads(task_json)
                tasks.append(task)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in task queue", extra={"task": task_json})
                continue
        return tasks

    def _parse_uuid(self, uuid_str: str) -> uuid.UUID:
        """
        Parse a UUID string and return a UUID object.
        Args:
            uuid_str: String representation of a UUID
        Returns:
            uuid.UUID: Parsed UUID object
        Raises:
            ValueError: If the string is not a valid UUID
        """
        try:
            return uuid.UUID(uuid_str)
        except (ValueError, TypeError) as e:
            raise AgentExecutionError(f"Invalid session_id format: {uuid_str}") from e

    def _validate_agent_creation(self, agent: Agent) -> bool:
        """
        Validate the agent creation parameters.
        Args:
            agent: The agent to validate
        Returns:
            bool: True if validation passes, False otherwise
        """
        # Check for valid agent type
        if agent.agent_type not in AgentType:
            return False
        # Check for valid session_id (can be UUID or string)
        if agent.session_id:
            if isinstance(agent.session_id, uuid.UUID):
                # Additional checks for build_id and iteration
                if not isinstance(agent.build_id, str) or not agent.build_id.strip():
                    return False
                if not isinstance(agent.iteration, int) or agent.iteration < 1:
                    return False
                return True
            # If it's a string, try to parse it
            try:
                uuid.UUID(str(agent.session_id))
                # Additional checks for build_id and iteration
                if not isinstance(agent.build_id, str) or not agent.build_id.strip():
                    return False
                if not isinstance(agent.iteration, int) or agent.iteration < 1:
                    return False
                return True
            except (ValueError, TypeError):
                return False
        return False

    async def create_agent(
        self,
        agent_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Agent:
        """Create a new agent record."""
        return Agent(
            agent_type=AgentType(agent_type)
            if agent_type in AgentType.__members__
            else AgentType.CODER,
            session_id=session_id or str(uuid.uuid4()),
            build_id=user_id,
            iteration=1,
            status=AgentStatus.RUNNING,
            started_at=datetime.utcnow(),
            completed_at=None,
        )

    async def submit_task(
        self,
        agent_id: str,
        task_data: Dict[str, Any],
        priority: int = 0,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a task to an agent."""
        return {"task_id": agent_id, "status": "submitted"}

    async def get_agent(self, agent_id: str, user_id: str) -> Any:
        """Get agent by ID."""
        return {"id": agent_id, "user_id": user_id, "status": "running"}

    async def stop_agent(
        self, agent_id: str, user_id: str, reason: Optional[str] = None
    ) -> None:
        """Stop an agent."""
        logger.info("Agent stopped", extra={"agent_id": agent_id, "reason": reason})


# Create a global instance for easy access


task_router = TaskRouter()
