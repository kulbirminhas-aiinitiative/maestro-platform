# ADR-3091: Unified Execution Foundation

## Status
Accepted

## Context

The Maestro platform currently has multiple executor implementations scattered across the codebase:

1. `/maestro-hive/iterative_executor.py` - JIRA integration patterns
2. `/src/maestro_hive/core/execution/iterative_executor.py` - SelfHealingEngine, FailureDetector
3. `/src/maestro_hive/execution/iterative_executor.py` - Async patterns, exponential backoff

This fragmentation creates several problems:
- Inconsistent behavior between different execution contexts
- State is lost on process restart (runs in-memory with `/tmp` defaults)
- No unified retry architecture
- Difficult to maintain and extend

## Decision

We will consolidate all executor implementations into a single **Unified Execution Module** at `/src/maestro_hive/unified_execution/` with the following components:

### Module Structure

```
/src/maestro_hive/unified_execution/
├── __init__.py              # Public API exports
├── config.py                # Unified retry configuration
├── exceptions.py            # RecoverableError, UnrecoverableError, HelpNeeded
├── persona_executor.py      # Merged executor (Level 1 retry)
├── safety_retry.py          # External wrapper (Level 2 retry)
└── state_persistence.py     # StateManager integration with /var/maestro/state
```

### Two-Level Retry Architecture

**Level 1 (Internal - PersonaExecutor):**
- `max_attempts`: 3
- `delay`: 1-5 seconds (exponential backoff)
- Integrates SelfHealingEngine for auto-fix
- Raises `UnrecoverableError` on exhaustion

**Level 2 (External - SafetyRetryWrapper):**
- `max_attempts`: 2
- `delay`: exponential backoff (5s, 10s, 20s)
- Circuit breaker: opens after 5 consecutive failures
- Creates JIRA ticket on final failure
- Raises `HelpNeeded` after all retries exhausted

### State Persistence

- Default state path changed from `/tmp` to `/var/maestro/state`
- Uses existing `StateManager` singleton with `auto_persist=True`
- Uses existing `CheckpointManager` for atomic writes with SHA-256 verification
- Process restart automatically resumes from last checkpoint

## Consequences

### Positive
- Single source of truth for execution logic
- State survives process restarts
- Clear separation between internal and external retry levels
- Circuit breaker prevents cascading failures
- Existing infrastructure (StateManager, CheckpointManager) reused

### Negative
- Migration effort required for existing callers
- Deprecated executors need backward-compatible wrappers temporarily

### Risks
- State corruption if multiple processes access same state directory
- Disk space growth if checkpoints not cleaned up

## Acceptance Criteria Mapping

| AC | Requirement | Implementation |
|----|-------------|----------------|
| AC-1 | State persists to /var/maestro/state | `state_persistence.py` with `DEFAULT_STATE_PATH` |
| AC-2 | Process restart auto-resumes | `StatePersistence.restore_latest()` on startup |
| AC-3 | Single PersonaExecutor | `persona_executor.py` merging all 3 implementations |
| AC-4 | Two-level retry operational | `PersonaExecutor` (L1) + `SafetyRetryWrapper` (L2) |

## References

- Architecture Review: `/maestro-hive/CRITICAL_ARCHITECTURE_REVIEW.md`
- StateManager: `/src/maestro_hive/core/state_manager.py`
- CheckpointManager: `/src/maestro_hive/maestro/state/checkpoint.py`
- Gap Analysis: `/maestro-hive/MD-3091_3094_TICKETS.md`
