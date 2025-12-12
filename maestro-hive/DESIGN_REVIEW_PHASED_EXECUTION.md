# Design Document: Phased Execution & Rerunnability

## 1. Executive Summary
This document outlines the design for enabling **Phased Execution** and **Rerunnability** in the Maestro Hive platform. The goal is to allow workflows to be executed phase-by-phase (e.g., Requirements -> Design -> Implementation), paused, resumed after failure, or started from an intermediate phase using external inputs.

## 2. Current State Analysis

### 2.1 Available Components
1.  **`TeamExecutionEngineV2`**: The current monolithic execution engine. It runs end-to-end but lacks native checkpointing or resume capabilities.
2.  **`TeamExecutionEngineV2SplitMode`**: A specialized engine (recently restored from deprecated code) designed for phased execution. It supports:
    *   `execute_phase()`: Running a single phase.
    *   `execute_batch()`: Running all phases sequentially.
    *   `execute_mixed()`: Hybrid execution.
    *   **Checkpointing**: Uses `TeamExecutionContext` to save state to JSON.
3.  **`TeamExecutionContext`**: A robust state management class that wraps `WorkflowContext` and adds checkpoint metadata (version, timestamp, phase status).
4.  **`resume_failed_workflow.py`**: A script that attempts to resume workflows by checking their status and restarting from the failed phase.

### 2.2 Identified Gaps
1.  **Integration**: The `SplitMode` engine is not the default. The main `automated_workflow.service` and `dag_api_server` likely use the monolithic V2 engine.
2.  **Networking Resilience**: The current V2 engine does not save state frequently enough. If a network failure occurs, the in-memory state is lost.
3.  **Partial Execution**: While `SplitMode` supports `execute_phase`, there is no clear API or CLI to "start from Design phase with these inputs". The inputs are expected to be in a previous checkpoint.
4.  **External Inputs**: The system assumes all context comes from the previous phase. It needs a way to inject external context (e.g., "Here is the Design, just do Implementation").

## 3. Proposed Design

### 3.1 Architecture: The "Split Mode" Standard
We will promote `TeamExecutionEngineV2SplitMode` to be the primary execution driver for complex workflows.

**Key Concepts:**
*   **Session Persistence**: Every workflow run creates a `session_id` and a corresponding directory in `maestro_workflows.db` (or filesystem).
*   **Phase Boundaries**: Execution is broken into discrete phases: `requirements`, `design`, `implementation`, `testing`, `deployment`.
*   **Checkpoints**: At the end of *every* phase, a `checkpoint_{phase}.json` is written.
*   **Resumption**: To resume, the engine looks for the latest valid checkpoint and loads the `TeamExecutionContext` from it.

### 3.2 Rerunnability Logic
When a job fails (e.g., network error in `implementation`):
1.  User/System triggers "Resume `session_123`".
2.  Engine loads `checkpoint_design.json` (last successful phase).
3.  Engine hydrates `TeamExecutionContext`.
4.  Engine calls `execute_phase("implementation")`.

### 3.3 Partial Execution (The "Start-From-X" Feature)
To support "Run Development Phase only" with external inputs:
1.  **Input Normalization**: Create a utility to convert external inputs (e.g., a Design Doc PDF or text) into a synthetic `checkpoint_design.json`.
2.  **Synthetic Context**: The engine loads this synthetic checkpoint as if it had run the previous phases itself.
3.  **Execution**: The engine proceeds with `execute_phase("implementation")`.

### 3.4 API Design
We will expose these capabilities via `workflow_api_v2.py`:

```python
POST /api/workflow/start
{
  "requirement": "...",
  "mode": "phased" | "monolithic",
  "phases": ["requirements", "design"] // Optional: run only these
}

POST /api/workflow/{id}/resume
{
  "from_phase": "auto" // or specific phase
}

POST /api/workflow/inject_context
{
  "phase": "design",
  "data": { ... } // External design data
}
```

## 4. Internal Review & Validation

### 4.1 Review Points
*   **State Consistency**: Does `TeamExecutionContext` capture *everything* needed for the next phase? (e.g., are `contracts` saved? are `blueprints` saved?)
    *   *Verification*: `TeamExecutionContext` has fields for `contracts` and `blueprint_recommendation`.
*   **Concurrency**: If we run phases in parallel (e.g., testing), how is state merged?
    *   *Answer*: `SplitMode` currently seems sequential between phases, but parallel within a phase (via `TeamExecutionEngineV2`). Merging parallel phase branches (e.g. if we split Design into Backend/Frontend design) would require a "Merge" phase.
*   **Error Handling**: What if the checkpoint is corrupted?
    *   *Mitigation*: Checkpoint validation logic exists in `validate_checkpoint_file`.

### 4.2 Implementation Roadmap
1.  **Phase 1: Stabilization**: Ensure `TeamExecutionEngineV2SplitMode` works correctly with the current codebase (imports, dependencies).
2.  **Phase 2: Resumption**: Update `resume_failed_workflow.py` to use the `SplitMode` engine for true state hydration.
3.  **Phase 3: API Exposure**: Update the API server to support phased commands.
4.  **Phase 4: External Injection**: Build the "Synthetic Checkpoint" generator.

---

## 5. Technical Review & Recommendations

### 5.1 Code Quality Assessment

**Strengths Identified:**

| Component | Rating | Notes |
|-----------|--------|-------|
| `TeamExecutionEngineV2SplitMode` | ⭐⭐⭐⭐ | Well-architected with circuit breaker, rich context passing, and multiple execution modes |
| `TeamExecutionContext` | ⭐⭐⭐⭐ | Comprehensive state management with proper serialization and RAG integration |
| `PhaseCircuitBreaker` | ⭐⭐⭐⭐ | Good resilience pattern, prevents cascading failures |
| Checkpoint Validation | ⭐⭐⭐ | Basic validation exists but could be more robust |
| `resume_failed_workflow.py` | ⭐⭐ | Placeholder only - **NOT integrated with Split Mode** |

**Code Observations:**

1. **Rich Context Passing (Fixed)**: The `_extract_phase_requirement()` method correctly passes FULL context (not truncated) between phases including:
   - All previous phase outputs as JSON
   - Artifact paths and content
   - Instructions passed forward
   - Phase-specific objectives

2. **Contract Collection**: `_collect_previous_contracts()` accumulates contracts across phases for lifecycle tracking.

3. **Progress Callbacks**: Async callbacks support real-time event streaming (`phase_started`, `blueprint_selected`, `phase_completed`, etc.).

---

### 5.2 Gap Analysis (Detailed)

| Gap ID | Description | Severity | Impact |
|--------|-------------|----------|--------|
| G-001 | `resume_failed_workflow.py` does not use `SplitMode` engine | 🔴 HIGH | Resume attempts fail to hydrate context properly |
| G-002 | No `/api/workflow/{id}/resume` endpoint implemented | 🔴 HIGH | Cannot resume via API (noted in script comments) |
| G-003 | Synthetic checkpoint generation missing | 🟡 MEDIUM | Cannot start mid-workflow with external data |
| G-004 | Hardcoded SDLC phases in both scripts | 🟡 MEDIUM | Phase mismatch risk (e.g., `backend_development` vs `implementation`) |
| G-005 | Checkpoint directory not configurable via API | 🟢 LOW | Operational inconvenience |
| G-006 | No checkpoint rotation/cleanup mechanism | 🟢 LOW | Disk space accumulation over time |

**Critical Finding - Phase Name Mismatch:**
```
SplitMode SDLC_PHASES = ["requirements", "design", "implementation", "testing", "deployment"]
resume_failed SDLC_PHASES = ["requirements", "design", "backend_development", "frontend_development", "testing", "review"]
```
This inconsistency will cause resume failures if checkpoints are created by one system and read by another.

---

### 5.3 Recommendations

#### Immediate Actions (Phase 1)

1. **Unify Phase Names**
   - Standardize on SplitMode's phase names OR create a mapping layer
   - Update `resume_failed_workflow.py` to use centralized phase definitions

2. **Wire Resume Script to SplitMode**
   ```python
   # Replace HTTP-based resume with direct engine call:
   async def resume_workflow(self, checkpoint_path: str):
       engine = TeamExecutionEngineV2SplitMode()
       await engine.initialize_contract_manager()
       context = await engine.resume_from_checkpoint(checkpoint_path)
       return context
   ```

3. **Implement Missing API Endpoint**
   ```python
   # In workflow_api_v2.py:
   @router.post("/api/workflow/{workflow_id}/resume")
   async def resume_workflow(workflow_id: str, body: ResumeRequest):
       checkpoint_path = find_latest_checkpoint(workflow_id)
       engine = TeamExecutionEngineV2SplitMode()
       context = await engine.resume_from_checkpoint(checkpoint_path, body.human_edits)
       return {"resumed": True, "next_phase": context.checkpoint_metadata.awaiting_phase}
   ```

#### Medium-Term Actions (Phase 2)

4. **Synthetic Checkpoint Generator**
   ```python
   class SyntheticCheckpointBuilder:
       """Generate checkpoint from external data (e.g., Design Doc PDF)"""

       def inject_design_phase(self, design_data: Dict[str, Any]) -> TeamExecutionContext:
           context = TeamExecutionContext.create_new(...)
           # Populate design phase outputs
           context.workflow.phase_results["design"] = PhaseResult(
               phase_name="design",
               status=PhaseStatus.COMPLETED,
               outputs=design_data,
               ...
           )
           return context
   ```

5. **Checkpoint Rotation Policy**
   - Keep last N checkpoints per workflow (configurable)
   - Archive older checkpoints to S3/GCS

#### Architectural Recommendations

6. **Single Source of Truth for Phases**
   Create `src/maestro_hive/config/phases.py`:
   ```python
   SDLC_PHASES = ["requirements", "design", "implementation", "testing", "deployment"]
   PHASE_ALIASES = {"backend_development": "implementation", "frontend_development": "implementation"}
   ```

7. **Checkpoint Storage Abstraction**
   - Current: Filesystem-based
   - Recommended: Abstract interface supporting:
     - Local filesystem (dev)
     - Redis (fast access, TTL support)
     - S3 (long-term storage)

---

### 5.4 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Resume fails due to phase mismatch | HIGH | HIGH | Unify phase names immediately |
| State lost on network failure | MEDIUM | HIGH | SplitMode already saves after each phase |
| Checkpoint corruption | LOW | HIGH | Existing validation is adequate |
| Disk exhaustion from checkpoints | LOW | MEDIUM | Implement rotation policy |

---

### 5.5 Validation Checklist

Before declaring Phase 1 complete:

- [ ] `SplitMode` is invocable from CLI with `--resume` flag
- [ ] `resume_failed_workflow.py` uses `SplitMode.resume_from_checkpoint()`
- [ ] Phase names are consistent across all files
- [ ] `/api/workflow/{id}/resume` endpoint returns HTTP 200 with valid checkpoint
- [ ] Integration test: Create checkpoint → Kill process → Resume → Complete workflow

---

### 5.6 Reviewer Sign-Off

**Review Date:** 2025-12-11
**Reviewer:** Claude Code (Opus 4.5)
**Status:** ✅ APPROVED WITH CONDITIONS

**Summary:**
The design is sound and the existing `TeamExecutionEngineV2SplitMode` implementation is more complete than the document suggests. The primary gap is **integration** - the pieces exist but are not wired together. The `resume_failed_workflow.py` script is a placeholder that needs to be connected to the Split Mode engine.

**Conditions for Approval:**
1. Fix the phase name mismatch before any resume functionality is exposed
2. Implement the `/resume` API endpoint using the existing `engine.resume_from_checkpoint()` method
3. Add integration tests validating the full checkpoint → resume cycle

---

### 5.7 Feature Parity Analysis: V2 vs SplitMode

**Question:** Will we lose any critical functionality from `TeamExecutionEngineV2` by adopting `SplitMode` as the default?

**Answer:** ✅ **NO.** SplitMode is a superset that wraps V2 internally.

#### Architecture Relationship

```python
# From team_execution_v2_split_mode.py line 215:
self.engine = TeamExecutionEngineV2(output_dir=self.output_dir)
```

SplitMode calls `V2.execute()` internally for each phase execution, preserving all V2 capabilities.

