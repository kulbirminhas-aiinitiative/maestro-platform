"""
Tri-Modal Test Suite: Failure Diagnosis & Recommendations
Test Range: TRI-101 to TRI-135 (35 tests)

This test suite implements comprehensive failure diagnosis including:
- Root cause analysis across DDE, BDV, ACC streams
- Cross-stream correlation and pattern detection
- Actionable recommendation generation with ROI calculation
- Failure pattern detection and clustering
- Integration with all audit streams
- Performance benchmarks for large-scale diagnosis

Test Categories:
1. Root Cause Analysis (TRI-101 to TRI-107): 7 tests
2. Cross-Stream Correlation (TRI-108 to TRI-114): 7 tests
3. Recommendation Engine (TRI-115 to TRI-121): 7 tests
4. Failure Patterns (TRI-122 to TRI-128): 7 tests
5. Integration & Performance (TRI-129 to TRI-135): 7 tests
"""

import pytest
import json
import time
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pathlib import Path
from collections import defaultdict


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class StreamType(str, Enum):
    """Audit stream types"""
    DDE = "DDE"
    BDV = "BDV"
    ACC = "ACC"


class FailurePattern(str, Enum):
    """Detected failure patterns"""
    ARCHITECTURAL_EROSION = "ARCHITECTURAL_EROSION"
    DESIGN_GAP = "DESIGN_GAP"
    SYSTEMIC_FAILURE = "SYSTEMIC_FAILURE"
    PROCESS_ISSUE = "PROCESS_ISSUE"
    COUPLING_WITH_TEST_FAILURE = "coupling_violation_with_test_failure"
    FLAKINESS_WITH_COMPLEXITY = "test_flakiness_with_high_complexity"
    CONTRACT_BREAKING_NO_TESTS = "contract_breaking_without_tests"
    DEPENDENCY_ISSUE = "coupling_violation_with_test_failure"


