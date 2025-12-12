"""
Best Practices Enforcer for Workflow Optimization
=================================================

Validates workflows against defined best practices and coding standards.
Ensures execution excellence through automated compliance checking.

EPIC: MD-2961 - Workflow Optimization & Standardization
AC-2: Implement best_practices_enforcer.py to validate workflows against best practices
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import json
import hashlib

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for best practice violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleCategory(Enum):
    """Categories of best practice rules."""
    RESILIENCE = "resilience"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    OBSERVABILITY = "observability"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


@dataclass
class ValidationResult:
    """Result of a single rule validation."""
    rule_id: str
    rule_name: str
    passed: bool
    severity: Severity
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable
        }


@dataclass
class ValidationReport:
    """Complete validation report for a workflow."""
    workflow_id: str
    workflow_name: str
    timestamp: datetime
    results: List[ValidationResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Check if all critical and error rules passed."""
        return not any(
            not r.passed and r.severity in (Severity.CRITICAL, Severity.ERROR)
            for r in self.results
        )

    @property
    def score(self) -> float:
        """Calculate compliance score (0-100)."""
        if not self.results:
            return 100.0

        weights = {
            Severity.CRITICAL: 10,
            Severity.ERROR: 5,
            Severity.WARNING: 2,
            Severity.INFO: 1
        }

        total_weight = sum(weights[r.severity] for r in self.results)
        passed_weight = sum(
            weights[r.severity] for r in self.results if r.passed
        )

        return (passed_weight / total_weight * 100) if total_weight > 0 else 100.0

    @property
    def violations(self) -> List[ValidationResult]:
        """Get all violations."""
        return [r for r in self.results if not r.passed]

    @property
    def critical_violations(self) -> List[ValidationResult]:
        """Get critical violations."""
        return [
            r for r in self.results
            if not r.passed and r.severity == Severity.CRITICAL
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.passed,
            "score": self.score,
            "total_rules": len(self.results),
            "violations_count": len(self.violations),
            "critical_count": len(self.critical_violations),
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata
        }


@dataclass
class Workflow:
    """Workflow definition to be validated."""
    id: str
    name: str
    steps: List[Dict[str, Any]]
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "steps": self.steps,
            "config": self.config,
            "metadata": self.metadata
        }


class BestPracticeRule(ABC):
    """Abstract base class for best practice rules."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        category: RuleCategory,
        severity: Severity
    ):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.category = category
        self.severity = severity
        self.enabled = True

    @abstractmethod
    def check(self, workflow: Workflow) -> ValidationResult:
        """Check the workflow against this rule."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "enabled": self.enabled
        }


class TimeoutRequiredRule(BestPracticeRule):
    """Ensures all steps have timeout configuration."""

    def __init__(self):
        super().__init__(
            rule_id="BP-RES-001",
            name="Timeout Required",
            description="All workflow steps must have a timeout configured",
            category=RuleCategory.RESILIENCE,
            severity=Severity.ERROR
        )

    def check(self, workflow: Workflow) -> ValidationResult:
        steps_without_timeout = []

        for i, step in enumerate(workflow.steps):
            if "timeout" not in step and "timeout_seconds" not in step:
                steps_without_timeout.append(f"Step {i + 1}: {step.get('name', 'unnamed')}")

        if steps_without_timeout:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message=f"Steps missing timeout: {', '.join(steps_without_timeout)}",
                suggestion="Add timeout_seconds: 30 to each step configuration",
                auto_fixable=True
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="All steps have timeout configured"
        )


class RetryConfiguredRule(BestPracticeRule):
    """Ensures steps that can fail have retry configuration."""

    def __init__(self):
        super().__init__(
            rule_id="BP-RES-002",
            name="Retry Configuration",
            description="Steps with external calls should have retry configuration",
            category=RuleCategory.RESILIENCE,
            severity=Severity.WARNING
        )
        self.external_step_types = {"api_call", "http", "database", "external_service"}

    def check(self, workflow: Workflow) -> ValidationResult:
        steps_needing_retry = []

        for i, step in enumerate(workflow.steps):
            step_type = step.get("type", "").lower()
            if step_type in self.external_step_types:
                if "retry" not in step and "retry_config" not in step:
                    steps_needing_retry.append(
                        f"Step {i + 1}: {step.get('name', 'unnamed')} ({step_type})"
                    )

        if steps_needing_retry:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message=f"External steps without retry: {', '.join(steps_needing_retry)}",
                suggestion="Add retry_config with max_attempts and backoff",
                auto_fixable=True
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="All external steps have retry configuration"
        )


