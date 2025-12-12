#!/usr/bin/env python3
"""
Token Tracker - Per-Persona Token Usage Tracking (MD-3094)

This module implements token tracking and budget management for persona execution:
- AC-1: Token usage tracked and reported per persona
- AC-2: Configurable max_attempts per persona (default: 3)

Key Features:
    - Per-persona token budgets with configurable limits
    - Real-time usage tracking and reporting
    - Budget exceeded exceptions with context
    - Give Up thresholds (max_attempts) to prevent infinite loops
    - Thread-safe operation for parallel execution

Architecture:
    TokenTracker
        ├── record() - Record token usage for a persona
        ├── get_usage() - Get current usage for a persona
        ├── get_report() - Get comprehensive usage report
        ├── check_budget() - Verify budget not exceeded
        └── check_attempts() - Verify max attempts not exceeded
"""

import logging
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

TOKEN_TRACKER_CONFIG = {
    # Default token budget per persona
    "default_token_budget": int(os.environ.get("MAESTRO_TOKEN_BUDGET", 100000)),

    # Default max attempts per persona (Give Up threshold)
    "default_max_attempts": int(os.environ.get("MAESTRO_MAX_ATTEMPTS", 3)),

    # Warning threshold (percentage of budget)
    "warning_threshold_percent": 80,

    # Enable logging
    "enable_logging": True,

    # Track timestamps
    "track_timestamps": True,
}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class TokenUsage:
    """Token usage record for a single persona."""
    persona_id: str
    tokens_used: int = 0
    budget: int = 100000
    attempts: int = 0
    max_attempts: int = 3
    last_updated: Optional[datetime] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def budget_remaining(self) -> int:
        """Get remaining token budget."""
        return max(0, self.budget - self.tokens_used)

    @property
    def budget_used_percent(self) -> float:
        """Get percentage of budget used."""
        if self.budget <= 0:
            return 100.0
        return (self.tokens_used / self.budget) * 100

    @property
    def attempts_remaining(self) -> int:
        """Get remaining attempts."""
        return max(0, self.max_attempts - self.attempts)

    @property
    def is_over_budget(self) -> bool:
        """Check if over budget."""
        return self.tokens_used >= self.budget

    @property
    def is_max_attempts_reached(self) -> bool:
        """Check if max attempts reached."""
        return self.attempts >= self.max_attempts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona_id": self.persona_id,
            "tokens_used": self.tokens_used,
            "budget": self.budget,
            "budget_remaining": self.budget_remaining,
            "budget_used_percent": round(self.budget_used_percent, 2),
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "attempts_remaining": self.attempts_remaining,
            "is_over_budget": self.is_over_budget,
            "is_max_attempts_reached": self.is_max_attempts_reached,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


@dataclass
class PersonaUsageReport:
    """Comprehensive usage report for all personas."""
    total_tokens_used: int
    total_budget: int
    personas: Dict[str, TokenUsage]
    generated_at: datetime
    warnings: List[str] = field(default_factory=list)

    @property
    def total_budget_used_percent(self) -> float:
        """Get total percentage of budget used."""
        if self.total_budget <= 0:
            return 0.0
        return (self.total_tokens_used / self.total_budget) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tokens_used": self.total_tokens_used,
            "total_budget": self.total_budget,
            "total_budget_used_percent": round(self.total_budget_used_percent, 2),
            "personas": {
                pid: usage.to_dict() for pid, usage in self.personas.items()
            },
            "warnings": self.warnings,
            "generated_at": self.generated_at.isoformat()
        }


class TokenBudgetExceeded(Exception):
    """
    Exception raised when a persona exceeds their token budget.

    Attributes:
        persona_id: The persona that exceeded budget
        tokens_used: Current token usage
        budget: The budget that was exceeded
        message: Human-readable error message
    """

    def __init__(
        self,
        persona_id: str,
        tokens_used: int,
        budget: int,
        message: Optional[str] = None
    ):
        self.persona_id = persona_id
        self.tokens_used = tokens_used
        self.budget = budget
        self.message = message or f"Persona '{persona_id}' exceeded token budget: {tokens_used}/{budget}"
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "error": "TokenBudgetExceeded",
            "persona_id": self.persona_id,
            "tokens_used": self.tokens_used,
            "budget": self.budget,
            "overage": self.tokens_used - self.budget,
            "message": self.message
        }


