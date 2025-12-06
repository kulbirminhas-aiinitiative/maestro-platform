"""
MCP Tool Registry

Provides centralized registration and management of MCP tools.
Supports tool discovery, validation, and multi-LLM format export.

Epic: MD-2565
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Type, Callable, Awaitable
from enum import Enum
import logging
import asyncio

from .interface import (
    MCPToolInterface,
    MCPToolSchema,
    MCPToolResult,
    LLMProvider,
    ToolStatus
)
from .cache import MCPResultCache, CacheConfig
from .retry import MCPRetryPolicy, RetryConfig

logger = logging.getLogger(__name__)


class RegistryEvent(str, Enum):
    """Events emitted by the registry"""
    TOOL_REGISTERED = "tool_registered"
    TOOL_UNREGISTERED = "tool_unregistered"
    TOOL_EXECUTED = "tool_executed"
    TOOL_ERROR = "tool_error"
    CACHE_HIT = "cache_hit"


@dataclass
class ToolExecutionMetrics:
    """Metrics for tool execution"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_time_ms: float = 0.0
    cache_hits: int = 0
    retry_count: int = 0
    last_called: Optional[datetime] = None

    @property
    def average_time_ms(self) -> float:
        """Calculate average execution time"""
        if self.total_calls == 0:
            return 0.0
        return self.total_time_ms / self.total_calls

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "total_time_ms": self.total_time_ms,
            "average_time_ms": self.average_time_ms,
            "cache_hits": self.cache_hits,
            "retry_count": self.retry_count,
            "success_rate": self.success_rate,
            "last_called": self.last_called.isoformat() if self.last_called else None
        }


@dataclass
class RegisteredTool:
    """Container for a registered tool with metadata"""
    tool: MCPToolInterface
    registered_at: datetime = field(default_factory=datetime.utcnow)
    metrics: ToolExecutionMetrics = field(default_factory=ToolExecutionMetrics)
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    custom_retry_config: Optional[RetryConfig] = None
    custom_ttl_seconds: Optional[int] = None

    @property
    def name(self) -> str:
        return self.tool.name

    @property
    def schema(self) -> MCPToolSchema:
        return self.tool.schema


