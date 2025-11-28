"""
UTCP - Unified Tool Communication Protocol

Provides standardized tool interfaces for AI agents to interact with
external services like JIRA, Git, deployment platforms, etc.

Part of MD-857: Tool Registry - Discovery and access control
"""

from .registry import ToolRegistry, Tool, ToolCapability
from .base import UTCPTool, ToolResult, ToolError

__all__ = [
    'ToolRegistry',
    'Tool',
    'ToolCapability',
    'UTCPTool',
    'ToolResult',
    'ToolError',
]
