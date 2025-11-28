"""Retry with exponential backoff pattern.

Automatically retries failed operations with increasing delays.
Per ADR-006 resilience requirements.
"""

import asyncio
import logging
from typing import Callable, TypeVar, Type

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    operation_name: str = "operation",
) -> T:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types to retry
        operation_name: Name for logging

    Returns:
        Result from successful function call

    Raises:
        RetryExhaustedError: If all retries exhausted
        Any non-retryable exception
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = await func()
            if attempt > 0:
                logger.info(
                    f"Operation '{operation_name}' succeeded on attempt {attempt + 1}"
                )
            return result

        except retryable_exceptions as e:
            last_exception = e

            if attempt >= max_retries:
                logger.error(
                    f"Operation '{operation_name}' failed after {max_retries + 1} attempts: {e}"
                )
                raise RetryExhaustedError(
                    f"Operation '{operation_name}' failed after {max_retries + 1} attempts"
                ) from e

            wait_time = min(delay, max_delay)
            logger.warning(
                f"Operation '{operation_name}' failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {wait_time:.1f}s: {e}"
            )

            await asyncio.sleep(wait_time)
            delay *= backoff_factor

        except Exception as e:
            # Non-retryable exception
            logger.error(f"Operation '{operation_name}' failed with non-retryable error: {e}")
            raise

    # Should never reach here
    raise RetryExhaustedError(
        f"Operation '{operation_name}' failed after {max_retries + 1} attempts"
    ) from last_exception
