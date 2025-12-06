"""
ACC Architecture Diff Tracking (MD-2085)

Tracks architectural changes over time to detect regressions.
Provides snapshot comparison for modules, dependencies, cycles, and violations.

Features:
- ArchitectureSnapshot: Immutable point-in-time capture
- ArchitectureDiff: Computed differences between snapshots
- DiffTracker: Manages snapshots and computes diffs
- Historical analysis for trend detection
"""

import json
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from acc.import_graph_builder import ImportGraph, ImportGraphBuilder
from acc.rule_engine import Violation, Severity

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureSnapshot:
    """
    Immutable snapshot of architecture at a point in time.

    Captures key metrics and structure for comparison.
    """
    id: str
    timestamp: datetime
    project_path: str
    commit_hash: Optional[str] = None
    branch: Optional[str] = None

    # Module metrics
    module_count: int = 0
    total_lines: int = 0
    modules: List[str] = field(default_factory=list)

    # Dependency metrics
    dependency_count: int = 0
    dependencies: List[Tuple[str, str]] = field(default_factory=list)

    # Cycle metrics
    cycle_count: int = 0
    cycles: List[List[str]] = field(default_factory=list)

    # Violation metrics
    violation_count: int = 0
    blocking_violations: int = 0
    warning_violations: int = 0
    violations: List[Dict[str, Any]] = field(default_factory=list)

    # Coupling metrics
    coupling_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    avg_instability: float = 0.0
    max_coupling: int = 0

    # Graph hash for quick comparison
    graph_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for serialization."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'project_path': self.project_path,
            'commit_hash': self.commit_hash,
            'branch': self.branch,
            'module_count': self.module_count,
            'total_lines': self.total_lines,
            'modules': self.modules,
            'dependency_count': self.dependency_count,
            'dependencies': self.dependencies,
            'cycle_count': self.cycle_count,
            'cycles': self.cycles,
            'violation_count': self.violation_count,
            'blocking_violations': self.blocking_violations,
            'warning_violations': self.warning_violations,
            'violations': self.violations,
            'coupling_metrics': self.coupling_metrics,
            'avg_instability': self.avg_instability,
            'max_coupling': self.max_coupling,
            'graph_hash': self.graph_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchitectureSnapshot':
        """Create snapshot from dictionary."""
        return cls(
            id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            project_path=data['project_path'],
            commit_hash=data.get('commit_hash'),
            branch=data.get('branch'),
            module_count=data.get('module_count', 0),
            total_lines=data.get('total_lines', 0),
            modules=data.get('modules', []),
            dependency_count=data.get('dependency_count', 0),
            dependencies=[tuple(d) for d in data.get('dependencies', [])],
            cycle_count=data.get('cycle_count', 0),
            cycles=data.get('cycles', []),
            violation_count=data.get('violation_count', 0),
            blocking_violations=data.get('blocking_violations', 0),
            warning_violations=data.get('warning_violations', 0),
            violations=data.get('violations', []),
            coupling_metrics=data.get('coupling_metrics', {}),
            avg_instability=data.get('avg_instability', 0.0),
            max_coupling=data.get('max_coupling', 0),
            graph_hash=data.get('graph_hash', '')
        )

    @classmethod
    def from_graph(
        cls,
        graph: ImportGraph,
        project_path: str,
        snapshot_id: Optional[str] = None,
        commit_hash: Optional[str] = None,
        branch: Optional[str] = None,
        violations: Optional[List[Violation]] = None
    ) -> 'ArchitectureSnapshot':
        """
        Create snapshot from ImportGraph.

        Args:
            graph: ImportGraph to snapshot
            project_path: Project path
            snapshot_id: Optional snapshot ID (generated if not provided)
            commit_hash: Git commit hash
            branch: Git branch name
            violations: Optional list of violations to include

        Returns:
            ArchitectureSnapshot
        """
        timestamp = datetime.now()
        if not snapshot_id:
            snapshot_id = f"snap_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Extract modules
        modules = list(graph.modules.keys())

        # Extract dependencies
        dependencies = list(graph.graph.edges())

        # Extract cycles
        cycles = graph.find_cycles()

        # Calculate coupling metrics
        coupling_metrics = {}
        instabilities = []
        max_coupling = 0

        for module_name in modules:
            ca, ce, instability = graph.calculate_coupling(module_name)
            coupling_metrics[module_name] = {
                'afferent_coupling': ca,
                'efferent_coupling': ce,
                'instability': instability
            }
            instabilities.append(instability)
            max_coupling = max(max_coupling, ca + ce)

        avg_instability = sum(instabilities) / len(instabilities) if instabilities else 0.0

        # Calculate total lines
        total_lines = sum(info.size_lines for info in graph.modules.values())

        # Process violations
        violation_dicts = []
        blocking = 0
        warning = 0

        if violations:
            for v in violations:
                violation_dicts.append(v.to_dict())
                if v.severity == Severity.BLOCKING:
                    blocking += 1
                elif v.severity == Severity.WARNING:
                    warning += 1

        # Calculate graph hash
        hash_content = json.dumps({
            'modules': sorted(modules),
            'dependencies': sorted([f"{s}->{t}" for s, t in dependencies])
        }, sort_keys=True)
        graph_hash = hashlib.md5(hash_content.encode()).hexdigest()

        return cls(
            id=snapshot_id,
            timestamp=timestamp,
            project_path=project_path,
            commit_hash=commit_hash,
            branch=branch,
            module_count=len(modules),
            total_lines=total_lines,
            modules=modules,
            dependency_count=len(dependencies),
            dependencies=dependencies,
            cycle_count=len(cycles),
            cycles=cycles,
            violation_count=len(violation_dicts),
            blocking_violations=blocking,
            warning_violations=warning,
            violations=violation_dicts,
            coupling_metrics=coupling_metrics,
            avg_instability=avg_instability,
            max_coupling=max_coupling,
            graph_hash=graph_hash
        )


