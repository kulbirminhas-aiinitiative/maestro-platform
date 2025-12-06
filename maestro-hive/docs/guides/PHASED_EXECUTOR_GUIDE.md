# Phased Autonomous SDLC Executor - Complete Guide

## Overview

The Phased Autonomous SDLC Executor is a revolutionary system that addresses critical workflow management needs:

1. **Phase-based execution** with clear boundaries
2. **Entry and exit gates** for early failure detection
3. **Progressive quality thresholds** that increase with iterations
4. **Intelligent rework** with minimal persona re-execution
5. **Dynamic team composition** based on phase and iteration

## Key Innovations

### 1. Phased Execution with Gates

Each SDLC phase has:
- **Entry Gate**: Validates dependencies before execution
- **Execution**: Runs selected personas
- **Exit Gate**: Validates outputs and quality

```
┌─────────────────────────────────────┐
│ Phase: Requirements                 │
│                                     │
│  Entry Gate ✓                       │
│      ↓                              │
│  Execute Personas                   │
│      ↓                              │
│  Exit Gate ✓/✗                      │
│                                     │
│  ✓ Pass → Next Phase                │
│  ✗ Fail → Rework                    │
└─────────────────────────────────────┘
```

### 2. Progressive Quality Management

Quality thresholds increase with each iteration:

| Iteration | Completeness | Quality Score | Coverage |
|-----------|--------------|---------------|----------|
| 1         | 60%          | 0.60          | 50%      |
| 2         | 75%          | 0.75          | 70%      |
| 3         | 85%          | 0.85          | 85%      |
| 4+        | 90%          | 0.90          | 90%      |

**Key Rule**: Iteration N+1 must score **higher** than iteration N (minimum +5%)

### 3. Early Failure Detection

Entry gates prevent divergence by checking:
- Previous phase completion
- Required artifacts exist
- Dependency satisfaction
- Quality baseline met

**Benefit**: Fail fast at phase boundaries instead of discovering issues late

### 4. Smart Rework

Instead of re-running entire phases:
- Identify specific failed personas
- Re-execute only what's needed
- Preserve successful work
- Minimize cost and time

### 5. Dynamic Team Composition

Personas adapt to phase and iteration:

**Iteration 1**:
- Required personas only (minimal team)

**Iteration 2+**:
- Required + Optional personas (enhanced team)
- Add specialists based on issues

**Rework**:
- Required + Failed personas only (targeted fix)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                 Phased Autonomous Executor                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Checkpoint │  │ Phase Gate   │  │ Progressive        │  │
│  │ Manager    │  │ Validator    │  │ Quality Manager    │  │
│  └────────────┘  └──────────────┘  └────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Phase Execution Loop                    │  │
│  │                                                      │  │
│  │  For each Phase (Requirements → Deployment):        │  │
│  │    1. Load checkpoint                               │  │
│  │    2. Run entry gate                                │  │
│  │    3. Select personas (adaptive)                    │  │
│  │    4. Execute personas                              │  │
│  │    5. Run exit gate                                 │  │
│  │    6. If failed: rework (up to max iterations)      │  │
│  │    7. If passed: save checkpoint → next phase       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Validation & Remediation                │  │
│  │                                                      │  │
│  │  For existing projects:                             │  │
│  │    1. Run comprehensive validation                  │  │
│  │    2. Identify gaps and issues                      │  │
│  │    3. Build remediation plan                        │  │
│  │    4. Execute targeted fixes                        │  │
│  │    5. Re-validate and report                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Usage Examples

### 1. Fresh Project Execution

Create a new project with full phased workflow:

```bash
python3 phased_autonomous_executor.py \
    --requirement "Create task management system with real-time collaboration" \
    --session task_mgmt_v1 \
    --max-phase-iterations 3 \
    --max-global-iterations 10
```

**What happens**:
1. Starts with Requirements phase (iteration 1)
2. Runs requirement_analyst persona
3. Validates outputs via exit gate
4. If passed: moves to Design phase
5. If failed: reworks Requirements (iteration 2 with higher thresholds)
6. Continues through all phases
7. Saves checkpoint after each phase

### 2. Resume from Checkpoint

Continue a paused or failed execution:

