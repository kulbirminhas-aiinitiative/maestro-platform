"""
ACC Integration Service (MD-895)

Connects ACC validation with team_execution_v2.py.
Checks generated code for architectural conformance.

Features:
- Analyze generated code dependencies
- Apply architectural rules from manifest
- Report violations with severity
- Block deployment for critical violations

ML Integration Points:
- Violation pattern recognition
- Architecture health prediction
"""

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from acc.rule_engine import RuleEngine, Rule, Violation, EvaluationResult, Component, Severity, RuleType
from acc.import_graph_builder import ImportGraphBuilder

logger = logging.getLogger(__name__)


@dataclass
class ArchitecturalViolationSummary:
    """Summary of architectural violations"""
    total: int
    blocking: int
    warning: int
    info: int
    by_type: Dict[str, int]
    by_component: Dict[str, int]

    @property
    def has_blocking(self) -> bool:
        return self.blocking > 0


@dataclass
class ACCValidationResult:
    """Result of ACC validation for an execution"""
    execution_id: str
    project_path: str
    files_analyzed: int
    components_checked: int
    rules_evaluated: int
    violations: ArchitecturalViolationSummary
    is_compliant: bool
    conformance_score: float
    detailed_violations: List[Dict[str, Any]]
    coupling_metrics: Dict[str, Dict[str, float]]
    cycles_detected: List[List[str]]
    validated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'project_path': self.project_path,
            'files_analyzed': self.files_analyzed,
            'components_checked': self.components_checked,
            'rules_evaluated': self.rules_evaluated,
            'violations': {
                'total': self.violations.total,
                'blocking': self.violations.blocking,
                'warning': self.violations.warning,
                'info': self.violations.info,
                'by_type': self.violations.by_type,
                'by_component': self.violations.by_component
            },
            'is_compliant': self.is_compliant,
            'conformance_score': round(self.conformance_score, 4),
            'detailed_violations': self.detailed_violations,
            'coupling_metrics': self.coupling_metrics,
            'cycles_detected': self.cycles_detected,
            'validated_at': self.validated_at.isoformat()
        }


