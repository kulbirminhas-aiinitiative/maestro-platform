"""
Unified Execution Module

EPIC: MD-3091 - Unified Execution Foundation

This module consolidates 3 IterativeExecutor implementations into a unified
PersonaExecutor with persistent state and two-level retry architecture.

Architecture:
    Level 1 (PersonaExecutor): Fast internal retry with self-healing
        - max_attempts: 3
        - delay: 1-5 seconds (exponential backoff)
        - Integrates SelfHealingEngine for auto-fix
        - Raises UnrecoverableError on exhaustion

    Level 2 (SafetyRetryWrapper): External safety net
        - max_attempts: 2
        - delay: 5-60 seconds (exponential backoff)
        - Circuit breaker: opens after 5 consecutive failures
        - Creates JIRA ticket on final failure

Usage:
    # Simple Level 1 execution
    from maestro_hive.unified_execution import PersonaExecutor

    executor = PersonaExecutor(persona_id="backend_dev")
    result = await executor.execute(my_task, "Generate API endpoint")

    # Full two-level execution
    from maestro_hive.unified_execution import execute_with_full_retry

    result = await execute_with_full_retry(
        my_task,
        task_name="Generate API endpoint",
        persona_id="backend_dev"
    )

Migration from legacy executors:
    The legacy IterativeExecutor has been removed in MD-3094.
    Use PersonaExecutor from this module instead.

    # Usage (unified)
    from maestro_hive.unified_execution import PersonaExecutor
    executor = PersonaExecutor(persona_id="my_persona")
    result = await executor.execute(task, "task_name")
"""

from .config import (
    ExecutionConfig,
    Level1Config,
    Level2Config,
    StateConfig,
    TokenConfig,
    RecoveryStrategy,
    ErrorCategory,
    get_execution_config,
    reset_execution_config,
)

from .exceptions import (
    ExecutionException,
    RecoverableError,
    UnrecoverableError,
    HelpNeeded,
    CircuitBreakerOpen,
    TokenBudgetExceeded,
    FailureReport,
    GovernanceViolation,
)

from .persona_executor import (
    PersonaExecutor,
    ExecutionResult,
    ExecutionAttempt,
    ExecutionStatus,
    execute_with_level1_retry,
)

from .safety_retry import (
    SafetyRetryWrapper,
    Level2Result,
    CircuitBreaker,
    CircuitState,
    execute_with_full_retry,
)

from .state_persistence import (
    StatePersistence,
    ExecutionState,
    StateCorruptionError,
    DEFAULT_STATE_PATH,
    DEFAULT_CHECKPOINT_PATH,
    get_state_persistence,
    save_state,
    load_state,
)

from .synthetic_checkpoint import (
    SyntheticCheckpointBuilder,
    SyntheticCheckpointConfig,
    SyntheticPhase,
    SyntheticPersonaResult,
    create_synthetic_checkpoint,
)

__all__ = [
    # Configuration
    "ExecutionConfig",
    "Level1Config",
    "Level2Config",
    "StateConfig",
    "TokenConfig",
    "RecoveryStrategy",
    "ErrorCategory",
    "get_execution_config",
    "reset_execution_config",
    # Exceptions
    "ExecutionException",
    "RecoverableError",
    "UnrecoverableError",
    "HelpNeeded",
    "CircuitBreakerOpen",
    "TokenBudgetExceeded",
    "FailureReport",
    "GovernanceViolation",
    # Level 1 - PersonaExecutor
    "PersonaExecutor",
    "ExecutionResult",
    "ExecutionAttempt",
    "ExecutionStatus",
    "execute_with_level1_retry",
    # Level 2 - SafetyRetryWrapper
    "SafetyRetryWrapper",
    "Level2Result",
    "CircuitBreaker",
    "CircuitState",
    "execute_with_full_retry",
    # State Persistence (AC-1, AC-2)
    "StatePersistence",
    "ExecutionState",
    "StateCorruptionError",
    "DEFAULT_STATE_PATH",
    "DEFAULT_CHECKPOINT_PATH",
    "get_state_persistence",
    "save_state",
    "load_state",
    # Synthetic Checkpoint Builder (MD-3162)
    "SyntheticCheckpointBuilder",
    "SyntheticCheckpointConfig",
    "SyntheticPhase",
    "SyntheticPersonaResult",
    "create_synthetic_checkpoint",
]

__version__ = "1.0.0"
