# ADR-004: Emergency Override ("God Mode")

**EPIC**: MD-3120 - Implement Emergency Override ("God Mode")
**Status**: Accepted
**Date**: 2025-12-11
**Parent**: MD-3200 (Governance Layer)

## Context

If the Constitution policy has a bug (e.g., accidentally banning all file edits), the system could become permanently stuck. We need a "Break Glass" mechanism for human operators to override the Constitution safely.

## Decision

Implement the `maestro-cli override` command with the following security controls:

### 1. Access Control (AC-1)
```python
# Only admin users can invoke override
def check_admin_access(user: str) -> bool:
    """AC-1: Standard user cannot invoke override."""
    admin_users = os.environ.get("MAESTRO_ADMIN_USERS", "").split(",")
    return user in admin_users or user.endswith("@fifth-9.com")
```

### 2. Multi-Signature Requirement
```python
# Require 2 different human signatures for high-risk actions
def require_multi_sig(action: str, signatures: List[str]) -> bool:
    """Require 2 unique signatures for high-risk actions."""
    unique_sigs = set(signatures)
    return len(unique_sigs) >= 2
```

### 3. Time-Limited Token (AC-2)
```python
# Override token expires after 4 hours
OVERRIDE_DURATION_HOURS = 4

@dataclass
class OverrideToken:
    token_id: str
    created_at: datetime
    expires_at: datetime  # created_at + 4 hours
    reason: str
    signatures: List[str]

    def is_expired(self) -> bool:
        """AC-2: Token stops working after 4 hours."""
        return datetime.utcnow() > self.expires_at
```

### 4. Audit Logging (AC-3, AC-4)
```python
# Log EVERYTHING done during override session
class AuditLogger:
    def __init__(self, log_path: str = "/var/log/maestro/override_audit.log"):
        self.log_path = log_path
        self._ensure_immutable()

    def log_action(self, token: OverrideToken, action: str) -> None:
        """AC-3: Actions taken during override are flagged in the log."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "token_id": token.token_id,
            "action": action,
            "flag": "OVERRIDE_SESSION"
        }
        self._append_log(entry)

    def _ensure_immutable(self) -> None:
        """AC-4: Even in God Mode, cannot delete the Audit Log."""
        # Set append-only attribute on audit log
        # chattr +a /var/log/maestro/override_audit.log
```

## CLI Interface

```bash
# Initiate override session
maestro-cli override --reason "Fixing critical policy bug" --signature SIG1

# Second approver adds signature
maestro-cli override --add-signature SIG2 --token <token_id>

# Check override status
maestro-cli override --status

# Actions during override are logged
maestro-cli <any_command>  # Will be logged as OVERRIDE_SESSION
```

## Security Considerations

1. **Admin-Only Access**: Environment variable controls who can override
2. **Dual Control**: Two different signatures required
3. **Time Bound**: 4-hour expiration prevents permanent overrides
4. **Full Audit**: Every action during override is logged
5. **Immutable Logs**: Audit log cannot be deleted even in God Mode

## Files

| File | Purpose |
|------|---------|
| `src/maestro_hive/cli/override.py` | Main override implementation |
| `src/maestro_hive/cli/audit_logger.py` | Immutable audit logging |
| `tests/cli/test_override.py` | Test suite |

## Consequences

### Positive
- System can be recovered from policy bugs
- Full accountability through audit trail
- Time-limited access prevents abuse

### Negative
- Adds complexity to security model
- Requires operational discipline for multi-sig

## Verification

```bash
# Test override access control
pytest tests/cli/test_override.py -v -k "test_ac1"

# Test token expiration
pytest tests/cli/test_override.py -v -k "test_ac2"

# Test audit logging
pytest tests/cli/test_override.py -v -k "test_ac3"

# Test audit immutability
pytest tests/cli/test_override.py -v -k "test_ac4"
```
