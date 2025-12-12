#!/usr/bin/env python3
"""
Shift-Left Validator - Per-Group BDV/ACC Validation (MD-3093)

This module implements shift-left validation to detect issues early in the pipeline:
- BDV (Behavior-Driven Validation) checks run after each persona group
- ACC (Architectural Conformance Checking) runs incrementally
- Critical violations stop execution immediately
- Validator feedback reaches personas for correction

Architecture:
    ShiftLeftValidator
        ├── validate_group_bdv() - BDV checks per group (AC-1)
        ├── validate_group_acc() - ACC checks incrementally (AC-2)
        ├── check_critical_violations() - Early stop on critical (AC-3)
        └── generate_feedback() - Feedback for correction (AC-4)

Key Benefits:
    - Early failure detection (fail fast)
    - Reduced wasted work
    - Feedback loops for correction
    - Better quality gates
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

SHIFT_LEFT_CONFIG = {
    "enable_per_group_bdv": True,
    "enable_per_group_acc": True,
    "early_stop_on_critical": True,
    "max_correction_retries": 2,
    "critical_violation_threshold": 0.3,  # Stop if quality < 30%
    "feedback_enabled": True,
    "blocking_severity_threshold": "BLOCKING",
}


# =============================================================================
# DATA MODELS
# =============================================================================

class ViolationSeverity(str, Enum):
    """Severity levels for validation violations."""
    BLOCKING = "blocking"  # Stop execution immediately
    HIGH = "high"          # Log warning, continue but flag
    MEDIUM = "medium"      # Log info, continue
    LOW = "low"            # Silent pass


@dataclass
class ValidationViolation:
    """A single validation violation."""
    id: str
    severity: ViolationSeverity
    category: str  # "bdv", "acc", "contract", "security"
    message: str
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    rule_id: Optional[str] = None
    suggestion: Optional[str] = None

    def is_blocking(self) -> bool:
        """Check if this violation should block execution."""
        return self.severity == ViolationSeverity.BLOCKING


@dataclass
class ValidationFeedback:
    """
    Feedback for a persona to correct their work (AC-4).

    Contains actionable suggestions derived from validation failures.
    """
    persona_id: str
    violations: List[ValidationViolation]
    suggestions: List[str]
    affected_files: List[str]
    priority: ViolationSeverity
    retry_context: Dict[str, Any] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Convert feedback to prompt context for persona correction."""
        lines = [
            "VALIDATION FEEDBACK - Please correct the following issues:",
            "",
            f"Priority: {self.priority.value.upper()}",
            f"Affected files: {', '.join(self.affected_files)}",
            "",
            "Issues found:",
        ]

        for i, v in enumerate(self.violations, 1):
            lines.append(f"  {i}. [{v.severity.value.upper()}] {v.message}")
            if v.suggestion:
                lines.append(f"     Suggestion: {v.suggestion}")

        lines.extend(["", "Recommended corrections:"])
        for i, s in enumerate(self.suggestions, 1):
            lines.append(f"  {i}. {s}")

        return "\n".join(lines)


@dataclass
class GroupValidationResult:
    """Result of validating a single execution group."""
    group_id: str
    passed: bool
    bdv_score: float
    acc_score: float
    violations: List[ValidationViolation]
    feedback: Optional[ValidationFeedback] = None
    should_stop: bool = False
    stop_reason: Optional[str] = None
    validated_at: datetime = field(default_factory=datetime.now)

    @property
    def has_blocking_violations(self) -> bool:
        """Check if any violations are blocking."""
        return any(v.is_blocking() for v in self.violations)

    @property
    def combined_score(self) -> float:
        """Combined validation score (average of BDV and ACC)."""
        return (self.bdv_score + self.acc_score) / 2


class CriticalViolation(Exception):
    """
    Exception raised when critical violations require immediate stop (AC-3).

    This exception is caught by ParallelCoordinatorV2 to halt execution
    when blocking issues are detected.
    """

    def __init__(
        self,
        message: str,
        violations: List[ValidationViolation],
        group_id: str,
        validation_result: Optional[GroupValidationResult] = None
    ):
        super().__init__(message)
        self.violations = violations
        self.group_id = group_id
        self.validation_result = validation_result

    def get_blocking_violations(self) -> List[ValidationViolation]:
        """Get only the blocking violations."""
        return [v for v in self.violations if v.is_blocking()]


# =============================================================================
# SHIFT-LEFT VALIDATOR
# =============================================================================

