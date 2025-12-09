"""
Compliance Validator: Pre/post execution compliance validation for blocks.

EPIC: MD-2801 - Core Services & CLI Compliance (Batch 2)
AC-1: Core Compliance Integration

Provides compliance validation hooks for BlockInterface execution,
ensuring all block operations meet regulatory and security requirements.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import threading

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels."""
    MINIMAL = "minimal"       # Basic input validation only
    STANDARD = "standard"     # Input + output validation
    STRICT = "strict"         # Full compliance with all checks
    AUDIT = "audit"           # All checks + detailed logging


@dataclass
class ValidationResult:
    """Result of a compliance validation check."""
    valid: bool
    level: ValidationLevel
    timestamp: str
    checks_passed: int
    checks_failed: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = asdict(self)
        result['level'] = self.level.value
        return result


@dataclass
class ComplianceReport:
    """Comprehensive compliance report for an execution."""
    execution_id: str
    block_id: str
    timestamp: str
    pre_validation: Optional[ValidationResult] = None
    post_validation: Optional[ValidationResult] = None
    overall_compliant: bool = False
    compliance_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "execution_id": self.execution_id,
            "block_id": self.block_id,
            "timestamp": self.timestamp,
            "pre_validation": self.pre_validation.to_dict() if self.pre_validation else None,
            "post_validation": self.post_validation.to_dict() if self.post_validation else None,
            "overall_compliant": self.overall_compliant,
            "compliance_score": self.compliance_score,
            "recommendations": self.recommendations,
        }


