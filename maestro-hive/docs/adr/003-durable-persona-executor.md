# ADR-003: Durable Persona Executor Integration

**EPIC**: MD-3097 - [CORRECTION] MD-3091: Integrate StateManager for Execution Persistence
**Status**: Accepted
**Date**: 2025-12-11
**Parent**: MD-3091 - Unified Execution Foundation

## Context

MD-3091 established the Unified Execution Foundation with state persistence capabilities. However, the Gemini compliance review identified that the PersonaExecutor needed tighter integration with the StatePersistence module to ensure:

1. Agents survive process interrupts (Ctrl+C, SIGTERM)
2. State is saved after every LLM interaction
3. Memory and history are hydrated on restart

## Decision

Integrate StatePersistence directly into PersonaExecutor with the following hooks:

### 1. Startup State Hydration (AC-2)
```python
# PersonaExecutor.__init__ (lines 180-188)
if self.workflow_id and not self.state_persistence:
    self.state_persistence = StatePersistence(
        config=self.config,
        workflow_id=self.workflow_id
    )
    # StatePersistence auto-restores from checkpoint
```

### 2. Per-Step State Persistence (AC-3)
```python
# PersonaExecutor.execute() (line 430)
await self._execute_attempt(task, attempt, *args, **kwargs)
self._persist_state(result, attempt)  # After EVERY attempt
```

### 3. _persist_state Implementation
```python
def _persist_state(self, result, attempt):
    persona_state = {
        "last_updated": datetime.utcnow().isoformat(),
        "status": attempt.status.value,
        "current_attempt": attempt.attempt_number,
        "tokens_used": self._tokens_used,
        "last_error": attempt.error_message,
        "recovery_applied": result.recovery_applied
    }
    self.state_persistence.update_persona_state(self.persona_id, persona_state)
    self.state_persistence.checkpoint()  # Durable write to disk
```

## State Schema (AC-1)

```python
@dataclass
class ExecutionState:
    workflow_id: str
    phase: str = "initializing"
    step: int = 0
    status: str = "pending"
    persona_states: Dict[str, Dict[str, Any]]  # memory, history per persona
    retry_counts: Dict[str, int]
    completed_tasks: List[str]
    pending_tasks: List[str]
    artifacts: Dict[str, str]
    metrics: Dict[str, Any]
```

## Recovery Flow (AC-4)

```
1. User starts execution (PersonaExecutor.execute())
2. Each attempt triggers _persist_state() -> checkpoint()
3. User hits Ctrl+C (SIGINT)
4. Process dies, checkpoint file remains on disk
5. User restarts execution with same workflow_id
6. StatePersistence.restore_latest() hydrates state
7. PersonaExecutor resumes from last successful step
```

## Files Modified

| File | Changes |
|------|---------|
| `unified_execution/persona_executor.py` | Added state_persistence integration, _persist_state() |
| `unified_execution/state_persistence.py` | AC-1 compliant (created in MD-3091) |
| `unified_execution/__init__.py` | Exported StatePersistence, ExecutionState |

## Consequences

### Positive
- Agents are durable across process restarts
- No lost work on Ctrl+C interruption
- Atomic checkpoint writes prevent corruption

### Negative
- Slight overhead per LLM call (checkpoint write ~5ms)
- Checkpoint files accumulate (mitigated by max_checkpoints_per_workflow)

## Verification

```bash
# Test durability (AC-4)
pytest tests/unified_execution/test_state_persistence.py -v
# All 18 tests pass including test_ac4_survives_kill_and_resumes
```
