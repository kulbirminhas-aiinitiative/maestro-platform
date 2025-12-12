# Maestro Gap Analysis: MD-3162 (Synthetic Checkpoint Generator)

**Date:** December 11, 2025
**Ticket:** MD-3162
**Executor:** TeamExecutionEngineV2 (Maestro)
**Mode:** STRICT (No Fallback Allowed)

## Executive Summary

Maestro V2 failed to generate the source code for the requested feature (`SyntheticCheckpointBuilder`). Instead, it generated the *output* of the requested feature (`checkpoint_design.json`). This failure revealed critical gaps in the `ContractDesignerAgent` and `BlueprintScorer`.

**Root Cause:** Silent fallback to hardcoded behavior masked the actual failures.

**Resolution:** Implement strict mode - fail explicitly rather than produce garbage.

---

## Identified Gaps

### Gap #1: ContractDesignerAgent is Hardcoded (CRITICAL)

| Aspect | Current | Required |
|--------|---------|----------|
| Contract generation | Hardcoded templates | AI-driven with validation |
| On AI failure | Silent fallback | Explicit `AIContractDesignError` |
| Artifact validation | None | Must match requirement language |

**Evidence:**
- Sequential Mode: Generates generic "Deliverables from {persona}" with empty artifact lists
- Parallel Mode: Uses hardcoded "Web App" template regardless of requirement
- Result: `backend_developer` misinterpreted requirement, created JSON instead of Python class

**Strict Mode Fix:**
```python
if not CLAUDE_SDK_AVAILABLE:
    raise AIContractDesignError(
        requirement=requirement,
        reason="Claude SDK not available"
    )
# NO FALLBACK - AI must succeed or error is raised
```

### Gap #2: BlueprintScorer Defaults to Wrong Team (HIGH)

| Aspect | Current | Required |
|--------|---------|----------|
| Default team | Frontend + Backend + DevOps | Match requirement type |
| On low confidence | Proceed anyway | Explicit `LowConfidenceError` |
| Backend-only detection | Not implemented | Check classification |

**Evidence:**
- `_extract_personas_for_requirement` adds `frontend_developer` for backend-only Python task
- Wasted resources on irrelevant personas

**Strict Mode Fix:**
```python
if recommendation.match_score < self.confidence_threshold:
    raise LowConfidenceError(
        component="Blueprint selection",
        confidence=recommendation.match_score,
        threshold=self.confidence_threshold
    )
# NO FALLBACK - must have confident team selection
```

### Gap #3: Test Generation Without Source (MEDIUM)

| Aspect | Current | Required |
|--------|---------|----------|
| Pre-condition check | None | Verify source exists |
| On missing source | Generate broken tests | Explicit error |

**Evidence:**
- `qa_engineer` generated `test_synthetic_checkpoint_comprehensive.py`
- Imports non-existent module `from maestro_hive.unified_execution.synthetic_checkpoint import ...`

**Strict Mode Fix:**
```python
# In QA contract execution
for dependency in contract.dependencies:
    if not self._verify_artifacts_exist(dependency):
        raise DependencyNotMetError(
            contract=contract.name,
            missing_dependency=dependency
        )
```

---

## Priority Matrix

| Gap | Frequency | Impact | Fix Effort | Priority |
|-----|-----------|--------|------------|----------|
| Hardcoded Contracts | Every execution | CRITICAL | Medium | **P0** |
| Bad Persona Extraction | Backend-only tasks | HIGH | Low | **P1** |
| Test w/o Source | When code gen fails | MEDIUM | Low | **P2** |

---

## Strict Mode Exception Hierarchy

```python
class StrictModeViolation(Exception):
    """Base for all strict mode failures."""
    pass

class AIContractDesignError(StrictModeViolation):
    """AI cannot design contracts."""
    pass

class AITeamCompositionError(StrictModeViolation):
    """AI cannot compose team."""
    pass

class LowConfidenceError(StrictModeViolation):
    """AI confidence below threshold."""
    pass

class DependencyNotMetError(StrictModeViolation):
    """Required artifacts from previous phase missing."""
    pass
```

---

## Recommendations for Remediation

### Immediate Fixes (Strict Mode)

1. **Remove all fallback code** - Replace with explicit exceptions
2. **Add contract validation** - Artifacts must match requirement language
3. **Add confidence thresholds** - Fail if AI confidence < 70%

### User Escape Hatches

Users can bypass AI by providing explicit overrides:

```python
result = await engine.execute(
    requirement="Build SyntheticCheckpointBuilder",
    constraints={
        # Override team selection
        "team": ["backend_developer", "qa_engineer"],

        # Override contract design
        "contracts": [
            {
                "persona_id": "backend_developer",
                "deliverables": [{
                    "artifacts": ["src/maestro_hive/unified_execution/synthetic_checkpoint.py"],
                    "acceptance_criteria": ["Class SyntheticCheckpointBuilder exists"]
                }]
            }
        ]
    }
)
```

### Long-Term Improvements

1. **Blueprint Catalog Expansion:** Add "Backend Library" and "CLI Tool" blueprints
2. **Dependency Graph Validation:** Verify all contract dependencies before execution
3. **Observability:** Log which mode was used (AI vs User Override)

---

## Action Plan

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 1 | Add `StrictModeViolation` exception hierarchy | Dev | Pending |
| 2 | Remove fallback in `ContractDesignerAgent` | Dev | Pending |
| 3 | Remove fallback in `TeamComposerAgent` | Dev | Pending |
| 4 | Add `constraints['team']` check | Dev | Pending |
| 5 | Add `constraints['contracts']` check | Dev | Pending |
| 6 | Add contract validation | Dev | Pending |
| 7 | Re-run MD-3162 with strict mode | QA | Pending |

---

## Success Criteria

| Criteria | Metric |
|----------|--------|
| No silent fallbacks | 0 hardcoded template usages |
| Clear errors | All failures include resolution steps |
| User overrides work | `constraints['team']` and `constraints['contracts']` honored |
| MD-3162 passes | Python class generated, not JSON |
