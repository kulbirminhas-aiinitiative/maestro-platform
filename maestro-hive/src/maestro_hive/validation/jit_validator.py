"""
JIT Validator - Main Validation Orchestrator (MD-3092)

This module implements the complete JIT validation flow:
- AC-1: ast.parse() runs on all generated Python files
- AC-2: Syntax errors trigger internal retry (max 3)
- AC-3: Personas can execute tests on generated code
- AC-4: Failed tests trigger reflection + retry
- AC-5: HelpNeeded raised after exhausting retries

Implements the Generate → Test → Reflect → Refine loop.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .syntax_checker import SyntaxChecker, SyntaxCheckResult
from .reflection_engine import ReflectionEngine, ReflectionResult
from .test_runner import TestRunner, TestResult
from .exceptions import HelpNeeded, HelpNeededContext, ValidationError


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Comprehensive validation result.
    
    Attributes:
        valid: Overall validation status
        syntax_result: Result of syntax check
        test_result: Result of test execution
        reflection_result: Result of reflection (if errors)
        attempts: Number of validation attempts
        max_attempts: Maximum allowed attempts
        validation_time_ms: Total validation time
    """
    valid: bool
    syntax_result: Optional[SyntaxCheckResult] = None
    test_result: Optional[TestResult] = None
    reflection_result: Optional[ReflectionResult] = None
    attempts: int = 1
    max_attempts: int = 3
    validation_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "valid": self.valid,
            "syntax_result": self.syntax_result.to_dict() if self.syntax_result else None,
            "test_result": self.test_result.to_dict() if self.test_result else None,
            "reflection_result": self.reflection_result.to_dict() if self.reflection_result else None,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "validation_time_ms": self.validation_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class JITValidator:
    """
    JIT (Just-In-Time) Validator for persona-generated code.
    
    Orchestrates the complete validation flow:
    
    ```
    Generate → Validate Syntax → Run Tests → Reflect → Refine
                    ↑                              |
                    └──────────────────────────────┘
                              (retry loop)
    ```
    
    Implements all acceptance criteria:
    - AC-1: ast.parse() on all Python files
    - AC-2: Syntax errors trigger retry (max 3)
    - AC-3: Test execution on generated code
    - AC-4: Failed tests trigger reflection
    - AC-5: HelpNeeded after exhausting retries
    
    Example:
        >>> validator = JITValidator(max_attempts=3)
        >>> 
        >>> # Validate code with retry loop
        >>> result = validator.validate_with_retry(
        ...     code="def foo(): return 42",
        ...     refine_callback=my_refine_function
        ... )
        >>> 
        >>> if result.valid:
        ...     print("Code passed validation!")
        ... else:
        ...     print(f"Validation failed after {result.attempts} attempts")
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        run_tests: bool = True,
        syntax_checker: Optional[SyntaxChecker] = None,
        reflection_engine: Optional[ReflectionEngine] = None,
        test_runner: Optional[TestRunner] = None
    ):
        """
        Initialize the JIT validator.
        
        Args:
            max_attempts: Maximum retry attempts (AC-2: default 3)
            run_tests: Whether to run tests (AC-3)
            syntax_checker: Custom syntax checker
            reflection_engine: Custom reflection engine
            test_runner: Custom test runner
        """
        self.max_attempts = max_attempts
        self.run_tests = run_tests
        
        # Initialize components
        self.syntax_checker = syntax_checker or SyntaxChecker()
        self.reflection_engine = reflection_engine or ReflectionEngine()
        self.test_runner = test_runner or TestRunner()
        
        # Validation history
        self._history: List[ValidationResult] = []
        
        logger.info(f"JITValidator initialized (max_attempts={max_attempts})")
    
    def validate_code(
        self,
        code: str,
        filename: str = "<generated>",
        test_code: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate generated Python code.
        
        Implements AC-1: ast.parse() on generated code.
        
        Args:
            code: Python source code to validate
            filename: Filename for error reporting
            test_code: Optional test code to execute
        
        Returns:
            ValidationResult with all check results
        """
        import time
        start_time = time.perf_counter()
        
        # AC-1: Syntax check
        syntax_result = self.syntax_checker.check(code, filename)
        
        if not syntax_result.valid:
            # Syntax error - reflect on it
            reflection = self.reflection_engine.reflect_on_syntax_error(syntax_result)
            
            validation_time = (time.perf_counter() - start_time) * 1000
            
            return ValidationResult(
                valid=False,
                syntax_result=syntax_result,
                reflection_result=reflection,
                validation_time_ms=validation_time
            )
        
        # AC-3: Run tests if provided
        test_result = None
        reflection_result = None
        
        if self.run_tests and test_code:
            test_result = self.test_runner.run_test_code(
                test_code=test_code,
                implementation_code=code
            )
            
            if not test_result.success:
                # AC-4: Test failure - reflect on it
                reflection_result = self.reflection_engine.reflect_on_test_failure(
                    test_output=test_result.output,
                    failed_tests=test_result.failed_tests,
                    code=code
                )
        
        validation_time = (time.perf_counter() - start_time) * 1000
        
        is_valid = syntax_result.valid and (test_result is None or test_result.success)
        
        result = ValidationResult(
            valid=is_valid,
            syntax_result=syntax_result,
            test_result=test_result,
            reflection_result=reflection_result,
            validation_time_ms=validation_time
        )
        
        self._history.append(result)
        
        return result
    
    def validate_with_retry(
        self,
        code: str,
        filename: str = "<generated>",
        test_code: Optional[str] = None,
        refine_callback: Optional[Callable[[str, ReflectionResult], str]] = None,
        persona_id: str = "unknown"
    ) -> ValidationResult:
        """
        Validate code with automatic retry loop.
        
        Implements:
        - AC-2: Syntax errors trigger retry (max 3)
        - AC-4: Failed tests trigger reflection + retry
        - AC-5: HelpNeeded after exhausting retries
        
        Args:
            code: Initial Python source code
            filename: Filename for error reporting
            test_code: Optional test code to execute
            refine_callback: Function to refine code based on reflection
            persona_id: ID of the persona (for HelpNeeded)
        
        Returns:
            ValidationResult from final attempt
        
        Raises:
            HelpNeeded: If validation fails after max_attempts (AC-5)
        """
        import time
        overall_start = time.perf_counter()
        
        current_code = code
        validation_history = []
        suggestions_tried = []
        last_result = None
        
        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Validation attempt {attempt}/{self.max_attempts}")
            
            # Validate current code
            result = self.validate_code(
                code=current_code,
                filename=filename,
                test_code=test_code
            )
            result.attempts = attempt
            result.max_attempts = self.max_attempts
            last_result = result
            
            # Track history
            validation_history.append({
                "attempt": attempt,
                "valid": result.valid,
                "error_type": "syntax" if result.syntax_result and not result.syntax_result.valid else "test",
                "message": (
                    result.syntax_result.error_message if result.syntax_result and not result.syntax_result.valid
                    else (result.test_result.output[:100] if result.test_result else "")
                )
            })
            
            # If valid, return success
            if result.valid:
                logger.info(f"Validation PASSED on attempt {attempt}")
                return result
            
            # If we have reflection and callback, try to refine
            if result.reflection_result and refine_callback and attempt < self.max_attempts:
                try:
                    # Track suggestion
                    if result.reflection_result.suggestions:
                        suggestions_tried.extend(result.reflection_result.suggestions[:2])
                    
                    # Refine code
                    current_code = refine_callback(current_code, result.reflection_result)
                    logger.info(f"Code refined based on reflection, retrying...")
                    
                except Exception as e:
                    logger.warning(f"Refine callback failed: {e}")
        
        # AC-5: Exhausted retries - raise HelpNeeded
        context = HelpNeededContext(
            last_code=current_code,
            last_error_output=(
                last_result.syntax_result.error_message if last_result and last_result.syntax_result and not last_result.syntax_result.valid
                else (last_result.test_result.output if last_result and last_result.test_result else None)
            ),
            validation_history=validation_history,
            suggestions_tried=suggestions_tried,
            execution_time_seconds=(time.perf_counter() - overall_start)
        )
        
        last_error = "Unknown error"
        if last_result:
            if last_result.syntax_result and not last_result.syntax_result.valid:
                last_error = last_result.syntax_result.error_message or "Syntax error"
            elif last_result.test_result and not last_result.test_result.success:
                last_error = f"Test failures: {', '.join(last_result.test_result.failed_tests[:3])}"
        
        logger.error(f"Validation FAILED after {self.max_attempts} attempts - raising HelpNeeded")
        
        raise HelpNeeded(
            persona_id=persona_id,
            task=f"Validate {filename}",
            attempts=self.max_attempts,
            max_attempts=self.max_attempts,
            last_error=last_error,
            context=context
        )
    
    def validate_file(
        self,
        filepath: str,
        test_filepath: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate a Python file.
        
        Args:
            filepath: Path to Python file
            test_filepath: Optional path to test file
        
        Returns:
            ValidationResult with validation details
        """
        try:
            with open(filepath, 'r') as f:
                code = f.read()
            
            test_code = None
            if test_filepath:
                with open(test_filepath, 'r') as f:
                    test_code = f.read()
            
            return self.validate_code(code, filename=filepath, test_code=test_code)
            
        except FileNotFoundError as e:
            return ValidationResult(
                valid=False,
                syntax_result=SyntaxCheckResult(
                    valid=False,
                    filename=filepath,
                    error_message=f"File not found: {e}"
                )
            )
    
    def get_history(self) -> List[ValidationResult]:
        """Get validation history."""
        return list(self._history)
    
    def clear_history(self) -> None:
        """Clear validation history."""
        self._history.clear()
        self.reflection_engine.clear_history()


def validate_python_code(
    code: str,
    filename: str = "<generated>",
    max_attempts: int = 3
) -> ValidationResult:
    """
    Convenience function for validating Python code.
    
    Args:
        code: Python source code
        filename: Filename for error reporting
        max_attempts: Maximum retry attempts
    
    Returns:
        ValidationResult with validation details
    """
    validator = JITValidator(max_attempts=max_attempts, run_tests=False)
    return validator.validate_code(code, filename)