class ComplianceValidator:
    """
    Compliance validation service for block executions.
    
    Integrates with BlockInterface to provide:
    - Pre-execution input validation
    - Post-execution output validation
    - Runtime compliance monitoring
    - Compliance report generation
    
    Thread-safe implementation using RLock for concurrent access.
    """

    _instance: Optional['ComplianceValidator'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global compliance access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        level: ValidationLevel = ValidationLevel.STANDARD,
        custom_validators: Optional[List[Callable]] = None,
        enabled: bool = True
    ):
        """
        Initialize the compliance validator.

        Args:
            level: Validation strictness level
            custom_validators: Additional validation functions
            enabled: Whether validation is active
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._level = level
        self._custom_validators = custom_validators or []
        self._enabled = enabled
        self._validation_lock = threading.RLock()
        self._reports: Dict[str, ComplianceReport] = {}
        self._initialized = True

        # Define validation rules
        self._input_rules = self._define_input_rules()
        self._output_rules = self._define_output_rules()

        logger.info(f"ComplianceValidator initialized with level: {level.value}")

    def _define_input_rules(self) -> List[Dict[str, Any]]:
        """Define input validation rules."""
        return [
            {
                "name": "non_empty_inputs",
                "description": "Inputs must not be empty",
                "check": lambda inputs: bool(inputs),
            },
            {
                "name": "no_dangerous_paths",
                "description": "No path traversal patterns",
                "check": lambda inputs: not any(
                    ".." in str(v) for v in inputs.values()
                ),
            },
            {
                "name": "valid_types",
                "description": "All input values must be serializable",
                "check": lambda inputs: self._check_serializable(inputs),
            },
            {
                "name": "size_limits",
                "description": "Input size within limits",
                "check": lambda inputs: len(json.dumps(inputs, default=str)) < 1_000_000,
            },
        ]

    def _define_output_rules(self) -> List[Dict[str, Any]]:
        """Define output validation rules."""
        return [
            {
                "name": "has_status",
                "description": "Output must have status",
                "check": lambda output: "status" in output or hasattr(output, 'status'),
            },
            {
                "name": "no_sensitive_data",
                "description": "No exposed secrets in output",
                "check": lambda output: not self._contains_sensitive(output),
            },
            {
                "name": "valid_structure",
                "description": "Output structure is valid",
                "check": lambda output: self._check_serializable(output),
            },
        ]

    def _check_serializable(self, data: Any) -> bool:
        """Check if data is JSON serializable."""
        try:
            json.dumps(data, default=str)
            return True
        except (TypeError, ValueError):
            return False

    def _contains_sensitive(self, data: Any) -> bool:
        """Check if data contains sensitive patterns."""
        sensitive_patterns = [
            "password", "secret", "token", "api_key", "private_key",
            "credential", "auth_token", "access_token"
        ]
        data_str = json.dumps(data, default=str).lower()
        return any(pattern in data_str for pattern in sensitive_patterns)

    def validate_inputs(
        self,
        inputs: Dict[str, Any],
        block_id: str = "unknown"
    ) -> ValidationResult:
        """
        Validate inputs before block execution.

        Args:
            inputs: Input dictionary to validate
            block_id: Block identifier for logging

        Returns:
            ValidationResult with validation outcome
        """
        if not self._enabled:
            return ValidationResult(
                valid=True,
                level=self._level,
                timestamp=datetime.utcnow().isoformat(),
                checks_passed=0,
                checks_failed=0,
                metadata={"validation_disabled": True}
            )

        with self._validation_lock:
            checks_passed = 0
            checks_failed = 0
            errors = []
            warnings = []

            for rule in self._input_rules:
                try:
                    if rule["check"](inputs):
                        checks_passed += 1
                    else:
                        checks_failed += 1
                        errors.append(f"Rule '{rule['name']}' failed: {rule['description']}")
                except Exception as e:
                    checks_failed += 1
                    errors.append(f"Rule '{rule['name']}' error: {str(e)}")

            # Run custom validators
            for validator in self._custom_validators:
                try:
                    if validator(inputs):
                        checks_passed += 1
                    else:
                        checks_failed += 1
                        warnings.append(f"Custom validator failed: {validator.__name__}")
                except Exception as e:
                    warnings.append(f"Custom validator error: {str(e)}")

            result = ValidationResult(
                valid=checks_failed == 0,
                level=self._level,
                timestamp=datetime.utcnow().isoformat(),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                warnings=warnings,
                errors=errors,
                metadata={
                    "block_id": block_id,
                    "input_hash": hashlib.sha256(
                        json.dumps(inputs, sort_keys=True, default=str).encode()
                    ).hexdigest()[:16]
                }
            )

            logger.debug(f"Input validation for {block_id}: valid={result.valid}")
            return result

    def validate_execution(
        self,
        block_result: Any,
        execution_id: str,
        block_id: str = "unknown"
    ) -> ValidationResult:
        """
        Validate block execution result.

        Args:
            block_result: Result from block execution
            execution_id: Unique execution identifier
            block_id: Block identifier

        Returns:
            ValidationResult with validation outcome
        """
        if not self._enabled:
            return ValidationResult(
                valid=True,
                level=self._level,
                timestamp=datetime.utcnow().isoformat(),
                checks_passed=0,
                checks_failed=0,
                metadata={"validation_disabled": True}
            )

        with self._validation_lock:
            checks_passed = 0
            checks_failed = 0
            errors = []
            warnings = []

            # Convert to dict if needed
            if hasattr(block_result, 'to_dict'):
                output = block_result.to_dict()
            elif hasattr(block_result, '__dict__'):
                output = vars(block_result)
            else:
                output = {"result": block_result}

            for rule in self._output_rules:
                try:
                    if rule["check"](output):
                        checks_passed += 1
                    else:
                        checks_failed += 1
                        if self._level == ValidationLevel.STRICT:
                            errors.append(f"Rule '{rule['name']}' failed: {rule['description']}")
                        else:
                            warnings.append(f"Rule '{rule['name']}' not satisfied")
                except Exception as e:
                    warnings.append(f"Rule '{rule['name']}' check error: {str(e)}")

            result = ValidationResult(
                valid=checks_failed == 0 or self._level != ValidationLevel.STRICT,
                level=self._level,
                timestamp=datetime.utcnow().isoformat(),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                warnings=warnings,
                errors=errors,
                metadata={
                    "execution_id": execution_id,
                    "block_id": block_id,
                }
            )

            logger.debug(f"Execution validation for {block_id}: valid={result.valid}")
            return result

    def validate_outputs(
        self,
        outputs: Dict[str, Any],
        block_id: str = "unknown"
    ) -> ValidationResult:
        """
        Validate outputs after block execution.

        Args:
            outputs: Output dictionary to validate
            block_id: Block identifier

        Returns:
            ValidationResult with validation outcome
        """
        return self.validate_execution(outputs, f"{block_id}_output", block_id)

    def generate_report(
        self,
        execution_id: str,
        block_id: str,
        pre_validation: Optional[ValidationResult] = None,
        post_validation: Optional[ValidationResult] = None
    ) -> ComplianceReport:
        """
        Generate comprehensive compliance report.

        Args:
            execution_id: Unique execution identifier
            block_id: Block identifier
            pre_validation: Pre-execution validation result
            post_validation: Post-execution validation result

        Returns:
            ComplianceReport with complete analysis
        """
        with self._validation_lock:
            # Calculate compliance score
            total_checks = 0
            passed_checks = 0

            if pre_validation:
                total_checks += pre_validation.checks_passed + pre_validation.checks_failed
                passed_checks += pre_validation.checks_passed

            if post_validation:
                total_checks += post_validation.checks_passed + post_validation.checks_failed
                passed_checks += post_validation.checks_passed

            compliance_score = (passed_checks / total_checks * 100) if total_checks > 0 else 100.0

            # Generate recommendations
            recommendations = []
            if pre_validation and pre_validation.errors:
                recommendations.append("Address input validation errors before execution")
            if post_validation and post_validation.warnings:
                recommendations.append("Review output for potential compliance issues")
            if compliance_score < 100:
                recommendations.append("Run full compliance audit for detailed analysis")

            report = ComplianceReport(
                execution_id=execution_id,
                block_id=block_id,
                timestamp=datetime.utcnow().isoformat(),
                pre_validation=pre_validation,
                post_validation=post_validation,
                overall_compliant=compliance_score >= 80,
                compliance_score=compliance_score,
                recommendations=recommendations,
            )

            # Store report
            self._reports[execution_id] = report

            logger.info(
                f"Compliance report for {block_id}: "
                f"score={compliance_score:.1f}%, compliant={report.overall_compliant}"
            )

            return report

    def get_report(self, execution_id: str) -> Optional[ComplianceReport]:
        """Retrieve stored compliance report."""
        return self._reports.get(execution_id)

    def set_level(self, level: ValidationLevel) -> None:
        """Update validation level."""
        self._level = level
        logger.info(f"Validation level updated to: {level.value}")

    def enable(self) -> None:
        """Enable validation."""
        self._enabled = True
        logger.info("Compliance validation enabled")

    def disable(self) -> None:
        """Disable validation."""
        self._enabled = False
        logger.info("Compliance validation disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if validation is enabled."""
        return self._enabled


def get_compliance_validator(**kwargs) -> ComplianceValidator:
    """Get the singleton ComplianceValidator instance."""
    return ComplianceValidator(**kwargs)
