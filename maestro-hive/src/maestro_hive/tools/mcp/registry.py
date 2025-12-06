"""
MCP Tool Registry

EPIC: MD-2565
AC-1: MCP-compliant tool interface implementation
AC-2: Tools callable from Claude, GPT, and other LLMs

Provides centralized registration and discovery of MCP tools.
"""

from typing import Dict, List, Optional, Type, Any
from .models import MCPTool, ToolParameter, ParameterType
import logging

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """
    Registry for MCP-compliant tools (AC-1).

    Manages tool registration, discovery, and schema generation
    for use with any LLM provider (AC-2).

    Example:
        registry = MCPToolRegistry()
        registry.register(SearchTool())
        registry.register(CalculatorTool())

        # Get all tools for Claude
        tools = registry.get_tools_for_provider("claude")

        # Get specific tool
        search = registry.get_tool("search")
    """

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._categories: Dict[str, List[str]] = {}
        self._provider_filters: Dict[str, List[str]] = {}

    def register(
        self,
        tool: MCPTool,
        category: Optional[str] = None,
        providers: Optional[List[str]] = None,
    ) -> None:
        """
        Register a tool with the registry.

        Args:
            tool: The MCPTool instance to register
            category: Optional category for grouping
            providers: Optional list of providers this tool supports
        """
        if not tool.name:
            raise ValueError("Tool must have a name")

        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")

        self._tools[tool.name] = tool

        if category:
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(tool.name)

        if providers:
            for provider in providers:
                if provider not in self._provider_filters:
                    self._provider_filters[provider] = []
                self._provider_filters[provider].append(tool.name)

        logger.info(f"Registered tool: {tool.name}")

    def register_class(
        self,
        tool_class: Type[MCPTool],
        category: Optional[str] = None,
        providers: Optional[List[str]] = None,
    ) -> None:
        """
        Register a tool class (instantiates automatically).

        Args:
            tool_class: The MCPTool class to register
            category: Optional category for grouping
            providers: Optional list of providers this tool supports
        """
        tool = tool_class()
        self.register(tool, category, providers)

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool by name.

        Returns True if tool was found and removed.
        """
        if name not in self._tools:
            return False

        del self._tools[name]

        # Clean up categories
        for category, tools in self._categories.items():
            if name in tools:
                tools.remove(name)

        # Clean up provider filters
        for provider, tools in self._provider_filters.items():
            if name in tools:
                tools.remove(name)

        logger.info(f"Unregistered tool: {name}")
        return True

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[MCPTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_by_category(self, category: str) -> List[MCPTool]:
        """Get all tools in a category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_tools_for_provider(self, provider: str) -> List[MCPTool]:
        """
        Get tools available for a specific provider (AC-2).

        If provider has no filter, returns all tools.
        """
        if provider in self._provider_filters:
            tool_names = self._provider_filters[provider]
            return [self._tools[name] for name in tool_names if name in self._tools]
        return self.get_all_tools()

    def get_categories(self) -> List[str]:
        """Get all registered categories."""
        return list(self._categories.keys())

    def get_mcp_schemas(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get MCP schemas for all tools (AC-1).

        Args:
            provider: Optional provider to filter tools

        Returns:
            List of MCP-compliant tool schemas
        """
        if provider:
            tools = self.get_tools_for_provider(provider)
        else:
            tools = self.get_all_tools()

        return [tool.get_mcp_schema() for tool in tools]

    def get_openai_functions(self, provider: str = "openai") -> List[Dict[str, Any]]:
        """
        Get tool schemas in OpenAI function format (AC-2).

        Converts MCP schemas to OpenAI's function calling format.
        """
        tools = self.get_tools_for_provider(provider)
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

    def get_claude_tools(self, provider: str = "claude") -> List[Dict[str, Any]]:
        """
        Get tool schemas in Claude format (AC-2).

        Claude uses MCP format natively.
        """
        return self.get_mcp_schemas(provider)

    def find_tools(
        self,
        query: str,
        limit: int = 10,
    ) -> List[MCPTool]:
        """
        Search for tools by name or description.

        Simple substring matching for now.
        """
        query_lower = query.lower()
        matches = []

        for tool in self._tools.values():
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                matches.append(tool)
                if len(matches) >= limit:
                    break

        return matches

    def validate_all(self) -> Dict[str, List[str]]:
        """
        Validate all registered tools.

        Returns dict of tool_name -> list of issues.
        """
        issues = {}

        for name, tool in self._tools.items():
            tool_issues = []

            if not tool.name:
                tool_issues.append("Missing tool name")

            if not tool.description:
                tool_issues.append("Missing tool description")

            # Validate parameters
            param_names = set()
            for param in tool.parameters:
                if param.name in param_names:
                    tool_issues.append(f"Duplicate parameter: {param.name}")
                param_names.add(param.name)

            if tool_issues:
                issues[name] = tool_issues

        return issues

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools.values())


# Global registry instance
_global_registry: Optional[MCPToolRegistry] = None


def get_global_registry() -> MCPToolRegistry:
    """Get the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = MCPToolRegistry()
    return _global_registry


def register_tool(
    tool: MCPTool,
    category: Optional[str] = None,
    providers: Optional[List[str]] = None,
) -> None:
    """Register a tool with the global registry."""
    get_global_registry().register(tool, category, providers)
