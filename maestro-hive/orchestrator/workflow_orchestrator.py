"""
Workflow Orchestrator (MD-2124)

Unified orchestration layer providing single entry point for coordinating:
- DDE (Design Document Engine)
- Documentation generation
- Task management (JIRA integration)
- Governance protocols

Usage:
    orchestrator = WorkflowOrchestrator(config)
    result = await orchestrator.execute(requirement)
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union
)

from .event_bus import (
    EventBus, Event, EventType, get_event_bus, emit_event
)

logger = logging.getLogger(__name__)


class WorkflowPhase(Enum):
    """SDLC workflow phases"""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"


class WorkflowState(Enum):
    """Workflow execution states"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowConfig:
    """
    Configuration for workflow execution.

    Attributes:
        project_id: JIRA project ID (e.g., "MD")
        epic_id: Parent epic ID (optional)
        phases: Phases to execute (default: all)
        parallel_tasks: Maximum parallel tasks
        checkpoint_enabled: Enable checkpoint/resume
        governance_enabled: Enable governance checks
        documentation_enabled: Enable auto-documentation
        webhook_urls: URLs for event webhooks
        timeout_minutes: Workflow timeout
        retry_config: Retry configuration
    """
    project_id: str
    epic_id: Optional[str] = None
    phases: List[WorkflowPhase] = field(default_factory=lambda: list(WorkflowPhase))
    parallel_tasks: int = 4
    checkpoint_enabled: bool = True
    governance_enabled: bool = True
    documentation_enabled: bool = True
    webhook_urls: List[str] = field(default_factory=list)
    timeout_minutes: int = 120
    retry_config: Dict[str, Any] = field(default_factory=lambda: {
        'max_retries': 3,
        'base_delay': 1.0,
        'max_delay': 60.0
    })
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'project_id': self.project_id,
            'epic_id': self.epic_id,
            'phases': [p.value for p in self.phases],
            'parallel_tasks': self.parallel_tasks,
            'checkpoint_enabled': self.checkpoint_enabled,
            'governance_enabled': self.governance_enabled,
            'documentation_enabled': self.documentation_enabled,
            'webhook_urls': self.webhook_urls,
            'timeout_minutes': self.timeout_minutes,
            'retry_config': self.retry_config,
            'metadata': self.metadata
        }


@dataclass
class PhaseResult:
    """Result of a phase execution"""
    phase: WorkflowPhase
    status: str  # success, failed, skipped
    started_at: datetime
    completed_at: Optional[datetime] = None
    tasks_created: List[str] = field(default_factory=list)
    documents_generated: List[str] = field(default_factory=list)
    governance_passed: Optional[bool] = None
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Get phase duration"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'phase': self.phase.value,
            'status': self.status,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'tasks_created': self.tasks_created,
            'documents_generated': self.documents_generated,
            'governance_passed': self.governance_passed,
            'error_message': self.error_message,
            'artifacts': self.artifacts
        }


@dataclass
class WorkflowResult:
    """
    Complete workflow execution result.

    Attributes:
        workflow_id: Unique workflow identifier
        state: Final workflow state
        phases: Results from each phase
        total_tasks: Total tasks created
        total_documents: Total documents generated
        started_at: Workflow start time
        completed_at: Workflow completion time
        error_message: Error if failed
    """
    workflow_id: str
    state: WorkflowState
    config: WorkflowConfig
    phases: List[PhaseResult] = field(default_factory=list)
    total_tasks: int = 0
    total_documents: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    checkpoint_id: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Get total duration"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def is_success(self) -> bool:
        """Check if workflow completed successfully"""
        return self.state == WorkflowState.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workflow_id': self.workflow_id,
            'state': self.state.value,
            'config': self.config.to_dict(),
            'phases': [p.to_dict() for p in self.phases],
            'total_tasks': self.total_tasks,
            'total_documents': self.total_documents,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'is_success': self.is_success,
            'error_message': self.error_message,
            'checkpoint_id': self.checkpoint_id
        }


# Type for phase handlers
PhaseHandler = Callable[[str, WorkflowConfig, Dict[str, Any]], PhaseResult]


