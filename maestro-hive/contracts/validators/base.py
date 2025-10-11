"""
Base Validator
Version: 1.0.0

Abstract base class for all validators with async execution and timeout support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of validation execution.
    """

    # Status
    passed: bool                        # True if validation passed
    score: float                         # Validation score (0.0-1.0)

    # Messages
    message: str                        # Primary message
    details: str = ""                   # Detailed explanation

    # Evidence
    evidence: Dict[str, Any] = field(default_factory=dict)  # Supporting data

    # Metadata
    validator_name: str = ""            # Name of validator
    validator_version: str = "1.0.0"    # Validator version
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: float = 0.0      # Execution time in milliseconds

    # Failures
    errors: List[str] = field(default_factory=list)        # Error messages
    warnings: List[str] = field(default_factory=list)      # Warning messages

    # Context
    criterion_id: Optional[str] = None  # Related criterion
    contract_id: Optional[str] = None   # Related contract

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "passed": self.passed,
            "score": self.score,
            "message": self.message,
            "details": self.details,
            "evidence": self.evidence,
            "validator_name": self.validator_name,
            "validator_version": self.validator_version,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors,
            "warnings": self.warnings,
            "criterion_id": self.criterion_id,
            "contract_id": self.contract_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """Deserialize from dictionary"""
        result = cls(
            passed=data["passed"],
            score=data["score"],
            message=data["message"],
            details=data.get("details", ""),
            evidence=data.get("evidence", {}),
            validator_name=data.get("validator_name", ""),
            validator_version=data.get("validator_version", "1.0.0"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            criterion_id=data.get("criterion_id"),
            contract_id=data.get("contract_id")
        )

        if "timestamp" in data:
            result.timestamp = datetime.fromisoformat(data["timestamp"])

        return result


class ValidationError(Exception):
    """Exception raised when validation fails"""
    pass


class BaseValidator(ABC):
    """
    Abstract base class for all validators.

    All validators must implement the validate() method which performs
    the actual validation logic.

    Features:
    - Async execution support
    - Timeout enforcement
    - Error handling
    - Evidence collection
    """

    def __init__(
        self,
        validator_name: str,
        validator_version: str = "1.0.0",
        timeout_seconds: float = 30.0
    ):
        """
        Initialize validator.

        Args:
            validator_name: Name of the validator
            validator_version: Version string
            timeout_seconds: Maximum execution time (default: 30s)
        """
        self.validator_name = validator_name
        self.validator_version = validator_version
        self.timeout_seconds = timeout_seconds

        logger.info(f"Initialized {validator_name} v{validator_version}")

    @abstractmethod
    async def validate(
        self,
        artifacts: Dict[str, Any],
        config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Perform validation (abstract method - must be implemented by subclasses).

        Args:
            artifacts: Dictionary of artifacts to validate
                {
                    "actual": Artifact or path to actual output,
                    "expected": Artifact or path to expected output (optional),
                    "config": Additional configuration (optional)
                }
            config: Validation configuration from acceptance criterion
                {
                    "threshold": 0.95,  # Example: similarity threshold
                    "strict": True,      # Example: strict mode
                    ... (validator-specific config)
                }

        Returns:
            ValidationResult with pass/fail status, score, and evidence

        Raises:
            ValidationError: If validation cannot be performed
        """
        pass

    async def execute(
        self,
        artifacts: Dict[str, Any],
        config: Dict[str, Any],
        criterion_id: Optional[str] = None,
        contract_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Execute validation with timeout and error handling.

        This method wraps the validate() method with:
        - Timeout enforcement
        - Execution time measurement
        - Error handling
        - Metadata population

        Args:
            artifacts: Artifacts to validate
            config: Validation configuration
            criterion_id: Related criterion ID (optional)
            contract_id: Related contract ID (optional)

        Returns:
            ValidationResult with complete metadata
        """
        start_time = datetime.utcnow()

        try:
            # Execute validation with timeout
            result = await asyncio.wait_for(
                self.validate(artifacts, config),
                timeout=self.timeout_seconds
            )

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Populate metadata
            result.validator_name = self.validator_name
            result.validator_version = self.validator_version
            result.timestamp = end_time
            result.execution_time_ms = execution_time_ms
            result.criterion_id = criterion_id
            result.contract_id = contract_id

            logger.info(
                f"{self.validator_name}: "
                f"{'PASS' if result.passed else 'FAIL'} "
                f"(score: {result.score:.2f}, time: {execution_time_ms:.0f}ms)"
            )

            return result

        except asyncio.TimeoutError:
            # Timeout exceeded
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(
                f"{self.validator_name}: TIMEOUT "
                f"(exceeded {self.timeout_seconds}s)"
            )

            return ValidationResult(
                passed=False,
                score=0.0,
                message=f"Validation timeout (>{self.timeout_seconds}s)",
                details=f"Validator exceeded maximum execution time of {self.timeout_seconds}s",
                validator_name=self.validator_name,
                validator_version=self.validator_version,
                timestamp=end_time,
                execution_time_ms=execution_time_ms,
                errors=[f"Timeout after {self.timeout_seconds}s"],
                criterion_id=criterion_id,
                contract_id=contract_id
            )

        except ValidationError as e:
            # Validation error
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(f"{self.validator_name}: ERROR - {str(e)}")

            return ValidationResult(
                passed=False,
                score=0.0,
                message="Validation error",
                details=str(e),
                validator_name=self.validator_name,
                validator_version=self.validator_version,
                timestamp=end_time,
                execution_time_ms=execution_time_ms,
                errors=[str(e)],
                criterion_id=criterion_id,
                contract_id=contract_id
            )

        except Exception as e:
            # Unexpected error
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            logger.exception(f"{self.validator_name}: UNEXPECTED ERROR - {str(e)}")

            return ValidationResult(
                passed=False,
                score=0.0,
                message="Unexpected validation error",
                details=f"Unexpected error: {type(e).__name__}: {str(e)}",
                validator_name=self.validator_name,
                validator_version=self.validator_version,
                timestamp=end_time,
                execution_time_ms=execution_time_ms,
                errors=[f"Unexpected error: {str(e)}"],
                criterion_id=criterion_id,
                contract_id=contract_id
            )

    def __repr__(self) -> str:
        return f"{self.validator_name} v{self.validator_version} (timeout: {self.timeout_seconds}s)"


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "ValidationResult",
    "ValidationError",
    "BaseValidator",
]
