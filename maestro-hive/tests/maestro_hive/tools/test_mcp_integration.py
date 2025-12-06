"""
Tests for MCP Integration Module

EPIC: MD-2565
[TOOL-FRAMEWORK] MCP Integration - Standard Tool Protocol

Tests all acceptance criteria:
- AC-1: MCP-compliant tool interface implementation
- AC-2: Tools callable from Claude, GPT, and other LLMs
- AC-3: Streaming support for long-running tools
- AC-4: Error handling and retry logic
- AC-5: Tool result caching where appropriate
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

# Import MCP components
from maestro_hive.tools.mcp import (
    MCPTool,
    ToolParameter,
    ToolResult,
    ToolError,
    StreamChunk,
    ParameterType,
    MCPConfig,
    RetryPolicy,
    MCPToolRegistry,
    MCPToolInvoker,
    ToolResultCache,
    ClaudeAdapter,
    OpenAIAdapter,
)
from maestro_hive.tools.mcp.config import RetryStrategy, CacheConfig
from maestro_hive.tools.mcp.adapters import GeminiAdapter, get_adapter


# =============================================================================
# Test Fixtures
# =============================================================================

class SearchTool(MCPTool):
    """Sample search tool for testing."""
    name = "search"
    description = "Search for information"
    parameters = [
        ToolParameter(name="query", type=ParameterType.STRING, required=True),
        ToolParameter(name="limit", type=ParameterType.INTEGER, default=10),
    ]
    cacheable = True
    stream_capable = False

    async def execute(self, query: str, limit: int = 10) -> ToolResult:
        return ToolResult(
            content={"results": [f"Result for: {query}"], "count": 1},
            metadata={"query": query, "limit": limit},
        )


class StreamingTool(MCPTool):
    """Sample streaming tool for testing."""
    name = "generate"
    description = "Generate text with streaming"
    parameters = [
        ToolParameter(name="prompt", type=ParameterType.STRING, required=True),
    ]
    cacheable = False
    stream_capable = True

    async def execute(self, prompt: str) -> ToolResult:
        return ToolResult(content=f"Generated: {prompt}")

    async def execute_stream(self, prompt: str):
        words = ["Hello", " ", "world", "!"]
        for i, word in enumerate(words):
            yield StreamChunk(
                content=word,
                index=i,
                is_final=(i == len(words) - 1),
            )


class FailingTool(MCPTool):
    """Tool that fails for retry testing."""
    name = "failing"
    description = "A tool that fails"
    parameters = []
    fail_count = 0

    async def execute(self) -> ToolResult:
        FailingTool.fail_count += 1
        if FailingTool.fail_count < 3:
            raise ToolError(code="timeout", message="Simulated timeout", retryable=True)
        return ToolResult(content="Success after retries")


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return MCPToolRegistry()


@pytest.fixture
def config():
    """Create test configuration."""
    return MCPConfig(
        retry_policy=RetryPolicy(max_retries=3, base_delay_ms=10),
        cache=CacheConfig(enabled=True, default_ttl_seconds=60),
    )


@pytest.fixture
def invoker(config, registry):
    """Create invoker with test config and registry."""
    registry.register(SearchTool())
    registry.register(StreamingTool())
    return MCPToolInvoker(config=config, registry=registry)


# =============================================================================
# AC-1: MCP-compliant tool interface implementation
# =============================================================================

class TestMCPToolInterface:
    """Tests for AC-1: MCP-compliant tool interface."""

    def test_tool_parameter_creation(self):
        """Test ToolParameter dataclass."""
        param = ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="Search query",
            required=True,
        )
        assert param.name == "query"
        assert param.type == ParameterType.STRING
        assert param.required is True

    def test_tool_parameter_json_schema(self):
        """Test ToolParameter.to_json_schema()."""
        param = ToolParameter(
            name="count",
            type=ParameterType.INTEGER,
            description="Number of items",
            minimum=1,
            maximum=100,
            default=10,
        )
        schema = param.to_json_schema()

        assert schema["type"] == "integer"
        assert schema["description"] == "Number of items"
        assert schema["minimum"] == 1
        assert schema["maximum"] == 100
        assert schema["default"] == 10

    def test_tool_parameter_array_schema(self):
        """Test array parameter schema."""
        param = ToolParameter(
            name="tags",
            type=ParameterType.ARRAY,
            items=ToolParameter(name="item", type=ParameterType.STRING),
        )
        schema = param.to_json_schema()

        assert schema["type"] == "array"
        assert schema["items"]["type"] == "string"

    def test_tool_parameter_object_schema(self):
        """Test object parameter schema."""
        param = ToolParameter(
            name="config",
            type=ParameterType.OBJECT,
            properties={
                "enabled": ToolParameter(name="enabled", type=ParameterType.BOOLEAN),
                "count": ToolParameter(name="count", type=ParameterType.INTEGER),
            },
        )
        schema = param.to_json_schema()

        assert schema["type"] == "object"
        assert "enabled" in schema["properties"]
        assert schema["properties"]["enabled"]["type"] == "boolean"

    def test_mcp_tool_schema(self):
        """Test MCPTool.get_mcp_schema()."""
        tool = SearchTool()
        schema = tool.get_mcp_schema()

        assert schema["name"] == "search"
        assert schema["description"] == "Search for information"
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "query" in schema["input_schema"]["properties"]
        assert "query" in schema["input_schema"]["required"]

    def test_tool_validate_arguments_success(self):
        """Test argument validation - success case."""
        tool = SearchTool()
        errors = tool.validate_arguments({"query": "test", "limit": 5})
        assert errors == []

    def test_tool_validate_arguments_missing_required(self):
        """Test argument validation - missing required."""
        tool = SearchTool()
        errors = tool.validate_arguments({"limit": 5})
        assert len(errors) == 1
        assert "Missing required parameter: query" in errors[0]

    def test_tool_validate_arguments_wrong_type(self):
        """Test argument validation - wrong type."""
        tool = SearchTool()
        errors = tool.validate_arguments({"query": 123})  # Should be string
        assert len(errors) == 1
        assert "Invalid type" in errors[0]

    def test_tool_cache_key_generation(self):
        """Test cache key is consistent."""
        tool = SearchTool()
        key1 = tool.get_cache_key({"query": "test", "limit": 10})
        key2 = tool.get_cache_key({"limit": 10, "query": "test"})  # Different order
        assert key1 == key2  # Should be same due to sorted keys


# =============================================================================
# AC-2: Tools callable from Claude, GPT, and other LLMs
# =============================================================================

class TestProviderAdapters:
    """Tests for AC-2: Provider adapters."""

    def test_claude_adapter_tools_conversion(self):
        """Test ClaudeAdapter converts tools correctly."""
        adapter = ClaudeAdapter()
        tools = [SearchTool()]
        converted = adapter.convert_tools_to_provider(tools)

        assert len(converted) == 1
        assert converted[0]["name"] == "search"
        assert "input_schema" in converted[0]

    def test_claude_adapter_tool_call_conversion(self):
        """Test ClaudeAdapter converts tool calls correctly."""
        adapter = ClaudeAdapter()
        tool_call = {
            "type": "tool_use",
            "id": "call_123",
            "name": "search",
            "input": {"query": "test"},
        }
        converted = adapter.convert_tool_call_from_provider(tool_call)

        assert converted["tool_name"] == "search"
        assert converted["call_id"] == "call_123"
        assert converted["arguments"]["query"] == "test"

    def test_claude_adapter_result_conversion(self):
        """Test ClaudeAdapter converts results correctly."""
        adapter = ClaudeAdapter()
        result = ToolResult(content={"data": "test"}, is_error=False)
        converted = adapter.convert_result_to_provider(result)

        assert converted["type"] == "tool_result"
        assert "content" in converted

    def test_openai_adapter_tools_conversion(self):
        """Test OpenAIAdapter converts tools correctly."""
        adapter = OpenAIAdapter()
        tools = [SearchTool()]
        converted = adapter.convert_tools_to_provider(tools)

        assert len(converted) == 1
        assert converted[0]["type"] == "function"
        assert converted[0]["function"]["name"] == "search"
        assert "parameters" in converted[0]["function"]

    def test_openai_adapter_tool_call_conversion(self):
        """Test OpenAIAdapter converts tool calls correctly."""
        adapter = OpenAIAdapter()
        tool_call = {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "search",
                "arguments": '{"query": "test"}',
            },
        }
        converted = adapter.convert_tool_call_from_provider(tool_call)

        assert converted["tool_name"] == "search"
        assert converted["arguments"]["query"] == "test"

    def test_openai_adapter_result_conversion(self):
        """Test OpenAIAdapter converts results correctly."""
        adapter = OpenAIAdapter()
        result = ToolResult(content="test result")
        converted = adapter.convert_result_to_provider(result)

        assert converted["role"] == "tool"
        assert "content" in converted

    def test_gemini_adapter_tools_conversion(self):
        """Test GeminiAdapter converts tools correctly."""
        adapter = GeminiAdapter()
        tools = [SearchTool()]
        converted = adapter.convert_tools_to_provider(tools)

        assert len(converted) == 1
        assert "function_declarations" in converted[0]
        assert converted[0]["function_declarations"][0]["name"] == "search"

    def test_get_adapter_function(self):
        """Test get_adapter helper function."""
        claude = get_adapter("claude")
        openai = get_adapter("openai")
        gemini = get_adapter("gemini")

        assert isinstance(claude, ClaudeAdapter)
        assert isinstance(openai, OpenAIAdapter)
        assert isinstance(gemini, GeminiAdapter)

    def test_adapters_support_streaming(self):
        """Test streaming support detection."""
        assert ClaudeAdapter().supports_streaming() is True
        assert OpenAIAdapter().supports_streaming() is True
        assert GeminiAdapter().supports_streaming() is True


class TestToolRegistry:
    """Tests for tool registry functionality."""

    def test_register_tool(self, registry):
        """Test tool registration."""
        tool = SearchTool()
        registry.register(tool)

        assert "search" in registry
        assert len(registry) == 1

    def test_register_with_category(self, registry):
        """Test tool registration with category."""
        tool = SearchTool()
        registry.register(tool, category="search")

        tools = registry.get_tools_by_category("search")
        assert len(tools) == 1
        assert tools[0].name == "search"

    def test_register_with_provider_filter(self, registry):
        """Test tool registration with provider filter."""
        tool = SearchTool()
        registry.register(tool, providers=["claude"])

        claude_tools = registry.get_tools_for_provider("claude")
        openai_tools = registry.get_tools_for_provider("openai")

        assert len(claude_tools) == 1
        assert len(openai_tools) == 1  # No filter = all tools

    def test_get_mcp_schemas(self, registry):
        """Test getting all MCP schemas."""
        registry.register(SearchTool())
        registry.register(StreamingTool())

        schemas = registry.get_mcp_schemas()
        assert len(schemas) == 2
        names = [s["name"] for s in schemas]
        assert "search" in names
        assert "generate" in names

    def test_get_openai_functions(self, registry):
        """Test getting OpenAI function format."""
        registry.register(SearchTool())

        functions = registry.get_openai_functions()
        assert len(functions) == 1
        assert functions[0]["type"] == "function"

    def test_find_tools(self, registry):
        """Test tool search."""
        registry.register(SearchTool())
        registry.register(StreamingTool())

        results = registry.find_tools("search")
        assert len(results) == 1
        assert results[0].name == "search"

    def test_unregister_tool(self, registry):
        """Test tool unregistration."""
        registry.register(SearchTool())
        assert "search" in registry

        result = registry.unregister("search")
        assert result is True
        assert "search" not in registry


# =============================================================================
# AC-3: Streaming support for long-running tools
# =============================================================================

class TestStreamingSupport:
    """Tests for AC-3: Streaming support."""

    def test_stream_chunk_creation(self):
        """Test StreamChunk dataclass."""
        chunk = StreamChunk(
            content="Hello",
            index=0,
            is_final=False,
        )
        assert chunk.content == "Hello"
        assert chunk.index == 0
        assert chunk.is_final is False

    def test_stream_chunk_to_dict(self):
        """Test StreamChunk serialization."""
        chunk = StreamChunk(content="test", index=1, is_final=True)
        data = chunk.to_dict()

        assert data["content"] == "test"
        assert data["index"] == 1
        assert data["is_final"] is True
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_tool_execute_stream(self):
        """Test streaming tool execution."""
        tool = StreamingTool()
        chunks = []

        async for chunk in tool.execute_stream(prompt="test"):
            chunks.append(chunk)

        assert len(chunks) == 4
        assert chunks[-1].is_final is True
        assert "".join(c.content for c in chunks) == "Hello world!"

    @pytest.mark.asyncio
    async def test_invoker_stream_invocation(self, invoker):
        """Test invoker streaming."""
        chunks = []

        async for chunk in invoker.invoke_stream("generate", {"prompt": "test"}):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert chunks[-1].is_final is True

    @pytest.mark.asyncio
    async def test_non_streaming_tool_wrapped(self, invoker):
        """Test non-streaming tool wrapped as stream."""
        chunks = []

        async for chunk in invoker.invoke_stream("search", {"query": "test"}):
            chunks.append(chunk)

        # Non-streaming tool returns single chunk
        assert len(chunks) == 1
        assert chunks[0].is_final is True


# =============================================================================
# AC-4: Error handling and retry logic
# =============================================================================

class TestErrorHandlingAndRetry:
    """Tests for AC-4: Error handling and retry logic."""

    def test_retry_policy_creation(self):
        """Test RetryPolicy configuration."""
        policy = RetryPolicy(
            max_retries=5,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_ms=100,
        )
        assert policy.max_retries == 5
        assert policy.strategy == RetryStrategy.EXPONENTIAL

    def test_retry_policy_delay_calculation(self):
        """Test retry delay calculation."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_ms=100,
            max_delay_ms=10000,
            jitter=False,
        )

        assert policy.get_delay_ms(1) == 100
        assert policy.get_delay_ms(2) == 200
        assert policy.get_delay_ms(3) == 400
        assert policy.get_delay_ms(10) == 10000  # Capped at max

    def test_retry_policy_linear_delay(self):
        """Test linear delay strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.LINEAR,
            base_delay_ms=100,
            jitter=False,
        )

        assert policy.get_delay_ms(1) == 100
        assert policy.get_delay_ms(2) == 200
        assert policy.get_delay_ms(3) == 300

    def test_retry_policy_fixed_delay(self):
        """Test fixed delay strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIXED,
            base_delay_ms=100,
            jitter=False,
        )

        assert policy.get_delay_ms(1) == 100
        assert policy.get_delay_ms(5) == 100  # Always same

    def test_retry_policy_is_retryable(self):
        """Test retryable error detection."""
        policy = RetryPolicy(
            retryable_errors=["timeout", "rate_limit"],
        )

        assert policy.is_retryable("timeout") is True
        assert policy.is_retryable("rate_limit") is True
        assert policy.is_retryable("validation_error") is False

    def test_tool_error_creation(self):
        """Test ToolError dataclass."""
        error = ToolError(
            code="timeout",
            message="Request timed out",
            retryable=True,
            retry_after_ms=1000,
        )
        assert error.code == "timeout"
        assert error.retryable is True
        assert error.retry_after_ms == 1000

    def test_tool_error_to_dict(self):
        """Test ToolError serialization."""
        error = ToolError(code="error", message="Test", retryable=False)
        data = error.to_dict()

        assert data["code"] == "error"
        assert data["message"] == "Test"
        assert data["retryable"] is False

    @pytest.mark.asyncio
    async def test_invoker_retry_on_failure(self, config, registry):
        """Test invoker retries on retryable errors."""
        FailingTool.fail_count = 0  # Reset counter
        registry.register(FailingTool())
        invoker = MCPToolInvoker(config=config, registry=registry)

        result = await invoker.invoke("failing", {})

        # Should succeed after retries
        assert result.content == "Success after retries"
        assert FailingTool.fail_count == 3

    @pytest.mark.asyncio
    async def test_invoker_validation_error(self, invoker):
        """Test validation error handling."""
        result = await invoker.invoke("search", {})  # Missing required query

        assert result.is_error is True
        assert "validation_errors" in result.metadata


