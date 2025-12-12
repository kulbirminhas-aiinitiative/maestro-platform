# ADR: JIT Linting Integration for Code Quality

## Status

Accepted

## Context

The Maestro platform's PersonaExecutor generates code artifacts through AI agents. Currently, there is no automated validation of code quality before accepting the output. This leads to:

1. Syntax errors going undetected until runtime
2. Type mismatches causing downstream failures
3. Code style inconsistencies across generated artifacts
4. Manual review burden for code quality issues

The AGORA Architecture (Critics Guild) specifies that code produced by agents must be verified by machine tools before being accepted.

## Decision

We will integrate linting tools (flake8 and mypy) into the PersonaExecutor workflow with an automatic feedback loop:

### 1. Linting Integration

Add a `CodeLinter` class that:
- Runs flake8 for style and syntax checking
- Runs mypy for static type checking
- Returns structured lint results with error details

### 2. Output Type Detection

When `output_type == 'code'`:
- Extract code blocks from persona output
- Automatically run linting pipeline
- Block acceptance if critical errors exist

### 3. Feedback Loop

If linting fails:
- Parse error messages into structured format
- Construct retry prompt with specific error context
- Feed back to agent: "Your code failed linting with errors: X, Y. Please fix."
- Track retry count per execution

### 4. Retry Limits

- Default max_lint_retries: 3
- Configurable via environment: MAESTRO_MAX_LINT_RETRIES
- After max retries, log failure and escalate

## Architecture

```
PersonaExecutor
    ├── execute()
    │   ├── Run persona task
    │   ├── Check output_type
    │   └── If 'code': run lint_and_retry()
    │
    └── lint_and_retry()
        ├── Extract code blocks
        ├── CodeLinter.lint()
        │   ├── flake8 check
        │   └── mypy check
        ├── If errors and retries < max:
        │   ├── Build retry prompt
        │   └── Re-run persona with error context
        └── Return final result
```

## Consequences

### Positive

- Automated code quality enforcement
- Reduced manual review burden
- Consistent code style across generated artifacts
- Early detection of type errors
- Self-healing capability through retry loop

### Negative

- Increased execution time for code generation tasks
- Additional dependencies (flake8, mypy)
- Potential for infinite loops without retry limits

### Mitigations

- Retry limits prevent infinite loops
- Linting runs in subprocess with timeout
- Results cached to avoid redundant checks

## Implementation

### Files to Create

- `src/maestro_hive/quality/code_linter.py` - Core linting logic
- `src/maestro_hive/quality/__init__.py` - Package init
- `tests/quality/test_code_linter.py` - Unit tests

### Files to Modify

- `persona_executor_v2.py` - Add lint integration
- `requirements.txt` - Add flake8, mypy deps

## References

- EPIC: MD-3098 (MD-3092 Correction)
- Vision: docs/vision/AI_ECOSYSTEM.md (Section 5.1 "Critics Guild")
- Roadmap: docs/roadmap/AGORA_ROADMAP.md (Phase 1)
