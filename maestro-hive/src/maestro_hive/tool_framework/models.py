"""Tool Framework Models - Core data structures for tool integration."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4
import json


class ToolCategory(Enum):
    """Categories of tools."""
    DATA = "data"
    CODE = "code"
    COMMUNICATION = "communication"
    FILE = "file"
    WEB = "web"
    SYSTEM = "system"
    CUSTOM = "custom"


class ParameterType(Enum):
    """Tool parameter types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    param_type: ParameterType = ParameterType.STRING
    description: str = ""
    required: bool = True
    default: Any = None
    enum_values: List[Any] = field(default_factory=list)
    
    def validate(self, value: Any) -> bool:
        """Validate parameter value."""
        if value is None:
            return not self.required
        
        type_map = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.FLOAT: (int, float),
            ParameterType.BOOLEAN: bool,
            ParameterType.ARRAY: (list, tuple),
            ParameterType.OBJECT: dict,
        }
        expected_type = type_map.get(self.param_type, object)
        
        if not isinstance(value, expected_type):
            return False
        
        if self.enum_values and value not in self.enum_values:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "type": self.param_type.value, "description": self.description,
                "required": self.required, "default": self.default, "enum": self.enum_values}


@dataclass
class ToolResult:
    """Result from tool execution."""
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"tool_name": self.tool_name, "success": self.success, "output": self.output,
                "error": self.error, "execution_time_ms": self.execution_time_ms, "metadata": self.metadata}


@dataclass
class Tool:
    """Definition of an executable tool."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.CUSTOM
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    version: str = "1.0.0"
    enabled: bool = True
    permissions: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None  # calls per minute
    timeout_ms: int = 30000
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against schema."""
        errors = []
        for param in self.parameters:
            value = params.get(param.name, param.default)
            if not param.validate(value):
                errors.append(f"Invalid parameter '{param.name}': expected {param.param_type.value}")
        return errors
    
    def to_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {p.name: {"type": p.param_type.value, "description": p.description} for p in self.parameters},
                "required": [p.name for p in self.parameters if p.required],
            }
        }


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}
    
    def register(self, tool: Tool) -> bool:
        """Register a tool."""
        if tool.name in self._tools:
            return False
        self._tools[tool.name] = tool
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)
        return True
    
    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        if category:
            return [self._tools[n] for n in self._categories.get(category, []) if n in self._tools]
        return list(self._tools.values())
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        return [t.to_schema() for t in self._tools.values() if t.enabled]
