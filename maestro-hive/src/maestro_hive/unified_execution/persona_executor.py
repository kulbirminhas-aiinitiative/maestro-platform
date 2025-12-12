"""
Unified PersonaExecutor - Level 1 Retry Implementation

EPIC: MD-3091 - Unified Execution Foundation
AC-3: Single PersonaExecutor replaces 3 implementations
AC-4: Two-level retry operational (internal 3x)

Merges functionality from:
- /core/execution/iterative_executor.py (SelfHealingEngine, FailureDetector)
- /execution/iterative_executor.py (async patterns, exponential backoff)
"""

from __future__ import annotations

import ast
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic

from .config import ExecutionConfig, Level1Config, RecoveryStrategy, get_execution_config
from .state_persistence import StatePersistence, ExecutionState
from .exceptions import (
    RecoverableError,
    UnrecoverableError,
    HelpNeeded,
    FailureReport,
    TokenBudgetExceeded,
    GovernanceViolation,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExecutionStatus(Enum):
    """Status of an execution attempt."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    RECOVERED = "recovered"
    HELP_NEEDED = "help_needed"
    BANKRUPT = "bankrupt"  # MD-3099: Token budget exceeded


@dataclass
class ExecutionAttempt:
    """Record of a single execution attempt."""

    attempt_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    attempt_number: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    output: Any = None
    tokens_used: int = 0
    healing_applied: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "attempt_id": self.attempt_id,
            "attempt_number": self.attempt_number,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "tokens_used": self.tokens_used,
            "healing_applied": self.healing_applied,
            "output": str(self.output)[:500] if self.output else None,
            "metrics": self.metrics,
        }


@dataclass
class ExecutionResult:
    """Final result of a Level 1 execution."""

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_name: str = ""
    persona_id: str = ""
    final_status: ExecutionStatus = ExecutionStatus.PENDING
    attempts: List[ExecutionAttempt] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    total_tokens_used: int = 0
    final_output: Any = None
    recovery_applied: bool = False
    failure_report: Optional[FailureReport] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def attempt_count(self) -> int:
        """Get total number of attempts."""
        return len(self.attempts)

    @property
    def success(self) -> bool:
        """Check if execution succeeded."""
        return self.final_status in (ExecutionStatus.SUCCESS, ExecutionStatus.RECOVERED)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "task_name": self.task_name,
            "persona_id": self.persona_id,
            "final_status": self.final_status.value,
            "attempt_count": self.attempt_count,
            "attempts": [a.to_dict() for a in self.attempts],
            "total_duration_seconds": self.total_duration_seconds,
            "total_tokens_used": self.total_tokens_used,
            "recovery_applied": self.recovery_applied,
            "failure_report": self.failure_report.to_dict() if self.failure_report else None,
            "created_at": self.created_at.isoformat(),
            "success": self.success,
        }


class PersonaExecutor(Generic[T]):
    """
    Level 1 Executor with self-healing capabilities.

    Executes tasks with:
    - Configurable retry policies (default: 3 attempts)
    - Exponential backoff (1-5 seconds)
    - Syntax validation on generated code
    - Self-healing via reflection and fix suggestions
    - Token budget tracking

    Raises UnrecoverableError when Level 1 retries are exhausted,
    signaling SafetyRetryWrapper (Level 2) to take over.
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        persona_id: str = "default",
        healing_engine: Optional[Any] = None,
        workflow_id: Optional[str] = None,
        state_persistence: Optional[StatePersistence] = None,
        enforcer: Optional[Any] = None,
        audit_log_path: Optional[str] = None,
        persona_role: str = "developer_agent",
    ):
        """
        Initialize the persona executor.

        Args:
            config: Execution configuration (uses default if None)
            persona_id: Identifier for this persona
            healing_engine: Optional SelfHealingEngine instance
            workflow_id: Optional ID for the parent workflow (for state persistence)
            state_persistence: Optional StatePersistence instance
            enforcer: Optional Enforcer middleware for governance checks (MD-3126)
            audit_log_path: Path to audit log file (default: /var/log/maestro/audit.log)
            persona_role: Role for governance checks (e.g., developer_agent, architect_agent)
        """
        self.config = config or get_execution_config()
        self.l1_config = self.config.level1
        self.persona_id = persona_id
        self.healing_engine = healing_engine
        self.workflow_id = workflow_id
        self.state_persistence = state_persistence
        self._tokens_used = 0

        # MD-3126: Enforcer middleware integration
        self.enforcer = enforcer
        self.audit_log_path = audit_log_path or "/var/log/maestro/audit.log"
        self.persona_role = persona_role

        # Initialize state persistence if workflow_id is provided but persistence is missing
        if self.workflow_id and not self.state_persistence:
            try:
                self.state_persistence = StatePersistence(
                    config=self.config,
                    workflow_id=self.workflow_id
                )
                logger.info(f"[{self.persona_id}] Initialized new StatePersistence for workflow {self.workflow_id}")
            except Exception as e:
                logger.warning(f"[{self.persona_id}] Failed to initialize StatePersistence: {e}")

        logger.info(
            f"PersonaExecutor[{persona_id}] initialized with "
            f"max_attempts={self.l1_config.max_attempts}"
        )

    def _persist_state(self, result: ExecutionResult, attempt: ExecutionAttempt) -> None:
        """
        Persist the current execution state to disk.
        
        Updates the shared ExecutionState with the latest attempt info for this persona.
        """
        if not self.state_persistence or not self.state_persistence._state:
            return

        try:
            # Update the persona-specific state within the global workflow state
            persona_state = {
                "last_updated": datetime.utcnow().isoformat(),
                "status": attempt.status.value,  # Use attempt status as it's the most current
                "current_attempt": attempt.attempt_number,
                "tokens_used": self._tokens_used,
                "last_error": attempt.error_message,
                "recovery_applied": result.recovery_applied
            }
            
            # Use the proper API for updating state
            self.state_persistence.update_persona_state(self.persona_id, persona_state)
            
            # Update retry counts
            # We can't easily set retry_counts directly via API without incrementing, 
            # so we'll access the state object directly for this specific field if needed,
            # or just rely on the persona_state blob.
            
            # Save to disk (Checkpoint)
            # We use checkpoint() to ensure durability
            self.state_persistence.checkpoint()
                
        except Exception as e:
            logger.warning(f"[{self.persona_id}] Failed to persist state: {e}")

    def _calculate_delay(self, attempt_number: int) -> float:
        """Calculate delay before next retry using exponential backoff."""
        delay = self.l1_config.base_delay_seconds * (
            self.l1_config.backoff_multiplier ** (attempt_number - 1)
        )
        return min(delay, self.l1_config.max_delay_seconds)

    def _validate_python_syntax(self, code: str, file_path: str = "<generated>") -> None:
        """
        Validate Python code syntax using AST parsing.

        Args:
            code: Python source code to validate
            file_path: File path for error messages

        Raises:
            RecoverableError: If syntax error is found
        """
        if not self.l1_config.enable_syntax_validation:
            return

        try:
            ast.parse(code)
        except SyntaxError as e:
            raise RecoverableError(
                message=f"Syntax error in {file_path}: {e.msg}",
                error_category="SYNTAX",
                file_path=file_path,
                line_number=e.lineno,
                context={"offset": e.offset, "text": e.text},
            )

    def _check_token_budget(self, tokens: int) -> None:
        """
        Check if token usage is within budget.

        Args:
            tokens: Number of tokens to add

        Raises:
            TokenBudgetExceeded: If budget would be exceeded
        """
        if not self.config.tokens.enforce_budget:
            return

        new_total = self._tokens_used + tokens
        if new_total > self.config.tokens.max_tokens_per_persona:
            raise TokenBudgetExceeded(
                message=f"Token budget exceeded for persona {self.persona_id}",
                persona_id=self.persona_id,
                tokens_used=new_total,
                budget_limit=self.config.tokens.max_tokens_per_persona,
            )

        self._tokens_used = new_total

    def _validate_governance(
        self,
        tool_name: str,
        target_path: Optional[str] = None,
        action: str = "execute",
    ) -> None:
        """
        Validate action against governance policy via Enforcer middleware.

        MD-3126 Implementation:
        AC-1: Protected file write throws GovernanceViolation
        AC-2: Forbidden tool use throws GovernanceViolation
        AC-3: Valid actions pass through with <10ms latency
        AC-4: Violations are logged to audit.log

        Args:
            tool_name: Name of the tool being executed
            target_path: Optional file path being accessed
            action: Action type (read, write, delete, execute)

        Raises:
            GovernanceViolation: If action violates policy
        """
        if not self.enforcer:
            return

        # Import AgentContext from enforcer (lazy import to avoid circular deps)
        try:
            from ..governance.enforcer import AgentContext
        except ImportError:
            # Fallback if enforcer module not available
            logger.warning("Enforcer module not available, skipping governance check")
            return

        # Build agent context for the enforcer
        agent = AgentContext(
            agent_id=self.persona_id,
            role=self.persona_role,
        )

        # Invoke enforcer check (must complete in <10ms per AC-4)
        result = self.enforcer.check(
            agent=agent,
            tool_name=tool_name,
            target_path=target_path,
            action=action,
        )

        # Log to audit (AC-4)
        self._log_audit(result, tool_name, target_path)

        # Raise GovernanceViolation if blocked
        if not result.allowed:
            raise GovernanceViolation(
                message=result.message,
                violation_type=result.violation_type.value if result.violation_type else "policy_violation",
                path=target_path,
                tool_name=tool_name,
                agent_id=self.persona_id,
            )

    def _log_audit(
        self,
        result: Any,
        tool_name: str,
        target_path: Optional[str],
    ) -> None:
        """
        Log enforcement result to audit.log.

        MD-3126 AC-4: Violations are logged to audit.log

        Args:
            result: EnforcerResult from governance check
            tool_name: Name of the tool
            target_path: Optional file path
        """
        import json
        import os
        from datetime import datetime

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "persona_id": self.persona_id,
            "role": self.persona_role,
            "tool": tool_name,
            "path": target_path,
            "allowed": result.allowed,
            "violation_type": result.violation_type.value if hasattr(result, 'violation_type') and result.violation_type else None,
            "message": result.message if hasattr(result, 'message') else "",
            "latency_ms": result.latency_ms if hasattr(result, 'latency_ms') else 0,
        }

        try:
            # Ensure directory exists
            log_dir = os.path.dirname(self.audit_log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            # Append to audit log
            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"[{self.persona_id}] Failed to write audit log: {e}")

    def _infer_action_from_tool(self, tool_name: str) -> str:
        """
        Infer action type from tool name for governance checks.

        Args:
            tool_name: Name of the tool

        Returns:
            Action type: read, write, delete, or execute
        """
        tool_lower = tool_name.lower()

        if any(word in tool_lower for word in ["write", "edit", "create", "update", "set"]):
            return "write"
        elif any(word in tool_lower for word in ["delete", "remove", "rm", "unlink"]):
            return "delete"
        elif any(word in tool_lower for word in ["read", "get", "fetch", "cat", "head", "tail"]):
            return "read"
        else:
            return "execute"

    def _extract_tokens_from_output(self, output: Any) -> int:
        """
        Extract token count from task output.

        MD-3099: Supports multiple output formats for token extraction.

        Args:
            output: The task output (dict, object with tokens_used, or string)

        Returns:
            Token count, or estimated count based on string length
        """
        if output is None:
            return 0

        # Check for dict with token info
        if isinstance(output, dict):
            # Try common keys for token counts
            for key in ["tokens_used", "token_count", "usage", "tokens"]:
                if key in output:
                    value = output[key]
                    if isinstance(value, int):
                        return value
                    if isinstance(value, dict):
                        # Handle nested usage dict (e.g., {"input_tokens": X, "output_tokens": Y})
                        total = 0
                        for sub_key in ["input_tokens", "output_tokens", "total_tokens", "prompt_tokens", "completion_tokens"]:
                            if sub_key in value:
                                total += value[sub_key]
                        if total > 0:
                            return total

        # Check for object with tokens_used attribute
        if hasattr(output, "tokens_used"):
            return getattr(output, "tokens_used", 0)
        if hasattr(output, "usage"):
            usage = getattr(output, "usage", None)
            if hasattr(usage, "total_tokens"):
                return getattr(usage, "total_tokens", 0)

        # Estimate tokens from string length (rough: ~4 chars per token)
        if isinstance(output, str):
            return len(output) // 4

        return 0

    def _classify_error(self, error: Exception) -> str:
        """Classify error into category for recovery routing."""
        error_type = type(error).__name__

        if isinstance(error, RecoverableError):
            return error.error_category

        if "Syntax" in error_type:
            return "SYNTAX"
        if "Timeout" in error_type or "asyncio" in str(error):
            return "TIMEOUT"
        if "API" in error_type or "Request" in error_type:
            return "API_ERROR"

        return "UNKNOWN"

    def _attempt_healing(
        self,
        error: Exception,
        attempt: ExecutionAttempt,
    ) -> bool:
        """
        Attempt to heal the error using SelfHealingEngine.

        Args:
            error: The error to heal
            attempt: Current execution attempt

        Returns:
            True if healing was successful
        """
        if not self.l1_config.enable_self_healing:
            return False

        if self.healing_engine is None:
            logger.debug("No healing engine configured")
            return False

        try:
            # Call healing engine (implementation varies)
            result = self.healing_engine.heal_single(error)
            if hasattr(result, "status") and str(result.status) == "FIXED":
                attempt.healing_applied = True
                logger.info("Self-healing applied successfully")
                return True
        except Exception as heal_error:
            logger.warning(f"Healing attempt failed: {heal_error}")

        return False

    async def _execute_attempt(
        self,
        task: Callable[..., T],
        attempt: ExecutionAttempt,
        *args,
        **kwargs,
    ) -> None:
        """Execute a single attempt of the task."""
        attempt.started_at = datetime.utcnow()
        attempt.status = ExecutionStatus.RUNNING

        try:
            if asyncio.iscoroutinefunction(task):
                if self.config.timeout_seconds:
                    attempt.output = await asyncio.wait_for(
                        task(*args, **kwargs), timeout=self.config.timeout_seconds
                    )
                else:
                    attempt.output = await task(*args, **kwargs)
            else:
                attempt.output = task(*args, **kwargs)

            # If output is code, validate syntax
            if isinstance(attempt.output, str) and attempt.output.strip().startswith(
                ("def ", "class ", "import ", "from ")
            ):
                self._validate_python_syntax(attempt.output)

            attempt.status = ExecutionStatus.SUCCESS
            attempt.ended_at = datetime.utcnow()

        except asyncio.TimeoutError:
            attempt.status = ExecutionStatus.FAILED
            attempt.error_type = "TimeoutError"
            attempt.error_message = f"Execution timed out after {self.config.timeout_seconds}s"
            attempt.ended_at = datetime.utcnow()

        except RecoverableError as e:
            attempt.status = ExecutionStatus.FAILED
            attempt.error_type = type(e).__name__
            attempt.error_message = str(e)
            attempt.ended_at = datetime.utcnow()
            attempt.metrics["error_category"] = e.error_category

        except Exception as e:
            import traceback

            attempt.status = ExecutionStatus.FAILED
            attempt.error_type = type(e).__name__
            attempt.error_message = str(e)
            attempt.error_traceback = traceback.format_exc()
            attempt.ended_at = datetime.utcnow()
            attempt.metrics["error_category"] = self._classify_error(e)

    async def execute(
        self,
        task: Callable[..., T],
        task_name: str = "unnamed_task",
        *args,
        **kwargs,
    ) -> ExecutionResult:
        """
        Execute a task with Level 1 retry and self-healing.

        Args:
            task: The callable to execute
            task_name: Human-readable name for the task
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            ExecutionResult containing all attempt information

        Raises:
            UnrecoverableError: When all Level 1 retries are exhausted
        """
        result = ExecutionResult(task_name=task_name, persona_id=self.persona_id)
        start_time = time.time()

        logger.info(f"PersonaExecutor[{self.persona_id}] starting: {task_name}")

        # MD-3126: Governance validation before execution
        # Extract tool name and target path from task/kwargs for governance check
        tool_name = getattr(task, '__name__', task_name)
        target_path = kwargs.get('path') or kwargs.get('file_path') or kwargs.get('target')
        action = self._infer_action_from_tool(tool_name)

        try:
            self._validate_governance(tool_name, target_path, action)
        except GovernanceViolation as gov_error:
            # Governance violation - fail immediately without retry
            logger.warning(
                f"[{self.persona_id}] Governance violation: {gov_error.message}"
            )
            result.final_status = ExecutionStatus.FAILED
            result.total_duration_seconds = time.time() - start_time
            result.failure_report = FailureReport(
                failed_persona=self.persona_id,
                error_category="GOVERNANCE_VIOLATION",
                details=str(gov_error),
                context=[f"Tool: {tool_name}", f"Path: {target_path}", f"Violation: {gov_error.violation_type}"],
                attempt_number=0,
                recoverable=False,
            )
            raise  # Re-raise GovernanceViolation for caller to handle

        last_error: Optional[Exception] = None

        for attempt_num in range(1, self.l1_config.max_attempts + 1):
            attempt = ExecutionAttempt(attempt_number=attempt_num)
            result.attempts.append(attempt)

            logger.info(
                f"[{self.persona_id}] Attempt {attempt_num}/{self.l1_config.max_attempts}: {task_name}"
            )

            await self._execute_attempt(task, attempt, *args, **kwargs)

            # MD-3099: Extract and track token usage after each attempt
            tokens_from_output = self._extract_tokens_from_output(attempt.output)
            attempt.tokens_used = tokens_from_output

            try:
                # MD-3099: Wire up token budget check (previously defined but never called)
                self._check_token_budget(tokens_from_output)
            except TokenBudgetExceeded as budget_error:
                # Handle budget exceeded with BANKRUPT status
                logger.warning(
                    f"[{self.persona_id}] Token budget exceeded: "
                    f"{budget_error.tokens_used}/{budget_error.budget_limit} tokens"
                )
                attempt.status = ExecutionStatus.BANKRUPT
                attempt.error_type = "TokenBudgetExceeded"
                attempt.error_message = str(budget_error)
                attempt.metrics["tokens_at_bankruptcy"] = budget_error.tokens_used
                attempt.metrics["budget_limit"] = budget_error.budget_limit

                # Persist state before returning (save progress)
                self._persist_state(result, attempt)

                # Return with BANKRUPT status (graceful termination)
                result.final_status = ExecutionStatus.BANKRUPT
                result.total_duration_seconds = time.time() - start_time
                result.total_tokens_used = budget_error.tokens_used
                result.failure_report = FailureReport(
                    failed_persona=self.persona_id,
                    error_category="TOKEN_BUDGET",
                    details=str(budget_error),
                    context=[f"Budget limit: {budget_error.budget_limit}", f"Tokens used: {budget_error.tokens_used}"],
                    attempt_number=attempt_num,
                    recoverable=False,
                )
                return result

            # Persist state after every attempt (Durable Execution)
            self._persist_state(result, attempt)

            if attempt.status == ExecutionStatus.SUCCESS:
                result.final_status = ExecutionStatus.SUCCESS
                result.final_output = attempt.output
                result.total_duration_seconds = time.time() - start_time
                result.total_tokens_used = self._tokens_used
                logger.info(f"[{self.persona_id}] Success after {attempt_num} attempt(s)")
                return result

            # Failed - try healing
            last_error = Exception(attempt.error_message or "Unknown error")
            if attempt.error_traceback:
                last_error.__traceback__ = None  # Clear for serialization

            if attempt_num < self.l1_config.max_attempts:
                # Try healing before retry
                healed = self._attempt_healing(last_error, attempt)

                if healed:
                    result.recovery_applied = True
                    logger.info(f"[{self.persona_id}] Healing applied, retrying...")
                else:
                    delay = self._calculate_delay(attempt_num)
                    logger.info(f"[{self.persona_id}] Retrying in {delay:.1f}s...")
                    attempt.status = ExecutionStatus.RETRYING
                    await asyncio.sleep(delay)

        # All Level 1 retries exhausted
        result.final_status = ExecutionStatus.FAILED
        result.total_duration_seconds = time.time() - start_time
        result.total_tokens_used = self._tokens_used

        # Create failure report for Level 2
        last_attempt = result.attempts[-1]
        failure_report = FailureReport(
            failed_persona=self.persona_id,
            error_category=last_attempt.metrics.get("error_category", "UNKNOWN"),
            details=last_attempt.error_message or "Unknown error",
            context=[a.error_message for a in result.attempts if a.error_message],
            attempt_number=result.attempt_count,
            recoverable=False,  # Level 1 exhausted
        )
        result.failure_report = failure_report

        logger.warning(
            f"[{self.persona_id}] Level 1 exhausted after {result.attempt_count} attempts. "
            f"Raising UnrecoverableError for Level 2."
        )

        raise UnrecoverableError(
            message=f"Level 1 retries exhausted for {task_name}",
            failure_report=failure_report,
            original_error=last_error,
            context={"execution_id": result.execution_id, "attempts": result.attempt_count},
        )

    def reset_token_usage(self) -> None:
        """Reset token usage counter."""
        self._tokens_used = 0

    def get_token_usage(self) -> int:
        """Get current token usage."""
        return self._tokens_used


# Convenience function for simple execution
async def execute_with_level1_retry(
    task: Callable[..., T],
    task_name: str = "task",
    persona_id: str = "default",
    max_attempts: int = 3,
    *args,
    **kwargs,
) -> ExecutionResult:
    """
    Convenience function to execute a task with Level 1 retry.

    Args:
        task: Callable to execute
        task_name: Name for logging
        persona_id: Persona identifier
        max_attempts: Maximum retry attempts
        *args, **kwargs: Arguments for the task

    Returns:
        ExecutionResult
    """
    config = get_execution_config()
    config.level1.max_attempts = max_attempts
    executor = PersonaExecutor(config=config, persona_id=persona_id)
    return await executor.execute(task, task_name, *args, **kwargs)
