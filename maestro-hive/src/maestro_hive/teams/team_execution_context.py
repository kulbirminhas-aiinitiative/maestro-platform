#!/usr/bin/env python3
"""
Team Execution Context - Enhanced State Management for Split Mode

This module provides unified state management combining:
- SDLC workflow context (from sdlc_workflow_context.py)
- Team execution state (from team_execution_v2.py)
- Checkpoint serialization/deserialization
- Contract validation tracking

Enables:
- Phase-by-phase execution with full state persistence
- Human edits between phases
- Contract validation at phase boundaries
- Complete audit trail of decisions and results
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# Add conductor path for imports
conductor_path = Path("/home/ec2-user/projects/conductor")
sys.path.insert(0, str(conductor_path))

# Import SDLC workflow context
from examples.sdlc_workflow_context import (
    WorkflowContext,
    PhaseResult,
    PhaseStatus
)

# Import team execution data models
from team_execution_v2 import (
    RequirementClassification,
    BlueprintRecommendation,
    ContractSpecification,
    ExecutionResult,
    RequirementComplexity,
    ParallelizabilityLevel
)


# =============================================================================
# CHECKPOINT METADATA
# =============================================================================

class CheckpointType(str, Enum):
    """Type of checkpoint"""
    PHASE_BOUNDARY = "phase_boundary"  # After phase completes
    HUMAN_REVIEW = "human_review"       # Awaiting human input
    ERROR_RECOVERY = "error_recovery"   # After error for recovery
    BATCH_COMPLETE = "batch_complete"   # After all phases


@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint"""
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    workflow_id: str = ""
    phase_completed: Optional[str] = None
    awaiting_phase: Optional[str] = None
    checkpoint_type: CheckpointType = CheckpointType.PHASE_BOUNDARY

    # Human interaction
    awaiting_human_review: bool = False
    human_edits_applied: bool = False

    # Quality gates
    quality_gate_passed: bool = True
    quality_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['checkpoint_type'] = self.checkpoint_type.value
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointMetadata':
        """Create from dictionary"""
        if 'checkpoint_type' in data:
            data['checkpoint_type'] = CheckpointType(data['checkpoint_type'])
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


# =============================================================================
# TEAM EXECUTION STATE
# =============================================================================

