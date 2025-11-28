"""Retry with exponential backoff pattern."""

import asyncio
from typing import TypeVar, Callable, Type
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    operation_name: str = "operation",
) -> T:
    """
    Retry async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        max_delay: Maximum delay between retries
        retryable_exceptions: Exceptions to retry on
        operation_name: Name for logging

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries exhausted

    Example:
        >>> result = await retry_with_backoff(
        ...     db_query,
        ...     max_retries=3,
        ...     initial_delay=1.0,
        ...     operation_name="fetch_user"
        ... )
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            result = await func()

            if attempt > 0:
                logger.info(
                    "retry_success",
                    operation=operation_name,
                    attempt=attempt + 1,
                    total_attempts=max_retries + 1
                )

            return result

        except retryable_exceptions as e:
            if attempt >= max_retries:
                logger.error(
                    "retry_exhausted",
                    operation=operation_name,
                    attempts=attempt + 1,
                    max_retries=max_retries,
                    error=str(e)
                )
                raise

            wait_time = min(delay, max_delay)
            logger.warning(
                "retry_attempt",
                operation=operation_name,
                attempt=attempt + 1,
                max_retries=max_retries,
                wait_time=wait_time,
                error=str(e)
            )

            await asyncio.sleep(wait_time)
            delay *= backoff_factor
