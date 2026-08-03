"""Tool injection for Agent Executor."""

import os

from typing import Dict, Any, Optional

from .config import config

from .models import AgentType

from .exceptions import AgentExecutionError

from .observability import log_info, log_error

from .logging import logger

from .utils import create_session_workspace


class ToolInjector:
    """Manages secure tool injection for agent processes."""

    def __init__(self) -> None:
        self.tools: Dict[str, Any] = {}
        self._initialized = False
        self._tool_injection_timeout = config.TOOL_INJECTION_TIMEOUT

    async def inject_tools(self, agent_type: AgentType) -> Dict[str, Any]:
        """
        Inject required tools into an agent process via dependency injection.
        """
        try:
            # Set up environment for tool injection
            os.environ["AGENT_TYPE"] = agent_type.value
            # Create session workspace for the agent
            workspace_root = create_session_workspace()
            os.environ["WORKSPACE_ROOT"] = workspace_root
            tools = {}
            # Inject FileSystemTool
            filesystem_tool = await self._create_filesystem_tool(agent_type)
            if filesystem_tool:
                tools["filesystem_tool"] = filesystem_tool
            # Inject CommandTool
            command_tool = await self._create_command_tool(agent_type)
            if command_tool:
                tools["command_tool"] = command_tool
            # Inject LLMTool
            llm_tool = await self._create_llm_tool(agent_type)
            if llm_tool:
                tools["llm_tool"] = llm_tool
            # Inject SandboxTool
            sandbox_tool = await self._create_sandbox_tool(agent_type)
            if sandbox_tool:
                tools["sandbox_tool"] = sandbox_tool
            # Validate all tools were successfully created
            if not tools:
                raise AgentExecutionError("Failed to create any tools for agent type")
            # Log successful tool injection
            log_info(
                "Tools injected successfully",
                extra={
                    "agent_type": agent_type.value,
                    "tool_count": len(tools),
                    "tools": list(tools.keys()),
                },
            )
            self._initialized = True
            return tools
        except Exception as e:
            log_error(
                "Tool injection failed",
                extra={"agent_type": agent_type.value, "error": str(e)},
            )
            raise AgentExecutionError(f"Tool injection failed: {str(e)}") from e

    async def _create_filesystem_tool(
        self, agent_type: AgentType
    ) -> Optional[Dict[str, Any]]:
        """
        Create and configure FileSystemTool for an agent.
        """
        try:
            # Get workspace root from environment
            workspace_root = os.environ.get("WORKSPACE_ROOT", "/workspace/sandboxes")
            tool_config = {
                "name": "filesystem_tool",
                "description": "Secure file system operations for agent tasks",
                "allowed_operations": [
                    "read_file",
                    "write_file",
                    "list_directory",
                    "delete_file",
                ],
                "workspace_root": workspace_root,
            }
            return tool_config
        except Exception as e:
            logger.error(f"Failed to create filesystem tool: {str(e)}")
            return None

    async def _create_command_tool(
        self, agent_type: AgentType
    ) -> Optional[Dict[str, Any]]:
        """
        Create and configure CommandTool for an agent.
        """
        try:
            allowed_commands = config.ALLOWED_COMMANDS
            tool_config = {
                "name": "command_tool",
                "description": "Execute allowed commands in sandbox",
                "allowed_commands": allowed_commands,
                "execute_via": "docker_exec",
                "timeout_seconds": 30,
            }
            return tool_config
        except Exception as e:
            logger.error(f"Failed to create command tool: {str(e)}")
            return None

    async def _create_llm_tool(self, agent_type: AgentType) -> Optional[Dict[str, Any]]:
        """
        Create and configure LLMTool for an agent.
        """
        try:
            llm_proxy_url = config.LLM_PROXY_URL
            tool_config = {
                "name": "llm_tool",
                "description": "Call LLM Proxy for completions",
                "endpoint": llm_proxy_url,
                "timeout": 30,
            }
            return tool_config
        except Exception as e:
            logger.error(f"Failed to create LLM tool: {str(e)}")
            return None

    async def _create_sandbox_tool(
        self, agent_type: AgentType
    ) -> Optional[Dict[str, Any]]:
        """
        Create and configure SandboxTool for an agent.
        """
        try:
            sandbox_manager_url = config.SANDBOX_MANAGER_URL
            tool_config = {
                "name": "sandbox_tool",
                "description": "Interact with Sandbox Manager",
                "endpoint": sandbox_manager_url,
                "timeout": 30,
            }
            return tool_config
        except Exception as e:
            logger.error(f"Failed to create sandbox tool: {str(e)}")
            return None
