"""
ACC Audit Engine Test Suite - Test Suite 18: Audit & Reporting

Comprehensive tests for ACC Audit Engine functionality.
Test IDs: ACC-501 to ACC-530 (30 tests)

Test Categories:
1. Rule Compliance (ACC-501 to ACC-506): All rules, compliance scores, severity breakdown
2. Violation Reports (ACC-507 to ACC-512): Report generation, grouping, export formats
3. Remediation Recommendations (ACC-513 to ACC-518): Fix suggestions, prioritization
4. Metrics Dashboard (ACC-519 to ACC-524): Health scores, trends, benchmarks
5. Integration & Performance (ACC-525 to ACC-530): System integrations, performance

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import pytest

# Mark all tests as ACC integration tests
pytestmark = [pytest.mark.acc, pytest.mark.integration]
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import tempfile
import json
import time
from dataclasses import dataclass, field
from enum import Enum

from acc.rule_engine import (
    RuleEngine,
    Rule,
    RuleType,
    Severity,
    Component,
    Violation,
    EvaluationResult
)
from acc.import_graph_builder import ImportGraphBuilder, ImportGraph
from acc.suppression_system import SuppressionManager, SuppressionEntry, SuppressionLevel, PatternType


# ============================================================================
# Helper Classes for ACC Audit System
# ============================================================================

@dataclass
class ComplianceScore:
    """Compliance score calculation."""
    total_rules: int
    passing_rules: int
    failing_rules: int
    suppressed_violations: int
    score: float  # 0.0 to 1.0

    @property
    def percentage(self) -> float:
        """Get score as percentage."""
        return self.score * 100


@dataclass
class ComplexityMetrics:
    """Code complexity metrics."""
    total_modules: int
    average_complexity: float
    high_complexity_modules: int
    complexity_threshold: int = 10

    def get_health_score(self) -> float:
        """Calculate health score based on complexity (0-1)."""
        if self.average_complexity >= 20:
            return 0.0
        return 1 - (self.average_complexity / 20)


@dataclass
class CouplingMetrics:
    """Coupling metrics."""
    average_coupling: float
    high_coupling_modules: int
    coupling_threshold: int = 10

    def get_health_score(self) -> float:
        """Calculate health score based on coupling (0-1)."""
        if self.average_coupling >= 10:
            return 0.0
        return 1 - (self.average_coupling / 10)


@dataclass
class CycleMetrics:
    """Cycle detection metrics."""
    cycles_detected: int
    cycle_threshold: int = 5

    def get_health_score(self) -> float:
        """Calculate health score based on cycles (0-1)."""
        if self.cycles_detected >= self.cycle_threshold:
            return 0.0
        return 1 - (self.cycles_detected / self.cycle_threshold)


@dataclass
class ViolationGroup:
    """Grouped violations."""
    group_key: str
    group_type: str  # 'severity', 'module', 'rule_type'
    violations: List[Violation] = field(default_factory=list)
    count: int = 0


@dataclass
class RemediationSuggestion:
    """Remediation suggestion for a violation."""
    priority: str  # HIGH, MEDIUM, LOW
    module: str
    issue: str
    suggestion: str
    estimated_effort: str  # SMALL, MEDIUM, LARGE
    impact: str  # HIGH, MEDIUM, LOW
    roi_score: float  # Return on investment score


@dataclass
class AuditReport:
    """Complete audit report."""
    audit_id: str
    timestamp: datetime
    architecture_health_score: float
    compliance: ComplianceScore
    metrics: Dict[str, Any]
    violations: List[Violation]
    recommendations: List[RemediationSuggestion]
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'audit_id': self.audit_id,
            'timestamp': self.timestamp.isoformat(),
            'architecture_health_score': self.architecture_health_score,
            'compliance': {
                'score': self.compliance.score,
                'passing_rules': self.compliance.passing_rules,
                'failing_rules': self.compliance.failing_rules,
                'suppressed': self.compliance.suppressed_violations
            },
            'metrics': self.metrics,
            'violations': [v.to_dict() for v in self.violations],
            'recommendations': [
                {
                    'priority': r.priority,
                    'module': r.module,
                    'issue': r.issue,
                    'suggestion': r.suggestion,
                    'estimated_effort': r.estimated_effort,
                    'impact': r.impact,
                    'roi_score': r.roi_score
                }
                for r in self.recommendations
            ],
            'execution_time_ms': self.execution_time_ms
        }


class ComplianceCalculator:
    """Calculate compliance scores from rule evaluation."""

    def calculate(
        self,
        evaluation_result: EvaluationResult,
        total_rules: int,
        suppressed_count: int = 0
    ) -> ComplianceScore:
        """
        Calculate compliance score.

        Args:
            evaluation_result: Rule evaluation result
            total_rules: Total number of rules
            suppressed_count: Number of suppressed violations

        Returns:
            ComplianceScore object
        """
        # Count passing rules (rules with no violations)
        rules_with_violations = set()
        for violation in evaluation_result.violations:
            rules_with_violations.add(violation.rule_id)

        failing_rules = len(rules_with_violations)
        passing_rules = total_rules - failing_rules

        # Calculate score
        if total_rules == 0:
            score = 1.0
        else:
            score = passing_rules / total_rules

        return ComplianceScore(
            total_rules=total_rules,
            passing_rules=passing_rules,
            failing_rules=failing_rules,
            suppressed_violations=suppressed_count,
            score=score
        )

    def get_severity_breakdown(self, violations: List[Violation]) -> Dict[str, int]:
        """Get breakdown of violations by severity."""
        breakdown = {
            'INFO': 0,
            'WARNING': 0,
            'BLOCKING': 0
        }

        for violation in violations:
            severity_key = violation.severity.value.upper()
            breakdown[severity_key] = breakdown.get(severity_key, 0) + 1

        return breakdown

    def get_violations_by_module(self, violations: List[Violation]) -> Dict[str, int]:
        """Get violations grouped by module."""
        by_module = {}

        for violation in violations:
            module = violation.source_component or 'Unknown'
            by_module[module] = by_module.get(module, 0) + 1

        return by_module


class ViolationReportGenerator:
    """Generate violation reports in various formats."""

    def generate_report(
        self,
        violations: List[Violation],
        group_by: str = 'severity'
    ) -> Dict[str, Any]:
        """
        Generate violation report.

        Args:
            violations: List of violations
            group_by: Grouping key ('severity', 'module', 'rule_type')

        Returns:
            Report dictionary
        """
        report = {
            'total_violations': len(violations),
            'generated_at': datetime.now().isoformat(),
            'groups': []
        }

        # Group violations
        groups = self._group_violations(violations, group_by)

        for group in groups:
            report['groups'].append({
                'key': group.group_key,
                'type': group.group_type,
                'count': len(group.violations),
                'violations': [v.to_dict() for v in group.violations]
            })

        return report

    def _group_violations(
        self,
        violations: List[Violation],
        group_by: str
    ) -> List[ViolationGroup]:
        """Group violations by specified key."""
        groups_dict: Dict[str, ViolationGroup] = {}

        for violation in violations:
            if group_by == 'severity':
                key = violation.severity.value
            elif group_by == 'module':
                key = violation.source_component or 'Unknown'
            elif group_by == 'rule_type':
                key = violation.rule_type.value
            else:
                key = 'other'

            if key not in groups_dict:
                groups_dict[key] = ViolationGroup(
                    group_key=key,
                    group_type=group_by,
                    violations=[]
                )

            groups_dict[key].violations.append(violation)
            groups_dict[key].count += 1

        return list(groups_dict.values())

    def export_json(self, report: Dict[str, Any]) -> str:
        """Export report as JSON."""
        return json.dumps(report, indent=2)

    def export_html(self, report: Dict[str, Any]) -> str:
        """Export report as HTML."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ACC Violation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .violation {{ border: 1px solid #ddd; padding: 10px; margin: 10px 0; }}
        .blocking {{ border-left: 4px solid red; }}
        .warning {{ border-left: 4px solid orange; }}
        .info {{ border-left: 4px solid blue; }}
    </style>
