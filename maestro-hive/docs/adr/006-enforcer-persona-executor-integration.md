# ADR-006: Enforcer Middleware Integration into PersonaExecutor

**EPIC**: MD-3126 - Integrate Enforcer Middleware into Persona Executor (Control)
**Status**: Accepted
**Date**: 2025-12-11
**Parent**: MD-3116 - Enforcer Middleware (Synchronous Policy Enforcement)

## Context

The Enforcer Middleware (MD-3116) provides synchronous policy enforcement for blocking illegal agent actions. The PersonaExecutor (MD-3091) handles Level 1 retry and self-healing. These two components need integration so that:

1. Every tool execution is validated against policy.yaml before running
2. Governance violations are logged to audit.log
3. Protected file access and forbidden tools are blocked immediately
4. Validation adds minimal latency (<10ms) to valid operations

## Decision

Integrate the Enforcer into PersonaExecutor as an optional middleware that intercepts task execution:

### 1. GovernanceViolation Exception

```python
# exceptions.py
class GovernanceViolation(Exception):
    """Raised when an action violates governance policy."""
    def __init__(self, message: str, violation_type: str, path: Optional[str] = None):
        super().__init__(message)
        self.violation_type = violation_type
        self.path = path
```

### 2. Enforcer Integration Point (AC-1, AC-2)

```python
# PersonaExecutor.__init__ additions
self.enforcer: Optional[Enforcer] = enforcer
self.audit_log_path: str = audit_log_path or "/var/log/maestro/audit.log"

# Before _execute_attempt (line ~474)
if self.enforcer:
    self._validate_governance(task, args, kwargs)
```

### 3. _validate_governance Implementation

```python
def _validate_governance(
    self,
    task: Callable,
    args: tuple,
    kwargs: Dict[str, Any]
) -> None:
    """
    Validate task execution against governance policy.

    AC-1: Protected file write throws GovernanceViolation
    AC-2: Forbidden tool use throws GovernanceViolation
    AC-4: Violations logged to audit.log
    """
    # Extract tool info from task/args
    tool_name = getattr(task, '__name__', 'unknown_task')
    target_path = kwargs.get('path') or kwargs.get('file_path') or kwargs.get('target')

    # Build agent context
    agent = AgentContext(
        agent_id=self.persona_id,
        role=self._get_persona_role(),
    )

    # Invoke enforcer check
    result = self.enforcer.check(
        agent=agent,
        tool_name=tool_name,
        target_path=target_path,
        action=self._infer_action(tool_name)
    )

    # AC-4: Log to audit
    self._log_audit(result, tool_name, target_path)

    if not result.allowed:
        raise GovernanceViolation(
            message=result.message,
            violation_type=result.violation_type.value if result.violation_type else "policy_violation",
            path=target_path
        )
```

### 4. Performance Requirement (AC-3)

```python
# _validate_governance is synchronous and must complete in <10ms
# Enforcer.check() already has AC-4 performance guarantees (<10ms)
# No additional latency sources in integration code
```

### 5. Audit Logging (AC-4)

```python
def _log_audit(
    self,
    result: EnforcerResult,
    tool_name: str,
    target_path: Optional[str]
) -> None:
    """Log enforcement result to audit.log."""
    import json
    from datetime import datetime

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "persona_id": self.persona_id,
        "tool": tool_name,
        "path": target_path,
        "allowed": result.allowed,
        "violation_type": result.violation_type.value if result.violation_type else None,
        "latency_ms": result.latency_ms
    }

    # Append to audit log
    with open(self.audit_log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

## Files Modified

| File | Changes |
|------|---------|
| `unified_execution/persona_executor.py` | Add enforcer integration, _validate_governance(), _log_audit() |
| `unified_execution/exceptions.py` | Add GovernanceViolation exception |
| `unified_execution/__init__.py` | Export GovernanceViolation |

## Consequences

### Positive
- All persona tool calls are policy-validated before execution
- Governance violations are immediately blocked (fail-fast)
- Audit trail for compliance and debugging
- Minimal latency impact (<10ms for valid actions)

### Negative
- Additional dependency on Enforcer module
- Audit log file I/O per call (mitigated by async logging option)

## Verification

```bash
# Run AC-specific tests
pytest tests/unified_execution/test_enforcer_integration.py -v
# Expected: All 4 AC tests pass
# - test_ac1_protected_file_throws_violation
# - test_ac2_forbidden_tool_throws_violation
# - test_ac3_valid_actions_under_10ms
# - test_ac4_violations_logged_to_audit
```