class Priority(str, Enum):
    """Recommendation priority levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FailureType(str, Enum):
    """Types of failures"""
    RECURRING = "recurring"
    CLUSTER = "cluster"
    INTERMITTENT = "intermittent"
    ENVIRONMENTAL = "environmental"
    REGRESSION = "regression"
    NEW = "new"


@dataclass
class RootCause:
    """Root cause analysis result"""
    primary_stream: StreamType
    confidence: float  # 0.0 to 1.0
    description: str
    evidence: List[str]
    cascading_from: Optional[StreamType] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['primary_stream'] = self.primary_stream.value if isinstance(self.primary_stream, StreamType) else self.primary_stream
        if self.cascading_from:
            result['cascading_from'] = self.cascading_from.value if isinstance(self.cascading_from, StreamType) else self.cascading_from
        return result


@dataclass
class Correlation:
    """Cross-stream correlation"""
    streams_affected: List[StreamType]
    correlation_strength: float  # 0.0 to 1.0
    pattern: FailurePattern
    description: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['streams_affected'] = [s.value if isinstance(s, StreamType) else s for s in self.streams_affected]
        result['pattern'] = self.pattern.value if isinstance(self.pattern, FailurePattern) else self.pattern
        return result


@dataclass
class Recommendation:
    """Actionable recommendation"""
    priority: Priority
    impact: int  # 1-10 scale
    effort: int  # 1-10 scale
    title: str
    description: str
    code_location: Optional[str] = None
    estimated_hours: Optional[int] = None
    documentation_link: Optional[str] = None

    @property
    def roi(self) -> float:
        """Return on Investment: impact / effort"""
        if self.effort == 0:
            return float('inf')
        return round(self.impact / self.effort, 2)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['priority'] = self.priority.value if isinstance(self.priority, Priority) else self.priority
        result['roi'] = self.roi
        return result


@dataclass
class FailureCluster:
    """Cluster of related failures"""
    cluster_id: str
    failures: List[str]
    pattern: FailurePattern
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['pattern'] = self.pattern.value if isinstance(self.pattern, FailurePattern) else self.pattern
        result['first_seen'] = self.first_seen.isoformat()
        result['last_seen'] = self.last_seen.isoformat()
        return result


@dataclass
class DiagnosisReport:
    """Complete failure diagnosis report"""
    diagnosis_id: str
    timestamp: str
    verdict: str
    root_cause: RootCause
    correlation: Correlation
    recommendations: List[Recommendation]
    failure_pattern: Optional[FailurePattern] = None
    historical_occurrences: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'diagnosis_id': self.diagnosis_id,
            'timestamp': self.timestamp,
            'verdict': self.verdict,
            'root_cause': self.root_cause.to_dict(),
            'correlation': self.correlation.to_dict(),
            'recommendations': [r.to_dict() for r in self.recommendations],
            'historical_occurrences': self.historical_occurrences
        }
        if self.failure_pattern:
            result['failure_pattern'] = self.failure_pattern.value if isinstance(self.failure_pattern, FailurePattern) else self.failure_pattern
        return result


# ============================================================================
# ROOT CAUSE ANALYZER
# ============================================================================

class RootCauseAnalyzer:
    """Analyzes failures to determine root cause"""

    def analyze(
        self,
        dde_passed: bool,
        bdv_passed: bool,
        acc_passed: bool,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> RootCause:
        """
        Analyze verdict pattern to determine root cause

        Returns root cause with confidence score
        """
        evidence = []

        # Determine primary failure stream
        if not dde_passed and bdv_passed and acc_passed:
            primary = StreamType.DDE
            confidence = 0.95
            description = "DDE execution or quality gate failure"
            evidence = self._extract_dde_evidence(dde_details)

        elif dde_passed and not bdv_passed and acc_passed:
            primary = StreamType.BDV
            confidence = 0.92
            description = "BDV scenario failures indicate design gap"
            evidence = self._extract_bdv_evidence(bdv_details)

        elif dde_passed and bdv_passed and not acc_passed:
            primary = StreamType.ACC
            confidence = 0.90
            description = "ACC architectural violations detected"
            evidence = self._extract_acc_evidence(acc_details)

        elif not dde_passed and not bdv_passed and not acc_passed:
            # Systemic failure - determine likely origin
            primary = self._determine_systemic_origin(dde_details, bdv_details, acc_details)
            confidence = 0.75
            description = "Systemic failure across all streams"
            evidence = ["All three audit streams failed", "Systemic issue requires investigation"]

        else:
            # Mixed failure - analyze correlation
            primary = self._determine_mixed_failure_origin(dde_passed, bdv_passed, acc_passed, dde_details, bdv_details, acc_details)
            confidence = 0.65
            description = "Mixed failure pattern detected"
            evidence = ["Multiple streams failed", "Requires multi-stream analysis"]

        # Detect cascading failures
        cascading_from = self._detect_cascading_failure(dde_passed, bdv_passed, acc_passed, dde_details, bdv_details, acc_details)

        return RootCause(
            primary_stream=primary,
            confidence=confidence,
            description=description,
            evidence=evidence,
            cascading_from=cascading_from
        )

    def _extract_dde_evidence(self, details: Dict[str, Any]) -> List[str]:
        """Extract evidence from DDE failure"""
        evidence = []
        if not details.get('all_nodes_complete', True):
            evidence.append(f"DDE: {details.get('failed_nodes', 0)} nodes failed to complete")
        if not details.get('blocking_gates_passed', True):
            evidence.append("DDE: Quality gates blocked deployment")
        if not details.get('contracts_locked', True):
            evidence.append("DDE: Contracts not properly locked")
        return evidence or ["DDE execution failure"]

    def _extract_bdv_evidence(self, details: Dict[str, Any]) -> List[str]:
        """Extract evidence from BDV failure"""
        evidence = []
        failed = details.get('failed_scenarios', 0)
        if failed > 0:
            evidence.append(f"BDV: {failed} scenarios failed")

        flake_rate = details.get('flake_rate', 0.0)
        if flake_rate > 0.10:
            evidence.append(f"BDV: High flake rate {flake_rate:.1%}")

        mismatches = details.get('contract_mismatches', [])
        if mismatches:
            evidence.append(f"BDV: Contract mismatches - {', '.join(mismatches)}")

        return evidence or ["BDV scenario failures"]

    def _extract_acc_evidence(self, details: Dict[str, Any]) -> List[str]:
        """Extract evidence from ACC failure"""
        evidence = []
        blocking = details.get('blocking_violations', 0)
        if blocking > 0:
            evidence.append(f"ACC: {blocking} blocking violations")

        cycles = details.get('cycles', [])
        if cycles:
            evidence.append(f"ACC: {len(cycles)} cyclic dependencies detected")

        if not details.get('coupling_within_limits', True):
            evidence.append("ACC: Coupling exceeds architectural limits")

        coupling_scores = details.get('coupling_scores', {})
        for source, targets in coupling_scores.items():
            for target, score in targets.items():
                if score > 0.7:
                    evidence.append(f"ACC: High coupling {source} -> {target}: {score:.2f}")

        return evidence or ["ACC architectural violations"]

    def _determine_systemic_origin(
        self,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> StreamType:
        """Determine likely origin of systemic failure"""
        # Score each stream by severity
        dde_score = self._calculate_failure_severity(dde_details, 'dde')
        bdv_score = self._calculate_failure_severity(bdv_details, 'bdv')
        acc_score = self._calculate_failure_severity(acc_details, 'acc')

        scores = {
            StreamType.DDE: dde_score,
            StreamType.BDV: bdv_score,
            StreamType.ACC: acc_score
        }

        return max(scores, key=scores.get)

    def _determine_mixed_failure_origin(
        self,
        dde_passed: bool,
        bdv_passed: bool,
        acc_passed: bool,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> StreamType:
        """Determine origin of mixed failure"""
        # Identify which streams failed
        failed_streams = []
        if not dde_passed:
            failed_streams.append((StreamType.DDE, self._calculate_failure_severity(dde_details, 'dde')))
        if not bdv_passed:
            failed_streams.append((StreamType.BDV, self._calculate_failure_severity(bdv_details, 'bdv')))
        if not acc_passed:
            failed_streams.append((StreamType.ACC, self._calculate_failure_severity(acc_details, 'acc')))

        # Return stream with highest severity
        if failed_streams:
            return max(failed_streams, key=lambda x: x[1])[0]
        return StreamType.DDE

    def _calculate_failure_severity(self, details: Dict[str, Any], stream_type: str) -> float:
        """Calculate severity score for a failure"""
        if stream_type == 'dde':
            severity = 0.0
            if not details.get('all_nodes_complete', True):
                severity += 0.4
            if not details.get('blocking_gates_passed', True):
                severity += 0.3
            if not details.get('contracts_locked', True):
                severity += 0.3
            return severity

        elif stream_type == 'bdv':
            total = details.get('total_scenarios', 1)
            failed = details.get('failed_scenarios', 0)
            flake_rate = details.get('flake_rate', 0.0)
            return (failed / total) * 0.7 + flake_rate * 0.3

        elif stream_type == 'acc':
            blocking = details.get('blocking_violations', 0)
            cycles = len(details.get('cycles', []))
            return min(1.0, (blocking * 0.2 + cycles * 0.15))

        return 0.0

    def _detect_cascading_failure(
        self,
        dde_passed: bool,
        bdv_passed: bool,
        acc_passed: bool,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> Optional[StreamType]:
        """Detect if failure cascaded from one stream to others"""
        # If ACC has high coupling and BDV fails, ACC may have caused BDV failure
        if not acc_passed and not bdv_passed and dde_passed:
            if not acc_details.get('coupling_within_limits', True):
                return StreamType.ACC

        # If DDE contracts not locked and BDV has mismatches, DDE caused BDV failure
        if not dde_passed and not bdv_passed and acc_passed:
            if not dde_details.get('contracts_locked', True) and bdv_details.get('contract_mismatches', []):
                return StreamType.DDE

        return None

    def analyze_time_correlation(
        self,
        failures: List[Tuple[datetime, StreamType, str]]
    ) -> Dict[str, Any]:
        """Analyze time-based correlation between failures"""
        if len(failures) < 2:
            return {'correlated': False, 'time_window': 0}

        # Sort by time
        sorted_failures = sorted(failures, key=lambda x: x[0])

        # Check if failures occurred within short time window (5 minutes)
        time_window = (sorted_failures[-1][0] - sorted_failures[0][0]).total_seconds()
        correlated = time_window <= 300  # 5 minutes

        # Identify sequence
        sequence = [f[1].value for f in sorted_failures]

        return {
            'correlated': correlated,
            'time_window': time_window,
            'sequence': sequence,
            'first_failure': sorted_failures[0][1].value
        }

    def analyze_historical_pattern(
        self,
        current_failure: RootCause,
        historical_failures: List[RootCause]
    ) -> Dict[str, Any]:
        """Analyze historical failure patterns"""
        if not historical_failures:
            return {'is_recurring': False, 'occurrence_count': 1}

        # Check for similar failures
        similar_count = 0
        for hist in historical_failures:
            if hist.primary_stream == current_failure.primary_stream:
                # Check evidence similarity
                evidence_overlap = len(set(current_failure.evidence) & set(hist.evidence))
                if evidence_overlap > 0:
                    similar_count += 1

        return {
            'is_recurring': similar_count >= 2,
            'occurrence_count': similar_count + 1,
            'pattern': 'recurring' if similar_count >= 2 else 'isolated'
        }


# ============================================================================
# CROSS-STREAM CORRELATOR
# ============================================================================

class CrossStreamCorrelator:
    """Correlates failures across multiple audit streams"""

    def correlate(
        self,
        dde_passed: bool,
        bdv_passed: bool,
        acc_passed: bool,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> Correlation:
        """
        Correlate failures across streams to identify patterns
        """
        streams_affected = []
        if not dde_passed:
            streams_affected.append(StreamType.DDE)
        if not bdv_passed:
            streams_affected.append(StreamType.BDV)
        if not acc_passed:
            streams_affected.append(StreamType.ACC)

        # Determine pattern
        pattern = self._identify_pattern(dde_passed, bdv_passed, acc_passed, dde_details, bdv_details, acc_details)

        # Calculate correlation strength
        strength = self._calculate_correlation_strength(streams_affected, dde_details, bdv_details, acc_details)

        # Generate description
        description = self._generate_correlation_description(pattern, streams_affected)

        return Correlation(
            streams_affected=streams_affected,
            correlation_strength=strength,
            pattern=pattern,
            description=description
        )

    def _identify_pattern(
        self,
        dde_passed: bool,
        bdv_passed: bool,
        acc_passed: bool,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> FailurePattern:
        """Identify specific failure pattern"""
        # Check specific patterns FIRST (before generic patterns)
        if self._is_flakiness_with_complexity(bdv_details, acc_details):
            return FailurePattern.FLAKINESS_WITH_COMPLEXITY

        if self._is_coupling_with_test_failure(bdv_details, acc_details):
            return FailurePattern.COUPLING_WITH_TEST_FAILURE

        if self._is_contract_breaking_without_tests(dde_details, bdv_details):
            return FailurePattern.CONTRACT_BREAKING_NO_TESTS

        # Then check generic verdict patterns
        # BDV failure + ACC violation = ARCHITECTURAL_EROSION
        if not bdv_passed and not acc_passed and dde_passed:
            return FailurePattern.ARCHITECTURAL_EROSION

        # DDE failure + BDV pass = DESIGN_GAP (process issue actually)
        if not dde_passed and bdv_passed and acc_passed:
            return FailurePattern.PROCESS_ISSUE

        # All streams fail = SYSTEMIC_FAILURE
        if not dde_passed and not bdv_passed and not acc_passed:
            return FailurePattern.SYSTEMIC_FAILURE

        # BDV fails alone (DDE + ACC pass) = DESIGN_GAP
        if dde_passed and not bdv_passed and acc_passed:
            return FailurePattern.DESIGN_GAP

        # Default to architectural erosion if multiple streams affected
        if len([p for p in [dde_passed, bdv_passed, acc_passed] if not p]) > 1:
            return FailurePattern.ARCHITECTURAL_EROSION

        return FailurePattern.DESIGN_GAP

    def _is_coupling_with_test_failure(self, bdv_details: Dict[str, Any], acc_details: Dict[str, Any]) -> bool:
        """Detect pattern: high coupling + test failures"""
        has_test_failures = bdv_details.get('failed_scenarios', 0) > 0
        has_high_coupling = not acc_details.get('coupling_within_limits', True)
        return has_test_failures and has_high_coupling

    def _is_flakiness_with_complexity(self, bdv_details: Dict[str, Any], acc_details: Dict[str, Any]) -> bool:
        """Detect pattern: test flakiness + high complexity"""
        high_flake = bdv_details.get('flake_rate', 0.0) > 0.10
        high_complexity = acc_details.get('details', {}).get('instability_score', 0.0) > 0.6
        return high_flake and high_complexity

    def _is_contract_breaking_without_tests(self, dde_details: Dict[str, Any], bdv_details: Dict[str, Any]) -> bool:
        """Detect pattern: contract changes without test updates"""
        contracts_changed = not dde_details.get('contracts_locked', True)
        has_mismatches = len(bdv_details.get('contract_mismatches', [])) > 0
        return contracts_changed and has_mismatches

    def _calculate_correlation_strength(
        self,
        streams_affected: List[StreamType],
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> float:
        """Calculate correlation strength between failures"""
        if len(streams_affected) == 0:
            return 0.0

        if len(streams_affected) == 1:
            return 0.5  # Single stream, moderate correlation

        # Multiple streams - check for evidence linking
        strength = 0.6  # Base correlation for multiple streams

        # Boost if specific patterns detected
        if self._is_coupling_with_test_failure(bdv_details, acc_details):
            strength += 0.25

        if self._is_contract_breaking_without_tests(dde_details, bdv_details):
            strength += 0.25

        return min(1.0, strength)

    def _generate_correlation_description(
        self,
        pattern: FailurePattern,
        streams_affected: List[StreamType]
    ) -> str:
        """Generate human-readable correlation description"""
        descriptions = {
            FailurePattern.ARCHITECTURAL_EROSION: "BDV and ACC failures indicate architectural violations affecting behavior",
            FailurePattern.DESIGN_GAP: "Implementation doesn't match requirements",
            FailurePattern.SYSTEMIC_FAILURE: "All streams failed - fundamental issues detected",
            FailurePattern.PROCESS_ISSUE: "DDE process issues detected",
            FailurePattern.COUPLING_WITH_TEST_FAILURE: "High coupling causing test failures",
            FailurePattern.FLAKINESS_WITH_COMPLEXITY: "Test flakiness correlated with high complexity",
            FailurePattern.CONTRACT_BREAKING_NO_TESTS: "Contract changes made without test updates",
        }

        base_desc = descriptions.get(pattern, "Multiple failures detected")
        stream_names = [s.value for s in streams_affected]
        return f"{base_desc} (Streams: {', '.join(stream_names)})"


# ============================================================================
# RECOMMENDATION ENGINE
# ============================================================================

class RecommendationEngine:
    """Generates actionable recommendations from failure analysis"""

    def generate_recommendations(
        self,
        root_cause: RootCause,
        correlation: Correlation,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate prioritized, actionable recommendations"""
        recommendations = []

        # Generate recommendations based on primary failure stream
        if root_cause.primary_stream == StreamType.DDE:
            recommendations.extend(self._generate_dde_recommendations(dde_details))

        if root_cause.primary_stream == StreamType.BDV or StreamType.BDV in correlation.streams_affected:
            recommendations.extend(self._generate_bdv_recommendations(bdv_details))

        if root_cause.primary_stream == StreamType.ACC or StreamType.ACC in correlation.streams_affected:
            recommendations.extend(self._generate_acc_recommendations(acc_details))

        # Add pattern-specific recommendations
        pattern_recs = self._generate_pattern_recommendations(correlation.pattern)
        recommendations.extend(pattern_recs)

        # Sort by ROI (descending)
        recommendations.sort(key=lambda r: r.roi, reverse=True)

        return recommendations

    def _generate_dde_recommendations(self, details: Dict[str, Any]) -> List[Recommendation]:
        """Generate DDE-specific recommendations"""
        recs = []

        if not details.get('all_nodes_complete', True):
            failed = details.get('failed_nodes', 0)
            recs.append(Recommendation(
                priority=Priority.CRITICAL,
                impact=9,
                effort=5,
                title=f"Fix {failed} failed DDE execution nodes",
                description="Complete all nodes in the execution manifest to ensure proper workflow",
                code_location="dag_workflow.py",
                estimated_hours=failed * 2,
                documentation_link="/docs/dde/node-execution"
            ))

        if not details.get('contracts_locked', True):
            recs.append(Recommendation(
                priority=Priority.HIGH,
                impact=8,
                effort=3,
                title="Lock all interface contracts",
                description="Ensure contracts are locked before dependent work begins",
                code_location="contract_manager.py",
                estimated_hours=4,
                documentation_link="/docs/contracts/locking"
            ))

        if not details.get('blocking_gates_passed', True):
            recs.append(Recommendation(
                priority=Priority.HIGH,
                impact=8,
                effort=6,
                title="Fix quality gate failures",
                description="Address coverage, lint, or security scan failures",
                estimated_hours=8,
                documentation_link="/docs/quality-gates"
            ))

        return recs

    def _generate_bdv_recommendations(self, details: Dict[str, Any]) -> List[Recommendation]:
        """Generate BDV-specific recommendations"""
        recs = []

        failed_scenarios = details.get('failed_scenarios', 0)
        if failed_scenarios > 0:
            recs.append(Recommendation(
                priority=Priority.CRITICAL,
                impact=9,
                effort=4,
                title=f"Fix {failed_scenarios} failing BDV scenarios",
                description="Update implementation to pass all behavior validation tests",
                code_location="bdv/scenarios/",
                estimated_hours=failed_scenarios * 1,
                documentation_link="/docs/bdv/scenario-fixing"
            ))

        flake_rate = details.get('flake_rate', 0.0)
        if flake_rate > 0.10:
            recs.append(Recommendation(
                priority=Priority.MEDIUM,
                impact=6,
                effort=5,
                title=f"Reduce test flake rate from {flake_rate:.1%}",
                description="Stabilize intermittent test failures to improve reliability",
                estimated_hours=10,
                documentation_link="/docs/bdv/flakiness"
            ))

        contract_mismatches = details.get('contract_mismatches', [])
        if contract_mismatches:
            recs.append(Recommendation(
                priority=Priority.HIGH,
                impact=8,
                effort=2,
                title="Update scenarios for contract version mismatches",
                description=f"Sync scenarios with contracts: {', '.join(contract_mismatches)}",
                code_location="bdv/contracts/",
                estimated_hours=2,
                documentation_link="/docs/contracts/versioning"
            ))

        return recs

    def _generate_acc_recommendations(self, details: Dict[str, Any]) -> List[Recommendation]:
        """Generate ACC-specific recommendations"""
        recs = []

        blocking_violations = details.get('blocking_violations', 0)
        if blocking_violations > 0:
            recs.append(Recommendation(
                priority=Priority.CRITICAL,
                impact=10,
                effort=7,
                title=f"Fix {blocking_violations} blocking architectural violations",
                description="Refactor code to comply with architectural constraints",
                estimated_hours=blocking_violations * 3,
                documentation_link="/docs/acc/violations"
            ))

        cycles = details.get('cycles', [])
        if cycles:
            recs.append(Recommendation(
                priority=Priority.HIGH,
                impact=9,
                effort=6,
                title=f"Break {len(cycles)} cyclic dependencies",
                description="Refactor to eliminate circular dependencies",
                code_location="See ACC report for cycle details",
                estimated_hours=len(cycles) * 4,
                documentation_link="/docs/acc/cycles"
            ))

        if not details.get('coupling_within_limits', True):
            coupling_scores = details.get('coupling_scores', {})
            high_coupling = []
            for source, targets in coupling_scores.items():
                for target, score in targets.items():
                    if score > 0.7:
                        high_coupling.append(f"{source}->{target}")

            recs.append(Recommendation(
                priority=Priority.MEDIUM,
                impact=7,
                effort=8,
                title="Reduce coupling to meet architectural limits",
                description=f"Decouple high-coupling pairs: {', '.join(high_coupling[:3])}",
                code_location="services/",
                estimated_hours=12,
                documentation_link="/docs/acc/coupling"
            ))

        return recs

    def _generate_pattern_recommendations(self, pattern: FailurePattern) -> List[Recommendation]:
        """Generate pattern-specific recommendations"""
        pattern_map = {
            FailurePattern.COUPLING_WITH_TEST_FAILURE: Recommendation(
                priority=Priority.HIGH,
                impact=8,
                effort=6,
                title="Extract interface to reduce coupling",
                description="High coupling is causing test failures. Extract interfaces to decouple components",
                estimated_hours=8,
                documentation_link="/docs/patterns/coupling-isolation"
            ),
            FailurePattern.FLAKINESS_WITH_COMPLEXITY: Recommendation(
                priority=Priority.MEDIUM,
                impact=6,
                effort=8,
                title="Simplify complex components to reduce flakiness",
                description="High complexity correlates with test flakiness. Refactor to reduce complexity",
                estimated_hours=16,
                documentation_link="/docs/patterns/complexity-reduction"
            ),
            FailurePattern.CONTRACT_BREAKING_NO_TESTS: Recommendation(
                priority=Priority.CRITICAL,
                impact=10,
                effort=2,
                title="Add contract validation tests",
                description="Contract changes must be validated by tests before deployment",
                estimated_hours=4,
                documentation_link="/docs/contracts/testing"
            ),
        }

        rec = pattern_map.get(pattern)
        return [rec] if rec else []

    def generate_github_issue(self, recommendation: Recommendation) -> Dict[str, Any]:
        """Generate GitHub issue from recommendation"""
        labels = []
        if recommendation.priority == Priority.CRITICAL:
            labels = ["priority: critical", "bug"]
        elif recommendation.priority == Priority.HIGH:
            labels = ["priority: high", "bug"]
        elif recommendation.priority == Priority.MEDIUM:
            labels = ["priority: medium", "enhancement"]
        else:
            labels = ["priority: low", "tech-debt"]

        body = f"""## Description
{recommendation.description}

## Impact
- Severity: {recommendation.impact}/10
- Effort: {recommendation.effort}/10
- ROI: {recommendation.roi}

## Estimated Effort
{recommendation.estimated_hours or 'TBD'} hours

## Code Location
{recommendation.code_location or 'See diagnosis report'}

## Documentation
{recommendation.documentation_link or 'N/A'}

## Generated by
Tri-Modal Failure Diagnosis System
"""

        return {
            "title": recommendation.title,
            "body": body,
            "labels": labels,
            "assignees": []
        }