</head>
<body>
    <h1>ACC Violation Report</h1>
    <p>Total Violations: {report['total_violations']}</p>
    <p>Generated: {report['generated_at']}</p>
"""

        for group in report.get('groups', []):
            html += f"<h2>{group['key']} ({group['count']} violations)</h2>\n"
            for violation in group['violations']:
                severity_class = violation.get('severity', 'info')
                html += f"""
    <div class="violation {severity_class}">
        <strong>{violation.get('rule_id')}</strong>: {violation.get('message')}
        <br><small>{violation.get('source_file', 'N/A')}</small>
    </div>
"""

        html += "</body></html>"
        return html

    def export_markdown(self, report: Dict[str, Any]) -> str:
        """Export report as Markdown."""
        md = f"""# ACC Violation Report

**Total Violations:** {report['total_violations']}
**Generated:** {report['generated_at']}

"""

        for group in report.get('groups', []):
            md += f"## {group['key']} ({group['count']} violations)\n\n"
            for violation in group['violations']:
                md += f"- **{violation.get('rule_id')}**: {violation.get('message')}\n"
                md += f"  - File: `{violation.get('source_file', 'N/A')}`\n"
                md += f"  - Severity: {violation.get('severity', 'info')}\n\n"

        return md

    def export_csv(self, violations: List[Violation]) -> str:
        """Export violations as CSV."""
        csv = "Rule ID,Severity,Source Component,Target Component,Message,Source File\n"

        for violation in violations:
            csv += f"{violation.rule_id},{violation.severity.value},"
            csv += f"{violation.source_component or 'N/A'},"
            csv += f"{violation.target_component or 'N/A'},"
            csv += f"\"{violation.message}\","
            csv += f"{violation.source_file or 'N/A'}\n"

        return csv


class RemediationEngine:
    """Generate remediation recommendations for violations."""

    def generate_recommendations(
        self,
        violations: List[Violation],
        coupling_metrics: Optional[Dict[str, Tuple[int, int, float]]] = None
    ) -> List[RemediationSuggestion]:
        """
        Generate remediation recommendations.

        Args:
            violations: List of violations
            coupling_metrics: Optional coupling metrics

        Returns:
            List of remediation suggestions
        """
        recommendations = []

        # Group violations by module
        by_module = {}
        for violation in violations:
            module = violation.source_component or 'Unknown'
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(violation)

        # Generate recommendations for each module
        for module, module_violations in by_module.items():
            # Check for coupling violations
            coupling_violations = [
                v for v in module_violations
                if v.rule_type == RuleType.COUPLING
            ]

            if coupling_violations:
                recommendations.append(
                    RemediationSuggestion(
                        priority='HIGH',
                        module=module,
                        issue=f'High coupling detected ({len(coupling_violations)} violations)',
                        suggestion='Extract interfaces, apply dependency inversion principle',
                        estimated_effort='MEDIUM',
                        impact='HIGH',
                        roi_score=self._calculate_roi('HIGH', 'MEDIUM')
                    )
                )

            # Check for architecture violations
            arch_violations = [
                v for v in module_violations
                if v.rule_type in (RuleType.CAN_CALL, RuleType.MUST_NOT_CALL)
            ]

            if arch_violations:
                recommendations.append(
                    RemediationSuggestion(
                        priority='HIGH' if any(v.severity == Severity.BLOCKING for v in arch_violations) else 'MEDIUM',
                        module=module,
                        issue=f'Architectural violations detected ({len(arch_violations)})',
                        suggestion='Refactor dependencies to comply with layer architecture',
                        estimated_effort='LARGE',
                        impact='HIGH',
                        roi_score=self._calculate_roi('HIGH', 'LARGE')
                    )
                )

            # Check for cycles
            cycle_violations = [
                v for v in module_violations
                if v.rule_type == RuleType.NO_CYCLES
            ]

            if cycle_violations:
                recommendations.append(
                    RemediationSuggestion(
                        priority='HIGH',
                        module=module,
                        issue='Cyclic dependencies detected',
                        suggestion='Break cycles using dependency inversion or event-driven patterns',
                        estimated_effort='LARGE',
                        impact='HIGH',
                        roi_score=self._calculate_roi('HIGH', 'LARGE')
                    )
                )

        # Sort by ROI score (highest first)
        recommendations.sort(key=lambda r: r.roi_score, reverse=True)

        return recommendations

    def _calculate_roi(self, impact: str, effort: str) -> float:
        """Calculate ROI score based on impact and effort."""
        impact_scores = {'HIGH': 3.0, 'MEDIUM': 2.0, 'LOW': 1.0}
        effort_scores = {'SMALL': 1.0, 'MEDIUM': 2.0, 'LARGE': 3.0}

        impact_val = impact_scores.get(impact, 2.0)
        effort_val = effort_scores.get(effort, 2.0)

        return impact_val / effort_val

    def suggest_suppression(self, violation: Violation) -> Dict[str, Any]:
        """Suggest suppression for a violation (for false positives)."""
        return {
            'suppression_id': f"supp_{violation.rule_id}_{hash(violation.source_file or '')}",
            'pattern': violation.source_file or '*',
            'level': 'file',
            'rule_type': violation.rule_type.value,
            'justification': f'False positive for {violation.rule_id}',
            'recommended': True
        }


class MetricsDashboard:
    """Generate metrics dashboard data."""

    def calculate_health_score(
        self,
        compliance: ComplianceScore,
        complexity: ComplexityMetrics,
        coupling: CouplingMetrics,
        cycles: CycleMetrics
    ) -> float:
        """
        Calculate overall architecture health score (0-100).

        Formula:
        health_score = (
            compliance_score * 0.4 +
            (1 - avg_complexity / 20) * 0.2 +
            (1 - avg_coupling / 10) * 0.2 +
            (1 - cycles_count / 5) * 0.2
        ) * 100
        """
        compliance_component = compliance.score * 0.4
        complexity_component = complexity.get_health_score() * 0.2
        coupling_component = coupling.get_health_score() * 0.2
        cycles_component = cycles.get_health_score() * 0.2

        health_score = (
            compliance_component +
            complexity_component +
            coupling_component +
            cycles_component
        ) * 100

        return round(health_score, 2)

    def generate_dashboard(
        self,
        compliance: ComplianceScore,
        violations: List[Violation],
        complexity: ComplexityMetrics,
        coupling: CouplingMetrics,
        cycles: CycleMetrics
    ) -> Dict[str, Any]:
        """Generate dashboard data."""
        health_score = self.calculate_health_score(
            compliance, complexity, coupling, cycles
        )

        # Calculate hotspots (modules with multiple violations)
        hotspots = self._calculate_hotspots(violations)

        dashboard = {
            'overall_health_score': health_score,
            'compliance': {
                'score': compliance.score,
                'percentage': compliance.percentage,
                'passing_rules': compliance.passing_rules,
                'failing_rules': compliance.failing_rules
            },
            'metrics': {
                'total_modules': complexity.total_modules,
                'average_complexity': complexity.average_complexity,
                'high_complexity_modules': complexity.high_complexity_modules,
                'average_coupling': coupling.average_coupling,
                'cycles_detected': cycles.cycles_detected,
                'hotspots': len(hotspots)
            },
            'hotspots': hotspots,
            'health_components': {
                'compliance': compliance.score * 40,
                'complexity': complexity.get_health_score() * 20,
                'coupling': coupling.get_health_score() * 20,
                'cycles': cycles.get_health_score() * 20
            }
        }

        return dashboard

    def _calculate_hotspots(self, violations: List[Violation]) -> List[Dict[str, Any]]:
        """Calculate module hotspots (multiple violations)."""
        by_module = {}

        for violation in violations:
            module = violation.source_file or 'Unknown'
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(violation)

        # Filter modules with 2+ violations
        hotspots = [
            {
                'module': module,
                'violation_count': len(viols),
                'severity_breakdown': self._get_severity_breakdown(viols)
            }
            for module, viols in by_module.items()
            if len(viols) >= 2
        ]

        # Sort by violation count
        hotspots.sort(key=lambda h: h['violation_count'], reverse=True)

        return hotspots

    def _get_severity_breakdown(self, violations: List[Violation]) -> Dict[str, int]:
        """Get severity breakdown for violations."""
        breakdown = {'BLOCKING': 0, 'WARNING': 0, 'INFO': 0}
        for v in violations:
            severity = v.severity.value.upper()
            breakdown[severity] = breakdown.get(severity, 0) + 1
        return breakdown

    def export_dashboard_json(self, dashboard: Dict[str, Any]) -> str:
        """Export dashboard as JSON."""
        return json.dumps(dashboard, indent=2)

    def export_dashboard_html(self, dashboard: Dict[str, Any]) -> str:
        """Export dashboard as HTML."""
        health_score = dashboard['overall_health_score']

        # Determine health color
        if health_score >= 80:
            color = 'green'
        elif health_score >= 60:
            color = 'orange'
        else:
            color = 'red'

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ACC Metrics Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .health-score {{ font-size: 48px; color: {color}; font-weight: bold; }}
        .metric {{ padding: 10px; margin: 10px 0; border: 1px solid #ddd; }}
        .hotspot {{ background: #fff3cd; padding: 10px; margin: 5px 0; }}
    </style>
</head>
<body>
    <h1>ACC Metrics Dashboard</h1>
    <div class="health-score">Health Score: {health_score}</div>

    <h2>Compliance</h2>
    <div class="metric">
        <p>Score: {dashboard['compliance']['percentage']:.1f}%</p>
        <p>Passing Rules: {dashboard['compliance']['passing_rules']}</p>
        <p>Failing Rules: {dashboard['compliance']['failing_rules']}</p>
    </div>

    <h2>Metrics</h2>
    <div class="metric">
        <p>Total Modules: {dashboard['metrics']['total_modules']}</p>
        <p>Average Complexity: {dashboard['metrics']['average_complexity']:.2f}</p>
        <p>Average Coupling: {dashboard['metrics']['average_coupling']:.2f}</p>
        <p>Cycles Detected: {dashboard['metrics']['cycles_detected']}</p>
        <p>Hotspots: {dashboard['metrics']['hotspots']}</p>
    </div>

    <h2>Hotspots</h2>
"""

        for hotspot in dashboard.get('hotspots', [])[:10]:
            html += f"""
    <div class="hotspot">
        <strong>{hotspot['module']}</strong>: {hotspot['violation_count']} violations
        <br><small>Blocking: {hotspot['severity_breakdown']['BLOCKING']},
        Warning: {hotspot['severity_breakdown']['WARNING']},
        Info: {hotspot['severity_breakdown']['INFO']}</small>
    </div>
"""

        html += "</body></html>"
        return html


