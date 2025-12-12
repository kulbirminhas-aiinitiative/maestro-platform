"""
SafetyRetryWrapper - Level 2 Retry Implementation

EPIC: MD-3091 - Unified Execution Foundation
AC-4: Two-level retry operational (external 2x with circuit breaker)

External safety wrapper that:
- Catches UnrecoverableError from Level 1
- Applies broader recovery strategies
- Implements circuit breaker pattern
- Escalates to JIRA when all options exhausted
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

from .config import ExecutionConfig, Level2Config, get_execution_config
from .exceptions import (
    UnrecoverableError,
    HelpNeeded,
    CircuitBreakerOpen,
    FailureReport,
)
from .persona_executor import PersonaExecutor, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Opens after threshold consecutive failures,
    prevents cascade failures during outages.
    """

    threshold: int = 5
    cooldown_seconds: int = 300
    consecutive_failures: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None

    def record_success(self) -> None:
        """Record a successful execution."""
        self.consecutive_failures = 0
        self.state = CircuitState.CLOSED
        self.last_success_time = datetime.utcnow()

    def record_failure(self) -> None:
        """Record a failed execution."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.utcnow()

        if self.consecutive_failures >= self.threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self.consecutive_failures} consecutive failures"
            )

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state != CircuitState.OPEN:
            return False

        # Check if cooldown has passed
        if self.last_failure_time:
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            if elapsed >= self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "threshold": self.threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
        }


@dataclass
class Level2Result:
    """Result of Level 2 execution."""

    execution_id: str
    task_name: str
    final_status: ExecutionStatus
    level1_results: List[ExecutionResult] = field(default_factory=list)
    level2_attempts: int = 0
    total_duration_seconds: float = 0.0
    jira_ticket: Optional[str] = None
    circuit_breaker_state: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def success(self) -> bool:
        """Check if execution succeeded."""
        return self.final_status in (ExecutionStatus.SUCCESS, ExecutionStatus.RECOVERED)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "task_name": self.task_name,
            "final_status": self.final_status.value,
            "level1_results": [r.to_dict() for r in self.level1_results],
            "level2_attempts": self.level2_attempts,
            "total_duration_seconds": self.total_duration_seconds,
            "jira_ticket": self.jira_ticket,
            "circuit_breaker_state": self.circuit_breaker_state,
            "created_at": self.created_at.isoformat(),
            "success": self.success,
        }


class SafetyRetryWrapper:
    """
    Level 2 External Safety Wrapper.

    Wraps PersonaExecutor execution with:
    - Additional retry attempts (default: 2)
    - Circuit breaker pattern
    - Exponential backoff (5s, 10s, 20s)
    - JIRA ticket creation on final failure

    Usage:
        wrapper = SafetyRetryWrapper()
        result = await wrapper.execute_safe(
            executor.execute,
            my_task,
            "Process data"
        )
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        jira_client: Optional[Any] = None,
    ):
        """
        Initialize safety wrapper.

        Args:
            config: Execution configuration
            jira_client: Optional JIRA client for ticket creation
        """
        self.config = config or get_execution_config()
        self.l2_config = self.config.level2
        self.jira_client = jira_client

        self.circuit_breaker = CircuitBreaker(
            threshold=self.l2_config.circuit_breaker_threshold,
            cooldown_seconds=self.l2_config.circuit_breaker_cooldown_seconds,
        )

        logger.info(
            f"SafetyRetryWrapper initialized with max_attempts={self.l2_config.max_attempts}, "
            f"circuit_breaker_threshold={self.l2_config.circuit_breaker_threshold}"
        )

    def _calculate_delay(self, attempt_number: int) -> float:
        """Calculate delay before next retry using exponential backoff."""
        delay = self.l2_config.base_delay_seconds * (
            self.l2_config.backoff_multiplier ** (attempt_number - 1)
        )
        return min(delay, self.l2_config.max_delay_seconds)

    async def _create_jira_ticket(
        self,
        task_name: str,
        failure_report: FailureReport,
        execution_id: str,
    ) -> Optional[str]:
        """
        Create JIRA ticket for unrecoverable failure.

        Args:
            task_name: Name of failed task
            failure_report: Structured failure information
            execution_id: Execution identifier

        Returns:
            JIRA ticket key if created, None otherwise
        """
        if not self.l2_config.enable_jira_escalation:
            logger.info("JIRA escalation disabled")
            return None

        if self.jira_client is None:
            logger.warning("No JIRA client configured for escalation")
            return None

        try:
            # Build ticket content
            summary = f"[Auto-Bug] Execution failed: {task_name}"
            description = (
                f"## Failure Report\n\n"
                f"**Persona:** {failure_report.failed_persona}\n"
                f"**Error Category:** {failure_report.error_category}\n"
                f"**Attempts:** {failure_report.attempt_number}\n\n"
                f"### Details\n```\n{failure_report.details}\n```\n\n"
                f"### Context\n"
                + "\n".join(f"- {ctx}" for ctx in failure_report.context)
                + f"\n\n**Execution ID:** {execution_id}"
            )

            # Create ticket (implementation varies by JIRA client)
            if hasattr(self.jira_client, "create_ticket"):
                ticket = await self.jira_client.create_ticket(
                    project_key=self.config.jira_project_key,
                    summary=summary,
                    description=description,
                    issue_type="Bug",
                    labels=["auto-bug", "execution-failure"],
                )
                logger.info(f"Created JIRA ticket: {ticket}")
                return ticket

        except Exception as e:
            logger.error(f"Failed to create JIRA ticket: {e}")

        return None

    async def execute_safe(
        self,
        executor_func: Callable[..., ExecutionResult],
        *args,
        task_name: str = "unnamed_task",
        **kwargs,
    ) -> Level2Result:
        """
        Execute with Level 2 safety wrapper.

        Args:
            executor_func: PersonaExecutor.execute method
            *args: Arguments for executor_func
            task_name: Human-readable task name
            **kwargs: Keyword arguments for executor_func

        Returns:
            Level2Result with complete execution information

        Raises:
            CircuitBreakerOpen: If circuit breaker is open
            HelpNeeded: If all retries exhausted and JIRA created
        """
        import uuid

        result = Level2Result(
            execution_id=str(uuid.uuid4()),
            task_name=task_name,
            final_status=ExecutionStatus.PENDING,
        )
        start_time = time.time()

        # Check circuit breaker
        if self.circuit_breaker.is_open():
            result.final_status = ExecutionStatus.FAILED
            result.circuit_breaker_state = self.circuit_breaker.to_dict()
            raise CircuitBreakerOpen(
                message=f"Circuit breaker is OPEN. Cooldown: {self.l2_config.circuit_breaker_cooldown_seconds}s",
                consecutive_failures=self.circuit_breaker.consecutive_failures,
                cooldown_seconds=self.l2_config.circuit_breaker_cooldown_seconds,
            )

        last_failure_report: Optional[FailureReport] = None

        for attempt_num in range(1, self.l2_config.max_attempts + 1):
            result.level2_attempts = attempt_num

            logger.info(
                f"Level 2 attempt {attempt_num}/{self.l2_config.max_attempts}: {task_name}"
            )

            try:
                # Execute via PersonaExecutor (Level 1)
                l1_result = await executor_func(*args, **kwargs)
                result.level1_results.append(l1_result)

                if l1_result.success:
                    # Success!
                    result.final_status = ExecutionStatus.SUCCESS
                    result.total_duration_seconds = time.time() - start_time
                    result.circuit_breaker_state = self.circuit_breaker.to_dict()
                    self.circuit_breaker.record_success()

                    logger.info(
                        f"Level 2 success after {attempt_num} attempt(s), "
                        f"total L1 attempts: {sum(r.attempt_count for r in result.level1_results)}"
                    )
                    return result

            except UnrecoverableError as e:
                # Level 1 exhausted
                last_failure_report = e.failure_report
                self.circuit_breaker.record_failure()

                logger.warning(
                    f"Level 1 exhausted on L2 attempt {attempt_num}: {str(e)}"
                )

                if attempt_num < self.l2_config.max_attempts:
                    delay = self._calculate_delay(attempt_num)
                    logger.info(f"Level 2 retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)

            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error in Level 2: {e}")
                self.circuit_breaker.record_failure()

                last_failure_report = FailureReport(
                    failed_persona="unknown",
                    error_category="UNKNOWN",
                    details=str(e),
                    attempt_number=attempt_num,
                    recoverable=False,
                )

                if attempt_num < self.l2_config.max_attempts:
                    delay = self._calculate_delay(attempt_num)
                    await asyncio.sleep(delay)

        # All Level 2 retries exhausted
        result.final_status = ExecutionStatus.HELP_NEEDED
        result.total_duration_seconds = time.time() - start_time
        result.circuit_breaker_state = self.circuit_breaker.to_dict()

        # Create JIRA ticket
        if last_failure_report:
            ticket = await self._create_jira_ticket(
                task_name, last_failure_report, result.execution_id
            )
            result.jira_ticket = ticket

        total_l1_attempts = sum(r.attempt_count for r in result.level1_results)

        logger.error(
            f"Level 2 exhausted after {result.level2_attempts} attempts "
            f"(total L1: {total_l1_attempts}). JIRA: {result.jira_ticket}"
        )

        raise HelpNeeded(
            message=f"All retry levels exhausted for {task_name}",
            failure_report=last_failure_report
            or FailureReport(
                failed_persona="unknown",
                error_category="UNKNOWN",
                details="Unknown failure",
                attempt_number=0,
                recoverable=False,
            ),
            total_attempts=total_l1_attempts + result.level2_attempts,
            suggested_actions=[
                "Review JIRA ticket for details",
                "Check logs for root cause",
                "Verify external dependencies",
            ],
        )


async def execute_with_full_retry(
    task: Callable[..., T],
    task_name: str = "task",
    persona_id: str = "default",
    config: Optional[ExecutionConfig] = None,
    *args,
    **kwargs,
) -> Level2Result:
    """
    Convenience function for full two-level retry execution.

    Args:
        task: Callable to execute
        task_name: Name for logging
        persona_id: Persona identifier
        config: Optional configuration override
        *args, **kwargs: Arguments for the task

    Returns:
        Level2Result with complete execution information
    """
    config = config or get_execution_config()
    executor = PersonaExecutor(config=config, persona_id=persona_id)
    wrapper = SafetyRetryWrapper(config=config)

    return await wrapper.execute_safe(
        executor.execute, task, task_name, *args, **kwargs
    )
