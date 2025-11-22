"""
Timeout Pattern.

Prevents operations from hanging indefinitely by enforcing time limits.
"""

import asyncio
from typing import TypeVar, Callable
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when operation exceeds timeout."""
    pass


async def with_timeout(
    func: Callable[..., T],
    seconds: float,
    name: str = "operation",
) -> T:
    """
    Execute function with timeout enforcement.

    Args:
        func: Async function to execute
        seconds: Timeout in seconds
        name: Operation name for logging

    Returns:
        Result from func

    Raises:
        TimeoutError: If operation exceeds timeout
    """
    try:
        async with asyncio.timeout(seconds):
            result = await func()
            return result

    except asyncio.TimeoutError:
        logger.error(f"{name}: Operation exceeded {seconds}s timeout")
        raise TimeoutError(
            f"Operation '{name}' exceeded {seconds}s timeout"
        ) from None


async def with_timeout_and_default(
    func: Callable[..., T],
    seconds: float,
    default: T,
    name: str = "operation",
) -> T:
    """
    Execute function with timeout, returning default on timeout.

    Args:
        func: Async function to execute
        seconds: Timeout in seconds
        default: Default value to return on timeout
        name: Operation name for logging

    Returns:
        Result from func or default if timeout
    """
    try:
        return await with_timeout(func, seconds, name)
    except TimeoutError:
        logger.warning(f"{name}: Timeout, returning default value")
        return default
