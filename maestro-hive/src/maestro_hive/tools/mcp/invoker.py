"""
MCP Tool Invoker

EPIC: MD-2565
AC-1: MCP-compliant tool interface implementation
AC-3: Streaming support for long-running tools
AC-4: Error handling and retry logic
AC-5: Tool result caching where appropriate

Provides unified tool invocation with retry, caching, and streaming.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from .models import MCPTool, ToolResult, ToolError, StreamChunk
from .config import MCPConfig, RetryPolicy
from .registry import MCPToolRegistry, get_global_registry
from .cache import ToolResultCache

logger = logging.getLogger(__name__)


class MCPToolInvoker:
    """
    Unified tool invocation with retry, caching, and streaming (AC-1, AC-3, AC-4, AC-5).

    Features:
    - Automatic retry with configurable backoff (AC-4)
    - Result caching for cacheable tools (AC-5)
    - Streaming support for long-running tools (AC-3)
    - Concurrent invocation limits
    - Metrics and logging

    Example:
        invoker = MCPToolInvoker(config)

        # Simple invocation
        result = await invoker.invoke("search", {"query": "hello"})

        # Streaming invocation
        async for chunk in invoker.invoke_stream("generate", {"prompt": "hello"}):
            print(chunk.content)
    """

    def __init__(
        self,
        config: Optional[MCPConfig] = None,
        registry: Optional[MCPToolRegistry] = None,
    ):
        self.config = config or MCPConfig()
        self.registry = registry or get_global_registry()
        self.cache = ToolResultCache(self.config.cache)

        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_invocations)
        self._invocation_count = 0
        self._error_count = 0
        self._total_duration_ms = 0

    async def invoke(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        use_cache: bool = True,
        retry_policy: Optional[RetryPolicy] = None,
        timeout_seconds: Optional[int] = None,
    ) -> ToolResult:
        """
        Invoke a tool with retry and caching (AC-4, AC-5).

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments
            use_cache: Whether to use caching (default True)
            retry_policy: Override retry policy for this invocation
            timeout_seconds: Override timeout for this invocation

        Returns:
            ToolResult from tool execution

        Raises:
            ValueError: If tool not found
            ToolError: If invocation fails after retries
        """
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        # Validate arguments
        validation_errors = tool.validate_arguments(arguments)
        if validation_errors:
            return ToolResult(
                content=None,
                is_error=True,
                metadata={"validation_errors": validation_errors},
            )

        # Check cache (AC-5)
        if use_cache and tool.cacheable:
            cached = await self.cache.get(tool_name, arguments)
            if cached is not None:
                logger.debug(f"Cache hit for {tool_name}")
                return ToolResult(
                    content=cached,
                    cached=True,
                    metadata={"source": "cache"},
                )

        # Execute with retry (AC-4)
        policy = retry_policy or self.config.retry_policy
        timeout = timeout_seconds or tool.timeout_seconds or self.config.default_timeout_seconds

        result = await self._execute_with_retry(tool, arguments, policy, timeout)

        # Cache successful result (AC-5)
        if use_cache and tool.cacheable and not result.is_error:
            await self.cache.set(tool_name, arguments, result.content)

        return result

    async def _execute_with_retry(
        self,
        tool: MCPTool,
        arguments: Dict[str, Any],
        policy: RetryPolicy,
        timeout: int,
    ) -> ToolResult:
        """Execute tool with retry logic (AC-4)."""
        last_error: Optional[ToolError] = None

        for attempt in range(policy.max_retries + 1):
            try:
                async with self._semaphore:
                    start_time = time.monotonic()

                    try:
                        result = await asyncio.wait_for(
                            tool.execute(**arguments),
                            timeout=timeout,
                        )
                    except asyncio.TimeoutError:
                        raise ToolError(
                            code="timeout",
                            message=f"Tool execution timed out after {timeout}s",
                            retryable=True,
                        )

                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    result.duration_ms = duration_ms

                    self._invocation_count += 1
                    self._total_duration_ms += duration_ms

                    logger.info(
                        f"Tool invoked: {tool.name} "
                        f"duration={duration_ms}ms "
                        f"attempt={attempt + 1}"
                    )

                    return result

            except ToolError as e:
                last_error = e
                self._error_count += 1

                if not e.retryable or not policy.is_retryable(e.code):
                    logger.error(f"Tool failed (non-retryable): {tool.name} error={e.code}")
                    break

                if attempt < policy.max_retries:
                    delay_ms = policy.get_delay_ms(attempt + 1)
                    logger.warning(
                        f"Tool retry: {tool.name} "
                        f"attempt={attempt + 1} "
                        f"error={e.code} "
                        f"delay={delay_ms}ms"
                    )
                    await asyncio.sleep(delay_ms / 1000)
                else:
                    logger.error(f"Tool failed (max retries): {tool.name} error={e.code}")

            except Exception as e:
                self._error_count += 1
                last_error = ToolError(
                    code="execution_error",
                    message=str(e),
                    retryable=False,
                )
                logger.exception(f"Tool exception: {tool.name}")
                break

        # Return error result
        return ToolResult(
            content=None,
            is_error=True,
            metadata={
                "error_code": last_error.code if last_error else "unknown",
                "error_message": last_error.message if last_error else "Unknown error",
            },
        )

    async def invoke_stream(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Invoke a tool with streaming output (AC-3).

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments
            timeout_seconds: Override timeout

        Yields:
            StreamChunk objects as they become available
        """
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        # Validate arguments
        validation_errors = tool.validate_arguments(arguments)
        if validation_errors:
            yield StreamChunk(
                content={"validation_errors": validation_errors},
                is_final=True,
                metadata={"is_error": True},
            )
            return

        if not tool.stream_capable:
            # Fall back to regular execution wrapped in stream
            result = await self.invoke(tool_name, arguments, use_cache=False)
            yield StreamChunk(
                content=result.content,
                is_final=True,
                metadata=result.metadata,
            )
            return

        timeout = timeout_seconds or tool.timeout_seconds or self.config.default_timeout_seconds
        start_time = time.monotonic()
        chunk_index = 0

        try:
            async with self._semaphore:
                async for chunk in tool.execute_stream(**arguments):
                    # Check timeout
                    elapsed = time.monotonic() - start_time
                    if elapsed > timeout:
                        yield StreamChunk(
                            content={"error": "Stream timeout"},
                            is_final=True,
                            metadata={"is_error": True},
                        )
                        return

                    chunk.index = chunk_index
                    chunk_index += 1

                    logger.debug(f"Stream chunk: {tool.name} index={chunk.index}")
                    yield chunk

                    if chunk.is_final:
                        break

        except Exception as e:
            logger.exception(f"Stream error: {tool.name}")
            yield StreamChunk(
                content={"error": str(e)},
                is_final=True,
                metadata={"is_error": True},
            )

        duration_ms = int((time.monotonic() - start_time) * 1000)
        self._invocation_count += 1
        self._total_duration_ms += duration_ms

        logger.info(f"Stream complete: {tool.name} chunks={chunk_index} duration={duration_ms}ms")

    async def invoke_batch(
        self,
        invocations: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None,
    ) -> List[ToolResult]:
        """
        Invoke multiple tools concurrently.

        Args:
            invocations: List of {"tool_name": str, "arguments": dict}
            max_concurrent: Max concurrent invocations (default: config limit)

        Returns:
            List of ToolResults in same order as invocations
        """
        if max_concurrent:
            semaphore = asyncio.Semaphore(max_concurrent)
        else:
            semaphore = self._semaphore

        async def invoke_with_semaphore(inv: Dict[str, Any]) -> ToolResult:
            async with semaphore:
                return await self.invoke(inv["tool_name"], inv.get("arguments", {}))

        return await asyncio.gather(
            *[invoke_with_semaphore(inv) for inv in invocations]
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get invoker statistics."""
        avg_duration = (
            self._total_duration_ms / self._invocation_count
            if self._invocation_count > 0
            else 0
        )

        return {
            "invocation_count": self._invocation_count,
            "error_count": self._error_count,
            "error_rate": (
                self._error_count / self._invocation_count
                if self._invocation_count > 0
                else 0
            ),
            "avg_duration_ms": avg_duration,
            "cache_stats": self.cache.get_stats(),
        }

    def reset_stats(self) -> None:
        """Reset invocation statistics."""
        self._invocation_count = 0
        self._error_count = 0
        self._total_duration_ms = 0
