"""
Quality Gate Integration
MD-2482: Integrate validation results with phase gates.

AC-2: Test results integrated with quality gates
AC-5: Architecture violations block phase progression
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from .bdv.test_runner import TestResults
from .acc.architecture_validator import ValidationResult

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Quality gate status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class GateResult:
    """Result of a quality gate check."""
    name: str
    status: GateStatus
    score: float = 100.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    blocking: bool = True


@dataclass
class QualityGateReport:
    """Complete quality gate report."""
    phase: str
    passed: bool
    gates: List[GateResult] = field(default_factory=list)
    overall_score: float = 0.0
    blocking_failures: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "phase": self.phase,
            "passed": self.passed,
            "overall_score": self.overall_score,
            "gates": [
                {
                    "name": g.name,
                    "status": g.status.value,
                    "score": g.score,
                    "message": g.message,
                }
                for g in self.gates
            ],
            "blocking_failures": self.blocking_failures,
        }


class QualityGateValidator:
    """
    Validate phase quality gates.
    
    AC-2: Test results integrated with quality gates
    AC-5: Architecture violations block phase progression
    """
    
    def __init__(
        self,
        test_coverage_threshold: float = 80.0,
        architecture_score_threshold: float = 70.0,
    ):
        """
        Initialize validator.
        
        Args:
            test_coverage_threshold: Minimum test coverage (%)
            architecture_score_threshold: Minimum architecture score
        """
        self.test_coverage_threshold = test_coverage_threshold
        self.architecture_score_threshold = architecture_score_threshold
    
    def validate_phase(
        self,
        phase: str,
        test_results: Optional[TestResults] = None,
        arch_results: Optional[ValidationResult] = None,
    ) -> QualityGateReport:
        """
        Validate all quality gates for a phase.
        
        Args:
            phase: Phase name
            test_results: BDV test results
            arch_results: ACC architecture validation results
            
        Returns:
            QualityGateReport with all gate results
        """
        gates: List[GateResult] = []
        blocking_failures: List[str] = []
        
        # Test execution gate
        if test_results:
            test_gate = self._validate_test_gate(test_results)
            gates.append(test_gate)
            if test_gate.status == GateStatus.FAILED and test_gate.blocking:
                blocking_failures.append(f"Tests: {test_gate.message}")
        
        # Coverage gate
        if test_results and test_results.coverage:
            coverage_gate = self._validate_coverage_gate(test_results)
            gates.append(coverage_gate)
            if coverage_gate.status == GateStatus.FAILED and coverage_gate.blocking:
                blocking_failures.append(f"Coverage: {coverage_gate.message}")
        
        # Architecture gate
        if arch_results:
            arch_gate = self._validate_architecture_gate(arch_results)
            gates.append(arch_gate)
            if arch_gate.status == GateStatus.FAILED and arch_gate.blocking:
                blocking_failures.append(f"Architecture: {arch_gate.message}")
        
        # Calculate overall score
        if gates:
            overall_score = sum(g.score for g in gates) / len(gates)
        else:
            overall_score = 100.0
        
        passed = len(blocking_failures) == 0
        
        report = QualityGateReport(
            phase=phase,
            passed=passed,
            gates=gates,
            overall_score=overall_score,
            blocking_failures=blocking_failures,
        )
        
        logger.info(
            f"Phase {phase} quality gate: {'PASSED' if passed else 'FAILED'} "
            f"(score: {overall_score:.1f})"
        )
        
        return report
    
    def _validate_test_gate(self, results: TestResults) -> GateResult:
        """Validate test execution gate."""
        if results.failed > 0 or results.errors > 0:
            return GateResult(
                name="Test Execution",
                status=GateStatus.FAILED,
                score=results.success_rate,
                message=f"{results.failed} tests failed, {results.errors} errors",
                details={"total": results.total, "passed": results.passed},
                blocking=True,
            )
        
        if results.total == 0:
            return GateResult(
                name="Test Execution",
                status=GateStatus.WARNING,
                score=0.0,
                message="No tests found",
                blocking=False,
            )
        
        return GateResult(
            name="Test Execution",
            status=GateStatus.PASSED,
            score=100.0,
            message=f"All {results.total} tests passed",
            details={"total": results.total, "duration": results.duration},
        )
    
    def _validate_coverage_gate(self, results: TestResults) -> GateResult:
        """Validate test coverage gate."""
        coverage = results.coverage
        if not coverage:
            return GateResult(
                name="Test Coverage",
                status=GateStatus.WARNING,
                score=0.0,
                message="Coverage data not available",
                blocking=False,
            )
        
        if coverage.coverage_percent < self.test_coverage_threshold:
            return GateResult(
                name="Test Coverage",
                status=GateStatus.FAILED,
                score=coverage.coverage_percent,
                message=f"Coverage {coverage.coverage_percent:.1f}% below threshold {self.test_coverage_threshold}%",
                blocking=True,
            )
        
        return GateResult(
            name="Test Coverage",
            status=GateStatus.PASSED,
            score=coverage.coverage_percent,
            message=f"Coverage {coverage.coverage_percent:.1f}% meets threshold",
        )
    
    def _validate_architecture_gate(self, results: ValidationResult) -> GateResult:
        """
        Validate architecture conformance gate.
        AC-5: Architecture violations block phase progression
        """
        blocking_count = len(results.blocking_violations)
        
        if blocking_count > 0:
            return GateResult(
                name="Architecture Conformance",
                status=GateStatus.FAILED,
                score=results.score,
                message=f"{blocking_count} blocking architecture violations",
                details={
                    "violations": [v.message for v in results.blocking_violations[:5]],
                },
                blocking=True,
            )
        
        if results.score < self.architecture_score_threshold:
            return GateResult(
                name="Architecture Conformance",
                status=GateStatus.WARNING,
                score=results.score,
                message=f"Architecture score {results.score:.1f} below threshold {self.architecture_score_threshold}",
                blocking=False,
            )
        
        return GateResult(
            name="Architecture Conformance",
            status=GateStatus.PASSED,
            score=results.score,
            message=f"Architecture conformance score: {results.score:.1f}",
            details={"pattern": results.pattern.value},
        )
