"""
Exceptions for JIT Validation & Persona Reflection (MD-3092)

This module defines custom exceptions for the validation system:
- HelpNeeded: AC-5 - Raised after exhausting retries
- ValidationError: General validation failures
- ReflectionError: Reflection/analysis failures
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """
    Base exception for validation failures.
    
    Attributes:
        message: Human-readable error message
        code: Optional error code for categorization
        context: Additional context about the error
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or "VALIDATION_ERROR"
        self.context = context or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "context": self.context
        }


class ReflectionError(ValidationError):
    """
    Exception for reflection/analysis failures.
    
    Raised when the reflection engine cannot analyze a failure
    or suggest meaningful fixes.
    """
    
    def __init__(
        self,
        message: str,
        original_error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.original_error = original_error
        super().__init__(
            message=message,
            code="REFLECTION_ERROR",
            context={**(context or {}), "original_error": original_error}
        )


@dataclass
class HelpNeededContext:
    """Context information for HelpNeeded exception."""
    last_code: Optional[str] = None
    last_error_output: Optional[str] = None
    validation_history: List[Dict[str, Any]] = field(default_factory=list)
    suggestions_tried: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0


class HelpNeeded(Exception):
    """
    AC-5: Raised when a persona cannot complete a task after max retries.
    
    This exception signals that the persona has exhausted all retry attempts
    and needs human or coordinator intervention.
    
    Attributes:
        persona_id: ID of the persona that raised the exception
        task: Description of the task that failed
        attempts: Number of attempts made
        max_attempts: Maximum attempts allowed
        last_error: The last error encountered
        context: HelpNeededContext with detailed information
        timestamp: When the exception was raised
    
    Example:
        >>> try:
        ...     result = persona.execute(task)
        ... except HelpNeeded as e:
        ...     print(f"Persona {e.persona_id} needs help with: {e.task}")
        ...     print(f"Attempted {e.attempts}/{e.max_attempts} times")
        ...     print(f"Last error: {e.last_error}")
        ...     # Escalate to coordinator or human
    """
    
    def __init__(
        self,
        persona_id: str,
        task: str,
        attempts: int,
        max_attempts: int,
        last_error: str,
        context: Optional[HelpNeededContext] = None
    ):
        self.persona_id = persona_id
        self.task = task
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.last_error = last_error
        self.context = context or HelpNeededContext()
        self.timestamp = datetime.now()
        
        message = (
            f"Persona '{persona_id}' needs help with '{task}' "
            f"after {attempts}/{max_attempts} attempts. "
            f"Last error: {last_error}"
        )
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "exception": "HelpNeeded",
            "persona_id": self.persona_id,
            "task": self.task,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "timestamp": self.timestamp.isoformat(),
            "context": {
                "last_code_length": len(self.context.last_code or ""),
                "last_error_output": self.context.last_error_output,
                "validation_history_count": len(self.context.validation_history),
                "suggestions_tried": self.context.suggestions_tried,
                "execution_time_seconds": self.context.execution_time_seconds
            }
        }
    
    def get_escalation_summary(self) -> str:
        """Generate a summary for escalation to coordinator/human."""
        summary_lines = [
            f"=== HELP NEEDED: {self.persona_id} ===",
            f"Task: {self.task}",
            f"Attempts: {self.attempts}/{self.max_attempts}",
            f"Last Error: {self.last_error}",
            "",
            "Validation History:"
        ]
        
        for i, entry in enumerate(self.context.validation_history[-3:], 1):
            summary_lines.append(f"  {i}. {entry.get('error_type', 'unknown')}: {entry.get('message', 'N/A')}")
        
        if self.context.suggestions_tried:
            summary_lines.append("")
            summary_lines.append("Suggestions Tried:")
            for suggestion in self.context.suggestions_tried[-3:]:
                summary_lines.append(f"  - {suggestion}")
        
        return "\n".join(summary_lines)


class SyntaxValidationError(ValidationError):
    """
    Specific exception for syntax validation failures.
    
    Contains detailed information about the syntax error location.
    """
    
    def __init__(
        self,
        message: str,
        filename: str,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
        code_snippet: Optional[str] = None
    ):
        self.filename = filename
        self.lineno = lineno
        self.col_offset = col_offset
        self.code_snippet = code_snippet
        
        super().__init__(
            message=message,
            code="SYNTAX_ERROR",
            context={
                "filename": filename,
                "lineno": lineno,
                "col_offset": col_offset,
                "code_snippet": code_snippet
            }
        )
    
    def get_error_location(self) -> str:
        """Get formatted error location string."""
        if self.lineno:
            if self.col_offset:
                return f"{self.filename}:{self.lineno}:{self.col_offset}"
            return f"{self.filename}:{self.lineno}"
        return self.filename


class TestExecutionError(ValidationError):
    """
    Exception for test execution failures.
    
    Contains test output and failure details.
    """
    
    def __init__(
        self,
        message: str,
        test_file: str,
        tests_passed: int = 0,
        tests_failed: int = 0,
        test_output: Optional[str] = None,
        failed_tests: Optional[List[str]] = None
    ):
        self.test_file = test_file
        self.tests_passed = tests_passed
        self.tests_failed = tests_failed
        self.test_output = test_output
        self.failed_tests = failed_tests or []
        
        super().__init__(
            message=message,
            code="TEST_EXECUTION_ERROR",
            context={
                "test_file": test_file,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "failed_tests": failed_tests
            }
        )