class ShiftLeftValidator:
    """
    Orchestrates shift-left validation for per-group BDV/ACC checks.

    This validator integrates with ParallelCoordinatorV2 to run validation
    after each execution group, enabling early failure detection.

    Key Features:
        - Per-group BDV contract validation (AC-1)
        - Incremental ACC architectural checks (AC-2)
        - Critical violation detection with early stop (AC-3)
        - Feedback generation for persona correction (AC-4)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the shift-left validator.

        Args:
            config: Optional configuration override
        """
        self.config = {**SHIFT_LEFT_CONFIG, **(config or {})}
        self._bdv_service = None
        self._acc_service = None
        self._cumulative_state: Dict[str, Any] = {}
        self._validation_history: List[GroupValidationResult] = []

        logger.info("ShiftLeftValidator initialized")
        logger.info(f"  BDV per-group: {self.config['enable_per_group_bdv']}")
        logger.info(f"  ACC incremental: {self.config['enable_per_group_acc']}")
        logger.info(f"  Early stop: {self.config['early_stop_on_critical']}")

    def _get_bdv_service(self):
        """Lazy-load BDV service."""
        if self._bdv_service is None:
            try:
                from bdv.integration_service import get_bdv_integration_service
                self._bdv_service = get_bdv_integration_service()
                logger.info("  BDV service loaded")
            except ImportError:
                logger.warning("  BDV service not available")
        return self._bdv_service

    def _get_acc_service(self):
        """Lazy-load ACC service."""
        if self._acc_service is None:
            try:
                from acc.integration_service import get_acc_integration_service
                self._acc_service = get_acc_integration_service()
                logger.info("  ACC service loaded")
            except ImportError:
                logger.warning("  ACC service not available")
        return self._acc_service

    async def validate_group(
        self,
        group_id: str,
        group_result: Dict[str, Any],
        contracts: List[Dict[str, Any]],
        output_dir: Path,
        execution_id: str
    ) -> GroupValidationResult:
        """
        Validate a completed execution group.

        This is the main entry point called by ParallelCoordinatorV2 after
        each group completes.

        Args:
            group_id: Identifier for the execution group
            group_result: Results from persona execution
            contracts: Contracts fulfilled by this group
            output_dir: Directory containing generated files
            execution_id: Session/execution identifier

        Returns:
            GroupValidationResult with pass/fail status and any feedback

        Raises:
            CriticalViolation: If blocking violations detected and early_stop enabled
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"SHIFT-LEFT VALIDATION: {group_id}")
        logger.info(f"{'='*60}")

        violations: List[ValidationViolation] = []
        bdv_score = 1.0
        acc_score = 1.0

        # AC-1: BDV contract checks per group
        if self.config["enable_per_group_bdv"]:
            bdv_violations, bdv_score = await self._validate_group_bdv(
                group_id, group_result, contracts, execution_id
            )
            violations.extend(bdv_violations)

        # AC-2: ACC architectural checks incrementally
        if self.config["enable_per_group_acc"]:
            acc_violations, acc_score = await self._validate_group_acc(
                group_id, group_result, output_dir, execution_id
            )
            violations.extend(acc_violations)

        # Determine if we should stop
        should_stop = False
        stop_reason = None

        # AC-3: Check for critical violations
        if self.config["early_stop_on_critical"]:
            blocking = [v for v in violations if v.is_blocking()]
            if blocking:
                should_stop = True
                stop_reason = f"Found {len(blocking)} blocking violation(s)"

        # Check combined score threshold
        combined_score = (bdv_score + acc_score) / 2
        threshold = self.config["critical_violation_threshold"]
        if combined_score < threshold:
            should_stop = True
            stop_reason = f"Combined score {combined_score:.2f} below threshold {threshold}"

        # AC-4: Generate feedback for correction
        feedback = None
        if violations and self.config["feedback_enabled"]:
            feedback = self._generate_feedback(group_id, violations, group_result)

        # Build result
        result = GroupValidationResult(
            group_id=group_id,
            passed=not should_stop and len([v for v in violations if v.severity in [ViolationSeverity.BLOCKING, ViolationSeverity.HIGH]]) == 0,
            bdv_score=bdv_score,
            acc_score=acc_score,
            violations=violations,
            feedback=feedback,
            should_stop=should_stop,
            stop_reason=stop_reason
        )

        # Store in history
        self._validation_history.append(result)

        # Log summary
        self._log_validation_summary(result)

        # Raise exception if early stop required
        if should_stop and self.config["early_stop_on_critical"]:
            blocking = [v for v in violations if v.is_blocking()]
            raise CriticalViolation(
                message=stop_reason or "Critical validation failure",
                violations=blocking if blocking else violations[:5],
                group_id=group_id,
                validation_result=result
            )

        return result

    async def _validate_group_bdv(
        self,
        group_id: str,
        group_result: Dict[str, Any],
        contracts: List[Dict[str, Any]],
        execution_id: str
    ) -> tuple[List[ValidationViolation], float]:
        """
        AC-1: Run BDV contract checks for this group.

        Validates that contracts are properly fulfilled using BDV scenarios.
        """
        logger.info(f"  [BDV] Validating contracts for {group_id}...")

        violations = []
        score = 1.0

        bdv_service = self._get_bdv_service()
        if not bdv_service:
            logger.warning("  [BDV] Service not available, skipping")
            return violations, score

        try:
            # Prepare contracts for BDV
            contracts_for_bdv = []
            for contract in contracts:
                contracts_for_bdv.append({
                    'id': contract.get('id', ''),
                    'name': contract.get('name', ''),
                    'description': contract.get('description', ''),
                    'acceptance_criteria': contract.get('acceptance_criteria', []),
                    'deliverables': contract.get('deliverables', [])
                })

            if not contracts_for_bdv:
                logger.info("  [BDV] No contracts to validate")
                return violations, score

            # Run BDV validation
            bdv_result = bdv_service.validate_contracts(
                execution_id=f"{execution_id}_{group_id}",
                contracts=contracts_for_bdv,
                iteration_id=f"shift-left-{group_id}"
            )

            # Calculate score
            if bdv_result.total_contracts > 0:
                score = bdv_result.contracts_fulfilled / bdv_result.total_contracts

            # Convert failed scenarios to violations
            if hasattr(bdv_result, 'failed_scenarios'):
                for scenario in bdv_result.failed_scenarios:
                    violations.append(ValidationViolation(
                        id=f"bdv_{group_id}_{len(violations)}",
                        severity=ViolationSeverity.HIGH,
                        category="bdv",
                        message=f"BDV scenario failed: {scenario.get('name', 'Unknown')}",
                        rule_id=scenario.get('id'),
                        suggestion="Review contract acceptance criteria"
                    ))

            # Check for unfulfilled contracts
            unfulfilled = bdv_result.total_contracts - bdv_result.contracts_fulfilled
            if unfulfilled > 0:
                violations.append(ValidationViolation(
                    id=f"bdv_{group_id}_unfulfilled",
                    severity=ViolationSeverity.BLOCKING if unfulfilled > 1 else ViolationSeverity.HIGH,
                    category="bdv",
                    message=f"{unfulfilled} contract(s) not fulfilled",
                    suggestion="Ensure all contract deliverables are produced"
                ))

            logger.info(f"  [BDV] Score: {score:.2f} ({bdv_result.contracts_fulfilled}/{bdv_result.total_contracts} contracts)")

        except Exception as e:
            logger.error(f"  [BDV] Validation error: {e}")
            violations.append(ValidationViolation(
                id=f"bdv_{group_id}_error",
                severity=ViolationSeverity.MEDIUM,
                category="bdv",
                message=f"BDV validation error: {str(e)}",
                suggestion="Check BDV service availability"
            ))

        return violations, score

    async def _validate_group_acc(
        self,
        group_id: str,
        group_result: Dict[str, Any],
        output_dir: Path,
        execution_id: str
    ) -> tuple[List[ValidationViolation], float]:
        """
        AC-2: Run ACC architectural checks incrementally.

        Analyzes newly generated files for architectural compliance.
        """
        logger.info(f"  [ACC] Analyzing architecture for {group_id}...")

        violations = []
        score = 1.0

        acc_service = self._get_acc_service()
        if not acc_service:
            logger.warning("  [ACC] Service not available, skipping")
            return violations, score

        try:
            # Run ACC analysis
            acc_result = acc_service.validate_architecture(
                execution_id=f"{execution_id}_{group_id}",
                project_path=str(output_dir)
            )

            score = acc_result.conformance_score

            # Convert violations
            if hasattr(acc_result, 'violations') and acc_result.violations:
                # Handle blocking violations
                if hasattr(acc_result.violations, 'blocking') and acc_result.violations.blocking > 0:
                    violations.append(ValidationViolation(
                        id=f"acc_{group_id}_blocking",
                        severity=ViolationSeverity.BLOCKING,
                        category="acc",
                        message=f"{acc_result.violations.blocking} blocking architectural violation(s)",
                        suggestion="Review architecture compliance rules"
                    ))

                # Handle other violations
                if hasattr(acc_result.violations, 'total'):
                    non_blocking = acc_result.violations.total - getattr(acc_result.violations, 'blocking', 0)
                    if non_blocking > 0:
                        violations.append(ValidationViolation(
                            id=f"acc_{group_id}_warnings",
                            severity=ViolationSeverity.MEDIUM,
                            category="acc",
                            message=f"{non_blocking} architectural warning(s)",
                            suggestion="Consider addressing architectural warnings"
                        ))

            # Check for dependency cycles
            if hasattr(acc_result, 'cycles_detected') and acc_result.cycles_detected:
                for cycle in acc_result.cycles_detected[:3]:  # First 3 cycles
                    violations.append(ValidationViolation(
                        id=f"acc_{group_id}_cycle_{len(violations)}",
                        severity=ViolationSeverity.HIGH,
                        category="acc",
                        message=f"Dependency cycle detected: {cycle}",
                        suggestion="Refactor to remove circular dependencies"
                    ))

            logger.info(f"  [ACC] Score: {score:.2f} (compliant: {acc_result.is_compliant})")

            # Update cumulative state for incremental analysis
            self._cumulative_state[group_id] = {
                "conformance_score": score,
                "is_compliant": acc_result.is_compliant,
                "violations_count": acc_result.violations.total if hasattr(acc_result, 'violations') else 0
            }

        except Exception as e:
            logger.error(f"  [ACC] Validation error: {e}")
            violations.append(ValidationViolation(
                id=f"acc_{group_id}_error",
                severity=ViolationSeverity.MEDIUM,
                category="acc",
                message=f"ACC validation error: {str(e)}",
                suggestion="Check ACC service availability"
            ))

        return violations, score

    def _generate_feedback(
        self,
        group_id: str,
        violations: List[ValidationViolation],
        group_result: Dict[str, Any]
    ) -> ValidationFeedback:
        """
        AC-4: Generate actionable feedback for persona correction.

        Creates a ValidationFeedback object with suggestions for fixing issues.
        """
        # Determine responsible persona
        persona_id = "unknown"
        if isinstance(group_result, dict):
            # Get first persona from results
            for pid in group_result.keys():
                persona_id = pid
                break

        # Collect affected files
        affected_files = set()
        for v in violations:
            if v.source_file:
                affected_files.add(v.source_file)

        # Generate suggestions based on violation categories
        suggestions = []
        bdv_violations = [v for v in violations if v.category == "bdv"]
        acc_violations = [v for v in violations if v.category == "acc"]

        if bdv_violations:
            suggestions.append("Review contract acceptance criteria and ensure all deliverables are complete")
            suggestions.append("Verify generated code matches the contract specifications")

        if acc_violations:
            suggestions.append("Check architectural patterns and layer dependencies")
            suggestions.append("Review import statements for circular dependencies")

        # Add specific suggestions from violations
        for v in violations:
            if v.suggestion and v.suggestion not in suggestions:
                suggestions.append(v.suggestion)

        # Determine priority
        if any(v.severity == ViolationSeverity.BLOCKING for v in violations):
            priority = ViolationSeverity.BLOCKING
        elif any(v.severity == ViolationSeverity.HIGH for v in violations):
            priority = ViolationSeverity.HIGH
        else:
            priority = ViolationSeverity.MEDIUM

        return ValidationFeedback(
            persona_id=persona_id,
            violations=violations,
            suggestions=suggestions[:5],  # Top 5 suggestions
            affected_files=list(affected_files)[:10],  # Top 10 files
            priority=priority,
            retry_context={
                "group_id": group_id,
                "violation_count": len(violations),
                "retry_number": 0
            }
        )

    def _log_validation_summary(self, result: GroupValidationResult):
        """Log validation summary."""
        status = "PASS" if result.passed else ("BLOCKED" if result.should_stop else "WARN")
        symbol = "✅" if result.passed else ("🛑" if result.should_stop else "⚠️")

        logger.info(f"\n  {symbol} {status}: {result.group_id}")
        logger.info(f"     BDV Score: {result.bdv_score:.2f}")
        logger.info(f"     ACC Score: {result.acc_score:.2f}")
        logger.info(f"     Combined:  {result.combined_score:.2f}")
        logger.info(f"     Violations: {len(result.violations)}")

        if result.violations:
            by_severity = {}
            for v in result.violations:
                by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
            logger.info(f"     By severity: {by_severity}")

        if result.should_stop:
            logger.error(f"     EARLY STOP: {result.stop_reason}")

        logger.info(f"{'='*60}\n")

    def get_validation_history(self) -> List[GroupValidationResult]:
        """Get history of all group validations."""
        return self._validation_history.copy()

    def get_cumulative_score(self) -> float:
        """Get cumulative validation score across all groups."""
        if not self._validation_history:
            return 1.0
        return sum(r.combined_score for r in self._validation_history) / len(self._validation_history)

    def reset(self):
        """Reset validator state for new execution."""
        self._cumulative_state = {}
        self._validation_history = []
        logger.info("ShiftLeftValidator state reset")
