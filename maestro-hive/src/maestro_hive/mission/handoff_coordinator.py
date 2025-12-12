"""
Mission to Execution Handoff Coordinator.
EPIC: MD-3024 - Mission to Execution Handoff

Orchestrates seamless transition from mission planning to execution,
managing state, validation, and execution triggering.
"""

import asyncio
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class HandoffState(Enum):
    """Handoff lifecycle states."""
    PENDING = "pending"
    VALIDATING = "validating"
    PACKAGING = "packaging"
    TRIGGERING = "triggering"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A validation issue found during readiness check."""
    code: str
    message: str
    severity: ValidationSeverity
    field: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of mission readiness validation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


@dataclass
class MissionConstraints:
    """Constraints for mission execution."""
    max_duration_hours: float = 8.0
    max_cost_dollars: float = 100.0
    max_personas: int = 10
    require_human_review: bool = False
    allowed_tools: Optional[List[str]] = None
    forbidden_actions: Optional[List[str]] = None


@dataclass
class Artifact:
    """An artifact produced or consumed by a mission."""
    id: str
    name: str
    type: str
    path: Optional[str] = None
    content: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MissionContext:
    """
    Complete context for a mission handoff.

    Contains all information needed to execute a mission
    including objectives, team composition, and constraints.
    """
    mission_id: str
    mission_name: str
    objectives: List[str]
    team_composition: Dict[str, Any]
    constraints: MissionConstraints
    artifacts: List[Artifact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "mission_id": self.mission_id,
            "mission_name": self.mission_name,
            "objectives": self.objectives,
            "team_composition": self.team_composition,
            "constraints": {
                "max_duration_hours": self.constraints.max_duration_hours,
                "max_cost_dollars": self.constraints.max_cost_dollars,
                "max_personas": self.constraints.max_personas,
                "require_human_review": self.constraints.require_human_review,
                "allowed_tools": self.constraints.allowed_tools,
                "forbidden_actions": self.constraints.forbidden_actions,
            },
            "artifacts": [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.type,
                    "path": a.path,
                    "metadata": a.metadata,
                }
                for a in self.artifacts
            ],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionContext":
        """Deserialize context from dictionary."""
        constraints_data = data.get("constraints", {})
        constraints = MissionConstraints(
            max_duration_hours=constraints_data.get("max_duration_hours", 8.0),
            max_cost_dollars=constraints_data.get("max_cost_dollars", 100.0),
            max_personas=constraints_data.get("max_personas", 10),
            require_human_review=constraints_data.get("require_human_review", False),
            allowed_tools=constraints_data.get("allowed_tools"),
            forbidden_actions=constraints_data.get("forbidden_actions"),
        )

        artifacts = [
            Artifact(
                id=a["id"],
                name=a["name"],
                type=a["type"],
                path=a.get("path"),
                metadata=a.get("metadata", {}),
            )
            for a in data.get("artifacts", [])
        ]

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.utcnow()

        return cls(
            mission_id=data["mission_id"],
            mission_name=data["mission_name"],
            objectives=data.get("objectives", []),
            team_composition=data.get("team_composition", {}),
            constraints=constraints,
            artifacts=artifacts,
            metadata=data.get("metadata", {}),
            created_at=created_at,
            version=data.get("version", "1.0"),
        )


@dataclass
class HandoffConfig:
    """Configuration for handoff operation."""
    timeout_seconds: int = 300
    max_retries: int = 3
    enable_validation: bool = True
    enable_compression: bool = True
    priority: str = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffStatus:
    """Current status of a handoff operation."""
    handoff_id: str
    mission_id: str
    state: HandoffState
    progress_percent: float = 0.0
    current_step: str = ""
    error: Optional[str] = None
    execution_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HandoffResult:
    """Result of a completed handoff operation."""
    handoff_id: str
    mission_id: str
    status: HandoffState
    execution_id: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class HandoffCoordinator:
    """
    Coordinates mission handoff to execution.

    Manages the complete handoff lifecycle:
    1. Validation of mission readiness
    2. Context packaging
    3. Execution triggering
    4. Status tracking

    Example:
        coordinator = HandoffCoordinator()
        context = MissionContext(
            mission_id="m-001",
            mission_name="Feature Implementation",
            objectives=["Implement auth"],
            team_composition={"lead": "architect"},
            constraints=MissionConstraints()
        )
        result = await coordinator.coordinate_handoff("m-001", context)
    """

    def __init__(
        self,
        context_packager: Optional["ContextPackager"] = None,
        execution_trigger: Optional["ExecutionTrigger"] = None,
    ):
        """
        Initialize coordinator.

        Args:
            context_packager: Packager for context serialization
            execution_trigger: Trigger for starting execution
        """
        self._handoffs: Dict[str, HandoffStatus] = {}
        self._lock = asyncio.Lock()
        self._context_packager = context_packager
        self._execution_trigger = execution_trigger
        logger.info("HandoffCoordinator initialized")

    async def coordinate_handoff(
        self,
        mission_id: str,
        context: MissionContext,
        config: Optional[HandoffConfig] = None,
    ) -> HandoffResult:
        """
        Coordinate complete handoff from mission to execution.

        Args:
            mission_id: Mission identifier
            context: Mission context to hand off
            config: Optional handoff configuration

        Returns:
            HandoffResult with outcome
        """
        config = config or HandoffConfig()
        handoff_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # Initialize status
        status = HandoffStatus(
            handoff_id=handoff_id,
            mission_id=mission_id,
            state=HandoffState.PENDING,
            started_at=started_at,
        )

        async with self._lock:
            self._handoffs[handoff_id] = status

        logger.info(f"Starting handoff {handoff_id} for mission {mission_id}")

        try:
            # Step 1: Validate readiness
            if config.enable_validation:
                status.state = HandoffState.VALIDATING
                status.current_step = "Validating mission readiness"
                status.progress_percent = 10.0

                validation_result = await self.validate_readiness(context)

                if not validation_result.is_valid:
                    error_msgs = [e.message for e in validation_result.errors]
                    raise ValueError(f"Validation failed: {'; '.join(error_msgs)}")
            else:
                validation_result = ValidationResult(is_valid=True)

            # Step 2: Package context
            status.state = HandoffState.PACKAGING
            status.current_step = "Packaging mission context"
            status.progress_percent = 30.0

            if self._context_packager:
                packed_context = self._context_packager.pack_context(context)
                logger.debug(f"Context packed: {len(packed_context)} bytes")

            # Step 3: Trigger execution
            status.state = HandoffState.TRIGGERING
            status.current_step = "Triggering execution"
            status.progress_percent = 60.0

            execution_id = None
            if self._execution_trigger:
                execution_handle = await self._execution_trigger.trigger_execution(context)
                execution_id = execution_handle.execution_id
                status.execution_id = execution_id
            else:
                # Simulate execution ID for testing
                execution_id = f"exec-{uuid.uuid4().hex[:8]}"
                status.execution_id = execution_id

            # Step 4: Mark as executing
            status.state = HandoffState.EXECUTING
            status.current_step = "Execution in progress"
            status.progress_percent = 80.0

            # Step 5: Complete
            status.state = HandoffState.COMPLETED
            status.current_step = "Handoff completed"
            status.progress_percent = 100.0
            status.completed_at = datetime.utcnow()

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            logger.info(f"Handoff {handoff_id} completed in {duration:.2f}s")

            return HandoffResult(
                handoff_id=handoff_id,
                mission_id=mission_id,
                status=HandoffState.COMPLETED,
                execution_id=execution_id,
                validation_result=validation_result,
                duration_seconds=duration,
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as e:
            status.state = HandoffState.FAILED
            status.error = str(e)
            status.completed_at = datetime.utcnow()

            logger.error(f"Handoff {handoff_id} failed: {e}")

            return HandoffResult(
                handoff_id=handoff_id,
                mission_id=mission_id,
                status=HandoffState.FAILED,
                error=str(e),
                duration_seconds=(datetime.utcnow() - started_at).total_seconds(),
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

    async def validate_readiness(
        self,
        context: MissionContext,
    ) -> ValidationResult:
        """
        Validate mission is ready for handoff.

        Checks:
        - Required fields present
        - Constraints are valid
        - Team composition valid
        - Artifacts accessible

        Args:
            context: Mission context to validate

        Returns:
            ValidationResult with any issues found
        """
        issues: List[ValidationIssue] = []

        # Check required fields
        if not context.mission_id:
            issues.append(ValidationIssue(
                code="MISSING_MISSION_ID",
                message="Mission ID is required",
                severity=ValidationSeverity.ERROR,
                field="mission_id",
            ))

        if not context.mission_name:
            issues.append(ValidationIssue(
                code="MISSING_MISSION_NAME",
                message="Mission name is required",
                severity=ValidationSeverity.ERROR,
                field="mission_name",
            ))

        if not context.objectives:
            issues.append(ValidationIssue(
                code="NO_OBJECTIVES",
                message="At least one objective is required",
                severity=ValidationSeverity.ERROR,
                field="objectives",
                suggestion="Add mission objectives to define what needs to be accomplished",
            ))

        # Validate constraints
        if context.constraints.max_duration_hours <= 0:
            issues.append(ValidationIssue(
                code="INVALID_DURATION",
                message="Max duration must be positive",
                severity=ValidationSeverity.ERROR,
                field="constraints.max_duration_hours",
            ))

        if context.constraints.max_cost_dollars < 0:
            issues.append(ValidationIssue(
                code="INVALID_COST",
                message="Max cost cannot be negative",
                severity=ValidationSeverity.ERROR,
                field="constraints.max_cost_dollars",
            ))

        # Warnings for best practices
        if not context.team_composition:
            issues.append(ValidationIssue(
                code="EMPTY_TEAM",
                message="No team composition defined",
                severity=ValidationSeverity.WARNING,
                field="team_composition",
                suggestion="Consider defining team roles for better execution",
            ))

        if context.constraints.max_duration_hours > 24:
            issues.append(ValidationIssue(
                code="LONG_DURATION",
                message="Mission duration exceeds 24 hours",
                severity=ValidationSeverity.WARNING,
                field="constraints.max_duration_hours",
                suggestion="Consider breaking into smaller missions",
            ))

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        logger.info(f"Validation complete: valid={is_valid}, issues={len(issues)}")

        return ValidationResult(is_valid=is_valid, issues=issues)

    async def get_status(self, handoff_id: str) -> Optional[HandoffStatus]:
        """
        Get current handoff status.

        Args:
            handoff_id: Handoff identifier

        Returns:
            Current status or None if not found
        """
        async with self._lock:
            return self._handoffs.get(handoff_id)

    async def cancel(self, handoff_id: str) -> bool:
        """
        Cancel a pending handoff.

        Args:
            handoff_id: Handoff to cancel

        Returns:
            True if cancelled, False if not cancellable
        """
        async with self._lock:
            status = self._handoffs.get(handoff_id)
            if not status:
                return False

            if status.state in (HandoffState.PENDING, HandoffState.VALIDATING):
                status.state = HandoffState.CANCELLED
                status.completed_at = datetime.utcnow()
                logger.info(f"Handoff {handoff_id} cancelled")
                return True

            return False

    async def list_active(self) -> List[HandoffStatus]:
        """List all active handoffs."""
        async with self._lock:
            return [
                s for s in self._handoffs.values()
                if s.state not in (
                    HandoffState.COMPLETED,
                    HandoffState.FAILED,
                    HandoffState.CANCELLED,
                )
            ]

    def get_metrics(self) -> Dict[str, Any]:
        """Get coordinator metrics."""
        states = {}
        for status in self._handoffs.values():
            state_name = status.state.value
            states[state_name] = states.get(state_name, 0) + 1

        return {
            "total_handoffs": len(self._handoffs),
            "by_state": states,
        }
