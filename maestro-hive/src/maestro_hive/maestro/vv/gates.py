"""
Quality Gate Engine for Verification & Validation.

EPIC: MD-2521 - [SDLC-Phase7] Verification & Validation
AC-1: Quality Gate Engine - Configurable gates with pass/fail thresholds and policy enforcement

This module provides:
- Gate definition with configurable thresholds
- Policy-based enforcement (mandatory vs advisory)
- Gate result caching for performance
- Integration with CI/CD pipeline stages
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class GateType(Enum):
    """Types of quality gates."""
    MANDATORY = "mandatory"  # Must pass to proceed
    ADVISORY = "advisory"    # Warning only, does not block
    BLOCKING = "blocking"    # Blocks until resolved


class GateStatus(Enum):
    """Gate evaluation status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class GateResult:
    """Result of a gate evaluation."""
    gate_id: str
    status: GateStatus
    score: float  # 0.0 to 1.0
    threshold: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def passed(self) -> bool:
        """Check if gate passed."""
        return self.status == GateStatus.PASSED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gate_id": self.gate_id,
            "status": self.status.value,
            "score": self.score,
            "threshold": self.threshold,
            "message": self.message,
            "details": self.details,
            "evaluated_at": self.evaluated_at.isoformat()
        }


@dataclass
class QualityGate:
    """
    Definition of a quality gate.

    A gate evaluates some aspect of the codebase/workflow and determines
    if quality thresholds are met.
    """
    gate_id: str
    name: str
    description: str
    gate_type: GateType
    threshold: float  # 0.0 to 1.0
    evaluator: Optional[Callable[[Any], float]] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, context: Any) -> GateResult:
        """
        Evaluate this gate against the provided context.

        Args:
            context: The data/context to evaluate

        Returns:
            GateResult with evaluation outcome
        """
        if not self.enabled:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.SKIPPED,
                score=0.0,
                threshold=self.threshold,
                message=f"Gate '{self.name}' is disabled"
            )

        if self.evaluator is None:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.ERROR,
                score=0.0,
                threshold=self.threshold,
                message=f"Gate '{self.name}' has no evaluator"
            )

        try:
            score = self.evaluator(context)
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

            passed = score >= self.threshold
            status = GateStatus.PASSED if passed else GateStatus.FAILED

            return GateResult(
                gate_id=self.gate_id,
                status=status,
                score=score,
                threshold=self.threshold,
                message=f"Gate '{self.name}' {'passed' if passed else 'failed'}: {score:.2%} (threshold: {self.threshold:.2%})"
            )
        except Exception as e:
            logger.error(f"Gate evaluation error for {self.gate_id}: {e}")
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.ERROR,
                score=0.0,
                threshold=self.threshold,
                message=f"Gate evaluation error: {str(e)}",
                details={"error": str(e)}
            )


@dataclass
class GatePolicy:
    """
    Policy for a set of quality gates.

    Defines how gates should be evaluated and what happens on failure.
    """
    policy_id: str
    name: str
    gates: List[QualityGate]
    require_all: bool = True  # All mandatory gates must pass
    fail_fast: bool = False   # Stop on first failure

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "gate_count": len(self.gates),
            "require_all": self.require_all,
            "fail_fast": self.fail_fast
        }


