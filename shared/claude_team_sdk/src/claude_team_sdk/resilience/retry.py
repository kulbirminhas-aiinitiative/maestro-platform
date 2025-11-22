"""
Retry Pattern with Exponential Backoff.

Automatically retries failed operations with increasing delays to handle
transient failures.
"""

import asyncio
from typing import TypeVar, Callable, Tuple, Type
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    name: str = "operation",
) -> T:
    """
    Retry function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exceptions to retry on
        name: Operation name for logging

    Returns:
        Result from func

    Raises:
        RetryError: If all retries are exhausted
        Exception: Original exception if not retryable
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = await func()
            if attempt > 0:
                logger.info(f"{name}: Succeeded on attempt {attempt + 1}/{max_retries + 1}")
            return result

        except retryable_exceptions as e:
            last_exception = e

            if attempt >= max_retries:
                logger.error(
                    f"{name}: Max retries ({max_retries}) exceeded. Last error: {str(e)}"
                )
                raise RetryError(
                    f"Operation '{name}' failed after {max_retries + 1} attempts"
                ) from e

            wait_time = min(delay, max_delay)
            logger.warning(
                f"{name}: Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. "
                f"Retrying in {wait_time}s..."
            )

            await asyncio.sleep(wait_time)
            delay *= backoff_factor

        except Exception as e:
            # Non-retryable exception
            logger.error(f"{name}: Non-retryable exception: {str(e)}")
            raise

    # Should never reach here
    raise RetryError(f"Operation '{name}' failed") from last_exception


async def retry_on_condition(
    func: Callable[..., T],
    condition: Callable[[T], bool],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    name: str = "operation",
) -> T:
    """
    Retry function until condition is met.

    Args:
        func: Async function to retry
        condition: Function that returns True if result is acceptable
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        name: Operation name for logging

    Returns:
        Result from func when condition is met

    Raises:
        RetryError: If all retries are exhausted
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        result = await func()

        if condition(result):
            if attempt > 0:
                logger.info(f"{name}: Condition met on attempt {attempt + 1}/{max_retries + 1}")
            return result

        if attempt >= max_retries:
            logger.error(f"{name}: Condition not met after {max_retries + 1} attempts")
            raise RetryError(
                f"Operation '{name}' condition not met after {max_retries + 1} attempts"
            )

        wait_time = delay
        logger.warning(
            f"{name}: Condition not met on attempt {attempt + 1}/{max_retries + 1}. "
            f"Retrying in {wait_time}s..."
        )

        await asyncio.sleep(wait_time)
        delay *= backoff_factor

    raise RetryError(f"Operation '{name}' failed")
