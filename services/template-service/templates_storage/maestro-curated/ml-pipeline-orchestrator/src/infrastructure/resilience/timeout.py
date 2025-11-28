"""Timeout pattern implementation.

Prevents operations from hanging indefinitely.
Per ADR-006 resilience requirements.
"""

import asyncio
import logging
from typing import TypeVar, Awaitable

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when operation exceeds timeout"""
    pass


async def with_timeout(
    operation: Awaitable[T],
    timeout_seconds: float,
    operation_name: str = "operation"
) -> T:
    """Execute async operation with timeout.

    Args:
        operation: Async operation to execute
        timeout_seconds: Maximum execution time in seconds
        operation_name: Name for logging

    Returns:
        Result from operation

    Raises:
        TimeoutError: If operation exceeds timeout
    """
    try:
        result = await asyncio.wait_for(operation, timeout=timeout_seconds)
        return result

    except asyncio.TimeoutError:
        logger.error(
            f"Operation '{operation_name}' exceeded {timeout_seconds}s timeout"
        )
        raise TimeoutError(
            f"Operation '{operation_name}' exceeded {timeout_seconds}s timeout"
        )
