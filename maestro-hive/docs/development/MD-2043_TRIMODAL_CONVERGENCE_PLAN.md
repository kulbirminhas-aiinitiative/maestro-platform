# MD-2043: Trimodal Convergence Completion - Implementation Plan

## Epic Summary

**JIRA:** [MD-2043](https://fifth9.atlassian.net/browse/MD-2043)
**Parent:** MD-2040
**Phase:** Phase 2: Trimodal (Weeks 7-12)
**Complexity:** L (4 weeks)
**Status:** To Do → In Progress

---

## Current State Analysis

### What Exists (Already Implemented)

| Component | File | Status |
|-----------|------|--------|
| Tri-Audit Structure | `tri_audit/tri_audit.py` | Data classes defined |
| 8-Case Truth Table | `determine_verdict()` | COMPLETE |
| Diagnosis Generator | `diagnose_failure()` | COMPLETE |
| Recommendations | `generate_recommendations()` | COMPLETE |
| DDE Integration | `dde/verdict_aggregator.py` | COMPLETE (from MD-2020) |
| BDV Integration | `bdv/integration_service.py` | COMPLETE (from MD-2020) |
| ACC Integration | `acc/integration_service.py` | COMPLETE (from MD-2020) |

### What Needs Work (Stubs)

| Function | Location | Current State |
|----------|----------|---------------|
| `load_dde_audit()` | `tri_audit/tri_audit.py:418` | Returns hardcoded stub |
| `load_bdv_audit()` | `tri_audit/tri_audit.py:434` | Returns hardcoded stub |
| `load_acc_audit()` | `tri_audit/tri_audit.py:449+` | Returns hardcoded stub |
| Persistent Storage | N/A | File-based only |
| Deployment Gate API | N/A | Not implemented |
| Auto-block | N/A | Not implemented |
| Dashboard | N/A | Not implemented |
| Webhooks | N/A | Not implemented |

---

## 8-Case Truth Table (Already Implemented)

```
| DDE | BDV | ACC | Verdict              | can_deploy |
|-----|-----|-----|----------------------|------------|
|  T  |  T  |  T  | ALL_PASS             |    YES     |
|  T  |  F  |  T  | DESIGN_GAP           |    NO      |
|  T  |  T  |  F  | ARCHITECTURAL_EROSION|    NO      |
|  F  |  T  |  T  | PROCESS_ISSUE        |    NO      |
|  F  |  F  |  F  | SYSTEMIC_FAILURE     |    NO      |
|  T  |  F  |  F  | MIXED_FAILURE        |    NO      |
|  F  |  T  |  F  | MIXED_FAILURE        |    NO      |
|  F  |  F  |  T  | MIXED_FAILURE        |    NO      |
```

---

## Implementation Plan

### Phase 1: Wire Real Data Loaders (Story 1-2)

**Story 1: Replace DDE stub with real data loader**

```python
# BEFORE (stub):
def load_dde_audit(iteration_id: str) -> Optional[DDEAuditResult]:
    return DDEAuditResult(iteration_id=iteration_id, passed=True, ...)  # Hardcoded

# AFTER (real):
def load_dde_audit(iteration_id: str) -> Optional[DDEAuditResult]:
    # 1. Load from reports/bdv/{iteration_id}/bdv_results.json
    # 2. Load from DDE performance tracker
    # 3. Convert to DDEAuditResult dataclass
```

**Story 2: Replace BDV/ACC stubs with real data loaders**
- Load BDV from `reports/bdv/{iteration_id}/bdv_validation_result.json`
- Load ACC from `reports/acc/{iteration_id}/acc_validation_result.json`

### Phase 2: Persistent Storage (Story 3)

**Story 3: Implement database-backed audit storage**

```python
# Tables needed:
# - tri_audit_results (execution_id, verdict, timestamp, can_deploy, ...)
# - dde_audit_results (execution_id, score, all_nodes_complete, ...)
# - bdv_audit_results (execution_id, scenarios_passed, scenarios_failed, ...)
# - acc_audit_results (execution_id, conformance_score, violations, ...)
```

Options:
1. **SQLite** (simplest - already used in project)
2. **PostgreSQL** (if already available)
3. **JSON file store** (current approach, enhanced)

**Recommendation:** Start with enhanced JSON file store, migrate to DB later.

### Phase 3: Deployment Gate API (Story 4-5)

**Story 4: Create deployment gate FastAPI endpoint**

```python
# In new file: tri_audit/api.py

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/deployment-gate", tags=["deployment"])

@router.get("/{execution_id}/can-deploy")
async def check_deployment_gate(execution_id: str) -> dict:
    """
    Check if deployment is allowed.
    Returns: {"can_deploy": bool, "verdict": str, "diagnosis": str}
    """
    result = tri_modal_audit(execution_id)
    return {
        "can_deploy": result.can_deploy,
        "verdict": result.verdict.value,
        "diagnosis": result.diagnosis,
        "recommendations": result.recommendations
    }

@router.post("/{execution_id}/force-deploy")
async def force_deploy(execution_id: str, reason: str, approver: str) -> dict:
    """
    Force deployment with override (requires approval).
    Creates audit trail.
    """
    # Implement force-deploy with audit trail
```

**Story 5: Implement auto-block on SYSTEMIC_FAILURE**

```python
@router.get("/{execution_id}/status")
async def get_deployment_status(execution_id: str) -> dict:
    result = load_tri_audit_result(execution_id)

    if result.verdict == TriModalVerdict.SYSTEMIC_FAILURE:
        # Trigger alert
        await send_alert(
            severity="CRITICAL",
            message=f"SYSTEMIC_FAILURE detected for {execution_id}",
            action="Deployment automatically blocked"
        )

    return result.to_dict()
```

### Phase 4: Dashboard & Notifications (Story 6-7)

**Story 6: Create convergence dashboard**

```
┌─────────────────────────────────────────────────────────────┐
│              TRIMODAL CONVERGENCE DASHBOARD                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Execution: sdlc_abc123_20251202_120000                     │
│  Timestamp: 2025-12-02T12:15:00Z                            │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │     DDE     │  │     BDV     │  │     ACC     │         │
│  │     ✅      │  │     ✅      │  │     ✅      │         │
│  │  Score: 97% │  │ Pass: 100%  │  │  Conform:   │         │
│  │             │  │  62/62      │  │    100%     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │  VERDICT: ALL_PASS                              │       │
│  │  DECISION: ✅ APPROVED FOR DEPLOYMENT           │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
│  Recent History:                                            │
│  ├── sdlc_abc123: ALL_PASS ✅                              │
│  ├── sdlc_def456: DESIGN_GAP ⚠️                            │
│  └── sdlc_ghi789: ALL_PASS ✅                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Story 7: Add webhook notifications**

```python
async def send_webhook_notification(
    execution_id: str,
    result: TriAuditResult,
    webhook_url: str
):
    payload = {
        "event": "trimodal_verdict",
        "execution_id": execution_id,
        "verdict": result.verdict.value,
        "can_deploy": result.can_deploy,
        "timestamp": result.timestamp,
        "diagnosis": result.diagnosis
    }

    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=payload)
