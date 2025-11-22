"""
Bulkhead Pattern.

Isolates resources to prevent cascading failures by limiting concurrent operations.
"""

import asyncio
from typing import TypeVar, Callable
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BulkheadFullError(Exception):
    """Raised when bulkhead is at capacity."""
    pass


class Bulkhead:
    """
    Bulkhead pattern implementation using semaphore.

    Limits concurrent executions to prevent resource exhaustion.

    Args:
        max_concurrent: Maximum number of concurrent operations
        name: Name for logging and identification
        wait_timeout: Optional timeout for acquiring semaphore (None = wait forever)
    """

    def __init__(
        self,
        max_concurrent: int,
        name: str = "bulkhead",
        wait_timeout: float = None,
    ):
        self.max_concurrent = max_concurrent
        self.name = name
        self.wait_timeout = wait_timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> T:
        """
        Execute function with concurrency limit.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            BulkheadFullError: If wait_timeout is set and semaphore can't be acquired
            Exception: Original exception from func
        """
        if self.wait_timeout is not None:
            try:
                async with asyncio.timeout(self.wait_timeout):
                    return await self._execute(func, *args, **kwargs)
            except asyncio.TimeoutError:
                raise BulkheadFullError(
                    f"Bulkhead '{self.name}' is full. "
                    f"Could not acquire slot within {self.wait_timeout}s"
                ) from None
        else:
            return await self._execute(func, *args, **kwargs)

    async def _execute(self, func: Callable, *args, **kwargs) -> T:
        """Internal execution with semaphore."""
        async with self.semaphore:
            self._active_count += 1
            logger.debug(
                f"Bulkhead '{self.name}': Acquired slot "
                f"({self._active_count}/{self.max_concurrent} active)"
            )

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                self._active_count -= 1
                logger.debug(
                    f"Bulkhead '{self.name}': Released slot "
                    f"({self._active_count}/{self.max_concurrent} active)"
                )

    @property
    def active_count(self) -> int:
        """Get current number of active operations."""
        return self._active_count

    @property
    def available_slots(self) -> int:
        """Get number of available slots."""
        return self.max_concurrent - self._active_count

    @property
    def is_full(self) -> bool:
        """Check if bulkhead is at capacity."""
        return self._active_count >= self.max_concurrent
