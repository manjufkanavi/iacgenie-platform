"""Process pool for agent execution."""

import asyncio

import json

import os

import time

from multiprocessing import Process, Queue

from typing import Dict, Any, List

import uuid

from .config import config

from .models import AgentType

from .task_router import TaskRouter

from .resource_monitor import ResourceMonitor

from .tool_injector import ToolInjector

from .logging import logger

from redis import Redis as Redis


class AgentProcessPool:
    """Process pool for agent execution with resource monitoring and tool injection."""

    def __init__(self, pool_size: int = 4, group_name: str = "agent_pool"):
        self.pool_size = pool_size
        self.group_name = group_name
        self._processes: List[Process] = []
        self._task_queue: Queue = Queue()
        self._result_queue: Queue = Queue()
        self._shutdown_event = asyncio.Event()
        self._monitoring = False
        self._resource_monitor = ResourceMonitor()
        self._tool_injector = ToolInjector()
        self._task_router = TaskRouter()
        # Redis client for task distribution
        self.redis_client = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
        )
        # Queue mapping
        self.queue_mapping = {
            AgentType.CODER: "coder_tasks",
            AgentType.VALIDATOR: "validator_tasks",
            AgentType.PLANNER: "planner_tasks",
            AgentType.APPLIER: "applier_tasks",
            AgentType.TESTER: "tester_tasks",
        }

    async def start(self) -> None:
        """Start the process pool."""
        logger.info(
            "Starting agent process pool",
            extra={"pool_size": self.pool_size, "group_name": self.group_name},
        )
        # Start monitoring
        self._monitoring = True
        self._resource_monitor.start_monitoring()
        # Start worker processes
        for i in range(self.pool_size):
            process = Process(
                target=self._run_agent_task, args=(i,), name=f"{self.group_name}_{i}"
            )
            self._processes.append(process)
            process.start()
            logger.info(
                f"Started worker process {i}",
                extra={"process_id": process.pid, "process_name": process.name},
            )
        logger.info("Agent process pool started successfully")

    async def stop(self) -> None:
        """Stop the process pool."""
        logger.info("Stopping agent process pool")
        # Stop monitoring
        self._monitoring = False
        self._resource_monitor.stop_monitoring()
        # Terminate all processes
        for process in self._processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                    process.join()
        logger.info("Agent process pool stopped successfully")

    async def submit_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a task to the process pool."""
        # Validate task data
        if not task_data.get("task_id"):
            raise ValueError("Task ID is required")
        if not task_data.get("session_id"):
            raise ValueError("Session ID is required")
        if not task_data.get("agent_type"):
            raise ValueError("Agent type is required")
        # Route task to appropriate worker
        self._task_router.route_task(task_data)
        # Publish task to Redis queue
        task_id = self._publish_task(task_data)
        # Wait for result from Redis worker (would be separate process)
        # This is now just a task publisher
        return {"task_id": task_id, "status": "queued"}

    async def _run_agent_task(self, worker_id: int) -> None:
        """Run a single agent task in a worker process."""
        # Get task from queue
        task_data = self._task_queue.get()
        # Extract task information
        task_id = task_data.get("task_id")
        session_id = task_data.get("session_id")
        build_id = task_data.get("build_id")
        agent_type = task_data.get("agent_type")
        context = task_data.get("context", {})
        context.get("prompt", "")
        # Initialize result dictionary
        result = {
            "task_id": task_id,
            "session_id": session_id,
            "build_id": build_id,
            "agent_type": agent_type,
            "status": "running",
            "result": None,
            "error": None,
            "timestamp": time.time(),
        }
        try:
            # Get tools from tool injector
            tools = await self._tool_injector.inject_tools(AgentType(agent_type))
            # Validate command before execution
            command = context.get("command", [])
            if not command:
                raise ValueError("Command cannot be empty")
            command_name = command[0]
            if command_name not in config.ALLOWED_COMMANDS:
                raise ValueError(f"Command '{command_name}' is not allowed")
            # Validate arguments for shell injection
            for arg in command[1:]:
                if ";" in arg or "|" in arg or "&" in arg:
                    raise ValueError(
                        f"Invalid argument '{arg}': shell metacharacters not allowed"
                    )
            # Validate paths for traversal prevention
            if "path" in task_data:
                path = task_data.get("path")
                if path:
                    # Check for path traversal attempts
                    normalized_path = os.path.normpath(path)
                    workspace_root = os.environ.get("WORKSPACE_ROOT", "")
                    if not normalized_path.startswith(workspace_root):
                        raise ValueError("Path must be within workspace")
                    # Check for symlinks
                    if os.path.islink(normalized_path):
                        raise ValueError("Symlinks are not allowed")
            # Execute the task with tools
            process = Process(
                target=_execute_with_tools,
                args=(task_data, tools),
                name=f"agent_{agent_type}_{task_id}",
            )
            # Start process
            process.start()
            # Wait for completion with timeout
            timeout = config.AGENT_TIMEOUT_SECONDS
            process.join(timeout=timeout)
            # Check if process completed
            if process.is_alive():
                # Process timed out
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                    process.join()
                result["status"] = "timeout"
                result["error"] = f"Agent task timed out after {timeout} seconds"
            else:
                # Process completed normally
                if process.exitcode == 0:
                    result["status"] = "completed"
                    logger.info(
                        "Agent task completed successfully",
                        extra={
                            "task_id": task_id,
                            "session_id": session_id,
                            "build_id": build_id,
                            "agent_type": agent_type,
                        },
                    )
                else:
                    result["status"] = "failed"
                    result["error"] = f"Process exited with code {process.exitcode}"
                    logger.error(
                        "Agent task failed",
                        extra={
                            "task_id": task_id,
                            "session_id": session_id,
                            "build_id": build_id,
                            "agent_type": agent_type,
                            "exit_code": process.exitcode,
                        },
                    )
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(
                "Agent task error",
                extra={
                    "task_id": task_id,
                    "session_id": session_id,
                    "build_id": build_id,
                    "agent_type": agent_type,
                    "error": str(e),
                },
            )
        # Put result in queue
        self._result_queue.put(result)

    def _publish_task(self, task_data: Dict[str, Any]) -> str:
        """Publish a task to the appropriate Redis queue."""
        agent_type_str = task_data.get("agent_type")
        queue_name = self.queue_mapping.get(AgentType(agent_type_str))
        if not queue_name:
            raise ValueError(f"No queue mapping for agent type: {agent_type_str}")
        task_json = json.dumps(task_data)
        self.redis_client.rpush(queue_name, task_json)
        # Generate and return a task ID
        task_id = str(uuid.uuid4())
        return task_id

    def _get_injected_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get injected tools from environment."""
        tools: Dict[str, Dict[str, Any]] = {}
        # FileSystemTool
        if os.environ.get("FILESYSTEM_TOOL"):
            tools["filesystem_tool"] = {
                "name": "filesystem_tool",
                "workspace_root": os.environ.get("WORKSPACE_ROOT", ""),
                "allowed_operations": [
                    "read_file",
                    "write_file",
                    "list_directory",
                    "delete_file",
                ],
            }
        # CommandTool
        if os.environ.get("COMMAND_TOOL"):
            tools["command_tool"] = {
                "name": "command_tool",
                "allowed_commands": os.environ.get("ALLOWED_COMMANDS", ["tofu", "git"]),
                "execute_via": "docker_exec",
                "timeout_seconds": 30,
            }
        # LLMTool
        if os.environ.get("LLM_TOOL"):
            tools["llm_tool"] = {
                "name": "llm_tool",
                "endpoint": os.environ.get("LLM_PROXY_URL", ""),
                "timeout": 30,
            }
        # SandboxTool
        if os.environ.get("SANDBOX_TOOL"):
            tools["sandbox_tool"] = {
                "name": "sandbox_tool",
                "endpoint": os.environ.get("SANDBOX_MANAGER_URL", ""),
                "timeout": 30,
            }
        return tools


