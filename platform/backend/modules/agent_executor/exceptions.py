"""Custom exceptions for Agent Executor."""

import logging

from typing import Optional

# Create a logger for this module

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """Base exception for agent execution failures."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "AGENT_EXECUTION_ERROR"
        self.details = details or {}
        logger.error(f"AgentExecutionError: {message}", extra=self.details)

    def __str__(self):
        return f"AgentExecutionError: {self.message}"


class AgentTimeoutError(AgentExecutionError):
    """Exception raised when an agent task exceeds its timeout."""

    def __init__(
        self, message: str = "Agent task timed out", error_code: str = "AGENT_TIMEOUT"
    ):
        super().__init__(message, error_code)


class AgentResourceExceededError(AgentExecutionError):
    """Exception raised when an agent exceeds its resource limits."""

    def __init__(
        self,
        message: str = "Agent resource limits exceeded",
        error_code: str = "AGENT_RESOURCE_EXCEEDED",
    ):
        super().__init__(message, error_code)


class AgentConfigurationError(AgentExecutionError):
    """Exception raised when agent configuration is invalid."""

    def __init__(
        self,
        message: str = "Invalid agent configuration",
        error_code: str = "AGENT_CONFIG_ERROR",
    ):
        super().__init__(message, error_code)


class AgentToolInjectionError(AgentExecutionError):
    """Exception raised when tool injection fails."""

    def __init__(
        self,
        message: str = "Tool injection failed",
        error_code: str = "AGENT_TOOL_INJECTION_ERROR",
    ):
        super().__init__(message, error_code)


class AgentProcessError(AgentExecutionError):
    """Exception raised when agent process management fails."""

    def __init__(
        self,
        message: str = "Agent process management failed",
        error_code: str = "AGENT_PROCESS_ERROR",
    ):
        super().__init__(message, error_code)


class AgentResourceMonitorError(AgentExecutionError):
    """Exception raised when resource monitoring fails."""

    def __init__(
        self,
        message: str = "Resource monitoring failed",
        error_code: str = "AGENT_RESOURCE_MONITOR_ERROR",
    ):
        super().__init__(message, error_code)


class AgentTracingError(AgentExecutionError):
    """Exception raised when tracing fails."""

    def __init__(
        self, message: str = "Tracing failed", error_code: str = "AGENT_TRACING_ERROR"
    ):
        super().__init__(message, error_code)


# Define a custom exception for invalid agent type


class InvalidAgentTypeError(AgentExecutionError):
    """Exception raised when an invalid agent type is specified."""

    def __init__(self, agent_type: str, valid_types: list):
        message = f"Invalid agent type: {agent_type}. Must be one of: {valid_types}"
        super().__init__(message, "INVALID_AGENT_TYPE")


# Define a custom exception for invalid task data


class InvalidTaskDataError(AgentExecutionError):
    """Exception raised when task data is invalid."""

    def __init__(
        self, message: str = "Invalid task data", error_code: str = "INVALID_TASK_DATA"
    ):
        super().__init__(message, error_code)


# Define a custom exception for invalid session ID


class InvalidSessionIdError(AgentExecutionError):
    """Exception raised when session ID is invalid."""

    def __init__(self, session_id: str, error: str = "Invalid session ID format"):
        message = f"Invalid session ID: {session_id}. {error}"
        super().__init__(message, "INVALID_SESSION_ID")


# Define a custom exception for invalid build ID


class InvalidBuildIdError(AgentExecutionError):
    """Exception raised when build ID is invalid."""

    def __init__(self, build_id: str, error: str = "Invalid build ID format"):
        message = f"Invalid build ID: {build_id}. {error}"
        super().__init__(message, "INVALID_BUILD_ID")


# Define a custom exception for invalid prompt


class InvalidPromptError(AgentExecutionError):
    """Exception raised when prompt is invalid."""

    def __init__(self, prompt: str, error: str = "Invalid prompt format"):
        message = f"Invalid prompt: {prompt}. {error}"
        super().__init__(message, "INVALID_PROMPT")


# Define a custom exception for invalid tool configuration


class InvalidToolConfigurationError(AgentExecutionError):
    """Exception raised when tool configuration is invalid."""

    def __init__(self, tool_name: str, error: str = "Invalid tool configuration"):
        message = f"Invalid tool configuration for {tool_name}: {error}"
        super().__init__(message, "INVALID_TOOL_CONFIGURATION")


# Define a custom exception for invalid command


class InvalidCommandError(AgentExecutionError):
    """Exception raised when command is invalid."""

    def __init__(self, command: str, error: str = "Invalid command"):
        message = f"Invalid command: {command}. {error}"
        super().__init__(message, "INVALID_COMMAND")


# Define a custom exception for invalid argument


class InvalidArgumentError(AgentExecutionError):
    """Exception raised when argument is invalid."""

    def __init__(self, argument: str, error: str = "Invalid argument"):
        message = f"Invalid argument: {argument}. {error}"
        super().__init__(message, "INVALID_ARGUMENT")


# Define a custom exception for invalid file operation


class InvalidFileOperationError(AgentExecutionError):
    """Exception raised when file operation is invalid."""

    def __init__(self, operation: str, error: str = "Invalid file operation"):
        message = f"Invalid file operation: {operation}. {error}"
        super().__init__(message, "INVALID_FILE_OPERATION")


# Define a custom exception for invalid directory


class InvalidDirectoryError(AgentExecutionError):
    """Exception raised when directory is invalid."""

    def __init__(self, directory: str, error: str = "Invalid directory"):
        message = f"Invalid directory: {directory}. {error}"
        super().__init__(message, "INVALID_DIRECTORY")


# Define a custom exception for invalid file path


class InvalidFilePathError(AgentExecutionError):
    """Exception raised when file path is invalid."""

    def __init__(self, file_path: str, error: str = "Invalid file path"):
        message = f"Invalid file path: {file_path}. {error}"
        super().__init__(message, "INVALID_FILE_PATH")


# Define a custom exception for invalid file size


class InvalidFileSizeError(AgentExecutionError):
    """Exception raised when file size is invalid."""

    def __init__(self, file_size: int, error: str = "Invalid file size"):
        message = f"Invalid file size: {file_size}. {error}"
        super().__init__(message, "INVALID_FILE_SIZE")


# Define a custom exception for invalid file extension


class InvalidFileExtensionError(AgentExecutionError):
    """Exception raised when file extension is invalid."""

    def __init__(self, file_extension: str, error: str = "Invalid file extension"):
        message = f"Invalid file extension: {file_extension}. {error}"
        super().__init__(message, "INVALID_FILE_EXTENSION")


# Define a custom exception for invalid command argument


class InvalidCommandArgumentError(AgentExecutionError):
    """Exception raised when command argument is invalid."""

    def __init__(self, argument: str, error: str = "Invalid command argument"):
        message = f"Invalid command argument: {argument}. {error}"
        super().__init__(message, "INVALID_COMMAND_ARGUMENT")


# Define a custom exception for invalid LLM API response


class InvalidLLMResponseError(AgentExecutionError):
    """Exception raised when LLM API response is invalid."""

    def __init__(self, response: str, error: str = "Invalid LLM API response"):
        message = f"Invalid LLM API response: {response}. {error}"
        super().__init__(message, "INVALID_LLM_RESPONSE")


# Define a custom exception for invalid sandbox operation


class InvalidSandboxOperationError(AgentExecutionError):
    """Exception raised when sandbox operation is invalid."""

    def __init__(self, operation: str, error: str = "Invalid sandbox operation"):
        message = f"Invalid sandbox operation: {operation}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION")


# Define a custom exception for invalid sandbox API response


class InvalidSandboxResponseError(AgentExecutionError):
    """Exception raised when sandbox API response is invalid."""

    def __init__(self, response: str, error: str = "Invalid sandbox API response"):
        message = f"Invalid sandbox API response: {response}. {error}"
        super().__init__(message, "INVALID_SANDBOX_RESPONSE")


# Define a custom exception for invalid sandbox configuration


class InvalidSandboxConfigurationError(AgentExecutionError):
    """Exception raised when sandbox configuration is invalid."""

    def __init__(
        self, sandbox_config: dict, error: str = "Invalid sandbox configuration"
    ):
        message = f"Invalid sandbox configuration: {sandbox_config}. {error}"
        super().__init__(message, "INVALID_SANDBOX_CONFIGURATION")


# Define a custom exception for invalid sandbox resource limit


class InvalidSandboxResourceLimitError(AgentExecutionError):
    """Exception raised when sandbox resource limit is invalid."""

    def __init__(self, limit: str, error: str = "Invalid sandbox resource limit"):
        message = f"Invalid sandbox resource limit: {limit}. {error}"
        super().__init__(message, "INVALID_SANDBOX_RESOURCE_LIMIT")


# Define a custom exception for invalid sandbox operation timeout


class InvalidSandboxOperationTimeoutError(AgentExecutionError):
    """Exception raised when sandbox operation timeout is invalid."""

    def __init__(self, timeout: int, error: str = "Invalid sandbox operation timeout"):
        message = f"Invalid sandbox operation timeout: {timeout}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_TIMEOUT")


# Define a custom exception for invalid sandbox operation retry count


class InvalidSandboxOperationRetryCountError(AgentExecutionError):
    """Exception raised when sandbox operation retry count is invalid."""

    def __init__(
        self, retry_count: int, error: str = "Invalid sandbox operation retry count"
    ):
        message = f"Invalid sandbox operation retry count: {retry_count}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_RETRY_COUNT")


# Define a custom exception for invalid sandbox operation result


class InvalidSandboxOperationResultError(AgentExecutionError):
    """Exception raised when sandbox operation result is invalid."""

    def __init__(self, result: str, error: str = "Invalid sandbox operation result"):
        message = f"Invalid sandbox operation result: {result}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_RESULT")


# Define a custom exception for invalid sandbox operation status


class InvalidSandboxOperationStatusError(AgentExecutionError):
    """Exception raised when sandbox operation status is invalid."""

    def __init__(self, status: str, error: str = "Invalid sandbox operation status"):
        message = f"Invalid sandbox operation status: {status}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_STATUS")


# Define a custom exception for invalid sandbox operation error


class InvalidSandboxOperationErrorError(AgentExecutionError):
    """Exception raised when sandbox operation error is invalid."""

    def __init__(self, error: str, error_msg: str = "Invalid sandbox operation error"):
        message = f"Invalid sandbox operation error: {error}. {error_msg}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR")


# Define a custom exception for invalid sandbox operation details


class InvalidSandboxOperationDetailsError(AgentExecutionError):
    """Exception raised when sandbox operation details are invalid."""

    def __init__(self, details: dict, error: str = "Invalid sandbox operation details"):
        message = f"Invalid sandbox operation details: {details}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_DETAILS")


# Define a custom exception for invalid sandbox operation response


class InvalidSandboxOperationResponseError(AgentExecutionError):
    """Exception raised when sandbox operation response is invalid."""

    def __init__(
        self, response: str, error: str = "Invalid sandbox operation response"
    ):
        message = f"Invalid sandbox operation response: {response}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_RESPONSE")


# Define a custom exception for invalid sandbox operation log


class InvalidSandboxOperationLogError(AgentExecutionError):
    """Exception raised when sandbox operation log is invalid."""

    def __init__(self, log: str, error: str = "Invalid sandbox operation log"):
        message = f"Invalid sandbox operation log: {log}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_LOG")


# Define a custom exception for invalid sandbox operation status code


class InvalidSandboxOperationStatusCodeError(AgentExecutionError):
    """Exception raised when sandbox operation status code is invalid."""

    def __init__(
        self, status_code: int, error: str = "Invalid sandbox operation status code"
    ):
        message = f"Invalid sandbox operation status code: {status_code}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_STATUS_CODE")


# Define a custom exception for invalid sandbox operation error code


class InvalidSandboxOperationErrorCodeError(AgentExecutionError):
    """Exception raised when sandbox operation error code is invalid."""

    def __init__(
        self, error_code: str, error: str = "Invalid sandbox operation error code"
    ):
        message = f"Invalid sandbox operation error code: {error_code}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_CODE")


# Define a custom exception for invalid sandbox operation error message


class InvalidSandboxOperationErrorMessageError(AgentExecutionError):
    """Exception raised when sandbox operation error message is invalid."""

    def __init__(
        self, error_message: str, error: str = "Invalid sandbox operation error message"
    ):
        message = f"Invalid sandbox operation error message: {error_message}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_MESSAGE")


# Define a custom exception for invalid sandbox operation error details


class InvalidSandboxOperationErrorDetailsError(AgentExecutionError):
    """Exception raised when sandbox operation error details are invalid."""

    def __init__(
        self,
        error_details: dict,
        error: str = "Invalid sandbox operation error details",
    ):
        message = f"Invalid sandbox operation error details: {error_details}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_DETAILS")


# Define a custom exception for invalid sandbox operation error type


class InvalidSandboxOperationErrorTypeError(AgentExecutionError):
    """Exception raised when sandbox operation error type is invalid."""

    def __init__(
        self, error_type: str, error: str = "Invalid sandbox operation error type"
    ):
        message = f"Invalid sandbox operation error type: {error_type}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_TYPE")


# Define a custom exception for invalid sandbox operation error source


class InvalidSandboxOperationErrorSourceError(AgentExecutionError):
    """Exception raised when sandbox operation error source is invalid."""

    def __init__(
        self, error_source: str, error: str = "Invalid sandbox operation error source"
    ):
        message = f"Invalid sandbox operation error source: {error_source}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_SOURCE")


# Define a custom exception for invalid sandbox operation error timestamp


class InvalidSandboxOperationErrorTimestampError(AgentExecutionError):
    """Exception raised when sandbox operation error timestamp is invalid."""

    def __init__(
        self, timestamp: str, error: str = "Invalid sandbox operation error timestamp"
    ):
        message = f"Invalid sandbox operation error timestamp: {timestamp}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_TIMESTAMP")


# Define a custom exception for invalid sandbox operation error location


class InvalidSandboxOperationErrorLocationError(AgentExecutionError):
    """Exception raised when sandbox operation error location is invalid."""

    def __init__(
        self,
        error_location: str,
        error: str = "Invalid sandbox operation error location",
    ):
        message = f"Invalid sandbox operation error location: {error_location}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_LOCATION")


# Define a custom exception for agent not found


class AgentNotFoundError(AgentExecutionError):
    """Exception raised when an agent is not found."""

    def __init__(self, agent_id: str):
        message = f"Agent not found with ID: {agent_id}"
        super().__init__(message, "AGENT_NOT_FOUND")


# Define a custom exception for invalid sandbox operation error stack trace


class InvalidSandboxOperationErrorStackTraceError(AgentExecutionError):
    """Exception raised when sandbox operation error stack trace is invalid."""

    def __init__(
        self,
        stack_trace: str,
        error: str = "Invalid sandbox operation error stack trace",
    ):
        message = f"Invalid sandbox operation error stack trace: {stack_trace}. {error}"
        super().__init__(message, "INVALID_SANDBOX_OPERATION_ERROR_STACK_TRACE")


# Export all custom exceptions for use in other modules


__all__ = [
    "AgentExecutionError",
    "AgentTimeoutError",
    "AgentResourceExceededError",
    "AgentConfigurationError",
    "AgentToolInjectionError",
    "AgentProcessError",
    "AgentResourceMonitorError",
    "AgentTracingError",
    "InvalidAgentTypeError",
    "InvalidTaskDataError",
    "InvalidSessionIdError",
    "InvalidBuildIdError",
    "InvalidPromptError",
    "InvalidToolConfigurationError",
    "InvalidCommandError",
    "InvalidArgumentError",
    "InvalidFileOperationError",
    "InvalidDirectoryError",
    "InvalidFilePathError",
    "InvalidFileSizeError",
    "InvalidFileExtensionError",
    "InvalidCommandArgumentError",
    "InvalidLLMResponseError",
    "InvalidSandboxOperationError",
    "InvalidSandboxResponseError",
    "InvalidSandboxConfigurationError",
    "InvalidSandboxResourceLimitError",
    "InvalidSandboxOperationTimeoutError",
    "InvalidSandboxOperationRetryCountError",
    "InvalidSandboxOperationResultError",
    "InvalidSandboxOperationStatusError",
    "InvalidSandboxOperationErrorError",
    "InvalidSandboxOperationDetailsError",
    "InvalidSandboxOperationResponseError",
    "InvalidSandboxOperationLogError",
    "InvalidSandboxOperationStatusCodeError",
    "InvalidSandboxOperationErrorCodeError",
    "InvalidSandboxOperationErrorMessageError",
    "InvalidSandboxOperationErrorDetailsError",
    "InvalidSandboxOperationErrorTypeError",
    "InvalidSandboxOperationErrorSourceError",
    "InvalidSandboxOperationErrorTimestampError",
    "InvalidSandboxOperationErrorLocationError",
    "InvalidSandboxOperationErrorStackTraceError",
    "AgentNotFoundError",
]