class MaxAttemptsExceeded(Exception):
    """
    Exception raised when a persona exceeds max attempts (Give Up threshold).

    Attributes:
        persona_id: The persona that exceeded attempts
        attempts: Current attempt count
        max_attempts: The maximum allowed attempts
        message: Human-readable error message
    """

    def __init__(
        self,
        persona_id: str,
        attempts: int,
        max_attempts: int,
        message: Optional[str] = None
    ):
        self.persona_id = persona_id
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.message = message or f"Persona '{persona_id}' exceeded max attempts: {attempts}/{max_attempts}"
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "error": "MaxAttemptsExceeded",
            "persona_id": self.persona_id,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "message": self.message
        }


# =============================================================================
# TOKEN TRACKER
# =============================================================================

class TokenTracker:
    """
    Track token usage and enforce budgets per persona.

    This is the main class for token tracking as required by:
    - AC-1: Token usage tracked and reported per persona
    - AC-2: Configurable max_attempts per persona (default: 3)

    Thread-safe for use in parallel execution environments.

    Example:
        >>> tracker = TokenTracker(max_tokens_per_persona=100000, max_attempts=3)
        >>> tracker.record("backend_developer", tokens=5000)
        >>> usage = tracker.get_usage("backend_developer")
        >>> print(f"Used: {usage.tokens_used} / {usage.budget}")
        Used: 5000 / 100000
    """

    def __init__(
        self,
        max_tokens_per_persona: int = None,
        max_attempts: int = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the token tracker.

        Args:
            max_tokens_per_persona: Default token budget per persona
            max_attempts: Default max attempts per persona (Give Up threshold)
            config: Optional configuration override
        """
        self._config = {**TOKEN_TRACKER_CONFIG, **(config or {})}
        self._default_budget = max_tokens_per_persona or self._config["default_token_budget"]
        self._default_max_attempts = max_attempts or self._config["default_max_attempts"]

        # Per-persona usage tracking
        self._usage: Dict[str, TokenUsage] = {}

        # Thread lock for concurrent access
        self._lock = threading.Lock()

        logger.info("TokenTracker initialized")
        logger.info(f"  Default budget: {self._default_budget:,} tokens")
        logger.info(f"  Default max_attempts: {self._default_max_attempts}")

    def _get_or_create_usage(
        self,
        persona_id: str,
        budget: Optional[int] = None,
        max_attempts: Optional[int] = None
    ) -> TokenUsage:
        """Get existing usage record or create new one."""
        if persona_id not in self._usage:
            self._usage[persona_id] = TokenUsage(
                persona_id=persona_id,
                budget=budget or self._default_budget,
                max_attempts=max_attempts or self._default_max_attempts
            )
        return self._usage[persona_id]

    def record(
        self,
        persona_id: str,
        tokens: int,
        operation: str = "unknown",
        raise_on_exceeded: bool = True
    ) -> TokenUsage:
        """
        Record token usage for a persona.

        Args:
            persona_id: The persona identifier
            tokens: Number of tokens used
            operation: Description of the operation (for history)
            raise_on_exceeded: Whether to raise exception if budget exceeded

        Returns:
            TokenUsage: Updated usage record

        Raises:
            TokenBudgetExceeded: If budget exceeded and raise_on_exceeded=True
        """
        with self._lock:
            usage = self._get_or_create_usage(persona_id)
            usage.tokens_used += tokens
            usage.last_updated = datetime.now()

            # Track history
            if self._config["track_timestamps"]:
                usage.history.append({
                    "tokens": tokens,
                    "operation": operation,
                    "timestamp": usage.last_updated.isoformat(),
                    "cumulative": usage.tokens_used
                })

            # Log if enabled
            if self._config["enable_logging"]:
                logger.debug(f"TokenTracker: {persona_id} +{tokens} = {usage.tokens_used}/{usage.budget}")

            # Check warning threshold
            if usage.budget_used_percent >= self._config["warning_threshold_percent"]:
                logger.warning(
                    f"TokenTracker: {persona_id} at {usage.budget_used_percent:.1f}% of budget"
                )

            # Check if budget exceeded
            if raise_on_exceeded and usage.is_over_budget:
                raise TokenBudgetExceeded(
                    persona_id=persona_id,
                    tokens_used=usage.tokens_used,
                    budget=usage.budget
                )

            return usage

    def record_attempt(
        self,
        persona_id: str,
        raise_on_exceeded: bool = True
    ) -> TokenUsage:
        """
        Record an execution attempt for a persona.

        This implements AC-2: Configurable max_attempts per persona.

        Args:
            persona_id: The persona identifier
            raise_on_exceeded: Whether to raise exception if max attempts exceeded

        Returns:
            TokenUsage: Updated usage record

        Raises:
            MaxAttemptsExceeded: If max attempts exceeded and raise_on_exceeded=True
        """
        with self._lock:
            usage = self._get_or_create_usage(persona_id)
            usage.attempts += 1
            usage.last_updated = datetime.now()

            # Log if enabled
            if self._config["enable_logging"]:
                logger.debug(
                    f"TokenTracker: {persona_id} attempt {usage.attempts}/{usage.max_attempts}"
                )

            # Check if max attempts exceeded
            if raise_on_exceeded and usage.is_max_attempts_reached:
                raise MaxAttemptsExceeded(
                    persona_id=persona_id,
                    attempts=usage.attempts,
                    max_attempts=usage.max_attempts
                )

            return usage

    def get_usage(self, persona_id: str) -> Optional[TokenUsage]:
        """
        Get token usage for a specific persona.

        Args:
            persona_id: The persona identifier

        Returns:
            TokenUsage if persona has usage records, None otherwise
        """
        with self._lock:
            return self._usage.get(persona_id)

    def check_budget(self, persona_id: str, required_tokens: int = 0) -> bool:
        """
        Check if persona has sufficient budget.

        Args:
            persona_id: The persona identifier
            required_tokens: Tokens needed for next operation

        Returns:
            True if budget is sufficient, False otherwise
        """
        with self._lock:
            usage = self._get_or_create_usage(persona_id)
            return (usage.tokens_used + required_tokens) <= usage.budget

    def check_attempts(self, persona_id: str) -> bool:
        """
        Check if persona has remaining attempts.

        Args:
            persona_id: The persona identifier

        Returns:
            True if attempts remaining, False otherwise
        """
        with self._lock:
            usage = self._get_or_create_usage(persona_id)
            return usage.attempts < usage.max_attempts

    def set_budget(self, persona_id: str, budget: int) -> TokenUsage:
        """
        Set custom budget for a persona.

        Args:
            persona_id: The persona identifier
            budget: New budget value

        Returns:
            Updated TokenUsage
        """
        with self._lock:
            usage = self._get_or_create_usage(persona_id, budget=budget)
            usage.budget = budget
            return usage

    def set_max_attempts(self, persona_id: str, max_attempts: int) -> TokenUsage:
        """
        Set custom max_attempts for a persona.

        Args:
            persona_id: The persona identifier
            max_attempts: New max_attempts value

        Returns:
            Updated TokenUsage
        """
        with self._lock:
            usage = self._get_or_create_usage(persona_id, max_attempts=max_attempts)
            usage.max_attempts = max_attempts
            return usage

    def reset(self, persona_id: Optional[str] = None) -> None:
        """
        Reset usage tracking.

        Args:
            persona_id: Specific persona to reset, or None for all
        """
        with self._lock:
            if persona_id:
                if persona_id in self._usage:
                    del self._usage[persona_id]
            else:
                self._usage.clear()
            logger.info(f"TokenTracker reset: {persona_id or 'all'}")

    def get_report(self) -> PersonaUsageReport:
        """
        Generate comprehensive usage report.

        Returns:
            PersonaUsageReport with all persona usage data
        """
        with self._lock:
            total_tokens = sum(u.tokens_used for u in self._usage.values())
            total_budget = sum(u.budget for u in self._usage.values())

            warnings = []
            for pid, usage in self._usage.items():
                if usage.is_over_budget:
                    warnings.append(f"{pid}: OVER BUDGET ({usage.tokens_used}/{usage.budget})")
                elif usage.budget_used_percent >= self._config["warning_threshold_percent"]:
                    warnings.append(f"{pid}: {usage.budget_used_percent:.1f}% of budget used")

                if usage.is_max_attempts_reached:
                    warnings.append(f"{pid}: MAX ATTEMPTS REACHED ({usage.attempts}/{usage.max_attempts})")

            return PersonaUsageReport(
                total_tokens_used=total_tokens,
                total_budget=total_budget,
                personas=dict(self._usage),
                generated_at=datetime.now(),
                warnings=warnings
            )

    def get_all_usage(self) -> Dict[str, TokenUsage]:
        """Get all persona usage records."""
        with self._lock:
            return dict(self._usage)


# =============================================================================
# GLOBAL INSTANCE (Optional singleton pattern)
# =============================================================================

_global_tracker: Optional[TokenTracker] = None


def get_token_tracker() -> TokenTracker:
    """Get or create global token tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenTracker()
    return _global_tracker


def reset_global_tracker() -> None:
    """Reset the global token tracker."""
    global _global_tracker
    if _global_tracker:
        _global_tracker.reset()
    _global_tracker = None