class GateEngine:
    """
    Engine for evaluating quality gates.

    Manages gate policies, caches results, and provides
    integration points for CI/CD pipelines.
    """

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize the gate engine.

        Args:
            cache_enabled: Whether to cache gate results
        """
        self._policies: Dict[str, GatePolicy] = {}
        self._gates: Dict[str, QualityGate] = {}
        self._cache: Dict[str, GateResult] = {}
        self._cache_enabled = cache_enabled
        self._evaluation_history: List[Dict[str, Any]] = []
        logger.info("GateEngine initialized")

    def register_gate(self, gate: QualityGate) -> None:
        """
        Register a quality gate.

        Args:
            gate: The gate to register
        """
        self._gates[gate.gate_id] = gate
        logger.debug(f"Registered gate: {gate.gate_id}")

    def register_policy(self, policy: GatePolicy) -> None:
        """
        Register a gate policy.

        Args:
            policy: The policy to register
        """
        self._policies[policy.policy_id] = policy
        # Also register all gates in the policy
        for gate in policy.gates:
            self.register_gate(gate)
        logger.debug(f"Registered policy: {policy.policy_id} with {len(policy.gates)} gates")

    def get_gate(self, gate_id: str) -> Optional[QualityGate]:
        """Get a registered gate by ID."""
        return self._gates.get(gate_id)

    def get_policy(self, policy_id: str) -> Optional[GatePolicy]:
        """Get a registered policy by ID."""
        return self._policies.get(policy_id)

    def evaluate_gate(self, gate_id: str, context: Any, use_cache: bool = True) -> GateResult:
        """
        Evaluate a single gate.

        Args:
            gate_id: ID of the gate to evaluate
            context: Context data to evaluate against
            use_cache: Whether to use cached results

        Returns:
            GateResult with evaluation outcome
        """
        gate = self._gates.get(gate_id)
        if gate is None:
            return GateResult(
                gate_id=gate_id,
                status=GateStatus.ERROR,
                score=0.0,
                threshold=0.0,
                message=f"Gate '{gate_id}' not found"
            )

        # Check cache
        cache_key = self._compute_cache_key(gate_id, context)
        if use_cache and self._cache_enabled and cache_key in self._cache:
            logger.debug(f"Cache hit for gate {gate_id}")
            return self._cache[cache_key]

        # Evaluate gate
        result = gate.evaluate(context)

        # Cache result
        if self._cache_enabled:
            self._cache[cache_key] = result

        # Record in history
        self._evaluation_history.append({
            "gate_id": gate_id,
            "result": result.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })

        return result

    def evaluate_policy(self, policy_id: str, context: Any) -> Dict[str, Any]:
        """
        Evaluate all gates in a policy.

        Args:
            policy_id: ID of the policy to evaluate
            context: Context data to evaluate against

        Returns:
            Dictionary with overall result and individual gate results
        """
        policy = self._policies.get(policy_id)
        if policy is None:
            return {
                "policy_id": policy_id,
                "status": "error",
                "message": f"Policy '{policy_id}' not found",
                "gate_results": []
            }

        results: List[GateResult] = []
        mandatory_passed = True
        advisory_warnings = []

        for gate in policy.gates:
            result = self.evaluate_gate(gate.gate_id, context)
            results.append(result)

            if gate.gate_type == GateType.MANDATORY and not result.passed:
                mandatory_passed = False
                if policy.fail_fast:
                    break

            if gate.gate_type == GateType.ADVISORY and not result.passed:
                advisory_warnings.append(result.message)

        overall_passed = mandatory_passed if policy.require_all else any(r.passed for r in results)

        return {
            "policy_id": policy_id,
            "policy_name": policy.name,
            "status": "passed" if overall_passed else "failed",
            "mandatory_passed": mandatory_passed,
            "advisory_warnings": advisory_warnings,
            "gate_results": [r.to_dict() for r in results],
            "evaluated_at": datetime.utcnow().isoformat()
        }

    def clear_cache(self) -> None:
        """Clear the result cache."""
        self._cache.clear()
        logger.debug("Gate cache cleared")

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get evaluation history."""
        return self._evaluation_history[-limit:]

    def _compute_cache_key(self, gate_id: str, context: Any) -> str:
        """Compute a cache key for gate + context."""
        context_str = str(context)
        combined = f"{gate_id}:{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()


# Built-in gate evaluators
def test_coverage_evaluator(context: Dict[str, Any]) -> float:
    """Evaluate test coverage percentage."""
    covered = context.get("covered_lines", 0)
    total = context.get("total_lines", 1)
    return covered / total if total > 0 else 0.0


def test_pass_rate_evaluator(context: Dict[str, Any]) -> float:
    """Evaluate test pass rate."""
    passed = context.get("tests_passed", 0)
    total = context.get("tests_total", 1)
    return passed / total if total > 0 else 0.0


def code_complexity_evaluator(context: Dict[str, Any]) -> float:
    """Evaluate code complexity (lower is better)."""
    avg_complexity = context.get("average_complexity", 10)
    # Score: 1.0 for complexity <= 5, 0.0 for complexity >= 20
    if avg_complexity <= 5:
        return 1.0
    elif avg_complexity >= 20:
        return 0.0
    else:
        return 1.0 - (avg_complexity - 5) / 15


def security_scan_evaluator(context: Dict[str, Any]) -> float:
    """Evaluate security scan results."""
    critical = context.get("critical_issues", 0)
    high = context.get("high_issues", 0)
    medium = context.get("medium_issues", 0)

    # Critical issues are weighted heavily
    if critical > 0:
        return 0.0
    if high > 2:
        return 0.3
    if medium > 5:
        return 0.6
    return 1.0


# Pre-defined quality gates
BUILTIN_GATES = {
    "test_coverage": QualityGate(
        gate_id="test_coverage",
        name="Test Coverage",
        description="Minimum test coverage threshold",
        gate_type=GateType.MANDATORY,
        threshold=0.80,
        evaluator=test_coverage_evaluator
    ),
    "test_pass_rate": QualityGate(
        gate_id="test_pass_rate",
        name="Test Pass Rate",
        description="All tests must pass",
        gate_type=GateType.MANDATORY,
        threshold=1.0,
        evaluator=test_pass_rate_evaluator
    ),
    "code_complexity": QualityGate(
        gate_id="code_complexity",
        name="Code Complexity",
        description="Code complexity threshold",
        gate_type=GateType.ADVISORY,
        threshold=0.7,
        evaluator=code_complexity_evaluator
    ),
    "security_scan": QualityGate(
        gate_id="security_scan",
        name="Security Scan",
        description="Security vulnerability check",
        gate_type=GateType.BLOCKING,
        threshold=0.8,
        evaluator=security_scan_evaluator
    )
}


def create_standard_policy() -> GatePolicy:
    """Create a standard quality gate policy."""
    return GatePolicy(
        policy_id="standard",
        name="Standard Quality Policy",
        gates=list(BUILTIN_GATES.values()),
        require_all=True,
        fail_fast=False
    )
