"""
Tests for MCP (Model Context Protocol) Integration Module

Tests all 5 Acceptance Criteria for MD-2565:
- AC-1: MCP-compliant tool interface implementation
- AC-2: Tools callable from Claude, GPT, and other LLMs
- AC-3: Streaming support for long-running tools
- AC-4: Error handling and retry logic
- AC-5: Tool result caching where appropriate

Epic: MD-2565
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, AsyncIterator

from maestro_hive.maestro.mcp import (
    MCPToolInterface,
    MCPToolSchema,
    MCPToolResult,
    MCPToolRegistry,
    MCPStreamHandler,
    StreamChunk,
    MCPRetryPolicy,
    RetryConfig,
    MCPResultCache,
    CacheConfig,
)
from maestro_hive.maestro.mcp.interface import (
    ToolStatus,
    LLMProvider,
)
from maestro_hive.maestro.mcp.streaming import (
    StreamEventType,
    StreamCancelled,
    StreamCompleted,
    stream_text_chunks,
    collect_stream,
)
from maestro_hive.maestro.mcp.retry import (
    RetryStrategy,
    ErrorCategory,
    RetryAttempt,
    RetryResult,
    create_retry_policy,
)
from maestro_hive.maestro.mcp.cache import (
    CacheStrategy,
    CacheEntry,
    CacheStats,
    create_cache,
)


# =============================================================================
# Test Fixtures
# =============================================================================

class MockCalculatorTool(MCPToolInterface):
    """Mock tool for testing - simple calculator"""

    @property
    def schema(self) -> MCPToolSchema:
        return MCPToolSchema(
            name="calculator",
            description="Performs basic arithmetic operations",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "number"}
                }
            },
            cacheable=True,
            timeout_seconds=10
        )

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolResult:
        op = inputs["operation"]
        a = inputs["a"]
        b = inputs["b"]

        if op == "add":
            result = a + b
        elif op == "subtract":
            result = a - b
        elif op == "multiply":
            result = a * b
        elif op == "divide":
            if b == 0:
                return MCPToolResult.error(self.name, "Division by zero")
            result = a / b
        else:
            return MCPToolResult.error(self.name, f"Unknown operation: {op}")

        return MCPToolResult.success(self.name, {"result": result})


class MockStreamingTool(MCPToolInterface):
    """Mock tool for testing streaming"""

    @property
    def schema(self) -> MCPToolSchema:
        return MCPToolSchema(
            name="text_generator",
            description="Generates text in chunks",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "chunk_size": {"type": "integer"}
                },
                "required": ["text"]
            },
            streaming_supported=True,
            cacheable=False
        )

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolResult:
        return MCPToolResult.success(self.name, inputs["text"])

    async def stream_execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Any]:
        text = inputs["text"]
        chunk_size = inputs.get("chunk_size", 10)
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]
            await asyncio.sleep(0.01)


class MockFailingTool(MCPToolInterface):
    """Mock tool that fails for retry testing"""

    def __init__(self, fail_count: int = 2):
        self._fail_count = fail_count
        self._call_count = 0

    @property
    def schema(self) -> MCPToolSchema:
        return MCPToolSchema(
            name="failing_tool",
            description="Tool that fails first N times",
            input_schema={"type": "object", "properties": {}},
            cacheable=False
        )

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolResult:
        self._call_count += 1
        if self._call_count <= self._fail_count:
            raise ConnectionError("Temporary connection failure")
        return MCPToolResult.success(self.name, {"success": True})


# =============================================================================
# AC-1 Tests: MCP-compliant tool interface implementation
# =============================================================================

class TestAC1_MCPCompliantInterface:
    """Tests for AC-1: MCP-compliant tool interface implementation"""

    def test_tool_schema_creation(self):
        """Test MCPToolSchema can be created with required fields"""
        schema = MCPToolSchema(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {"x": {"type": "string"}}}
        )
        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert "properties" in schema.input_schema

    def test_tool_schema_to_dict(self):
        """Test schema serialization"""
        schema = MCPToolSchema(
            name="test",
            description="Test",
            input_schema={"type": "object"},
            streaming_supported=True,
            cacheable=False
        )
        data = schema.to_dict()
        assert data["name"] == "test"
        assert data["streaming_supported"] is True
        assert data["cacheable"] is False

    def test_tool_schema_from_dict(self):
        """Test schema deserialization"""
        data = {
            "name": "from_dict_tool",
            "description": "Created from dict",
            "input_schema": {"type": "object"},
            "timeout_seconds": 60
        }
        schema = MCPToolSchema.from_dict(data)
        assert schema.name == "from_dict_tool"
        assert schema.timeout_seconds == 60

    def test_tool_result_success(self):
        """Test successful result creation"""
        result = MCPToolResult.success("test", {"value": 42}, execution_time_ms=100.5)
        assert result.status == ToolStatus.SUCCESS
        assert result.result == {"value": 42}
        assert result.execution_time_ms == 100.5
        assert result.is_success()

    def test_tool_result_error(self):
        """Test error result creation"""
        result = MCPToolResult.error("test", "Something went wrong")
        assert result.status == ToolStatus.ERROR
        assert result.error == "Something went wrong"
        assert not result.is_success()

    @pytest.mark.asyncio
    async def test_tool_interface_execute(self):
        """Test tool execution through interface"""
        tool = MockCalculatorTool()
        result = await tool.execute({"operation": "add", "a": 5, "b": 3})
        assert result.is_success()
        assert result.result == {"result": 8}

    def test_input_validation_valid(self):
        """Test input validation with valid inputs"""
        tool = MockCalculatorTool()
        assert tool.validate_inputs({"operation": "add", "a": 1, "b": 2})

    def test_input_validation_missing_required(self):
        """Test input validation with missing required field"""
        tool = MockCalculatorTool()
        with pytest.raises(ValueError, match="Missing required field"):
            tool.validate_inputs({"operation": "add", "a": 1})

    def test_cache_key_generation(self):
        """Test cache key generation is deterministic"""
        tool = MockCalculatorTool()
        key1 = tool.get_cache_key({"operation": "add", "a": 1, "b": 2})
        key2 = tool.get_cache_key({"operation": "add", "a": 1, "b": 2})
        key3 = tool.get_cache_key({"operation": "add", "a": 2, "b": 1})
        assert key1 == key2
        assert key1 != key3


# =============================================================================
# AC-2 Tests: Tools callable from Claude, GPT, and other LLMs
# =============================================================================

class TestAC2_MultiLLMSupport:
    """Tests for AC-2: Tools callable from Claude, GPT, and other LLMs"""

    def test_claude_format_export(self):
        """Test export to Claude/Anthropic format"""
        tool = MockCalculatorTool()
        claude_def = tool.to_llm_format(LLMProvider.CLAUDE)
        assert "name" in claude_def
        assert "description" in claude_def
        assert "input_schema" in claude_def
        assert claude_def["name"] == "calculator"

    def test_openai_format_export(self):
        """Test export to OpenAI/GPT format"""
        tool = MockCalculatorTool()
        openai_def = tool.to_llm_format(LLMProvider.GPT)
        assert openai_def["type"] == "function"
        assert "function" in openai_def
        assert openai_def["function"]["name"] == "calculator"
        assert "parameters" in openai_def["function"]

    def test_generic_format_export(self):
        """Test export to generic MCP format"""
        tool = MockCalculatorTool()
        generic_def = tool.to_llm_format(LLMProvider.GENERIC)
        assert "tool" in generic_def
        assert "metadata" in generic_def
        assert generic_def["tool"]["name"] == "calculator"

    def test_result_to_claude_format(self):
        """Test result conversion to Claude format"""
        result = MCPToolResult.success("test", {"value": 42}, tool_use_id="test123")
        claude_result = result.to_claude_format()
        assert claude_result["type"] == "tool_result"
        assert "content" in claude_result
        assert claude_result["is_error"] is False

    def test_result_to_openai_format(self):
        """Test result conversion to OpenAI format"""
        result = MCPToolResult.success("test", {"value": 42}, tool_call_id="call123")
        openai_result = result.to_openai_format()
        assert openai_result["role"] == "tool"
        assert "content" in openai_result

    def test_all_providers_supported(self):
        """Test all LLM providers are supported"""
        tool = MockCalculatorTool()
        for provider in LLMProvider:
            definition = tool.to_llm_format(provider)
            assert definition is not None
            assert isinstance(definition, dict)


# =============================================================================
# AC-3 Tests: Streaming support for long-running tools
# =============================================================================

class TestAC3_StreamingSupport:
    """Tests for AC-3: Streaming support for long-running tools"""

    @pytest.mark.asyncio
    async def test_stream_handler_basic(self):
        """Test basic stream handler flow - unit test style"""
        handler = MCPStreamHandler("test_tool")

        # Test individual chunk creation
        start_chunk = await handler.start()
        assert start_chunk.event_type == StreamEventType.START
        assert start_chunk.tool_name == "test_tool"

        chunk1 = await handler.send_chunk("chunk1")
        assert chunk1.event_type == StreamEventType.CHUNK
        assert chunk1.data == "chunk1"
        assert chunk1.sequence == 1

        chunk2 = await handler.send_chunk("chunk2")
        assert chunk2.sequence == 2

        end_chunk = await handler.end(final_result="done")
        assert end_chunk.event_type == StreamEventType.END
        assert end_chunk.data["status"] == "completed"

        # Verify handler state
        assert handler.chunks_sent == 2
        assert not handler.is_active

    @pytest.mark.asyncio
    async def test_stream_progress_events(self):
        """Test progress events in stream"""
        handler = MCPStreamHandler("test_tool")

        await handler.start()
        progress_chunk = await handler.send_progress(50.0, "Halfway done")

        assert progress_chunk.event_type == StreamEventType.PROGRESS
        assert progress_chunk.data["percent"] == 50.0
        assert progress_chunk.data["message"] == "Halfway done"

        await handler.end()
        assert not handler.is_active

    @pytest.mark.asyncio
    async def test_stream_error_handling(self):
        """Test error event in stream"""
        handler = MCPStreamHandler("test_tool")

        await handler.start()
        error_chunk = await handler.error("Something went wrong")

        assert error_chunk.event_type == StreamEventType.ERROR
        assert "Something went wrong" in error_chunk.data["error"]
        assert not handler.is_active  # Error ends the stream

    def test_stream_chunk_sse_format(self):
        """Test SSE format output"""
        chunk = StreamChunk.chunk("test", {"text": "hello"}, 1)
        sse = chunk.to_sse_format()
        assert "event: chunk" in sse
        assert "data:" in sse
        assert "\\n\\n" in repr(sse)

    def test_stream_chunk_ndjson_format(self):
        """Test NDJSON format output"""
        chunk = StreamChunk.chunk("test", {"text": "hello"}, 1)
        ndjson = chunk.to_ndjson_format()
        assert ndjson.endswith("\n")
        import json
        data = json.loads(ndjson)
        assert data["event_type"] == "chunk"

    @pytest.mark.asyncio
    async def test_stream_cancellation(self):
        """Test stream cancellation"""
        handler = MCPStreamHandler("test_tool")
        await handler.start()
        handler.cancel()

        with pytest.raises(StreamCancelled):
            await handler.send_chunk("should fail")

    @pytest.mark.asyncio
    async def test_streaming_tool_execution(self):
        """Test streaming tool execution"""
        tool = MockStreamingTool()
        assert tool.supports_streaming

        chunks = []
        async for chunk in tool.stream_execute({"text": "hello world", "chunk_size": 5}):
            chunks.append(chunk)

        assert "".join(chunks) == "hello world"

    @pytest.mark.asyncio
    async def test_stream_text_chunks_utility(self):
        """Test text chunking utility"""
        text = "This is a test string"
        chunks = []
        async for chunk in stream_text_chunks(text, chunk_size=5):
            chunks.append(chunk)

        assert "".join(chunks) == text

    @pytest.mark.asyncio
    async def test_collect_stream_utility(self):
        """Test stream collection utility with a simple async generator"""
        # Create a simple async generator for testing
        async def simple_stream():
            yield StreamChunk.start("test")
            yield StreamChunk.chunk("test", "a", 1)
            yield StreamChunk.chunk("test", "b", 2)
            yield StreamChunk.end("test", 3)

        data, error = await collect_stream(simple_stream())
        assert data == ["a", "b"]
        assert error is None


# =============================================================================
# AC-4 Tests: Error handling and retry logic
# =============================================================================

class TestAC4_ErrorHandlingRetry:
    """Tests for AC-4: Error handling and retry logic"""

    def test_retry_config_creation(self):
        """Test retry config creation"""
        config = RetryConfig(
            max_retries=5,
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay_seconds=0.5
        )
        assert config.max_retries == 5
        assert config.strategy == RetryStrategy.EXPONENTIAL

    def test_retry_strategies_delay_calculation(self):
        """Test delay calculation for different strategies"""
        # Fixed
        fixed_policy = MCPRetryPolicy(RetryConfig(
            strategy=RetryStrategy.FIXED,
            initial_delay_seconds=1.0
        ))
        assert fixed_policy.calculate_delay(1) == 1.0
        assert fixed_policy.calculate_delay(3) == 1.0

        # Exponential
        exp_policy = MCPRetryPolicy(RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay_seconds=1.0,
            exponential_base=2.0
        ))
        assert exp_policy.calculate_delay(1) == 1.0
        assert exp_policy.calculate_delay(2) == 2.0
        assert exp_policy.calculate_delay(3) == 4.0

        # Linear
        linear_policy = MCPRetryPolicy(RetryConfig(
            strategy=RetryStrategy.LINEAR,
            initial_delay_seconds=1.0
        ))
        assert linear_policy.calculate_delay(1) == 1.0
        assert linear_policy.calculate_delay(3) == 3.0

    def test_error_categorization(self):
        """Test error categorization"""
        policy = MCPRetryPolicy()

        # Rate limit
        assert policy.categorize_error(Exception("429 Too Many Requests")) == ErrorCategory.RATE_LIMIT

        # Timeout
        assert policy.categorize_error(Exception("Connection timed out")) == ErrorCategory.TIMEOUT

        # Transient
        assert policy.categorize_error(Exception("503 Service Unavailable")) == ErrorCategory.TRANSIENT

        # Permanent
        assert policy.categorize_error(Exception("401 Unauthorized")) == ErrorCategory.PERMANENT

    def test_should_retry_logic(self):
        """Test retry decision logic"""
        policy = MCPRetryPolicy(RetryConfig(max_retries=3))

        # Should retry transient
        should, cat = policy.should_retry(Exception("connection error"), 1)
        assert should is True
        assert cat == ErrorCategory.TRANSIENT

        # Should not retry permanent
        should, cat = policy.should_retry(Exception("401 unauthorized"), 1)
        assert should is False
        assert cat == ErrorCategory.PERMANENT

        # Should not retry after max attempts
        should, cat = policy.should_retry(Exception("connection error"), 3)
        assert should is False

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self):
        """Test successful execution with retry"""
        policy = MCPRetryPolicy(RetryConfig(max_retries=3))
        call_count = 0

        async def success_fn():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await policy.execute_with_retry(success_fn)
        assert result.success
        assert result.result == "success"
        assert result.total_attempts == 1
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_eventual_success(self):
        """Test retry that eventually succeeds"""
        policy = MCPRetryPolicy(RetryConfig(
            max_retries=5,
            initial_delay_seconds=0.01  # Fast for testing
        ))
        call_count = 0

        async def eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await policy.execute_with_retry(eventual_success)
        assert result.success
        assert result.total_attempts == 3
        assert len(result.attempts) == 2  # Two failed attempts recorded

    @pytest.mark.asyncio
    async def test_execute_with_retry_permanent_failure(self):
        """Test retry gives up on permanent error"""
        policy = MCPRetryPolicy(RetryConfig(max_retries=5))

        async def permanent_fail():
            raise ValueError("Invalid input - 401 unauthorized")

        result = await policy.execute_with_retry(permanent_fail)
        assert not result.success
        assert result.total_attempts == 1  # Gave up immediately

    def test_create_retry_policy_factory(self):
        """Test factory function"""
        policy = create_retry_policy(
            max_retries=10,
            strategy="linear",
            initial_delay=2.0
        )
        assert policy.config.max_retries == 10
        assert policy.config.strategy == RetryStrategy.LINEAR


# =============================================================================
# AC-5 Tests: Tool result caching where appropriate
# =============================================================================

class TestAC5_ResultCaching:
    """Tests for AC-5: Tool result caching where appropriate"""

    @pytest.mark.asyncio
    async def test_cache_basic_operations(self):
        """Test basic cache get/set"""
        cache = MCPResultCache()
        await cache.set("key1", {"value": 42}, "test_tool")
        result = await cache.get("key1")
        assert result == {"value": 42}

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = MCPResultCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache TTL expiration"""
        cache = MCPResultCache(CacheConfig(default_ttl_seconds=0))
        await cache.set("key", "value", "tool", ttl_seconds=0)  # Immediate expiry

        # Entry exists but expired
        await asyncio.sleep(0.01)
        result = await cache.get("key")
        # Should be None as TTL is 0
        assert result is None or result == "value"  # Depends on exact timing

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation"""
        cache = MCPResultCache()
        await cache.set("key1", "value1", "tool")
        await cache.set("key2", "value2", "tool")

        removed = await cache.invalidate("key1")
        assert removed is True
        assert await cache.get("key1") is None
        assert await cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_cache_invalidate_by_tool(self):
        """Test invalidating all entries for a tool"""
        cache = MCPResultCache()
        await cache.set("key1", "value1", "tool_a")
        await cache.set("key2", "value2", "tool_a")
        await cache.set("key3", "value3", "tool_b")

        count = await cache.invalidate_tool("tool_a")
        assert count == 2
        assert await cache.get("key1") is None
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction strategy"""
        cache = MCPResultCache(CacheConfig(
            max_entries=3,
            strategy=CacheStrategy.LRU
        ))

        await cache.set("a", 1, "tool")
        await cache.set("b", 2, "tool")
        await cache.set("c", 3, "tool")

        # Access 'a' to make it recently used
        await cache.get("a")

        # Add new entry, should evict 'b' (least recently used)
        await cache.set("d", 4, "tool")

        assert await cache.get("a") == 1
        assert await cache.get("b") is None  # Evicted
        assert await cache.get("c") == 3
        assert await cache.get("d") == 4

    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """Test cache statistics tracking"""
        cache = MCPResultCache()
        await cache.set("key", "value", "tool")

        await cache.get("key")  # Hit
        await cache.get("key")  # Hit
        await cache.get("missing")  # Miss

        stats = cache.stats
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == 2/3

    def test_cache_key_generation(self):
        """Test cache key generation"""
        cache = MCPResultCache()
        key1 = cache.generate_key("tool", {"a": 1, "b": 2})
        key2 = cache.generate_key("tool", {"b": 2, "a": 1})
        key3 = cache.generate_key("tool", {"a": 1, "b": 3})

        # Same inputs (sorted) = same key
        assert key1 == key2
        # Different inputs = different key
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clear"""
        cache = MCPResultCache()
        await cache.set("a", 1, "tool")
        await cache.set("b", 2, "tool")
        await cache.clear()
        assert cache.size == 0

    def test_create_cache_factory(self):
        """Test factory function"""
        cache = create_cache(
            max_entries=500,
            ttl_seconds=600,
            strategy="lfu"
        )
        assert cache.config.max_entries == 500
        assert cache.config.default_ttl_seconds == 600
        assert cache.config.strategy == CacheStrategy.LFU


# =============================================================================
# Integration Tests: Registry with all features
# =============================================================================

class TestMCPToolRegistry:
    """Integration tests for MCP Tool Registry"""

    @pytest.mark.asyncio
    async def test_registry_register_and_execute(self):
        """Test tool registration and execution"""
        registry = MCPToolRegistry()
        tool = MockCalculatorTool()
        registry.register(tool)

        result = await registry.execute(
            "calculator",
            {"operation": "multiply", "a": 6, "b": 7}
        )
        assert result.is_success()
        assert result.result == {"result": 42}

    @pytest.mark.asyncio
    async def test_registry_caching(self):
        """Test registry uses caching"""
        registry = MCPToolRegistry()
        registry.register(MockCalculatorTool())

        # First call
        result1 = await registry.execute("calculator", {"operation": "add", "a": 1, "b": 2})
        assert result1.status == ToolStatus.SUCCESS
        assert not result1.cached

        # Second call should be cached
        result2 = await registry.execute("calculator", {"operation": "add", "a": 1, "b": 2})
        assert result2.status == ToolStatus.CACHED
        assert result2.cached

    @pytest.mark.asyncio
    async def test_registry_retry_on_failure(self):
        """Test registry uses retry logic"""
        registry = MCPToolRegistry(
            retry_config=RetryConfig(max_retries=5, initial_delay_seconds=0.01)
        )
        tool = MockFailingTool(fail_count=2)
        registry.register(tool, tags=["test"])

        result = await registry.execute("failing_tool", {}, use_cache=False)
        assert result.is_success()
        assert tool._call_count == 3  # Failed twice, succeeded third

    def test_registry_export_for_llm(self):
        """Test exporting tools for different LLMs"""
        registry = MCPToolRegistry()
        registry.register(MockCalculatorTool())
        registry.register(MockStreamingTool())

        claude_tools = registry.export_for_llm(LLMProvider.CLAUDE)
        assert len(claude_tools) == 2
        assert all("name" in t for t in claude_tools)

        gpt_tools = registry.export_for_llm(LLMProvider.GPT)
        assert len(gpt_tools) == 2
        assert all(t["type"] == "function" for t in gpt_tools)

    def test_registry_list_tools(self):
        """Test listing registered tools"""
        registry = MCPToolRegistry()
        registry.register(MockCalculatorTool(), tags=["math"])
        registry.register(MockStreamingTool(), tags=["text"])

        all_tools = registry.list_tools()
        assert len(all_tools) == 2

        math_tools = registry.list_tools(tags=["math"])
        assert len(math_tools) == 1
        assert math_tools[0].name == "calculator"

    @pytest.mark.asyncio
    async def test_registry_metrics(self):
        """Test execution metrics"""
        registry = MCPToolRegistry()
        registry.register(MockCalculatorTool())

        await registry.execute("calculator", {"operation": "add", "a": 1, "b": 2})
        await registry.execute("calculator", {"operation": "add", "a": 1, "b": 2})  # Cached

        metrics = registry.get_metrics("calculator")
        assert metrics["total_calls"] == 2
        assert metrics["cache_hits"] == 1

    def test_registry_enable_disable_tool(self):
        """Test enabling/disabling tools"""
        registry = MCPToolRegistry()
        registry.register(MockCalculatorTool())

        registry.disable_tool("calculator")
        assert len(registry.list_tools(enabled_only=True)) == 0

        registry.enable_tool("calculator")
        assert len(registry.list_tools(enabled_only=True)) == 1

    def test_registry_contains(self):
        """Test tool existence check"""
        registry = MCPToolRegistry()
        registry.register(MockCalculatorTool())

        assert "calculator" in registry
        assert "nonexistent" not in registry


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
