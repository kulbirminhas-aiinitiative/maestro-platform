"""
MCP (Model Context Protocol) Integration Module

Provides standardized tool invocation across all AI providers:
- MCP-compliant tool interface (AC-1)
- Multi-LLM support: Claude, GPT, others (AC-2)
- Streaming support for long-running tools (AC-3)
- Error handling and retry logic (AC-4)
- Tool result caching (AC-5)

Epic: MD-2565 - MCP Integration - Standard Tool Protocol
"""

from .interface import MCPToolInterface, MCPToolSchema, MCPToolResult
from .registry import MCPToolRegistry
from .streaming import MCPStreamHandler, StreamChunk
from .retry import MCPRetryPolicy, RetryConfig
from .cache import MCPResultCache, CacheConfig

__all__ = [
    # Core interface (AC-1)
    "MCPToolInterface",
    "MCPToolSchema",
    "MCPToolResult",
    # Registry
    "MCPToolRegistry",
    # Streaming (AC-3)
    "MCPStreamHandler",
    "StreamChunk",
    # Retry (AC-4)
    "MCPRetryPolicy",
    "RetryConfig",
    # Cache (AC-5)
    "MCPResultCache",
    "CacheConfig",
]
