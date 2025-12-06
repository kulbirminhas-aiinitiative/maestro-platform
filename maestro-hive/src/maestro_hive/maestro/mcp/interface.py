"""
MCP Tool Interface

Implements AC-1: MCP-compliant tool interface implementation.
Implements AC-2: Tools callable from Claude, GPT, and other LLMs.

Defines the standard interface that all MCP tools must implement.

Epic: MD-2565
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncIterator, Union
from enum import Enum
import json
import hashlib


class ToolStatus(str, Enum):
    """Status of a tool execution"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    STREAMING = "streaming"
    CACHED = "cached"


class LLMProvider(str, Enum):
    """Supported LLM providers (AC-2)"""
    CLAUDE = "claude"
    GPT = "gpt"
    GEMINI = "gemini"
    LLAMA = "llama"
    MISTRAL = "mistral"
    GENERIC = "generic"


@dataclass
class MCPToolSchema:
    """
    JSON Schema definition for an MCP tool.

    Follows the Model Context Protocol specification for tool definitions.
    This schema is compatible with Claude, GPT, and other LLM tool formats (AC-2).
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    streaming_supported: bool = False
    cacheable: bool = True
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

    def to_claude_format(self) -> Dict[str, Any]:
        """Convert to Claude/Anthropic tool format (AC-2)"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI/GPT function format (AC-2)"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }

    def to_generic_format(self) -> Dict[str, Any]:
        """Convert to generic MCP format"""
        return {
            "tool": {
                "name": self.name,
                "description": self.description,
                "inputSchema": self.input_schema,
                "outputSchema": self.output_schema
            },
            "metadata": {
                "streaming": self.streaming_supported,
                "cacheable": self.cacheable,
                "timeout": self.timeout_seconds,
                **self.metadata
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPToolSchema":
        """Create from dictionary"""
        return cls(
            name=data["name"],
            description=data["description"],
            input_schema=data["input_schema"],
            output_schema=data.get("output_schema"),
            streaming_supported=data.get("streaming_supported", False),
            cacheable=data.get("cacheable", True),
            timeout_seconds=data.get("timeout_seconds", 30),
            metadata=data.get("metadata", {})
        )


@dataclass
class MCPToolResult:
    """
    Result of an MCP tool execution.

    Standardized result format compatible with all LLM providers.
    """
    tool_name: str
    status: ToolStatus
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    cached: bool = False
    cache_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "cached": self.cached,
            "cache_key": self.cache_key,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }

    def to_claude_format(self) -> Dict[str, Any]:
        """Convert to Claude tool_result format (AC-2)"""
        return {
            "type": "tool_result",
            "tool_use_id": self.metadata.get("tool_use_id", ""),
            "content": json.dumps(self.result) if not isinstance(self.result, str) else self.result,
            "is_error": self.status == ToolStatus.ERROR
        }

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function result format (AC-2)"""
        return {
            "role": "tool",
            "tool_call_id": self.metadata.get("tool_call_id", ""),
            "content": json.dumps(self.result) if not isinstance(self.result, str) else self.result
        }

    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status in (ToolStatus.SUCCESS, ToolStatus.CACHED)

    @classmethod
    def success(
        cls,
        tool_name: str,
        result: Any,
        execution_time_ms: float = 0.0,
        **metadata
    ) -> "MCPToolResult":
        """Create a success result"""
        return cls(
            tool_name=tool_name,
            status=ToolStatus.SUCCESS,
            result=result,
            execution_time_ms=execution_time_ms,
            metadata=metadata
        )

    @classmethod
    def error(
        cls,
        tool_name: str,
        error: str,
        **metadata
    ) -> "MCPToolResult":
        """Create an error result"""
        return cls(
            tool_name=tool_name,
            status=ToolStatus.ERROR,
            result=None,
            error=error,
            metadata=metadata
        )


class MCPToolInterface(ABC):
    """
    Abstract base class for MCP-compliant tools.

    AC-1 Implementation: All tools must implement this interface
    to be compatible with the MCP protocol.

    AC-2 Implementation: Provides format conversion for multiple LLMs.
    """

    @property
    @abstractmethod
    def schema(self) -> MCPToolSchema:
        """Return the tool's schema definition"""
        pass

    @abstractmethod
    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolResult:
        """
        Execute the tool with given inputs.

        Args:
            inputs: Tool inputs matching the input_schema
            context: Optional execution context (user info, session, etc.)

        Returns:
            MCPToolResult with execution result
        """
        pass

    async def stream_execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Any]:
        """
        Execute the tool with streaming output (AC-3).

        Default implementation wraps execute() in a single-item iterator.
        Override for true streaming support.

        Args:
            inputs: Tool inputs
            context: Optional execution context

        Yields:
            Streaming chunks of the result
        """
        result = await self.execute(inputs, context)
        yield result.result

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate inputs against the schema.

        Args:
            inputs: Inputs to validate

        Returns:
            True if valid, raises ValueError if invalid
        """
        schema = self.schema.input_schema

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in inputs:
                raise ValueError(f"Missing required field: {field}")

        # Check property types
        properties = schema.get("properties", {})
        for key, value in inputs.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if not self._type_matches(value, expected_type):
                    raise ValueError(
                        f"Field '{key}' expected {expected_type}, got {type(value).__name__}"
                    )

        return True

    def _type_matches(self, value: Any, expected_type: Optional[str]) -> bool:
        """Check if value matches expected JSON Schema type"""
        if expected_type is None:
            return True

        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None)
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True

        return isinstance(value, expected)

    def get_cache_key(self, inputs: Dict[str, Any]) -> str:
        """
        Generate cache key for inputs (AC-5).

        Args:
            inputs: Tool inputs

        Returns:
            Cache key string
        """
        content = json.dumps({
            "tool": self.schema.name,
            "inputs": inputs
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_llm_format(self, provider: LLMProvider) -> Dict[str, Any]:
        """
        Convert tool schema to LLM-specific format (AC-2).

        Args:
            provider: Target LLM provider

        Returns:
            Provider-specific tool definition
        """
        if provider == LLMProvider.CLAUDE:
            return self.schema.to_claude_format()
        elif provider == LLMProvider.GPT:
            return self.schema.to_openai_format()
        else:
            return self.schema.to_generic_format()

    @property
    def name(self) -> str:
        """Get tool name"""
        return self.schema.name

    @property
    def description(self) -> str:
        """Get tool description"""
        return self.schema.description

    @property
    def supports_streaming(self) -> bool:
        """Check if tool supports streaming (AC-3)"""
        return self.schema.streaming_supported

    @property
    def is_cacheable(self) -> bool:
        """Check if tool results can be cached (AC-5)"""
        return self.schema.cacheable
