# Bug Tickets for Team Execution V2 Workflow Issues

**Parent Epic**: MD-592 (Epic 1: Core Execution Engine (DDE))
**Labels**: `bug`, `backend-engine`

---

## BUG 1: Blueprint Search Type Error

**Summary**: [BUG] Blueprint search fails with BlueprintMetadata type error

**Priority**: High

**Labels**: `bug`, `backend-engine`, `workflow`

**Description**:
```
Error: 'BlueprintMetadata' object is not subscriptable

Location: team_execution_v2.py - recommend_blueprint() method

Impact: Falls back to "Basic Sequential Team" instead of selecting optimal
blueprint based on requirement classification.

Steps to reproduce:
1. Run team_execution_v2.py with any requirement
2. Observe Step 2 Blueprint Selection fails

Expected: Blueprint search returns correct result without type error
Actual: Type error prevents proper blueprint selection

Root cause: The code tries to subscript a BlueprintMetadata object like a
dictionary when it should use attribute access.
```

**Acceptance Criteria**:
- [ ] Blueprint search returns correct result without type error
- [ ] Appropriate blueprint selected based on requirement classification
- [ ] Add unit test for blueprint search

---

## BUG 2: Missing Contract Manager Module

**Summary**: [BUG] Contract manager module not available - affects contract validation

**Priority**: Medium

**Labels**: `bug`, `backend-engine`, `dependencies`

**Description**:
```
Warning: Contract manager not available: No module named
'contracts.integration.contract_manager'

Location: team_execution_v2.py imports (lines 57-67)

Impact: Contract validation and management features disabled. Fallback behavior
works but lacks full contract validation capabilities.

Expected: Either the module is available or a clear standalone fallback exists
Actual: Module not found, falls back silently
```

**Acceptance Criteria**:
- [ ] Either install/configure the contracts module OR implement standalone fallback
- [ ] Clear error message if feature is unavailable
- [ ] Document required dependencies in README

---

## BUG 3: Missing Maestro Engine Module

**Summary**: [BUG] maestro-engine not available - using fallback personas

**Priority**: Medium

**Labels**: `bug`, `backend-engine`, `dependencies`

**Description**:
```
Warning: maestro-engine not available, using fallback personas:
No module named 'src'

Location: parallel_coordinator_v2.py / persona_executor_v2.py

Impact: Uses hardcoded fallback personas instead of dynamic engine. This may
result in less optimal persona selection for requirements.

Expected: Dynamic persona loading from maestro-engine
Actual: Falls back to hardcoded persona definitions
```

**Acceptance Criteria**:
- [ ] Proper module path configuration OR standalone personas implementation
- [ ] Document required dependencies
- [ ] Ensure fallback personas are comprehensive for common use cases

---

## BUG 4: Low Confidence AI Classification

**Summary**: [BUG] AI requirement classification returns low confidence (60%)

**Priority**: Low

**Labels**: `bug`, `backend-engine`, `ai-quality`

**Description**:
```
Classification confidence: 60%
Typical threshold: 80%

Location: team_execution_v2.py - TeamComposerAgent.analyze_requirement()

Impact: May cause suboptimal team composition or workflow decisions due to
uncertain classification.

Test case:
Requirement: "Create a simple API endpoint"
Result: 60% confidence, classified as fully_sequential (may be incorrect)

Expected: Confidence >= 80% for clear requirements
Actual: 60% confidence suggests unclear prompt or response parsing issues
```

**Acceptance Criteria**:
- [ ] Improve prompt for better classification accuracy
- [ ] Add warning when confidence below threshold
- [ ] Consider retry with refined prompt when confidence is low
- [ ] Log the full classification response for debugging

---

## How to Create These Tickets

Since the API token lacks create permissions, create these manually in JIRA:

1. Go to https://fifth9.atlassian.net/jira/software/projects/MD/boards
2. Create new Task
3. Set parent to MD-592
4. Copy summary and description from above
5. Add labels: `bug`, `backend-engine`, etc.
6. Set priority

Or request elevated API token permissions to enable automated ticket creation.
