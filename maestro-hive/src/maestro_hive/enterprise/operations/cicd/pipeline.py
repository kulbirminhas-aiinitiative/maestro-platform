"""
CI/CD Pipeline Orchestration - AC-1 Implementation.

Provides automated build, test, and deployment pipeline with stage gates.
"""

import uuid
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .stages import PipelineStage, StageOutput, StageStatus
from .gates import QualityGate, GateResult
from .artifacts import ArtifactManager


class TriggerType(str, Enum):
    """Pipeline trigger types."""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    WEBHOOK = "webhook"


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    name: str
    stages: list[dict[str, Any]] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    timeout_seconds: int = 3600
    max_retries: int = 3
    parallel_stages: bool = False
    environment_variables: dict[str, str] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate configuration."""
        if not self.name:
            raise ValueError("Pipeline name is required")
        if not self.stages:
            raise ValueError("At least one stage is required")
        return True


@dataclass
class PipelineTrigger:
    """Trigger for pipeline execution."""
    type: TriggerType
    source: str = ""
    branch: str = "main"
    commit_sha: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    triggered_by: str = "system"

    @classmethod
    def manual(cls, triggered_by: str, parameters: dict[str, Any] = None) -> "PipelineTrigger":
        """Create manual trigger."""
        return cls(
            type=TriggerType.MANUAL,
            triggered_by=triggered_by,
            parameters=parameters or {}
        )

    @classmethod
    def push(cls, branch: str, commit_sha: str) -> "PipelineTrigger":
        """Create push trigger."""
        return cls(
            type=TriggerType.PUSH,
            branch=branch,
            commit_sha=commit_sha
        )


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    run_id: str
    pipeline_id: str
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    stages: list[StageOutput] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "pipeline_id": self.pipeline_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stages": [s.to_dict() for s in self.stages],
            "artifacts": self.artifacts,
            "error": self.error,
            "duration_ms": self.duration_ms
        }


class PipelineOrchestrator:
    """Orchestrates CI/CD pipeline execution."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.config.validate()
        self.pipeline_id = str(uuid.uuid4())
        self.stages: list[PipelineStage] = []
        self.gates: list[QualityGate] = []
        self.artifacts = ArtifactManager()
        self._runs: dict[str, PipelineResult] = {}

    def add_stage(self, stage: PipelineStage) -> None:
        """Add stage to pipeline."""
        self.stages.append(stage)

    def add_gate(self, gate: QualityGate, after_stage: str) -> None:
        """Add quality gate after specified stage."""
        gate.after_stage = after_stage
        self.gates.append(gate)

    async def execute(self, trigger: PipelineTrigger) -> PipelineResult:
        """Execute pipeline with all stages."""
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        result = PipelineResult(
            run_id=run_id,
            pipeline_id=self.pipeline_id,
            status=PipelineStatus.RUNNING,
            started_at=started_at
        )
        self._runs[run_id] = result

        try:
            for stage in self.stages:
                # Execute stage
                stage_output = await stage.execute(
                    context={
                        "trigger": trigger,
                        "pipeline_id": self.pipeline_id,
                        "run_id": run_id,
                        "env": self.config.environment_variables
                    }
                )
                result.stages.append(stage_output)

                if stage_output.status == StageStatus.FAILED:
                    result.status = PipelineStatus.FAILED
                    result.error = f"Stage '{stage.name}' failed: {stage_output.error}"
                    break

                # Check quality gates
                gate_result = await self._check_gates(stage.name, stage_output)
                if not gate_result.passed:
                    result.status = PipelineStatus.FAILED
                    result.error = f"Quality gate failed after '{stage.name}': {gate_result.reason}"
                    break

            else:
                result.status = PipelineStatus.SUCCESS

            # Collect artifacts
            result.artifacts = await self.artifacts.collect_all()

        except asyncio.CancelledError:
            result.status = PipelineStatus.CANCELLED
            result.error = "Pipeline execution cancelled"
        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)

        result.completed_at = datetime.utcnow()
        result.duration_ms = int(
            (result.completed_at - result.started_at).total_seconds() * 1000
        )

        return result

    async def _check_gates(self, stage_name: str, stage_output: StageOutput) -> GateResult:
        """Check quality gates for stage."""
        for gate in self.gates:
            if gate.after_stage == stage_name:
                gate_result = await gate.evaluate(stage_output)
                if not gate_result.passed:
                    return gate_result
        return GateResult(passed=True)

    def get_run(self, run_id: str) -> Optional[PipelineResult]:
        """Get pipeline run by ID."""
        return self._runs.get(run_id)

    async def cancel(self, run_id: str) -> bool:
        """Cancel running pipeline."""
        run = self._runs.get(run_id)
        if run and run.status == PipelineStatus.RUNNING:
            run.status = PipelineStatus.CANCELLED
            run.completed_at = datetime.utcnow()
            return True
        return False