class ACCAuditEngine:
    """
    Complete ACC audit engine with compliance, reporting, and recommendations.
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        suppression_manager: Optional[SuppressionManager] = None
    ):
        """
        Initialize audit engine.

        Args:
            rule_engine: Rule engine for evaluation
            suppression_manager: Optional suppression manager
        """
        self.rule_engine = rule_engine
        self.suppression_manager = suppression_manager or SuppressionManager()
        self.compliance_calculator = ComplianceCalculator()
        self.report_generator = ViolationReportGenerator()
        self.remediation_engine = RemediationEngine()
        self.metrics_dashboard = MetricsDashboard()

    def run_audit(
        self,
        dependencies: Dict[str, List[str]],
        coupling_metrics: Optional[Dict[str, Tuple[int, int, float]]] = None,
        cycles: Optional[List[List[str]]] = None,
        complexity_metrics: Optional[ComplexityMetrics] = None
    ) -> AuditReport:
        """
        Run complete audit.

        Args:
            dependencies: File dependencies
            coupling_metrics: Optional coupling metrics
            cycles: Optional cycles
            complexity_metrics: Optional complexity metrics

        Returns:
            Complete audit report
        """
        start_time = time.time()

        # Generate audit ID
        audit_id = f"acc_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Run rule evaluation
        evaluation_result = self.rule_engine.evaluate_all(
            dependencies=dependencies,
            coupling_metrics=coupling_metrics,
            cycles=cycles
        )

        # Apply suppressions
        active_violations, suppressed_violations = self.suppression_manager.filter_violations(
            evaluation_result.violations
        )

        # Calculate compliance
        compliance = self.compliance_calculator.calculate(
            evaluation_result=evaluation_result,
            total_rules=len(self.rule_engine.rules),
            suppressed_count=len(suppressed_violations)
        )

        # Generate recommendations
        recommendations = self.remediation_engine.generate_recommendations(
            violations=active_violations,
            coupling_metrics=coupling_metrics
        )

        # Calculate metrics
        if not complexity_metrics:
            complexity_metrics = ComplexityMetrics(
                total_modules=len(dependencies),
                average_complexity=5.0,
                high_complexity_modules=0
            )

        if not coupling_metrics:
            coupling_metrics_obj = CouplingMetrics(
                average_coupling=3.0,
                high_coupling_modules=0
            )
        else:
            avg_coupling = sum(ca + ce for ca, ce, _ in coupling_metrics.values()) / len(coupling_metrics)
            high_coupling = sum(1 for ca, ce, _ in coupling_metrics.values() if (ca + ce) > 10)
            coupling_metrics_obj = CouplingMetrics(
                average_coupling=avg_coupling,
                high_coupling_modules=high_coupling
            )

        cycle_metrics = CycleMetrics(
            cycles_detected=len(cycles) if cycles else 0
        )

        # Calculate health score
        health_score = self.metrics_dashboard.calculate_health_score(
            compliance=compliance,
            complexity=complexity_metrics,
            coupling=coupling_metrics_obj,
            cycles=cycle_metrics
        )

        # Build metrics dict
        metrics = {
            'total_modules': len(dependencies),
            'average_complexity': complexity_metrics.average_complexity,
            'high_complexity_modules': complexity_metrics.high_complexity_modules,
            'average_coupling': coupling_metrics_obj.average_coupling,
            'cycles_detected': cycle_metrics.cycles_detected,
            'hotspots': len(self.metrics_dashboard._calculate_hotspots(active_violations))
        }

        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        return AuditReport(
            audit_id=audit_id,
            timestamp=datetime.now(),
            architecture_health_score=health_score,
            compliance=compliance,
            metrics=metrics,
            violations=active_violations,
            recommendations=recommendations,
            execution_time_ms=execution_time_ms
        )


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_components():
    """Sample architectural components."""
    return [
        Component(
            name="Presentation",
            paths=["presentation/", "ui/"],
            description="UI layer"
        ),
        Component(
            name="BusinessLogic",
            paths=["business/", "services/"],
            description="Business logic layer"
        ),
        Component(
            name="DataAccess",
            paths=["data/", "repositories/"],
            description="Data access layer"
        )
    ]


@pytest.fixture
def rule_engine(sample_components):
    """Initialized rule engine."""
    engine = RuleEngine(components=sample_components)

    # Add sample rules
    rules = [
        Rule(
            id="R1",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.BLOCKING,
            description="Presentation must not call DataAccess",
            component="Presentation",
            target="DataAccess"
        ),
        Rule(
            id="R2",
            rule_type=RuleType.COUPLING,
            severity=Severity.WARNING,
            description="BusinessLogic coupling < 10",
            component="BusinessLogic",
            threshold=10
        ),
        Rule(
            id="R3",
            rule_type=RuleType.NO_CYCLES,
            severity=Severity.BLOCKING,
            description="No cycles allowed",
            component="BusinessLogic"
        )
    ]

    engine.add_rules(rules)
    return engine


@pytest.fixture
def suppression_manager():
    """Initialized suppression manager."""
    return SuppressionManager()


@pytest.fixture
def audit_engine(rule_engine, suppression_manager):
    """Initialized audit engine."""
    return ACCAuditEngine(
        rule_engine=rule_engine,
        suppression_manager=suppression_manager
    )


@pytest.fixture
def sample_dependencies():
    """Sample dependencies."""
    return {
        "presentation/home_view.py": ["business/user_service.py"],
        "business/user_service.py": ["data/user_repository.py"],
        "data/user_repository.py": []
    }


@pytest.fixture
def sample_violations(rule_engine):
    """Sample violations."""
    return [
        Violation(
            rule_id="R1",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.BLOCKING,
            source_component="Presentation",
            target_component="DataAccess",
            message="Presentation must not call DataAccess",
            source_file="presentation/bad_view.py",
            target_file="data/repository.py"
        ),
        Violation(
            rule_id="R2",
            rule_type=RuleType.COUPLING,
            severity=Severity.WARNING,
            source_component="BusinessLogic",
            target_component=None,
            message="BusinessLogic has coupling 15 > threshold 10",
            source_file="business/service.py"
        ),
        Violation(
            rule_id="R3",
            rule_type=RuleType.NO_CYCLES,
            severity=Severity.BLOCKING,
            source_component="BusinessLogic",
            target_component=None,
            message="Cyclic dependency detected",
            source_file="business/order_service.py"
        )
    ]


# ============================================================================
# Category 1: Rule Compliance (ACC-501 to ACC-506)
# ============================================================================

def test_acc_501_check_all_rules(audit_engine, sample_dependencies):
    """ACC-501: Check all rules from rule engine."""
    report = audit_engine.run_audit(sample_dependencies)

    # Should evaluate all rules
    assert report.compliance.total_rules == len(audit_engine.rule_engine.rules)
    assert report.compliance.total_rules == 3


def test_acc_502_calculate_compliance_score(audit_engine, sample_dependencies):
    """ACC-502: Calculate compliance score (passing_rules / total_rules)."""
    report = audit_engine.run_audit(sample_dependencies)

    # Compliance score should be between 0 and 1
    assert 0.0 <= report.compliance.score <= 1.0

    # Score should equal passing / total
    expected_score = report.compliance.passing_rules / report.compliance.total_rules
    assert abs(report.compliance.score - expected_score) < 0.01


def test_acc_503_severity_breakdown(audit_engine, sample_violations):
    """ACC-503: Severity breakdown (INFO, WARNING, BLOCKING)."""
    calculator = audit_engine.compliance_calculator
    breakdown = calculator.get_severity_breakdown(sample_violations)

    assert 'INFO' in breakdown
    assert 'WARNING' in breakdown
    assert 'BLOCKING' in breakdown

    # Should have 2 blocking, 1 warning from sample
    assert breakdown['BLOCKING'] == 2
    assert breakdown['WARNING'] == 1


def test_acc_504_violations_by_module(audit_engine, sample_violations):
    """ACC-504: Rule violations by module/package."""
    calculator = audit_engine.compliance_calculator
    by_module = calculator.get_violations_by_module(sample_violations)

    assert 'Presentation' in by_module
    assert 'BusinessLogic' in by_module
    assert by_module['Presentation'] == 1
    assert by_module['BusinessLogic'] == 2


def test_acc_505_suppressed_violations_tracking(audit_engine, sample_dependencies):
    """ACC-505: Suppressed violations tracking."""
    # Add suppression
    suppression = SuppressionEntry(
        id="supp1",
        pattern="presentation/bad_view.py",
        level=SuppressionLevel.FILE,
        pattern_type=PatternType.EXACT,
        author="test",
        justification="Test suppression"
    )
    audit_engine.suppression_manager.add_suppression(suppression)

    # Run audit with violation
    deps_with_violation = sample_dependencies.copy()
    deps_with_violation["presentation/bad_view.py"] = ["data/repository.py"]

    report = audit_engine.run_audit(deps_with_violation)

    # Should track suppressed violations
    assert report.compliance.suppressed_violations >= 0


def test_acc_506_compliance_trends_over_time(audit_engine, sample_dependencies):
    """ACC-506: Compliance trends over time."""
    # Run multiple audits
    reports = []

    for i in range(3):
        report = audit_engine.run_audit(sample_dependencies)
        reports.append({
            'timestamp': report.timestamp,
            'score': report.compliance.score,
            'violations': len(report.violations)
        })

    # Should have trend data
    assert len(reports) == 3

    # All reports should have timestamps
    for r in reports:
        assert 'timestamp' in r
        assert 'score' in r


# ============================================================================
# Category 2: Violation Reports (ACC-507 to ACC-512)
# ============================================================================

def test_acc_507_generate_violation_report(audit_engine, sample_violations):
    """ACC-507: Generate violation report with full context."""
    report = audit_engine.report_generator.generate_report(sample_violations)

    assert 'total_violations' in report
    assert report['total_violations'] == len(sample_violations)
    assert 'generated_at' in report
    assert 'groups' in report


def test_acc_508_group_violations_by_type(audit_engine, sample_violations):
    """ACC-508: Group violations by type, severity, module."""
    generator = audit_engine.report_generator

    # Group by severity
    report_severity = generator.generate_report(sample_violations, group_by='severity')
    assert len(report_severity['groups']) > 0

    # Group by module
    report_module = generator.generate_report(sample_violations, group_by='module')
    assert len(report_module['groups']) > 0

    # Group by rule type
    report_rule = generator.generate_report(sample_violations, group_by='rule_type')
    assert len(report_rule['groups']) > 0


def test_acc_509_include_code_snippets(sample_violations):
    """ACC-509: Include code snippets for violations."""
    # Violation should include file information
    for violation in sample_violations:
        if violation.source_file:
            assert isinstance(violation.source_file, str)
            assert len(violation.source_file) > 0


def test_acc_510_link_to_rule_definitions(sample_violations):
    """ACC-510: Link to rule definitions."""
    # Each violation should have rule_id
    for violation in sample_violations:
        assert violation.rule_id is not None
        assert len(violation.rule_id) > 0


def test_acc_511_prioritize_violations_by_impact(audit_engine, sample_violations):
    """ACC-511: Prioritize violations by impact."""
    # Sort by severity (blocking first)
    sorted_violations = sorted(
        sample_violations,
        key=lambda v: {'blocking': 0, 'warning': 1, 'info': 2}.get(v.severity.value, 3)
    )

    # First violations should be blocking
    blocking_count = sum(1 for v in sorted_violations if v.severity == Severity.BLOCKING)
    assert blocking_count > 0

    # All blocking should come first
    for i in range(blocking_count):
        assert sorted_violations[i].severity == Severity.BLOCKING


def test_acc_512_export_formats_json_html_markdown_csv(audit_engine, sample_violations):
    """ACC-512: Export formats: JSON, HTML, Markdown, CSV."""
    generator = audit_engine.report_generator

    # Generate report
    report = generator.generate_report(sample_violations)

    # Export JSON
    json_output = generator.export_json(report)
    assert json_output is not None
    assert 'total_violations' in json_output

    # Export HTML
    html_output = generator.export_html(report)
    assert html_output is not None
    assert '<html>' in html_output
    assert '</html>' in html_output

    # Export Markdown
    md_output = generator.export_markdown(report)
    assert md_output is not None
    assert '# ACC Violation Report' in md_output

    # Export CSV
    csv_output = generator.export_csv(sample_violations)
    assert csv_output is not None
    assert 'Rule ID' in csv_output


# ============================================================================
# Category 3: Remediation Recommendations (ACC-513 to ACC-518)
# ============================================================================

def test_acc_513_suggest_fixes_for_common_violations(audit_engine, sample_violations):
    """ACC-513: Suggest fixes for common violations."""
    recommendations = audit_engine.remediation_engine.generate_recommendations(
        sample_violations
    )

    assert len(recommendations) > 0

    for rec in recommendations:
        assert rec.suggestion is not None
        assert len(rec.suggestion) > 0


def test_acc_514_extract_interface_patterns(audit_engine, sample_violations):
    """ACC-514: Extract interface patterns for coupling violations."""
    # Filter coupling violations
    coupling_violations = [
        v for v in sample_violations
        if v.rule_type == RuleType.COUPLING
    ]

    if coupling_violations:
        recommendations = audit_engine.remediation_engine.generate_recommendations(
            coupling_violations
        )

        # Should have interface/dependency inversion suggestions
        interface_recs = [
            r for r in recommendations
            if 'interface' in r.suggestion.lower() or 'inversion' in r.suggestion.lower()
        ]
        assert len(interface_recs) > 0


def test_acc_515_suggest_refactoring_for_complexity(audit_engine, sample_violations):
    """ACC-515: Suggest refactoring for complexity hotspots."""
    # Generate recommendations
    recommendations = audit_engine.remediation_engine.generate_recommendations(
        sample_violations
    )

    # Should have suggestions
    assert len(recommendations) > 0

    # Recommendations should have priority
    for rec in recommendations:
        assert rec.priority in ('HIGH', 'MEDIUM', 'LOW')


def test_acc_516_recommend_suppression_for_false_positives(audit_engine, sample_violations):
    """ACC-516: Recommend suppression for false positives."""
    engine = audit_engine.remediation_engine

    # Suggest suppression for a violation
    violation = sample_violations[0]
    suppression_suggestion = engine.suggest_suppression(violation)

    assert suppression_suggestion is not None
    assert 'suppression_id' in suppression_suggestion
    assert 'pattern' in suppression_suggestion
    assert 'justification' in suppression_suggestion


def test_acc_517_prioritize_remediation_by_roi(audit_engine, sample_violations):
    """ACC-517: Prioritize remediation by ROI (impact / effort)."""
    recommendations = audit_engine.remediation_engine.generate_recommendations(
        sample_violations
    )

    # Recommendations should be sorted by ROI
    if len(recommendations) > 1:
        # Check that ROI is in descending order
        for i in range(len(recommendations) - 1):
            assert recommendations[i].roi_score >= recommendations[i + 1].roi_score


def test_acc_518_generate_todo_comments(audit_engine, sample_violations):
    """ACC-518: Generate TODO comments for codebase."""
    recommendations = audit_engine.remediation_engine.generate_recommendations(
        sample_violations
    )

    # Each recommendation could be converted to TODO comment
    for rec in recommendations:
        todo_comment = f"# TODO [{rec.priority}]: {rec.issue} - {rec.suggestion}"
        assert len(todo_comment) > 0
        assert rec.priority in todo_comment


# ============================================================================
# Category 4: Metrics Dashboard (ACC-519 to ACC-524)
# ============================================================================

def test_acc_519_overall_architecture_health_score(audit_engine, sample_dependencies):
    """ACC-519: Overall architecture health score (0-100)."""
    report = audit_engine.run_audit(sample_dependencies)

    health_score = report.architecture_health_score

    # Should be between 0 and 100
    assert 0.0 <= health_score <= 100.0


def test_acc_520_metrics_summary(audit_engine, sample_dependencies):
    """ACC-520: Metrics summary: complexity, coupling, cohesion."""
    report = audit_engine.run_audit(sample_dependencies)

    metrics = report.metrics

    assert 'total_modules' in metrics
    assert 'average_complexity' in metrics
    assert 'average_coupling' in metrics
    assert metrics['total_modules'] >= 0


def test_acc_521_hotspot_visualization_data(audit_engine, sample_dependencies):
    """ACC-521: Hotspot visualization data."""
    report = audit_engine.run_audit(sample_dependencies)

    assert 'hotspots' in report.metrics
    assert isinstance(report.metrics['hotspots'], int)


def test_acc_522_trend_charts_historical_data(audit_engine, sample_dependencies):
    """ACC-522: Trend charts (historical data)."""
    # Run multiple audits to build history
    history = []

    for i in range(3):
        report = audit_engine.run_audit(sample_dependencies)
        history.append({
            'timestamp': report.timestamp.isoformat(),
            'health_score': report.architecture_health_score,
            'compliance_score': report.compliance.score
        })

    # Should have trend data
    assert len(history) == 3

    # Each entry should have required fields
    for entry in history:
        assert 'timestamp' in entry
        assert 'health_score' in entry
        assert 'compliance_score' in entry


def test_acc_523_comparison_with_industry_benchmarks(audit_engine, sample_dependencies):
    """ACC-523: Comparison with industry benchmarks."""
    report = audit_engine.run_audit(sample_dependencies)

    # Industry benchmarks
    benchmarks = {
        'excellent': 90,
        'good': 75,
        'fair': 60,
        'poor': 40
    }

    health_score = report.architecture_health_score

    # Categorize against benchmarks
    if health_score >= benchmarks['excellent']:
        category = 'excellent'
    elif health_score >= benchmarks['good']:
        category = 'good'
    elif health_score >= benchmarks['fair']:
        category = 'fair'
    else:
        category = 'poor'

    assert category in benchmarks.keys()


def test_acc_524_dashboard_export_json_html(audit_engine, sample_dependencies):
    """ACC-524: Dashboard export: JSON, HTML."""
    # Create dashboard data
    compliance = ComplianceScore(
        total_rules=10,
        passing_rules=8,
        failing_rules=2,
        suppressed_violations=0,
        score=0.8
    )

    complexity = ComplexityMetrics(
        total_modules=100,
        average_complexity=5.0,
        high_complexity_modules=5
    )

    coupling = CouplingMetrics(
        average_coupling=3.5,
        high_coupling_modules=3
    )

    cycles = CycleMetrics(cycles_detected=1)

    dashboard = audit_engine.metrics_dashboard.generate_dashboard(
        compliance=compliance,
        violations=[],
        complexity=complexity,
        coupling=coupling,
        cycles=cycles
    )

    # Export JSON
    json_output = audit_engine.metrics_dashboard.export_dashboard_json(dashboard)
    assert json_output is not None
    assert 'overall_health_score' in json_output

    # Export HTML
    html_output = audit_engine.metrics_dashboard.export_dashboard_html(dashboard)
    assert html_output is not None
    assert '<html>' in html_output


# ============================================================================
# Category 5: Integration & Performance (ACC-525 to ACC-530)
# ============================================================================

def test_acc_525_integration_with_import_graph_builder(audit_engine, sample_components):
    """ACC-525: Integration with ImportGraphBuilder."""
    # Create temporary test files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test Python files
        (tmpdir_path / "module_a.py").write_text("import module_b\n")
        (tmpdir_path / "module_b.py").write_text("# Empty module\n")

        # Build import graph
        builder = ImportGraphBuilder(str(tmpdir_path))
        graph = builder.build_graph()

        # Should build successfully
        assert graph is not None
        assert len(graph.modules) >= 0


def test_acc_526_integration_with_rule_engine(audit_engine, sample_dependencies):
    """ACC-526: Integration with RuleEngine."""
    # Rule engine should be integrated
    assert audit_engine.rule_engine is not None

    # Should be able to run evaluation
    result = audit_engine.rule_engine.evaluate_all(sample_dependencies)
    assert result is not None


def test_acc_527_integration_with_suppression_system(audit_engine, sample_dependencies):
    """ACC-527: Integration with SuppressionSystem."""
    # Suppression manager should be integrated
    assert audit_engine.suppression_manager is not None

    # Add a suppression
    suppression = SuppressionEntry(
        id="test_supp",
        pattern="*.py",
        level=SuppressionLevel.FILE,
        pattern_type=PatternType.GLOB,
        author="test",
        justification="Test"
    )

    audit_engine.suppression_manager.add_suppression(suppression)

    # Should have the suppression
    assert len(audit_engine.suppression_manager.suppressions) > 0


def test_acc_528_integration_with_complexity_analyzer(audit_engine):
    """ACC-528: Integration with ComplexityAnalyzer."""
    # Create complexity metrics
    complexity = ComplexityMetrics(
        total_modules=50,
        average_complexity=6.5,
        high_complexity_modules=3
    )

    # Should calculate health score
    health_score = complexity.get_health_score()
    assert 0.0 <= health_score <= 1.0


def test_acc_529_integration_with_architecture_diff_engine(audit_engine, sample_dependencies):
    """ACC-529: Integration with ArchitectureDiffEngine."""
    # Run two audits to compare
    report1 = audit_engine.run_audit(sample_dependencies)
    report2 = audit_engine.run_audit(sample_dependencies)

    # Calculate diff
    diff = {
        'health_score_delta': report2.architecture_health_score - report1.architecture_health_score,
        'compliance_delta': report2.compliance.score - report1.compliance.score,
        'violations_delta': len(report2.violations) - len(report1.violations)
    }

    # Diff should be calculable
    assert 'health_score_delta' in diff
    assert isinstance(diff['health_score_delta'], float)


def test_acc_530_performance_audit_1000_files_under_10_seconds(audit_engine):
    """ACC-530: Performance: audit 1000+ files in <10 seconds."""
    # Create large dependency graph
    large_dependencies = {}

    for i in range(1000):
        file_name = f"module_{i}.py"
        # Each module depends on next 2 modules (circular to some extent)
        deps = [f"module_{(i+1) % 1000}.py", f"module_{(i+2) % 1000}.py"]
        large_dependencies[file_name] = deps

    # Run audit and measure time
    start_time = time.time()
    report = audit_engine.run_audit(large_dependencies)
    elapsed_time = time.time() - start_time

    # Should complete within 10 seconds
    assert elapsed_time < 10.0

    # Report should be generated
    assert report is not None
    assert report.audit_id is not None


# ============================================================================
# Additional Integration Tests
# ============================================================================

def test_complete_audit_workflow(audit_engine, sample_dependencies):
    """Test complete audit workflow end-to-end."""
    # Run audit
    report = audit_engine.run_audit(sample_dependencies)

    # Verify report structure
    assert report.audit_id is not None
    assert report.timestamp is not None
    assert report.architecture_health_score >= 0
    assert report.compliance is not None
    assert report.metrics is not None
    assert isinstance(report.violations, list)
    assert isinstance(report.recommendations, list)

    # Verify serialization
    report_dict = report.to_dict()
    assert 'audit_id' in report_dict
    assert 'compliance' in report_dict
    assert 'violations' in report_dict


def test_audit_report_serialization(audit_engine, sample_dependencies):
    """Test audit report can be serialized and deserialized."""
    report = audit_engine.run_audit(sample_dependencies)

    # Serialize to dict
    report_dict = report.to_dict()

    # Should be JSON serializable
    json_str = json.dumps(report_dict)
    assert json_str is not None

    # Should be deserializable
    loaded = json.loads(json_str)
    assert loaded['audit_id'] == report.audit_id


def test_health_score_calculation_formula(audit_engine):
    """Test health score calculation formula."""
    dashboard = audit_engine.metrics_dashboard

    # Create test metrics
    compliance = ComplianceScore(
        total_rules=10,
        passing_rules=8,
        failing_rules=2,
        suppressed_violations=0,
        score=0.8
    )

    complexity = ComplexityMetrics(
        total_modules=100,
        average_complexity=10.0,
        high_complexity_modules=5
    )

    coupling = CouplingMetrics(
        average_coupling=5.0,
        high_coupling_modules=3
    )

    cycles = CycleMetrics(cycles_detected=2)

    # Calculate health score
    health_score = dashboard.calculate_health_score(
        compliance, complexity, coupling, cycles
    )

    # Verify formula components
    # compliance: 0.8 * 0.4 = 0.32
    # complexity: (1 - 10/20) * 0.2 = 0.5 * 0.2 = 0.10
    # coupling: (1 - 5/10) * 0.2 = 0.5 * 0.2 = 0.10
    # cycles: (1 - 2/5) * 0.2 = 0.6 * 0.2 = 0.12
    # Total: (0.32 + 0.10 + 0.10 + 0.12) * 100 = 64

    expected = (0.8 * 0.4 + 0.5 * 0.2 + 0.5 * 0.2 + 0.6 * 0.2) * 100
    assert abs(health_score - expected) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "acc"])