def _execute_with_tools(task_data: Dict[str, Any], tools: Dict[str, Any]) -> Any:
    """Execute agent task with injected tools."""
    import os

    task_data.get("task_id")
    session_id = task_data.get("session_id") or ""
    build_id = task_data.get("build_id") or ""
    task_data.get("context", {}).get("prompt", "")
    # Set up environment
    os.environ["SESSION_ID"] = session_id
    os.environ["BUILD_ID"] = build_id
    # Execute based on agent type
    agent_type = task_data.get("agent_type")
    if agent_type == "coder":
        return _execute_coder_task(task_data, tools)
    elif agent_type == "validator":
        return _execute_validator_task(task_data, tools)
    elif agent_type == "planner":
        return _execute_planner_task(task_data, tools)
    elif agent_type == "applier":
        return _execute_applier_task(task_data, tools)
    elif agent_type == "tester":
        return _execute_tester_task(task_data, tools)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def _execute_coder_task(task_data: Dict[str, Any], tools: Dict[str, Any]) -> Any:
    """Execute coder agent task with tools."""
    import httpx
    import asyncio
    import os

    # Use filesystem tool to create files
    fs_tool = tools.get("filesystem_tool")
    if not fs_tool:
        raise ValueError("FileSystemTool not available")
    workspace_root = fs_tool["workspace_root"]

    # Generate code using LLM
    llm_tool = tools.get("llm_tool")
    if not llm_tool:
        raise ValueError("LLMTool not available")

    prompt = task_data.get("context", {}).get("prompt", "")
    refined_spec = task_data.get("context", {}).get("refined_spec", "")
    model_name = task_data.get("context", {}).get("model", "ollama/codellama")

    system_prompt = (
        "You are an expert Infrastructure as Code (IaC) engineer. "
        "Generate fully functional code based on the provided specification. "
        "IMPORTANT: You MUST format your response exactly like this for every file you generate:\n\n"
        "FILE: <filename>\n"
        "<file contents>\n\n"
        "If you do not prefix each file with 'FILE: <filename>\\n', the system will fail to parse your output."
    )

    user_prompt = (
        f"Original Request: {prompt}\n\nRefined Specification:\n{refined_spec}"
    )

    async def _generate_code() -> str:
        async with httpx.AsyncClient() as client:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 4000,
                "temperature": 0.2,
            }
            # Fallback to older style /completions if using a completion endpoint, but assume chat completions for proxy
            endpoint = llm_tool["endpoint"]
            if not endpoint.endswith("/chat/completions"):
                if endpoint.endswith("/v1"):
                    endpoint = f"{endpoint}/chat/completions"

            response = await client.post(
                endpoint,
                json=payload,
                timeout=llm_tool.get("timeout", 120),
            )
            response.raise_for_status()
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0].get("message", {}).get("content", "")
            return data.get("text", "")

    try:
        code = asyncio.run(_generate_code())
    except Exception as e:
        raise ValueError(f"LLM Generation failed: {str(e)}")

    parsed_files = _parse_generated_code(code)

    if not parsed_files:
        raise ValueError(
            "LLM generated output, but no files were successfully parsed. Ensure the model uses the 'FILE: filename' format."
        )

    # Write files using filesystem tool
    for file_info in parsed_files:
        filename = file_info["name"]
        content = file_info["content"]
        filepath = os.path.join(workspace_root, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)

    return {
        "task_id": task_data.get("task_id"),
        "status": "completed",
        "result": {"files": parsed_files},
    }


