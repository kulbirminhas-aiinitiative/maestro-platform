"""
Completion Verifier for validating mission execution results.

Validates that mission execution meets all completion criteria including
required outputs, validation rules, and success thresholds.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Status of a verification check."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class VerificationRule:
    """A verification rule to apply."""
    name: str
    rule_type: str  # 'schema', 'completeness', 'custom'
    required: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    validator: Optional[Callable[[Any], bool]] = None


@dataclass
class VerificationResult:
    """Result of completion verification."""
    success: bool
    status: VerificationStatus
    completion_time: datetime
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed_rules: List[str] = field(default_factory=list)
    failed_rules: List[str] = field(default_factory=list)
    outputs_verified: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompletionVerifier:
    """
    Verifies mission completion against defined criteria.

    Supports:
    - Output presence validation
    - Schema validation
    - Completeness checks
    - Custom validation rules

    Example:
        >>> verifier = CompletionVerifier(strict_mode=True)
        >>> verifier.add_required_output("result")
        >>> verifier.add_rule(VerificationRule("schema", "schema"))
        >>> result = await verifier.verify_completion(execution_result)
    """

    def __init__(
        self,
        strict_mode: bool = True,
        required_outputs: Optional[List[str]] = None,
        validation_rules: Optional[List[str]] = None,
        async_mode: bool = False
    ):
        """
        Initialize the completion verifier.

        Args:
            strict_mode: If True, any failure causes overall failure
            required_outputs: List of required output keys
            validation_rules: List of rule types to apply
            async_mode: If True, run verifications concurrently
        """
        self.strict_mode = strict_mode
        self.async_mode = async_mode
        self._required_outputs: List[str] = required_outputs or []
        self._rules: List[VerificationRule] = []
        self._custom_validators: Dict[str, Callable[[Any], bool]] = {}
        self._execution_result: Optional[Any] = None
        self._outputs: Dict[str, Any] = {}

        # Add default rules based on validation_rules
        if validation_rules:
            for rule_type in validation_rules:
                self.add_rule(VerificationRule(
                    name=f"{rule_type}_check",
                    rule_type=rule_type,
                    required=True
                ))

        logger.info(f"CompletionVerifier initialized (strict={strict_mode})")

    def add_required_output(self, output_name: str) -> None:
        """
        Add a required output to verify.

        Args:
            output_name: Name of the required output
        """
        if output_name not in self._required_outputs:
            self._required_outputs.append(output_name)
            logger.debug(f"Added required output: {output_name}")

    def remove_required_output(self, output_name: str) -> None:
        """
        Remove a required output.

        Args:
            output_name: Name of the output to remove
        """
        if output_name in self._required_outputs:
            self._required_outputs.remove(output_name)

    def add_rule(self, rule: VerificationRule) -> None:
        """
        Add a verification rule.

        Args:
            rule: VerificationRule to add
        """
        self._rules.append(rule)
        logger.debug(f"Added verification rule: {rule.name}")

    def add_custom_validator(
        self,
        name: str,
        validator: Callable[[Any], bool]
    ) -> None:
        """
        Add a custom validation function.

        Args:
            name: Name for the validator
            validator: Function that returns True if valid
        """
        self._custom_validators[name] = validator
        self.add_rule(VerificationRule(
            name=name,
            rule_type="custom",
            required=True,
            validator=validator
        ))

    async def verify_completion(
        self,
        execution_result: Optional[Any] = None,
        outputs: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        Verify mission completion.

        Args:
            execution_result: Result from execution manager
            outputs: Dictionary of execution outputs

        Returns:
            VerificationResult with success status and details
        """
        self._execution_result = execution_result
        self._outputs = outputs or {}

        if execution_result and hasattr(execution_result, 'outputs'):
            self._outputs.update(execution_result.outputs)

        issues: List[str] = []
        warnings: List[str] = []
        passed_rules: List[str] = []
        failed_rules: List[str] = []
        outputs_verified: Dict[str, bool] = {}

        # Verify required outputs
        for output_name in self._required_outputs:
            if output_name in self._outputs:
                outputs_verified[output_name] = True
                logger.debug(f"Required output '{output_name}' present")
            else:
                outputs_verified[output_name] = False
                issues.append(f"Missing required output: {output_name}")
                logger.warning(f"Missing required output: {output_name}")

        # Run verification rules
        if self.async_mode:
            rule_results = await self._run_rules_async()
        else:
            rule_results = await self._run_rules_sequential()

        for rule_name, passed, issue in rule_results:
            if passed:
                passed_rules.append(rule_name)
            else:
                failed_rules.append(rule_name)
                if issue:
                    issues.append(issue)

        # Determine overall success
        if self.strict_mode:
            success = len(issues) == 0 and all(outputs_verified.values())
        else:
            # In non-strict mode, only required rule failures cause failure
            required_failures = [
                r for r in self._rules
                if r.name in failed_rules and r.required
            ]
            missing_required = [
                name for name, verified in outputs_verified.items()
                if not verified
            ]
            success = len(required_failures) == 0 and len(missing_required) == 0

        status = VerificationStatus.PASSED if success else VerificationStatus.FAILED
        if not success and not self.strict_mode and len(warnings) > 0:
            status = VerificationStatus.WARNING

        result = VerificationResult(
            success=success,
            status=status,
            completion_time=datetime.utcnow(),
            issues=issues,
            warnings=warnings,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            outputs_verified=outputs_verified,
            metadata={
                "strict_mode": self.strict_mode,
                "total_rules": len(self._rules),
                "total_required_outputs": len(self._required_outputs)
            }
        )

        logger.info(f"Verification complete: {status.value} ({len(passed_rules)}/{len(self._rules)} rules passed)")
        return result

    async def _run_rules_sequential(self) -> List[tuple]:
        """Run verification rules sequentially."""
        results = []
        for rule in self._rules:
            passed, issue = await self._execute_rule(rule)
            results.append((rule.name, passed, issue))
        return results

    async def _run_rules_async(self) -> List[tuple]:
        """Run verification rules concurrently."""
        tasks = [self._execute_rule(rule) for rule in self._rules]
        raw_results = await asyncio.gather(*tasks)
        return [
            (self._rules[i].name, passed, issue)
            for i, (passed, issue) in enumerate(raw_results)
        ]

    async def _execute_rule(self, rule: VerificationRule) -> tuple:
        """
        Execute a single verification rule.

        Returns:
            Tuple of (passed: bool, issue: Optional[str])
        """
        try:
            if rule.rule_type == "schema":
                return await self._verify_schema(rule)
            elif rule.rule_type == "completeness":
                return await self._verify_completeness(rule)
            elif rule.rule_type == "custom" and rule.validator:
                passed = rule.validator(self._outputs)
                return (passed, None if passed else f"Custom validation '{rule.name}' failed")
            else:
                logger.warning(f"Unknown rule type: {rule.rule_type}")
                return (True, None)  # Skip unknown rules
        except Exception as e:
            logger.error(f"Error executing rule {rule.name}: {e}")
            return (False, f"Rule execution error: {e}")

    async def _verify_schema(self, rule: VerificationRule) -> tuple:
        """Verify outputs match expected schema."""
        schema = rule.parameters.get("schema", {})

        if not schema:
            # No schema specified, check basic structure
            for key, value in self._outputs.items():
                if value is None and key in self._required_outputs:
                    return (False, f"Output '{key}' is None")

            return (True, None)

        # Validate against schema
        for field_name, field_type in schema.items():
            if field_name not in self._outputs:
                if rule.required:
                    return (False, f"Schema field '{field_name}' missing")
                continue

            value = self._outputs[field_name]
            if not isinstance(value, field_type):
                return (False, f"Schema type mismatch for '{field_name}'")

        return (True, None)

    async def _verify_completeness(self, rule: VerificationRule) -> tuple:
        """Verify execution completeness."""
        if self._execution_result is None:
            return (False, "No execution result provided")

        # Check execution status
        if hasattr(self._execution_result, 'status'):
            if self._execution_result.status not in ('completed', 'COMPLETED'):
                return (False, f"Execution status is '{self._execution_result.status}', not completed")

        # Check for failed tasks
        if hasattr(self._execution_result, 'tasks_failed'):
            if self._execution_result.tasks_failed > 0:
                threshold = rule.parameters.get("failure_threshold", 0)
                if self._execution_result.tasks_failed > threshold:
                    return (False, f"{self._execution_result.tasks_failed} tasks failed")

        # Check minimum completed tasks
        if hasattr(self._execution_result, 'tasks_completed'):
            min_tasks = rule.parameters.get("min_completed", 0)
            if self._execution_result.tasks_completed < min_tasks:
                return (False, f"Only {self._execution_result.tasks_completed} tasks completed (min: {min_tasks})")

        return (True, None)

    def get_rules(self) -> List[VerificationRule]:
        """Get all configured verification rules."""
        return self._rules.copy()

    def get_required_outputs(self) -> List[str]:
        """Get list of required outputs."""
        return self._required_outputs.copy()

    def clear(self) -> None:
        """Clear all rules and required outputs."""
        self._rules.clear()
        self._required_outputs.clear()
        self._custom_validators.clear()
        self._execution_result = None
        self._outputs.clear()
        logger.info("CompletionVerifier cleared")
