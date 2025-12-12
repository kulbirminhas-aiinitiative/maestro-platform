"""
Shared Toolkit for Workflow Optimization
========================================

Common utilities and helper functions for workflow execution and management.
Provides a standardized set of tools for building robust workflows.

EPIC: MD-2961 - Workflow Optimization & Standardization
AC-3: Implement shared_toolkit.py with common utilities for workflow execution
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Awaitable, Callable, Dict, Generic, Iterator, List, Optional,
    Set, Tuple, TypeVar, Union
)
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    wait_on_limit: bool = True
    max_wait_time: float = 30.0


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter implementation.

    Allows burst traffic up to bucket size while maintaining average rate.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._tokens = float(config.burst_size)
        self._last_update = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False otherwise
        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            if self.config.wait_on_limit:
                wait_time = (tokens - self._tokens) / self.config.requests_per_second
                if wait_time <= self.config.max_wait_time:
                    time.sleep(wait_time)
                    self._refill()
                    self._tokens -= tokens
                    return True

            return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(
            self.config.burst_size,
            self._tokens + elapsed * self.config.requests_per_second
        )
        self._last_update = now

    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return self._tokens


def rate_limited(
    requests_per_second: float = 10.0,
    burst_size: int = 20
) -> Callable:
    """
    Decorator for rate limiting function calls.

    Example:
        @rate_limited(requests_per_second=5)
        def call_api():
            ...
    """
    config = RateLimitConfig(
        requests_per_second=requests_per_second,
        burst_size=burst_size
    )
    limiter = TokenBucketRateLimiter(config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not limiter.acquire():
                raise RateLimitExceeded(
                    f"Rate limit exceeded for {func.__name__}",
                    retry_after=1.0 / requests_per_second
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Caching
# =============================================================================

@dataclass
class CacheEntry(Generic[T]):
    """Entry in the cache."""
    value: T
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class CacheConfig:
    """Configuration for cache."""
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[timedelta] = None,
        eviction_policy: str = "lru"
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl or timedelta(hours=1)
        self.eviction_policy = eviction_policy


class Cache(Generic[T]):
    """
    Thread-safe cache with TTL and eviction policies.

    Supports LRU eviction and automatic expiration.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.expires_at and datetime.utcnow() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None

            # Update access info (LRU)
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            self._cache.move_to_end(key)

            self._hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[timedelta] = None
    ) -> None:
        """Set value in cache."""
        with self._lock:
            # Evict if needed
            while len(self._cache) >= self.config.max_size:
                self._evict()

            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + ttl
            elif self.config.default_ttl:
                expires_at = datetime.utcnow() + self.config.default_ttl

            self._cache[key] = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                expires_at=expires_at
            )

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def _evict(self) -> None:
        """Evict entries based on policy."""
        if not self._cache:
            return

        if self.config.eviction_policy == "lru":
            # Remove least recently used (first item in OrderedDict)
            self._cache.popitem(last=False)
        else:
            # Default: remove oldest
            self._cache.popitem(last=False)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.config.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate
            }


def cached(
    ttl: Optional[timedelta] = None,
    max_size: int = 100
) -> Callable:
    """
    Decorator for caching function results.

    Example:
        @cached(ttl=timedelta(minutes=5))
        def expensive_computation(x):
            ...
    """
    cache = Cache[Any](CacheConfig(max_size=max_size, default_ttl=ttl))

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Create cache key from arguments
            key = hashlib.md5(
                json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str).encode()
            ).hexdigest()

            result = cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        wrapper.cache = cache  # type: ignore
        wrapper.cache_clear = cache.clear  # type: ignore
        return wrapper
    return decorator


# =============================================================================
# Execution Context
# =============================================================================

