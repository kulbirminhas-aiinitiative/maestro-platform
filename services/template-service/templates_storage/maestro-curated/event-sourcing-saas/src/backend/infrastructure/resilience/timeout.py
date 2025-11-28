"""Timeout pattern for preventing hanging operations."""

import asyncio
from typing import TypeVar, Awaitable
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when operation exceeds timeout."""
    pass


async def with_timeout(
    operation: Awaitable[T],
    timeout_seconds: float,
    operation_name: str = "operation"
) -> T:
    """
    Execute async operation with timeout.

    Args:
        operation: Awaitable to execute
        timeout_seconds: Timeout in seconds
        operation_name: Name for logging

    Returns:
        Result from operation

    Raises:
        TimeoutError: If operation exceeds timeout

    Example:
        >>> result = await with_timeout(
        ...     db.fetch_user(user_id),
        ...     timeout_seconds=10.0,
        ...     operation_name="fetch_user"
        ... )
    """
    try:
        result = await asyncio.wait_for(operation, timeout=timeout_seconds)
        return result

    except asyncio.TimeoutError:
        logger.error(
            "operation_timeout",
            operation=operation_name,
            timeout_seconds=timeout_seconds
        )
        raise TimeoutError(
            f"Operation '{operation_name}' exceeded {timeout_seconds}s timeout"
        )
