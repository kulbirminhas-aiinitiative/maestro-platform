"""Fallback pattern for graceful degradation."""

from typing import TypeVar, Callable, Optional
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


async def with_fallback(
    primary: Callable[..., T],
    fallback: Callable[..., T],
    operation_name: str = "operation",
    *args,
    **kwargs
) -> T:
    """
    Execute primary function with fallback on failure.

    Args:
        primary: Primary async function to try
        fallback: Fallback async function if primary fails
        operation_name: Name for logging
        *args: Arguments for both functions
        **kwargs: Keyword arguments for both functions

    Returns:
        Result from primary or fallback

    Example:
        >>> user = await with_fallback(
        ...     fetch_from_database,
        ...     fetch_from_cache,
        ...     operation_name="get_user",
        ...     user_id=123
        ... )
    """
    try:
        return await primary(*args, **kwargs)

    except Exception as e:
        logger.warning(
            "fallback_triggered",
            operation=operation_name,
            error=str(e)
        )

        try:
            result = await fallback(*args, **kwargs)
            logger.info(
                "fallback_success",
                operation=operation_name
            )
            return result

        except Exception as fallback_error:
            logger.error(
                "fallback_failed",
                operation=operation_name,
                primary_error=str(e),
                fallback_error=str(fallback_error)
            )
            raise


class FallbackValue:
    """Provider for fallback values."""

    @staticmethod
    async def none() -> None:
        """Return None as fallback."""
        return None

    @staticmethod
    async def empty_list() -> list:
        """Return empty list as fallback."""
        return []

    @staticmethod
    async def empty_dict() -> dict:
        """Return empty dict as fallback."""
        return {}

    @staticmethod
    def constant(value: T) -> Callable[[], T]:
        """
        Return constant value as fallback.

        Args:
            value: Value to return

        Returns:
            Async function that returns the value
        """
        async def _constant() -> T:
            return value
        return _constant
