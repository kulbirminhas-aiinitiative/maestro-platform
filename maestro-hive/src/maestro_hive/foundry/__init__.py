"""
AI Persona Foundry - Core Architecture
Master platform for creating, deploying, and evolving AI Agents with specialized personas.
"""
from .interfaces import (
    PersonaEngine,
    KnowledgeStore,
    AgentRuntime,
    ToolFramework,
    LearningEngine,
    InnovationEngine,
    CollaborationProtocol,
    DomainOnboarding,
)
from .types import (
    Persona,
    PersonaConfig,
    Document,
    Tool,
    Feedback,
    DomainConfig,
)

__version__ = "1.0.0"
__all__ = [
    "PersonaEngine",
    "KnowledgeStore", 
    "AgentRuntime",
    "ToolFramework",
    "LearningEngine",
    "InnovationEngine",
    "CollaborationProtocol",
    "DomainOnboarding",
    "Persona",
    "PersonaConfig",
    "Document",
    "Tool",
    "Feedback",
    "DomainConfig",
]
