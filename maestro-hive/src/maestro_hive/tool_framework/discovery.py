"""Tool Discovery - Discover and load tools dynamically."""
import importlib
import logging
from pathlib import Path
from typing import List, Optional
from .models import Tool, ToolRegistry, ToolCategory, ToolParameter, ParameterType

logger = logging.getLogger(__name__)


class ToolDiscovery:
    """Discovers and loads tools from various sources."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    def discover_builtin(self) -> int:
        """Discover and register built-in tools."""
        count = 0
        
        # Echo tool
        echo_tool = Tool(
            name="echo",
            description="Echo back the input message",
            category=ToolCategory.SYSTEM,
            parameters=[ToolParameter(name="message", param_type=ParameterType.STRING, description="Message to echo")],
            handler=lambda message: {"echo": message}
        )
        if self.registry.register(echo_tool):
            count += 1
        
        # Calculator tool
        calc_tool = Tool(
            name="calculator",
            description="Perform basic arithmetic",
            category=ToolCategory.DATA,
            parameters=[
                ToolParameter(name="operation", param_type=ParameterType.STRING, enum_values=["+", "-", "*", "/"]),
                ToolParameter(name="a", param_type=ParameterType.FLOAT),
                ToolParameter(name="b", param_type=ParameterType.FLOAT),
            ],
            handler=lambda operation, a, b: {"result": eval(f"{a}{operation}{b}") if operation in "+-*/" else None}
        )
        if self.registry.register(calc_tool):
            count += 1
        
        # HTTP GET tool
        http_tool = Tool(
            name="http_get",
            description="Fetch data from a URL",
            category=ToolCategory.WEB,
            parameters=[ToolParameter(name="url", param_type=ParameterType.STRING, description="URL to fetch")],
            timeout_ms=10000
        )
        if self.registry.register(http_tool):
            count += 1
        
        logger.info("Discovered %d built-in tools", count)
        return count
    
    def discover_from_path(self, path: Path) -> int:
        """Discover tools from a directory."""
        count = 0
        if not path.exists():
            return count
        
        for file_path in path.glob("*.py"):
            try:
                # Would load module and find Tool definitions
                count += 1
            except Exception as e:
                logger.error("Failed to load tool from %s: %s", file_path, e)
        
        return count
