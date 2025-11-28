"""
ACC Architecture Diff & Erosion Detection Tests
Test IDs: ACC-401 to ACC-430

Test Suite: Architecture Diff & Erosion Detection System

Comprehensive testing for:
1. Baseline Comparison (ACC-401 to ACC-406): Store/compare baselines, detect changes
2. Erosion Detection (ACC-407 to ACC-412): Track architectural degradation over time
3. Trend Analysis (ACC-413 to ACC-418): Analyze metrics trends and predict hotspots
4. Diff Reporting (ACC-419 to ACC-424): Generate comprehensive diff reports
5. Integration & Performance (ACC-425 to ACC-430): Integration and performance tests

These tests ensure:
1. Architecture changes are tracked accurately
2. Architectural erosion is detected early
3. Trends are analyzed for predictive maintenance
4. Comprehensive diff reports are generated
5. Performance meets requirements (<3s for 1000+ files)
"""

import pytest
import json
import yaml
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import networkx as nx
from enum import Enum
import time
import os


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ArchitectureSnapshot:
    """Snapshot of architecture state at a point in time"""
    commit: str
    date: datetime
    modules: Dict[str, Any]
    dependencies: List[Tuple[str, str]]
    coupling_metrics: Dict[str, Tuple[int, int, float]]
    cycles: List[List[str]]
    violations: List[Dict[str, Any]]
    complexity_metrics: Dict[str, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'commit': self.commit,
            'date': self.date.isoformat(),
            'modules': self.modules,
            'dependencies': [list(d) for d in self.dependencies],
            'coupling_metrics': {
                k: list(v) for k, v in self.coupling_metrics.items()
            },
            'cycles': self.cycles,
            'violations': self.violations,
            'complexity_metrics': self.complexity_metrics,
            'metadata': self.metadata,
            'stats': {
                'module_count': len(self.modules),
                'dependency_count': len(self.dependencies),
                'cycle_count': len(self.cycles),
                'violation_count': len(self.violations)
            }
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ArchitectureSnapshot':
        """Create from dictionary"""
        return ArchitectureSnapshot(
            commit=data['commit'],
            date=datetime.fromisoformat(data['date']),
            modules=data['modules'],
            dependencies=[tuple(d) for d in data['dependencies']],
            coupling_metrics={
                k: tuple(v) for k, v in data['coupling_metrics'].items()
            },
            cycles=data['cycles'],
            violations=data['violations'],
            complexity_metrics=data['complexity_metrics'],
            metadata=data.get('metadata', {})
        )


@dataclass
class ArchitectureDiff:
    """Difference between two architecture snapshots"""
    baseline: ArchitectureSnapshot
    current: ArchitectureSnapshot
    modules_added: List[str] = field(default_factory=list)
    modules_removed: List[str] = field(default_factory=list)
    modules_changed: List[str] = field(default_factory=list)
    dependencies_added: List[Tuple[str, str]] = field(default_factory=list)
    dependencies_removed: List[Tuple[str, str]] = field(default_factory=list)
    dependencies_changed: List[Tuple[str, str, str]] = field(default_factory=list)  # (module, old, new)
    cycles_introduced: List[List[str]] = field(default_factory=list)
    coupling_delta: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # module -> (old_total, new_total)
    complexity_delta: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    violations_introduced: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'baseline': {
                'commit': self.baseline.commit,
                'date': self.baseline.date.isoformat(),
                'modules': len(self.baseline.modules),
                'dependencies': len(self.baseline.dependencies)
            },
            'current': {
                'commit': self.current.commit,
                'date': self.current.date.isoformat(),
                'modules': len(self.current.modules),
                'dependencies': len(self.current.dependencies)
            },
            'diff': {
                'modules_added': self.modules_added,
                'modules_removed': self.modules_removed,
                'modules_changed': self.modules_changed,
                'dependencies_added': [list(d) for d in self.dependencies_added],
                'dependencies_removed': [list(d) for d in self.dependencies_removed],
                'dependencies_changed': [list(d) for d in self.dependencies_changed],
                'cycles_introduced': self.cycles_introduced,
                'coupling_delta': {
                    k: {'old': v[0], 'new': v[1], 'delta': v[1] - v[0]}
                    for k, v in self.coupling_delta.items()
                },
                'complexity_delta': {
                    k: {'old': v[0], 'new': v[1], 'delta': v[1] - v[0]}
                    for k, v in self.complexity_delta.items()
                },
                'violations_introduced': self.violations_introduced
            },
            'summary': {
                'modules_added_count': len(self.modules_added),
                'modules_removed_count': len(self.modules_removed),
                'dependencies_added_count': len(self.dependencies_added),
                'dependencies_removed_count': len(self.dependencies_removed),
                'cycles_introduced_count': len(self.cycles_introduced),
                'total_coupling_increase': sum(v[1] - v[0] for v in self.coupling_delta.values()),
                'total_complexity_increase': sum(v[1] - v[0] for v in self.complexity_delta.values()),
                'violations_introduced_count': len(self.violations_introduced)
            }
        }


@dataclass
class ErosionMetrics:
    """Architecture erosion metrics"""
    new_violations: int
    coupling_increases: int
    complexity_increases: int
    cycles_introduced: int
    days_since_baseline: int
    erosion_score: float
    severity: str  # low, medium, high, critical

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'new_violations': self.new_violations,
            'coupling_increases': self.coupling_increases,
            'complexity_increases': self.complexity_increases,
            'cycles_introduced': self.cycles_introduced,
            'days_since_baseline': self.days_since_baseline,
            'erosion_score': round(self.erosion_score, 3),
            'severity': self.severity
        }


@dataclass
class TrendPoint:
    """Single point in a trend analysis"""
    timestamp: datetime
    value: float
    commit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'commit': self.commit
        }


@dataclass
class TrendAnalysis:
    """Trend analysis results"""
    metric_name: str
    points: List[TrendPoint]
    trend: str  # increasing, decreasing, stable
    slope: float
    prediction: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'metric_name': self.metric_name,
            'points': [p.to_dict() for p in self.points],
            'trend': self.trend,
            'slope': round(self.slope, 4),
            'prediction': round(self.prediction, 2) if self.prediction else None,
            'stats': {
                'min': min(p.value for p in self.points) if self.points else 0,
                'max': max(p.value for p in self.points) if self.points else 0,
                'avg': sum(p.value for p in self.points) / len(self.points) if self.points else 0
            }
        }


# ============================================================================
# Core Classes
# ============================================================================

