"""Fallback pattern implementation.

Provides graceful degradation when primary operations fail.
Per ADR-006 resilience requirements.
"""

import logging
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def with_fallback(
    primary: Callable[..., T],
    fallback: Callable[..., T],
    operation_name: str = "operation",
    *args,
    **kwargs
) -> T:
    """Execute operation with fallback on failure.

    Args:
        primary: Primary async function to try
        fallback: Fallback async function if primary fails
        operation_name: Name for logging
        *args, **kwargs: Arguments to pass to functions

    Returns:
        Result from primary or fallback function

    Raises:
        Exception: If both primary and fallback fail
    """
    try:
        return await primary(*args, **kwargs)

    except Exception as e:
        logger.warning(
            f"Primary operation '{operation_name}' failed: {e}. Trying fallback..."
        )

        try:
            result = await fallback(*args, **kwargs)
            logger.info(f"Fallback for '{operation_name}' succeeded")
            return result

        except Exception as fallback_error:
            logger.error(
                f"Both primary and fallback failed for '{operation_name}': {fallback_error}"
            )
            raise