class ACCIntegrationService:
    """
    ACC Integration Service

    Connects architectural conformance checking with the execution pipeline.
    """

    def __init__(
        self,
        manifests_path: str = "manifests/architectural/",
        default_components: Optional[List[Component]] = None
    ):
        """
        Initialize ACC integration service.

        Args:
            manifests_path: Path to architectural manifests
            default_components: Default component definitions
        """
        self.manifests_path = Path(manifests_path)
        self.manifests_path.mkdir(parents=True, exist_ok=True)

        # Initialize rule engine with default components
        if default_components is None:
            default_components = self._get_default_components()

        self.rule_engine = RuleEngine(components=default_components)

        # Load any existing rules
        self._load_default_rules()

        # Results storage
        self._validation_results: List[ACCValidationResult] = []

        logger.info("✅ ACCIntegrationService initialized")

    def _get_default_components(self) -> List[Component]:
        """Get default architectural components."""
        return [
            Component(
                name="Presentation",
                paths=["routes/", "api/", "controllers/", "views/"],
                description="API routes and controllers"
            ),
            Component(
                name="BusinessLogic",
                paths=["services/", "domain/", "core/"],
                description="Business logic and domain services"
            ),
            Component(
                name="DataAccess",
                paths=["repositories/", "models/", "database/", "dal/"],
                description="Data access and persistence"
            ),
            Component(
                name="Infrastructure",
                paths=["utils/", "helpers/", "config/", "common/"],
                description="Cross-cutting infrastructure"
            ),
            Component(
                name="Tests",
                paths=["tests/", "test_", "_test.py"],
                description="Test files"
            )
        ]

    def _load_default_rules(self):
        """Load default architectural rules."""
        default_rules = [
            # Layering rules
            Rule(
                id="layer_presentation_business",
                rule_type=RuleType.CAN_CALL,
                severity=Severity.BLOCKING,
                description="Presentation can only call BusinessLogic",
                component="Presentation",
                target="BusinessLogic"
            ),
            Rule(
                id="layer_business_data",
                rule_type=RuleType.CAN_CALL,
                severity=Severity.WARNING,
                description="BusinessLogic should primarily call DataAccess",
                component="BusinessLogic",
                target="DataAccess"
            ),
            Rule(
                id="layer_no_data_to_presentation",
                rule_type=RuleType.MUST_NOT_CALL,
                severity=Severity.BLOCKING,
                description="DataAccess must not call Presentation",
                component="DataAccess",
                target="Presentation"
            ),

            # Coupling rules
            Rule(
                id="coupling_business_logic",
                rule_type=RuleType.COUPLING,
                severity=Severity.WARNING,
                description="BusinessLogic coupling should be reasonable",
                component="BusinessLogic",
                threshold=10
            ),

            # Cycle rules
            Rule(
                id="no_cycles_business",
                rule_type=RuleType.NO_CYCLES,
                severity=Severity.WARNING,
                description="No circular dependencies in BusinessLogic",
                component="BusinessLogic"
            )
        ]

        self.rule_engine.add_rules(default_rules)

    def validate_architecture(
        self,
        execution_id: str,
        project_path: str,
        custom_rules: Optional[List[Rule]] = None
    ) -> ACCValidationResult:
        """
        Validate project architecture.

        Args:
            execution_id: Execution identifier
            project_path: Path to project to analyze
            custom_rules: Optional custom rules to apply

        Returns:
            ACCValidationResult with analysis outcomes
        """
        logger.info(f"🏗️ Analyzing architecture for {project_path}")

        project_path = Path(project_path)

        # Add custom rules if provided
        if custom_rules:
            self.rule_engine.add_rules(custom_rules)

        # Build import graph
        graph_builder = ImportGraphBuilder(str(project_path))
        dependencies = graph_builder.build_graph()

        # Calculate coupling metrics
        coupling_metrics = self._calculate_coupling_metrics(dependencies)

        # Detect cycles
        cycles = self._detect_cycles(dependencies)

        # Evaluate rules
        eval_result = self.rule_engine.evaluate_all(
            dependencies=dependencies,
            coupling_metrics=coupling_metrics,
            cycles=cycles
        )

        # Summarize violations
        violation_summary = self._summarize_violations(eval_result.violations)

        # Calculate conformance score
        conformance_score = self._calculate_conformance_score(
            eval_result,
            len(dependencies)
        )

        # Determine compliance
        is_compliant = not violation_summary.has_blocking

        result = ACCValidationResult(
            execution_id=execution_id,
            project_path=str(project_path),
            files_analyzed=eval_result.files_analyzed,
            components_checked=eval_result.components_checked,
            rules_evaluated=eval_result.rules_evaluated,
            violations=violation_summary,
            is_compliant=is_compliant,
            conformance_score=conformance_score,
            detailed_violations=[v.to_dict() for v in eval_result.violations],
            coupling_metrics=self._format_coupling_metrics(coupling_metrics),
            cycles_detected=cycles
        )

        # Store result
        self._validation_results.append(result)

        # Save to file
        self._save_validation_result(result)

        logger.info(f"✅ ACC validation complete: {'COMPLIANT' if is_compliant else 'NON-COMPLIANT'}, "
                   f"score: {conformance_score:.2f}, "
                   f"violations: {violation_summary.total} ({violation_summary.blocking} blocking)")

        return result

    def _calculate_coupling_metrics(
        self,
        dependencies: Dict[str, List[str]]
    ) -> Dict[str, tuple]:
        """
        Calculate coupling metrics for each file.

        Returns:
            Dict of file -> (Ca, Ce, Instability)
        """
        # Calculate afferent coupling (Ca) - who depends on me
        afferent = {f: 0 for f in dependencies}
        for source, deps in dependencies.items():
            for dep in deps:
                if dep in afferent:
                    afferent[dep] += 1

        # Calculate efferent coupling (Ce) - what I depend on
        efferent = {f: len(deps) for f, deps in dependencies.items()}

        # Calculate instability
        metrics = {}
        for f in dependencies:
            ca = afferent.get(f, 0)
            ce = efferent.get(f, 0)
            total = ca + ce
            instability = ce / total if total > 0 else 0.0
            metrics[f] = (ca, ce, instability)

        return metrics

    def _detect_cycles(self, dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """
        Detect cyclic dependencies.

        Returns:
            List of cycles (each cycle is a list of files)
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, []):
                dfs(neighbor, path.copy())

            rec_stack.remove(node)

        for node in dependencies:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _summarize_violations(
        self,
        violations: List[Violation]
    ) -> ArchitecturalViolationSummary:
        """Summarize violations by type and severity."""
        by_type: Dict[str, int] = {}
        by_component: Dict[str, int] = {}
        blocking = 0
        warning = 0
        info = 0

        for v in violations:
            # Count by severity
            if v.severity == Severity.BLOCKING:
                blocking += 1
            elif v.severity == Severity.WARNING:
                warning += 1
            else:
                info += 1

            # Count by type
            type_name = v.rule_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

            # Count by component
            by_component[v.source_component] = by_component.get(v.source_component, 0) + 1

        return ArchitecturalViolationSummary(
            total=len(violations),
            blocking=blocking,
            warning=warning,
            info=info,
            by_type=by_type,
            by_component=by_component
        )

    def _calculate_conformance_score(
        self,
        eval_result: EvaluationResult,
        total_files: int
    ) -> float:
        """
        Calculate architectural conformance score.

        Returns:
            Score from 0.0 to 1.0
        """
        if total_files == 0:
            return 1.0

        # Penalty factors
        blocking_penalty = 0.3  # Per blocking violation
        warning_penalty = 0.1   # Per warning violation
        info_penalty = 0.02     # Per info violation

        # Calculate penalties
        blocking_count = len(eval_result.blocking_violations)
        warning_count = len(eval_result.warning_violations)
        info_count = len(eval_result.info_violations)

        total_penalty = (
            blocking_count * blocking_penalty +
            warning_count * warning_penalty +
            info_count * info_penalty
        )

        # Cap penalty at 1.0
        score = max(0.0, 1.0 - total_penalty)

        return score

    def _format_coupling_metrics(
        self,
        metrics: Dict[str, tuple]
    ) -> Dict[str, Dict[str, float]]:
        """Format coupling metrics for output."""
        return {
            file_path: {
                'afferent_coupling': ca,
                'efferent_coupling': ce,
                'instability': round(instability, 4)
            }
            for file_path, (ca, ce, instability) in metrics.items()
        }

    def _save_validation_result(self, result: ACCValidationResult):
        """Save validation result to file."""
        output_dir = Path(f"reports/acc/{result.execution_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "validation_result.json"
        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        logger.debug(f"Saved ACC validation result to {output_file}")

    def get_validation_metrics(
        self,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get validation metrics for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Metrics dictionary or None
        """
        for result in reversed(self._validation_results):
            if result.execution_id == execution_id:
                return {
                    'acc_conformance_score': result.conformance_score,
                    'is_compliant': result.is_compliant,
                    'blocking_violations': result.violations.blocking,
                    'warning_violations': result.violations.warning,
                    'total_violations': result.violations.total,
                    'files_analyzed': result.files_analyzed,
                    'cycles_detected': len(result.cycles_detected)
                }

        return None

    def calculate_quality_score_contribution(
        self,
        result: ACCValidationResult
    ) -> float:
        """
        Calculate ACC contribution to overall quality score.

        Args:
            result: ACC validation result

        Returns:
            Quality score contribution (0.0 to 1.0)
        """
        # Base on conformance score with compliance bonus
        score = result.conformance_score

        # Bonus for full compliance
        if result.is_compliant:
            score = min(1.0, score + 0.1)

        return score

    def load_manifest(self, manifest_path: str) -> int:
        """
        Load architectural rules from manifest file.

        Args:
            manifest_path: Path to YAML manifest

        Returns:
            Number of rules loaded
        """
        return self.rule_engine.load_rules_from_yaml(Path(manifest_path))

    def add_custom_component(self, component: Component):
        """Add a custom component definition."""
        self.rule_engine.components.append(component)

    def get_ml_training_data(self) -> List[Dict[str, Any]]:
        """
        Get validation data formatted for ML training.

        Returns:
            List of feature dictionaries for ML
        """
        training_data = []

        for result in self._validation_results:
            training_data.append({
                'execution_id': result.execution_id,
                'files_analyzed': result.files_analyzed,
                'components_checked': result.components_checked,
                'total_violations': result.violations.total,
                'blocking_violations': result.violations.blocking,
                'warning_violations': result.violations.warning,
                'is_compliant': 1 if result.is_compliant else 0,
                'conformance_score': result.conformance_score,
                'cycles_count': len(result.cycles_detected),
                'timestamp': result.validated_at.isoformat()
            })

        return training_data


# Global instance
_acc_service: Optional[ACCIntegrationService] = None


def get_acc_integration_service() -> ACCIntegrationService:
    """Get or create global ACC integration service instance."""
    global _acc_service
    if _acc_service is None:
        _acc_service = ACCIntegrationService()
    return _acc_service


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize service
    service = get_acc_integration_service()

    # Validate a project
    result = service.validate_architecture(
        execution_id="exec-001",
        project_path="./generated/test-project"
    )

    print("\n=== ACC Validation Result ===")
    print(f"Files Analyzed: {result.files_analyzed}")
    print(f"Components: {result.components_checked}")
    print(f"Compliant: {'YES' if result.is_compliant else 'NO'}")
    print(f"Score: {result.conformance_score:.2f}")
    print(f"\nViolations:")
    print(f"  Blocking: {result.violations.blocking}")
    print(f"  Warning: {result.violations.warning}")
    print(f"  Info: {result.violations.info}")
    print(f"\nCycles Detected: {len(result.cycles_detected)}")
    print(f"\nQuality Contribution: {service.calculate_quality_score_contribution(result):.2f}")