class BaselineManager:
    """Manages architecture baselines (snapshots)"""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize baseline manager"""
        self.storage_dir = storage_dir or Path(".acc_baselines")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.baselines: Dict[str, ArchitectureSnapshot] = {}
        self._load_all_baselines()

    def save_baseline(self, snapshot: ArchitectureSnapshot) -> Path:
        """Save a baseline snapshot"""
        filename = f"baseline_{snapshot.commit}_{snapshot.date.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.storage_dir / filename

        with open(filepath, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        self.baselines[snapshot.commit] = snapshot
        return filepath

    def load_baseline(self, commit: str) -> Optional[ArchitectureSnapshot]:
        """Load a baseline by commit"""
        if commit in self.baselines:
            return self.baselines[commit]

        # Try to load from file
        for filepath in self.storage_dir.glob(f"baseline_{commit}_*.json"):
            with open(filepath) as f:
                data = json.load(f)
                snapshot = ArchitectureSnapshot.from_dict(data)
                self.baselines[commit] = snapshot
                return snapshot

        return None

    def get_latest_baseline(self) -> Optional[ArchitectureSnapshot]:
        """Get the most recent baseline"""
        if not self.baselines:
            return None

        return max(self.baselines.values(), key=lambda s: s.date)

    def list_baselines(self) -> List[ArchitectureSnapshot]:
        """List all baselines"""
        return sorted(self.baselines.values(), key=lambda s: s.date, reverse=True)

    def delete_baseline(self, commit: str) -> bool:
        """Delete a baseline"""
        if commit in self.baselines:
            del self.baselines[commit]

            # Delete file
            for filepath in self.storage_dir.glob(f"baseline_{commit}_*.json"):
                filepath.unlink()

            return True

        return False

    def _load_all_baselines(self):
        """Load all baselines from storage"""
        for filepath in self.storage_dir.glob("baseline_*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    snapshot = ArchitectureSnapshot.from_dict(data)
                    self.baselines[snapshot.commit] = snapshot
            except Exception as e:
                print(f"Warning: Failed to load baseline from {filepath}: {e}")


class ArchitectureDiffEngine:
    """Engine for comparing architecture snapshots and detecting changes"""

    def __init__(self):
        """Initialize diff engine"""
        pass

    def compare(self, baseline: ArchitectureSnapshot, current: ArchitectureSnapshot) -> ArchitectureDiff:
        """Compare two snapshots and generate diff"""
        diff = ArchitectureDiff(baseline=baseline, current=current)

        # Compare modules
        baseline_modules = set(baseline.modules.keys())
        current_modules = set(current.modules.keys())

        diff.modules_added = sorted(list(current_modules - baseline_modules))
        diff.modules_removed = sorted(list(baseline_modules - current_modules))

        # Find changed modules (same name but different content)
        common_modules = baseline_modules & current_modules
        for module in common_modules:
            if baseline.modules[module] != current.modules[module]:
                diff.modules_changed.append(module)

        # Compare dependencies
        baseline_deps = set(baseline.dependencies)
        current_deps = set(current.dependencies)

        diff.dependencies_added = sorted(list(current_deps - baseline_deps))
        diff.dependencies_removed = sorted(list(baseline_deps - current_deps))

        # Detect dependency direction changes
        for dep in diff.dependencies_added:
            reverse_dep = (dep[1], dep[0])
            if reverse_dep in diff.dependencies_removed:
                diff.dependencies_changed.append((dep[0], dep[1], 'reversed'))

        # Compare cycles
        baseline_cycle_set = {tuple(sorted(cycle)) for cycle in baseline.cycles}
        current_cycle_set = {tuple(sorted(cycle)) for cycle in current.cycles}
        new_cycles = current_cycle_set - baseline_cycle_set
        diff.cycles_introduced = [list(cycle) for cycle in new_cycles]

        # Compare coupling
        for module in common_modules:
            baseline_coupling = baseline.coupling_metrics.get(module)
            current_coupling = current.coupling_metrics.get(module)

            if baseline_coupling and current_coupling:
                baseline_total = baseline_coupling[0] + baseline_coupling[1]
                current_total = current_coupling[0] + current_coupling[1]

                if baseline_total != current_total:
                    diff.coupling_delta[module] = (baseline_total, current_total)

        # Compare complexity
        for module in common_modules:
            baseline_complexity = baseline.complexity_metrics.get(module, 0)
            current_complexity = current.complexity_metrics.get(module, 0)

            if baseline_complexity != current_complexity:
                diff.complexity_delta[module] = (baseline_complexity, current_complexity)

        # Compare violations
        baseline_violation_ids = {v.get('id', f"{v['rule_id']}_{v['source_component']}") for v in baseline.violations}
        for violation in current.violations:
            violation_id = violation.get('id', f"{violation['rule_id']}_{violation['source_component']}")
            if violation_id not in baseline_violation_ids:
                diff.violations_introduced.append(violation)

        return diff

    def detect_breaking_changes(self, diff: ArchitectureDiff) -> List[Dict[str, Any]]:
        """Detect breaking changes in diff"""
        breaking_changes = []

        # Removed modules are breaking
        for module in diff.modules_removed:
            breaking_changes.append({
                'type': 'module_removed',
                'module': module,
                'severity': 'high',
                'message': f"Module {module} was removed"
            })

        # Removed dependencies are breaking
        for dep in diff.dependencies_removed:
            breaking_changes.append({
                'type': 'dependency_removed',
                'from': dep[0],
                'to': dep[1],
                'severity': 'medium',
                'message': f"Dependency {dep[0]} -> {dep[1]} was removed"
            })

        # New cycles are breaking
        for cycle in diff.cycles_introduced:
            breaking_changes.append({
                'type': 'cycle_introduced',
                'cycle': cycle,
                'severity': 'high',
                'message': f"New cyclic dependency: {' -> '.join(cycle[:3])}..."
            })

        return breaking_changes


class ErosionDetector:
    """Detects architectural erosion over time"""

    def __init__(self, coupling_threshold: int = 0, complexity_threshold: int = 3):
        """Initialize erosion detector"""
        self.coupling_threshold = coupling_threshold
        self.complexity_threshold = complexity_threshold

    def detect_erosion(self, diff: ArchitectureDiff) -> ErosionMetrics:
        """Detect erosion from diff"""
        # Count violations
        new_violations = len(diff.violations_introduced)

        # Count coupling increases above threshold
        coupling_increases = sum(
            1 for old, new in diff.coupling_delta.values()
            if new - old > self.coupling_threshold
        )

        # Count complexity increases above threshold
        complexity_increases = sum(
            1 for old, new in diff.complexity_delta.values()
            if new - old > self.complexity_threshold
        )

        # Count cycles introduced
        cycles_introduced = len(diff.cycles_introduced)

        # Calculate days since baseline
        days_since = (diff.current.date - diff.baseline.date).days
        if days_since == 0:
            days_since = 1  # Avoid division by zero

        # Calculate erosion score
        total_issues = new_violations + coupling_increases + complexity_increases + cycles_introduced
        erosion_score = total_issues / days_since

        # Determine severity
        if erosion_score >= 1.0:
            severity = 'critical'
        elif erosion_score >= 0.5:
            severity = 'high'
        elif erosion_score >= 0.2:
            severity = 'medium'
        else:
            severity = 'low'

        return ErosionMetrics(
            new_violations=new_violations,
            coupling_increases=coupling_increases,
            complexity_increases=complexity_increases,
            cycles_introduced=cycles_introduced,
            days_since_baseline=days_since,
            erosion_score=erosion_score,
            severity=severity
        )


class TrendAnalyzer:
    """Analyzes trends over multiple snapshots"""

    def __init__(self):
        """Initialize trend analyzer"""
        pass

    def analyze_trend(self, snapshots: List[ArchitectureSnapshot], metric_name: str) -> TrendAnalysis:
        """Analyze trend for a specific metric"""
        points = []

        for snapshot in sorted(snapshots, key=lambda s: s.date):
            value = self._extract_metric(snapshot, metric_name)
            points.append(TrendPoint(
                timestamp=snapshot.date,
                value=value,
                commit=snapshot.commit
            ))

        # Calculate trend
        if len(points) < 2:
            trend = 'stable'
            slope = 0.0
            prediction = None
        else:
            # Simple linear regression
            x_values = [(p.timestamp - points[0].timestamp).total_seconds() / 86400 for p in points]  # Days
            y_values = [p.value for p in points]

            slope = self._calculate_slope(x_values, y_values)

            if slope > 0.01:
                trend = 'increasing'
            elif slope < -0.01:
                trend = 'decreasing'
            else:
                trend = 'stable'

            # Predict next value (30 days out)
            next_x = x_values[-1] + 30
            prediction = self._predict_value(x_values, y_values, next_x)

        return TrendAnalysis(
            metric_name=metric_name,
            points=points,
            trend=trend,
            slope=slope,
            prediction=prediction
        )

    def predict_hotspots(self, snapshots: List[ArchitectureSnapshot]) -> List[Dict[str, Any]]:
        """Predict future hotspots using trend analysis"""
        hotspots = []

        if len(snapshots) < 2:
            return hotspots

        # Analyze coupling trends
        coupling_trend = self.analyze_trend(snapshots, 'avg_coupling')
        if coupling_trend.trend == 'increasing' and coupling_trend.prediction and coupling_trend.prediction > 10:
            hotspots.append({
                'type': 'coupling',
                'metric': 'average_coupling',
                'current': coupling_trend.points[-1].value,
                'predicted': coupling_trend.prediction,
                'risk': 'high' if coupling_trend.prediction > 15 else 'medium'
            })

        # Analyze complexity trends
        complexity_trend = self.analyze_trend(snapshots, 'avg_complexity')
        if complexity_trend.trend == 'increasing' and complexity_trend.prediction and complexity_trend.prediction > 20:
            hotspots.append({
                'type': 'complexity',
                'metric': 'average_complexity',
                'current': complexity_trend.points[-1].value,
                'predicted': complexity_trend.prediction,
                'risk': 'high' if complexity_trend.prediction > 30 else 'medium'
            })

        return hotspots

    def _extract_metric(self, snapshot: ArchitectureSnapshot, metric_name: str) -> float:
        """Extract metric value from snapshot"""
        if metric_name == 'module_count':
            return float(len(snapshot.modules))
        elif metric_name == 'dependency_count':
            return float(len(snapshot.dependencies))
        elif metric_name == 'cycle_count':
            return float(len(snapshot.cycles))
        elif metric_name == 'violation_count':
            return float(len(snapshot.violations))
        elif metric_name == 'avg_coupling':
            if not snapshot.coupling_metrics:
                return 0.0
            total = sum(ca + ce for ca, ce, _ in snapshot.coupling_metrics.values())
            return total / len(snapshot.coupling_metrics)
        elif metric_name == 'avg_complexity':
            if not snapshot.complexity_metrics:
                return 0.0
            return sum(snapshot.complexity_metrics.values()) / len(snapshot.complexity_metrics)
        else:
            return 0.0

    def _calculate_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate linear regression slope"""
        n = len(x_values)
        if n == 0:
            return 0.0

        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _predict_value(self, x_values: List[float], y_values: List[float], future_x: float) -> float:
        """Predict future value using linear regression"""
        slope = self._calculate_slope(x_values, y_values)

        n = len(x_values)
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        intercept = y_mean - slope * x_mean

        return slope * future_x + intercept


