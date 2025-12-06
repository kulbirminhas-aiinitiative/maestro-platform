"""
ACC Cycle Analyzer (MD-2088)

Enhanced cycle detection with classification, reporting, and approval workflow.

Features:
- Cycle classification by severity
- Breaking point analysis
- Approval workflow for accepted cycles
- Historical tracking
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import json

logger = logging.getLogger(__name__)


class CycleClassification(str, Enum):
    """Classification of cyclic dependency severity."""
    INTRA_MODULE = "intra_module"  # Within same module/package
    INTER_MODULE = "inter_module"  # Between modules in same component
    INTER_COMPONENT = "inter_component"  # Between architectural components
    CROSS_LAYER = "cross_layer"  # Across architectural layers (worst)


class CycleSeverity(str, Enum):
    """Severity of a cycle."""
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


@dataclass
class BreakingCandidate:
    """Candidate edge to break a cycle."""
    source: str
    target: str
    impact_score: float  # 0-1, lower is better
    suggestion: str
    refactoring_type: str  # MOVE, EXTRACT_INTERFACE, EVENT_BUS, etc.


@dataclass
class CycleReport:
    """Detailed report for a detected cycle."""
    cycle_id: str
    nodes: List[str]
    edges: List[Tuple[str, str]]
    length: int
    classification: CycleClassification
    severity: CycleSeverity
    breaking_candidates: List[BreakingCandidate]
    is_approved: bool = False
    approval_adr: Optional[str] = None
    first_detected: datetime = field(default_factory=datetime.now)
    occurrences: int = 1
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cycle_id': self.cycle_id,
            'nodes': self.nodes,
            'edges': self.edges,
            'length': self.length,
            'classification': self.classification.value,
            'severity': self.severity.value,
            'breaking_candidates': [
                {
                    'source': bc.source,
                    'target': bc.target,
                    'impact_score': bc.impact_score,
                    'suggestion': bc.suggestion,
                    'refactoring_type': bc.refactoring_type
                }
                for bc in self.breaking_candidates
            ],
            'is_approved': self.is_approved,
            'approval_adr': self.approval_adr,
            'first_detected': self.first_detected.isoformat(),
            'occurrences': self.occurrences,
            'description': self.description
        }


class CycleAnalyzer:
    """
    Analyzes and classifies cyclic dependencies.

    Provides:
    - Cycle detection and classification
    - Breaking point analysis
    - Approval workflow
    - Historical tracking
    """

    def __init__(
        self,
        components: Optional[Dict[str, List[str]]] = None,
        layers: Optional[List[str]] = None,
        approved_cycles_path: str = "config/approved_cycles.json"
    ):
        """
        Initialize cycle analyzer.

        Args:
            components: Dict mapping component names to path patterns
            layers: List of layers from top to bottom
            approved_cycles_path: Path to approved cycles file
        """
        self.components = components or {
            'Presentation': ['routes/', 'api/', 'controllers/', 'views/'],
            'BusinessLogic': ['services/', 'domain/', 'core/'],
            'DataAccess': ['repositories/', 'models/', 'database/', 'dal/'],
            'Infrastructure': ['utils/', 'helpers/', 'config/', 'common/']
        }

        self.layers = layers or [
            'Presentation',
            'BusinessLogic',
            'DataAccess',
            'Infrastructure'
        ]

        self.approved_cycles_path = Path(approved_cycles_path)
        self._approved_cycles: Dict[str, Dict] = {}
        self._load_approved_cycles()

    def _load_approved_cycles(self):
        """Load approved cycles from file."""
        if self.approved_cycles_path.exists():
            try:
                with open(self.approved_cycles_path, 'r') as f:
                    self._approved_cycles = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load approved cycles: {e}")

    def _save_approved_cycles(self):
        """Save approved cycles to file."""
        self.approved_cycles_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.approved_cycles_path, 'w') as f:
            json.dump(self._approved_cycles, f, indent=2)

    def _get_cycle_id(self, cycle: List[str]) -> str:
        """Generate unique ID for a cycle."""
        # Normalize by starting from smallest node
        min_idx = cycle.index(min(cycle))
        normalized = cycle[min_idx:] + cycle[:min_idx]
        return f"cycle_{hash(tuple(normalized)) & 0xFFFFFFFF:08x}"

    def _get_component(self, module: str) -> Optional[str]:
        """Determine which component a module belongs to."""
        for component, patterns in self.components.items():
            for pattern in patterns:
                if pattern in module:
                    return component
        return None

    def _get_layer_index(self, component: Optional[str]) -> int:
        """Get layer index for a component (lower = higher layer)."""
        if component and component in self.layers:
            return self.layers.index(component)
        return len(self.layers)  # Unknown = lowest

    def classify_cycle(self, cycle: List[str]) -> CycleClassification:
        """
        Classify a cycle by its severity.

        Args:
            cycle: List of module names in the cycle

        Returns:
            CycleClassification
        """
        # Get components for all nodes
        components = [self._get_component(node) for node in cycle]
        unique_components = set(c for c in components if c)

        if len(unique_components) == 0:
            return CycleClassification.INTRA_MODULE

        if len(unique_components) == 1:
            return CycleClassification.INTRA_MODULE

        # Check for cross-layer violations
        layer_indices = [self._get_layer_index(c) for c in components]
        if len(set(layer_indices)) > 1:
            # Check if it crosses layers
            for i in range(len(layer_indices)):
                next_idx = (i + 1) % len(layer_indices)
                if layer_indices[next_idx] < layer_indices[i]:  # Going up layers
                    return CycleClassification.CROSS_LAYER

        if len(unique_components) > 1:
            return CycleClassification.INTER_COMPONENT

        return CycleClassification.INTER_MODULE

    def get_severity(self, classification: CycleClassification) -> CycleSeverity:
        """Map classification to severity."""
        mapping = {
            CycleClassification.INTRA_MODULE: CycleSeverity.INFO,
            CycleClassification.INTER_MODULE: CycleSeverity.WARNING,
            CycleClassification.INTER_COMPONENT: CycleSeverity.WARNING,
            CycleClassification.CROSS_LAYER: CycleSeverity.BLOCKING
        }
        return mapping.get(classification, CycleSeverity.WARNING)

    def find_breaking_candidates(
        self,
        cycle: List[str],
        dependencies: Dict[str, List[str]]
    ) -> List[BreakingCandidate]:
        """
        Find optimal edges to break a cycle.

        Args:
            cycle: List of module names in the cycle
            dependencies: Full dependency graph

        Returns:
            List of BreakingCandidate sorted by impact score
        """
        candidates = []

        for i in range(len(cycle)):
            source = cycle[i]
            target = cycle[(i + 1) % len(cycle)]

            # Calculate impact score based on:
            # - Number of other dependencies source has to target
            # - How central the edge is
            source_deps = len(dependencies.get(source, []))
            target_deps = len(dependencies.get(target, []))
            total_deps = source_deps + target_deps

            # Lower score = better candidate to break
            impact_score = 0.5  # Base score

            # Prefer breaking edges from modules with many dependencies
            if total_deps > 0:
                impact_score = 1 - (source_deps / total_deps) * 0.5

            # Generate suggestion
            source_component = self._get_component(source)
            target_component = self._get_component(target)

            if source_component and target_component and source_component != target_component:
                suggestion = f"Extract interface in {target_component} for {target}"
                refactoring_type = "EXTRACT_INTERFACE"
            else:
                suggestion = f"Consider using event bus or dependency injection for {source} -> {target}"
                refactoring_type = "EVENT_BUS"

            candidates.append(BreakingCandidate(
                source=source,
                target=target,
                impact_score=impact_score,
                suggestion=suggestion,
                refactoring_type=refactoring_type
            ))

        # Sort by impact score (lower is better)
        return sorted(candidates, key=lambda c: c.impact_score)

    def analyze_cycles(
        self,
        cycles: List[List[str]],
        dependencies: Dict[str, List[str]]
    ) -> List[CycleReport]:
        """
        Analyze all cycles and generate reports.

        Args:
            cycles: List of cycles (each cycle is list of module names)
            dependencies: Full dependency graph

        Returns:
            List of CycleReport objects
        """
        reports = []

        for cycle in cycles:
            cycle_id = self._get_cycle_id(cycle)
            classification = self.classify_cycle(cycle)
            severity = self.get_severity(classification)
            breaking_candidates = self.find_breaking_candidates(cycle, dependencies)

            # Check if approved
            approved_info = self._approved_cycles.get(cycle_id, {})
            is_approved = approved_info.get('approved', False)
            approval_adr = approved_info.get('adr_reference')

            # Build edges
            edges = [
                (cycle[i], cycle[(i + 1) % len(cycle)])
                for i in range(len(cycle))
            ]

            # Generate description
            description = f"{classification.value.replace('_', ' ').title()} cycle "
            description += f"involving {len(cycle)} modules"

            report = CycleReport(
                cycle_id=cycle_id,
                nodes=cycle,
                edges=edges,
                length=len(cycle),
                classification=classification,
                severity=severity,
                breaking_candidates=breaking_candidates,
                is_approved=is_approved,
                approval_adr=approval_adr,
                description=description
            )
            reports.append(report)

        return reports

    def approve_cycle(
        self,
        cycle_id: str,
        adr_reference: str,
        approved_by: str,
        justification: str
    ):
        """
        Approve a cycle with ADR reference.

        Args:
            cycle_id: Cycle ID to approve
            adr_reference: ADR reference (required)
            approved_by: Who approved
            justification: Why it's approved
        """
        self._approved_cycles[cycle_id] = {
            'approved': True,
            'adr_reference': adr_reference,
            'approved_by': approved_by,
            'approved_at': datetime.now().isoformat(),
            'justification': justification
        }
        self._save_approved_cycles()
        logger.info(f"Approved cycle {cycle_id} with ADR {adr_reference}")

    def revoke_approval(self, cycle_id: str):
        """Revoke approval for a cycle."""
        if cycle_id in self._approved_cycles:
            del self._approved_cycles[cycle_id]
            self._save_approved_cycles()
            logger.info(f"Revoked approval for cycle {cycle_id}")

    def get_unapproved_cycles(
        self,
        reports: List[CycleReport]
    ) -> List[CycleReport]:
        """Filter to only unapproved cycles."""
        return [r for r in reports if not r.is_approved]

    def get_blocking_cycles(
        self,
        reports: List[CycleReport]
    ) -> List[CycleReport]:
        """Filter to blocking (unapproved blocking severity) cycles."""
        return [
            r for r in reports
            if r.severity == CycleSeverity.BLOCKING and not r.is_approved
        ]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Sample cycles
    cycles = [
        ['services.user_service', 'services.auth_service', 'services.user_service'],
        ['controllers.api', 'services.business', 'dal.repository', 'controllers.api']
    ]

    # Sample dependencies
    dependencies = {
        'services.user_service': ['services.auth_service'],
        'services.auth_service': ['services.user_service'],
        'controllers.api': ['services.business'],
        'services.business': ['dal.repository'],
        'dal.repository': ['controllers.api']
    }

    analyzer = CycleAnalyzer()
    reports = analyzer.analyze_cycles(cycles, dependencies)

    print("=== Cycle Analysis Report ===\n")
    for report in reports:
        print(f"Cycle: {report.cycle_id}")
        print(f"  Classification: {report.classification.value}")
        print(f"  Severity: {report.severity.value}")
        print(f"  Nodes: {' -> '.join(report.nodes)}")
        print(f"  Approved: {report.is_approved}")
        if report.breaking_candidates:
            best = report.breaking_candidates[0]
            print(f"  Best fix: {best.suggestion}")
        print()
