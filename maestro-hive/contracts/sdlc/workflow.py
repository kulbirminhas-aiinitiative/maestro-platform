"""
SDLC Workflow Orchestration
Version: 1.0.0

Workflow definitions and orchestration for contract-driven SDLC.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

from contracts.handoff.models import HandoffSpec
from contracts.models import UniversalContract


class SDLCPhase(str, Enum):
    """Standard SDLC phases"""
    REQUIREMENTS = "requirements"
    ANALYSIS = "analysis"
    DESIGN = "design"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"


class WorkflowStepStatus(str, Enum):
    """Status of a workflow step"""
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class WorkflowStep:
    """
    Individual step in an SDLC workflow.

    Each step represents a unit of work with contracts and handoffs.
    """
    step_id: str
    name: str
    phase: SDLCPhase
    description: str = ""

    # Execution
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    assigned_to: Optional[str] = None  # Agent ID

    # Contracts and Handoffs
    contracts: List[str] = field(default_factory=list)  # Contract IDs
    input_handoff_id: Optional[str] = None
    output_handoff_id: Optional[str] = None

    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Step IDs

    # Timing
    estimated_duration_hours: float = 1.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def actual_duration_hours(self) -> Optional[float]:
        """Calculate actual duration if step is completed"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() / 3600
        return None

    def is_ready(self) -> bool:
        """Check if step is ready to execute"""
        return self.status in [WorkflowStepStatus.READY, WorkflowStepStatus.PENDING]

    def is_complete(self) -> bool:
        """Check if step is completed"""
        return self.status == WorkflowStepStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if step failed"""
        return self.status == WorkflowStepStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "phase": self.phase.value,
            "description": self.description,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "contracts": self.contracts,
            "input_handoff_id": self.input_handoff_id,
            "output_handoff_id": self.output_handoff_id,
            "depends_on": self.depends_on,
            "estimated_duration_hours": self.estimated_duration_hours,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "actual_duration_hours": self.actual_duration_hours(),
            "metadata": self.metadata
        }


@dataclass
class SDLCWorkflow:
    """
    Complete SDLC workflow with phases and steps.

    Orchestrates the execution of contracts through SDLC phases.
    """
    workflow_id: str
    name: str
    description: str
    project_id: str

    # Steps and Phases
    steps: List[WorkflowStep] = field(default_factory=list)

    # Team
    team_id: Optional[str] = None

    # Status
    status: str = "draft"  # draft, active, completed, failed

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_steps_by_phase(self, phase: SDLCPhase) -> List[WorkflowStep]:
        """Get all steps in a specific phase"""
        return [step for step in self.steps if step.phase == phase]

    def get_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        """Get specific step by ID"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get all steps ready for execution"""
        ready_steps = []

        for step in self.steps:
            if step.is_ready():
                # Check if all dependencies are completed
                deps_completed = all(
                    self.get_step_by_id(dep_id) and self.get_step_by_id(dep_id).is_complete()
                    for dep_id in step.depends_on
                )
                if deps_completed:
                    ready_steps.append(step)

        return ready_steps

    def get_in_progress_steps(self) -> List[WorkflowStep]:
        """Get all steps currently in progress"""
        return [step for step in self.steps if step.status == WorkflowStepStatus.IN_PROGRESS]

    def get_completed_steps(self) -> List[WorkflowStep]:
        """Get all completed steps"""
        return [step for step in self.steps if step.is_complete()]

    def get_failed_steps(self) -> List[WorkflowStep]:
        """Get all failed steps"""
        return [step for step in self.steps if step.is_failed()]

    def calculate_progress(self) -> float:
        """Calculate workflow completion percentage"""
        if not self.steps:
            return 0.0

        completed = len(self.get_completed_steps())
        total = len(self.steps)

        return (completed / total) * 100.0

    def estimated_total_duration_hours(self) -> float:
        """Calculate total estimated duration"""
        return sum(step.estimated_duration_hours for step in self.steps)

    def actual_total_duration_hours(self) -> Optional[float]:
        """Calculate actual total duration if workflow completed"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() / 3600
        return None

    def get_critical_path(self) -> List[WorkflowStep]:
        """
        Calculate critical path (longest path through dependencies).

        Returns list of steps in critical path order.
        """
        # Build dependency graph
        graph: Dict[str, List[str]] = {step.step_id: step.depends_on for step in self.steps}
        step_map: Dict[str, WorkflowStep] = {step.step_id: step for step in self.steps}

        # Calculate longest path to each node
        longest_paths: Dict[str, float] = {}

        def calculate_longest_path(step_id: str) -> float:
            """Recursively calculate longest path to a step"""
            if step_id in longest_paths:
                return longest_paths[step_id]

            step = step_map.get(step_id)
            if not step:
                return 0.0

            if not step.depends_on:
                longest_paths[step_id] = step.estimated_duration_hours
                return step.estimated_duration_hours

            # Max path from dependencies + this step's duration
            max_dep_path = max(
                (calculate_longest_path(dep_id) for dep_id in step.depends_on),
                default=0.0
            )
            longest_paths[step_id] = max_dep_path + step.estimated_duration_hours
            return longest_paths[step_id]

        # Calculate for all steps
        for step in self.steps:
            calculate_longest_path(step.step_id)

        # Find the step with longest path (end of critical path)
        if not longest_paths:
            return []

        critical_end = max(longest_paths.items(), key=lambda x: x[1])[0]

        # Backtrack to find critical path
        critical_path = []
        current = critical_end

        while current:
            step = step_map.get(current)
            if not step:
                break

            critical_path.append(step)

            # Find dependency with longest path
            if step.depends_on:
                current = max(
                    step.depends_on,
                    key=lambda dep_id: longest_paths.get(dep_id, 0.0)
                )
            else:
                current = None

        # Reverse to get start-to-end order
        critical_path.reverse()
        return critical_path

    def workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        completed = len(self.get_completed_steps())
        in_progress = len(self.get_in_progress_steps())
        failed = len(self.get_failed_steps())
        ready = len(self.get_ready_steps())
        pending = len([s for s in self.steps if s.status == WorkflowStepStatus.PENDING])

        # Phase breakdown
        phase_stats = {}
        for phase in SDLCPhase:
            phase_steps = self.get_steps_by_phase(phase)
            phase_completed = len([s for s in phase_steps if s.is_complete()])
            phase_stats[phase.value] = {
                "total": len(phase_steps),
                "completed": phase_completed,
                "progress": (phase_completed / len(phase_steps) * 100) if phase_steps else 0.0
            }

        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "total_steps": len(self.steps),
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "ready": ready,
            "pending": pending,
            "progress_percentage": self.calculate_progress(),
            "estimated_total_hours": self.estimated_total_duration_hours(),
            "actual_total_hours": self.actual_total_duration_hours(),
            "phase_breakdown": phase_stats,
            "critical_path_duration": sum(
                s.estimated_duration_hours for s in self.get_critical_path()
            )
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "team_id": self.team_id,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "statistics": self.workflow_statistics(),
            "metadata": self.metadata
        }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "SDLCPhase",
    "WorkflowStepStatus",
    "WorkflowStep",
    "SDLCWorkflow",
]