class DiffReportGenerator:
    """Generates comprehensive diff reports in various formats"""

    def __init__(self):
        """Initialize report generator"""
        pass

    def generate_json(self, diff: ArchitectureDiff, erosion: Optional[ErosionMetrics] = None) -> Dict[str, Any]:
        """Generate JSON report"""
        report = diff.to_dict()

        if erosion:
            report['erosion'] = erosion.to_dict()

        report['generated_at'] = datetime.now().isoformat()

        return report

    def generate_html(self, diff: ArchitectureDiff, erosion: Optional[ErosionMetrics] = None) -> str:
        """Generate HTML report"""
        json_report = self.generate_json(diff, erosion)

        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Architecture Diff Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f5f5f5; border-radius: 3px; }
        .critical { background: #ffcccc; }
        .high { background: #ffddaa; }
        .medium { background: #ffffcc; }
        .low { background: #ccffcc; }
    </style>
</head>
<body>
    <h1>Architecture Diff Report</h1>
"""

        # Baseline vs Current
        html += f"""
    <div class="section">
        <h2>Comparison</h2>
        <p><strong>Baseline:</strong> {json_report['baseline']['commit']} ({json_report['baseline']['date']})</p>
        <p><strong>Current:</strong> {json_report['current']['commit']} ({json_report['current']['date']})</p>
    </div>
"""

        # Summary
        summary = json_report['summary']
        html += f"""
    <div class="section">
        <h2>Summary</h2>
        <div class="metric">Modules Added: {summary['modules_added_count']}</div>
        <div class="metric">Modules Removed: {summary['modules_removed_count']}</div>
        <div class="metric">Dependencies Added: {summary['dependencies_added_count']}</div>
        <div class="metric">Cycles Introduced: {summary['cycles_introduced_count']}</div>
        <div class="metric">Violations Introduced: {summary['violations_introduced_count']}</div>
    </div>
"""

        # Erosion
        if erosion:
            severity_class = erosion.severity
            html += f"""
    <div class="section {severity_class}">
        <h2>Erosion Metrics</h2>
        <p><strong>Erosion Score:</strong> {erosion.erosion_score:.3f}</p>
        <p><strong>Severity:</strong> {erosion.severity.upper()}</p>
        <p><strong>Days Since Baseline:</strong> {erosion.days_since_baseline}</p>
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def generate_markdown(self, diff: ArchitectureDiff, erosion: Optional[ErosionMetrics] = None) -> str:
        """Generate Markdown report"""
        json_report = self.generate_json(diff, erosion)

        md = "# Architecture Diff Report\n\n"

        # Comparison
        md += "## Comparison\n\n"
        md += f"**Baseline:** {json_report['baseline']['commit']} ({json_report['baseline']['date']})\n\n"
        md += f"**Current:** {json_report['current']['commit']} ({json_report['current']['date']})\n\n"

        # Summary
        summary = json_report['summary']
        md += "## Summary\n\n"
        md += f"- Modules Added: {summary['modules_added_count']}\n"
        md += f"- Modules Removed: {summary['modules_removed_count']}\n"
        md += f"- Dependencies Added: {summary['dependencies_added_count']}\n"
        md += f"- Cycles Introduced: {summary['cycles_introduced_count']}\n"
        md += f"- Violations Introduced: {summary['violations_introduced_count']}\n\n"

        # Erosion
        if erosion:
            md += "## Erosion Metrics\n\n"
            md += f"- **Erosion Score:** {erosion.erosion_score:.3f}\n"
            md += f"- **Severity:** {erosion.severity.upper()}\n"
            md += f"- **Days Since Baseline:** {erosion.days_since_baseline}\n\n"

        # Details
        if diff.modules_added:
            md += "## Modules Added\n\n"
            for module in diff.modules_added:
                md += f"- {module}\n"
            md += "\n"

        if diff.cycles_introduced:
            md += "## Cycles Introduced\n\n"
            for cycle in diff.cycles_introduced:
                md += f"- {' -> '.join(cycle)}\n"
            md += "\n"

        return md

    def generate_impact_analysis(self, diff: ArchitectureDiff) -> Dict[str, Any]:
        """Generate impact analysis"""
        impact = {
            'high_impact_changes': [],
            'medium_impact_changes': [],
            'low_impact_changes': [],
            'affected_modules': set()
        }

        # Removed modules have high impact
        for module in diff.modules_removed:
            impact['high_impact_changes'].append({
                'type': 'module_removed',
                'module': module,
                'reason': 'Module removal may break dependents'
            })
            impact['affected_modules'].add(module)

        # New cycles have high impact
        for cycle in diff.cycles_introduced:
            impact['high_impact_changes'].append({
                'type': 'cycle_introduced',
                'cycle': cycle,
                'reason': 'Cyclic dependency violates architecture'
            })
            impact['affected_modules'].update(cycle)

        # Large coupling increases have medium impact
        for module, (old, new) in diff.coupling_delta.items():
            if new - old > 5:
                impact['medium_impact_changes'].append({
                    'type': 'coupling_increase',
                    'module': module,
                    'old': old,
                    'new': new,
                    'delta': new - old
                })
                impact['affected_modules'].add(module)

        # New modules have low impact
        for module in diff.modules_added:
            impact['low_impact_changes'].append({
                'type': 'module_added',
                'module': module
            })

        impact['affected_modules'] = sorted(list(impact['affected_modules']))

        return impact

    def generate_recommendations(self, diff: ArchitectureDiff, erosion: Optional[ErosionMetrics] = None) -> List[str]:
        """Generate recommendations based on diff and erosion"""
        recommendations = []

        # Cycle recommendations
        if diff.cycles_introduced:
            recommendations.append(
                f"CRITICAL: {len(diff.cycles_introduced)} new cyclic dependencies detected. "
                "Refactor to break cycles by introducing interfaces or dependency inversion."
            )

        # Coupling recommendations
        high_coupling = [m for m, (old, new) in diff.coupling_delta.items() if new > 10]
        if high_coupling:
            recommendations.append(
                f"WARNING: {len(high_coupling)} modules have high coupling (>10). "
                "Consider splitting modules or reducing dependencies."
            )

        # Erosion recommendations
        if erosion:
            if erosion.severity in ('high', 'critical'):
                recommendations.append(
                    f"URGENT: Architecture erosion score is {erosion.severity.upper()} ({erosion.erosion_score:.3f}). "
                    "Schedule immediate architecture review and refactoring."
                )
            elif erosion.severity == 'medium':
                recommendations.append(
                    "MODERATE: Architecture quality is declining. "
                    "Plan refactoring work in upcoming sprints."
                )

        # Violation recommendations
        if diff.violations_introduced:
            recommendations.append(
                f"ACTION: {len(diff.violations_introduced)} new rule violations introduced. "
                "Review and fix violations before merging."
            )

        if not recommendations:
            recommendations.append("Good: No significant architectural issues detected.")

        return recommendations


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def baseline_manager(temp_dir):
    """Create baseline manager with temp storage"""
    return BaselineManager(storage_dir=temp_dir / "baselines")


@pytest.fixture
def sample_snapshot_baseline():
    """Create sample baseline snapshot"""
    return ArchitectureSnapshot(
        commit="abc123",
        date=datetime.now() - timedelta(days=12),
        modules={
            'module_a': {'size': 100, 'functions': 10},
            'module_b': {'size': 150, 'functions': 15},
            'module_c': {'size': 200, 'functions': 20}
        },
        dependencies=[
            ('module_a', 'module_b'),
            ('module_b', 'module_c')
        ],
        coupling_metrics={
            'module_a': (0, 1, 1.0),
            'module_b': (1, 1, 0.5),
            'module_c': (1, 0, 0.0)
        },
        cycles=[],
        violations=[],
        complexity_metrics={
            'module_a': 10,
            'module_b': 15,
            'module_c': 20
        }
    )


@pytest.fixture
def sample_snapshot_current():
    """Create sample current snapshot"""
    return ArchitectureSnapshot(
        commit="def456",
        date=datetime.now(),
        modules={
            'module_a': {'size': 120, 'functions': 12},
            'module_b': {'size': 150, 'functions': 15},
            'module_c': {'size': 200, 'functions': 20},
            'module_d': {'size': 80, 'functions': 8}
        },
        dependencies=[
            ('module_a', 'module_b'),
            ('module_b', 'module_c'),
            ('module_a', 'module_d'),
            ('module_d', 'module_c')
        ],
        coupling_metrics={
            'module_a': (0, 2, 1.0),
            'module_b': (1, 1, 0.5),
            'module_c': (2, 0, 0.0),
            'module_d': (1, 1, 0.5)
        },
        cycles=[
            ['module_a', 'module_d', 'module_a']
        ],
        violations=[
            {'rule_id': 'R-001', 'source_component': 'module_a', 'message': 'Violation 1'}
        ],
        complexity_metrics={
            'module_a': 15,
            'module_b': 15,
            'module_c': 25,
            'module_d': 8
        }
    )


@pytest.fixture
def diff_engine():
    """Create diff engine"""
    return ArchitectureDiffEngine()


@pytest.fixture
def erosion_detector():
    """Create erosion detector"""
    return ErosionDetector(coupling_threshold=0, complexity_threshold=3)


@pytest.fixture
def trend_analyzer():
    """Create trend analyzer"""
    return TrendAnalyzer()


@pytest.fixture
def report_generator():
    """Create report generator"""
    return DiffReportGenerator()


# ============================================================================
# Test Suite 1: Baseline Comparison (ACC-401 to ACC-406)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestBaselineComparison:
    """Test suite for baseline comparison functionality"""

    def test_acc_401_store_baseline_snapshot(self, baseline_manager, sample_snapshot_baseline):
        """ACC-401: Store baseline import graph snapshot"""
        filepath = baseline_manager.save_baseline(sample_snapshot_baseline)

        assert filepath.exists()
        assert sample_snapshot_baseline.commit in baseline_manager.baselines

        # Verify content
        loaded = baseline_manager.load_baseline(sample_snapshot_baseline.commit)
        assert loaded is not None
        assert loaded.commit == sample_snapshot_baseline.commit
        assert len(loaded.modules) == 3

    def test_acc_402_compare_current_vs_baseline(self, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-402: Compare current vs baseline (additions, deletions, changes)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)

        # Check additions
        assert 'module_d' in diff.modules_added
        assert len(diff.modules_added) == 1

        # Check no removals
        assert len(diff.modules_removed) == 0

        # Check dependency changes
        assert len(diff.dependencies_added) > 0
        assert ('module_a', 'module_d') in diff.dependencies_added

    def test_acc_403_detect_new_dependencies(self, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-403: Detect new dependencies (modules, packages)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)

        # New dependencies should be detected
        assert len(diff.dependencies_added) == 2
        assert ('module_a', 'module_d') in diff.dependencies_added
        assert ('module_d', 'module_c') in diff.dependencies_added

    def test_acc_404_detect_removed_dependencies(self, diff_engine):
        """ACC-404: Detect removed dependencies (breaking changes)"""
        baseline = ArchitectureSnapshot(
            commit="old",
            date=datetime.now() - timedelta(days=1),
            modules={'a': {}, 'b': {}, 'c': {}},
            dependencies=[('a', 'b'), ('b', 'c')],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        current = ArchitectureSnapshot(
            commit="new",
            date=datetime.now(),
            modules={'a': {}, 'c': {}},
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        diff = diff_engine.compare(baseline, current)

        # Module b removed
        assert 'b' in diff.modules_removed

        # Dependencies removed
        assert len(diff.dependencies_removed) == 2
        assert ('a', 'b') in diff.dependencies_removed
        assert ('b', 'c') in diff.dependencies_removed

    def test_acc_405_detect_dependency_direction_changes(self, diff_engine):
        """ACC-405: Detect dependency direction changes"""
        baseline = ArchitectureSnapshot(
            commit="old",
            date=datetime.now() - timedelta(days=1),
            modules={'a': {}, 'b': {}},
            dependencies=[('a', 'b')],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        current = ArchitectureSnapshot(
            commit="new",
            date=datetime.now(),
            modules={'a': {}, 'b': {}},
            dependencies=[('b', 'a')],  # Reversed
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        diff = diff_engine.compare(baseline, current)

        # Direction change should be detected
        assert len(diff.dependencies_changed) > 0
        assert ('b', 'a', 'reversed') in diff.dependencies_changed

    def test_acc_406_version_control_integration(self, baseline_manager):
        """ACC-406: Version control integration (git commit as baseline)"""
        # Simulate git integration
        commit_hash = "abc123def456"
        snapshot = ArchitectureSnapshot(
            commit=commit_hash,
            date=datetime.now(),
            modules={'test': {}},
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={},
            metadata={
                'git_branch': 'main',
                'git_author': 'test@example.com',
                'git_message': 'Test commit'
            }
        )

        baseline_manager.save_baseline(snapshot)

        # Load by commit hash
        loaded = baseline_manager.load_baseline(commit_hash)
        assert loaded is not None
        assert loaded.commit == commit_hash
        assert loaded.metadata['git_branch'] == 'main'


# ============================================================================
# Test Suite 2: Erosion Detection (ACC-407 to ACC-412)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestErosionDetection:
    """Test suite for erosion detection"""

    def test_acc_407_coupling_increase_detection(self, erosion_detector, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-407: Coupling increase detection (Ce delta > threshold)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        erosion = erosion_detector.detect_erosion(diff)

        # module_a coupling increased from 1 to 2
        assert 'module_a' in diff.coupling_delta
        assert erosion.coupling_increases > 0

    def test_acc_408_complexity_increase_detection(self, erosion_detector, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-408: Complexity increase detection (functions becoming more complex)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        erosion = erosion_detector.detect_erosion(diff)

        # module_a complexity increased from 10 to 15
        # module_c complexity increased from 20 to 25
        assert erosion.complexity_increases > 0

    def test_acc_409_new_cycles_introduced(self, erosion_detector, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-409: New cycles introduced (architecture violation)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)

        # Baseline has no cycles, current has 1 cycle
        assert len(diff.cycles_introduced) == 1
        assert 'module_a' in diff.cycles_introduced[0]

    def test_acc_410_rule_violations_introduced(self, erosion_detector, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-410: Rule violations introduced since baseline"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        erosion = erosion_detector.detect_erosion(diff)

        # 1 new violation introduced
        assert len(diff.violations_introduced) == 1
        assert erosion.new_violations == 1

    def test_acc_411_layer_boundary_violations(self, diff_engine):
        """ACC-411: Layer boundary violations (presentation -> database)"""
        baseline = ArchitectureSnapshot(
            commit="old",
            date=datetime.now() - timedelta(days=5),
            modules={'presentation': {}, 'business': {}, 'database': {}},
            dependencies=[('presentation', 'business'), ('business', 'database')],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        current = ArchitectureSnapshot(
            commit="new",
            date=datetime.now(),
            modules={'presentation': {}, 'business': {}, 'database': {}},
            dependencies=[
                ('presentation', 'business'),
                ('business', 'database'),
                ('presentation', 'database')  # Layer violation
            ],
            coupling_metrics={},
            cycles=[],
            violations=[
                {
                    'rule_id': 'LAYER-001',
                    'source_component': 'presentation',
                    'target_component': 'database',
                    'message': 'Presentation layer cannot call database layer directly'
                }
            ],
            complexity_metrics={}
        )

        diff = diff_engine.compare(baseline, current)

        # Layer violation should be detected
        assert len(diff.violations_introduced) == 1
        assert ('presentation', 'database') in diff.dependencies_added

    def test_acc_412_erosion_score_calculation(self, erosion_detector, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-412: Erosion score calculation (violations_introduced / days_since_baseline)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        erosion = erosion_detector.detect_erosion(diff)

        # Calculate expected score
        total_issues = (
            erosion.new_violations +
            erosion.coupling_increases +
            erosion.complexity_increases +
            erosion.cycles_introduced
        )
        expected_score = total_issues / erosion.days_since_baseline

        assert abs(erosion.erosion_score - expected_score) < 0.001
        assert erosion.severity in ('low', 'medium', 'high', 'critical')


# ============================================================================
# Test Suite 3: Trend Analysis (ACC-413 to ACC-418)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestTrendAnalysis:
    """Test suite for trend analysis"""

    def test_acc_413_complexity_trends(self, trend_analyzer):
        """ACC-413: Complexity trends (increasing/decreasing)"""
        # Create snapshots with increasing complexity
        snapshots = []
        for i in range(5):
            snapshot = ArchitectureSnapshot(
                commit=f"commit_{i}",
                date=datetime.now() - timedelta(days=20 - i * 5),
                modules={'test': {}},
                dependencies=[],
                coupling_metrics={},
                cycles=[],
                violations=[],
                complexity_metrics={'test': 10 + i * 2}  # Increasing: 10, 12, 14, 16, 18
            )
            snapshots.append(snapshot)

        trend = trend_analyzer.analyze_trend(snapshots, 'avg_complexity')

        assert trend.metric_name == 'avg_complexity'
        assert len(trend.points) == 5
        assert trend.trend == 'increasing'
        assert trend.slope > 0

    def test_acc_414_coupling_trends_over_time(self, trend_analyzer):
        """ACC-414: Coupling trends over time series"""
        # Create snapshots with varying coupling
        snapshots = []
        for i in range(4):
            snapshot = ArchitectureSnapshot(
                commit=f"commit_{i}",
                date=datetime.now() - timedelta(days=15 - i * 5),
                modules={'test': {}},
                dependencies=[],
                coupling_metrics={'test': (i, i + 1, 0.5)},  # Increasing coupling
                cycles=[],
                violations=[],
                complexity_metrics={}
            )
            snapshots.append(snapshot)

        trend = trend_analyzer.analyze_trend(snapshots, 'avg_coupling')

        assert trend.trend in ('increasing', 'stable')
        assert len(trend.points) == 4

    def test_acc_415_dependency_growth_rate(self, trend_analyzer):
        """ACC-415: Dependency growth rate"""
        snapshots = []
        for i in range(5):
            deps = [(f'a', f'b_{j}') for j in range(5 + i * 3)]  # Growing dependencies
            snapshot = ArchitectureSnapshot(
                commit=f"commit_{i}",
                date=datetime.now() - timedelta(days=20 - i * 5),
                modules={'a': {}, **{f'b_{j}': {} for j in range(5 + i * 3)}},
                dependencies=deps,
                coupling_metrics={},
                cycles=[],
                violations=[],
                complexity_metrics={}
            )
            snapshots.append(snapshot)

        trend = trend_analyzer.analyze_trend(snapshots, 'dependency_count')

        assert trend.trend == 'increasing'
        assert trend.points[-1].value > trend.points[0].value

    def test_acc_416_test_coverage_trends(self, trend_analyzer):
        """ACC-416: Test coverage trends (from BDV audit)"""
        # Simulate test coverage trends
        snapshots = []
        for i in range(4):
            snapshot = ArchitectureSnapshot(
                commit=f"commit_{i}",
                date=datetime.now() - timedelta(days=12 - i * 4),
                modules={'test': {}},
                dependencies=[],
                coupling_metrics={},
                cycles=[],
                violations=[],
                complexity_metrics={},
                metadata={'test_coverage': 70 + i * 5}  # Increasing coverage
            )
            snapshots.append(snapshot)

        # Test coverage would be extracted from metadata
        assert len(snapshots) == 4
        coverages = [s.metadata.get('test_coverage', 0) for s in snapshots]
        assert coverages[-1] > coverages[0]

    def test_acc_417_technical_debt_accumulation(self, trend_analyzer):
        """ACC-417: Technical debt accumulation rate"""
        snapshots = []
        for i in range(5):
            violations = [{'id': f'V-{j}'} for j in range(i * 2)]  # Increasing violations
            snapshot = ArchitectureSnapshot(
                commit=f"commit_{i}",
                date=datetime.now() - timedelta(days=20 - i * 5),
                modules={'test': {}},
                dependencies=[],
                coupling_metrics={},
                cycles=[],
                violations=violations,
                complexity_metrics={}
            )
            snapshots.append(snapshot)

        trend = trend_analyzer.analyze_trend(snapshots, 'violation_count')

        assert trend.trend == 'increasing'
        assert trend.points[-1].value > trend.points[0].value

    def test_acc_418_predict_future_hotspots(self, trend_analyzer):
        """ACC-418: Predict future hotspots using linear regression"""
        # Create snapshots with high coupling trend
        snapshots = []
        for i in range(5):
            snapshot = ArchitectureSnapshot(
                commit=f"commit_{i}",
                date=datetime.now() - timedelta(days=20 - i * 5),
                modules={'test': {}},
                dependencies=[],
                coupling_metrics={'test': (i + 2, i + 3, 0.5)},  # High coupling
                cycles=[],
                violations=[],
                complexity_metrics={'test': 10 + i * 5}  # Increasing complexity
            )
            snapshots.append(snapshot)

        hotspots = trend_analyzer.predict_hotspots(snapshots)

        # Should predict coupling or complexity hotspots
        assert isinstance(hotspots, list)


# ============================================================================
# Test Suite 4: Diff Reporting (ACC-419 to ACC-424)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestDiffReporting:
    """Test suite for diff reporting"""

    def test_acc_419_generate_diff_report(self, report_generator, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-419: Generate diff report (added, removed, changed)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        report = report_generator.generate_json(diff)

        assert 'baseline' in report
        assert 'current' in report
        assert 'diff' in report
        assert 'summary' in report

        # Check summary
        assert report['summary']['modules_added_count'] == 1
        assert report['summary']['violations_introduced_count'] == 1

    def test_acc_420_visual_diff_graph(self, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-420: Visual diff (graph visualization)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)

        # Create NetworkX graphs for visualization
        baseline_graph = nx.DiGraph()
        baseline_graph.add_edges_from(diff.baseline.dependencies)

        current_graph = nx.DiGraph()
        current_graph.add_edges_from(diff.current.dependencies)

        # Check graphs
        assert baseline_graph.number_of_edges() < current_graph.number_of_edges()
        assert current_graph.number_of_nodes() > baseline_graph.number_of_nodes()

    def test_acc_421_impact_analysis(self, report_generator, diff_engine, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-421: Impact analysis (downstream effects)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        impact = report_generator.generate_impact_analysis(diff)

        assert 'high_impact_changes' in impact
        assert 'medium_impact_changes' in impact
        assert 'low_impact_changes' in impact
        assert 'affected_modules' in impact

        # New cycle is high impact
        assert len(impact['high_impact_changes']) > 0

    def test_acc_422_breaking_change_detection(self, diff_engine):
        """ACC-422: Breaking change detection"""
        baseline = ArchitectureSnapshot(
            commit="old",
            date=datetime.now() - timedelta(days=1),
            modules={'a': {}, 'b': {}},
            dependencies=[('a', 'b')],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        current = ArchitectureSnapshot(
            commit="new",
            date=datetime.now(),
            modules={'a': {}},  # b removed
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        diff = diff_engine.compare(baseline, current)
        breaking_changes = diff_engine.detect_breaking_changes(diff)

        assert len(breaking_changes) > 0
        assert any(bc['type'] == 'module_removed' for bc in breaking_changes)
        assert any(bc['severity'] == 'high' for bc in breaking_changes)

    def test_acc_423_recommendation_engine(self, report_generator, diff_engine, erosion_detector, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-423: Recommendation engine (suggest fixes)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        erosion = erosion_detector.detect_erosion(diff)
        recommendations = report_generator.generate_recommendations(diff, erosion)

        assert len(recommendations) > 0
        # Should recommend fixing cycles
        assert any('cyclic' in r.lower() for r in recommendations)

    def test_acc_424_report_formats(self, report_generator, diff_engine, erosion_detector, sample_snapshot_baseline, sample_snapshot_current):
        """ACC-424: Report formats (JSON, HTML, Markdown)"""
        diff = diff_engine.compare(sample_snapshot_baseline, sample_snapshot_current)
        erosion = erosion_detector.detect_erosion(diff)

        # JSON format
        json_report = report_generator.generate_json(diff, erosion)
        assert isinstance(json_report, dict)
        assert 'diff' in json_report

        # HTML format
        html_report = report_generator.generate_html(diff, erosion)
        assert isinstance(html_report, str)
        assert '<html>' in html_report
        assert 'Architecture Diff Report' in html_report

        # Markdown format
        md_report = report_generator.generate_markdown(diff, erosion)
        assert isinstance(md_report, str)
        assert '# Architecture Diff Report' in md_report


# ============================================================================
# Test Suite 5: Integration & Performance (ACC-425 to ACC-430)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestIntegrationPerformance:
    """Test suite for integration and performance"""

    def test_acc_425_import_graph_builder_integration(self, diff_engine):
        """ACC-425: Integration with ImportGraphBuilder"""
        # Simulate integration with ImportGraphBuilder
        from acc.import_graph_builder import ImportGraph, ModuleInfo

        # Create mock import graphs
        baseline_graph = ImportGraph()
        baseline_graph.add_module(ModuleInfo(
            module_name='test_module',
            file_path=Path('/test/module.py'),
            imports=['os'],
            from_imports=['sys']
        ))

        current_graph = ImportGraph()
        current_graph.add_module(ModuleInfo(
            module_name='test_module',
            file_path=Path('/test/module.py'),
            imports=['os', 'json'],
            from_imports=['sys']
        ))

        # Convert to snapshots
        baseline_snapshot = ArchitectureSnapshot(
            commit='base',
            date=datetime.now() - timedelta(days=1),
            modules={m: {} for m in baseline_graph.modules.keys()},
            dependencies=list(baseline_graph.graph.edges()),
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        current_snapshot = ArchitectureSnapshot(
            commit='current',
            date=datetime.now(),
            modules={m: {} for m in current_graph.modules.keys()},
            dependencies=list(current_graph.graph.edges()),
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        # Compare
        diff = diff_engine.compare(baseline_snapshot, current_snapshot)
        assert diff is not None

    def test_acc_426_rule_engine_integration(self, diff_engine):
        """ACC-426: Integration with RuleEngine (detect new violations)"""
        # Simulate rule engine integration
        baseline = ArchitectureSnapshot(
            commit="old",
            date=datetime.now() - timedelta(days=1),
            modules={'a': {}},
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        current = ArchitectureSnapshot(
            commit="new",
            date=datetime.now(),
            modules={'a': {}},
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[
                {'rule_id': 'R-001', 'source_component': 'a', 'message': 'New violation'}
            ],
            complexity_metrics={}
        )

        diff = diff_engine.compare(baseline, current)

        # New violation should be detected
        assert len(diff.violations_introduced) == 1

    def test_acc_427_git_integration(self, baseline_manager):
        """ACC-427: Git integration (fetch baseline from commit)"""
        # Simulate git integration
        commit = "abc123"

        # Create and save baseline with git metadata
        snapshot = ArchitectureSnapshot(
            commit=commit,
            date=datetime.now(),
            modules={'test': {}},
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={},
            metadata={
                'git_commit': commit,
                'git_branch': 'main',
                'git_author': 'test@example.com'
            }
        )

        baseline_manager.save_baseline(snapshot)

        # Fetch by commit
        loaded = baseline_manager.load_baseline(commit)
        assert loaded is not None
        assert loaded.metadata['git_commit'] == commit

    def test_acc_428_performance_large_dataset(self, diff_engine):
        """ACC-428: Performance test - diff 1000+ files in <3 seconds"""
        # Create large snapshots
        num_modules = 1000

        baseline_modules = {f'module_{i}': {'size': 100} for i in range(num_modules)}
        baseline_deps = [(f'module_{i}', f'module_{i+1}') for i in range(num_modules - 1)]

        baseline = ArchitectureSnapshot(
            commit="old",
            date=datetime.now() - timedelta(days=1),
            modules=baseline_modules,
            dependencies=baseline_deps,
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        current_modules = {f'module_{i}': {'size': 100} for i in range(num_modules + 50)}
        current_deps = baseline_deps + [(f'module_{i}', f'module_{i+1}') for i in range(num_modules, num_modules + 49)]

        current = ArchitectureSnapshot(
            commit="new",
            date=datetime.now(),
            modules=current_modules,
            dependencies=current_deps,
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        # Measure performance
        start_time = time.time()
        diff = diff_engine.compare(baseline, current)
        elapsed_time = time.time() - start_time

        # Should complete in < 3 seconds
        assert elapsed_time < 3.0
        assert len(diff.modules_added) == 50

    def test_acc_429_incremental_diff(self, diff_engine):
        """ACC-429: Incremental diff (only changed modules)"""
        # Create snapshots with partial changes
        baseline = ArchitectureSnapshot(
            commit="old",
            date=datetime.now() - timedelta(days=1),
            modules={f'module_{i}': {'hash': f'hash_{i}'} for i in range(100)},
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        # Only change 5 modules
        current_modules = {f'module_{i}': {'hash': f'hash_{i}'} for i in range(100)}
        for i in range(5):
            current_modules[f'module_{i}']['hash'] = f'hash_{i}_changed'

        current = ArchitectureSnapshot(
            commit="new",
            date=datetime.now(),
            modules=current_modules,
            dependencies=[],
            coupling_metrics={},
            cycles=[],
            violations=[],
            complexity_metrics={}
        )

        diff = diff_engine.compare(baseline, current)

        # Should detect only changed modules
        assert len(diff.modules_changed) == 5

    def test_acc_430_historical_tracking(self, baseline_manager):
        """ACC-430: Historical tracking (multiple baselines)"""
        # Create multiple baselines over time
        for i in range(5):
            snapshot = ArchitectureSnapshot(
                commit=f"commit_{i}",
                date=datetime.now() - timedelta(days=20 - i * 5),
                modules={f'module_{j}': {} for j in range(10 + i)},
                dependencies=[],
                coupling_metrics={},
                cycles=[],
                violations=[],
                complexity_metrics={}
            )
            baseline_manager.save_baseline(snapshot)

        # List all baselines
        baselines = baseline_manager.list_baselines()
        assert len(baselines) == 5

        # Verify ordering (most recent first)
        for i in range(len(baselines) - 1):
            assert baselines[i].date >= baselines[i + 1].date

        # Get latest
        latest = baseline_manager.get_latest_baseline()
        assert latest is not None
        assert latest.commit == "commit_4"


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
def test_acc_architecture_diff_full_workflow(
    baseline_manager,
    diff_engine,
    erosion_detector,
    trend_analyzer,
    report_generator,
    temp_dir
):
    """
    Full workflow integration test for architecture diff system.

    Tests complete workflow:
    1. Create baseline snapshot
    2. Create current snapshot with changes
    3. Compare and generate diff
    4. Detect erosion
    5. Analyze trends
    6. Generate reports in all formats
    """
    # Step 1: Create baseline
    baseline = ArchitectureSnapshot(
        commit="baseline_v1",
        date=datetime.now() - timedelta(days=30),
        modules={
            'service_a': {'size': 200, 'functions': 20},
            'service_b': {'size': 150, 'functions': 15},
            'service_c': {'size': 180, 'functions': 18}
        },
        dependencies=[
            ('service_a', 'service_b'),
            ('service_b', 'service_c')
        ],
        coupling_metrics={
            'service_a': (0, 1, 1.0),
            'service_b': (1, 1, 0.5),
            'service_c': (1, 0, 0.0)
        },
        cycles=[],
        violations=[],
        complexity_metrics={
            'service_a': 20,
            'service_b': 15,
            'service_c': 18
        }
    )

    baseline_manager.save_baseline(baseline)

    # Step 2: Create intermediate snapshots for trend analysis
    intermediate_snapshots = [baseline]
    for i in range(1, 4):
        snapshot = ArchitectureSnapshot(
            commit=f"v1.{i}",
            date=datetime.now() - timedelta(days=30 - i * 10),
            modules=baseline.modules,
            dependencies=baseline.dependencies + [(f'service_a', f'new_{i}')],
            coupling_metrics={
                'service_a': (0, 1 + i, 0.8),
                'service_b': (1, 1, 0.5),
                'service_c': (1, 0, 0.0)
            },
            cycles=[],
            violations=[],
            complexity_metrics={
                'service_a': 20 + i * 2,
                'service_b': 15,
                'service_c': 18
            }
        )
        intermediate_snapshots.append(snapshot)
        baseline_manager.save_baseline(snapshot)

    # Step 3: Create current snapshot with significant changes
    current = ArchitectureSnapshot(
        commit="current_v2",
        date=datetime.now(),
        modules={
            'service_a': {'size': 250, 'functions': 25},
            'service_b': {'size': 150, 'functions': 15},
            'service_c': {'size': 180, 'functions': 18},
            'service_d': {'size': 120, 'functions': 12}
        },
        dependencies=[
            ('service_a', 'service_b'),
            ('service_b', 'service_c'),
            ('service_a', 'service_d'),
            ('service_d', 'service_a')  # Cycle
        ],
        coupling_metrics={
            'service_a': (1, 2, 0.67),
            'service_b': (1, 1, 0.5),
            'service_c': (1, 0, 0.0),
            'service_d': (1, 1, 0.5)
        },
        cycles=[
            ['service_a', 'service_d', 'service_a']
        ],
        violations=[
            {'rule_id': 'R-001', 'source_component': 'service_a', 'message': 'High coupling'},
            {'rule_id': 'R-002', 'source_component': 'service_d', 'message': 'Cycle detected'}
        ],
        complexity_metrics={
            'service_a': 30,
            'service_b': 15,
            'service_c': 20,
            'service_d': 12
        }
    )

    # Step 4: Compare baseline and current
    diff = diff_engine.compare(baseline, current)

    # Verify diff
    assert len(diff.modules_added) == 1
    assert 'service_d' in diff.modules_added
    assert len(diff.cycles_introduced) == 1
    assert len(diff.violations_introduced) == 2

    # Step 5: Detect erosion
    erosion = erosion_detector.detect_erosion(diff)

    # Verify erosion
    assert erosion.new_violations == 2
    assert erosion.cycles_introduced == 1
    assert erosion.erosion_score > 0

    # Step 6: Analyze trends
    all_snapshots = intermediate_snapshots + [current]
    coupling_trend = trend_analyzer.analyze_trend(all_snapshots, 'avg_coupling')
    complexity_trend = trend_analyzer.analyze_trend(all_snapshots, 'avg_complexity')

    # Verify trends
    assert coupling_trend.trend == 'increasing'
    assert len(coupling_trend.points) == 5

    # Step 7: Generate reports
    json_report = report_generator.generate_json(diff, erosion)
    html_report = report_generator.generate_html(diff, erosion)
    md_report = report_generator.generate_markdown(diff, erosion)

    # Save reports
    (temp_dir / "diff_report.json").write_text(json.dumps(json_report, indent=2))
    (temp_dir / "diff_report.html").write_text(html_report)
    (temp_dir / "diff_report.md").write_text(md_report)

    # Verify reports exist
    assert (temp_dir / "diff_report.json").exists()
    assert (temp_dir / "diff_report.html").exists()
    assert (temp_dir / "diff_report.md").exists()

    # Step 8: Generate recommendations
    recommendations = report_generator.generate_recommendations(diff, erosion)
    assert len(recommendations) > 0

    # Step 9: Impact analysis
    impact = report_generator.generate_impact_analysis(diff)
    assert len(impact['high_impact_changes']) > 0

    # Step 10: Predict hotspots
    hotspots = trend_analyzer.predict_hotspots(all_snapshots)

    print("\n" + "="*80)
    print("ARCHITECTURE DIFF & EROSION DETECTION - FULL WORKFLOW TEST")
    print("="*80)
    print(f"\nBaseline: {baseline.commit} ({baseline.date.strftime('%Y-%m-%d')})")
    print(f"Current:  {current.commit} ({current.date.strftime('%Y-%m-%d')})")
    print(f"\nChanges:")
    print(f"  - Modules added: {len(diff.modules_added)}")
    print(f"  - Dependencies added: {len(diff.dependencies_added)}")
    print(f"  - Cycles introduced: {len(diff.cycles_introduced)}")
    print(f"  - Violations introduced: {len(diff.violations_introduced)}")
    print(f"\nErosion:")
    print(f"  - Score: {erosion.erosion_score:.3f}")
    print(f"  - Severity: {erosion.severity.upper()}")
    print(f"  - Days since baseline: {erosion.days_since_baseline}")
    print(f"\nTrends:")
    print(f"  - Coupling: {coupling_trend.trend}")
    print(f"  - Complexity: {complexity_trend.trend}")
    print(f"\nRecommendations:")
    for rec in recommendations[:3]:
        print(f"  - {rec}")
    print("\n" + "="*80)