# ============================================================================
# PATTERN DETECTOR
# ============================================================================

class PatternDetector:
    """Detects and clusters failure patterns"""

    def __init__(self):
        self.db_path = ":memory:"  # Use in-memory database for testing
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Initialize failure history database"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                iteration_id TEXT,
                verdict TEXT,
                primary_stream TEXT,
                evidence TEXT,
                pattern TEXT
            )
        """)
        self.conn.commit()

    def _get_connection(self):
        """Get database connection, creating if needed"""
        if self.conn is None:
            self._init_database()
        return self.conn

    def record_failure(
        self,
        iteration_id: str,
        verdict: str,
        root_cause: RootCause,
        pattern: FailurePattern
    ):
        """Record failure in history database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO failure_history (timestamp, iteration_id, verdict, primary_stream, evidence, pattern)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            iteration_id,
            verdict,
            root_cause.primary_stream.value,
            json.dumps(root_cause.evidence),
            pattern.value
        ))
        conn.commit()

    def detect_recurring_failure(self, root_cause: RootCause, window_days: int = 30) -> bool:
        """Detect if failure is recurring"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=window_days)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM failure_history
            WHERE primary_stream = ? AND timestamp > ?
        """, (root_cause.primary_stream.value, cutoff))

        count = cursor.fetchone()[0]

        return count >= 3  # Recurring if 3+ occurrences in window

    def detect_failure_cluster(self, root_cause: RootCause) -> Optional[FailureCluster]:
        """Detect cluster of related failures"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Find similar failures (same primary stream)
        cursor.execute("""
            SELECT iteration_id, timestamp, pattern FROM failure_history
            WHERE primary_stream = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (root_cause.primary_stream.value,))

        rows = cursor.fetchall()

        if len(rows) >= 3:
            # Create cluster
            timestamps = [datetime.fromisoformat(r[1]) for r in rows]
            return FailureCluster(
                cluster_id=f"cluster_{root_cause.primary_stream.value}_{int(time.time())}",
                failures=[r[0] for r in rows],
                pattern=FailurePattern(rows[0][2]) if rows[0][2] else FailurePattern.DESIGN_GAP,
                first_seen=min(timestamps),
                last_seen=max(timestamps),
                occurrence_count=len(rows)
            )

        return None

    def detect_intermittent_failure(self, iteration_id: str, window_hours: int = 24) -> bool:
        """Detect intermittent (flaky) failures"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
        cursor.execute("""
            SELECT pattern FROM failure_history
            WHERE iteration_id = ? AND timestamp > ?
        """, (iteration_id, cutoff))

        rows = cursor.fetchall()

        # Intermittent if multiple different patterns for same iteration
        patterns = set(r[0] for r in rows if r[0])
        return len(patterns) > 1

    def detect_regression(self, iteration_id: str) -> bool:
        """Detect regression (working -> failing)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if this iteration previously passed
        cursor.execute("""
            SELECT verdict FROM failure_history
            WHERE iteration_id = ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (iteration_id,))

        rows = cursor.fetchall()

        if len(rows) >= 2:
            verdicts = [r[0] for r in rows]
            # Regression if latest is failure but previous was pass
            return verdicts[0] != "ALL_PASS" and "ALL_PASS" in verdicts[1:]

        return False

    def detect_new_failure(self, root_cause: RootCause) -> bool:
        """Detect if this is a new type of failure"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if we've seen this primary stream fail before
        cursor.execute("""
            SELECT COUNT(*) FROM failure_history
            WHERE primary_stream = ?
        """, (root_cause.primary_stream.value,))

        count = cursor.fetchone()[0]

        return count == 0  # New if never seen before

    def classify_failure_type(self, root_cause: RootCause, iteration_id: str) -> FailureType:
        """Classify failure type using pattern detection"""
        if self.detect_new_failure(root_cause):
            return FailureType.NEW

        if self.detect_recurring_failure(root_cause):
            return FailureType.RECURRING

        if self.detect_intermittent_failure(iteration_id):
            return FailureType.INTERMITTENT

        cluster = self.detect_failure_cluster(root_cause)
        if cluster and cluster.occurrence_count >= 3:
            return FailureType.CLUSTER

        if self.detect_regression(iteration_id):
            return FailureType.REGRESSION

        return FailureType.NEW


# ============================================================================
# FAILURE DIAGNOSIS ENGINE
# ============================================================================

class FailureDiagnosisEngine:
    """Main engine for failure diagnosis and recommendations"""

    def __init__(self):
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.cross_stream_correlator = CrossStreamCorrelator()
        self.recommendation_engine = RecommendationEngine()
        self.pattern_detector = PatternDetector()

    def diagnose(
        self,
        iteration_id: str,
        verdict: str,
        dde_passed: bool,
        bdv_passed: bool,
        acc_passed: bool,
        dde_details: Dict[str, Any],
        bdv_details: Dict[str, Any],
        acc_details: Dict[str, Any]
    ) -> DiagnosisReport:
        """
        Complete failure diagnosis with root cause, correlation, and recommendations
        """
        # Analyze root cause
        root_cause = self.root_cause_analyzer.analyze(
            dde_passed, bdv_passed, acc_passed,
            dde_details, bdv_details, acc_details
        )

        # Correlate across streams
        correlation = self.cross_stream_correlator.correlate(
            dde_passed, bdv_passed, acc_passed,
            dde_details, bdv_details, acc_details
        )

        # Generate recommendations
        recommendations = self.recommendation_engine.generate_recommendations(
            root_cause, correlation,
            dde_details, bdv_details, acc_details
        )

        # Detect patterns
        failure_type = self.pattern_detector.classify_failure_type(root_cause, iteration_id)

        # Record in history
        if verdict != "ALL_PASS":
            self.pattern_detector.record_failure(iteration_id, verdict, root_cause, correlation.pattern)

        # Check historical occurrences
        historical = self.pattern_detector.detect_recurring_failure(root_cause)
        hist_count = 1
        if historical:
            cluster = self.pattern_detector.detect_failure_cluster(root_cause)
            hist_count = cluster.occurrence_count if cluster else 1

        # Create diagnosis report
        diagnosis_id = f"diag_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return DiagnosisReport(
            diagnosis_id=diagnosis_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            verdict=verdict,
            root_cause=root_cause,
            correlation=correlation,
            recommendations=recommendations,
            failure_pattern=correlation.pattern,
            historical_occurrences=hist_count
        )

    def export_report_json(self, report: DiagnosisReport) -> str:
        """Export diagnosis report as JSON"""
        return json.dumps(report.to_dict(), indent=2)

    def export_report_html(self, report: DiagnosisReport) -> str:
        """Export diagnosis report as HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Failure Diagnosis Report - {report.diagnosis_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 3px solid #007bff; }}
        .critical {{ border-left-color: #dc3545; }}
        .high {{ border-left-color: #fd7e14; }}
        .medium {{ border-left-color: #ffc107; }}
        .low {{ border-left-color: #28a745; }}
        .recommendation {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Failure Diagnosis Report</h1>
        <p><strong>ID:</strong> {report.diagnosis_id}</p>
        <p><strong>Timestamp:</strong> {report.timestamp}</p>
        <p><strong>Verdict:</strong> {report.verdict}</p>
    </div>

    <div class="section">
        <h2>Root Cause Analysis</h2>
        <p><strong>Primary Stream:</strong> {report.root_cause.primary_stream.value}</p>
        <p><strong>Confidence:</strong> {report.root_cause.confidence:.2%}</p>
        <p><strong>Description:</strong> {report.root_cause.description}</p>
        <h3>Evidence:</h3>
        <ul>
            {"".join(f"<li>{e}</li>" for e in report.root_cause.evidence)}
        </ul>
    </div>

    <div class="section">
        <h2>Cross-Stream Correlation</h2>
        <p><strong>Streams Affected:</strong> {", ".join(s.value for s in report.correlation.streams_affected)}</p>
        <p><strong>Correlation Strength:</strong> {report.correlation.correlation_strength:.2%}</p>
        <p><strong>Pattern:</strong> {report.correlation.pattern.value}</p>
        <p>{report.correlation.description}</p>
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        {"".join(f'''
        <div class="recommendation {rec.priority.value.lower()}">
            <h3>{rec.title}</h3>
            <p><strong>Priority:</strong> {rec.priority.value}</p>
            <p><strong>Impact:</strong> {rec.impact}/10 | <strong>Effort:</strong> {rec.effort}/10 | <strong>ROI:</strong> {rec.roi}</p>
            <p>{rec.description}</p>
            {f"<p><strong>Location:</strong> {rec.code_location}</p>" if rec.code_location else ""}
            {f"<p><strong>Estimated:</strong> {rec.estimated_hours} hours</p>" if rec.estimated_hours else ""}
        </div>
        ''' for rec in report.recommendations)}
    </div>
</body>
</html>
"""
        return html


# ============================================================================
# TEST SUITE: ROOT CAUSE ANALYSIS (TRI-101 to TRI-107)
# ============================================================================

@pytest.mark.tri_audit
@pytest.mark.integration
class TestRootCauseAnalysis:
    """Test Suite: Root Cause Analysis (7 tests)"""

    def test_tri_101_analyze_truth_table_all_pass(self):
        """TRI-101: Analyze verdict pattern - ALL_PASS (✅✅✅)"""
        analyzer = RootCauseAnalyzer()

        root_cause = analyzer.analyze(
            dde_passed=True, bdv_passed=True, acc_passed=True,
            dde_details={}, bdv_details={}, acc_details={}
        )

        # For all pass, should indicate success (can use any stream as "primary")
        assert root_cause.confidence > 0.5
        assert root_cause.evidence is not None

    def test_tri_102_identify_primary_failure_stream(self):
        """TRI-102: Identify primary failure stream from evidence"""
        analyzer = RootCauseAnalyzer()

        # DDE failure
        dde_root = analyzer.analyze(
            dde_passed=False, bdv_passed=True, acc_passed=True,
            dde_details={'all_nodes_complete': False, 'failed_nodes': 3},
            bdv_details={}, acc_details={}
        )
        assert dde_root.primary_stream == StreamType.DDE
        assert "DDE" in dde_root.evidence[0]

        # BDV failure
        bdv_root = analyzer.analyze(
            dde_passed=True, bdv_passed=False, acc_passed=True,
            dde_details={},
            bdv_details={'failed_scenarios': 5, 'total_scenarios': 20},
            acc_details={}
        )
        assert bdv_root.primary_stream == StreamType.BDV
        assert any("BDV" in e for e in bdv_root.evidence)

        # ACC failure
        acc_root = analyzer.analyze(
            dde_passed=True, bdv_passed=True, acc_passed=False,
            dde_details={}, bdv_details={},
            acc_details={'blocking_violations': 3}
        )
        assert acc_root.primary_stream == StreamType.ACC
        assert any("ACC" in e for e in acc_root.evidence)

    def test_tri_103_correlate_failures_across_streams(self):
        """TRI-103: Correlate failures when multiple streams fail"""
        analyzer = RootCauseAnalyzer()

        root_cause = analyzer.analyze(
            dde_passed=False, bdv_passed=False, acc_passed=True,
            dde_details={'contracts_locked': False},
            bdv_details={'contract_mismatches': ['API.v1']},
            acc_details={}
        )

        # Should identify correlation
        assert root_cause.primary_stream in [StreamType.DDE, StreamType.BDV]
        assert root_cause.confidence > 0.0

    def test_tri_104_detect_cascading_failures(self):
        """TRI-104: Detect cascading failures (one failure causes another)"""
        analyzer = RootCauseAnalyzer()

        # ACC high coupling causes BDV test failures
        root_cause = analyzer.analyze(
            dde_passed=True, bdv_passed=False, acc_passed=False,
            dde_details={},
            bdv_details={'failed_scenarios': 3},
            acc_details={'coupling_within_limits': False, 'blocking_violations': 2}
        )

        # Should detect ACC as cascading source
        assert root_cause.cascading_from == StreamType.ACC or root_cause.primary_stream == StreamType.ACC

    def test_tri_105_time_based_failure_correlation(self):
        """TRI-105: Analyze time-based correlation between failures"""
        analyzer = RootCauseAnalyzer()

        now = datetime.utcnow()
        failures = [
            (now, StreamType.ACC, "Coupling violation"),
            (now + timedelta(seconds=30), StreamType.BDV, "Test failure"),
            (now + timedelta(minutes=1), StreamType.DDE, "Quality gate")
        ]

        correlation = analyzer.analyze_time_correlation(failures)

        assert 'correlated' in correlation
        assert correlation['time_window'] < 120  # Within 2 minutes
        assert correlation['correlated'] is True
        assert correlation['first_failure'] == StreamType.ACC.value

    def test_tri_106_historical_failure_pattern_analysis(self):
        """TRI-106: Analyze historical failure patterns"""
        analyzer = RootCauseAnalyzer()

        current = RootCause(
            primary_stream=StreamType.ACC,
            confidence=0.85,
            description="Coupling violation",
            evidence=["ACC: High coupling", "ACC: 3 blocking violations"]
        )

        historical = [
            RootCause(
                primary_stream=StreamType.ACC,
                confidence=0.80,
                description="Coupling violation",
                evidence=["ACC: High coupling", "ACC: 2 blocking violations"]
            ),
            RootCause(
                primary_stream=StreamType.ACC,
                confidence=0.88,
                description="Coupling violation",
                evidence=["ACC: High coupling", "ACC: 4 blocking violations"]
            )
        ]

        pattern = analyzer.analyze_historical_pattern(current, historical)

        assert pattern['is_recurring'] is True
        assert pattern['occurrence_count'] >= 2
        assert pattern['pattern'] == 'recurring'

    def test_tri_107_confidence_scoring(self):
        """TRI-107: Confidence score (0.0-1.0) for root cause determination"""
        analyzer = RootCauseAnalyzer()

        # Single stream failure = high confidence
        single_stream = analyzer.analyze(
            dde_passed=False, bdv_passed=True, acc_passed=True,
            dde_details={'all_nodes_complete': False},
            bdv_details={}, acc_details={}
        )
        assert single_stream.confidence >= 0.90

        # Systemic failure = lower confidence
        systemic = analyzer.analyze(
            dde_passed=False, bdv_passed=False, acc_passed=False,
            dde_details={}, bdv_details={}, acc_details={}
        )
        assert systemic.confidence < 0.85

        # All scores should be in valid range
        assert 0.0 <= single_stream.confidence <= 1.0
        assert 0.0 <= systemic.confidence <= 1.0


# ============================================================================
# TEST SUITE: CROSS-STREAM CORRELATION (TRI-108 to TRI-114)
# ============================================================================

@pytest.mark.tri_audit
@pytest.mark.integration
class TestCrossStreamCorrelation:
    """Test Suite: Cross-Stream Correlation (7 tests)"""

    def test_tri_108_bdv_acc_failure_architectural_erosion(self):
        """TRI-108: BDV failure + ACC violation = ARCHITECTURAL_EROSION"""
        correlator = CrossStreamCorrelator()

        correlation = correlator.correlate(
            dde_passed=True, bdv_passed=False, acc_passed=False,
            dde_details={},
            bdv_details={'failed_scenarios': 3},
            acc_details={'blocking_violations': 2}
        )

        assert correlation.pattern == FailurePattern.ARCHITECTURAL_EROSION
        assert StreamType.BDV in correlation.streams_affected
        assert StreamType.ACC in correlation.streams_affected
        assert correlation.correlation_strength > 0.5

    def test_tri_109_dde_fail_others_pass_process_issue(self):
        """TRI-109: DDE failure + BDV pass = PROCESS_ISSUE"""
        correlator = CrossStreamCorrelator()

        correlation = correlator.correlate(
            dde_passed=False, bdv_passed=True, acc_passed=True,
            dde_details={'blocking_gates_passed': False},
            bdv_details={}, acc_details={}
        )

        assert correlation.pattern == FailurePattern.PROCESS_ISSUE
        assert StreamType.DDE in correlation.streams_affected
        assert len(correlation.streams_affected) == 1

    def test_tri_110_all_streams_fail_systemic(self):
        """TRI-110: All streams fail = SYSTEMIC_FAILURE"""
        correlator = CrossStreamCorrelator()

        correlation = correlator.correlate(
            dde_passed=False, bdv_passed=False, acc_passed=False,
            dde_details={'all_nodes_complete': False},
            bdv_details={'failed_scenarios': 10},
            acc_details={'blocking_violations': 5}
        )

        assert correlation.pattern == FailurePattern.SYSTEMIC_FAILURE
        assert len(correlation.streams_affected) == 3
        assert correlation.correlation_strength > 0.5

    def test_tri_111_flakiness_with_complexity_pattern(self):
        """TRI-111: Test flakiness + high complexity = code smell"""
        correlator = CrossStreamCorrelator()

        correlation = correlator.correlate(
            dde_passed=True, bdv_passed=False, acc_passed=False,
            dde_details={},
            bdv_details={'flake_rate': 0.15, 'failed_scenarios': 0},  # High flake but no hard failures
            acc_details={'details': {'instability_score': 0.75}, 'coupling_within_limits': True, 'blocking_violations': 0}
        )

        assert correlation.pattern == FailurePattern.FLAKINESS_WITH_COMPLEXITY
        assert correlation.correlation_strength >= 0.6  # Should have reasonable correlation

    def test_tri_112_contract_breaking_no_tests_pattern(self):
        """TRI-112: Contract breaking + no tests = risky change"""
        correlator = CrossStreamCorrelator()

        correlation = correlator.correlate(
            dde_passed=False, bdv_passed=False, acc_passed=True,
            dde_details={'contracts_locked': False},
            bdv_details={'contract_mismatches': ['PaymentAPI.v2', 'AuthAPI.v3']},
            acc_details={}
        )

        assert correlation.pattern == FailurePattern.CONTRACT_BREAKING_NO_TESTS
        assert correlation.correlation_strength > 0.8

    def test_tri_113_coupling_violation_test_failure_dependency_issue(self):
        """TRI-113: Coupling violation + test failure = dependency issue"""
        correlator = CrossStreamCorrelator()

        correlation = correlator.correlate(
            dde_passed=True, bdv_passed=False, acc_passed=False,
            dde_details={},
            bdv_details={'failed_scenarios': 5},
            acc_details={'coupling_within_limits': False, 'blocking_violations': 1}
        )

        assert correlation.pattern == FailurePattern.COUPLING_WITH_TEST_FAILURE
        assert StreamType.BDV in correlation.streams_affected
        assert StreamType.ACC in correlation.streams_affected

    def test_tri_114_correlation_strength_calculation(self):
        """TRI-114: Correlation strength calculation (0.0-1.0)"""
        correlator = CrossStreamCorrelator()

        # Single stream = moderate correlation
        single = correlator.correlate(
            dde_passed=False, bdv_passed=True, acc_passed=True,
            dde_details={}, bdv_details={}, acc_details={}
        )
        assert 0.4 <= single.correlation_strength <= 0.6

        # Multiple streams with pattern = high correlation
        multiple = correlator.correlate(
            dde_passed=True, bdv_passed=False, acc_passed=False,
            dde_details={},
            bdv_details={'failed_scenarios': 3},
            acc_details={'coupling_within_limits': False}
        )
        assert multiple.correlation_strength > 0.7

        # All in valid range
        assert 0.0 <= single.correlation_strength <= 1.0
        assert 0.0 <= multiple.correlation_strength <= 1.0


# ============================================================================
# TEST SUITE: RECOMMENDATION ENGINE (TRI-115 to TRI-121)
# ============================================================================

@pytest.mark.tri_audit
@pytest.mark.integration
class TestRecommendationEngine:
    """Test Suite: Recommendation Engine (7 tests)"""

    def test_tri_115_generate_actionable_recommendations(self):
        """TRI-115: Generate actionable recommendations"""
        engine = RecommendationEngine()

        root_cause = RootCause(
            primary_stream=StreamType.ACC,
            confidence=0.90,
            description="Coupling violation",
            evidence=["ACC: High coupling"]
        )

        correlation = Correlation(
            streams_affected=[StreamType.ACC],
            correlation_strength=0.85,
            pattern=FailurePattern.ARCHITECTURAL_EROSION,
            description="Architectural violations"
        )

        recommendations = engine.generate_recommendations(
            root_cause, correlation,
            dde_details={},
            bdv_details={},
            acc_details={'blocking_violations': 2, 'coupling_within_limits': False}
        )

        assert len(recommendations) > 0
        assert all(isinstance(r, Recommendation) for r in recommendations)
        assert all(r.title and r.description for r in recommendations)

    def test_tri_116_prioritize_by_impact(self):
        """TRI-116: Prioritize recommendations by impact (CRITICAL, HIGH, MEDIUM, LOW)"""
        engine = RecommendationEngine()

        root_cause = RootCause(
            primary_stream=StreamType.BDV,
            confidence=0.92,
            description="Test failures",
            evidence=["BDV: 5 scenarios failed"]
        )

        correlation = Correlation(
            streams_affected=[StreamType.BDV],
            correlation_strength=0.80,
            pattern=FailurePattern.DESIGN_GAP,
            description="Design gap"
        )

        recommendations = engine.generate_recommendations(
            root_cause, correlation,
            dde_details={},
            bdv_details={'failed_scenarios': 5, 'total_scenarios': 20},
            acc_details={}
        )

        # Should have priority levels
        priorities = [r.priority for r in recommendations]
        assert any(p in [Priority.CRITICAL, Priority.HIGH] for p in priorities)

    def test_tri_117_suggest_concrete_fixes(self):
        """TRI-117: Suggest concrete fixes (code changes, refactoring)"""
        engine = RecommendationEngine()

        root_cause = RootCause(
            primary_stream=StreamType.DDE,
            confidence=0.95,
            description="Contract not locked",
            evidence=["DDE: Contracts not locked"]
        )

        correlation = Correlation(
            streams_affected=[StreamType.DDE],
            correlation_strength=0.90,
            pattern=FailurePattern.PROCESS_ISSUE,
            description="Process issue"
        )

        recommendations = engine.generate_recommendations(
            root_cause, correlation,
            dde_details={'contracts_locked': False},
            bdv_details={},
            acc_details={}
        )

        # Should have specific fixes
        assert any("contract" in r.title.lower() for r in recommendations)
        assert any(r.code_location for r in recommendations)

    def test_tri_118_link_documentation_best_practices(self):
        """TRI-118: Link to documentation and best practices"""
        engine = RecommendationEngine()

        recommendations = engine._generate_acc_recommendations({
            'blocking_violations': 1,
            'cycles': [['A', 'B', 'A']]
        })

        # Should have documentation links
        assert any(r.documentation_link for r in recommendations)
        assert any('/docs/' in (r.documentation_link or '') for r in recommendations)

    def test_tri_119_estimate_effort(self):
        """TRI-119: Estimate effort (hours/story points)"""
        engine = RecommendationEngine()

        recommendations = engine._generate_bdv_recommendations({
            'failed_scenarios': 5,
            'total_scenarios': 25,
            'flake_rate': 0.12
        })

        # Should have effort estimates
        assert all(r.estimated_hours is not None for r in recommendations)
        assert all(r.estimated_hours > 0 for r in recommendations)

    def test_tri_120_roi_calculation(self):
        """TRI-120: ROI calculation: impact / effort"""
        rec = Recommendation(
            priority=Priority.HIGH,
            impact=8,
            effort=4,
            title="Fix coupling",
            description="Reduce coupling"
        )

        assert rec.roi == 2.0  # 8 / 4

        # Test edge case
        rec_zero_effort = Recommendation(
            priority=Priority.CRITICAL,
            impact=10,
            effort=0,
            title="Critical fix",
            description="Must fix"
        )
        assert rec_zero_effort.roi == float('inf')

    def test_tri_121_generate_github_issues(self):
        """TRI-121: Generate GitHub issues from recommendations"""
        engine = RecommendationEngine()

        rec = Recommendation(
            priority=Priority.CRITICAL,
            impact=10,
            effort=5,
            title="Fix architectural violations",
            description="Refactor to meet architectural constraints",
            code_location="services/payment.py:42",
            estimated_hours=8,
            documentation_link="/docs/architecture"
        )

        issue = engine.generate_github_issue(rec)

        assert 'title' in issue
        assert 'body' in issue
        assert 'labels' in issue
        assert issue['title'] == rec.title
        assert 'priority: critical' in issue['labels']
        assert 'ROI' in issue['body']


