# Executor Migration Guide

## Overview

This guide helps migrate from deprecated `iterative_executor.py` variants to the unified V2 execution architecture.

## Migration Summary

| Old Component | New Component | Status |
|--------------|---------------|--------|
| `iterative_executor.py` (root) | `persona_executor_v2.py` | Removed |
| `core/execution/iterative_executor.py` | `persona_executor_v2.py` | Removed |
| `execution/iterative_executor.py` | `persona_executor_v2.py` | Removed |

## Step-by-Step Migration

### 1. Update Imports

**Before:**
```python
from iterative_executor import IterativeExecutor
# or
from maestro_hive.core.execution.iterative_executor import IterativeExecutor
# or
from maestro_hive.execution.iterative_executor import IterativeExecutor
```

**After:**
```python
from persona_executor_v2 import PersonaExecutorV2
from parallel_coordinator_v2 import ParallelCoordinatorV2
```

### 2. Update Instantiation

**Before:**
```python
executor = IterativeExecutor(
    output_dir="./output",
    max_iterations=5
)
result = executor.execute(requirement="Build feature X")
```

**After:**
```python
from pathlib import Path

executor = PersonaExecutorV2(
    persona_id="backend_developer",
    output_dir=Path("./output")
)
result = await executor.execute(
    requirement="Build feature X",
    contract=your_contract,
    context={"max_attempts": 3}
)
```

### 3. Handle Token Tracking

The new architecture includes built-in token tracking:

```python
from maestro_hive.cost.token_tracker import TokenTracker

# Create tracker with budget
tracker = TokenTracker(max_tokens_per_persona=100000)

# Record usage (automatic in V2 executors)
tracker.record(persona_id="backend_developer", tokens=5000)

# Check usage
usage = tracker.get_usage("backend_developer")
print(f"Used: {usage.tokens_used} / {usage.budget}")

# Get report
report = tracker.get_report()
```

### 4. Configure Give Up Thresholds

**Before:** No consistent threshold

**After:**
```python
# In persona configuration
persona_config = {
    "max_attempts": 3,  # Default
    "token_budget": 100000,
    "give_up_on_failure": True
}

# Or via environment
export MAESTRO_MAX_ATTEMPTS=3
export MAESTRO_TOKEN_BUDGET=100000
```

### 5. Use Parallel Coordinator for Multi-Persona

**Before:** Manual orchestration

**After:**
```python
from parallel_coordinator_v2 import ParallelCoordinatorV2

coordinator = ParallelCoordinatorV2(
    output_dir=Path("./output"),
    max_parallel_workers=4
)

result = await coordinator.execute_parallel(
    requirement="Build feature X",
    contracts=contracts_list,
    context={"session_id": "exec_001"}
)

# Access results
for persona_id, persona_result in result.persona_results.items():
    print(f"{persona_id}: {persona_result.quality_score}")
```

## Breaking Changes

### 1. Async/Await Required

V2 executors use async/await pattern:

```python
# Old
result = executor.execute(...)

# New
result = await executor.execute(...)
```

### 2. Contract-Based Execution

V2 requires contracts for execution:

```python
contract = {
    "id": "contract_001",
    "name": "Backend API Contract",
    "provider_persona_id": "backend_developer",
    "deliverables": [
        {"name": "api", "artifacts": ["src/*.py"]}
    ]
}

result = await executor.execute(
    requirement="Build API",
    contract=contract
)
```

### 3. Result Structure Changed

**Old:**
```python
result.success
result.output
result.errors
```

**New:**
```python
result.success
result.artifacts  # List of created files
result.quality_score  # 0.0 - 1.0
result.contract_fulfilled  # Boolean
result.duration_seconds
result.tokens_used
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'iterative_executor'`:

1. Update your import to use `persona_executor_v2`
2. Check PYTHONPATH includes the project root
3. Ensure you're using the latest code

### Token Budget Exceeded

If you see `TokenBudgetExceeded` exception:

1. Increase budget: `tracker = TokenTracker(max_tokens_per_persona=200000)`
2. Optimize prompts to reduce token usage
3. Use diff-based edits instead of full rewrites

### Max Attempts Reached

If execution stops at max_attempts:

1. Check logs for root cause
2. Increase `max_attempts` if needed
3. Review and fix underlying issues

## Verification

After migration, verify your code works:

```bash
# Run tests
PYTHONPATH=src python -m pytest tests/ -v

# Verify imports
python -c "from persona_executor_v2 import PersonaExecutorV2; print('OK')"
python -c "from maestro_hive.cost.token_tracker import TokenTracker; print('OK')"
```

## Support

- JIRA: MD-3094 (Token Efficiency & Cleanup)
- ADR: docs/adr/unified-execution-architecture.md
- Questions: Post on MD-3094 comments
