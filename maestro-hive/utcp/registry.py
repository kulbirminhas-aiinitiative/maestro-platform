"""
UTCP Tool Registry

Central registry for discovering and managing UTCP tools.
Part of MD-857: Tool Registry - Discovery and access control
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type
from .base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


@dataclass
class Tool:
    """Registered tool metadata."""
    name: str
    description: str
    tool_class: Type[UTCPTool]
    config: ToolConfig
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


class ToolRegistry:
    """
    Central registry for UTCP tools.

    Provides:
    - Tool discovery
    - Access control
    - Tool instantiation
    - Capability querying
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._instances: Dict[str, UTCPTool] = {}

    def register(
        self,
        name: str,
        description: str,
        tool_class: Type[UTCPTool],
        tags: Optional[List[str]] = None
    ) -> None:
        """Register a new tool."""
        # Get config from a dummy instance check
        temp_config = tool_class.__dict__.get('_config')
        if not temp_config:
            # Create config from class properties
            temp_config = ToolConfig(
                name=name,
                version="1.0.0",
                capabilities=[],
                required_credentials=[]
            )

        self._tools[name] = Tool(
            name=name,
            description=description,
            tool_class=tool_class,
            config=temp_config,
            tags=tags or [],
            enabled=True
        )

    def get_tool(self, name: str, credentials: Dict[str, str]) -> UTCPTool:
        """Get an instantiated tool by name."""
        if name not in self._tools:
            raise ToolError(f"Tool '{name}' not found in registry", code="TOOL_NOT_FOUND")

        tool_meta = self._tools[name]
        if not tool_meta.enabled:
            raise ToolError(f"Tool '{name}' is disabled", code="TOOL_DISABLED")

        # Create new instance with credentials
        return tool_meta.tool_class(credentials)

    def list_tools(self, capability: Optional[ToolCapability] = None, tag: Optional[str] = None) -> List[Tool]:
        """List available tools, optionally filtered."""
        tools = list(self._tools.values())

        if capability:
            tools = [t for t in tools if capability in t.config.capabilities]

        if tag:
            tools = [t for t in tools if tag in t.tags]

        return [t for t in tools if t.enabled]

    def get_tools_for_phase(self, phase_type: str) -> List[Tool]:
        """Get tools suitable for a specific workflow phase."""
        phase_tool_mapping = {
            'requirements': ['jira'],
            'architecture': ['jira', 'git'],
            'implementation': ['git', 'jira'],
            'testing': ['git', 'jira'],
            'deployment': ['git', 'jira'],
            'review': ['jira', 'git'],
        }

        tool_names = phase_tool_mapping.get(phase_type, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def disable_tool(self, name: str) -> None:
        """Disable a tool."""
        if name in self._tools:
            self._tools[name].enabled = False

    def enable_tool(self, name: str) -> None:
        """Enable a tool."""
        if name in self._tools:
            self._tools[name].enabled = True

    def get_tool_info(self, name: str) -> Optional[Dict]:
        """Get detailed information about a tool."""
        if name not in self._tools:
            return None

        tool = self._tools[name]
        return {
            'name': tool.name,
            'description': tool.description,
            'capabilities': [c.value for c in tool.config.capabilities],
            'required_credentials': tool.config.required_credentials,
            'optional_credentials': tool.config.optional_credentials,
            'tags': tool.tags,
            'enabled': tool.enabled,
            'rate_limit': tool.config.rate_limit,
            'timeout': tool.config.timeout,
        }


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry
