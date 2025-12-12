# JIRA Tickets: Workflow Modernization (MD-3091 - MD-3094)

Based on the "Critical Architecture Review" and the goal of moving from "Retry-Based" to "Refinement-Based" autonomy.

---

## CRITICAL REVIEW (Claude Opus 4.5 - 2025-12-11)

### Executive Summary

This document contains **Gemini's proposals** for tickets MD-3091 to MD-3094. These proposals were reviewed against the **actual JIRA tickets** created after independent codebase exploration. Key finding: **Gemini's proposals overlap with actual tickets but have different scope and prioritization.**

### Comparison Matrix

| Ticket | Gemini's Proposal | Actual JIRA Content | Verdict |
|--------|-------------------|---------------------|---------|
| **MD-3091** | JIT Validation (Micro-Loops) | Unified Execution Foundation | **CHALLENGE** |
| **MD-3091-CORRECTION** | N/A | Fix Missing State Persistence | **NEW - CRITICAL** |
| **MD-3092** | Stateful Orchestration | JIT Validation & Persona Reflection | **PARTIALLY ACCEPT** |
| **MD-3093** | BDV/ACC Prompt Injection | Shift-Left Validation Integration | **ACCEPT as Enhancement** |
| **MD-3094** | Feedback Highway | Token Efficiency & Cleanup | **ACCEPT - Merge** |

### Key Architectural Decisions

1. **Foundation First (MD-3091):** State persistence and executor consolidation must come BEFORE JIT validation. Without persistent state, JIT validation improvements are wasted on restart.

2. **Reuse Existing Infrastructure:** Gemini proposes new `execution_state.json` files. Better approach: reuse existing `StateManager` and `CheckpointManager` classes.

3. **Two-Level Retry:** Gemini's "Feedback Highway" should be part of the unified retry architecture, not a separate system.

### Reference Documents
- Architecture Review: `/maestro-hive/CRITICAL_ARCHITECTURE_REVIEW.md`
- Implementation Plan: `~/.claude/plans/reflective-cuddling-harp.md`
- Actual JIRA: MD-3091, MD-3092, MD-3093, MD-3094 (fifth9.atlassian.net)

---

## GEMINI'S ORIGINAL PROPOSALS (with inline review)

## MD-3091: Implement JIT Validation (Micro-Loops) in PersonaExecutor

> ### REVIEW VERDICT: CHALLENGE - Wrong Priority Order
>
> | Aspect | Assessment |
> |--------|------------|
> | Concept | Valid - JIT validation is needed |
> | Priority | **WRONG** - Should not be first |
> | Rationale | Foundation work (state persistence) must come BEFORE JIT validation. Without persistent state, improvements are lost on restart. |
>
> **Action Taken:** This content moved to **actual MD-3092**. Actual MD-3091 contains "Unified Execution Foundation":
> - Change default state path from `/tmp` to `/var/maestro/state`
> - Merge 3 IterativeExecutor implementations into single PersonaExecutor
> - Two-level retry (internal 3x + external 2x with circuit breaker)
>
> **Existing Infrastructure Gemini Missed:**
> - `StateManager` at `/src/maestro_hive/core/state_manager.py`
> - `CheckpointManager` at `/src/maestro_hive/maestro/state/checkpoint.py`
> - `DAGExecutor` at `/src/maestro_hive/dag/dag_executor.py` (already has checkpoint/resume)
>
> ### 🔴 STATUS UPDATE (2025-12-11): INCOMPLETE
> **Gap Analysis:** The implementation of MD-3091 is missing the critical "State Persistence" layer. The code runs in-memory only.
> **Action:** Created correction ticket **MD-3091-CORRECTION** to implement `StateManager` integration.
> **See:** `MD-3091_GAPS.md` for detailed findings.

**Type:** Story
**Priority:** Critical
**Component:** Persona Engine
**Epic:** MD-3089 (Core Platform Stability)

**Description:**
Currently, `PersonaExecutorV2` operates in "Single-Shot" mode. It generates code and returns immediately. Validation happens minutes later at the team level.
We need to implement a "Micro-Loop" *inside* the persona execution to catch syntax and basic logic errors immediately.

**Acceptance Criteria:**
1.  **Syntax Check:** After generating any Python file, the executor must run `ast.parse()` on it.
2.  **Self-Correction:** If syntax check fails, the executor must feed the error back to the AI and request a fix (up to 3 attempts).
3.  **Linting (Optional):** Run `pylint` or `flake8` on generated code and include critical errors in the self-correction loop.
4.  **Output:** The executor only returns after the code passes syntax checks or retries are exhausted.

**Technical Implementation:**
- Modify `src/maestro_hive/teams/persona_executor_v2.py`.
- Add `_validate_syntax(file_path)` method.
- Wrap the generation call in a `while attempts < max_retries:` loop.

---

## MD-3092: Implement Stateful Orchestration in ParallelCoordinator

> ### REVIEW VERDICT: PARTIALLY ACCEPT - Good Concept, Wrong Approach
>
> | Aspect | Assessment |
> |--------|------------|
> | Concept | **VALID** - Stateful orchestration is critical |
> | Approach | **SUBOPTIMAL** - Creates new state file instead of reusing existing infrastructure |
>
> **What Gemini Proposes:**
> ```python
> # New execution_state.json in ParallelCoordinator
> def save_state(self):
>     with open("execution_state.json", "w") as f:
>         json.dump(self.state, f)
> ```
>
> **Better Approach (Actual Implementation):**
> ```python
> # Reuse existing StateManager + CheckpointManager
> from maestro_hive.core.state_manager import StateManager
> from maestro_hive.maestro.state.checkpoint import CheckpointManager
>
> state_manager = StateManager(persistence_dir="/var/maestro/state", auto_persist=True)
> checkpoint_manager = CheckpointManager(state_manager)
> ```
>
> **Rationale:** Don't create ANOTHER state file in ANOTHER location. The codebase already has:
> - `StateManager` with thread-safe persistence
> - `CheckpointManager` with atomic writes and SHA-256 verification
> - `DAGExecutor` with node-level state tracking
>
> **Action Taken:** Stateful orchestration moved to **actual MD-3091** as "Unified Execution Foundation"
>
> ### 🟡 STATUS UPDATE (2025-12-11): PARTIAL
> **Gap Analysis:** Syntax checking (`ast.parse`) is implemented in `PersonaExecutor._validate_python_syntax`. However, deeper validation (linting, static analysis) is missing.
> **Action:** Proceed with implementation but prioritize MD-3091-CORRECTION first.

**Type:** Story
**Priority:** High
**Component:** Orchestration
**Epic:** MD-3089

**Description:**
Currently, if one persona fails, the `IterativeExecutor` restarts the entire team. This wipes out successful work from other personas.
We need "Stateful Orchestration" where the coordinator remembers which personas succeeded and skips them on retry.

**Acceptance Criteria:**
1.  **State Persistence:** `ParallelCoordinatorV2` must save a `execution_state.json` file containing the status (`SUCCESS`/`FAILURE`) and artifact paths for each persona.
2.  **Smart Resume:** On startup, check for `execution_state.json`.
3.  **Skip Logic:** If a persona is marked `SUCCESS` and inputs haven't changed, skip execution and reload artifacts from disk.
4.  **Force Refresh:** Add a `--force` flag to ignore state.

**Technical Implementation:**
- Modify `src/maestro_hive/teams/parallel_coordinator_v2.py`.
- Implement `save_state()` and `load_state()` methods.
- Update `execute_parallel()` to check state before spawning tasks.

---

## MD-3093: Implement Trimodal Injection (BDV/ACC) in Prompts

> ### REVIEW VERDICT: ACCEPT as Enhancement
>
> | Aspect | Assessment |
> |--------|------------|
> | Concept | **EXCELLENT** - Proactive constraint injection |
> | Complementary | Yes - adds to actual MD-3093 scope |
>
> **Why This Is Good:**
> - Gemini proposes **proactive** validation (inject rules INTO prompt)
> - Actual MD-3093 focuses on **reactive** validation (move validation earlier in pipeline)
> - Both approaches are valid and **complementary**
>
> **Action Taken:** Added as **AC-5** to actual MD-3093:
> - AC-5: Inject BDV Gherkin features and ACC architectural rules into persona prompts
>
> **Implementation Suggestion:**
> ```python
> def _build_persona_prompt(self, persona, requirement):
>     prompt = base_prompt
>
>     # Gemini's suggestion - inject constraints proactively
>     if bdv_features := bdv_service.get_features(requirement):
>         prompt += f"\n## Must-Pass Tests\n{bdv_features}"
>
>     if acc_rules := acc_service.get_rules():
>         prompt += f"\n## Architectural Constraints\n{acc_rules}"
>
>     return prompt
> ```
>
> ### 🔴 STATUS UPDATE (2025-12-11): FAILED
> **Gap Analysis:** No evidence of "Prompt Injection" or BDV/ACC constraint enforcement in `PersonaExecutor`. It executes tasks blindly without injecting safety rules.
> **Action:** Needs implementation of `_build_persona_prompt` logic to inject constraints.

**Type:** Story
**Priority:** High
**Component:** Team Execution
**Epic:** MD-3089

**Description:**
Currently, BDV (Behavior-Driven Validation) and ACC (Architectural Conformance) are used only as "Final Exams".
We need to inject these rules into the *input prompt* so the AI knows the constraints *before* it writes code.

**Acceptance Criteria:**
1.  **BDV Injection:** If Gherkin features exist for the requirement, inject them into the System Prompt as "Must-Pass Tests".
2.  **ACC Injection:** Inject the project's architectural rules (e.g., "Domain layer cannot import Infrastructure") into the System Prompt.
3.  **Prompt Update:** Update `_build_persona_prompt` in `team_execution_v2.py` to include these sections.

**Technical Implementation:**
- Modify `src/maestro_hive/teams/team_execution_v2.py`.
- Fetch BDV features using `bdv_service.get_features()`.
- Fetch ACC rules using `acc_service.get_rules()`.
- Append to prompt context.

---

## MD-3094: Implement Feedback Highway (Structured Failure Reporting)

> ### REVIEW VERDICT: ACCEPT - But Merge into MD-3091
>
> | Aspect | Assessment |
> |--------|------------|
> | Concept | **VALID** - Structured failure reporting is needed |
> | Standalone | **NO** - Should be part of two-level retry architecture |
>
> **Why Merge:**
> The `failure_report.json` is exactly what `SafetyRetryWrapper` (Level 2 retry) needs to make intelligent decisions. Creating it as a separate system creates coupling issues.
>
> **Better Architecture:**
> ```python
> # Part of two-level retry in MD-3091
> @dataclass
> class FailureReport:
>     failed_persona: str
>     error_category: Literal["SYNTAX", "TEST_FAILURE", "ACC_VIOLATION", "TIMEOUT"]
>     details: str
>     context: List[str]
>     attempt_number: int
>     recoverable: bool
>
> class SafetyRetryWrapper:
>     def handle_failure(self, error: UnrecoverableError) -> FailureReport:
>         return FailureReport(
>             failed_persona=error.persona_id,
>             error_category=self._classify_error(error),
>             details=str(error),
>             context=error.file_paths,
>             attempt_number=self.current_attempt,
>             recoverable=self._is_recoverable(error)
>         )
> ```
>
> **Action Taken:** Concept merged into **actual MD-3091** two-level retry design. Actual MD-3094 repurposed for "Token Efficiency & Cleanup"
>
> ### 🔴 STATUS UPDATE (2025-12-11): FAILED
> **Gap Analysis:** `_check_token_budget` method is defined in `PersonaExecutor` but **never called**. The budget limits are ignored.
> **Action:** Wire up `_check_token_budget` in the execution loop.

**Type:** Story
**Priority:** Medium
**Component:** Self-Healing
**Epic:** MD-3089

**Description:**
Currently, the `IterativeExecutor` relies on parsing unstructured logs to decide how to fix a failure.
We need a structured `failure_report.json` passed from the Team Engine to the Self-Healing Engine.

**Acceptance Criteria:**
1.  **Structured Output:** `team_execution_v2.py` must write a `failure_report.json` on exit if it fails.
2.  **Content:** The JSON must include:
    - `failed_persona`: ID of the persona that failed.
    - `error_category`: `SYNTAX`, `TEST_FAILURE`, `ACC_VIOLATION`, etc.
    - `details`: Specific error message or diff.
    - `context`: Relevant file paths.
3.  **Consumption:** `IterativeExecutor` must read this file and use it to construct the "Repair Prompt" for the next iteration.

**Technical Implementation:**
- Modify `src/maestro_hive/teams/team_execution_v2.py` to dump JSON on exception/failure.
- Modify `src/maestro_hive/core/execution/iterative_executor.py` to read JSON.

---

## FINAL RECONCILIATION

### What's Actually in JIRA (fifth9.atlassian.net)

| Ticket | Actual Title | Priority | Content |
|--------|--------------|----------|---------|
| **MD-3091** | Unified Execution Foundation | P0 | State persistence, executor merge, two-level retry |
| **MD-3092** | JIT Validation & Persona Reflection | P0 | AST validation, reflection loop, test execution |
| **MD-3093** | Shift-Left Validation Integration | P1 | BDV/ACC earlier + prompt injection (Gemini's idea) |
| **MD-3094** | Token Efficiency & Cleanup | P2 | Token tracking, deprecated code removal |

### Dependency Chain

```
MD-3091 (Foundation) ─┬─► MD-3092 (JIT) ─┬─► MD-3093 (Shift-Left)
                      ├─► MD-3093        │
                      └─► MD-3094        │
                          MD-3092 ───────┘
```

### Gemini Contributions Incorporated

1. **MD-3093 AC-5:** BDV/ACC prompt injection (from Gemini's MD-3093)
2. **MD-3091 FailureReport:** Structured failure data class (from Gemini's MD-3094)

---

## CORRECTION TICKETS (Created 2025-12-11)

Based on Gemini's gap analysis, the following correction tickets were created:

| Ticket | Original | Gap | Priority | Status |
|--------|----------|-----|----------|--------|
| **MD-3096** | MD-3093 | Proactive Constraint Injection (BDV/ACC in prompts) | P1 | To Do |
| **MD-3097** | MD-3091 | State Persistence (StateManager not integrated) | P0 | To Do |
| **MD-3098** | MD-3092 | Linting Integration (pylint/ruff not in JIT loop) | P1 | To Do |
| **MD-3099** | MD-3094 | Token Budget Wiring (_check_token_budget never called) | P1 | To Do |

### Evidence of Gaps

```python
# GAP 1 - MD-3097 (State Persistence)
# team_execution_v2.py:1016
# contract_manager will need StateManager - for now skip it

# GAP 2 - MD-3098 (Linting)
# grep -r "pylint|flake8|ruff" src/maestro_hive/teams
# Result: No matches found

# GAP 4 - MD-3099 (Token Budget)
# grep -r "_check_token_budget(" src/
# Result: Only definition at line 209, NO CALLS
```

### Updated Dependency Chain

```
MD-3097 (State Persistence) ──► MD-3091 (Foundation)
                                      │
                                      ├──► MD-3098 (Linting) ──► MD-3092 (JIT)
                                      │
                                      ├──► MD-3096 (Prompt Injection) ──► MD-3093 (Shift-Left)
                                      │
                                      └──► MD-3099 (Token Budget) ──► MD-3094 (Token Efficiency)
```