```bash
python3 phased_autonomous_executor.py \
    --resume task_mgmt_v1
```

**What happens**:
1. Loads checkpoint from `sdlc_sessions/checkpoints/task_mgmt_v1_checkpoint.json`
2. Resumes from last incomplete phase
3. Continues with previous iteration count
4. Preserves quality thresholds and best scores

### 3. Validate Existing Project (Sunday.com)

Validate the sunday_com project and identify issues:

```bash
# Quick validation only
./validate_sunday_com.sh

# Or use the main script
python3 phased_autonomous_executor.py \
    --validate sunday_com/sunday_com \
    --session sunday_validation
```

**What happens**:
1. Scans all project artifacts
2. Validates each phase (Requirements → Deployment)
3. Generates comprehensive report
4. Identifies gaps and issues
5. Calculates overall quality score

### 4. Remediate Existing Project

Fix issues in sunday_com:

```bash
# Validate and remediate
./validate_sunday_com.sh --remediate

# Or use the main script
python3 phased_autonomous_executor.py \
    --validate sunday_com/sunday_com \
    --session sunday_remediation \
    --remediate
```

**What happens**:
1. Runs validation (as above)
2. Builds remediation plan:
   - Maps issues to phases
   - Identifies personas to re-run
   - Creates targeted execution plan
3. Executes remediation:
   - Re-runs only failed personas
   - Fixes identified issues
   - Preserves working components
4. Re-validates:
   - Confirms improvements
   - Reports before/after scores
   - Shows quality delta

## Workflow Phases

### Phase 1: Requirements

**Purpose**: Define what to build

**Entry Gate Checks**:
- None (first phase)

**Personas Executed**:
- Iteration 1: `requirement_analyst`
- Iteration 2+: `requirement_analyst` (with higher standards)

**Exit Gate Checks**:
- ✓ Requirements document exists
- ✓ User stories defined
- ✓ Acceptance criteria clear
- ✓ Quality score ≥ threshold

**Deliverables**:
- `requirements_document.md`
- `user_stories.md`
- `acceptance_criteria.md`
- `requirement_backlog.md`

### Phase 2: Design

**Purpose**: Design the solution architecture

**Entry Gate Checks**:
- ✓ Phase 1 completed
- ✓ Requirements document exists
- ✓ Requirements quality ≥ 70%

**Personas Executed**:
- Iteration 1: `solution_architect`, `database_specialist`
- Iteration 2+: Add `security_specialist`

**Exit Gate Checks**:
- ✓ Architecture document exists
- ✓ Database design complete
- ✓ API specifications defined
- ✓ Tech stack documented
- ✓ Quality score ≥ threshold (progressive)

**Deliverables**:
- `architecture_document.md`
- `system_design.md`
- `database_design.md`
- `api_specifications.md`
- `tech_stack.md`

### Phase 3: Implementation

**Purpose**: Build the system

**Entry Gate Checks**:
- ✓ Phase 2 completed
- ✓ Architecture document exists
- ✓ Design quality ≥ 75%

**Personas Executed**:
- Iteration 1: `backend_developer`, `frontend_developer`
- Iteration 2+: Add `database_specialist` if DB issues
- Rework: Only failed personas

**Exit Gate Checks**:
- ✓ Backend code exists
- ✓ Frontend code exists
- ✓ No critical placeholders
- ✓ No commented-out routes
- ✓ Quality score ≥ threshold (progressive)
- ✓ Code quality metrics pass

**Deliverables**:
- Backend: `backend/src/**/*.ts`
- Frontend: `frontend/src/**/*.tsx`
- Tests: `**/*.test.ts`
- Configuration files

### Phase 4: Testing & QA

**Purpose**: Validate implementation quality

**Entry Gate Checks**:
- ✓ Phase 3 completed
- ✓ Backend code exists
- ✓ Frontend code exists
- ✓ Implementation quality ≥ 80%

**Personas Executed**:
- Iteration 1: `qa_engineer`, `unit_tester`
- Iteration 2+: Add `integration_tester`

**Exit Gate Checks**:
- ✓ Test plan exists
- ✓ Test coverage ≥ threshold
- ✓ Completeness report exists
- ✓ Critical bugs ≤ 0
- ✓ Quality score ≥ threshold (progressive)

