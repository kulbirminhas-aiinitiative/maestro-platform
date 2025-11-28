#!/usr/bin/env python3
"""
Workflow Gap Detection System
Identifies specific gaps in workflow outputs and generates actionable fix instructions
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set
from enum import Enum

from workflow_validation import (
    WorkflowValidator,
    ValidationSeverity,
    PhaseValidationReport
)


class GapType(Enum):
    """Types of gaps detected in workflow outputs"""
    MISSING_DIRECTORY = "missing_directory"
    MISSING_FILE = "missing_file"
    INSUFFICIENT_FILES = "insufficient_files"
    BROKEN_IMPORT = "broken_import"
    MISSING_DEPENDENCY = "missing_dependency"
    INVALID_REFERENCE = "invalid_reference"
    INCOMPLETE_IMPLEMENTATION = "incomplete_implementation"
    CONFIGURATION_ERROR = "configuration_error"


@dataclass
class Gap:
    """Represents a specific gap in the workflow output"""
    gap_type: GapType
    severity: ValidationSeverity
    phase: str
    description: str
    location: str
    expected: str
    actual: str
    fix_suggestion: str
    affected_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Other gaps that must be fixed first

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "gap_type": self.gap_type.value,
            "severity": self.severity.value,
            "phase": self.phase,
            "description": self.description,
            "location": self.location,
            "expected": self.expected,
            "actual": self.actual,
            "fix_suggestion": self.fix_suggestion,
            "affected_files": self.affected_files,
            "dependencies": self.dependencies
        }


@dataclass
class ImplementationGap:
    """Detailed gap information for implementation phase"""
    component_type: str  # e.g., "backend_routes", "frontend_components"
    component_name: str  # e.g., "RecipeService", "LoginComponent"
    expected_file_path: str
    referenced_in: List[str] = field(default_factory=list)
    required_for: List[str] = field(default_factory=list)  # What depends on this
    design_doc_reference: Optional[str] = None
    priority: int = 1  # 1=highest, 5=lowest

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GapAnalysisReport:
    """Complete gap analysis for a workflow"""
    workflow_id: str
    workflow_dir: Path
    total_gaps: int
    critical_gaps: int
    high_priority_gaps: int
    medium_priority_gaps: int
    low_priority_gaps: int
    gaps_by_phase: Dict[str, List[Gap]]
    implementation_gaps: List[ImplementationGap]
    deployment_blockers: List[Gap]
    estimated_completion_percentage: float
    is_deployable: bool
    recovery_priority: int  # 1=fix first, lower=fix later

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "workflow_id": self.workflow_id,
            "workflow_dir": str(self.workflow_dir),
            "total_gaps": self.total_gaps,
            "critical_gaps": self.critical_gaps,
            "high_priority_gaps": self.high_priority_gaps,
            "medium_priority_gaps": self.medium_priority_gaps,
            "low_priority_gaps": self.low_priority_gaps,
            "gaps_by_phase": {
                phase: [gap.to_dict() for gap in gaps]
                for phase, gaps in self.gaps_by_phase.items()
            },
            "implementation_gaps": [gap.to_dict() for gap in self.implementation_gaps],
            "deployment_blockers": [gap.to_dict() for gap in self.deployment_blockers],
            "estimated_completion_percentage": self.estimated_completion_percentage,
            "is_deployable": self.is_deployable,
            "recovery_priority": self.recovery_priority
        }


class WorkflowGapDetector:
    """Detects gaps in workflow outputs using validation framework"""

    def __init__(self, workflow_dir: Path):
        """
        Initialize gap detector

        Args:
            workflow_dir: Path to workflow output directory
        """
        self.workflow_dir = Path(workflow_dir)
        self.workflow_id = self.workflow_dir.name
        self.validator = WorkflowValidator(workflow_dir)

    def detect_gaps(self) -> GapAnalysisReport:
        """
        Detect all gaps in workflow output

        Returns:
            GapAnalysisReport with all detected gaps
        """
        # Run validation to get failures
        validation_reports = self.validator.validate_all()

        # Convert validation failures to gaps
        gaps_by_phase = {}
        all_gaps = []

        for phase, report in validation_reports.items():
            phase_gaps = self._convert_validation_to_gaps(phase, report)
            gaps_by_phase[phase] = phase_gaps
            all_gaps.extend(phase_gaps)

        # Analyze implementation gaps in detail
        implementation_gaps = self._analyze_implementation_gaps()

        # Identify deployment blockers
        deployment_blockers = [
            gap for gap in all_gaps
            if gap.severity == ValidationSeverity.CRITICAL
        ]

        # Calculate metrics
        critical_count = sum(1 for g in all_gaps if g.severity == ValidationSeverity.CRITICAL)
        high_count = sum(1 for g in all_gaps if g.severity == ValidationSeverity.HIGH)
        medium_count = sum(1 for g in all_gaps if g.severity == ValidationSeverity.MEDIUM)
        low_count = sum(1 for g in all_gaps if g.severity == ValidationSeverity.LOW)

        # Estimate completion percentage
        completion_pct = self._estimate_completion_percentage(gaps_by_phase, implementation_gaps)

        # Determine deployment readiness
        is_deployable = critical_count == 0 and high_count == 0

        # Calculate recovery priority (1-5, 1=highest)
        recovery_priority = self._calculate_recovery_priority(
            critical_count, high_count, completion_pct
        )

        return GapAnalysisReport(
            workflow_id=self.workflow_id,
            workflow_dir=self.workflow_dir,
            total_gaps=len(all_gaps),
            critical_gaps=critical_count,
            high_priority_gaps=high_count,
            medium_priority_gaps=medium_count,
            low_priority_gaps=low_count,
            gaps_by_phase=gaps_by_phase,
            implementation_gaps=implementation_gaps,
            deployment_blockers=deployment_blockers,
            estimated_completion_percentage=completion_pct,
            is_deployable=is_deployable,
            recovery_priority=recovery_priority
        )

    def _convert_validation_to_gaps(
        self, phase: str, report: PhaseValidationReport
    ) -> List[Gap]:
        """Convert validation failures to gap objects"""
        gaps = []

        for result in report.results:
            if not result.passed:
                gap = Gap(
                    gap_type=self._infer_gap_type(result.check_name),
                    severity=result.severity,
                    phase=phase,
                    description=result.message,
                    location=str(self.workflow_dir / phase),
                    expected=result.details.get("expected", "N/A"),
                    actual=result.details.get("actual", "N/A"),
                    fix_suggestion=result.fix_suggestion or "No suggestion available",
                    affected_files=result.details.get("affected_files", [])
                )
                gaps.append(gap)

        return gaps

    def _infer_gap_type(self, check_name: str) -> GapType:
        """Infer gap type from validation check name"""
        check_lower = check_name.lower()

        if "directory" in check_lower and "exists" in check_lower:
            return GapType.MISSING_DIRECTORY
        elif "file" in check_lower and "exists" in check_lower:
            return GapType.MISSING_FILE
        elif "minimum" in check_lower or "count" in check_lower:
            return GapType.INSUFFICIENT_FILES
        elif "import" in check_lower:
            return GapType.BROKEN_IMPORT
        elif "dependency" in check_lower or "package.json" in check_lower:
            return GapType.MISSING_DEPENDENCY
        elif "reference" in check_lower or "dockerfile" in check_lower:
            return GapType.INVALID_REFERENCE
        else:
            return GapType.INCOMPLETE_IMPLEMENTATION

    def _analyze_implementation_gaps(self) -> List[ImplementationGap]:
        """Analyze implementation phase in detail to identify missing components"""
        impl_gaps = []
        impl_dir = self.workflow_dir / "implementation"

        if not impl_dir.exists():
            return impl_gaps

        # Analyze backend gaps
        backend_gaps = self._analyze_backend_gaps(impl_dir / "backend")
        impl_gaps.extend(backend_gaps)

        # Analyze frontend gaps
        frontend_gaps = self._analyze_frontend_gaps(impl_dir / "frontend")
        impl_gaps.extend(frontend_gaps)

        return impl_gaps

    def _analyze_backend_gaps(self, backend_dir: Path) -> List[ImplementationGap]:
        """Analyze missing backend components"""
        gaps = []

        if not backend_dir.exists():
            gaps.append(ImplementationGap(
                component_type="backend_structure",
                component_name="backend",
                expected_file_path=str(backend_dir),
                priority=1
            ))
            return gaps

        src_dir = backend_dir / "src"
        if not src_dir.exists():
            return gaps

        # Check for server.ts to find expected imports
        server_file = src_dir / "server.ts"
        if server_file.exists():
            expected_routes = self._extract_expected_routes(server_file)
            for route_name in expected_routes:
                route_file = src_dir / "routes" / f"{route_name}.routes.ts"
                if not route_file.exists():
                    gaps.append(ImplementationGap(
                        component_type="backend_routes",
                        component_name=f"{route_name}Routes",
                        expected_file_path=str(route_file),
                        referenced_in=[str(server_file)],
                        priority=1
                    ))

        # Check for missing services (based on common patterns)
        services_dir = src_dir / "services"
        if not services_dir.exists():
            gaps.append(ImplementationGap(
                component_type="backend_structure",
                component_name="services",
                expected_file_path=str(services_dir),
                priority=1
            ))

        # Check for missing controllers
        controllers_dir = src_dir / "controllers"
        if not controllers_dir.exists():
            gaps.append(ImplementationGap(
                component_type="backend_structure",
                component_name="controllers",
                expected_file_path=str(controllers_dir),
                priority=1
            ))

        # Check for missing middleware
        middleware_dir = src_dir / "middleware"
        if not middleware_dir.exists():
            gaps.append(ImplementationGap(
                component_type="backend_structure",
                component_name="middleware",
                expected_file_path=str(middleware_dir),
                priority=2
            ))

        return gaps

    def _analyze_frontend_gaps(self, frontend_dir: Path) -> List[ImplementationGap]:
        """Analyze missing frontend components"""
        gaps = []

        if not frontend_dir.exists():
            gaps.append(ImplementationGap(
                component_type="frontend_structure",
                component_name="frontend",
                expected_file_path=str(frontend_dir),
                priority=1
            ))
            return gaps

        src_dir = frontend_dir / "src"
        if not src_dir.exists():
            gaps.append(ImplementationGap(
                component_type="frontend_structure",
                component_name="src",
                expected_file_path=str(src_dir),
                priority=1
            ))
            return gaps

        # Check for main App file
        app_files = [
            src_dir / "App.tsx",
            src_dir / "App.jsx",
            src_dir / "App.vue"
        ]
        if not any(f.exists() for f in app_files):
            gaps.append(ImplementationGap(
                component_type="frontend_core",
                component_name="App",
                expected_file_path=str(src_dir / "App.tsx"),
                priority=1
            ))

        # Check for components directory
        components_dir = src_dir / "components"
        if not components_dir.exists():
            gaps.append(ImplementationGap(
                component_type="frontend_structure",
                component_name="components",
                expected_file_path=str(components_dir),
                priority=1
            ))

        # Check for pages/views directory
        pages_dir = src_dir / "pages"
        views_dir = src_dir / "views"
        if not pages_dir.exists() and not views_dir.exists():
            gaps.append(ImplementationGap(
                component_type="frontend_structure",
                component_name="pages",
                expected_file_path=str(pages_dir),
                priority=2
            ))

        # Check for services/API directory
        services_dir = src_dir / "services"
        api_dir = src_dir / "api"
        if not services_dir.exists() and not api_dir.exists():
            gaps.append(ImplementationGap(
                component_type="frontend_structure",
                component_name="services",
                expected_file_path=str(services_dir),
                priority=2
            ))

        return gaps

    def _extract_expected_routes(self, server_file: Path) -> List[str]:
        """Extract expected route names from server.ts imports"""
        try:
            content = server_file.read_text()
            # Pattern: import <name>Routes from './routes/<name>.routes';
            pattern = r"import\s+(\w+)Routes\s+from\s+['\"]\.\/routes\/\w+\.routes['\"]"
            matches = re.findall(pattern, content)
            return matches
        except Exception:
            return []

    def _estimate_completion_percentage(
        self,
        gaps_by_phase: Dict[str, List[Gap]],
        implementation_gaps: List[ImplementationGap]
    ) -> float:
        """
        Estimate overall completion percentage based on gaps

        Phase weights:
        - Requirements: 10%
        - Design: 15%
        - Implementation: 50%
        - Testing: 15%
        - Deployment: 10%
        """
        phase_weights = {
            "requirements": 0.10,
            "design": 0.15,
            "implementation": 0.50,
            "testing": 0.15,
            "deployment": 0.10
        }

        total_completion = 0.0

        for phase, weight in phase_weights.items():
            phase_gaps = gaps_by_phase.get(phase, [])
            critical_gaps = sum(1 for g in phase_gaps if g.severity == ValidationSeverity.CRITICAL)
            high_gaps = sum(1 for g in phase_gaps if g.severity == ValidationSeverity.HIGH)

            if critical_gaps > 0:
                # Critical gaps mean phase is <30% complete
                phase_completion = 0.25
            elif high_gaps > 3:
                # Many high-priority gaps mean phase is ~50% complete
                phase_completion = 0.50
            elif high_gaps > 0:
                # Some high-priority gaps mean phase is ~70% complete
                phase_completion = 0.70
            elif len(phase_gaps) > 0:
                # Only medium/low gaps mean phase is ~85% complete
                phase_completion = 0.85
            else:
                # No gaps = 100% complete
                phase_completion = 1.0

            total_completion += phase_completion * weight

        # For implementation, also factor in implementation gaps
        if implementation_gaps:
            impl_gap_count = len(implementation_gaps)
            if impl_gap_count > 20:
                impl_penalty = 0.30  # Major implementation missing
            elif impl_gap_count > 10:
                impl_penalty = 0.20  # Significant implementation missing
            elif impl_gap_count > 5:
                impl_penalty = 0.10  # Some implementation missing
            else:
                impl_penalty = 0.05  # Minor implementation missing

            total_completion -= impl_penalty

        return max(0.0, min(1.0, total_completion))

    def _calculate_recovery_priority(
        self,
        critical_gaps: int,
        high_gaps: int,
        completion_pct: float
    ) -> int:
        """
        Calculate recovery priority (1-5, 1=highest priority)

        Priority rules:
        - 1: Critical gaps and <30% complete
        - 2: Critical gaps and 30-60% complete
        - 3: High gaps but no critical, or >60% complete with critical
        - 4: Only medium/low gaps
        - 5: Nearly complete (>90%)
        """
        if completion_pct > 0.90:
            return 5
        elif critical_gaps == 0 and high_gaps == 0:
            return 4
        elif critical_gaps == 0:
            return 3
        elif completion_pct < 0.30:
            return 1
        elif completion_pct < 0.60:
            return 2
        else:
            return 3

    def generate_recovery_context(self, report: GapAnalysisReport) -> Dict[str, Any]:
        """
        Generate recovery context for resuming workflow

        This context can be passed to the workflow engine to resume
        implementation phase with specific instructions to fill gaps
        """
        # Group implementation gaps by component type
        gaps_by_component = {}
        for gap in report.implementation_gaps:
            if gap.component_type not in gaps_by_component:
                gaps_by_component[gap.component_type] = []
            gaps_by_component[gap.component_type].append(gap)

        # Sort by priority
        for component_type in gaps_by_component:
            gaps_by_component[component_type].sort(key=lambda g: g.priority)

        # Generate specific instructions
        instructions = []

        # Backend instructions
        if "backend_routes" in gaps_by_component:
            route_names = [g.component_name for g in gaps_by_component["backend_routes"]]
            instructions.append({
                "phase": "implementation",
                "subphase": "backend_api",
                "action": "create_routes",
                "components": route_names,
                "details": "Create route handlers for the following endpoints",
                "priority": 1
            })

        if "backend_structure" in gaps_by_component:
            missing_dirs = [g.component_name for g in gaps_by_component["backend_structure"]]
            if "services" in missing_dirs:
                instructions.append({
                    "phase": "implementation",
                    "subphase": "backend_core",
                    "action": "create_services",
                    "details": "Create business logic services layer",
                    "priority": 1
                })
            if "controllers" in missing_dirs:
                instructions.append({
                    "phase": "implementation",
                    "subphase": "backend_api",
                    "action": "create_controllers",
                    "details": "Create request handler controllers",
                    "priority": 1
                })
            if "middleware" in missing_dirs:
                instructions.append({
                    "phase": "implementation",
                    "subphase": "backend_middleware",
                    "action": "create_middleware",
                    "details": "Create authentication, validation, and error handling middleware",
                    "priority": 2
                })

        # Frontend instructions
        if "frontend_structure" in gaps_by_component or "frontend_core" in gaps_by_component:
            instructions.append({
                "phase": "implementation",
                "subphase": "frontend_core",
                "action": "create_frontend_structure",
                "details": "Create complete frontend application structure with src/, components/, pages/, and services/",
                "priority": 1
            })

        # Sort instructions by priority
        instructions.sort(key=lambda i: i["priority"])

        # Serialize implementation gaps
        serialized_gaps = {}
        for component_type, gaps in gaps_by_component.items():
            serialized_gaps[component_type] = [gap.to_dict() for gap in gaps]

        recovery_context = {
            "workflow_id": report.workflow_id,
            "resume_from_phase": "implementation",
            "gaps_summary": {
                "total_gaps": report.total_gaps,
                "critical_gaps": report.critical_gaps,
                "estimated_completion": report.estimated_completion_percentage
            },
            "implementation_gaps": serialized_gaps,
            "recovery_instructions": instructions,
            "deployment_blockers": [gap.to_dict() for gap in report.deployment_blockers],
            "recommended_approach": self._generate_recovery_approach(report)
        }

        return recovery_context

    def _generate_recovery_approach(self, report: GapAnalysisReport) -> str:
        """Generate recommended recovery approach based on gaps"""
        if report.estimated_completion_percentage < 0.30:
            return (
                "FULL RESTART: Less than 30% complete. Recommend restarting "
                "implementation phase with enhanced validation and sub-phase tracking."
            )
        elif report.estimated_completion_percentage < 0.60:
            return (
                "INCREMENTAL COMPLETION: 30-60% complete. Resume implementation "
                "phase focusing on missing backend services/routes and frontend structure."
            )
        elif report.critical_gaps > 0:
            return (
                "TARGETED FIXES: >60% complete but has critical gaps. Fix specific "
                "deployment blockers without full phase restart."
            )
        else:
            return (
                "POLISH AND DEPLOY: >60% complete with no critical gaps. Focus on "
                "testing validation and deployment readiness checks."
            )


class BatchGapDetector:
    """Detect gaps across multiple workflows"""

    def __init__(self, workflows_dir: Path):
        """
        Initialize batch gap detector

        Args:
            workflows_dir: Directory containing multiple workflow outputs
        """
        self.workflows_dir = Path(workflows_dir)

    def detect_all_gaps(self) -> Dict[str, GapAnalysisReport]:
        """
        Detect gaps in all workflows

        Returns:
            Dictionary mapping workflow_id to GapAnalysisReport
        """
        reports = {}

        # Find all workflow directories
        workflow_dirs = [
            d for d in self.workflows_dir.iterdir()
            if d.is_dir() and d.name.startswith("wf-")
        ]

        for workflow_dir in workflow_dirs:
            try:
                detector = WorkflowGapDetector(workflow_dir)
                report = detector.detect_gaps()
                reports[report.workflow_id] = report
            except Exception as e:
                print(f"Error analyzing {workflow_dir.name}: {e}")

        return reports

    def generate_batch_summary(
        self, reports: Dict[str, GapAnalysisReport]
    ) -> Dict[str, Any]:
        """Generate summary across all workflows"""
        total_workflows = len(reports)
        deployable_workflows = sum(1 for r in reports.values() if r.is_deployable)

        avg_completion = sum(r.estimated_completion_percentage for r in reports.values()) / total_workflows if total_workflows > 0 else 0

        total_critical_gaps = sum(r.critical_gaps for r in reports.values())
        total_high_gaps = sum(r.high_priority_gaps for r in reports.values())
        total_gaps = sum(r.total_gaps for r in reports.values())

        # Sort by recovery priority
        prioritized_workflows = sorted(
            reports.values(),
            key=lambda r: (r.recovery_priority, -r.estimated_completion_percentage)
        )

        return {
            "total_workflows_analyzed": total_workflows,
            "deployable_workflows": deployable_workflows,
            "workflows_needing_fixes": total_workflows - deployable_workflows,
            "average_completion_percentage": round(avg_completion * 100, 2),
            "total_gaps": {
                "critical": total_critical_gaps,
                "high": total_high_gaps,
                "all": total_gaps
            },
            "recovery_queue": [
                {
                    "workflow_id": r.workflow_id,
                    "priority": r.recovery_priority,
                    "completion": round(r.estimated_completion_percentage * 100, 2),
                    "critical_gaps": r.critical_gaps,
                    "high_gaps": r.high_priority_gaps
                }
                for r in prioritized_workflows
            ]
        }

    def save_reports(
        self,
        reports: Dict[str, GapAnalysisReport],
        output_file: Path
    ):
        """Save all gap analysis reports to JSON file"""
        output_data = {
            "batch_summary": self.generate_batch_summary(reports),
            "workflow_reports": {
                wf_id: report.to_dict()
                for wf_id, report in reports.items()
            }
        }

        output_file.write_text(json.dumps(output_data, indent=2))
        print(f"Gap analysis reports saved to: {output_file}")


def main():
    """CLI for gap detection"""
    import argparse

    parser = argparse.ArgumentParser(description="Detect gaps in workflow outputs")
    parser.add_argument(
        "workflow_dir",
        type=Path,
        help="Path to workflow directory or parent directory containing multiple workflows"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Analyze all workflows in directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for gap analysis report (JSON)"
    )
    parser.add_argument(
        "--recovery-context",
        action="store_true",
        help="Generate recovery context for resuming workflows"
    )

    args = parser.parse_args()

    if args.batch:
        # Batch analysis
        detector = BatchGapDetector(args.workflow_dir)
        reports = detector.detect_all_gaps()

        # Print summary
        summary = detector.generate_batch_summary(reports)
        print("\n" + "="*80)
        print("BATCH GAP ANALYSIS SUMMARY")
        print("="*80)
        print(f"Total workflows analyzed: {summary['total_workflows_analyzed']}")
        print(f"Deployable workflows: {summary['deployable_workflows']}")
        print(f"Workflows needing fixes: {summary['workflows_needing_fixes']}")
        print(f"Average completion: {summary['average_completion_percentage']}%")
        print(f"\nTotal gaps: {summary['total_gaps']['all']}")
        print(f"  - Critical: {summary['total_gaps']['critical']}")
        print(f"  - High: {summary['total_gaps']['high']}")
        print("\nRecovery Queue (priority order):")
        for item in summary['recovery_queue']:
            print(f"  {item['workflow_id']}: Priority {item['priority']}, "
                  f"{item['completion']}% complete, "
                  f"{item['critical_gaps']} critical gaps")

        # Save reports if output specified
        if args.output:
            detector.save_reports(reports, args.output)

        # Generate recovery contexts
        if args.recovery_context:
            recovery_dir = args.workflow_dir / "recovery_contexts"
            recovery_dir.mkdir(exist_ok=True)

            for wf_id, report in reports.items():
                if not report.is_deployable:
                    detector_single = WorkflowGapDetector(report.workflow_dir)
                    recovery_ctx = detector_single.generate_recovery_context(report)

                    recovery_file = recovery_dir / f"{wf_id}_recovery.json"
                    recovery_file.write_text(json.dumps(recovery_ctx, indent=2))
                    print(f"Recovery context saved: {recovery_file}")

    else:
        # Single workflow analysis
        detector = WorkflowGapDetector(args.workflow_dir)
        report = detector.detect_gaps()

        # Print report
        print("\n" + "="*80)
        print(f"GAP ANALYSIS: {report.workflow_id}")
        print("="*80)
        print(f"Completion: {report.estimated_completion_percentage*100:.1f}%")
        print(f"Deployable: {'Yes' if report.is_deployable else 'No'}")
        print(f"Recovery Priority: {report.recovery_priority}")
        print(f"\nTotal Gaps: {report.total_gaps}")
        print(f"  - Critical: {report.critical_gaps}")
        print(f"  - High: {report.high_priority_gaps}")
        print(f"  - Medium: {report.medium_priority_gaps}")
        print(f"  - Low: {report.low_priority_gaps}")

        print("\nGaps by Phase:")
        for phase, gaps in report.gaps_by_phase.items():
            if gaps:
                print(f"\n  {phase.upper()}: {len(gaps)} gaps")
                for gap in gaps[:3]:  # Show first 3
                    print(f"    - [{gap.severity.value}] {gap.description}")
                if len(gaps) > 3:
                    print(f"    ... and {len(gaps) - 3} more")

        print(f"\nImplementation Gaps: {len(report.implementation_gaps)}")
        for gap in report.implementation_gaps[:5]:  # Show first 5
            print(f"  - {gap.component_type}: {gap.component_name}")
            print(f"    Expected: {gap.expected_file_path}")
        if len(report.implementation_gaps) > 5:
            print(f"  ... and {len(report.implementation_gaps) - 5} more")

        print(f"\nDeployment Blockers: {len(report.deployment_blockers)}")
        for blocker in report.deployment_blockers:
            print(f"  - {blocker.description}")

        # Save report if output specified
        if args.output:
            args.output.write_text(json.dumps(report.to_dict(), indent=2))
            print(f"\nReport saved to: {args.output}")

        # Generate recovery context
        if args.recovery_context:
            recovery_ctx = detector.generate_recovery_context(report)
            recovery_file = args.workflow_dir.parent / f"{report.workflow_id}_recovery.json"
            recovery_file.write_text(json.dumps(recovery_ctx, indent=2))
            print(f"\nRecovery context saved to: {recovery_file}")


if __name__ == "__main__":
    main()