class ErrorHandlingRule(BestPracticeRule):
    """Ensures proper error handling is configured."""

    def __init__(self):
        super().__init__(
            rule_id="BP-ERR-001",
            name="Error Handling Required",
            description="Workflows must have error handling configured",
            category=RuleCategory.ERROR_HANDLING,
            severity=Severity.ERROR
        )

    def check(self, workflow: Workflow) -> ValidationResult:
        has_error_handler = (
            "error_handler" in workflow.config or
            "on_error" in workflow.config or
            any("error_handler" in step or "on_error" in step for step in workflow.steps)
        )

        if not has_error_handler:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message="Workflow has no error handling configured",
                suggestion="Add error_handler or on_error configuration",
                auto_fixable=False
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="Error handling is configured"
        )


class LoggingConfiguredRule(BestPracticeRule):
    """Ensures logging is configured for observability."""

    def __init__(self):
        super().__init__(
            rule_id="BP-OBS-001",
            name="Logging Configuration",
            description="Workflows should have logging configured",
            category=RuleCategory.OBSERVABILITY,
            severity=Severity.WARNING
        )

    def check(self, workflow: Workflow) -> ValidationResult:
        has_logging = (
            "logging" in workflow.config or
            "log_level" in workflow.config or
            workflow.config.get("observability", {}).get("logging")
        )

        if not has_logging:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message="Workflow has no logging configuration",
                suggestion="Add logging configuration for observability",
                auto_fixable=True
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="Logging is configured"
        )


class InputValidationRule(BestPracticeRule):
    """Ensures inputs are validated."""

    def __init__(self):
        super().__init__(
            rule_id="BP-SEC-001",
            name="Input Validation",
            description="Workflow inputs must be validated",
            category=RuleCategory.SECURITY,
            severity=Severity.CRITICAL
        )

    def check(self, workflow: Workflow) -> ValidationResult:
        inputs = workflow.config.get("inputs", {})

        if inputs and not workflow.config.get("input_validation"):
            # Check if there's a validation step at the beginning
            first_step = workflow.steps[0] if workflow.steps else {}
            if first_step.get("type") != "validation":
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    passed=False,
                    severity=self.severity,
                    message="Workflow inputs are not validated",
                    suggestion="Add input_validation schema or validation step",
                    auto_fixable=False
                )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="Input validation is configured or not needed"
        )


class IdempotencyRule(BestPracticeRule):
    """Ensures write operations are idempotent."""

    def __init__(self):
        super().__init__(
            rule_id="BP-RES-003",
            name="Idempotency Check",
            description="Write operations should be idempotent",
            category=RuleCategory.RESILIENCE,
            severity=Severity.WARNING
        )
        self.write_step_types = {"write", "create", "update", "insert", "put"}

    def check(self, workflow: Workflow) -> ValidationResult:
        non_idempotent_steps = []

        for i, step in enumerate(workflow.steps):
            step_type = step.get("type", "").lower()
            if step_type in self.write_step_types:
                if not step.get("idempotent") and not step.get("idempotency_key"):
                    non_idempotent_steps.append(
                        f"Step {i + 1}: {step.get('name', 'unnamed')}"
                    )

        if non_idempotent_steps:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message=f"Non-idempotent write operations: {', '.join(non_idempotent_steps)}",
                suggestion="Add idempotency_key or mark step as idempotent: true",
                auto_fixable=False
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="Write operations are idempotent"
        )


class DocumentationRule(BestPracticeRule):
    """Ensures workflow has documentation."""

    def __init__(self):
        super().__init__(
            rule_id="BP-DOC-001",
            name="Documentation Required",
            description="Workflows should have description and documentation",
            category=RuleCategory.DOCUMENTATION,
            severity=Severity.INFO
        )

    def check(self, workflow: Workflow) -> ValidationResult:
        has_docs = bool(
            workflow.metadata.get("description") or
            workflow.metadata.get("documentation") or
            workflow.config.get("description")
        )

        if not has_docs:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message="Workflow lacks documentation",
                suggestion="Add description in metadata or config",
                auto_fixable=False
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="Documentation is present"
        )