**Deliverables**:
- `test_plan.md`
- `completeness_report.md` ← **Critical**
- `test_results.md`
- Test code: `**/*.test.ts`

### Phase 5: Deployment

**Purpose**: Prepare for production

**Entry Gate Checks**:
- ✓ Phase 4 completed
- ✓ Test coverage ≥ 80%
- ✓ Critical bugs = 0
- ✓ QA approved

**Personas Executed**:
- Iteration 1: `devops_engineer`, `deployment_integration_tester`
- Iteration 2+: Add `project_reviewer`

**Exit Gate Checks**:
- ✓ Deployment guide exists
- ✓ Docker config complete
- ✓ CI/CD pipeline configured
- ✓ Smoke tests pass
- ✓ Deployment readiness report ← **Critical**
- ✓ Quality score ≥ 90%

**Deliverables**:
- `deployment_guide.md`
- `deployment_readiness_report.md`
- `Dockerfile`, `docker-compose.yml`
- `.github/workflows/*.yml`

## Quality Gate Criteria

### Entry Gate (Before Phase Execution)

Validates preconditions:

```python
Entry Gate Checks:
1. Previous phase completed? (state = COMPLETED)
2. Previous phase quality ≥ minimum threshold?
3. Required artifacts from previous phase exist?
4. No blocking dependencies?

Result: PASS → Execute phase
        FAIL → BLOCKED (cannot start)
```

### Exit Gate (After Phase Execution)

Validates outputs:

```python
Exit Gate Checks:
1. All required deliverables created?
2. Quality score ≥ threshold (progressive)?
3. Completeness ≥ threshold?
4. No critical issues?
5. Improvement over previous iteration? (if iteration > 1)

Result: PASS → Next phase
        FAIL → NEEDS_REWORK (retry current phase)
```

## Progressive Quality Thresholds

Managed by `ProgressiveQualityManager`:

```python
class QualityThresholds:
    completeness: float  # 0.0-1.0 (deliverables created)
    quality: float       # 0.0-1.0 (quality score)
    coverage: float      # 0.0-1.0 (test coverage, testing phase)
```

**Iteration Progression**:

```python
Iteration 1:
    Completeness: 60%
    Quality: 0.60
    Coverage: 50%
    Rationale: "Initial implementation, focus on breadth"

Iteration 2:
    Completeness: 75%
    Quality: 0.75
    Coverage: 70%
    Rationale: "First refinement, fill gaps"

Iteration 3:
    Completeness: 85%
    Quality: 0.85
    Coverage: 85%
    Rationale: "Polish and complete"

Iteration 4+:
    Completeness: 90%
    Quality: 0.90
    Coverage: 90%
    Rationale: "Production-ready standards"
```

**Improvement Rule**:

If iteration N achieves quality score of 0.82, then iteration N+1 requires:
```
minimum_quality = max(
    baseline_for_iteration[N+1],  # e.g., 0.85
    previous_best + 0.05           # e.g., 0.82 + 0.05 = 0.87
)
```

This ensures **continuous improvement**.

## Checkpoint System

Enables resumable execution:

**Checkpoint Data**:
```json
{
  "session_id": "task_mgmt_v1",
  "current_phase": "implementation",
  "phase_iteration": 2,
  "global_iteration": 5,
  "completed_phases": ["requirements", "design"],
  "phase_executions": [...],
  "best_quality_scores": {
    "requirements": 0.92,
    "design": 0.88
  },
  "created_at": "2024-01-15T10:30:00",
  "last_updated": "2024-01-15T14:45:00"
}
```

**Saved to**: `sdlc_sessions/checkpoints/{session_id}_checkpoint.json`

**Auto-saved**:
- After each phase completion
- After each phase failure (for retry)
- On exit (graceful shutdown)

## Remediation Workflow

For existing projects (like sunday_com):

### Step 1: Validation

```bash
python3 phased_autonomous_executor.py \
    --validate sunday_com/sunday_com \
    --session sunday_validation
```