# =============================================================================
# AC-5: Tool result caching where appropriate
# =============================================================================

class TestResultCaching:
    """Tests for AC-5: Tool result caching."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test basic cache operations."""
        cache = ToolResultCache(CacheConfig(enabled=True))

        await cache.set("search", {"query": "test"}, {"results": []})
        result = await cache.get("search", {"query": "test"})

        assert result == {"results": []}

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss."""
        cache = ToolResultCache(CacheConfig(enabled=True))

        result = await cache.get("search", {"query": "nonexistent"})
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test caching when disabled."""
        cache = ToolResultCache(CacheConfig(enabled=False))

        await cache.set("search", {"query": "test"}, {"results": []})
        result = await cache.get("search", {"query": "test"})

        assert result is None  # Not cached when disabled

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = ToolResultCache(CacheConfig(enabled=True, default_ttl_seconds=1))

        await cache.set("search", {"query": "test"}, {"results": []})

        # Should be cached
        result = await cache.get("search", {"query": "test"})
        assert result is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        result = await cache.get("search", {"query": "test"})
        assert result is None  # Expired

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = ToolResultCache(CacheConfig(enabled=True))

        await cache.set("search", {"query": "test1"}, {"results": [1]})
        await cache.set("search", {"query": "test2"}, {"results": [2]})

        # Invalidate specific entry
        count = await cache.invalidate("search", {"query": "test1"})
        assert count == 1

        # Only test2 should remain
        assert await cache.get("search", {"query": "test1"}) is None
        assert await cache.get("search", {"query": "test2"}) is not None

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing."""
        cache = ToolResultCache(CacheConfig(enabled=True))

        await cache.set("search", {"query": "test1"}, {"results": []})
        await cache.set("search", {"query": "test2"}, {"results": []})

        count = await cache.clear()
        assert count == 2

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = ToolResultCache(CacheConfig(enabled=True))

        await cache.set("search", {"query": "test"}, {"results": []})
        await cache.get("search", {"query": "test"})  # Hit
        await cache.get("search", {"query": "other"})  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = ToolResultCache(CacheConfig(enabled=True, max_entries=2))

        await cache.set("tool", {"q": "1"}, "result1")
        await cache.set("tool", {"q": "2"}, "result2")
        await cache.set("tool", {"q": "3"}, "result3")  # Should evict oldest

        # Oldest entry should be evicted
        assert await cache.get("tool", {"q": "1"}) is None
        assert await cache.get("tool", {"q": "2"}) is not None
        assert await cache.get("tool", {"q": "3"}) is not None

    @pytest.mark.asyncio
    async def test_invoker_uses_cache(self, invoker):
        """Test invoker caches results."""
        # First call - not cached
        result1 = await invoker.invoke("search", {"query": "test"})
        assert result1.cached is False

        # Second call - should be cached
        result2 = await invoker.invoke("search", {"query": "test"})
        assert result2.cached is True

    @pytest.mark.asyncio
    async def test_invoker_cache_bypass(self, invoker):
        """Test cache bypass option."""
        # First call
        await invoker.invoke("search", {"query": "test"})

        # Second call with cache bypass
        result = await invoker.invoke("search", {"query": "test"}, use_cache=False)
        assert result.cached is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for MCP module."""

    @pytest.mark.asyncio
    async def test_full_tool_lifecycle(self, config, registry):
        """Test complete tool lifecycle."""
        # Register tools
        registry.register(SearchTool(), category="search")
        registry.register(StreamingTool(), category="generation")

        # Create invoker
        invoker = MCPToolInvoker(config=config, registry=registry)

        # Get schemas for provider
        schemas = registry.get_mcp_schemas()
        assert len(schemas) == 2

        # Convert for OpenAI
        adapter = OpenAIAdapter()
        openai_tools = adapter.convert_tools_to_provider(registry.get_all_tools())
        assert len(openai_tools) == 2

        # Invoke tool
        result = await invoker.invoke("search", {"query": "hello"})
        assert result.is_error is False
        assert "results" in result.content

        # Check caching worked
        result2 = await invoker.invoke("search", {"query": "hello"})
        assert result2.cached is True

        # Stream tool
        chunks = []
        async for chunk in invoker.invoke_stream("generate", {"prompt": "test"}):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_batch_invocation(self, invoker):
        """Test batch tool invocation."""
        invocations = [
            {"tool_name": "search", "arguments": {"query": "test1"}},
            {"tool_name": "search", "arguments": {"query": "test2"}},
        ]

        results = await invoker.invoke_batch(invocations)

        assert len(results) == 2
        assert all(r.is_error is False for r in results)

    def test_config_from_env(self):
        """Test configuration from environment."""
        with patch.dict("os.environ", {
            "MCP_MAX_RETRIES": "5",
            "MCP_CACHE_TTL": "120",
            "ANTHROPIC_API_KEY": "test_key",
        }):
            config = MCPConfig.from_env()

            assert config.retry_policy.max_retries == 5
            assert config.cache.default_ttl_seconds == 120
            assert "claude" in config.providers

    def test_invoker_stats(self, invoker):
        """Test invoker statistics."""
        stats = invoker.get_stats()

        assert "invocation_count" in stats
        assert "error_count" in stats
        assert "cache_stats" in stats


# =============================================================================
# ToolResult Tests
# =============================================================================

class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_tool_result_creation(self):
        """Test ToolResult creation."""
        result = ToolResult(
            content={"data": "test"},
            content_type="application/json",
        )
        assert result.content == {"data": "test"}
        assert result.is_error is False
        assert isinstance(result.id, UUID)

    def test_tool_result_to_dict(self):
        """Test ToolResult serialization."""
        result = ToolResult(content="test", duration_ms=100)
        data = result.to_dict()

        assert data["content"] == "test"
        assert data["duration_ms"] == 100
        assert "timestamp" in data
        assert "id" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
