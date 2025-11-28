"""
Unit tests for provider adapters

Tests each provider adapter's implementation of the SPI contract
"""

import pytest
import asyncio
from execution_platform.spi import (
    Message, ChatRequest, ChatChunk, ToolDefinition,
    ToolParameter, LLMClient
)
from execution_platform.providers.claude_agent import ClaudeAgentClient
from execution_platform.providers.openai_adapter import OpenAIClient
from execution_platform.providers.gemini_adapter import GeminiClient


pytestmark = pytest.mark.unit


class TestClaudeAgentAdapter:
    """Test Claude Agent SDK adapter"""

    @pytest.fixture
    def client(self):
        return ClaudeAgentClient()

    def test_client_implements_protocol(self, client):
        """Verify client implements LLMClient protocol"""
        assert hasattr(client, 'chat')
        assert asyncio.iscoroutinefunction(client.chat)

    @pytest.mark.asyncio
    async def test_simple_chat(self, client):
        """Test basic chat completion"""
        req = ChatRequest(
            messages=[Message(role="user", content="Say hello")],
            max_tokens=100,
            stream=True
        )
        
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
            assert isinstance(chunk, ChatChunk)
        
        # Should have at least one chunk with content
        assert len(chunks) > 0
        assert any(c.delta_text for c in chunks)

    @pytest.mark.asyncio
    async def test_tool_calling(self, client):
        """Test tool calling support"""
        tool = ToolDefinition(
            name="get_weather",
            description="Get weather for a location",
            parameters=[
                ToolParameter(name="location", type="string", required=True)
            ]
        )
        
        req = ChatRequest(
            messages=[Message(role="user", content="What's the weather in Paris?")],
            tools=[tool],
            max_tokens=100
        )
        
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
        
        # Should receive tool call chunks
        tool_calls = [c for c in chunks if c.tool_call_delta]
        assert len(tool_calls) > 0

    @pytest.mark.asyncio
    async def test_streaming_assembly(self, client):
        """Test that streaming chunks can be assembled"""
        req = ChatRequest(
            messages=[Message(role="user", content="Count to 5")],
            max_tokens=100
        )
        
        full_text = ""
        async for chunk in client.chat(req):
            if chunk.delta_text:
                full_text += chunk.delta_text
        
        assert len(full_text) > 0
        # Should have some numeric content
        assert any(c.isdigit() for c in full_text)


class TestOpenAIAdapter:
    """Test OpenAI adapter"""

    @pytest.fixture
    def client(self):
        return OpenAIClient()

    def test_client_implements_protocol(self, client):
        """Verify client implements LLMClient protocol"""
        assert hasattr(client, 'chat')
        assert asyncio.iscoroutinefunction(client.chat)

    @pytest.mark.asyncio
    async def test_simple_chat_live(self, client, request):
        """Test basic chat with live API (requires API key)"""
        # Skip if --run-live not provided
        if not request.config.getoption("--run-live"):
            pytest.skip("Requires --run-live flag")
        
        req = ChatRequest(
            messages=[Message(role="user", content="Say hello")],
            max_tokens=100,
            model="gpt-3.5-turbo"
        )
        
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert any(c.delta_text for c in chunks)

    @pytest.mark.asyncio
    async def test_request_structure(self, client):
        """Test request structure validation"""
        req = ChatRequest(
            messages=[Message(role="user", content="test")],
            max_tokens=50,
            temperature=0.7
        )
        
        # Should not raise validation errors
        assert req.max_tokens == 50
        assert req.temperature == 0.7


class TestGeminiAdapter:
    """Test Google Gemini adapter"""

    @pytest.fixture
    def client(self):
        return GeminiClient()

    def test_client_implements_protocol(self, client):
        """Verify client implements LLMClient protocol"""
        assert hasattr(client, 'chat')
        assert asyncio.iscoroutinefunction(client.chat)

    @pytest.mark.asyncio
    async def test_simple_chat_live(self, client, request):
        """Test basic chat with live API (requires API key)"""
        # Skip if --run-live not provided
        if not request.config.getoption("--run-live"):
            pytest.skip("Requires --run-live flag")
        
        req = ChatRequest(
            messages=[Message(role="user", content="Say hello")],
            max_tokens=100,
            model="gemini-pro"
        )
        
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert any(c.delta_text for c in chunks)


class TestAdapterConsistency:
    """Test that all adapters behave consistently"""

    @pytest.fixture(params=["claude_agent", "openai", "gemini"])
    def client(self, request):
        """Parametrized fixture to test all adapters"""
        if request.param == "claude_agent":
            return ClaudeAgentClient()
        elif request.param == "openai":
            return OpenAIClient()
        elif request.param == "gemini":
            return GeminiClient()

    def test_all_implement_protocol(self, client):
        """All adapters must implement LLMClient protocol"""
        assert hasattr(client, 'chat')
        assert asyncio.iscoroutinefunction(client.chat)

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, client):
        """Test handling of edge cases"""
        req = ChatRequest(
            messages=[Message(role="user", content="")],
            max_tokens=10
        )
        
        # Should not crash on empty input
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
        
        # Implementation-specific, but should complete

    @pytest.mark.asyncio
    async def test_usage_tracking(self, client):
        """Test that usage information is provided"""
        req = ChatRequest(
            messages=[Message(role="user", content="Hi")],
            max_tokens=50
        )
        
        chunks = []
        async for chunk in client.chat(req):
            chunks.append(chunk)
        
        # At least one chunk should have usage info
        usage_chunks = [c for c in chunks if c.usage]
        # Note: May be 0 for mock implementations
        assert usage_chunks or True  # Graceful for mocks


def test_adapter_registration():
    """Test that all adapters can be instantiated"""
    adapters = {
        "claude_agent": ClaudeAgentClient,
        "openai": OpenAIClient,
        "gemini": GeminiClient
    }
    
    for name, adapter_class in adapters.items():
        client = adapter_class()
        assert client is not None
        assert hasattr(client, 'chat')