**Output**:
```
🔍 VALIDATION & REMEDIATION
═══════════════════════════
📁 Project: sunday_com/sunday_com

📊 Validation Results:
   Overall Score: 0.68
   Issues Found: 23
   Critical Issues: 5

Phase Scores:
   Requirements: 0.85 ✓
   Design: 0.78 ✓
   Implementation: 0.52 ✗
   Testing: 0.45 ✗
   Deployment: 0.60 ⚠️
```

### Step 2: Remediation Plan

System automatically builds plan:

```
📋 Remediation Plan:
   implementation: backend_developer, frontend_developer
   testing: qa_engineer
   deployment: deployment_integration_tester
```

### Step 3: Execution

Re-runs only failed personas:

```
🔧 Remediating implementation:
   - backend_developer (fixing commented routes)
   - frontend_developer (replacing stubs)

🔧 Remediating testing:
   - qa_engineer (creating completeness report)
```

### Step 4: Re-validation

```
📊 Final Validation:
   Score improved: 0.68 → 0.89
   ✅ Remediation successful! (+21%)
```

## Configuration

### Phase Persona Mappings

Customize which personas run in each phase:

```python
custom_mappings = [
    PhasePersonaMapping(
        phase=SDLCPhase.REQUIREMENTS,
        required_personas=["requirement_analyst", "product_manager"],
        optional_personas=["business_analyst"],
        rework_personas=["requirement_analyst"]
    ),
    # ... more mappings
]

executor = PhasedAutonomousExecutor(
    session_id="my_session",
    requirement="...",
    phase_mappings=custom_mappings
)
```

### Quality Thresholds

Override default progressive thresholds:

```python
from progressive_quality_manager import ProgressiveQualityManager

quality_mgr = ProgressiveQualityManager(
    base_completeness=0.70,  # Start at 70% instead of 60%
    base_quality=0.70,
    base_coverage=0.60
)

executor.quality_manager = quality_mgr
```

### Iteration Limits

Control retry behavior:

```python
executor = PhasedAutonomousExecutor(
    session_id="my_session",
    requirement="...",
    max_phase_iterations=5,    # Retry phase up to 5 times
    max_global_iterations=20   # Total iterations across all phases
)
```

## Monitoring & Debugging

### Logs

Detailed logs saved to:
- `phased_autonomous_YYYYMMDD_HHMMSS.log`
- stdout (real-time)

**Log Levels**:
- INFO: Normal execution flow
- WARNING: Non-critical issues
- ERROR: Critical failures

### Checkpoint Files

Inspect execution state:

```bash
cat sdlc_sessions/checkpoints/task_mgmt_v1_checkpoint.json | jq
```

### Validation Reports

Per-phase validation:

```bash
cat sunday_com/sunday_com/validation_reports/summary.json | jq
```

## Best Practices

### 1. Start with Clear Requirements

Ensure the requirement is well-defined:
```bash
--requirement "Create task management system with:
- Real-time collaboration
- Role-based access control
- Kanban and Gantt views
- REST API
- React frontend"
```

### 2. Use Reasonable Iteration Limits

Don't over-iterate:
- `max_phase_iterations`: 3-5 (per phase)
- `max_global_iterations`: 10-15 (total)

### 3. Enable Progressive Quality

Always enable (default):
```bash
# Good
python3 phased_autonomous_executor.py ...

# Not recommended
python3 phased_autonomous_executor.py --disable-progressive-quality ...
```

### 4. Validate Before Deploy

Always validate sunday_com or any project before deployment:
```bash
./validate_sunday_com.sh
```

### 5. Review Checkpoint After Each Session

Check quality scores:
```bash
jq '.best_quality_scores' sdlc_sessions/checkpoints/SESSIONID_checkpoint.json
```

## Troubleshooting

### Issue: Phase Stuck in NEEDS_REWORK

**Symptom**: Phase keeps failing exit gate

**Solution**:
1. Check exit gate failures:
   ```bash
   tail -n 100 phased_autonomous_*.log | grep "Exit gate FAILED"
   ```
2. Review validation reports:
   ```bash
   cat OUTPUT_DIR/validation_reports/summary.json
   ```
3. Identify missing deliverables or quality issues
4. Manually fix critical issues
5. Resume execution:
   ```bash
   python3 phased_autonomous_executor.py --resume SESSION_ID
   ```

### Issue: Entry Gate Blocked

