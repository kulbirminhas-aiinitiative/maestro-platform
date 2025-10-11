"""
Handoff System Models
Version: 1.0.0

Models for phase-to-phase handoffs with tasks and artifacts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from contracts.models import AcceptanceCriterion
from contracts.artifacts.models import ArtifactManifest


class HandoffStatus(str, Enum):
    """Status of handoff"""
    DRAFT = "DRAFT"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


@dataclass
class HandoffTask:
    """Individual task in a handoff"""
    task_id: str
    description: str
    assigned_to: Optional[str] = None
    completed: bool = False
    priority: str = "medium"  # low, medium, high, critical
    dependencies: List[str] = field(default_factory=list)


@dataclass
class HandoffSpec:
    """
    Specification for phase-to-phase handoff.

    Defines what needs to be transferred between phases.
    """
    handoff_id: str
    from_phase: str
    to_phase: str

    # Tasks
    tasks: List[HandoffTask] = field(default_factory=list)

    # Artifacts
    input_artifacts: Optional[ArtifactManifest] = None

    # Acceptance Criteria
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)

    # Metadata
    status: HandoffStatus = HandoffStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "handoff_id": self.handoff_id,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "assigned_to": t.assigned_to,
                    "completed": t.completed,
                    "priority": t.priority,
                    "dependencies": t.dependencies
                }
                for t in self.tasks
            ],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "context": self.context
        }


__all__ = ["HandoffStatus", "HandoffTask", "HandoffSpec"]
