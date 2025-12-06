"""
Provider Adapters for MCP Integration

EPIC: MD-2565
AC-2: Tools callable from Claude, GPT, and other LLMs

Provides adapters to convert between MCP tool format and provider-specific formats.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json
import logging

from .models import MCPTool, ToolResult, ToolError
from .registry import MCPToolRegistry

logger = logging.getLogger(__name__)


class ProviderAdapter(ABC):
    """
    Base class for LLM provider adapters (AC-2).

    Adapters convert between MCP format and provider-specific formats.
    """

    provider_name: str = ""

    @abstractmethod
    def convert_tools_to_provider(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """Convert MCP tools to provider format."""
        pass

    @abstractmethod
    def convert_tool_call_from_provider(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Convert provider tool call to MCP format."""
        pass

    @abstractmethod
    def convert_result_to_provider(self, result: ToolResult) -> Dict[str, Any]:
        """Convert MCP result to provider format."""
        pass

    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming tool calls."""
        return False


class ClaudeAdapter(ProviderAdapter):
    """
    Adapter for Claude/Anthropic API (AC-2).

    Claude uses MCP format natively, so minimal conversion needed.
    """

    provider_name = "claude"

    def convert_tools_to_provider(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """
        Convert tools to Claude format.

        Claude uses MCP-compatible format with 'input_schema'.
        """
        return [tool.get_mcp_schema() for tool in tools]

    def convert_tool_call_from_provider(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Claude tool call to MCP format.

        Claude format:
        {
            "type": "tool_use",
            "id": "...",
            "name": "tool_name",
            "input": {...}
        }
        """
        return {
            "tool_name": tool_call.get("name", ""),
            "call_id": tool_call.get("id", ""),
            "arguments": tool_call.get("input", {}),
        }

    def convert_result_to_provider(self, result: ToolResult) -> Dict[str, Any]:
        """
        Convert result to Claude format.

        Claude expects tool_result format:
        {
            "type": "tool_result",
            "tool_use_id": "...",
            "content": "..."
        }
        """
        content = result.content
        if not isinstance(content, str):
            content = json.dumps(content, default=str)

        response = {
            "type": "tool_result",
            "tool_use_id": str(result.id),
            "content": content,
        }

        if result.is_error:
            response["is_error"] = True

        return response

    def supports_streaming(self) -> bool:
        """Claude supports streaming."""
        return True


class OpenAIAdapter(ProviderAdapter):
    """
    Adapter for OpenAI API (AC-2).

    Converts between MCP and OpenAI function calling format.
    """

    provider_name = "openai"

    def convert_tools_to_provider(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """
        Convert tools to OpenAI function format.

        OpenAI uses:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        functions = []

        for tool in tools:
            mcp_schema = tool.get_mcp_schema()
            functions.append({
                "type": "function",
                "function": {
                    "name": mcp_schema["name"],
                    "description": mcp_schema["description"],
                    "parameters": mcp_schema["input_schema"],
                }
            })

        return functions

    def convert_tool_call_from_provider(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert OpenAI tool call to MCP format.

        OpenAI format:
        {
            "id": "call_...",
            "type": "function",
            "function": {
                "name": "...",
                "arguments": "..." (JSON string)
            }
        }
        """
        function = tool_call.get("function", {})
        arguments_str = function.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {"raw": arguments_str}

        return {
            "tool_name": function.get("name", ""),
            "call_id": tool_call.get("id", ""),
            "arguments": arguments,
        }

    def convert_result_to_provider(self, result: ToolResult) -> Dict[str, Any]:
        """
        Convert result to OpenAI format.

        OpenAI expects:
        {
            "role": "tool",
            "tool_call_id": "...",
            "content": "..."
        }
        """
        content = result.content
        if not isinstance(content, str):
            content = json.dumps(content, default=str)

        return {
            "role": "tool",
            "tool_call_id": str(result.id),
            "content": content,
        }

    def supports_streaming(self) -> bool:
        """OpenAI supports streaming."""
        return True


class GeminiAdapter(ProviderAdapter):
    """
    Adapter for Google Gemini API (AC-2).

    Converts between MCP and Gemini function calling format.
    """

    provider_name = "gemini"

    def convert_tools_to_provider(self, tools: List[MCPTool]) -> List[Dict[str, Any]]:
        """
        Convert tools to Gemini function format.

        Gemini uses:
        {
            "function_declarations": [{
                "name": "...",
                "description": "...",
                "parameters": {...}
            }]
        }
        """
        declarations = []

        for tool in tools:
            mcp_schema = tool.get_mcp_schema()
            declarations.append({
                "name": mcp_schema["name"],
                "description": mcp_schema["description"],
                "parameters": mcp_schema["input_schema"],
            })

        return [{"function_declarations": declarations}]

    def convert_tool_call_from_provider(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Gemini tool call to MCP format.

        Gemini format:
        {
            "functionCall": {
                "name": "...",
                "args": {...}
            }
        }
        """
        function_call = tool_call.get("functionCall", {})

        return {
            "tool_name": function_call.get("name", ""),
            "call_id": "",  # Gemini doesn't use call IDs
            "arguments": function_call.get("args", {}),
        }

    def convert_result_to_provider(self, result: ToolResult) -> Dict[str, Any]:
        """
        Convert result to Gemini format.

        Gemini expects:
        {
            "functionResponse": {
                "name": "...",
                "response": {...}
            }
        }
        """
        content = result.content
        if isinstance(content, str):
            content = {"text": content}

        return {
            "functionResponse": {
                "name": result.metadata.get("tool_name", ""),
                "response": content,
            }
        }

    def supports_streaming(self) -> bool:
        """Gemini supports streaming."""
        return True


class AdapterRegistry:
    """
    Registry for provider adapters.

    Allows dynamic registration and lookup of adapters.
    """

    def __init__(self):
        self._adapters: Dict[str, ProviderAdapter] = {}

        # Register default adapters
        self.register(ClaudeAdapter())
        self.register(OpenAIAdapter())
        self.register(GeminiAdapter())

    def register(self, adapter: ProviderAdapter) -> None:
        """Register a provider adapter."""
        self._adapters[adapter.provider_name] = adapter
        logger.info(f"Registered adapter: {adapter.provider_name}")

    def get(self, provider: str) -> Optional[ProviderAdapter]:
        """Get adapter for a provider."""
        return self._adapters.get(provider.lower())

    def get_all(self) -> Dict[str, ProviderAdapter]:
        """Get all registered adapters."""
        return self._adapters.copy()

    def supports(self, provider: str) -> bool:
        """Check if provider is supported."""
        return provider.lower() in self._adapters


# Global adapter registry
_adapter_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry."""
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
    return _adapter_registry


def get_adapter(provider: str) -> Optional[ProviderAdapter]:
    """Get adapter for a provider."""
    return get_adapter_registry().get(provider)
