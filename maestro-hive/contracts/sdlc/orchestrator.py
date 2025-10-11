"""
Contract Orchestrator
Version: 1.0.0

Orchestrates contract execution across SDLC workflow with multi-agent teams.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import logging

from contracts.models import UniversalContract, ContractLifecycle
from contracts.handoff.models import HandoffSpec, HandoffStatus, HandoffTask
from contracts.sdlc.workflow import SDLCWorkflow, WorkflowStep, WorkflowStepStatus
from contracts.sdlc.team import AgentTeam, Agent, AgentRole

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationEvent:
    """Event in the orchestration process"""
    event_id: str
    event_type: str  # step_started, step_completed, handoff_ready, contract_fulfilled, etc.
    timestamp: datetime
    step_id: Optional[str] = None
    contract_id: Optional[str] = None
    handoff_id: Optional[str] = None
    agent_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractOrchestrator:
    """
    Orchestrates contract-driven SDLC with multi-agent teams.

    Manages workflow execution, agent assignment, handoff transitions,
    and contract fulfillment across the entire SDLC.
    """
    orchestrator_id: str
    workflow: SDLCWorkflow
    team: AgentTeam

    # Contracts and Handoffs
    contracts: Dict[str, UniversalContract] = field(default_factory=dict)
    handoffs: Dict[str, HandoffSpec] = field(default_factory=dict)

    # Execution State
    events: List[OrchestrationEvent] = field(default_factory=list)
    active_step_id: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_contract(self, contract: UniversalContract) -> None:
        """Add a contract to the orchestrator"""
        self.contracts[contract.contract_id] = contract
        logger.info(f"Added contract {contract.contract_id} to orchestrator")

    def add_handoff(self, handoff: HandoffSpec) -> None:
        """Add a handoff to the orchestrator"""
        self.handoffs[handoff.handoff_id] = handoff
        logger.info(f"Added handoff {handoff.handoff_id} to orchestrator")

    def get_contract(self, contract_id: str) -> Optional[UniversalContract]:
        """Get a contract by ID"""
        return self.contracts.get(contract_id)

    def get_handoff(self, handoff_id: str) -> Optional[HandoffSpec]:
        """Get a handoff by ID"""
        return self.handoffs.get(handoff_id)

    def assign_agent_to_step(self, step_id: str, agent_id: str) -> bool:
        """
        Assign an agent to a workflow step.

        Returns True if assignment successful, False otherwise.
        """
        step = self.workflow.get_step_by_id(step_id)
        agent = self.team.get_agent_by_id(agent_id)

        if not step or not agent:
            logger.error(f"Step {step_id} or agent {agent_id} not found")
            return False

        if not agent.available:
            logger.warning(f"Agent {agent_id} is not available")
            return False

        step.assigned_to = agent_id
        logger.info(f"Assigned agent {agent_id} to step {step_id}")

        self._log_event(OrchestrationEvent(
            event_id=f"assign-{step_id}-{agent_id}",
            event_type="agent_assigned",
            timestamp=datetime.utcnow(),
            step_id=step_id,
            agent_id=agent_id
        ))

        return True

    def auto_assign_agents(self) -> int:
        """
        Automatically assign available agents to ready steps.

        Returns number of assignments made.
        """
        ready_steps = self.workflow.get_ready_steps()
        assignments_made = 0

        for step in ready_steps:
            if step.assigned_to:
                continue  # Already assigned

            # Find available agent (simple round-robin for now)
            available = self.team.get_available_agents()
            if available:
                agent = available[0]
                if self.assign_agent_to_step(step.step_id, agent.agent_id):
                    assignments_made += 1

        return assignments_made

    def start_step(self, step_id: str) -> bool:
        """
        Start execution of a workflow step.

        Returns True if step started successfully, False otherwise.
        """
        step = self.workflow.get_step_by_id(step_id)

        if not step:
            logger.error(f"Step {step_id} not found")
            return False

        if not step.is_ready():
            logger.error(f"Step {step_id} is not ready (status: {step.status})")
            return False

        # Check dependencies
        for dep_id in step.depends_on:
            dep_step = self.workflow.get_step_by_id(dep_id)
            if not dep_step or not dep_step.is_complete():
                logger.error(f"Dependency {dep_id} not completed")
                return False

        # Start the step
        step.status = WorkflowStepStatus.IN_PROGRESS
        step.started_at = datetime.utcnow()
        self.active_step_id = step_id

        logger.info(f"Started step {step_id}")

        self._log_event(OrchestrationEvent(
            event_id=f"start-{step_id}",
            event_type="step_started",
            timestamp=datetime.utcnow(),
            step_id=step_id,
            agent_id=step.assigned_to
        ))

        # Start input handoff if exists
        if step.input_handoff_id:
            handoff = self.get_handoff(step.input_handoff_id)
            if handoff and handoff.status == HandoffStatus.READY:
                handoff.status = HandoffStatus.IN_PROGRESS
                logger.info(f"Started input handoff {step.input_handoff_id}")

        return True

    def complete_step(self, step_id: str, success: bool = True) -> bool:
        """
        Mark a workflow step as completed.

        Returns True if step completed successfully, False otherwise.
        """
        step = self.workflow.get_step_by_id(step_id)

        if not step:
            logger.error(f"Step {step_id} not found")
            return False

        if step.status != WorkflowStepStatus.IN_PROGRESS:
            logger.error(f"Step {step_id} is not in progress")
            return False

        # Update step status
        if success:
            step.status = WorkflowStepStatus.COMPLETED
        else:
            step.status = WorkflowStepStatus.FAILED

        step.completed_at = datetime.utcnow()

        if self.active_step_id == step_id:
            self.active_step_id = None

        logger.info(f"Completed step {step_id} (success: {success})")

        self._log_event(OrchestrationEvent(
            event_id=f"complete-{step_id}",
            event_type="step_completed" if success else "step_failed",
            timestamp=datetime.utcnow(),
            step_id=step_id,
            agent_id=step.assigned_to,
            details={"success": success}
        ))

        # Complete input handoff
        if step.input_handoff_id:
            handoff = self.get_handoff(step.input_handoff_id)
            if handoff and handoff.status == HandoffStatus.IN_PROGRESS:
                handoff.status = HandoffStatus.COMPLETED
                handoff.completed_at = datetime.utcnow()

        # Prepare output handoff
        if step.output_handoff_id and success:
            handoff = self.get_handoff(step.output_handoff_id)
            if handoff:
                handoff.status = HandoffStatus.READY
                logger.info(f"Output handoff {step.output_handoff_id} ready")

        # Update agent performance
        if step.assigned_to:
            agent = self.team.get_agent_by_id(step.assigned_to)
            if agent:
                agent.completed_tasks += 1
                if success:
                    agent.success_rate = (
                        (agent.success_rate * (agent.completed_tasks - 1) + 1.0) /
                        agent.completed_tasks
                    )
                else:
                    agent.success_rate = (
                        (agent.success_rate * (agent.completed_tasks - 1)) /
                        agent.completed_tasks
                    )

        return True

    def execute_next_ready_step(self) -> bool:
        """
        Execute the next ready step in the workflow.

        Returns True if a step was executed, False if no steps are ready.
        """
        ready_steps = self.workflow.get_ready_steps()

        if not ready_steps:
            logger.info("No ready steps to execute")
            return False

        # Pick first ready step (could be improved with priority logic)
        step = ready_steps[0]

        # Auto-assign if not assigned
        if not step.assigned_to:
            if not self.auto_assign_agents():
                logger.warning(f"Could not assign agent to step {step.step_id}")
                return False

        # Start the step
        return self.start_step(step.step_id)

    def get_workflow_status(self) -> Dict[str, Any]:
        """Get comprehensive workflow status"""
        stats = self.workflow.workflow_statistics()

        # Add contract status
        contract_stats = {
            "total_contracts": len(self.contracts),
            "by_lifecycle": {}
        }

        for lifecycle_state in ContractLifecycle:
            count = len([
                c for c in self.contracts.values()
                if c.lifecycle_state == lifecycle_state
            ])
            if count > 0:
                contract_stats["by_lifecycle"][lifecycle_state.value] = count

        # Add handoff status
        handoff_stats = {
            "total_handoffs": len(self.handoffs),
            "by_status": {}
        }

        for status in HandoffStatus:
            count = len([
                h for h in self.handoffs.values()
                if h.status == status
            ])
            if count > 0:
                handoff_stats["by_status"][status.value] = count

        # Add team status
        team_stats = self.team.team_statistics()

        return {
            "orchestrator_id": self.orchestrator_id,
            "workflow": stats,
            "contracts": contract_stats,
            "handoffs": handoff_stats,
            "team": team_stats,
            "active_step_id": self.active_step_id,
            "total_events": len(self.events)
        }

    def _log_event(self, event: OrchestrationEvent) -> None:
        """Log an orchestration event"""
        self.events.append(event)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "orchestrator_id": self.orchestrator_id,
            "workflow": self.workflow.to_dict(),
            "team": self.team.to_dict(),
            "contracts": {
                cid: {
                    "contract_id": c.contract_id,
                    "name": c.name,
                    "lifecycle_state": c.lifecycle_state.value
                }
                for cid, c in self.contracts.items()
            },
            "handoffs": {
                hid: h.to_dict()
                for hid, h in self.handoffs.items()
            },
            "status": self.get_workflow_status(),
            "events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "step_id": e.step_id,
                    "contract_id": e.contract_id,
                    "handoff_id": e.handoff_id,
                    "agent_id": e.agent_id,
                    "details": e.details
                }
                for e in self.events
            ],
            "metadata": self.metadata
        }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "OrchestrationEvent",
    "ContractOrchestrator",
]
