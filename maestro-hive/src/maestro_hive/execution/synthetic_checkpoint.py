#!/usr/bin/env python3
"""
Synthetic Checkpoint Generator

Creates checkpoints from external data to enable starting workflows
from intermediate phases without running previous phases.

This addresses the "Partial Execution" requirement from MD-3157:
- "Run Development Phase only" with external design data
- Inject external context as if previous phases had run

Usage:
    builder = SyntheticCheckpointBuilder()
    context = builder.inject_design_phase({
        "architecture": "microservices",
        "components": ["auth-service", "user-service"]
    })
    engine = TeamExecutionEngineV2SplitMode()
    result = await engine.execute_phase("implementation", context=context)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class SyntheticPhaseResult:
    """Result of a synthetic (injected) phase"""
    phase_name: str
    status: str = "completed"
    outputs: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    synthetic: bool = True
    injected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SyntheticCheckpoint:
    """Checkpoint created from external data"""
    workflow_id: str
    target_phase: str
    injected_phases: List[SyntheticPhaseResult]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "workflow_id": self.workflow_id,
            "target_phase": self.target_phase,
            "injected_phases": [asdict(p) for p in self.injected_phases],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "synthetic": True,
            "version": "1.0"
        }


class SyntheticCheckpointBuilder:
    """
    Builds synthetic checkpoints from external data.

    Enables starting workflows from intermediate phases by simulating
    the outputs of previous phases.
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """
        Initialize builder.

        Args:
            checkpoint_dir: Directory for storing checkpoints
        """
        if checkpoint_dir is not None:
            self.checkpoint_dir = Path(checkpoint_dir) if isinstance(checkpoint_dir, str) else checkpoint_dir
        else:
            self.checkpoint_dir = Path("./maestro_workflows.db")

        if self.checkpoint_dir.exists() and not self.checkpoint_dir.is_dir():
            # File exists with same name, use alternative path
            self.checkpoint_dir = Path(str(self.checkpoint_dir) + "_checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def inject_requirements_phase(
        self,
        requirements_data: Dict[str, Any],
        workflow_id: Optional[str] = None
    ) -> SyntheticCheckpoint:
        """
        Create checkpoint as if requirements phase completed.

        Args:
            requirements_data: External requirements data
            workflow_id: Optional workflow ID (auto-generated if not provided)

        Returns:
            Synthetic checkpoint ready for design phase
        """
        workflow_id = workflow_id or f"wf-synthetic-{uuid.uuid4().hex[:8]}"

        phase_result = SyntheticPhaseResult(
            phase_name="requirements",
            outputs={
                "classified_requirement": requirements_data.get("requirement", ""),
                "classification": requirements_data.get("classification", {
                    "type": "feature",
                    "complexity": "medium",
                    "estimated_phases": ["requirements", "design", "implementation", "testing"]
                }),
                "stakeholders": requirements_data.get("stakeholders", []),
                "constraints": requirements_data.get("constraints", []),
                "acceptance_criteria": requirements_data.get("acceptance_criteria", [])
            },
            artifacts=requirements_data.get("artifacts", [])
        )

        return SyntheticCheckpoint(
            workflow_id=workflow_id,
            target_phase="design",
            injected_phases=[phase_result],
            metadata={"source": "synthetic_injection", "type": "requirements"}
        )

    def inject_design_phase(
        self,
        design_data: Dict[str, Any],
        requirements_data: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> SyntheticCheckpoint:
        """
        Create checkpoint as if design phase completed.

        Args:
            design_data: External design data (architecture, components, etc.)
            requirements_data: Optional requirements context
            workflow_id: Optional workflow ID

        Returns:
            Synthetic checkpoint ready for implementation phase
        """
        workflow_id = workflow_id or f"wf-synthetic-{uuid.uuid4().hex[:8]}"
        phases = []

        # Create requirements phase if data provided
        if requirements_data:
            req_result = SyntheticPhaseResult(
                phase_name="requirements",
                outputs={
                    "classified_requirement": requirements_data.get("requirement", ""),
                    "classification": requirements_data.get("classification", {})
                }
            )
            phases.append(req_result)

        # Create design phase
        design_result = SyntheticPhaseResult(
            phase_name="design",
            outputs={
                "architecture": design_data.get("architecture", "monolith"),
                "components": design_data.get("components", []),
                "api_specs": design_data.get("api_specs", {}),
                "data_models": design_data.get("data_models", {}),
                "contracts": design_data.get("contracts", []),
                "blueprint": design_data.get("blueprint", {
                    "name": "custom",
                    "type": design_data.get("architecture", "monolith")
                }),
                "design_decisions": design_data.get("decisions", [])
            },
            artifacts=design_data.get("artifacts", [])
        )
        phases.append(design_result)

        return SyntheticCheckpoint(
            workflow_id=workflow_id,
            target_phase="implementation",
            injected_phases=phases,
            metadata={"source": "synthetic_injection", "type": "design"}
        )

    def inject_implementation_phase(
        self,
        implementation_data: Dict[str, Any],
        previous_phases: Optional[List[Dict[str, Any]]] = None,
        workflow_id: Optional[str] = None
    ) -> SyntheticCheckpoint:
        """
        Create checkpoint as if implementation phase completed.

        Args:
            implementation_data: External implementation data (code, artifacts)
            previous_phases: Optional previous phase results
            workflow_id: Optional workflow ID

        Returns:
            Synthetic checkpoint ready for testing phase
        """
        workflow_id = workflow_id or f"wf-synthetic-{uuid.uuid4().hex[:8]}"
        phases = []

        # Add previous phases if provided
        if previous_phases:
            for phase_data in previous_phases:
                phases.append(SyntheticPhaseResult(
                    phase_name=phase_data.get("phase_name", "unknown"),
                    outputs=phase_data.get("outputs", {}),
                    artifacts=phase_data.get("artifacts", [])
                ))

        # Create implementation phase
        impl_result = SyntheticPhaseResult(
            phase_name="implementation",
            outputs={
                "code_artifacts": implementation_data.get("code_artifacts", []),
                "files_created": implementation_data.get("files_created", []),
                "dependencies": implementation_data.get("dependencies", []),
                "contracts_fulfilled": implementation_data.get("contracts", []),
                "build_status": implementation_data.get("build_status", "success")
            },
            artifacts=implementation_data.get("artifacts", [])
        )
        phases.append(impl_result)

        return SyntheticCheckpoint(
            workflow_id=workflow_id,
            target_phase="testing",
            injected_phases=phases,
            metadata={"source": "synthetic_injection", "type": "implementation"}
        )

    def save_checkpoint(
        self,
        checkpoint: SyntheticCheckpoint,
        filename: Optional[str] = None
    ) -> Path:
        """
        Save checkpoint to filesystem.

        Args:
            checkpoint: Checkpoint to save
            filename: Optional custom filename

        Returns:
            Path to saved checkpoint file
        """
        # Create workflow directory
        workflow_dir = self.checkpoint_dir / checkpoint.workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        if not filename:
            last_phase = checkpoint.injected_phases[-1].phase_name if checkpoint.injected_phases else "init"
            filename = f"checkpoint_{last_phase}_synthetic.json"

        filepath = workflow_dir / filename

        # Write checkpoint
        with open(filepath, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        return filepath

    def load_checkpoint(self, filepath: Path) -> SyntheticCheckpoint:
        """
        Load a checkpoint from file.

        Args:
            filepath: Path to checkpoint file

        Returns:
            Loaded checkpoint
        """
        with open(filepath) as f:
            data = json.load(f)

        phases = [
            SyntheticPhaseResult(**p)
            for p in data.get("injected_phases", [])
        ]

        return SyntheticCheckpoint(
            workflow_id=data["workflow_id"],
            target_phase=data["target_phase"],
            injected_phases=phases,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )

    def to_execution_context(
        self,
        checkpoint: SyntheticCheckpoint
    ) -> Dict[str, Any]:
        """
        Convert synthetic checkpoint to execution context format.

        This format is compatible with TeamExecutionContext.

        Args:
            checkpoint: Synthetic checkpoint

        Returns:
            Dictionary compatible with TeamExecutionContext
        """
        phase_results = {}
        for phase in checkpoint.injected_phases:
            phase_results[phase.phase_name] = {
                "phase_name": phase.phase_name,
                "status": phase.status,
                "outputs": phase.outputs,
                "artifacts": phase.artifacts,
                "synthetic": phase.synthetic,
                "completed_at": phase.injected_at
            }

        return {
            "workflow_id": checkpoint.workflow_id,
            "phase_results": phase_results,
            "current_phase": checkpoint.target_phase,
            "checkpoint_metadata": {
                "version": 1,
                "created_at": checkpoint.created_at,
                "synthetic": True,
                "source": checkpoint.metadata.get("source", "synthetic_injection")
            }
        }


# Convenience function for quick synthetic checkpoint creation
def create_synthetic_checkpoint(
    phase: str,
    data: Dict[str, Any],
    checkpoint_dir: Optional[Path] = None
) -> Path:
    """
    Quick helper to create and save a synthetic checkpoint.

    Args:
        phase: Phase to inject (requirements, design, implementation)
        data: Phase-specific data
        checkpoint_dir: Optional checkpoint directory

    Returns:
        Path to saved checkpoint file
    """
    builder = SyntheticCheckpointBuilder(checkpoint_dir)

    if phase == "requirements":
        checkpoint = builder.inject_requirements_phase(data)
    elif phase == "design":
        checkpoint = builder.inject_design_phase(data)
    elif phase == "implementation":
        checkpoint = builder.inject_implementation_phase(data)
    else:
        raise ValueError(f"Unsupported phase for synthetic injection: {phase}")

    return builder.save_checkpoint(checkpoint)


__all__ = [
    "SyntheticCheckpointBuilder",
    "SyntheticCheckpoint",
    "SyntheticPhaseResult",
    "create_synthetic_checkpoint"
]
