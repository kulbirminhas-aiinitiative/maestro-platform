"""
Unified Execution Exceptions

EPIC: MD-3091 - Unified Execution Foundation
AC-4: Two-level retry operational

Custom exceptions for the unified execution module that enable
precise error handling and recovery decisions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ExecutionException(Exception):
    """Base exception for all execution errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


@dataclass
class FailureReport:
    """
    Structured failure information for retry decision-making.

    Used by SafetyRetryWrapper (Level 2) to make intelligent
    recovery decisions.
    """

    failed_persona: str
    error_category: str  # SYNTAX, TEST_FAILURE, ACC_VIOLATION, TIMEOUT, UNKNOWN
    details: str
    context: List[str] = field(default_factory=list)
    attempt_number: int = 0
    recoverable: bool = True
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "failed_persona": self.failed_persona,
            "error_category": self.error_category,
            "details": self.details,
            "context": self.context,
            "attempt_number": self.attempt_number,
            "recoverable": self.recoverable,
            "suggested_fix": self.suggested_fix,
        }


class RecoverableError(ExecutionException):
    """
    Error that can potentially be fixed with retry.

    Level 1 retry (PersonaExecutor) handles these internally.
    Examples: syntax errors, transient API failures, timeout.
    """

    def __init__(
        self,
        message: str,
        error_category: str = "UNKNOWN",
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.error_category = error_category
        self.file_path = file_path
        self.line_number = line_number


class UnrecoverableError(ExecutionException):
    """
    Error that cannot be fixed automatically.

    Level 1 exhausted, escalates to Level 2 (SafetyRetryWrapper).
    Level 2 may attempt broader recovery or create JIRA ticket.
    """

    def __init__(
        self,
        message: str,
        failure_report: Optional[FailureReport] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.failure_report = failure_report
        self.original_error = original_error


class HelpNeeded(ExecutionException):
    """
    Execution requires human intervention.

    Raised when both retry levels are exhausted and automatic
    recovery is not possible. Triggers JIRA ticket creation.
    """

    def __init__(
        self,
        message: str,
        failure_report: FailureReport,
        total_attempts: int = 0,
        suggested_actions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.failure_report = failure_report
        self.total_attempts = total_attempts
        self.suggested_actions = suggested_actions or []


class CircuitBreakerOpen(ExecutionException):
    """
    Circuit breaker has tripped due to repeated failures.

    System is in protection mode to prevent cascade failures.
    """

    def __init__(
        self,
        message: str,
        consecutive_failures: int,
        cooldown_seconds: int,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.consecutive_failures = consecutive_failures
        self.cooldown_seconds = cooldown_seconds


class TokenBudgetExceeded(ExecutionException):
    """
    Token budget for persona/execution has been exceeded.

    Prevents runaway LLM costs from infinite retry loops.
    """

    def __init__(
        self,
        message: str,
        persona_id: str,
        tokens_used: int,
        budget_limit: int,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.persona_id = persona_id
        self.tokens_used = tokens_used
        self.budget_limit = budget_limit


class GovernanceViolation(ExecutionException):
    """
    Action blocked by governance policy.

    EPIC: MD-3126 - Integrate Enforcer Middleware into Persona Executor
    AC-1: Attempting to write to a protected file throws GovernanceViolation
    AC-2: Attempting to use a forbidden tool throws GovernanceViolation

    This exception is raised when the Enforcer middleware detects:
    - Attempts to modify immutable files (e.g., policy.yaml, .env)
    - Use of forbidden tools for the agent's role (e.g., sudo, deploy_prod)
    - Budget exceeded violations
    - Role-based permission violations
    """

    def __init__(
        self,
        message: str,
        violation_type: str,
        path: Optional[str] = None,
        tool_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.message = message  # Store message explicitly for easy access
        self.violation_type = violation_type
        self.path = path
        self.tool_name = tool_name
        self.agent_id = agent_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for audit logging."""
        return {
            "message": self.message,
            "violation_type": self.violation_type,
            "path": self.path,
            "tool_name": self.tool_name,
            "agent_id": self.agent_id,
            "context": self.context,
        }
