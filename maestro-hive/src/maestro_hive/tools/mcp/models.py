"""
Data Models for MCP Integration

EPIC: MD-2565
AC-1: MCP-compliant tool interface implementation

Defines the core data models for MCP-compliant tool definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4


class ParameterType(str, Enum):
    """JSON Schema types for tool parameters."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """
    Definition of a tool parameter (AC-1).

    Follows JSON Schema specification for MCP compatibility.
    """
    name: str
    type: ParameterType = ParameterType.STRING
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    items: Optional["ToolParameter"] = None  # For array types
    properties: Optional[Dict[str, "ToolParameter"]] = None  # For object types
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: Dict[str, Any] = {
            "type": self.type.value,
        }

        if self.description:
            schema["description"] = self.description

        if self.default is not None:
            schema["default"] = self.default

        if self.enum:
            schema["enum"] = self.enum

        if self.type == ParameterType.ARRAY and self.items:
            schema["items"] = self.items.to_json_schema()

        if self.type == ParameterType.OBJECT and self.properties:
            schema["properties"] = {
                k: v.to_json_schema() for k, v in self.properties.items()
            }

        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.pattern:
            schema["pattern"] = self.pattern

        return schema


@dataclass
class ToolResult:
    """
    Result of a tool execution.

    Contains the output content and metadata.
    """
    id: UUID = field(default_factory=uuid4)
    content: Any = None
    content_type: str = "text/plain"
    is_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    duration_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "content": self.content,
            "content_type": self.content_type,
            "is_error": self.is_error,
            "metadata": self.metadata,
            "cached": self.cached,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class ToolError(Exception):
    """
    Error from a tool execution (AC-4).

    Includes error code, message, and retry hint.
    """

    def __init__(
        self,
        code: str,
        message: str,
        retryable: bool = False,
        retry_after_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after_ms = retry_after_ms
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "retry_after_ms": self.retry_after_ms,
            "details": self.details,
        }


@dataclass
class StreamChunk:
    """
    A chunk of streaming output (AC-3).

    Used for progressive tool output.
    """
    id: UUID = field(default_factory=uuid4)
    content: Any = None
    content_type: str = "text/plain"
    index: int = 0
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "content": self.content,
            "content_type": self.content_type,
            "index": self.index,
            "is_final": self.is_final,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class MCPTool(ABC):
    """
    Base class for MCP-compliant tools (AC-1, AC-2).

    Subclass this to create tools that can be invoked from any LLM provider.

    Example:
        class SearchTool(MCPTool):
            name = "search"
            description = "Search for information"
            parameters = [
                ToolParameter(name="query", type=ParameterType.STRING, required=True),
                ToolParameter(name="limit", type=ParameterType.INTEGER, default=10)
            ]

            async def execute(self, query: str, limit: int = 10) -> ToolResult:
                results = await do_search(query, limit)
                return ToolResult(content=results)
    """

    # Tool metadata (override in subclass)
    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = []

    # Optional settings
    cacheable: bool = True
    stream_capable: bool = False
    timeout_seconds: int = 30

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool arguments matching parameter definitions

        Returns:
            ToolResult containing the output
        """
        pass

    async def execute_stream(self, **kwargs):
        """
        Execute the tool with streaming output (AC-3).

        Override this method for tools that support streaming.

        Args:
            **kwargs: Tool arguments

        Yields:
            StreamChunk objects for progressive output
        """
        # Default implementation: just wrap execute in a single chunk
        result = await self.execute(**kwargs)
        yield StreamChunk(
            content=result.content,
            content_type=result.content_type,
            is_final=True,
            metadata=result.metadata,
        )

    def get_mcp_schema(self) -> Dict[str, Any]:
        """
        Get the MCP-compliant tool schema (AC-1).

        Returns JSON Schema-based tool definition.
        """
        required_params = [p.name for p in self.parameters if p.required]

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    p.name: p.to_json_schema() for p in self.parameters
                },
                "required": required_params,
            },
        }

    def validate_arguments(self, arguments: Dict[str, Any]) -> List[str]:
        """
        Validate arguments against parameter definitions.

        Returns list of validation errors (empty if valid).
        """
        errors = []

        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in arguments:
                errors.append(f"Missing required parameter: {param.name}")

        # Check types
        for param in self.parameters:
            if param.name in arguments:
                value = arguments[param.name]
                if not self._check_type(value, param.type):
                    errors.append(
                        f"Invalid type for {param.name}: expected {param.type.value}, got {type(value).__name__}"
                    )

        return errors

    def _check_type(self, value: Any, expected: ParameterType) -> bool:
        """Check if value matches expected type."""
        type_map = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.NUMBER: (int, float),
            ParameterType.BOOLEAN: bool,
            ParameterType.ARRAY: list,
            ParameterType.OBJECT: dict,
        }
        expected_types = type_map.get(expected, (object,))
        if isinstance(expected_types, tuple):
            return isinstance(value, expected_types)
        return isinstance(value, expected_types)

    def get_cache_key(self, arguments: Dict[str, Any]) -> str:
        """Generate cache key for arguments."""
        import hashlib
        import json

        # Sort keys for consistent hashing
        sorted_args = json.dumps(arguments, sort_keys=True)
        return hashlib.sha256(f"{self.name}:{sorted_args}".encode()).hexdigest()