@dataclass
class ExecutionContext:
    """
    Context for workflow execution.

    Carries metadata, correlation IDs, and shared state through execution.
    """
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    parent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _local_data: Dict[str, Any] = field(default_factory=dict)

    def with_step(self, step_id: str) -> ExecutionContext:
        """Create child context for a step."""
        return ExecutionContext(
            execution_id=str(uuid.uuid4()),
            correlation_id=self.correlation_id or self.execution_id,
            parent_id=self.execution_id,
            workflow_id=self.workflow_id,
            step_id=step_id,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            metadata=self.metadata.copy()
        )

    def set(self, key: str, value: Any) -> None:
        """Set local data."""
        self._local_data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get local data."""
        return self._local_data.get(key, default)

    @property
    def duration(self) -> timedelta:
        """Get execution duration."""
        return datetime.utcnow() - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "parent_id": self.parent_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "started_at": self.started_at.isoformat(),
            "duration_ms": self.duration.total_seconds() * 1000
        }


# Thread-local storage for current context
_context_storage = threading.local()


def get_current_context() -> Optional[ExecutionContext]:
    """Get current execution context."""
    return getattr(_context_storage, 'context', None)


def set_current_context(context: ExecutionContext) -> None:
    """Set current execution context."""
    _context_storage.context = context


@contextmanager
def execution_context(context: Optional[ExecutionContext] = None) -> Iterator[ExecutionContext]:
    """
    Context manager for execution context.

    Example:
        with execution_context() as ctx:
            ctx.set("key", "value")
            do_work()
    """
    previous = get_current_context()
    ctx = context or ExecutionContext()
    set_current_context(ctx)
    try:
        yield ctx
    finally:
        if previous:
            set_current_context(previous)
        else:
            _context_storage.context = None


# =============================================================================
# Metrics & Timing
# =============================================================================

@dataclass
class TimingResult:
    """Result of a timed operation."""
    name: str
    duration_ms: float
    started_at: datetime
    ended_at: datetime
    success: bool
    error: Optional[str] = None


class Timer:
    """
    High-precision timer for measuring execution time.
    """

    def __init__(self, name: str = "operation"):
        self.name = name
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._started_at: Optional[datetime] = None
        self._ended_at: Optional[datetime] = None
        self._success = True
        self._error: Optional[str] = None

    def start(self) -> Timer:
        """Start the timer."""
        self._start_time = time.perf_counter()
        self._started_at = datetime.utcnow()
        return self

    def stop(self, success: bool = True, error: Optional[str] = None) -> Timer:
        """Stop the timer."""
        self._end_time = time.perf_counter()
        self._ended_at = datetime.utcnow()
        self._success = success
        self._error = error
        return self

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self._start_time is None:
            return 0.0
        end = self._end_time or time.perf_counter()
        return (end - self._start_time) * 1000

    @property
    def result(self) -> TimingResult:
        """Get timing result."""
        return TimingResult(
            name=self.name,
            duration_ms=self.elapsed_ms,
            started_at=self._started_at or datetime.utcnow(),
            ended_at=self._ended_at or datetime.utcnow(),
            success=self._success,
            error=self._error
        )


@contextmanager
def timed(name: str = "operation") -> Iterator[Timer]:
    """
    Context manager for timing operations.

    Example:
        with timed("api_call") as timer:
            result = call_api()
        print(f"Took {timer.elapsed_ms}ms")
    """
    timer = Timer(name).start()
    try:
        yield timer
        timer.stop(success=True)
    except Exception as e:
        timer.stop(success=False, error=str(e))
        raise


def timed_decorator(name: Optional[str] = None) -> Callable:
    """
    Decorator for timing function execution.

    Example:
        @timed_decorator("api_call")
        def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        operation_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with timed(operation_name) as timer:
                result = func(*args, **kwargs)

            logger.debug(
                f"{operation_name} completed in {timer.elapsed_ms:.2f}ms"
            )
            return result
        return wrapper
    return decorator


# =============================================================================
# Async Utilities
# =============================================================================

