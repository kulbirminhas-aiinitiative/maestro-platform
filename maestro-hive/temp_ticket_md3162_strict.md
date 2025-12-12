**Summary:** Implement Strict Mode for TeamExecutionEngineV2 (MD-3162 Follow-up)
**Type:** Task
**Priority:** High
**Epic:** MD-3162

---

Implement the "Strict Mode" changes defined in PROPOSED_FIX_MD3162.md to prevent silent failures in AI generation.

### Requirements

1. **ContractDesignerAgent**:
   - Remove silent fallbacks in `_design_sequential_contracts`.
   - Remove hardcoded templates.
   - Raise `AIContractDesignError` when AI fails to generate contracts.

2. **BlueprintScorer**:
   - Raise `LowConfidenceError` when blueprint matching confidence is low (< 0.8).
   - Remove usage of `_default_blueprint_recommendation` in low confidence scenarios.

3. **Exception Handling**:
   - Ensure `TeamExecutionEngineV2` handles these new exceptions gracefully (fail fast and report error).

### References
- `PROPOSED_FIX_MD3162.md`
- `MAESTRO_GAP_ANALYSIS_MD3162.md`
- `STRICT_MODE_IMPLEMENTATION_PLAN.md`
