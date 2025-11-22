"""
Claude Team SDK - True multi-agent collaboration framework.

This SDK enables multiple Claude agents to collaborate through shared MCP
(Model Context Protocol) coordination, allowing for sophisticated team-based
AI workflows.
"""

__version__ = "1.0.0"

from .agents.base import TeamAgent, AgentConfig, AgentRole, AgentStatus
from .coordination.team_coordinator import TeamCoordinator
from .state.shared_state import SharedWorkspace, TaskQueue, KnowledgeBase

__all__ = [
    # Core Classes
    "TeamAgent",
    "TeamCoordinator",
    "SharedWorkspace",
    "TaskQueue",
    "KnowledgeBase",

    # Enums
    "AgentConfig",
    "AgentRole",
    "AgentStatus",
]