@dataclass
class ArchitectureDiff:
    """
    Computed differences between two architecture snapshots.

    Identifies:
    - Added/removed modules
    - Added/removed dependencies
    - New/resolved cycles
    - New/resolved violations
    - Coupling metric changes
    """
    from_snapshot_id: str
    to_snapshot_id: str
    from_timestamp: datetime
    to_timestamp: datetime

    # Module changes
    modules_added: List[str] = field(default_factory=list)
    modules_removed: List[str] = field(default_factory=list)
    modules_unchanged: int = 0

    # Dependency changes
    dependencies_added: List[Tuple[str, str]] = field(default_factory=list)
    dependencies_removed: List[Tuple[str, str]] = field(default_factory=list)
    dependencies_unchanged: int = 0

    # Cycle changes
    new_cycles: List[List[str]] = field(default_factory=list)
    resolved_cycles: List[List[str]] = field(default_factory=list)

    # Violation changes
    new_violations: List[Dict[str, Any]] = field(default_factory=list)
    resolved_violations: List[Dict[str, Any]] = field(default_factory=list)

    # Metric changes
    module_count_delta: int = 0
    dependency_count_delta: int = 0
    line_count_delta: int = 0
    violation_count_delta: int = 0
    cycle_count_delta: int = 0
    instability_delta: float = 0.0

    # Coupling changes (significant only)
    coupling_increases: Dict[str, float] = field(default_factory=dict)
    coupling_decreases: Dict[str, float] = field(default_factory=dict)

    # Summary flags
    has_breaking_changes: bool = False
    has_new_cycles: bool = False
    has_new_blocking_violations: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert diff to dictionary."""
        return {
            'from_snapshot_id': self.from_snapshot_id,
            'to_snapshot_id': self.to_snapshot_id,
            'from_timestamp': self.from_timestamp.isoformat(),
            'to_timestamp': self.to_timestamp.isoformat(),
            'modules_added': self.modules_added,
            'modules_removed': self.modules_removed,
            'modules_unchanged': self.modules_unchanged,
            'dependencies_added': self.dependencies_added,
            'dependencies_removed': self.dependencies_removed,
            'dependencies_unchanged': self.dependencies_unchanged,
            'new_cycles': self.new_cycles,
            'resolved_cycles': self.resolved_cycles,
            'new_violations': self.new_violations,
            'resolved_violations': self.resolved_violations,
            'module_count_delta': self.module_count_delta,
            'dependency_count_delta': self.dependency_count_delta,
            'line_count_delta': self.line_count_delta,
            'violation_count_delta': self.violation_count_delta,
            'cycle_count_delta': self.cycle_count_delta,
            'instability_delta': self.instability_delta,
            'coupling_increases': self.coupling_increases,
            'coupling_decreases': self.coupling_decreases,
            'has_breaking_changes': self.has_breaking_changes,
            'has_new_cycles': self.has_new_cycles,
            'has_new_blocking_violations': self.has_new_blocking_violations
        }

    def summary(self) -> str:
        """Generate human-readable summary of changes."""
        lines = [
            f"Architecture Diff: {self.from_snapshot_id} -> {self.to_snapshot_id}",
            f"Time span: {self.from_timestamp.isoformat()} to {self.to_timestamp.isoformat()}",
            "",
            "=== Module Changes ===",
            f"  Added: {len(self.modules_added)}",
            f"  Removed: {len(self.modules_removed)}",
            f"  Net change: {self.module_count_delta:+d}",
            "",
            "=== Dependency Changes ===",
            f"  Added: {len(self.dependencies_added)}",
            f"  Removed: {len(self.dependencies_removed)}",
            f"  Net change: {self.dependency_count_delta:+d}",
            "",
            "=== Cycle Changes ===",
            f"  New cycles: {len(self.new_cycles)}",
            f"  Resolved cycles: {len(self.resolved_cycles)}",
            f"  Net change: {self.cycle_count_delta:+d}",
            "",
            "=== Violation Changes ===",
            f"  New violations: {len(self.new_violations)}",
            f"  Resolved violations: {len(self.resolved_violations)}",
            f"  Net change: {self.violation_count_delta:+d}",
            "",
            "=== Metrics ===",
            f"  Lines of code: {self.line_count_delta:+d}",
            f"  Avg instability: {self.instability_delta:+.3f}",
        ]

        if self.has_breaking_changes:
            lines.append("\n*** WARNING: Breaking changes detected! ***")
        if self.has_new_cycles:
            lines.append("*** WARNING: New cyclic dependencies introduced! ***")
        if self.has_new_blocking_violations:
            lines.append("*** WARNING: New blocking violations! ***")

        return "\n".join(lines)


class DiffTracker:
    """
    Manages architecture snapshots and computes diffs.

    Stores snapshots in reports/acc/snapshots/ directory.
    Supports historical analysis and trend detection.
    """

    def __init__(
        self,
        storage_path: str = "reports/acc/snapshots",
        max_snapshots: int = 30
    ):
        """
        Initialize diff tracker.

        Args:
            storage_path: Directory for storing snapshots
            max_snapshots: Maximum number of snapshots to retain
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = max_snapshots
        self._snapshots: Dict[str, ArchitectureSnapshot] = {}
        self._load_snapshots()

    def _load_snapshots(self):
        """Load existing snapshots from storage."""
        for snapshot_file in self.storage_path.glob("*.json"):
            try:
                with open(snapshot_file, 'r') as f:
                    data = json.load(f)
                snapshot = ArchitectureSnapshot.from_dict(data)
                self._snapshots[snapshot.id] = snapshot
            except Exception as e:
                logger.warning(f"Failed to load snapshot {snapshot_file}: {e}")

        logger.info(f"Loaded {len(self._snapshots)} snapshots")

    def create_snapshot(
        self,
        graph: ImportGraph,
        project_path: str,
        snapshot_id: Optional[str] = None,
        commit_hash: Optional[str] = None,
        branch: Optional[str] = None,
        violations: Optional[List[Violation]] = None
    ) -> ArchitectureSnapshot:
        """
        Create and store a new architecture snapshot.

        Args:
            graph: ImportGraph to snapshot
            project_path: Project path
            snapshot_id: Optional snapshot ID
            commit_hash: Git commit hash
            branch: Git branch
            violations: Optional violations list

        Returns:
            Created ArchitectureSnapshot
        """
        snapshot = ArchitectureSnapshot.from_graph(
            graph=graph,
            project_path=project_path,
            snapshot_id=snapshot_id,
            commit_hash=commit_hash,
            branch=branch,
            violations=violations
        )

        # Store snapshot
        self._snapshots[snapshot.id] = snapshot
        self._save_snapshot(snapshot)

        # Cleanup old snapshots
        self._cleanup_old_snapshots()

        logger.info(f"Created snapshot {snapshot.id} with {snapshot.module_count} modules")

        return snapshot

    def _save_snapshot(self, snapshot: ArchitectureSnapshot):
        """Save snapshot to disk."""
        snapshot_file = self.storage_path / f"{snapshot.id}.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def _cleanup_old_snapshots(self):
        """Remove old snapshots exceeding max_snapshots limit."""
        if len(self._snapshots) <= self.max_snapshots:
            return

        # Sort by timestamp and remove oldest
        sorted_snapshots = sorted(
            self._snapshots.values(),
            key=lambda s: s.timestamp
        )

        to_remove = sorted_snapshots[:-self.max_snapshots]
        for snapshot in to_remove:
            del self._snapshots[snapshot.id]
            snapshot_file = self.storage_path / f"{snapshot.id}.json"
            if snapshot_file.exists():
                snapshot_file.unlink()

        logger.info(f"Cleaned up {len(to_remove)} old snapshots")

    def get_snapshot(self, snapshot_id: str) -> Optional[ArchitectureSnapshot]:
        """Get snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_latest_snapshot(self) -> Optional[ArchitectureSnapshot]:
        """Get most recent snapshot."""
        if not self._snapshots:
            return None

        return max(self._snapshots.values(), key=lambda s: s.timestamp)

    def list_snapshots(self) -> List[ArchitectureSnapshot]:
        """List all snapshots sorted by timestamp (newest first)."""
        return sorted(
            self._snapshots.values(),
            key=lambda s: s.timestamp,
            reverse=True
        )

    def compute_diff(
        self,
        from_snapshot_id: str,
        to_snapshot_id: str
    ) -> Optional[ArchitectureDiff]:
        """
        Compute diff between two snapshots.

        Args:
            from_snapshot_id: Earlier snapshot ID
            to_snapshot_id: Later snapshot ID

        Returns:
            ArchitectureDiff or None if snapshots not found
        """
        from_snap = self.get_snapshot(from_snapshot_id)
        to_snap = self.get_snapshot(to_snapshot_id)

        if not from_snap or not to_snap:
            logger.error(f"Snapshot not found: {from_snapshot_id} or {to_snapshot_id}")
            return None

        return self._compute_diff(from_snap, to_snap)

    def compute_diff_from_latest(
        self,
        current_graph: ImportGraph,
        project_path: str,
        violations: Optional[List[Violation]] = None
    ) -> Optional[ArchitectureDiff]:
        """
        Compute diff between latest snapshot and current state.

        Args:
            current_graph: Current ImportGraph
            project_path: Project path
            violations: Current violations

        Returns:
            ArchitectureDiff or None if no previous snapshot exists
        """
        latest = self.get_latest_snapshot()
        if not latest:
            logger.info("No previous snapshot found, creating baseline")
            return None

        # Create temporary snapshot for current state
        current_snap = ArchitectureSnapshot.from_graph(
            graph=current_graph,
            project_path=project_path,
            snapshot_id="current",
            violations=violations
        )

        return self._compute_diff(latest, current_snap)

    def _compute_diff(
        self,
        from_snap: ArchitectureSnapshot,
        to_snap: ArchitectureSnapshot
    ) -> ArchitectureDiff:
        """Compute diff between two snapshots."""
        # Module changes
        from_modules = set(from_snap.modules)
        to_modules = set(to_snap.modules)
        modules_added = list(to_modules - from_modules)
        modules_removed = list(from_modules - to_modules)
        modules_unchanged = len(from_modules & to_modules)

        # Dependency changes
        from_deps = set(from_snap.dependencies)
        to_deps = set(to_snap.dependencies)
        deps_added = list(to_deps - from_deps)
        deps_removed = list(from_deps - to_deps)
        deps_unchanged = len(from_deps & to_deps)

        # Cycle changes
        from_cycles = set(tuple(c) for c in from_snap.cycles)
        to_cycles = set(tuple(c) for c in to_snap.cycles)
        new_cycles = [list(c) for c in (to_cycles - from_cycles)]
        resolved_cycles = [list(c) for c in (from_cycles - to_cycles)]

        # Violation changes
        from_violation_ids = {v.get('rule_id') for v in from_snap.violations}
        to_violation_ids = {v.get('rule_id') for v in to_snap.violations}

        new_violations = [v for v in to_snap.violations if v.get('rule_id') not in from_violation_ids]
        resolved_violations = [v for v in from_snap.violations if v.get('rule_id') not in to_violation_ids]

        # Coupling changes
        coupling_increases = {}
        coupling_decreases = {}
        threshold = 0.1  # Significant change threshold

        for module in to_modules & from_modules:
            from_metrics = from_snap.coupling_metrics.get(module, {})
            to_metrics = to_snap.coupling_metrics.get(module, {})

            from_coupling = from_metrics.get('afferent_coupling', 0) + from_metrics.get('efferent_coupling', 0)
            to_coupling = to_metrics.get('afferent_coupling', 0) + to_metrics.get('efferent_coupling', 0)

            if to_coupling - from_coupling > threshold:
                coupling_increases[module] = to_coupling - from_coupling
            elif from_coupling - to_coupling > threshold:
                coupling_decreases[module] = from_coupling - to_coupling

        # Check for new blocking violations
        has_new_blocking = any(
            v.get('severity') == 'blocking' for v in new_violations
        )

        # Determine if breaking changes occurred
        has_breaking = bool(modules_removed) or bool(new_cycles) or has_new_blocking

        return ArchitectureDiff(
            from_snapshot_id=from_snap.id,
            to_snapshot_id=to_snap.id,
            from_timestamp=from_snap.timestamp,
            to_timestamp=to_snap.timestamp,
            modules_added=modules_added,
            modules_removed=modules_removed,
            modules_unchanged=modules_unchanged,
            dependencies_added=deps_added,
            dependencies_removed=deps_removed,
            dependencies_unchanged=deps_unchanged,
            new_cycles=new_cycles,
            resolved_cycles=resolved_cycles,
            new_violations=new_violations,
            resolved_violations=resolved_violations,
            module_count_delta=to_snap.module_count - from_snap.module_count,
            dependency_count_delta=to_snap.dependency_count - from_snap.dependency_count,
            line_count_delta=to_snap.total_lines - from_snap.total_lines,
            violation_count_delta=to_snap.violation_count - from_snap.violation_count,
            cycle_count_delta=to_snap.cycle_count - from_snap.cycle_count,
            instability_delta=to_snap.avg_instability - from_snap.avg_instability,
            coupling_increases=coupling_increases,
            coupling_decreases=coupling_decreases,
            has_breaking_changes=has_breaking,
            has_new_cycles=bool(new_cycles),
            has_new_blocking_violations=has_new_blocking
        )

    def get_trend(
        self,
        metric: str,
        num_snapshots: int = 10
    ) -> List[Tuple[datetime, float]]:
        """
        Get historical trend for a metric.

        Args:
            metric: Metric name (module_count, dependency_count, violation_count, etc.)
            num_snapshots: Number of snapshots to include

        Returns:
            List of (timestamp, value) tuples
        """
        snapshots = self.list_snapshots()[:num_snapshots]

        trend = []
        for snap in reversed(snapshots):
            value = getattr(snap, metric, None)
            if value is not None:
                trend.append((snap.timestamp, value))

        return trend


# Convenience function
def create_snapshot_from_project(
    project_path: str,
    storage_path: str = "reports/acc/snapshots",
    commit_hash: Optional[str] = None,
    branch: Optional[str] = None
) -> ArchitectureSnapshot:
    """
    Convenience function to create a snapshot from a project.

    Args:
        project_path: Path to project
        storage_path: Path to store snapshots
        commit_hash: Git commit hash
        branch: Git branch

    Returns:
        Created ArchitectureSnapshot
    """
    builder = ImportGraphBuilder(project_path)
    graph = builder.build_graph()

    tracker = DiffTracker(storage_path=storage_path)
    return tracker.create_snapshot(
        graph=graph,
        project_path=project_path,
        commit_hash=commit_hash,
        branch=branch
    )


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    project_path = sys.argv[1] if len(sys.argv) > 1 else "/home/ec2-user/projects/maestro-platform/maestro-hive"

    print(f"Creating architecture snapshot for: {project_path}")
    print("=" * 60)

    # Create snapshot
    snapshot = create_snapshot_from_project(project_path)

    print(f"\n=== Snapshot Created ===")
    print(f"  ID: {snapshot.id}")
    print(f"  Timestamp: {snapshot.timestamp}")
    print(f"  Modules: {snapshot.module_count}")
    print(f"  Dependencies: {snapshot.dependency_count}")
    print(f"  Cycles: {snapshot.cycle_count}")
    print(f"  Lines: {snapshot.total_lines}")
    print(f"  Avg Instability: {snapshot.avg_instability:.3f}")
    print(f"  Max Coupling: {snapshot.max_coupling}")
    print(f"  Graph Hash: {snapshot.graph_hash[:12]}...")

    # Show diff from previous if available
    tracker = DiffTracker()
    snapshots = tracker.list_snapshots()

    if len(snapshots) > 1:
        print(f"\n=== Diff from Previous Snapshot ===")
        diff = tracker.compute_diff(snapshots[1].id, snapshots[0].id)
        if diff:
            print(diff.summary())