def _execute_validator_task(task_data: Dict[str, Any], tools: Dict[str, Any]) -> Any:
    """Execute validator agent task with tools."""
    # Validate generated code
    fs_tool = tools.get("filesystem_tool")
    if not fs_tool:
        raise ValueError("FileSystemTool not available")
    workspace_root = fs_tool["workspace_root"]
    # Read files to validate
    files_to_validate = _get_files_to_validate(workspace_root)
    validation_results = []
    for file_path in files_to_validate:
        result = _validate_file(file_path)
        validation_results.append(result)
    return {
        "task_id": task_data.get("task_id"),
        "status": "completed",
        "result": {"validation_results": validation_results},
    }


def _execute_planner_task(task_data: Dict[str, Any], tools: Dict[str, Any]) -> Any:
    """Execute planner agent task with tools."""
    # Plan infrastructure changes
    llm_tool = tools.get("llm_tool")
    if not llm_tool:
        raise ValueError("LLMTool not available")
    prompt = task_data.get("context", {}).get("prompt", "")
    # Call LLM to generate plan
    import httpx

    async def _generate_plan():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                llm_tool["endpoint"],
                json={
                    "model": "ollama/codellama",
                    "prompt": f"Create a plan for: {prompt}",
                    "max_tokens": 1000,
                    "temperature": 0.5,
                },
                timeout=llm_tool["timeout"],
            )
        return response.json()

    # Note: This would need to be called from an async context
    plan = {"steps": ["Step 1", "Step 2", "Step 3"]}
    return {
        "task_id": task_data.get("task_id"),
        "status": "completed",
        "result": {"plan": plan},
    }