```

---

## File Changes Summary

| File | Changes |
|------|---------|
| `tri_audit/tri_audit.py` | Replace 3 stub functions with real loaders |
| `tri_audit/api.py` | NEW - FastAPI deployment gate endpoints |
| `tri_audit/storage.py` | NEW - Persistent storage layer |
| `tri_audit/webhooks.py` | NEW - Webhook notification system |
| `tri_audit/dashboard.py` | NEW - Dashboard data provider |

---

## Testing Strategy

### Unit Tests
- Test all 8 truth table cases
- Test each loader function
- Test storage read/write

### Integration Tests
- End-to-end: Run SDLC → Get verdict
- API endpoint tests
- Webhook delivery tests

### Test File
```
tests/tri_audit/
├── test_truth_table.py      # 8 verdict cases
├── test_data_loaders.py     # DDE/BDV/ACC loaders
├── test_api_endpoints.py    # FastAPI tests
└── test_webhooks.py         # Notification tests
```

---

## Acceptance Criteria Checklist

| Criteria | Implementation |
|----------|----------------|
| All 8 truth table cases return correct verdict | `determine_verdict()` - DONE |
| Deployment blocked when can_deploy = False | `tri_modal_audit()` - DONE |
| Audit trail for all deployment decisions | Storage layer - TODO |
| <500ms latency for verdict computation | In-memory with caching - TODO |

---

## Sub-Tasks for JIRA

1. **MD-2043-1**: Replace `load_dde_audit()` stub with real loader
2. **MD-2043-2**: Replace `load_bdv_audit()` stub with real loader
3. **MD-2043-3**: Replace `load_acc_audit()` stub with real loader
4. **MD-2043-4**: Implement persistent audit result storage
5. **MD-2043-5**: Create deployment gate API endpoint (`/api/deployment-gate`)
6. **MD-2043-6**: Implement auto-block on SYSTEMIC_FAILURE
7. **MD-2043-7**: Create convergence dashboard data provider
8. **MD-2043-8**: Add webhook notifications for verdicts
9. **MD-2043-9**: Write unit tests for 8 truth table cases
10. **MD-2043-10**: Write integration tests for full pipeline

---

## Dependencies

| Dependency | Status |
|------------|--------|
| DDE Integration (MD-2020) | COMPLETE |
| BDV Integration (MD-2020) | COMPLETE |
| ACC Integration (MD-2020) | COMPLETE |
| Verdict Aggregator fixes (MD-2023) | COMPLETE |

---

## Timeline Estimate

| Phase | Stories | Estimate |
|-------|---------|----------|
| Phase 1: Data Loaders | 1-3 | 3 days |
| Phase 2: Storage | 4 | 2 days |
| Phase 3: API | 5-6 | 3 days |
| Phase 4: Dashboard/Webhooks | 7-8 | 3 days |
| Testing | 9-10 | 2 days |
| **Total** | | **~13 days** |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance bottleneck | Use caching, async I/O |
| Data format mismatch | Strict schema validation |
| Webhook failures | Retry with exponential backoff |
| Storage corruption | Atomic writes, backups |

---

*Document created: 2025-12-02*
*Author: Claude Code Implementation*
