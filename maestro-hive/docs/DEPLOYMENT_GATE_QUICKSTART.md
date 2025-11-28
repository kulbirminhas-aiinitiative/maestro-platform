# Deployment Gate - Quick Start Guide

## Overview

The Deployment Gate is the **CRITICAL** final protection layer that prevents unsafe code from reaching production. It evaluates tri-modal audit verdicts and enforces deployment decisions.

**Core Principle**: Only `ALL_PASS` verdicts allow deployment to production.

---

## Quick Reference

### Verdict Decision Table

| Verdict | Gate Status | Deploy Allowed | Action |
|---------|-------------|----------------|--------|
| ALL_PASS | PASS | YES | Deploy automatically |
| DESIGN_GAP | WARN | YES (with caution) | Deploy but review |
| PROCESS_ISSUE | WARN | YES (with caution) | Deploy but review |
| ARCHITECTURAL_EROSION | FAIL | NO | Fix or request override |
| SYSTEMIC_FAILURE | FAIL | NO | Fix or request override |
| MIXED_FAILURE | FAIL | NO | Fix or request override |

---

## Usage

### 1. Command Line (CI/CD)

```bash
# Check deployment gate (returns exit code 0 or 1)
python tri_audit_gate_cli.py check --verdict ALL_PASS --iteration iter-123

# Check with JSON output
python tri_audit_gate_cli.py check --verdict SYSTEMIC_FAILURE --iteration iter-456 --json

# View gate status
python tri_audit_gate_cli.py status --iteration iter-123

# View metrics
python tri_audit_gate_cli.py metrics --days 30
```

### 2. Python API

```python
from test_deployment_gate import DeploymentGate, TriModalVerdict

# Initialize gate
gate = DeploymentGate()

# Check gate (returns GateResult)
result = gate.check(TriModalVerdict.ALL_PASS.value, "iter-123")
print(f"Deploy Allowed: {result.deploy_allowed}")
print(f"Status: {result.status.value}")
print(f"Message: {result.message}")

# Enforce gate (raises exception if blocked)
try:
    gate.enforce(verdict, iteration_id)
    print("Deployment approved!")
except DeploymentBlockedException as e:
    print(f"Deployment blocked: {e}")
```

### 3. Override Workflow

```bash
# Developer requests override
python tri_audit_gate_cli.py override \
  --iteration iter-789 \
  --requester dev@example.com \
  --justification "Emergency production hotfix for customer-facing bug" \
  --verdict SYSTEMIC_FAILURE

# Manager approves override
python tri_audit_gate_cli.py approve \
  --iteration iter-789 \
  --approver manager@example.com

# Re-check gate (now passes with override)
python tri_audit_gate_cli.py check --verdict SYSTEMIC_FAILURE --iteration iter-789
```

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Check Deployment Gate
  run: |
    python tri_audit_gate_cli.py check \
      --verdict ${{ steps.audit.outputs.verdict }} \
      --iteration ${{ github.run_id }}
```

### GitLab CI

```yaml
deploy_gate:
  script:
    - python tri_audit_gate_cli.py check --verdict $VERDICT --iteration $CI_PIPELINE_ID
```

### Jenkins

```groovy
stage('Deployment Gate') {
    steps {
        sh 'python tri_audit_gate_cli.py check --verdict ${VERDICT} --iteration ${BUILD_ID}'
    }
}
```

---

## Test Coverage

All 20 required tests (TRI-301 to TRI-320) implemented and passing:

- **TRI-301 to TRI-305**: Gate Enforcement (5 tests)
- **TRI-306 to TRI-310**: Override Handling (5 tests)
- **TRI-311 to TRI-315**: CI/CD Integration (5 tests)
- **TRI-316 to TRI-320**: Audit Trail (5 tests)

**Pass Rate**: 100% (22/22 tests)
**Execution Time**: < 1 second

---

## Files

- **Test Suite**: `tests/tri_audit/integration/test_deployment_gate.py` (1,084 lines)
- **CLI Tool**: `tri_audit_gate_cli.py` (245 lines)
- **Documentation**: `docs/DEPLOYMENT_GATE_SUMMARY.md` (535 lines)

---

## Exit Codes

- `0` = Deployment approved (gate PASS)
- `1` = Deployment blocked (gate FAIL)
- `2` = Invalid arguments or error

---

## Examples

### Example 1: Successful Deployment

```bash
$ python tri_audit_gate_cli.py check --verdict ALL_PASS --iteration iter-001
Gate Status: PASS
Deploy Allowed: True
Message: All audits passed. Deployment approved.

$ echo $?
0
```

### Example 2: Blocked Deployment

```bash
$ python tri_audit_gate_cli.py check --verdict SYSTEMIC_FAILURE --iteration iter-002
Gate Status: FAIL
Deploy Allowed: False
Message: Deployment blocked. Fix issues or request override.

$ echo $?
1
```

### Example 3: JSON Output

```bash
$ python tri_audit_gate_cli.py check --verdict ALL_PASS --iteration iter-003 --json
{
  "status": "PASS",
  "deploy_allowed": true,
  "message": "All audits passed. Deployment approved.",
  "verdict": "ALL_PASS"
}
```

---

## Troubleshooting

### Gate blocked but need to deploy?

1. Request override with justification:
   ```bash
   python tri_audit_gate_cli.py override \
     --iteration iter-XXX \
     --requester your-email@example.com \
     --justification "Emergency production fix required" \
     --verdict SYSTEMIC_FAILURE
   ```

2. Get manager approval:
   ```bash
   python tri_audit_gate_cli.py approve \
     --iteration iter-XXX \
     --approver manager@example.com
   ```

3. Re-check gate (should now pass):
   ```bash
   python tri_audit_gate_cli.py check --verdict SYSTEMIC_FAILURE --iteration iter-XXX
   ```

### View audit history

```bash
# Show gate status and history
python tri_audit_gate_cli.py status --iteration iter-XXX

# Show metrics
python tri_audit_gate_cli.py metrics --days 30
```

---

## Security & Compliance

- All gate checks logged with timestamp
- User tracking (who triggered deployment)
- Override tracking (who approved override)
- Time-limited overrides (default 24 hours)
- Complete audit trail for compliance
- Two-person rule for overrides (requester + approver)

---

## Support

For issues or questions:
1. Check audit trail: `python tri_audit_gate_cli.py status --iteration <ID>`
2. Review metrics: `python tri_audit_gate_cli.py metrics`
3. See full documentation: `docs/DEPLOYMENT_GATE_SUMMARY.md`
4. Run tests: `pytest tests/tri_audit/integration/test_deployment_gate.py -v`