**Symptom**: Cannot start phase

**Solution**:
1. Check previous phase completion:
   ```bash
   jq '.completed_phases' sdlc_sessions/checkpoints/SESSIONID_checkpoint.json
   ```
2. Verify previous phase quality:
   ```bash
   jq '.best_quality_scores' sdlc_sessions/checkpoints/SESSIONID_checkpoint.json
   ```
3. If previous phase quality too low, re-run it:
   ```python
   # Reset checkpoint to previous phase
   # Edit checkpoint.json manually or restart from scratch
   ```

### Issue: Personas Not Executing

**Symptom**: Personas selected but not running

**Solution**:
1. Check team_execution.py integration:
   ```bash
   python3 team_execution.py backend_developer --session test --requirement "test"
   ```
2. Verify Claude CLI available:
   ```bash
   which claude
   ```
3. Check logs for subprocess errors:
   ```bash
   grep "Persona execution failed" phased_autonomous_*.log
   ```

## Integration with Existing Systems

### With team_execution.py

The phased executor calls `team_execution.py` for persona execution:

```python
cmd = [
    "python3", "team_execution.py",
    *personas,
    "--session", session_id,
    "--output", output_dir,
    "--requirement", requirement,
    "--phase", phase.value,
    "--iteration", str(iteration)
]
```

### With Quality Fabric

Future integration (placeholder in code):

```python
# In _run_quality_gate
quality_result = await quality_fabric_client.validate(
    artifacts=persona_artifacts,
    phase=phase,
    thresholds=thresholds
)
```

### With Maestro ML (RAG/Reuse)

For persona-level reuse:

```python
# In execute_personas
reuse_client = PersonaReuseClient(maestro_ml_url)
similar_artifacts = await reuse_client.fetch_persona_artifacts(
    source_project_id=...,
    persona_id=persona_id
)
```

## Command Reference

### Fresh Execution

```bash
python3 phased_autonomous_executor.py \
    --requirement "PROJECT_DESCRIPTION" \
    --session SESSION_ID \
    [--output OUTPUT_DIR] \
    [--max-phase-iterations N] \
    [--max-global-iterations M] \
    [--disable-progressive-quality]
```

### Resume Execution

```bash
python3 phased_autonomous_executor.py \
    --resume SESSION_ID
```

### Validate Project

```bash
python3 phased_autonomous_executor.py \
    --validate PROJECT_DIR \
    --session SESSION_ID
```

### Validate & Remediate

```bash
python3 phased_autonomous_executor.py \
    --validate PROJECT_DIR \
    --session SESSION_ID \
    --remediate
```

### Sunday.com Quick Scripts

```bash
# Just validate
./validate_sunday_com.sh

# Validate and fix
./validate_sunday_com.sh --remediate
```

## FAQ

**Q: What if a phase fails after max iterations?**

A: The phase is marked as FAILED, execution stops, and you get a detailed failure report. You can:
- Manually fix critical issues
- Resume with `--resume SESSION_ID`
- Or restart with adjusted requirements

**Q: How do I know what went wrong?**

A: Check:
1. Logs: `phased_autonomous_*.log`
2. Validation reports: `OUTPUT_DIR/validation_reports/`
3. Checkpoint: `sdlc_sessions/checkpoints/SESSION_ID_checkpoint.json`

**Q: Can I customize phase mappings?**

A: Yes, modify `DEFAULT_PHASE_MAPPINGS` in the code or pass `phase_mappings` to constructor.

**Q: How does progressive quality work?**

A: Each iteration has higher thresholds. Iteration N+1 must improve over N by at least 5%.

**Q: Can I use this for non-software projects?**

A: Yes! Customize phases and personas for your domain (e.g., content creation, research, etc.)

---

## Conclusion

The Phased Autonomous SDLC Executor provides a complete solution for:

✅ **Phased execution** with clear boundaries
✅ **Early failure detection** via gates
✅ **Progressive quality** enforcement
✅ **Smart rework** with minimal re-execution
✅ **Dynamic teams** adapted to context
✅ **Resumable workflows** via checkpoints
✅ **Validation & remediation** for existing projects

Use it to build new projects or fix existing ones like sunday_com with confidence and quality.
