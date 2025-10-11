"""
SDLC Team Management
Version: 1.0.0

Multi-agent team configuration and role management.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class AgentRole(str, Enum):
    """Standard SDLC agent roles"""
    PRODUCT_OWNER = "product_owner"
    BUSINESS_ANALYST = "business_analyst"
    UX_DESIGNER = "ux_designer"
    UI_DESIGNER = "ui_designer"
    ARCHITECT = "architect"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    FULL_STACK_DEVELOPER = "full_stack_developer"
    QA_ENGINEER = "qa_engineer"
    AUTOMATION_ENGINEER = "automation_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    SECURITY_ENGINEER = "security_engineer"
    DATA_ENGINEER = "data_engineer"
    TECH_LEAD = "tech_lead"
    PROJECT_MANAGER = "project_manager"


@dataclass
class AgentCapability:
    """Capability that an agent possesses"""
    capability_id: str
    name: str
    description: str
    proficiency: str = "intermediate"  # beginner, intermediate, advanced, expert
    tags: List[str] = field(default_factory=list)


@dataclass
class Agent:
    """
    Individual agent in the SDLC team.

    Represents a single agent (human or AI) with specific roles and capabilities.
    """
    agent_id: str
    name: str
    roles: List[AgentRole]
    capabilities: List[AgentCapability] = field(default_factory=list)

    # Availability
    available: bool = True
    max_concurrent_tasks: int = 3

    # Performance Metrics
    completed_tasks: int = 0
    success_rate: float = 1.0
    average_completion_time_hours: float = 0.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_perform_role(self, role: AgentRole) -> bool:
        """Check if agent can perform a specific role"""
        return role in self.roles

    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability"""
        return any(cap.name == capability_name for cap in self.capabilities)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "roles": [role.value for role in self.roles],
            "capabilities": [
                {
                    "capability_id": cap.capability_id,
                    "name": cap.name,
                    "description": cap.description,
                    "proficiency": cap.proficiency,
                    "tags": cap.tags
                }
                for cap in self.capabilities
            ],
            "available": self.available,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "completed_tasks": self.completed_tasks,
            "success_rate": self.success_rate,
            "average_completion_time_hours": self.average_completion_time_hours,
            "metadata": self.metadata
        }


@dataclass
class AgentTeam:
    """
    Multi-agent team for SDLC workflow.

    Manages a collection of agents working together on a project.
    """
    team_id: str
    name: str
    agents: List[Agent]

    # Team Configuration
    description: str = ""
    project_id: Optional[str] = None

    # Team Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_agents_by_role(self, role: AgentRole) -> List[Agent]:
        """Get all agents with a specific role"""
        return [agent for agent in self.agents if agent.can_perform_role(role)]

    def get_available_agents(self) -> List[Agent]:
        """Get all currently available agents"""
        return [agent for agent in self.agents if agent.available]

    def get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get specific agent by ID"""
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None

    def assign_role(self, agent_id: str, role: AgentRole) -> bool:
        """Assign a role to an agent"""
        agent = self.get_agent_by_id(agent_id)
        if agent and role not in agent.roles:
            agent.roles.append(role)
            return True
        return False

    def team_has_role(self, role: AgentRole) -> bool:
        """Check if team has at least one agent with the given role"""
        return len(self.get_agents_by_role(role)) > 0

    def team_statistics(self) -> Dict[str, Any]:
        """Get team performance statistics"""
        total_tasks = sum(agent.completed_tasks for agent in self.agents)
        avg_success_rate = (
            sum(agent.success_rate for agent in self.agents) / len(self.agents)
            if self.agents else 0.0
        )

        return {
            "team_id": self.team_id,
            "total_agents": len(self.agents),
            "available_agents": len(self.get_available_agents()),
            "total_completed_tasks": total_tasks,
            "average_success_rate": avg_success_rate,
            "roles_coverage": {
                role.value: len(self.get_agents_by_role(role))
                for role in AgentRole
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "agents": [agent.to_dict() for agent in self.agents],
            "statistics": self.team_statistics(),
            "metadata": self.metadata
        }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "AgentRole",
    "AgentCapability",
    "Agent",
    "AgentTeam",
]
