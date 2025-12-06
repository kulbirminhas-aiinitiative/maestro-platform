"""
Maestro Workflow Orchestrator Package (MD-2108)

Provides unified orchestration layer for coordinating:
- DDE (Design Document Engine)
- Documentation generation
- Task management (JIRA integration)
- Governance protocols
"""

from .workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowConfig,
    WorkflowPhase,
    WorkflowState,
    WorkflowResult
)
from .event_bus import (
    EventBus,
    Event,
    EventType,
    EventHandler
)

__all__ = [
    'WorkflowOrchestrator',
    'WorkflowConfig',
    'WorkflowPhase',
    'WorkflowState',
    'WorkflowResult',
    'EventBus',
    'Event',
    'EventType',
    'EventHandler'
]