async def gather_with_concurrency(
    coroutines: List[Awaitable[T]],
    max_concurrency: int = 10,
    return_exceptions: bool = False
) -> List[Union[T, Exception]]:
    """
    Run coroutines with limited concurrency.

    Args:
        coroutines: List of coroutines to run
        max_concurrency: Maximum concurrent executions
        return_exceptions: If True, return exceptions instead of raising

    Returns:
        List of results (or exceptions if return_exceptions=True)
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded(coro: Awaitable[T]) -> Union[T, Exception]:
        async with semaphore:
            try:
                return await coro
            except Exception as e:
                if return_exceptions:
                    return e
                raise

    return await asyncio.gather(
        *[bounded(c) for c in coroutines],
        return_exceptions=return_exceptions
    )


async def retry_async(
    coro_factory: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[type, ...] = (Exception,)
) -> T:
    """
    Retry an async operation with exponential backoff.

    Args:
        coro_factory: Factory function that creates the coroutine
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries
        exponential_base: Multiplier for delay increase
        retryable_exceptions: Exceptions that trigger retry

    Returns:
        Result of successful execution
    """
    last_exception: Optional[Exception] = None
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}"
                )
                await asyncio.sleep(current_delay)
                current_delay *= exponential_base

    raise last_exception or RuntimeError("Retry failed")


# =============================================================================
# Data Transformation
# =============================================================================

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with values to override

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def flatten_dict(
    d: Dict[str, Any],
    separator: str = ".",
    prefix: str = ""
) -> Dict[str, Any]:
    """
    Flatten a nested dictionary.

    Args:
        d: Dictionary to flatten
        separator: Key separator
        prefix: Key prefix

    Returns:
        Flattened dictionary
    """
    items: List[Tuple[str, Any]] = []

    for key, value in d.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key

        if isinstance(value, dict):
            items.extend(flatten_dict(value, separator, new_key).items())
        else:
            items.append((new_key, value))

    return dict(items)


def unflatten_dict(d: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    """
    Unflatten a dictionary with dotted keys.

    Args:
        d: Flattened dictionary
        separator: Key separator

    Returns:
        Nested dictionary
    """
    result: Dict[str, Any] = {}

    for key, value in d.items():
        parts = key.split(separator)
        current = result

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    return result


# =============================================================================
# Validation Utilities
# =============================================================================

def validate_required_fields(
    data: Dict[str, Any],
    required: List[str]
) -> List[str]:
    """
    Validate required fields exist in data.

    Returns:
        List of missing field names
    """
    missing = []
    for field in required:
        if field not in data or data[field] is None:
            missing.append(field)
    return missing


def validate_field_types(
    data: Dict[str, Any],
    schema: Dict[str, type]
) -> List[str]:
    """
    Validate field types match schema.

    Returns:
        List of type mismatch errors
    """
    errors = []
    for field, expected_type in schema.items():
        if field in data:
            if not isinstance(data[field], expected_type):
                errors.append(
                    f"{field}: expected {expected_type.__name__}, "
                    f"got {type(data[field]).__name__}"
                )
    return errors


# =============================================================================
# ID Generation
# =============================================================================

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = str(uuid.uuid4())
    return f"{prefix}{uid}" if prefix else uid


def generate_short_id(length: int = 8) -> str:
    """Generate a short random ID."""
    return uuid.uuid4().hex[:length]


def generate_correlation_id() -> str:
    """Generate a correlation ID for request tracking."""
    return f"corr-{uuid.uuid4().hex[:12]}"


# =============================================================================
# Singleton Registry
# =============================================================================

class ToolkitRegistry:
    """
    Central registry for toolkit components.

    Provides access to shared instances of toolkit utilities.
    """

    _instance: Optional[ToolkitRegistry] = None
    _lock = threading.Lock()

    def __new__(cls) -> ToolkitRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        """Initialize registry."""
        self._rate_limiters: Dict[str, TokenBucketRateLimiter] = {}
        self._caches: Dict[str, Cache] = {}
        self._timers: List[TimingResult] = []

    def get_rate_limiter(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None
    ) -> TokenBucketRateLimiter:
        """Get or create a named rate limiter."""
        if name not in self._rate_limiters:
            self._rate_limiters[name] = TokenBucketRateLimiter(
                config or RateLimitConfig()
            )
        return self._rate_limiters[name]

    def get_cache(
        self,
        name: str,
        config: Optional[CacheConfig] = None
    ) -> Cache:
        """Get or create a named cache."""
        if name not in self._caches:
            self._caches[name] = Cache(config)
        return self._caches[name]

    def record_timing(self, result: TimingResult) -> None:
        """Record a timing result."""
        self._timers.append(result)
        # Keep only last 1000 timings
        if len(self._timers) > 1000:
            self._timers = self._timers[-1000:]

    def get_timing_stats(self) -> Dict[str, Any]:
        """Get timing statistics."""
        if not self._timers:
            return {"count": 0}

        durations = [t.duration_ms for t in self._timers]
        return {
            "count": len(self._timers),
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "success_rate": sum(1 for t in self._timers if t.success) / len(self._timers)
        }


def get_toolkit_registry() -> ToolkitRegistry:
    """Get the toolkit registry singleton."""
    return ToolkitRegistry()
