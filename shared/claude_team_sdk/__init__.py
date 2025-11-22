"""
Claude Team SDK - Multi-Agent Collaboration Framework
True multi-agent architecture with shared MCP coordination

This is a compatibility shim that re-exports from the new src/ structure.
New code should import directly from src.claude_team_sdk
"""

# Import from new structure and re-export for backward compatibility
try:
    # Try new structure first
    from src.claude_team_sdk import (
        TeamAgent, TeamCoordinator, AgentConfig, AgentRole, AgentStatus,
        SharedWorkspace, TaskQueue, KnowledgeBase
    )
    from src.claude_team_sdk.agents import (
        ArchitectAgent, DeveloperAgent, ReviewerAgent, TesterAgent, CoordinatorAgent
    )
    from src.claude_team_sdk.coordination import Message, MessageType
    from src.claude_team_sdk.config import settings
except ImportError:
    # Fallback to old structure for backward compatibility
    import warnings
    warnings.warn(
        "Using old flat structure. Please update imports to use src.claude_team_sdk",
        DeprecationWarning
    )
    from team_coordinator import TeamCoordinator
    from agent_base import TeamAgent, AgentRole, AgentStatus, AgentConfig
    from specialized_agents import (
        ArchitectAgent, DeveloperAgent, ReviewerAgent, TesterAgent, CoordinatorAgent
    )
    from communication import Message, MessageType
    from shared_state import SharedWorkspace, TaskQueue, KnowledgeBase

__version__ = "1.0.0"

# For config access
try:
    from src.claude_team_sdk.config import settings
except ImportError:
    settings = None

__all__ = [
    # Core
    "TeamCoordinator",
    "TeamAgent",
    "AgentRole",
    "AgentStatus",
    "AgentConfig",

    # Specialized Agents
    "ArchitectAgent",
    "DeveloperAgent",
    "ReviewerAgent",
    "TesterAgent",
    "CoordinatorAgent",

    # Communication
    "Message",
    "MessageType",

    # Shared State
    "SharedWorkspace",
    "TaskQueue",
    "KnowledgeBase",

    # Config
    "settings",
]
