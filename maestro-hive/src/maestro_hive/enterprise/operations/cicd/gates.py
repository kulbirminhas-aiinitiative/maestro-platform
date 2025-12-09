"""
Quality Gates for Pipeline Stages.

Implements gate conditions between pipeline stages.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .stages import StageOutput


class GateCondition(str, Enum):
    """Gate condition types."""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"


@dataclass
class GateRule:
    """Single gate rule definition."""
    metric: str
    condition: GateCondition
    threshold: float
    required: bool = True
    description: str = ""

    def evaluate(self, value: float) -> bool:
        """Evaluate rule against value."""
        if self.condition == GateCondition.GREATER_THAN:
            return value > self.threshold
        elif self.condition == GateCondition.LESS_THAN:
            return value < self.threshold
        elif self.condition == GateCondition.EQUALS:
            return value == self.threshold
        elif self.condition == GateCondition.NOT_EQUALS:
            return value != self.threshold
        elif self.condition == GateCondition.GREATER_THAN_OR_EQUAL:
            return value >= self.threshold
        elif self.condition == GateCondition.LESS_THAN_OR_EQUAL:
            return value <= self.threshold
        return False


@dataclass
class GateResult:
    """Result of gate evaluation."""
    passed: bool
    reason: str = ""
    failed_rules: list[str] = field(default_factory=list)
    metrics_evaluated: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "reason": self.reason,
            "failed_rules": self.failed_rules,
            "metrics_evaluated": self.metrics_evaluated
        }


class QualityGate:
    """Quality gate between pipeline stages."""

    def __init__(self, name: str, rules: Optional[list[GateRule]] = None):
        self.name = name
        self.rules = rules or []
        self.after_stage: str = ""

    def add_rule(self, rule: GateRule) -> None:
        """Add rule to gate."""
        self.rules.append(rule)

    async def evaluate(self, stage_output: StageOutput) -> GateResult:
        """Evaluate if gate conditions are met."""
        failed_rules = []
        metrics_evaluated = {}

        for rule in self.rules:
            value = stage_output.metrics.get(rule.metric)
            metrics_evaluated[rule.metric] = value

            if value is None:
                if rule.required:
                    failed_rules.append(
                        f"Required metric '{rule.metric}' not found"
                    )
                continue

            if not rule.evaluate(float(value)):
                failed_rules.append(
                    f"{rule.metric}: {value} {rule.condition.value} {rule.threshold} failed"
                )

        if failed_rules:
            return GateResult(
                passed=False,
                reason="; ".join(failed_rules),
                failed_rules=failed_rules,
                metrics_evaluated=metrics_evaluated
            )

        return GateResult(
            passed=True,
            reason="All gate conditions met",
            metrics_evaluated=metrics_evaluated
        )


class CoverageGate(QualityGate):
    """Gate requiring minimum test coverage."""

    def __init__(self, min_coverage: float = 80.0, name: str = "coverage"):
        super().__init__(name)
        self.add_rule(GateRule(
            metric="coverage_percent",
            condition=GateCondition.GREATER_THAN_OR_EQUAL,
            threshold=min_coverage,
            description=f"Code coverage must be >= {min_coverage}%"
        ))


class SecurityGate(QualityGate):
    """Gate requiring zero critical/high vulnerabilities."""

    def __init__(self, name: str = "security"):
        super().__init__(name)
        self.add_rule(GateRule(
            metric="vulnerabilities_critical",
            condition=GateCondition.EQUALS,
            threshold=0,
            description="No critical vulnerabilities allowed"
        ))
        self.add_rule(GateRule(
            metric="vulnerabilities_high",
            condition=GateCondition.EQUALS,
            threshold=0,
            description="No high vulnerabilities allowed"
        ))


class TestGate(QualityGate):
    """Gate requiring all tests to pass."""

    def __init__(self, name: str = "tests"):
        super().__init__(name)
        self.add_rule(GateRule(
            metric="tests_failed",
            condition=GateCondition.EQUALS,
            threshold=0,
            description="All tests must pass"
        ))