class CircuitBreakerRule(BestPracticeRule):
    """Ensures circuit breaker is configured for external services."""

    def __init__(self):
        super().__init__(
            rule_id="BP-RES-004",
            name="Circuit Breaker Configuration",
            description="External service calls should have circuit breaker",
            category=RuleCategory.RESILIENCE,
            severity=Severity.WARNING
        )
        self.external_step_types = {"api_call", "http", "external_service", "rpc"}

    def check(self, workflow: Workflow) -> ValidationResult:
        steps_needing_cb = []

        for i, step in enumerate(workflow.steps):
            step_type = step.get("type", "").lower()
            if step_type in self.external_step_types:
                if not step.get("circuit_breaker"):
                    steps_needing_cb.append(
                        f"Step {i + 1}: {step.get('name', 'unnamed')}"
                    )

        if steps_needing_cb:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message=f"Steps without circuit breaker: {', '.join(steps_needing_cb)}",
                suggestion="Add circuit_breaker configuration",
                auto_fixable=True
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="Circuit breakers are configured"
        )


class MetricsRule(BestPracticeRule):
    """Ensures metrics are configured for observability."""

    def __init__(self):
        super().__init__(
            rule_id="BP-OBS-002",
            name="Metrics Configuration",
            description="Workflows should emit metrics",
            category=RuleCategory.OBSERVABILITY,
            severity=Severity.INFO
        )

    def check(self, workflow: Workflow) -> ValidationResult:
        has_metrics = (
            workflow.config.get("metrics") or
            workflow.config.get("observability", {}).get("metrics")
        )

        if not has_metrics:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                passed=False,
                severity=self.severity,
                message="Workflow has no metrics configuration",
                suggestion="Add metrics configuration for monitoring",
                auto_fixable=True
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=True,
            severity=self.severity,
            message="Metrics are configured"
        )