# ============================================================================
# TEST SUITE: FAILURE PATTERNS (TRI-122 to TRI-128)
# ============================================================================

@pytest.mark.tri_audit
@pytest.mark.integration
class TestFailurePatterns:
    """Test Suite: Failure Patterns (7 tests)"""

    def test_tri_122_recurring_failure_detection(self):
        """TRI-122: Recurring failure detection (same failure N times)"""
        detector = PatternDetector()

        root_cause = RootCause(
            primary_stream=StreamType.ACC,
            confidence=0.85,
            description="Coupling violation",
            evidence=["ACC: High coupling"]
        )

        # Record multiple failures
        for i in range(3):
            detector.record_failure(
                f"iter-{i}",
                "ARCHITECTURAL_EROSION",
                root_cause,
                FailurePattern.ARCHITECTURAL_EROSION
            )

        # Should detect as recurring
        is_recurring = detector.detect_recurring_failure(root_cause, window_days=30)
        assert is_recurring is True

    def test_tri_123_failure_clusters(self):
        """TRI-123: Failure clusters (multiple related failures)"""
        detector = PatternDetector()

        root_cause = RootCause(
            primary_stream=StreamType.BDV,
            confidence=0.88,
            description="Test failures",
            evidence=["BDV: Scenarios failed"]
        )

        # Record cluster of failures
        for i in range(5):
            detector.record_failure(
                f"iter-cluster-{i}",
                "DESIGN_GAP",
                root_cause,
                FailurePattern.DESIGN_GAP
            )

        cluster = detector.detect_failure_cluster(root_cause)

        assert cluster is not None
        assert cluster.occurrence_count >= 3
        assert cluster.pattern == FailurePattern.DESIGN_GAP

    def test_tri_124_intermittent_failure_tracking(self):
        """TRI-124: Intermittent failure tracking (flakiness)"""
        detector = PatternDetector()

        root_cause1 = RootCause(
            primary_stream=StreamType.BDV,
            confidence=0.70,
            description="Flaky test",
            evidence=["BDV: Intermittent failure"]
        )

        root_cause2 = RootCause(
            primary_stream=StreamType.ACC,
            confidence=0.65,
            description="Intermittent coupling",
            evidence=["ACC: Sporadic violation"]
        )

        # Record different patterns for same iteration
        detector.record_failure("iter-flaky", "MIXED_FAILURE", root_cause1, FailurePattern.DESIGN_GAP)
        detector.record_failure("iter-flaky", "MIXED_FAILURE", root_cause2, FailurePattern.ARCHITECTURAL_EROSION)

        is_intermittent = detector.detect_intermittent_failure("iter-flaky")
        assert is_intermittent is True

    def test_tri_125_environmental_failures(self):
        """TRI-125: Environmental failures (CI vs local)"""
        # Environmental failures would be tracked by metadata
        # For now, test that classification system works
        detector = PatternDetector()

        root_cause = RootCause(
            primary_stream=StreamType.DDE,
            confidence=0.80,
            description="CI-specific failure",
            evidence=["DDE: Environment issue"]
        )

        failure_type = detector.classify_failure_type(root_cause, "iter-env-001")

        # Should classify as some failure type
        assert isinstance(failure_type, FailureType)

    def test_tri_126_regression_detection(self):
        """TRI-126: Regression detection (working → failing)"""
        detector = PatternDetector()

        # Record passing iteration
        passing_root = RootCause(
            primary_stream=StreamType.DDE,
            confidence=1.0,
            description="All passed",
            evidence=[]
        )
        detector.record_failure("iter-reg", "ALL_PASS", passing_root, FailurePattern.DESIGN_GAP)

        # Record failing iteration
        failing_root = RootCause(
            primary_stream=StreamType.BDV,
            confidence=0.85,
            description="Regression",
            evidence=["BDV: New failure"]
        )
        detector.record_failure("iter-reg", "DESIGN_GAP", failing_root, FailurePattern.DESIGN_GAP)

        is_regression = detector.detect_regression("iter-reg")
        assert is_regression is True

    def test_tri_127_new_failure_detection(self):
        """TRI-127: New failure detection (never seen before)"""
        detector = PatternDetector()

        new_root_cause = RootCause(
            primary_stream=StreamType.ACC,
            confidence=0.90,
            description="New violation type",
            evidence=["ACC: Never seen before"]
        )

        is_new = detector.detect_new_failure(new_root_cause)
        assert is_new is True

        # After recording, should no longer be new
        detector.record_failure("iter-new", "ARCHITECTURAL_EROSION", new_root_cause, FailurePattern.ARCHITECTURAL_EROSION)
        is_new_again = detector.detect_new_failure(new_root_cause)
        assert is_new_again is False

    def test_tri_128_pattern_matching_ml_clustering(self):
        """TRI-128: Pattern matching using classification"""
        detector = PatternDetector()

        # Record various failure types - need 3+ for recurring
        failures = [
            (StreamType.ACC, FailurePattern.ARCHITECTURAL_EROSION, "iter-1"),
            (StreamType.ACC, FailurePattern.ARCHITECTURAL_EROSION, "iter-2"),
            (StreamType.ACC, FailurePattern.ARCHITECTURAL_EROSION, "iter-3"),
            (StreamType.BDV, FailurePattern.DESIGN_GAP, "iter-4"),
            (StreamType.DDE, FailurePattern.PROCESS_ISSUE, "iter-5"),
        ]

        for stream, pattern, iter_id in failures:
            root = RootCause(stream, 0.85, f"{pattern.value}", [f"{stream.value} failure"])
            detector.record_failure(iter_id, pattern.value, root, pattern)

        # Classify new failure
        test_root = RootCause(StreamType.ACC, 0.88, "Arch issue", ["ACC: violation"])
        failure_type = detector.classify_failure_type(test_root, "iter-test")

        # Should classify as recurring (we have 3 ACC failures)
        assert failure_type == FailureType.RECURRING