#### Features Preserved (via underlying V2 engine)

| Feature | Module | Status |
|---------|--------|--------|
| RAG Template Recommendations | `TemplateRAGClient` | ✅ Preserved |
| AI Requirement Analysis | `TeamComposerAgent` | ✅ Preserved |
| Blueprint Selection | `BlueprintScorer` | ✅ Preserved |
| Contract Design | `ContractDesignerAgent` | ✅ Preserved |
| Quality Fabric (TaaS) | `QualityFabricClient` | ✅ Preserved |
| Trimodal Validation | DDE + BDV + ACC | ✅ Preserved |
| Verdict Aggregation | `VerdictAggregator` | ✅ Preserved |
| Event Bus | MD-3125 | ✅ Preserved |
| Enforcer/Governance | MD-3123 | ✅ Preserved |
| Parallel Execution | `ParallelCoordinatorV2` | ✅ Preserved |
| Claude SDK Integration | `ClaudeCLIClient` | ✅ Preserved |
| Session Management | `SessionManager` | ✅ Preserved |

#### Features NOT Directly Exposed (Require Wrapper)

| Feature | Impact | Recommended Action |
|---------|--------|-------------------|
| `execute_jira_task()` | 🟡 MEDIUM | Add wrapper method to SplitMode |

**Recommended Addition to SplitMode:**
```python
async def execute_jira_task(
    self,
    task_key: str,
    constraints: Optional[Dict[str, Any]] = None,
    update_jira: bool = True,
    create_checkpoints: bool = True
) -> TeamExecutionContext:
    """Wrapper for JIRA task execution in phased mode."""
    from jira_task_adapter import JiraTaskAdapter
    adapter = JiraTaskAdapter()
    requirement = await adapter.task_to_requirement(task_key)

    if update_jira:
        await adapter.update_task_status(task_key, 'inProgress')

    context = await self.execute_batch(
        requirement=requirement,
        create_checkpoints=create_checkpoints
    )

    if update_jira and context.checkpoint_metadata.quality_gate_passed:
        await adapter.update_task_status(task_key, 'done')

    return context
```

#### Features ONLY in SplitMode (Gained by Adoption)

| Feature | Description |
|---------|-------------|
| Phase-by-phase execution | `execute_phase()` for granular control |
| Checkpoint persistence | JSON state files after each phase |
| Resume from failure | `resume_from_checkpoint()` with context hydration |
| Mixed execution mode | Selective checkpoints at specific phases |
| Phase Circuit Breaker | Prevents cascading failures across phases |
| Human-in-the-loop | `awaiting_human_review` flag for approval gates |
| Rich context passing | Full outputs passed between phases (not truncated) |
| Progress callbacks | Async event streaming for UI integration |

#### Potential Redundancy to Address

| Issue | Description | Resolution |
|-------|-------------|------------|
| Dual Event Systems | V2 uses `EventBus`, SplitMode uses `progress_callback` | Unify: Use EventBus internally, expose via callback |
| ID Mismatch | V2 uses `session_id`, SplitMode uses `workflow_id` | Synchronize: Pass workflow_id to V2 as session_id |

#### Verdict

| Criteria | Assessment |
|----------|------------|
| Critical functionality lost? | ❌ NO |
| All integrations preserved? | ✅ YES |
| New capabilities gained? | ✅ YES (checkpointing, resume, phased execution) |
| Migration risk | 🟢 LOW |

**Recommendation:** Proceed with SplitMode as the default execution engine. Add the `execute_jira_task()` wrapper before deployment.

---

## 6. Conclusion

The `TeamExecutionEngineV2SplitMode` provides the necessary foundation. The immediate work is to integrate it as the standard runner and expose its capabilities to the API and CLI. The code review confirms the architecture is sound; the gaps are primarily in wiring and standardization, not in core functionality.

**Key Finding:** Adopting SplitMode as the default will **not** result in any loss of critical functionality. SplitMode wraps `TeamExecutionEngineV2` internally, preserving all existing capabilities (RAG, Quality Fabric, Trimodal Validation, Governance, etc.) while adding checkpointing and resume capabilities.