class WorkflowOrchestrator:
    """
    Unified workflow orchestrator for AI-driven SDLC.

    Provides single entry point for executing complete workflows,
    coordinating DDE, documentation, task management, and governance.

    Example:
        config = WorkflowConfig(project_id="MD")
        orchestrator = WorkflowOrchestrator(config)
        result = await orchestrator.execute({
            "title": "New Feature",
            "description": "Implement user authentication"
        })
    """

    def __init__(
        self,
        config: Optional[WorkflowConfig] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        Initialize the orchestrator.

        Args:
            config: Default workflow configuration
            event_bus: Event bus instance (uses default if not provided)
        """
        self.config = config or WorkflowConfig(project_id="MD")
        self.event_bus = event_bus or get_event_bus()
        self._phase_handlers: Dict[WorkflowPhase, PhaseHandler] = {}
        self._governance_handlers: List[Callable] = []
        self._active_workflows: Dict[str, WorkflowResult] = {}
        self._checkpoints: Dict[str, Dict[str, Any]] = {}

        # Register default phase handlers
        self._register_default_handlers()

        logger.info(f"WorkflowOrchestrator initialized for project {self.config.project_id}")

    def _register_default_handlers(self) -> None:
        """Register default phase handlers"""
        self.register_phase_handler(WorkflowPhase.REQUIREMENTS, self._handle_requirements)
        self.register_phase_handler(WorkflowPhase.DESIGN, self._handle_design)
        self.register_phase_handler(WorkflowPhase.IMPLEMENTATION, self._handle_implementation)
        self.register_phase_handler(WorkflowPhase.TESTING, self._handle_testing)
        self.register_phase_handler(WorkflowPhase.DEPLOYMENT, self._handle_deployment)

    def register_phase_handler(
        self,
        phase: WorkflowPhase,
        handler: PhaseHandler
    ) -> None:
        """
        Register a custom phase handler.

        Args:
            phase: Phase to handle
            handler: Handler function
        """
        self._phase_handlers[phase] = handler
        logger.debug(f"Registered handler for phase {phase.value}")

    def register_governance_check(
        self,
        check: Callable[[str, WorkflowPhase, Dict[str, Any]], bool]
    ) -> None:
        """
        Register a governance check.

        Args:
            check: Function returning True if governance passes
        """
        self._governance_handlers.append(check)

    def _emit(
        self,
        event_type: EventType,
        workflow_id: str,
        payload: Optional[Dict[str, Any]] = None,
        phase: Optional[str] = None
    ) -> Event:
        """Emit an event using this orchestrator's event bus."""
        event = Event(
            type=event_type,
            workflow_id=workflow_id,
            payload=payload or {},
            phase=phase
        )
        self.event_bus.emit(event)
        return event

    async def execute(
        self,
        requirement: Dict[str, Any],
        config: Optional[WorkflowConfig] = None
    ) -> WorkflowResult:
        """
        Execute a complete workflow.

        This is the single entry point for workflow execution.

        Args:
            requirement: Workflow requirement specification
                - title: Workflow title
                - description: Detailed description
                - priority: Priority level
                - labels: Optional labels
            config: Optional config override

        Returns:
            WorkflowResult with execution details
        """
        config = config or self.config
        workflow_id = str(uuid.uuid4())

        # Initialize result
        result = WorkflowResult(
            workflow_id=workflow_id,
            state=WorkflowState.PENDING,
            config=config,
            started_at=datetime.utcnow()
        )
        self._active_workflows[workflow_id] = result

        # Emit workflow started event
        self._emit(
            EventType.WORKFLOW_STARTED,
            workflow_id,
            payload={
                'requirement': requirement,
                'config': config.to_dict()
            }
        )

        try:
            result.state = WorkflowState.RUNNING

            # Execute phases in order
            context: Dict[str, Any] = {'requirement': requirement}

            for phase in config.phases:
                if phase == WorkflowPhase.COMPLETED:
                    continue

                # Check if checkpoint exists
                if config.checkpoint_enabled and workflow_id in self._checkpoints:
                    checkpoint = self._checkpoints[workflow_id]
                    if checkpoint.get('last_phase') == phase.value:
                        context = checkpoint.get('context', context)
                        logger.info(f"Restored from checkpoint at phase {phase.value}")

                # Execute phase
                phase_result = await self._execute_phase(
                    workflow_id, phase, config, context
                )
                result.phases.append(phase_result)

                # Update totals
                result.total_tasks += len(phase_result.tasks_created)
                result.total_documents += len(phase_result.documents_generated)

                # Check phase result
                if phase_result.status == 'failed':
                    result.state = WorkflowState.FAILED
                    result.error_message = phase_result.error_message
                    break

                # Store checkpoint
                if config.checkpoint_enabled:
                    self._create_checkpoint(workflow_id, phase, context)

                # Update context with phase artifacts
                context[phase.value] = phase_result.artifacts

            # Mark completed if all phases passed
            if result.state == WorkflowState.RUNNING:
                result.state = WorkflowState.COMPLETED

            result.completed_at = datetime.utcnow()

            # Emit completion event
            self._emit(
                EventType.WORKFLOW_COMPLETED if result.is_success else EventType.WORKFLOW_FAILED,
                workflow_id,
                payload=result.to_dict()
            )

            return result

        except Exception as e:
            logger.exception(f"Workflow {workflow_id} failed with exception")
            result.state = WorkflowState.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.utcnow()

            self._emit(
                EventType.WORKFLOW_FAILED,
                workflow_id,
                payload={'error': str(e)}
            )

            return result

        finally:
            # Cleanup
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]

    async def _execute_phase(
        self,
        workflow_id: str,
        phase: WorkflowPhase,
        config: WorkflowConfig,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """Execute a single phase"""
        started_at = datetime.utcnow()

        self._emit(
            EventType.PHASE_STARTED,
            workflow_id,
            phase=phase.value,
            payload={'context_keys': list(context.keys())}
        )

        try:
            # Run governance check if enabled
            if config.governance_enabled:
                governance_passed = await self._run_governance_checks(
                    workflow_id, phase, context
                )
                if not governance_passed:
                    return PhaseResult(
                        phase=phase,
                        status='failed',
                        started_at=started_at,
                        completed_at=datetime.utcnow(),
                        governance_passed=False,
                        error_message="Governance check failed"
                    )

            # Get phase handler
            handler = self._phase_handlers.get(phase)
            if not handler:
                return PhaseResult(
                    phase=phase,
                    status='skipped',
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    error_message=f"No handler registered for phase {phase.value}"
                )

            # Execute handler
            result = handler(workflow_id, config, context)
            result.governance_passed = True if config.governance_enabled else None

            self._emit(
                EventType.PHASE_COMPLETED,
                workflow_id,
                phase=phase.value,
                payload=result.to_dict()
            )

            return result

        except Exception as e:
            logger.exception(f"Phase {phase.value} failed")
            return PhaseResult(
                phase=phase,
                status='failed',
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )

    async def _run_governance_checks(
        self,
        workflow_id: str,
        phase: WorkflowPhase,
        context: Dict[str, Any]
    ) -> bool:
        """Run all registered governance checks"""
        self._emit(
            EventType.GOVERNANCE_CHECK_STARTED,
            workflow_id,
            phase=phase.value
        )

        for check in self._governance_handlers:
            try:
                if not check(workflow_id, phase, context):
                    self._emit(
                        EventType.GOVERNANCE_CHECK_FAILED,
                        workflow_id,
                        phase=phase.value
                    )
                    return False
            except Exception as e:
                logger.error(f"Governance check failed with exception: {e}")
                return False

        self._emit(
            EventType.GOVERNANCE_CHECK_PASSED,
            workflow_id,
            phase=phase.value
        )

        return True

    def _create_checkpoint(
        self,
        workflow_id: str,
        phase: WorkflowPhase,
        context: Dict[str, Any]
    ) -> str:
        """Create a checkpoint for the workflow"""
        checkpoint_id = str(uuid.uuid4())
        self._checkpoints[workflow_id] = {
            'checkpoint_id': checkpoint_id,
            'last_phase': phase.value,
            'context': context.copy(),
            'created_at': datetime.utcnow().isoformat()
        }

        self._emit(
            EventType.CHECKPOINT_CREATED,
            workflow_id,
            phase=phase.value,
            payload={'checkpoint_id': checkpoint_id}
        )

        logger.debug(f"Checkpoint created: {checkpoint_id}")
        return checkpoint_id

    async def resume(
        self,
        workflow_id: str,
        config: Optional[WorkflowConfig] = None
    ) -> WorkflowResult:
        """
        Resume a workflow from checkpoint.

        Args:
            workflow_id: Workflow to resume
            config: Optional config override

        Returns:
            WorkflowResult with execution details
        """
        if workflow_id not in self._checkpoints:
            raise ValueError(f"No checkpoint found for workflow {workflow_id}")

        checkpoint = self._checkpoints[workflow_id]
        context = checkpoint.get('context', {})
        last_phase = WorkflowPhase(checkpoint['last_phase'])

        self._emit(
            EventType.WORKFLOW_RESUMED,
            workflow_id,
            phase=last_phase.value,
            payload={'checkpoint_id': checkpoint['checkpoint_id']}
        )

        # Get remaining phases
        config = config or self.config
        remaining_phases = []
        found = False
        for phase in config.phases:
            if found:
                remaining_phases.append(phase)
            if phase == last_phase:
                found = True

        # Continue execution
        return await self.execute(
            requirement=context.get('requirement', {}),
            config=WorkflowConfig(
                **{**config.to_dict(), 'phases': remaining_phases}
            )
        )

    def pause(self, workflow_id: str) -> bool:
        """
        Pause a running workflow.

        Args:
            workflow_id: Workflow to pause

        Returns:
            True if paused successfully
        """
        if workflow_id in self._active_workflows:
            result = self._active_workflows[workflow_id]
            if result.state == WorkflowState.RUNNING:
                result.state = WorkflowState.PAUSED
                self._emit(EventType.WORKFLOW_PAUSED, workflow_id)
                return True
        return False

    def cancel(self, workflow_id: str) -> bool:
        """
        Cancel a workflow.

        Args:
            workflow_id: Workflow to cancel

        Returns:
            True if cancelled successfully
        """
        if workflow_id in self._active_workflows:
            result = self._active_workflows[workflow_id]
            result.state = WorkflowState.CANCELLED
            result.completed_at = datetime.utcnow()
            return True
        return False

    def get_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status"""
        if workflow_id in self._active_workflows:
            return self._active_workflows[workflow_id].to_dict()
        return None

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows"""
        return [w.to_dict() for w in self._active_workflows.values()]

    # Default phase handlers

    def _handle_requirements(
        self,
        workflow_id: str,
        config: WorkflowConfig,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """Default requirements phase handler"""
        started_at = datetime.utcnow()
        requirement = context.get('requirement', {})

        # Generate requirements document
        doc_id = f"REQ-{workflow_id[:8]}"

        return PhaseResult(
            phase=WorkflowPhase.REQUIREMENTS,
            status='success',
            started_at=started_at,
            completed_at=datetime.utcnow(),
            documents_generated=[doc_id],
            artifacts={
                'requirements_doc': doc_id,
                'title': requirement.get('title', 'Untitled'),
                'description': requirement.get('description', '')
            }
        )

    def _handle_design(
        self,
        workflow_id: str,
        config: WorkflowConfig,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """Default design phase handler"""
        started_at = datetime.utcnow()

        doc_id = f"DESIGN-{workflow_id[:8]}"

        return PhaseResult(
            phase=WorkflowPhase.DESIGN,
            status='success',
            started_at=started_at,
            completed_at=datetime.utcnow(),
            documents_generated=[doc_id],
            artifacts={
                'design_doc': doc_id,
                'architecture': 'default'
            }
        )

    def _handle_implementation(
        self,
        workflow_id: str,
        config: WorkflowConfig,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """Default implementation phase handler"""
        started_at = datetime.utcnow()

        task_id = f"{config.project_id}-IMPL-{workflow_id[:8]}"

        return PhaseResult(
            phase=WorkflowPhase.IMPLEMENTATION,
            status='success',
            started_at=started_at,
            completed_at=datetime.utcnow(),
            tasks_created=[task_id],
            artifacts={
                'implementation_task': task_id
            }
        )

    def _handle_testing(
        self,
        workflow_id: str,
        config: WorkflowConfig,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """Default testing phase handler"""
        started_at = datetime.utcnow()

        doc_id = f"TEST-{workflow_id[:8]}"
        task_id = f"{config.project_id}-TEST-{workflow_id[:8]}"

        return PhaseResult(
            phase=WorkflowPhase.TESTING,
            status='success',
            started_at=started_at,
            completed_at=datetime.utcnow(),
            tasks_created=[task_id],
            documents_generated=[doc_id],
            artifacts={
                'test_plan': doc_id,
                'test_task': task_id
            }
        )

    def _handle_deployment(
        self,
        workflow_id: str,
        config: WorkflowConfig,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """Default deployment phase handler"""
        started_at = datetime.utcnow()

        doc_id = f"DEPLOY-{workflow_id[:8]}"

        return PhaseResult(
            phase=WorkflowPhase.DEPLOYMENT,
            status='success',
            started_at=started_at,
            completed_at=datetime.utcnow(),
            documents_generated=[doc_id],
            artifacts={
                'runbook': doc_id
            }
        )


# Factory function
def create_orchestrator(
    project_id: str,
    epic_id: Optional[str] = None,
    **kwargs
) -> WorkflowOrchestrator:
    """
    Factory function to create an orchestrator.

    Args:
        project_id: JIRA project ID
        epic_id: Optional epic ID
        **kwargs: Additional config options

    Returns:
        Configured WorkflowOrchestrator
    """
    config = WorkflowConfig(
        project_id=project_id,
        epic_id=epic_id,
        **kwargs
    )
    return WorkflowOrchestrator(config)
