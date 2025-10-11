"""
SDLC Integration Module
Version: 1.0.0

Multi-agent workflow orchestration for contract-driven SDLC.
"""

from contracts.sdlc.team import AgentRole, AgentCapability, Agent, AgentTeam
from contracts.sdlc.workflow import SDLCPhase, WorkflowStepStatus, WorkflowStep, SDLCWorkflow
from contracts.sdlc.orchestrator import OrchestrationEvent, ContractOrchestrator

__all__ = [
    # Team Management
    "AgentRole",
    "AgentCapability",
    "Agent",
    "AgentTeam",

    # Workflow
    "SDLCPhase",
    "WorkflowStepStatus",
    "WorkflowStep",
    "SDLCWorkflow",

    # Orchestration
    "OrchestrationEvent",
    "ContractOrchestrator",
]
