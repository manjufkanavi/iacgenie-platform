"""Main entry point for Agent Executor."""

import asyncio

import signal

import sys

from typing import Any, Optional

from .config import AgentExecutorConfig

from .models import AgentType, Agent

from .exceptions import AgentExecutionError

from .logging import logger, setup_logging

from .observability import setup_tracing

from .utils import create_session_workspace, generate_task_id

from .task_router import TaskRouter

from .process_pool import AgentProcessPool

from .tool_injector import ToolInjector

from .resource_monitor import ResourceMonitor


class AgentExecutor:
    """Main agent executor class that manages all agent processes."""

    def __init__(self, config: Optional[AgentExecutorConfig] = None):
        self.config = config or AgentExecutorConfig()
        self.task_router = TaskRouter()
        self.process_pool = AgentProcessPool(pool_size=self.config.MAX_AGENT_PROCESSES)
        self.tool_injector = ToolInjector()
        self.resource_monitor = ResourceMonitor()
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the agent executor."""
        logger.info("Starting Agent Executor")
        # Setup logging
        setup_logging()
        # Setup tracing
        setup_tracing()
        # Validate configuration
        validation_result = self.config.validate_configuration()
        if not validation_result["valid"]:
            logger.error(
                "Configuration validation failed",
                extra={"issues": validation_result["issues"]},
            )
            raise AgentExecutionError(
                f"Configuration validation failed: {validation_result['issues']}"
            )
        # Start the process pool
        await self.process_pool.start()
        self._running = True
        logger.info("Agent Executor started successfully")

    async def stop(self) -> None:
        """Stop the agent executor."""
        logger.info("Stopping Agent Executor")
        # Stop the process pool
        await self.process_pool.stop()
        self._running = False
        self._shutdown_event.set()
        logger.info("Agent Executor stopped")

    async def submit_agent_task(
        self,
        agent_type: AgentType,
        session_id: str,
        build_id: str,
        iteration: int = 1,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Submit a task to be executed by an agent.
        Args:
            agent_type: Type of agent to execute the task
            session_id: UUID of the associated session
            build_id: Build identifier for the task
            iteration: Iteration number for the task
            context: Additional context for the task
        Returns:
            dict: Task submission result
        """
        if context is None:
            context = {}
        # Create agent record
        agent = Agent(  # type: ignore[call-arg]
            agent_type=agent_type,
            session_id=session_id,
            build_id=build_id,
            iteration=iteration,
        )
        # Start the agent
        agent.start()
        # Prepare task data
        task_data = {
            "task_id": generate_task_id(),
            "session_id": str(agent.session_id),
            "iteration": agent.iteration,
            "agent_type": agent.agent_type.value,
            "context": {"prompt": context.get("prompt", ""), "build_id": build_id},
        }
        # Route and submit task
        await self.task_router.route_task(task_data)
        result = await self.process_pool.submit_task(task_data)
        return result

    async def run_agent_task(
        self,
        agent_type: AgentType,
        session_id: str,
        build_id: str,
        iteration: int = 1,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Run an agent task synchronously (for testing/development).
        Args:
            agent_type: Type of agent to execute the task
            session_id: UUID of the associated session
            build_id: Build identifier for the task
            iteration: Iteration number for the task
            context: Additional context for the task
        Returns:
            dict: Task execution result
        """
        if context is None:
            context = {}
        # Create workspace for the agent
        workspace = create_session_workspace(session_id)
        logger.info(
            "Created workspace for agent",
            extra={"session_id": session_id, "workspace": workspace},
        )
        # Submit task
        result = await self.submit_agent_task(
            agent_type=agent_type,
            session_id=session_id,
            build_id=build_id,
            iteration=iteration,
            context=context,
        )
        return result


async def main() -> None:
    # Create executor instance
    executor = AgentExecutor()
    # Setup signal handlers for graceful shutdown
    asyncio.get_event_loop()

    def signal_handler(sig: Any, frame: Any) -> None:
        logger.info("Received shutdown signal")
        asyncio.create_task(executor.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        # Start the executor
        await executor.start()
        # Keep running until shutdown
        while executor._running:
            await asyncio.sleep(1)
    except AgentExecutionError as e:
        logger.error(
            "Agent execution error", extra={"error": str(e), "error_code": e.error_code}
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error", extra={"error": str(e)})
        sys.exit(1)
    finally:
        await executor.stop()


if __name__ == "__main__":
    asyncio.run(main())
