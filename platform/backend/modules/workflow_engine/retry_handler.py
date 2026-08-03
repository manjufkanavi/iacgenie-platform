"""

Retry Handler

Implements retry logic with exponential backoff for workflow operations.

"""

import logging

import asyncio

import time

from typing import Optional, Callable, Any, Type, cast

from functools import wraps

from config.workflow_config import workflow_config

from .exceptions import RetryError

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Handles retry logic with exponential backoff.
    Features:
    - Configurable max retry attempts
    - Exponential backoff with multiplier
    - Jitter to avoid thundering herd
    - Retry condition callback
    """

    def __init__(self) -> None:
        self.max_attempts = workflow_config.RETRY_MAX_ATTEMPTS
        self.base_delay = workflow_config.RETRY_INITIAL_DELAY
        self.multiplier = workflow_config.RETRY_BACKOFF_MULTIPLIER
        logger.info(
            f"Retry handler initialized: max_attempts={self.max_attempts}, "
            f"base_delay={self.base_delay}s, multiplier={self.multiplier}"
        )

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a retry attempt with jitter.
        Args:
            attempt: Current attempt number (0-indexed)
        Returns:
            Delay in seconds with jitter applied
        """
        # Exponential backoff
        delay = self.base_delay * (self.multiplier**attempt)
        # Add jitter (±25%)
        jitter = delay * 0.25
        import random

        delay = delay + random.uniform(-jitter, jitter)
        return max(0, delay)

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args: Any,
        retry_on: Optional[Type[Exception]] = Exception,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with retry logic.
        Args:
            func: Function to execute
            *args: Positional arguments for function
            retry_on: Exception type to retry on
            **kwargs: Keyword arguments for function
        Returns:
            Result from function
        Raises:
            RetryError: If all retry attempts fail
        """
        last_exception = None
        for attempt in range(self.max_attempts):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(
                        f"Operation succeeded on attempt {attempt + 1}/{self.max_attempts}"
                    )
                return result
            except cast(Type[BaseException], retry_on) as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Operation failed on attempt {attempt + 1}/{self.max_attempts}, "
                        f"retrying in {delay:.2f}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Operation failed after {self.max_attempts} attempts: {str(e)}"
                    )
        raise RetryError(
            f"Operation failed after {self.max_attempts} attempts",
            retry_count=self.max_attempts,
            max_retries=self.max_attempts,
        ) from last_exception

    def sync_execute_with_retry(
        self,
        func: Callable[..., Any],
        *args: Any,
        retry_on: Optional[Type[Exception]] = Exception,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a synchronous function with retry logic.
        Args:
            func: Function to execute
            *args: Positional arguments for function
            retry_on: Exception type to retry on
            **kwargs: Keyword arguments for function
        Returns:
            Result from function
        Raises:
            RetryError: If all retry attempts fail
        """
        last_exception = None
        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(
                        f"Operation succeeded on attempt {attempt + 1}/{self.max_attempts}"
                    )
                return result
            except cast(Type[BaseException], retry_on) as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Operation failed on attempt {attempt + 1}/{self.max_attempts}, "
                        f"retrying in {delay:.2f}s: {str(e)}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Operation failed after {self.max_attempts} attempts: {str(e)}"
                    )
        raise RetryError(
            f"Operation failed after {self.max_attempts} attempts",
            retry_count=self.max_attempts,
            max_retries=self.max_attempts,
        ) from last_exception


def retry_async(
    max_attempts: Optional[int] = None, retry_on: Optional[Type[Exception]] = Exception
) -> Callable[..., Any]:
    """
    Decorator for async functions with retry logic.
    Args:
        max_attempts: Maximum retry attempts
        retry_on: Exception type to retry on
    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            handler = RetryHandler()
            if max_attempts is not None:
                handler.max_attempts = max_attempts
            return await handler.execute_with_retry(
                func, *args, retry_on=retry_on, **kwargs
            )

        return wrapper

    return decorator


def retry_sync(
    max_attempts: Optional[int] = None, retry_on: Optional[Type[Exception]] = Exception
) -> Callable[..., Any]:
    """
    Decorator for synchronous functions with retry logic.
    Args:
        max_attempts: Maximum retry attempts
        retry_on: Exception type to retry on
    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            handler = RetryHandler()
            if max_attempts is not None:
                handler.max_attempts = max_attempts
            return handler.sync_execute_with_retry(
                func, *args, retry_on=retry_on, **kwargs
            )

        return wrapper

    return decorator


# Global retry handler instance


retry_handler = RetryHandler()