@dataclass
class TeamExecutionState:
    """
    Complete team execution state across all phases.

    Captures:
    - AI-driven requirement classification
    - Blueprint selections per phase
    - Contract specifications
    - Persona execution results per phase
    - Quality and timing metrics
    """

    # Requirement analysis (once at start)
    classification: Optional[RequirementClassification] = None

    # Blueprint selection per phase
    blueprint_selections: Dict[str, BlueprintRecommendation] = field(default_factory=dict)

    # Contracts designed for execution
    contract_specs: List[ContractSpecification] = field(default_factory=list)

    # Persona execution results per phase
    # Format: {phase_name: {persona_id: ExecutionResult}}
    persona_results: Dict[str, Dict[str, ExecutionResult]] = field(default_factory=dict)

    # Quality metrics per phase
    quality_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Timing metrics per phase
    timing_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # RAG-related fields (template recommendations and usage)
    template_package_id: Optional[str] = None
    template_package_name: Optional[str] = None
    template_package_confidence: float = 0.0
    template_package_explanation: str = ""

    # Templates recommended per persona
    # Format: {persona_id: [{"template_id": str, "name": str, "relevance": float, ...}]}
    recommended_templates: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Templates actually used per persona
    # Format: {persona_id: [template_id, ...]}
    templates_used: Dict[str, List[str]] = field(default_factory=dict)

    # Template selection reasoning per persona
    template_selection_reasoning: Dict[str, str] = field(default_factory=dict)

    # Custom development tracking (when templates were rejected)
    custom_development_reasons: Dict[str, str] = field(default_factory=dict)

    def add_blueprint_selection(
        self,
        phase_name: str,
        blueprint_rec: BlueprintRecommendation
    ):
        """Add blueprint selection for a phase"""
        self.blueprint_selections[phase_name] = blueprint_rec

    def add_persona_results(
        self,
        phase_name: str,
        results: Dict[str, ExecutionResult]
    ):
        """Add persona execution results for a phase"""
        self.persona_results[phase_name] = results

    def add_quality_metrics(
        self,
        phase_name: str,
        metrics: Dict[str, Any]
    ):
        """Add quality metrics for a phase"""
        self.quality_metrics[phase_name] = metrics

    def add_timing_metrics(
        self,
        phase_name: str,
        metrics: Dict[str, Any]
    ):
        """Add timing metrics for a phase"""
        self.timing_metrics[phase_name] = metrics

    def get_overall_quality(self) -> float:
        """Calculate overall quality score across all phases"""
        if not self.quality_metrics:
            return 0.0

        scores = [
            metrics.get('overall_quality', 0.0)
            for metrics in self.quality_metrics.values()
        ]

        return sum(scores) / len(scores) if scores else 0.0

    def get_total_duration(self) -> float:
        """Get total execution duration across all phases"""
        if not self.timing_metrics:
            return 0.0

        return sum(
            metrics.get('phase_duration', 0.0)
            for metrics in self.timing_metrics.values()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "classification": asdict(self.classification) if self.classification else None,
            "blueprint_selections": {
                phase: {
                    "blueprint_id": br.blueprint_id,
                    "blueprint_name": br.blueprint_name,
                    "match_score": br.match_score,
                    "personas": br.personas,
                    "rationale": br.rationale,
                    "execution_mode": br.execution_mode,
                    "coordination_mode": br.coordination_mode,
                    "scaling_strategy": br.scaling_strategy,
                    "estimated_time_savings": br.estimated_time_savings
                }
                for phase, br in self.blueprint_selections.items()
            },
            "contract_specs": [
                {
                    "id": c.id,
                    "name": c.name,
                    "version": c.version,
                    "contract_type": c.contract_type,
                    "deliverables": c.deliverables,
                    "dependencies": c.dependencies,
                    "provider_persona_id": c.provider_persona_id,
                    "consumer_persona_ids": c.consumer_persona_ids,
                    "acceptance_criteria": c.acceptance_criteria,
                    "estimated_effort_hours": c.estimated_effort_hours
                }
                for c in self.contract_specs
            ],
            "persona_results": {
                phase: {
                    persona_id: {
                        "persona_id": r.persona_id,
                        "contract_id": r.contract_id,
                        "success": r.success,
                        "files_created": r.files_created,
                        "deliverables": r.deliverables,
                        "contract_fulfilled": r.contract_fulfilled,
                        "fulfillment_score": r.fulfillment_score,
                        "quality_score": r.quality_score,
                        "completeness_score": r.completeness_score,
                        "duration_seconds": r.duration_seconds
                    }
                    for persona_id, r in results.items()
                }
                for phase, results in self.persona_results.items()
            },
            "quality_metrics": self.quality_metrics,
            "timing_metrics": self.timing_metrics,
            # RAG-related fields
            "template_package_id": self.template_package_id,
            "template_package_name": self.template_package_name,
            "template_package_confidence": self.template_package_confidence,
            "template_package_explanation": self.template_package_explanation,
            "recommended_templates": self.recommended_templates,
            "templates_used": self.templates_used,
            "template_selection_reasoning": self.template_selection_reasoning,
            "custom_development_reasons": self.custom_development_reasons
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamExecutionState':
        """Create from dictionary"""
        # Restore classification
        classification = None
        if data.get("classification"):
            c = data["classification"]
            classification = RequirementClassification(
                requirement_type=c["requirement_type"],
                complexity=RequirementComplexity(c["complexity"]),
                parallelizability=ParallelizabilityLevel(c["parallelizability"]),
                required_expertise=c["required_expertise"],
                estimated_effort_hours=c["estimated_effort_hours"],
                dependencies=c["dependencies"],
                risks=c["risks"],
                rationale=c["rationale"],
                confidence_score=c["confidence_score"]
            )

        # Restore blueprint selections
        blueprint_selections = {}
        for phase, br_data in data.get("blueprint_selections", {}).items():
            blueprint_selections[phase] = BlueprintRecommendation(
                blueprint_id=br_data["blueprint_id"],
                blueprint_name=br_data["blueprint_name"],
                match_score=br_data["match_score"],
                personas=br_data["personas"],
                rationale=br_data["rationale"],
                alternatives=[],
                execution_mode=br_data["execution_mode"],
                coordination_mode=br_data["coordination_mode"],
                scaling_strategy=br_data["scaling_strategy"],
                estimated_time_savings=br_data["estimated_time_savings"]
            )

        # Restore contract specs
        contract_specs = []
        for c_data in data.get("contract_specs", []):
            contract_specs.append(ContractSpecification(
                id=c_data["id"],
                name=c_data["name"],
                version=c_data["version"],
                contract_type=c_data["contract_type"],
                deliverables=c_data["deliverables"],
                dependencies=c_data["dependencies"],
                provider_persona_id=c_data["provider_persona_id"],
                consumer_persona_ids=c_data["consumer_persona_ids"],
                acceptance_criteria=c_data["acceptance_criteria"],
                estimated_effort_hours=c_data["estimated_effort_hours"]
            ))

        # Restore persona results
        persona_results = {}
        for phase, results in data.get("persona_results", {}).items():
            persona_results[phase] = {
                persona_id: ExecutionResult(
                    persona_id=r_data["persona_id"],
                    contract_id=r_data["contract_id"],
                    success=r_data["success"],
                    files_created=r_data["files_created"],
                    deliverables=r_data["deliverables"],
                    contract_fulfilled=r_data["contract_fulfilled"],
                    fulfillment_score=r_data["fulfillment_score"],
                    missing_deliverables=[],
                    quality_issues=[],
                    duration_seconds=r_data["duration_seconds"],
                    parallel_execution=False,
                    quality_score=r_data["quality_score"],
                    completeness_score=r_data["completeness_score"],
                    recommendations=[],
                    risks_identified=[]
                )
                for persona_id, r_data in results.items()
            }

        return cls(
            classification=classification,
            blueprint_selections=blueprint_selections,
            contract_specs=contract_specs,
            persona_results=persona_results,
            quality_metrics=data.get("quality_metrics", {}),
            timing_metrics=data.get("timing_metrics", {}),
            # RAG-related fields
            template_package_id=data.get("template_package_id"),
            template_package_name=data.get("template_package_name"),
            template_package_confidence=data.get("template_package_confidence", 0.0),
            template_package_explanation=data.get("template_package_explanation", ""),
            recommended_templates=data.get("recommended_templates", {}),
            templates_used=data.get("templates_used", {}),
            template_selection_reasoning=data.get("template_selection_reasoning", {}),
            custom_development_reasons=data.get("custom_development_reasons", {})
        )


# =============================================================================
# UNIFIED TEAM EXECUTION CONTEXT
# =============================================================================

@dataclass
class TeamExecutionContext:
    """
    Unified context combining workflow state and team execution state.

    This is the complete checkpoint that can be serialized/deserialized
    for phase-by-phase execution with full state persistence.
    """

    # Workflow context (SDLC phases)
    workflow: WorkflowContext

    # Team execution state
    team_state: TeamExecutionState

    # Checkpoint metadata
    checkpoint_metadata: CheckpointMetadata = field(default_factory=CheckpointMetadata)

    @classmethod
    def create_new(
        cls,
        requirement: str,
        workflow_id: str,
        execution_mode: str = "phased"
    ) -> 'TeamExecutionContext':
        """
        Create new context for a workflow.

        Args:
            requirement: Initial project requirement
            workflow_id: Unique workflow identifier
            execution_mode: Execution mode (single-go, phased, mixed)

        Returns:
            New TeamExecutionContext
        """
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type="sdlc",
            execution_mode=execution_mode,
            metadata={"initial_requirement": requirement}
        )

        team_state = TeamExecutionState()

        checkpoint_metadata = CheckpointMetadata(
            workflow_id=workflow_id
        )

        return cls(
            workflow=workflow,
            team_state=team_state,
            checkpoint_metadata=checkpoint_metadata
        )

    def add_blueprint_selection(
        self,
        phase_name: str,
        blueprint_rec: BlueprintRecommendation
    ):
        """Add blueprint selection for a phase"""
        self.team_state.add_blueprint_selection(phase_name, blueprint_rec)

    def add_persona_results(
        self,
        phase_name: str,
        results: Dict[str, ExecutionResult]
    ):
        """Add persona execution results for a phase"""
        self.team_state.add_persona_results(phase_name, results)

    def add_quality_metrics(
        self,
        phase_name: str,
        metrics: Dict[str, Any]
    ):
        """Add quality metrics for a phase"""
        self.team_state.add_quality_metrics(phase_name, metrics)

    def add_timing_metrics(
        self,
        phase_name: str,
        metrics: Dict[str, Any]
    ):
        """Add timing metrics for a phase"""
        self.team_state.add_timing_metrics(phase_name, metrics)

    def create_checkpoint(self, checkpoint_path: str):
        """
        Create checkpoint file with complete state.

        Args:
            checkpoint_path: Path to save checkpoint JSON
        """
        # Update checkpoint metadata
        self.checkpoint_metadata.workflow_id = self.workflow.workflow_id
        self.checkpoint_metadata.phase_completed = self.workflow.current_phase
        self.checkpoint_metadata.awaiting_human_review = self.workflow.awaiting_human_review
        self.checkpoint_metadata.quality_score = self.team_state.get_overall_quality()

        # Serialize to dict
        checkpoint_data = {
            "checkpoint_metadata": self.checkpoint_metadata.to_dict(),
            "workflow_context": self.workflow.to_dict(),
            "team_execution_state": self.team_state.to_dict()
        }

        # Validate before saving
        if not self._validate_checkpoint(checkpoint_data):
            raise ValueError("Checkpoint validation failed")

        # Save to file
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

        # Update workflow checkpoint info
        self.workflow.checkpoint_path = checkpoint_path
        self.workflow.last_checkpoint_at = datetime.utcnow()

    @classmethod
    def load_from_checkpoint(cls, checkpoint_path: str) -> 'TeamExecutionContext':
        """
        Load context from checkpoint file.

        Args:
            checkpoint_path: Path to checkpoint JSON

        Returns:
            Restored TeamExecutionContext
        """
        with open(checkpoint_path) as f:
            data = json.load(f)

        # Validate checkpoint
        if not cls._validate_checkpoint(data):
            raise ValueError(f"Invalid checkpoint: {checkpoint_path}")

        # Check version
        version = data["checkpoint_metadata"].get("version", "1.0")
        if version != "1.0":
            raise ValueError(f"Unsupported checkpoint version: {version}")

        # Restore components
        checkpoint_metadata = CheckpointMetadata.from_dict(data["checkpoint_metadata"])
        workflow = WorkflowContext.from_dict(data["workflow_context"])
        team_state = TeamExecutionState.from_dict(data["team_execution_state"])

        return cls(
            workflow=workflow,
            team_state=team_state,
            checkpoint_metadata=checkpoint_metadata
        )

    @staticmethod
    def _validate_checkpoint(data: Dict[str, Any]) -> bool:
        """Validate checkpoint data"""
        required_keys = ["checkpoint_metadata", "workflow_context", "team_execution_state"]

        if not all(key in data for key in required_keys):
            return False

        # Validate metadata
        metadata = data["checkpoint_metadata"]
        if not metadata.get("version") or not metadata.get("workflow_id"):
            return False

        # Validate workflow context
        workflow = data["workflow_context"]
        if not workflow.get("workflow_id") or not isinstance(workflow.get("phase_results"), dict):
            return False

        return True

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of context"""
        workflow_summary = self.workflow.get_workflow_summary()

        return {
            **workflow_summary,
            "overall_quality": self.team_state.get_overall_quality(),
            "total_execution_time": self.team_state.get_total_duration(),
            "blueprints_used": len(self.team_state.blueprint_selections),
            "contracts_designed": len(self.team_state.contract_specs),
            "personas_executed": sum(
                len(results) for results in self.team_state.persona_results.values()
            ),
            "checkpoint_info": {
                "last_checkpoint": self.workflow.checkpoint_path,
                "awaiting_review": self.checkpoint_metadata.awaiting_human_review,
                "quality_gate_passed": self.checkpoint_metadata.quality_gate_passed
            }
        }

    def print_summary(self):
        """Print formatted summary"""
        summary = self.get_summary()

        print("\n" + "="*80)
        print("TEAM EXECUTION CONTEXT SUMMARY")
        print("="*80)
        print(f"Workflow ID: {summary['workflow_id']}")
        print(f"Execution Mode: {summary['execution_mode']}")
        print(f"")
        print(f"Progress:")
        print(f"  Phases: {summary['completed_phases']}/{summary['total_phases']}")
        print(f"  Current Phase: {summary['current_phase']}")
        print(f"  Duration: {summary['total_duration_seconds']:.1f}s ({summary['total_execution_time']:.1f}s)")
        print(f"")
        print(f"Team Execution:")
        print(f"  Blueprints Used: {summary['blueprints_used']}")
        print(f"  Contracts Designed: {summary['contracts_designed']}")
        print(f"  Personas Executed: {summary['personas_executed']}")
        print(f"")
        print(f"Quality:")
        print(f"  Overall Quality: {summary['overall_quality']:.0%}")
        print(f"  Quality Gate: {'✅ PASSED' if summary['checkpoint_info']['quality_gate_passed'] else '❌ FAILED'}")
        print(f"")
        print(f"Checkpoint:")
        print(f"  Path: {summary['checkpoint_info']['last_checkpoint']}")
        print(f"  Awaiting Review: {summary['checkpoint_info']['awaiting_review']}")
        print(f"")
        print(f"Artifacts:")
        print(f"  Total: {summary['artifacts_created']}")
        print(f"  Contracts Validated: {summary['contracts_validated']}")
        print("="*80)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def list_checkpoints(checkpoint_dir: str) -> List[Dict[str, Any]]:
    """
    List all checkpoints in a directory.

    Args:
        checkpoint_dir: Directory containing checkpoints

    Returns:
        List of checkpoint metadata dicts
    """
    checkpoint_path = Path(checkpoint_dir)
    if not checkpoint_path.exists():
        return []

    checkpoints = []
    for filepath in sorted(checkpoint_path.glob("checkpoint_*.json")):
        try:
            with open(filepath) as f:
                data = json.load(f)

            metadata = data.get("checkpoint_metadata", {})
            workflow = data.get("workflow_context", {})

            checkpoints.append({
                "file": str(filepath),
                "workflow_id": metadata.get("workflow_id"),
                "created_at": metadata.get("created_at"),
                "phase_completed": metadata.get("phase_completed"),
                "awaiting_phase": metadata.get("awaiting_phase"),
                "quality_score": metadata.get("quality_score", 0.0),
                "phases_completed": len(workflow.get("phase_results", {})),
                "awaiting_review": metadata.get("awaiting_human_review", False)
            })
        except Exception as e:
            print(f"Warning: Failed to read checkpoint {filepath}: {e}")

    return checkpoints


def validate_checkpoint_file(checkpoint_path: str) -> Dict[str, Any]:
    """
    Validate a checkpoint file.

    Args:
        checkpoint_path: Path to checkpoint file

    Returns:
        Validation result dict with status and issues
    """
    issues = []

    # Check file exists
    if not Path(checkpoint_path).exists():
        return {
            "valid": False,
            "issues": [f"File does not exist: {checkpoint_path}"]
        }

    try:
        with open(checkpoint_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "issues": [f"Invalid JSON: {e}"]
        }

    # Validate structure
    required_keys = ["checkpoint_metadata", "workflow_context", "team_execution_state"]
    for key in required_keys:
        if key not in data:
            issues.append(f"Missing required key: {key}")

    # Validate version
    version = data.get("checkpoint_metadata", {}).get("version")
    if version != "1.0":
        issues.append(f"Unsupported version: {version}")

    # Validate workflow ID
    workflow_id = data.get("checkpoint_metadata", {}).get("workflow_id")
    if not workflow_id:
        issues.append("Missing workflow_id")

    # Validate phase results
    phase_results = data.get("workflow_context", {}).get("phase_results", {})
    if not isinstance(phase_results, dict):
        issues.append("Invalid phase_results structure")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "workflow_id": workflow_id,
        "phases_completed": len(phase_results),
        "version": version
    }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Create new context
    context = TeamExecutionContext.create_new(
        requirement="Build a REST API for ML model training",
        workflow_id="workflow-test-001",
        execution_mode="phased"
    )

    print("Created new context:")
    context.print_summary()

    # Example: Add some data
    classification = RequirementClassification(
        requirement_type="feature_development",
        complexity=RequirementComplexity.COMPLEX,
        parallelizability=ParallelizabilityLevel.FULLY_PARALLEL,
        required_expertise=["backend", "ml", "api"],
        estimated_effort_hours=40.0,
        dependencies=[],
        risks=["Model complexity"],
        rationale="Full-stack ML API with parallel backend/frontend potential",
        confidence_score=0.92
    )
    context.team_state.classification = classification

    # Example: Save checkpoint
    checkpoint_path = "/tmp/test_checkpoint.json"
    context.create_checkpoint(checkpoint_path)
    print(f"\n✅ Checkpoint saved to: {checkpoint_path}")

    # Example: Load checkpoint
    loaded_context = TeamExecutionContext.load_from_checkpoint(checkpoint_path)
    print(f"\n✅ Checkpoint loaded successfully")
    loaded_context.print_summary()

    # Example: Validate checkpoint
    validation = validate_checkpoint_file(checkpoint_path)
    print(f"\n✅ Checkpoint validation: {'PASSED' if validation['valid'] else 'FAILED'}")
    if not validation['valid']:
        for issue in validation['issues']:
            print(f"   - {issue}")
