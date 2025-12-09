"""Agent Collaboration Protocol - Enable multi-agent coordination."""
from .models import CollaborationMessage, CollaborationSession, TaskAssignment
from .coordinator import CollaborationCoordinator
from .messaging import MessageBus
from .orchestrator import TaskOrchestrator

__version__ = "1.0.0"
__all__ = ["CollaborationMessage", "CollaborationSession", "TaskAssignment",
           "CollaborationCoordinator", "MessageBus", "TaskOrchestrator"]
