"""
Workflow Pause Service
AC-5: Add pause and review capability to workflows
EU AI Act Article 14 - Human control over AI workflows
EPIC: MD-2158
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .compliance_logger import ComplianceLogger, ComplianceContext


class WorkflowState(Enum):
    """Workflow execution states."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowCheckpoint:
    """Checkpoint capturing workflow state at pause."""
    id: str
    workflow_id: str
    step_index: int
    step_name: str
    state: Dict[str, Any]
    captured_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowPauseRequest:
    """Request to pause a workflow."""
    workflow_id: str
    reason: str
    operator_id: str
    capture_checkpoint: bool = True
    context: Optional[ComplianceContext] = None


@dataclass
class WorkflowPauseResult:
    """Result of a workflow pause operation."""
    success: bool
    workflow_id: str
    previous_state: WorkflowState
    checkpoint: Optional[WorkflowCheckpoint]
    pause_id: str
    timestamp: datetime
    audit_log_id: str


@dataclass
class WorkflowRecord:
    """Workflow record in the system."""
    id: str
    name: str
    state: WorkflowState
    current_step: int
    current_step_name: str
    step_states: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class WorkflowPauseService:
    """
    Workflow Pause Service
    Provides pause and review capability for AI workflows with checkpoint support.
    EU AI Act Article 14 compliant human control mechanism.
    """

    def __init__(
        self,
        logger: ComplianceLogger,
        db_client: Optional[Any] = None,
        message_queue: Optional[Any] = None
    ):
        """
        Initialize workflow pause service.

        Args:
            logger: Compliance logger for audit trail
            db_client: Optional database client
            message_queue: Optional message queue for workflow control
        """
        self._logger = logger
        self._db = db_client
        self._mq = message_queue
        self._workflows: Dict[str, WorkflowRecord] = {}
        self._checkpoints: Dict[str, WorkflowCheckpoint] = {}
        self._pauses: Dict[str, Dict[str, Any]] = {}

    def _generate_pause_id(self) -> str:
        """Generate unique pause ID."""
        return f"pause_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _generate_checkpoint_id(self) -> str:
        """Generate unique checkpoint ID."""
        return f"chkpt_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def register_workflow(
        self,
        workflow_id: str,
        name: str,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> WorkflowRecord:
        """Register a workflow for pause tracking."""
        workflow = WorkflowRecord(
            id=workflow_id,
            name=name,
            state=WorkflowState.RUNNING,
            current_step=0,
            current_step_name="start",
            step_states=initial_state or {},
        )
        self._workflows[workflow_id] = workflow
        return workflow

    def update_workflow_step(
        self,
        workflow_id: str,
        step_index: int,
        step_name: str,
        step_state: Dict[str, Any]
    ) -> bool:
        """Update workflow current step information."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.current_step = step_index
        workflow.current_step_name = step_name
        workflow.step_states[step_name] = step_state
        workflow.updated_at = datetime.utcnow()
        return True

    async def pause_workflow(self, request: WorkflowPauseRequest) -> WorkflowPauseResult:
        """
        Pause a running workflow.

        Args:
            request: Pause request details

        Returns:
            WorkflowPauseResult with operation outcome

        Raises:
            ValueError: If workflow not found or not running
        """
        workflow = self._workflows.get(request.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {request.workflow_id}")

        if workflow.state != WorkflowState.RUNNING:
            raise ValueError(f"Workflow {request.workflow_id} is not running")

        previous_state = workflow.state
        pause_id = self._generate_pause_id()

        # Capture checkpoint if requested
        checkpoint = None
        if request.capture_checkpoint:
            checkpoint = WorkflowCheckpoint(
                id=self._generate_checkpoint_id(),
                workflow_id=request.workflow_id,
                step_index=workflow.current_step,
                step_name=workflow.current_step_name,
                state=workflow.step_states.copy(),
            )
            self._checkpoints[checkpoint.id] = checkpoint

        # Update workflow state
        workflow.state = WorkflowState.PAUSED
        workflow.updated_at = datetime.utcnow()

        # Record pause
        self._pauses[pause_id] = {
            "workflow_id": request.workflow_id,
            "operator_id": request.operator_id,
            "reason": request.reason,
            "checkpoint_id": checkpoint.id if checkpoint else None,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Send pause signal via message queue if available
        if self._mq:
            await self._mq.publish("workflow.control", {
                "type": "pause",
                "workflow_id": request.workflow_id,
                "pause_id": pause_id,
                "checkpoint_id": checkpoint.id if checkpoint else None,
                "command": "PAUSE",
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Log to audit
        audit_entry = await self._logger.log_workflow_control(
            request.operator_id,
            request.workflow_id,
            "pause",
            request.reason,
            checkpoint.id if checkpoint else None,
            request.context
        )

        return WorkflowPauseResult(
            success=True,
            workflow_id=request.workflow_id,
            previous_state=previous_state,
            checkpoint=checkpoint,
            pause_id=pause_id,
            timestamp=datetime.utcnow(),
            audit_log_id=audit_entry.id,
        )

    async def resume_workflow(
        self,
        workflow_id: str,
        pause_id: str,
        operator_id: str,
        from_checkpoint: Optional[str] = None,
        review_notes: Optional[str] = None
    ) -> WorkflowPauseResult:
        """
        Resume a paused workflow.

        Args:
            workflow_id: Workflow to resume
            pause_id: Original pause ID
            operator_id: Operator performing resume
            from_checkpoint: Optional checkpoint ID to resume from
            review_notes: Optional review notes

        Returns:
            WorkflowPauseResult with operation outcome

        Raises:
            ValueError: If workflow not found or not paused
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if workflow.state != WorkflowState.PAUSED:
            raise ValueError(f"Workflow {workflow_id} is not paused")

        # Verify pause exists
        pause = self._pauses.get(pause_id)
        if not pause or pause["workflow_id"] != workflow_id:
            raise ValueError(f"Pause {pause_id} not found for workflow {workflow_id}")

        previous_state = workflow.state

        # Restore from checkpoint if specified
        checkpoint = None
        if from_checkpoint:
            checkpoint = self._checkpoints.get(from_checkpoint)
            if checkpoint and checkpoint.workflow_id == workflow_id:
                workflow.current_step = checkpoint.step_index
                workflow.current_step_name = checkpoint.step_name
                workflow.step_states = checkpoint.state.copy()

        # Update workflow state
        workflow.state = WorkflowState.RUNNING
        workflow.updated_at = datetime.utcnow()

        # Send resume signal
        if self._mq:
            await self._mq.publish("workflow.control", {
                "type": "resume",
                "workflow_id": workflow_id,
                "pause_id": pause_id,
                "from_checkpoint": from_checkpoint,
                "command": "RESUME",
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Log to audit
        audit_entry = await self._logger.log_workflow_control(
            operator_id,
            workflow_id,
            "resume",
            review_notes or "Workflow resumed",
            from_checkpoint
        )

        return WorkflowPauseResult(
            success=True,
            workflow_id=workflow_id,
            previous_state=previous_state,
            checkpoint=checkpoint,
            pause_id=pause_id,
            timestamp=datetime.utcnow(),
            audit_log_id=audit_entry.id,
        )

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        return {
            "workflow_id": workflow.id,
            "name": workflow.name,
            "state": workflow.state.value,
            "current_step": workflow.current_step,
            "current_step_name": workflow.current_step_name,
            "updated_at": workflow.updated_at.isoformat(),
        }

    def list_paused_workflows(self) -> List[Dict[str, Any]]:
        """List all paused workflows."""
        paused = []
        for workflow in self._workflows.values():
            if workflow.state == WorkflowState.PAUSED:
                paused.append({
                    "workflow_id": workflow.id,
                    "name": workflow.name,
                    "current_step": workflow.current_step,
                    "current_step_name": workflow.current_step_name,
                    "paused_at": workflow.updated_at.isoformat(),
                })
        return paused

    def get_checkpoint(self, checkpoint_id: str) -> Optional[WorkflowCheckpoint]:
        """Get a specific checkpoint by ID."""
        return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(self, workflow_id: str) -> List[WorkflowCheckpoint]:
        """List all checkpoints for a workflow."""
        return [c for c in self._checkpoints.values() if c.workflow_id == workflow_id]

    def get_statistics(self) -> Dict[str, Any]:
        """Get workflow pause statistics."""
        by_state = {state.value: 0 for state in WorkflowState}

        for workflow in self._workflows.values():
            by_state[workflow.state.value] += 1

        return {
            "total_workflows": len(self._workflows),
            "by_state": by_state,
            "total_checkpoints": len(self._checkpoints),
            "total_pauses": len(self._pauses),
        }