class MCPToolRegistry:
    """
    Central registry for MCP tools.

    Manages tool registration, execution, caching, and metrics.
    Supports multiple LLM providers (AC-2).

    Features:
    - Tool registration and discovery
    - Automatic caching (AC-5)
    - Retry handling (AC-4)
    - Execution metrics
    - Multi-LLM schema export
    """

    def __init__(
        self,
        cache_config: Optional[CacheConfig] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize registry.

        Args:
            cache_config: Cache configuration
            retry_config: Default retry configuration
        """
        self._tools: Dict[str, RegisteredTool] = {}
        self._cache = MCPResultCache(cache_config)
        self._default_retry_config = retry_config or RetryConfig()
        self._event_handlers: Dict[RegistryEvent, List[Callable]] = {
            event: [] for event in RegistryEvent
        }
        self._lock = asyncio.Lock()

    def register(
        self,
        tool: MCPToolInterface,
        tags: Optional[List[str]] = None,
        retry_config: Optional[RetryConfig] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Register a tool.

        Args:
            tool: Tool to register
            tags: Optional tags for categorization
            retry_config: Optional custom retry config
            ttl_seconds: Optional custom cache TTL
        """
        name = tool.name

        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, updating...")

        registered = RegisteredTool(
            tool=tool,
            tags=tags or [],
            custom_retry_config=retry_config,
            custom_ttl_seconds=ttl_seconds
        )

        self._tools[name] = registered

        # Set custom TTL if provided
        if ttl_seconds is not None:
            self._cache.set_tool_ttl(name, ttl_seconds)

        self._emit(RegistryEvent.TOOL_REGISTERED, {"tool_name": name})
        logger.info(f"Registered tool: {name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was found and removed
        """
        if name in self._tools:
            del self._tools[name]
            self._emit(RegistryEvent.TOOL_UNREGISTERED, {"tool_name": name})
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[MCPToolInterface]:
        """
        Get a registered tool.

        Args:
            name: Tool name

        Returns:
            Tool or None if not found
        """
        registered = self._tools.get(name)
        return registered.tool if registered else None

    def list_tools(
        self,
        tags: Optional[List[str]] = None,
        enabled_only: bool = True
    ) -> List[MCPToolSchema]:
        """
        List all registered tools.

        Args:
            tags: Filter by tags
            enabled_only: Only return enabled tools

        Returns:
            List of tool schemas
        """
        tools = []
        for registered in self._tools.values():
            if enabled_only and not registered.enabled:
                continue
            if tags and not any(t in registered.tags for t in tags):
                continue
            tools.append(registered.schema)
        return tools

    async def execute(
        self,
        name: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        use_retry: bool = True
    ) -> MCPToolResult:
        """
        Execute a registered tool.

        Args:
            name: Tool name
            inputs: Tool inputs
            context: Optional execution context
            use_cache: Whether to use caching (AC-5)
            use_retry: Whether to use retry logic (AC-4)

        Returns:
            MCPToolResult with execution result
        """
        registered = self._tools.get(name)

        if registered is None:
            return MCPToolResult.error(name, f"Tool '{name}' not found")

        if not registered.enabled:
            return MCPToolResult.error(name, f"Tool '{name}' is disabled")

        tool = registered.tool
        metrics = registered.metrics

        # Check cache first
        if use_cache and tool.is_cacheable:
            cache_key = tool.get_cache_key(inputs)
            cached = await self._cache.get(cache_key)
            if cached is not None:
                metrics.cache_hits += 1
                metrics.total_calls += 1
                metrics.last_called = datetime.utcnow()
                self._emit(RegistryEvent.CACHE_HIT, {
                    "tool_name": name,
                    "cache_key": cache_key
                })
                return MCPToolResult(
                    tool_name=name,
                    status=ToolStatus.CACHED,
                    result=cached,
                    cached=True,
                    cache_key=cache_key
                )

        # Validate inputs
        try:
            tool.validate_inputs(inputs)
        except ValueError as e:
            return MCPToolResult.error(name, f"Input validation failed: {e}")

        # Execute with optional retry
        start_time = datetime.utcnow()

        if use_retry:
            retry_config = registered.custom_retry_config or self._default_retry_config
            retry_policy = MCPRetryPolicy(retry_config)

            async def execute_fn():
                return await tool.execute(inputs, context)

            retry_result = await retry_policy.execute_with_retry(execute_fn)

            if retry_result.success:
                result = retry_result.result
                metrics.retry_count += len(retry_result.attempts)
            else:
                metrics.total_calls += 1
                metrics.failed_calls += 1
                metrics.last_called = datetime.utcnow()
                self._emit(RegistryEvent.TOOL_ERROR, {
                    "tool_name": name,
                    "error": retry_result.final_error
                })
                return MCPToolResult.error(name, retry_result.final_error or "Unknown error")
        else:
            try:
                result = await tool.execute(inputs, context)
            except Exception as e:
                metrics.total_calls += 1
                metrics.failed_calls += 1
                metrics.last_called = datetime.utcnow()
                self._emit(RegistryEvent.TOOL_ERROR, {
                    "tool_name": name,
                    "error": str(e)
                })
                return MCPToolResult.error(name, str(e))

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Update metrics
        metrics.total_calls += 1
        metrics.successful_calls += 1
        metrics.total_time_ms += execution_time
        metrics.last_called = datetime.utcnow()

        # Handle MCPToolResult or raw result
        if isinstance(result, MCPToolResult):
            result.execution_time_ms = execution_time
            final_result = result
        else:
            final_result = MCPToolResult.success(
                name,
                result,
                execution_time_ms=execution_time
            )

        # Cache result
        if use_cache and tool.is_cacheable:
            cache_key = tool.get_cache_key(inputs)
            ttl = registered.custom_ttl_seconds
            await self._cache.set(
                cache_key,
                final_result.result,
                name,
                ttl_seconds=ttl
            )
            final_result.cache_key = cache_key

        self._emit(RegistryEvent.TOOL_EXECUTED, {
            "tool_name": name,
            "execution_time_ms": execution_time,
            "cached": False
        })

        return final_result

    def export_for_llm(
        self,
        provider: LLMProvider,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Export tool schemas for an LLM provider (AC-2).

        Args:
            provider: Target LLM provider
            tags: Optional tag filter

        Returns:
            List of provider-specific tool definitions
        """
        tools = []
        for registered in self._tools.values():
            if not registered.enabled:
                continue
            if tags and not any(t in registered.tags for t in tags):
                continue
            tools.append(registered.tool.to_llm_format(provider))
        return tools

    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution metrics.

        Args:
            name: Optional specific tool name

        Returns:
            Metrics dictionary
        """
        if name:
            registered = self._tools.get(name)
            if registered:
                return registered.metrics.to_dict()
            return {}

        return {
            tool_name: registered.metrics.to_dict()
            for tool_name, registered in self._tools.items()
        }

    def enable_tool(self, name: str) -> bool:
        """Enable a tool"""
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable_tool(self, name: str) -> bool:
        """Disable a tool"""
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    def on(
        self,
        event: RegistryEvent,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register an event handler.

        Args:
            event: Event type
            handler: Handler function
        """
        self._event_handlers[event].append(handler)

    def _emit(self, event: RegistryEvent, data: Dict[str, Any]) -> None:
        """Emit an event to handlers"""
        for handler in self._event_handlers[event]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    @property
    def cache(self) -> MCPResultCache:
        """Get cache instance"""
        return self._cache

    @property
    def tool_count(self) -> int:
        """Get number of registered tools"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered"""
        return name in self._tools

    def __iter__(self):
        """Iterate over tool names"""
        return iter(self._tools.keys())
