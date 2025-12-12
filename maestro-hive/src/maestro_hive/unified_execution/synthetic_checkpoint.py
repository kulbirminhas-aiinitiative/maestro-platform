#!/usr/bin/env python3
"""
Synthetic Checkpoint Builder - Generate TeamExecutionContext from External Data

This module provides the SyntheticCheckpointBuilder class that creates valid
TeamExecutionContext checkpoint files from external data sources such as:
- Design document summaries
- Requirements specifications
- Architecture decisions
- External system outputs

This enables:
- Bootstrapping workflow execution from external artifacts
- Integrating with existing documentation pipelines
- Creating test fixtures for checkpoint-based testing
- Migrating data from legacy systems

EPIC: MD-3162
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SyntheticPhase(str, Enum):
    """Standard SDLC phases for synthetic checkpoints"""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    REVIEW = "review"


@dataclass
class SyntheticPersonaResult:
    """Simplified persona result for synthetic checkpoints"""
    persona_id: str
    deliverables: List[str] = field(default_factory=list)
    success: bool = True
    quality_score: float = 0.85
    summary: str = ""


@dataclass
class SyntheticCheckpointConfig:
    """Configuration for synthetic checkpoint generation"""
    # Checkpoint versioning
    version: str = "1.0"

    # Default quality thresholds
    default_quality_score: float = 0.85
    quality_gate_threshold: float = 0.80

    # Execution mode
    execution_mode: str = "phased"
    workflow_type: str = "sdlc"

    # Phase configuration
    standard_phases: List[str] = field(default_factory=lambda: [
        "requirements", "design", "implementation", "testing", "deployment"
    ])


class SyntheticCheckpointBuilder:
    """
    Builder for creating valid TeamExecutionContext checkpoints from external data.

    This class enables creation of synthetic checkpoints that can be loaded by
    the execution framework, allowing integration of external artifacts (design
    docs, requirements, etc.) into the workflow execution pipeline.

    Usage:
        # Create checkpoint from design document
        builder = SyntheticCheckpointBuilder(
            external_data={
                "design_summary": "REST API with JWT auth",
                "components": ["auth_service", "api_gateway"],
                "decisions": {"database": "PostgreSQL"}
            },
            target_phase="design"
        )

        context = builder.build()
        builder.save("checkpoint_design.json")

    Attributes:
        external_data: Dictionary of external data to incorporate
        target_phase: The SDLC phase this checkpoint represents
        config: Configuration for checkpoint generation
    """

    def __init__(
        self,
        external_data: Dict[str, Any],
        target_phase: str,
        workflow_id: Optional[str] = None,
        config: Optional[SyntheticCheckpointConfig] = None
    ):
        """
        Initialize the SyntheticCheckpointBuilder.

        Args:
            external_data: Dictionary containing external data to incorporate
                          into the checkpoint (e.g., design doc summary,
                          requirements, architecture decisions)
            target_phase: Target SDLC phase (e.g., 'design', 'requirements')
            workflow_id: Optional workflow ID. Auto-generated if not provided.
            config: Optional configuration. Uses defaults if not provided.
        """
        self.external_data = external_data
        self.target_phase = target_phase.lower()
        self.workflow_id = workflow_id or self._generate_workflow_id()
        self.config = config or SyntheticCheckpointConfig()

        # Built context (populated by build())
        self._context: Optional[Dict[str, Any]] = None
        self._built_at: Optional[datetime] = None

    def _generate_workflow_id(self) -> str:
        """Generate a unique workflow ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"synthetic_{self.target_phase}_{timestamp}_{short_uuid}"

    def _get_phases_up_to_target(self) -> List[str]:
        """Get list of phases up to and including target phase"""
        phases = self.config.standard_phases

        if self.target_phase in phases:
            target_index = phases.index(self.target_phase)
            return phases[:target_index + 1]

        # If target phase is not in standard list, treat it as final
        return [self.target_phase]

    def _build_checkpoint_metadata(self) -> Dict[str, Any]:
        """Build the checkpoint_metadata section"""
        return {
            "version": self.config.version,
            "created_at": datetime.utcnow().isoformat(),
            "workflow_id": self.workflow_id,
            "phase_completed": self.target_phase,
            "awaiting_phase": self._get_next_phase(),
            "checkpoint_type": "phase_boundary",
            "awaiting_human_review": False,
            "human_edits_applied": False,
            "quality_gate_passed": True,
            "quality_score": self.config.default_quality_score,
            # Synthetic checkpoint metadata
            "synthetic": True,
            "synthetic_source": "external_data",
            "external_data_keys": list(self.external_data.keys())
        }

    def _get_next_phase(self) -> Optional[str]:
        """Get the phase that follows the target phase"""
        phases = self.config.standard_phases

        if self.target_phase in phases:
            target_index = phases.index(self.target_phase)
            if target_index + 1 < len(phases):
                return phases[target_index + 1]

        return None

    def _build_workflow_context(self) -> Dict[str, Any]:
        """Build the workflow_context section"""
        phases = self._get_phases_up_to_target()
        started_at = datetime.utcnow()

        # Build phase results for all phases up to target
        phase_results = {}
        for phase in phases:
            phase_results[phase] = self._build_phase_result(
                phase,
                is_target=(phase == self.target_phase)
            )

        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.config.workflow_type,
            "phase_results": phase_results,
            "phase_order": phases,
            "current_phase": self.target_phase,
            "shared_artifacts": self._build_shared_artifacts(phases),
            "shared_context": self._build_shared_context(),
            "contracts_validated": [],
            "metadata": {
                "initial_requirement": self.external_data.get("requirement", ""),
                "synthetic_checkpoint": True,
                "source_data_type": self._infer_source_type()
            },
            "started_at": started_at.isoformat(),
            "completed_at": None,
            "checkpoint_path": None,
            "last_checkpoint_at": None,
            "human_edits": {},
            "execution_mode": self.config.execution_mode,
            "awaiting_human_review": False
        }

    def _build_phase_result(
        self,
        phase: str,
        is_target: bool = False
    ) -> Dict[str, Any]:
        """Build a phase result entry"""
        now = datetime.utcnow()

        # Extract phase-specific data from external_data
        phase_outputs = self._extract_phase_outputs(phase)

        return {
            "phase_name": phase,
            "status": "completed",
            "outputs": phase_outputs,
            "context_received": {},
            "context_passed": phase_outputs if not is_target else {},
            "contracts_validated": [],
            "validation_results": [],
            "artifacts_created": self._infer_artifacts(phase),
            "artifacts_consumed": [],
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "agent_assignments": {},
            "error_message": None,
            "error_details": None
        }

    def _extract_phase_outputs(self, phase: str) -> Dict[str, Any]:
        """Extract outputs relevant to a specific phase from external data"""
        outputs = {}

        # Map external data keys to phases
        phase_key_mappings = {
            "requirements": [
                "requirement", "requirements", "user_stories",
                "acceptance_criteria", "functional_requirements",
                "non_functional_requirements"
            ],
            "design": [
                "design_summary", "design", "architecture", "components",
                "decisions", "api_design", "schema", "database_design",
                "system_design", "technical_design"
            ],
            "implementation": [
                "implementation", "code", "modules", "services",
                "endpoints", "functions", "classes"
            ],
            "testing": [
                "test_plan", "test_cases", "testing", "test_strategy",
                "coverage", "test_results"
            ],
            "deployment": [
                "deployment", "infrastructure", "ci_cd", "environments",
                "configuration", "deployment_plan"
            ]
        }

        relevant_keys = phase_key_mappings.get(phase, [])

        for key in relevant_keys:
            if key in self.external_data:
                outputs[key] = self.external_data[key]

        # If this is the target phase, include all external data
        if phase == self.target_phase:
            outputs["external_data"] = self.external_data
            outputs["synthetic_source"] = True

        return outputs

    def _build_shared_artifacts(self, phases: List[str]) -> List[Dict[str, Any]]:
        """Build shared artifacts list based on completed phases"""
        artifacts = []

        for phase in phases:
            phase_artifacts = self._infer_artifacts(phase)
            for artifact in phase_artifacts:
                artifacts.append({
                    "name": artifact,
                    "created_by_phase": phase,
                    "created_at": datetime.utcnow().isoformat()
                })

        return artifacts

    def _infer_artifacts(self, phase: str) -> List[str]:
        """Infer artifact names based on phase and external data"""
        artifact_templates = {
            "requirements": [
                "requirements_document",
                "user_stories",
                "acceptance_criteria"
            ],
            "design": [
                "system_design_document",
                "api_specification",
                "database_schema",
                "architecture_diagram"
            ],
            "implementation": [
                "source_code",
                "api_implementation",
                "database_migrations"
            ],
            "testing": [
                "test_suite",
                "test_results",
                "coverage_report"
            ],
            "deployment": [
                "deployment_manifest",
                "infrastructure_config",
                "release_notes"
            ]
        }

        base_artifacts = artifact_templates.get(phase, [f"{phase}_output"])

        # Add custom artifacts based on external data
        if phase == self.target_phase:
            if "components" in self.external_data:
                for component in self.external_data["components"]:
                    base_artifacts.append(f"{component}_spec")

        return base_artifacts

    def _build_shared_context(self) -> Dict[str, Any]:
        """Build shared context from external data"""
        context = {
            "synthetic_checkpoint": True,
            "created_from": "external_data",
            "target_phase": self.target_phase
        }

        # Include key external data in shared context
        key_fields = ["project_name", "project_type", "technology_stack", "team"]
        for field in key_fields:
            if field in self.external_data:
                context[field] = self.external_data[field]

        return context

    def _infer_source_type(self) -> str:
        """Infer the type of source data based on keys present"""
        key_indicators = {
            "design_summary": "design_document",
            "api_design": "api_specification",
            "requirements": "requirements_document",
            "architecture": "architecture_document",
            "user_stories": "agile_backlog",
            "schema": "database_design"
        }

        for key, source_type in key_indicators.items():
            if key in self.external_data:
                return source_type

        return "generic_external_data"

    def _build_team_execution_state(self) -> Dict[str, Any]:
        """Build the team_execution_state section"""
        phases = self._get_phases_up_to_target()

        # Build persona results per phase
        persona_results = {}
        for phase in phases:
            persona_results[phase] = self._build_phase_persona_results(phase)

        return {
            "classification": self._build_classification(),
            "blueprint_selections": {},
            "contract_specs": [],
            "persona_results": persona_results,
            "quality_metrics": self._build_quality_metrics(phases),
            "timing_metrics": self._build_timing_metrics(phases),
            # RAG-related fields (empty for synthetic)
            "template_package_id": None,
            "template_package_name": None,
            "template_package_confidence": 0.0,
            "template_package_explanation": "",
            "recommended_templates": {},
            "templates_used": {},
            "template_selection_reasoning": {},
            "custom_development_reasons": {}
        }

    def _build_classification(self) -> Optional[Dict[str, Any]]:
        """Build requirement classification from external data"""
        # Only build if we have requirement data
        if "requirement" not in self.external_data and "requirements" not in self.external_data:
            return None

        requirement_text = self.external_data.get(
            "requirement",
            self.external_data.get("requirements", "")
        )

        # Infer complexity from external data
        complexity = self._infer_complexity()

        return {
            "requirement_type": self.external_data.get("requirement_type", "feature_development"),
            "complexity": complexity,
            "parallelizability": "partially_parallel",
            "required_expertise": self._infer_expertise(),
            "estimated_effort_hours": self.external_data.get("estimated_hours", 40.0),
            "dependencies": self.external_data.get("dependencies", []),
            "risks": self.external_data.get("risks", []),
            "rationale": f"Synthetic classification from external data ({self._infer_source_type()})",
            "confidence_score": 0.75  # Lower confidence for synthetic
        }

    def _infer_complexity(self) -> str:
        """Infer complexity from external data"""
        # Check for explicit complexity
        if "complexity" in self.external_data:
            return self.external_data["complexity"]

        # Infer from component count
        components = self.external_data.get("components", [])
        if len(components) > 5:
            return "complex"
        elif len(components) > 2:
            return "moderate"

        return "simple"

    def _infer_expertise(self) -> List[str]:
        """Infer required expertise from external data"""
        expertise = set()

        # Check technology stack
        tech_stack = self.external_data.get("technology_stack", [])
        if isinstance(tech_stack, list):
            for tech in tech_stack:
                tech_lower = tech.lower()
                if any(x in tech_lower for x in ["python", "django", "flask", "fastapi"]):
                    expertise.add("python")
                if any(x in tech_lower for x in ["react", "vue", "angular", "javascript"]):
                    expertise.add("frontend")
                if any(x in tech_lower for x in ["postgres", "mysql", "mongodb", "database"]):
                    expertise.add("database")
                if any(x in tech_lower for x in ["docker", "kubernetes", "aws", "cloud"]):
                    expertise.add("devops")

        # Check design indicators
        if "api_design" in self.external_data or "api" in str(self.external_data).lower():
            expertise.add("api_development")

        if "auth" in str(self.external_data).lower():
            expertise.add("security")

        return list(expertise) if expertise else ["backend"]

    def _build_phase_persona_results(self, phase: str) -> Dict[str, Dict[str, Any]]:
        """Build persona results for a phase"""
        # Map phases to typical personas
        phase_personas = {
            "requirements": ["requirement_analyst"],
            "design": ["solution_architect", "backend_developer"],
            "implementation": ["backend_developer", "frontend_developer"],
            "testing": ["qa_engineer"],
            "deployment": ["devops_engineer"]
        }

        personas = phase_personas.get(phase, ["backend_developer"])
        results = {}

        for persona_id in personas:
            results[persona_id] = {
                "persona_id": persona_id,
                "contract_id": f"synthetic_{phase}_{persona_id}",
                "success": True,
                "files_created": [],
                "deliverables": self._infer_artifacts(phase),
                "contract_fulfilled": True,
                "fulfillment_score": self.config.default_quality_score,
                "quality_score": self.config.default_quality_score,
                "completeness_score": self.config.default_quality_score,
                "duration_seconds": 0.0
            }

        return results

    def _build_quality_metrics(self, phases: List[str]) -> Dict[str, Dict[str, Any]]:
        """Build quality metrics for all phases"""
        metrics = {}

        for phase in phases:
            metrics[phase] = {
                "overall_quality": self.config.default_quality_score,
                "completeness": self.config.default_quality_score,
                "consistency": self.config.default_quality_score,
                "synthetic": True
            }

        return metrics

    def _build_timing_metrics(self, phases: List[str]) -> Dict[str, Dict[str, Any]]:
        """Build timing metrics for all phases"""
        metrics = {}

        for phase in phases:
            metrics[phase] = {
                "phase_duration": 0.0,
                "synthetic": True
            }

        return metrics

    def build(self) -> Dict[str, Any]:
        """
        Build the complete TeamExecutionContext checkpoint.

        Returns:
            Dictionary representing a valid TeamExecutionContext that can be
            serialized to JSON and loaded by TeamExecutionContext.load_from_checkpoint()

        Raises:
            ValueError: If external_data is empty or target_phase is invalid
        """
        if not self.external_data:
            raise ValueError("external_data cannot be empty")

        if not self.target_phase:
            raise ValueError("target_phase cannot be empty")

        self._built_at = datetime.utcnow()

        self._context = {
            "checkpoint_metadata": self._build_checkpoint_metadata(),
            "workflow_context": self._build_workflow_context(),
            "team_execution_state": self._build_team_execution_state()
        }

        return self._context

    def get_context(self) -> Dict[str, Any]:
        """
        Get the built context.

        Returns:
            The built TeamExecutionContext dictionary

        Raises:
            RuntimeError: If build() hasn't been called yet
        """
        if self._context is None:
            raise RuntimeError("Context not built. Call build() first.")
        return self._context

    def save(
        self,
        output_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Save the checkpoint to a JSON file.

        Args:
            output_path: Full path for the output file. If not provided,
                        generates filename from target_phase.
            output_dir: Directory to save to. Defaults to current directory.

        Returns:
            Path to the saved checkpoint file

        Raises:
            RuntimeError: If build() hasn't been called yet
        """
        if self._context is None:
            self.build()

        # Determine output path
        if output_path:
            filepath = Path(output_path)
        else:
            filename = f"checkpoint_{self.target_phase}.json"
            if output_dir:
                filepath = Path(output_dir) / filename
            else:
                filepath = Path(filename)

        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Update checkpoint metadata with save path
        self._context["checkpoint_metadata"]["checkpoint_path"] = str(filepath)
        self._context["workflow_context"]["checkpoint_path"] = str(filepath)
        self._context["workflow_context"]["last_checkpoint_at"] = datetime.utcnow().isoformat()

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(self._context, f, indent=2)

        return str(filepath)

    def validate(self) -> Dict[str, Any]:
        """
        Validate the built checkpoint against TeamExecutionContext requirements.

        Returns:
            Validation result with 'valid' boolean and list of 'issues'

        Raises:
            RuntimeError: If build() hasn't been called yet
        """
        if self._context is None:
            raise RuntimeError("Context not built. Call build() first.")

        issues = []

        # Check required top-level keys
        required_keys = ["checkpoint_metadata", "workflow_context", "team_execution_state"]
        for key in required_keys:
            if key not in self._context:
                issues.append(f"Missing required key: {key}")

        # Validate checkpoint_metadata
        metadata = self._context.get("checkpoint_metadata", {})
        if not metadata.get("version"):
            issues.append("Missing version in checkpoint_metadata")
        if not metadata.get("workflow_id"):
            issues.append("Missing workflow_id in checkpoint_metadata")

        # Validate workflow_context
        workflow = self._context.get("workflow_context", {})
        if not workflow.get("workflow_id"):
            issues.append("Missing workflow_id in workflow_context")
        if not isinstance(workflow.get("phase_results"), dict):
            issues.append("Invalid phase_results in workflow_context")

        # Validate team_execution_state
        state = self._context.get("team_execution_state", {})
        if not isinstance(state.get("persona_results"), dict):
            issues.append("Invalid persona_results in team_execution_state")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "workflow_id": self.workflow_id,
            "target_phase": self.target_phase,
            "phases_included": len(self._context.get("workflow_context", {}).get("phase_results", {}))
        }

    def __repr__(self) -> str:
        built_status = "built" if self._context else "not built"
        return (
            f"SyntheticCheckpointBuilder("
            f"workflow_id='{self.workflow_id}', "
            f"target_phase='{self.target_phase}', "
            f"status='{built_status}')"
        )


def create_synthetic_checkpoint(
    external_data: Dict[str, Any],
    target_phase: str,
    output_path: Optional[str] = None,
    workflow_id: Optional[str] = None
) -> str:
    """
    Convenience function to create and save a synthetic checkpoint.

    Args:
        external_data: Dictionary of external data
        target_phase: Target SDLC phase
        output_path: Optional output file path
        workflow_id: Optional workflow ID

    Returns:
        Path to the saved checkpoint file

    Example:
        path = create_synthetic_checkpoint(
            external_data={"design_summary": "REST API design"},
            target_phase="design",
            output_path="./checkpoints/design.json"
        )
    """
    builder = SyntheticCheckpointBuilder(
        external_data=external_data,
        target_phase=target_phase,
        workflow_id=workflow_id
    )

    builder.build()
    return builder.save(output_path=output_path)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Create checkpoint from design document summary
    design_data = {
        "requirement": "Build a secure REST API for user management",
        "design_summary": "Microservices architecture with JWT authentication",
        "components": ["auth_service", "user_service", "api_gateway"],
        "decisions": {
            "database": "PostgreSQL",
            "cache": "Redis",
            "auth": "JWT with refresh tokens"
        },
        "api_design": {
            "endpoints": [
                "POST /auth/login",
                "POST /auth/refresh",
                "GET /users",
                "POST /users",
                "GET /users/{id}"
            ]
        },
        "technology_stack": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"]
    }

    # Create builder
    builder = SyntheticCheckpointBuilder(
        external_data=design_data,
        target_phase="design"
    )

    # Build context
    context = builder.build()

    # Validate
    validation = builder.validate()
    print(f"Validation: {'PASSED' if validation['valid'] else 'FAILED'}")
    if not validation['valid']:
        for issue in validation['issues']:
            print(f"  - {issue}")

    # Save checkpoint
    checkpoint_path = builder.save(output_dir="/tmp")
    print(f"\nCheckpoint saved to: {checkpoint_path}")

    # Print summary
    print(f"\nBuilder: {builder}")
    print(f"Workflow ID: {builder.workflow_id}")
    print(f"Target Phase: {builder.target_phase}")
    print(f"Phases Included: {validation['phases_included']}")