# ============================================================================
# TEST SUITE: INTEGRATION & PERFORMANCE (TRI-129 to TRI-135)
# ============================================================================

@pytest.mark.tri_audit
@pytest.mark.integration
class TestIntegrationAndPerformance:
    """Test Suite: Integration & Performance (7 tests)"""

    def test_tri_129_integration_with_dde_audit(self):
        """TRI-129: Integration with DDE audit results"""
        engine = FailureDiagnosisEngine()

        dde_details = {
            'all_nodes_complete': False,
            'failed_nodes': 2,
            'blocking_gates_passed': False,
            'contracts_locked': True
        }

        report = engine.diagnose(
            iteration_id="test-dde-001",
            verdict="PROCESS_ISSUE",
            dde_passed=False,
            bdv_passed=True,
            acc_passed=True,
            dde_details=dde_details,
            bdv_details={},
            acc_details={}
        )

        assert report.root_cause.primary_stream == StreamType.DDE
        assert len(report.recommendations) > 0
        assert any("DDE" in r.title for r in report.recommendations)

    def test_tri_130_integration_with_bdv_audit(self):
        """TRI-130: Integration with BDV audit results"""
        engine = FailureDiagnosisEngine()

        bdv_details = {
            'failed_scenarios': 5,
            'total_scenarios': 25,
            'flake_rate': 0.08,
            'contract_mismatches': ['API.v1']
        }

        report = engine.diagnose(
            iteration_id="test-bdv-001",
            verdict="DESIGN_GAP",
            dde_passed=True,
            bdv_passed=False,
            acc_passed=True,
            dde_details={},
            bdv_details=bdv_details,
            acc_details={}
        )

        assert report.root_cause.primary_stream == StreamType.BDV
        assert any("scenario" in r.title.lower() for r in report.recommendations)

    def test_tri_131_integration_with_acc_audit(self):
        """TRI-131: Integration with ACC audit results"""
        engine = FailureDiagnosisEngine()

        acc_details = {
            'blocking_violations': 3,
            'cycles': [['A', 'B', 'A'], ['X', 'Y', 'X']],
            'coupling_within_limits': False,
            'coupling_scores': {'service_a': {'service_b': 0.85}}
        }

        report = engine.diagnose(
            iteration_id="test-acc-001",
            verdict="ARCHITECTURAL_EROSION",
            dde_passed=True,
            bdv_passed=True,
            acc_passed=False,
            dde_details={},
            bdv_details={},
            acc_details=acc_details
        )

        assert report.root_cause.primary_stream == StreamType.ACC
        assert any("architectural" in r.title.lower() or "coupling" in r.title.lower() for r in report.recommendations)

    def test_tri_132_integration_with_verdict_determination(self):
        """TRI-132: Integration with verdict determination"""
        engine = FailureDiagnosisEngine()

        # Test each verdict type
        verdicts_to_test = [
            ("ALL_PASS", True, True, True),
            ("DESIGN_GAP", True, False, True),
            ("ARCHITECTURAL_EROSION", True, True, False),
            ("PROCESS_ISSUE", False, True, True),
            ("SYSTEMIC_FAILURE", False, False, False),
        ]

        for verdict, dde, bdv, acc in verdicts_to_test:
            report = engine.diagnose(
                iteration_id=f"test-verdict-{verdict}",
                verdict=verdict,
                dde_passed=dde,
                bdv_passed=bdv,
                acc_passed=acc,
                dde_details={},
                bdv_details={},
                acc_details={}
            )

            assert report.verdict == verdict
            assert report.diagnosis_id.startswith("diag_")

    def test_tri_133_performance_100_failures_under_5_seconds(self):
        """TRI-133: Performance: diagnose 100 failures in <5 seconds"""
        engine = FailureDiagnosisEngine()

        start_time = time.time()

        # Diagnose 100 failures
        for i in range(100):
            engine.diagnose(
                iteration_id=f"perf-test-{i}",
                verdict="DESIGN_GAP" if i % 2 == 0 else "ARCHITECTURAL_EROSION",
                dde_passed=True,
                bdv_passed=(i % 2 == 1),
                acc_passed=(i % 2 == 0),
                dde_details={},
                bdv_details={'failed_scenarios': i % 10} if i % 2 == 0 else {},
                acc_details={'blocking_violations': i % 5} if i % 2 == 1 else {}
            )

        elapsed = time.time() - start_time

        assert elapsed < 5.0, f"Performance test failed: {elapsed:.2f}s > 5.0s"
        print(f"✓ Diagnosed 100 failures in {elapsed:.2f}s")

    def test_tri_134_historical_failure_database(self):
        """TRI-134: Historical failure database (SQLite)"""
        detector = PatternDetector()

        # Record failures
        for i in range(10):
            root = RootCause(
                primary_stream=StreamType.BDV,
                confidence=0.85,
                description=f"Failure {i}",
                evidence=[f"Evidence {i}"]
            )
            detector.record_failure(
                f"hist-iter-{i}",
                "DESIGN_GAP",
                root,
                FailurePattern.DESIGN_GAP
            )

        # Verify data persists
        cluster = detector.detect_failure_cluster(root)
        assert cluster is not None
        assert cluster.occurrence_count >= 3

    def test_tri_135_export_diagnosis_reports(self):
        """TRI-135: Export diagnosis reports (JSON, HTML)"""
        engine = FailureDiagnosisEngine()

        report = engine.diagnose(
            iteration_id="export-test-001",
            verdict="ARCHITECTURAL_EROSION",
            dde_passed=True,
            bdv_passed=True,
            acc_passed=False,
            dde_details={},
            bdv_details={},
            acc_details={'blocking_violations': 2}
        )

        # Test JSON export
        json_output = engine.export_report_json(report)
        assert json_output is not None
        json_data = json.loads(json_output)
        assert json_data['diagnosis_id'] == report.diagnosis_id
        assert json_data['verdict'] == report.verdict

        # Test HTML export
        html_output = engine.export_report_html(report)
        assert html_output is not None
        assert '<html>' in html_output
        assert report.diagnosis_id in html_output
        assert 'Root Cause Analysis' in html_output
        assert 'Recommendations' in html_output


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def diagnosis_engine():
    """Provide FailureDiagnosisEngine instance"""
    return FailureDiagnosisEngine()


@pytest.fixture
def sample_diagnosis_report():
    """Provide sample diagnosis report"""
    return DiagnosisReport(
        diagnosis_id="diag_20251013_120000",
        timestamp="2025-10-13T12:00:00Z",
        verdict="ARCHITECTURAL_EROSION",
        root_cause=RootCause(
            primary_stream=StreamType.ACC,
            confidence=0.85,
            description="Coupling violation in payment service",
            evidence=[
                "ACC-RULE-VIOLATION: MUST_NOT_CALL",
                "High coupling metric: Ce=15"
            ]
        ),
        correlation=Correlation(
            streams_affected=[StreamType.ACC],
            correlation_strength=0.92,
            pattern=FailurePattern.ARCHITECTURAL_EROSION,
            description="Architectural violations detected"
        ),
        recommendations=[
            Recommendation(
                priority=Priority.HIGH,
                impact=8,
                effort=3,
                title="Extract repository interface",
                description="Create PaymentRepository to isolate database access",
                code_location="services/payment.py:42",
                estimated_hours=4
            )
        ]
    )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