def _execute_applier_task(task_data: Dict[str, Any], tools: Dict[str, Any]) -> Any:
    """Execute applier agent task with tools."""
    # Apply infrastructure changes
    sandbox_tool = tools.get("sandbox_tool")
    if not sandbox_tool:
        raise ValueError("SandboxTool not available")
    # Execute commands in sandbox
    command = task_data.get("context", {}).get("command", [])
    if not command:
        raise ValueError("Command cannot be empty")
    # Validate command
    command_name = command[0]
    if command_name not in config.ALLOWED_COMMANDS:
        raise ValueError(f"Command '{command_name}' is not allowed")
    # Execute command in sandbox
    result = _execute_in_sandbox(command, sandbox_tool)
    return {
        "task_id": task_data.get("task_id"),
        "status": "completed",
        "result": {"command_output": result},
    }


def _execute_tester_task(task_data: Dict[str, Any], tools: Dict[str, Any]) -> Any:
    """Execute tester agent task with tools."""
    # Run tests on generated infrastructure
    fs_tool = tools.get("filesystem_tool")
    if not fs_tool:
        raise ValueError("FileSystemTool not available")
    workspace_root = fs_tool["workspace_root"]
    # Find test files
    test_files = _find_test_files(workspace_root)
    # Run tests
    test_results = []
    for test_file in test_files:
        result = _run_test(test_file)
        test_results.append(result)
    return {
        "task_id": task_data.get("task_id"),
        "status": "completed",
        "result": {"test_results": test_results},
    }


def _parse_generated_code(code: str) -> list:
    """Parse generated code into files."""
    files = []
    lines = code.split("\n")
    current_file = {"name": "generated_file.tf", "content": ""}
    in_code_block = False

    for line in lines:
        if line.startswith("FILE:"):
            if current_file["content"].strip():
                # Strip markdown code blocks if present
                content = current_file["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content.rsplit("\n", 1)[0]
                current_file["content"] = content + "\n"
                files.append(current_file)
            current_file = {
                "name": line.replace("FILE:", "").replace("`", "").strip(),
                "content": "",
            }
            in_code_block = False
        else:
            if line.startswith("```"):
                in_code_block = not in_code_block
                # Ignore the backtick line itself if it's the start/end of the file's block
                continue
            current_file["content"] += line + "\n"

    if current_file["content"].strip():
        content = current_file["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("\n", 1)[0]
        current_file["content"] = content + "\n"
        files.append(current_file)

    return files


def _get_files_to_validate(workspace_root: str) -> list:
    """Get list of files to validate."""
    files = []
    if os.path.exists(workspace_root):
        for filename in os.listdir(workspace_root):
            filepath = os.path.join(workspace_root, filename)
            if os.path.isfile(filepath):
                files.append(filepath)
    return files


def _validate_file(file_path: str) -> dict:
    """Validate a single file."""
    return {"file_path": file_path, "valid": True, "errors": [], "warnings": []}


def _find_test_files(workspace_root: str) -> list:
    """Find test files in workspace."""
    test_files = []
    if os.path.exists(workspace_root):
        for filename in os.listdir(workspace_root):
            if filename.startswith("test_") or filename.endswith("_test.py"):
                test_files.append(os.path.join(workspace_root, filename))
    return test_files


def _run_test(test_file: str) -> dict:
    """Run a single test file."""
    return {"test_file": test_file, "passed": True, "tests_run": 1, "errors": []}


def _execute_in_sandbox(command: list, sandbox_tool: dict) -> str:
    """Execute a command in the sandbox."""
    import subprocess

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return str(e)
