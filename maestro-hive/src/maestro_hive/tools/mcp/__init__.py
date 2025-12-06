"""
MCP (Model Context Protocol) Integration Module

EPIC: MD-2565
[TOOL-FRAMEWORK] MCP Integration - Standard Tool Protocol

Provides a standardized tool interface for AI providers, enabling consistent
tool invocation across Claude, GPT, and other LLMs.

Acceptance Criteria:
- AC-1: MCP-compliant tool interface implementation
- AC-2: Tools callable from Claude, GPT, and other LLMs
- AC-3: Streaming support for long-running tools
- AC-4: Error handling and retry logic
- AC-5: Tool result caching where appropriate
"""

from .models import (
    MCPTool,
    ToolParameter,
    ToolResult,
    ToolError,
    StreamChunk,
    ParameterType,
)
from .config import MCPConfig, RetryPolicy
from .registry import MCPToolRegistry
from .invoker import MCPToolInvoker
from .cache import ToolResultCache
from .adapters import ProviderAdapter, ClaudeAdapter, OpenAIAdapter

__all__ = [
    # Core models
    "MCPTool",
    "ToolParameter",
    "ToolResult",
    "ToolError",
    "StreamChunk",
    "ParameterType",
    # Configuration
    "MCPConfig",
    "RetryPolicy",
    # Main components
    "MCPToolRegistry",
    "MCPToolInvoker",
    "ToolResultCache",
    # Provider adapters
    "ProviderAdapter",
    "ClaudeAdapter",
    "OpenAIAdapter",
]
