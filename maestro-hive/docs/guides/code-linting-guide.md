# Code Linting Integration Guide

## Overview

This guide explains how the JIT (Just-In-Time) linting integration works in the PersonaExecutor workflow to automatically validate code quality.

## Quick Start

### Enable Linting for Code Output

```python
from maestro_hive.quality.code_linter import CodeLinter

# Create linter instance
linter = CodeLinter()

# Lint a code snippet
result = linter.lint(code_content, language="python")

if result.has_errors:
    print(f"Linting failed: {result.errors}")
else:
    print("Code passed all checks")
```

### With PersonaExecutor Integration

```python
from persona_executor_v2 import PersonaExecutorV2

executor = PersonaExecutorV2(
    persona_id="backend_developer",
    enable_linting=True,  # Enable automatic linting
    max_lint_retries=3    # Retry up to 3 times on lint failure
)

result = await executor.execute(
    requirement="Write a function to calculate fibonacci",
    output_type="code"  # This triggers automatic linting
)

# Result includes lint status
print(f"Lint passed: {result.lint_passed}")
print(f"Lint attempts: {result.lint_attempts}")
```

## How It Works

### 1. Output Type Detection

When `output_type == 'code'`, the executor automatically:
1. Extracts code blocks from the persona output
2. Runs flake8 for style/syntax checking
3. Runs mypy for type checking
4. Evaluates combined results

### 2. Feedback Loop

If linting fails:

```
┌────────────────────────────────────────────────┐
│  Agent generates code                          │
│             ↓                                  │
│  Linter checks code                            │
│             ↓                                  │
│  Errors found?                                 │
│    YES → Build retry prompt with errors        │
│          Feed back to agent                    │
│          Repeat (up to max_lint_retries)       │
│    NO  → Accept code, continue                 │
└────────────────────────────────────────────────┘
```

### 3. Retry Prompt Format

When errors are detected, the agent receives:

```
Your code failed linting with the following errors:

flake8:
- Line 5: E302 expected 2 blank lines, found 1
- Line 12: E501 line too long (95 > 79 characters)

mypy:
- Line 8: error: Incompatible types in assignment

Please fix these errors and provide the corrected code.
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| MAESTRO_MAX_LINT_RETRIES | 3 | Max retry attempts for lint failures |
| MAESTRO_LINT_TIMEOUT | 30 | Timeout in seconds for lint commands |
| MAESTRO_ENABLE_MYPY | true | Enable mypy type checking |
| MAESTRO_ENABLE_FLAKE8 | true | Enable flake8 style checking |

### Programmatic Configuration

```python
from maestro_hive.quality.code_linter import LinterConfig

config = LinterConfig(
    max_retries=5,
    enable_mypy=True,
    enable_flake8=True,
    flake8_config={
        "max_line_length": 120,
        "ignore": ["E501", "W503"]
    },
    mypy_config={
        "ignore_missing_imports": True,
        "strict": False
    }
)

linter = CodeLinter(config=config)
```

## Linter Output Structure

```python
@dataclass
class LintResult:
    passed: bool
    errors: List[LintError]
    warnings: List[LintWarning]
    flake8_output: str
    mypy_output: str
    duration_seconds: float

@dataclass
class LintError:
    tool: str  # "flake8" or "mypy"
    line: int
    column: int
    code: str
    message: str
```

## Error Categories

### Blocking Errors (Fail Lint)
- Syntax errors (E999)
- Type errors (mypy)
- Undefined names (F821)
- Import errors (F401)

### Warnings (Pass with Warning)
- Line too long (E501)
- Whitespace issues (W291, W293)
- Import order (I001)

## Troubleshooting

### Lint Times Out

If linting takes too long:
1. Increase MAESTRO_LINT_TIMEOUT
2. Check for infinite loops in generated code
3. Verify flake8/mypy are installed correctly

### Mypy Import Errors

If mypy reports missing imports:
1. Add `--ignore-missing-imports` to config
2. Or install type stubs: `pip install types-requests`

### Flake8 False Positives

To ignore specific rules:
```python
config = LinterConfig(
    flake8_config={"ignore": ["E501", "W503"]}
)
```

## Best Practices

1. **Start with defaults** - The default configuration works well for most cases
2. **Review lint history** - Check `result.lint_attempts` to identify problematic patterns
3. **Don't disable too much** - Only ignore rules that consistently cause false positives
4. **Monitor retry rates** - High retry rates may indicate prompt quality issues

## Related Documentation

- ADR: docs/adr/jit-linting-integration.md
- EPIC: MD-3098
- Critics Guild Vision: docs/vision/AI_ECOSYSTEM.md (Section 5.1)