class BestPracticesEnforcer:
    """
    Central enforcer for workflow best practices.

    Validates workflows against a set of configurable rules and generates
    detailed compliance reports.
    """

    def __init__(self):
        self._rules: Dict[str, BestPracticeRule] = {}
        self._rule_sets: Dict[str, Set[str]] = {}
        self._cache: Dict[str, ValidationReport] = {}
        self._register_default_rules()
        self._register_default_rule_sets()

    def _register_default_rules(self) -> None:
        """Register built-in best practice rules."""
        default_rules = [
            TimeoutRequiredRule(),
            RetryConfiguredRule(),
            ErrorHandlingRule(),
            LoggingConfiguredRule(),
            InputValidationRule(),
            IdempotencyRule(),
            DocumentationRule(),
            CircuitBreakerRule(),
            MetricsRule(),
        ]

        for rule in default_rules:
            self.register_rule(rule)

    def _register_default_rule_sets(self) -> None:
        """Register default rule sets."""
        self._rule_sets["minimal"] = {
            "BP-RES-001",  # Timeout
            "BP-ERR-001",  # Error handling
            "BP-SEC-001",  # Input validation
        }

        self._rule_sets["standard"] = {
            "BP-RES-001", "BP-RES-002", "BP-RES-003",
            "BP-ERR-001",
            "BP-SEC-001",
            "BP-OBS-001",
            "BP-DOC-001",
        }

        self._rule_sets["strict"] = set(self._rules.keys())

    def register_rule(self, rule: BestPracticeRule) -> None:
        """Register a new rule."""
        if rule.rule_id in self._rules:
            logger.warning(f"Overwriting existing rule: {rule.rule_id}")
        self._rules[rule.rule_id] = rule
        logger.info(f"Registered rule: {rule.rule_id} - {rule.name}")

    def register_rule_set(self, name: str, rule_ids: Set[str]) -> None:
        """Register a named set of rules."""
        self._rule_sets[name] = rule_ids
        logger.info(f"Registered rule set: {name} with {len(rule_ids)} rules")

    def get_rule(self, rule_id: str) -> Optional[BestPracticeRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        category: Optional[RuleCategory] = None,
        severity: Optional[Severity] = None,
        enabled_only: bool = True
    ) -> List[BestPracticeRule]:
        """List rules with optional filtering."""
        rules = list(self._rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]
        if category:
            rules = [r for r in rules if r.category == category]
        if severity:
            rules = [r for r in rules if r.severity == severity]

        return rules

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def validate(
        self,
        workflow: Workflow,
        rule_set: Optional[str] = None,
        rule_ids: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> ValidationReport:
        """
        Validate a workflow against best practices.

        Args:
            workflow: The workflow to validate
            rule_set: Name of a predefined rule set to use
            rule_ids: Specific rule IDs to check (overrides rule_set)
            use_cache: Whether to use cached results

        Returns:
            ValidationReport with all results
        """
        # Check cache
        cache_key = self._get_cache_key(workflow, rule_set, rule_ids)
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached validation for workflow {workflow.id}")
            return self._cache[cache_key]

        # Determine which rules to run
        if rule_ids:
            rules_to_run = [self._rules[rid] for rid in rule_ids if rid in self._rules]
        elif rule_set and rule_set in self._rule_sets:
            rules_to_run = [
                self._rules[rid]
                for rid in self._rule_sets[rule_set]
                if rid in self._rules and self._rules[rid].enabled
            ]
        else:
            rules_to_run = [r for r in self._rules.values() if r.enabled]

        # Run validations
        results = []
        for rule in rules_to_run:
            try:
                result = rule.check(workflow)
                results.append(result)
                logger.debug(
                    f"Rule {rule.rule_id}: {'PASS' if result.passed else 'FAIL'}"
                )
            except Exception as e:
                logger.error(f"Error running rule {rule.rule_id}: {e}")
                results.append(ValidationResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    passed=False,
                    severity=Severity.ERROR,
                    message=f"Rule execution error: {str(e)}"
                ))

        # Create report
        report = ValidationReport(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            timestamp=datetime.utcnow(),
            results=results,
            metadata={
                "rule_set": rule_set,
                "rules_checked": len(rules_to_run),
                "workflow_steps": len(workflow.steps)
            }
        )

        # Cache result
        self._cache[cache_key] = report

        logger.info(
            f"Validation complete for {workflow.id}: "
            f"Score={report.score:.1f}, Passed={report.passed}"
        )

        return report

    def _get_cache_key(
        self,
        workflow: Workflow,
        rule_set: Optional[str],
        rule_ids: Optional[List[str]]
    ) -> str:
        """Generate cache key for validation."""
        workflow_hash = hashlib.md5(
            json.dumps(workflow.to_dict(), sort_keys=True).encode()
        ).hexdigest()

        rules_hash = hashlib.md5(
            json.dumps({
                "rule_set": rule_set,
                "rule_ids": sorted(rule_ids) if rule_ids else None
            }, sort_keys=True).encode()
        ).hexdigest()

        return f"{workflow_hash}:{rules_hash}"

    def clear_cache(self) -> None:
        """Clear validation cache."""
        self._cache.clear()
        logger.info("Validation cache cleared")

    def validate_multiple(
        self,
        workflows: List[Workflow],
        rule_set: Optional[str] = None
    ) -> Dict[str, ValidationReport]:
        """Validate multiple workflows."""
        results = {}
        for workflow in workflows:
            results[workflow.id] = self.validate(workflow, rule_set)
        return results

    def export_rules(self) -> Dict[str, Any]:
        """Export all rules configuration."""
        return {
            "version": "1.0.0",
            "rules": [rule.to_dict() for rule in self._rules.values()],
            "rule_sets": {
                name: list(rules) for name, rules in self._rule_sets.items()
            }
        }


# Singleton instance
_enforcer_instance: Optional[BestPracticesEnforcer] = None


def get_best_practices_enforcer() -> BestPracticesEnforcer:
    """Get the singleton enforcer instance."""
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = BestPracticesEnforcer()
    return _enforcer_instance


def validate_workflow(
    workflow: Workflow,
    rule_set: str = "standard"
) -> ValidationReport:
    """Convenience function to validate a workflow."""
    enforcer = get_best_practices_enforcer()
    return enforcer.validate(workflow, rule_set)


def quick_check(workflow: Workflow) -> Tuple[bool, float]:
    """Quick check returning (passed, score)."""
    report = validate_workflow(workflow, "minimal")
    return report.passed, report.score
