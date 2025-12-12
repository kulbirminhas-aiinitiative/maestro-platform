# ADR: Unified Execution Architecture

## Status

Accepted

## Context

The Maestro platform evolved with multiple execution pathways:
1. `iterative_executor.py` (root) - Original batch executor
2. `src/maestro_hive/core/execution/iterative_executor.py` - Core execution layer
3. `src/maestro_hive/execution/iterative_executor.py` - Execution module duplicate
4. `persona_executor_v2.py` - Contract-based persona executor
5. `parallel_coordinator_v2.py` - Parallel orchestration

This fragmentation caused:
- Token waste from redundant full-file rewrites
- No consistent "Give Up" thresholds
- Maintenance burden of multiple executors
- Inconsistent error handling across pathways

## Decision

We will:

1. **Consolidate to V2 execution architecture**
   - `persona_executor_v2.py` as the single persona execution entry point
   - `parallel_coordinator_v2.py` for multi-persona orchestration
   - `team_execution_v2.py` for team-level coordination

2. **Implement token tracking and budgets**
   - New `TokenTracker` class in `src/maestro_hive/cost/token_tracker.py`
   - Per-persona token budgets with configurable limits
   - Real-time usage reporting

3. **Add configurable "Give Up" thresholds**
   - `max_attempts` parameter per persona (default: 3)
   - Graceful failure with detailed error reporting
   - Prevents infinite retry loops

4. **Remove deprecated executors**
   - Delete all `iterative_executor.py` variants
   - Update imports in dependent modules
   - Provide migration guide for consumers

## Consequences

### Positive
- Single execution pathway reduces maintenance burden
- Token tracking enables cost control and optimization
- Give Up thresholds prevent runaway executions
- Cleaner codebase with less duplication

### Negative
- Breaking change for any code using deprecated executors
- One-time migration effort required

### Risks Mitigated
- Token waste: Tracked and budgeted
- Infinite loops: Bounded by max_attempts
- Inconsistent behavior: Single execution path

## Implementation

### Phase 1: Token Tracking (This EPIC)
- Implement `TokenTracker` class
- Integrate with persona executors
- Add reporting endpoints

### Phase 2: Cleanup (This EPIC)
- Remove deprecated `iterative_executor.py` files
- Update all imports
- Verify no broken dependencies

### Phase 3: Monitoring (Future)
- Dashboard for token usage
- Alerts for budget thresholds
- Historical analysis

## Files Changed

### Removed
- `/iterative_executor.py`
- `/src/maestro_hive/core/execution/iterative_executor.py`
- `/src/maestro_hive/execution/iterative_executor.py`

### Added
- `/src/maestro_hive/cost/token_tracker.py`

### Modified
- `persona_executor_v2.py` (token tracking integration)

## References

- EPIC: MD-3094 - Token Efficiency & Cleanup
- Blocking: MD-3091 - Unified Execution Foundation
- Related: MD-3093 - Shift-Left Validation Integration
