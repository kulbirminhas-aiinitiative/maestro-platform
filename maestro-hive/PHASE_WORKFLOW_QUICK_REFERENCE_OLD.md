# Phase Workflow System - Quick Reference Guide

## Overview

The phase workflow system provides phased SDLC execution with intelligent quality gates, progressive quality thresholds, and full persistence.

---

## Key Concepts

### 1. SDLC Phases
- **REQUIREMENTS** - Requirements analysis and documentation
- **DESIGN** - Architecture and system design
- **IMPLEMENTATION** - Code development
- **TESTING** - Quality assurance and testing
- **DEPLOYMENT** - Production deployment

### 2. Phase States
- **NOT_STARTED** - Phase hasn't been executed yet
- **IN_PROGRESS** - Phase is currently executing
- **COMPLETED** - Phase passed all gates
- **FAILED** - Phase failed entry/exit gates (blocking)
- **NEEDS_REWORK** - Phase needs improvements (can retry)

### 3. Phase Gates
- **Entry Gate** - Prerequisites before phase can start
- **Exit Gate** - Quality criteria before phase can complete

### 4. Progressive Quality
Quality thresholds increase with each iteration:
- Iteration 1: 60% completeness, 0.50 quality
- Iteration 2: 70% completeness, 0.60 quality
- Iteration 3: 80% completeness, 0.70 quality
- Iteration 4: 90% completeness, 0.80 quality
- Iteration 5+: 95% completeness, 0.85 quality

---

## Usage

### Basic Usage

```python
from phase_workflow_orchestrator import PhaseWorkflowOrchestrator

# Create orchestrator
orchestrator = PhaseWorkflowOrchestrator(
    session_id="my_project_v1",
    requirement="Build an e-commerce platform with payment integration",
    output_dir=Path("./my_project"),
    enable_phase_gates=True,
    enable_progressive_quality=True
)

# Execute workflow
result = await orchestrator.execute_workflow(max_iterations=5)

# Check results
if result.success:
    print(f"✅ All phases complete!")
    print(f"Quality: {result.final_quality_score:.0%}")
    print(f"Completeness: {result.final_completeness:.0%}")
else:
    print(f"❌ Workflow incomplete")
    print(f"Phases completed: {len(result.phases_completed)}/5")
```

### Command Line

```bash
# Start new workflow
python phase_workflow_orchestrator.py \
    --session-id ecommerce_v1 \
    --requirement "Build e-commerce platform" \
    --output ./ecommerce_output \
    --max-iterations 5

# Resume existing workflow
python phase_workflow_orchestrator.py \
    --session-id ecommerce_v1 \
    --requirement "Build e-commerce platform" \
    --max-iterations 5
```

### Advanced Options

```python
# Disable phase gates (not recommended)
orchestrator = PhaseWorkflowOrchestrator(
    session_id="prototype",
    requirement="Quick prototype",
    enable_phase_gates=False  # Skip validation
)

# Target specific phases only
result = await orchestrator.execute_workflow(
    max_iterations=3,
    target_phases=[SDLCPhase.REQUIREMENTS, SDLCPhase.DESIGN]
)

# Custom quality thresholds
from progressive_quality_manager import ProgressiveQualityManager

quality_mgr = ProgressiveQualityManager(
    baseline_completeness=0.70,  # Start higher
    baseline_quality=0.60,
    increment_per_iteration=0.05  # Slower ratcheting
)
```

---

## Session Management

### Creating Sessions

```python
from session_manager import SessionManager

session_mgr = SessionManager()

# Create new session
session = session_mgr.create_session(
    requirement="Build blog platform",
    output_dir=Path("./blog_output"),
    session_id="blog_v1"
)
```

### Resuming Sessions

```python
# Load existing session
session = session_mgr.load_session("blog_v1")

if session:
    print(f"Resuming session from {session.last_updated}")
    print(f"Completed personas: {session.completed_personas}")
    
    # Restore phase history
    phase_history = session.metadata.get("phase_history", [])
    print(f"Phase executions: {len(phase_history)}")
```

### Listing Sessions

```python
# Get all sessions
sessions = session_mgr.list_sessions()

for sess in sessions:
    print(f"{sess['session_id']}: {sess['requirement']}")
    print(f"  Last updated: {sess['last_updated']}")
    print(f"  Personas: {sess['completed_personas']}")
```

---

## Phase Execution Details

### Phase Execution Flow

```
1. Entry Gate Validation
   ├─ Check prerequisite phases complete
   ├─ Check environment readiness
   └─ PASS or FAIL

2. Progressive Quality Thresholds
   ├─ Calculate thresholds for iteration
   └─ Log quality expectations

3. Persona Selection
   ├─ Select primary personas
   ├─ Add supporting personas (iteration > 1)
   └─ Add specialists (if issues exist)

4. Persona Execution
   ├─ Execute via team_execution.py
   ├─ Track reuse vs. fresh execution
   └─ Calculate quality metrics

5. Quality Regression Check (iteration > 1)
   ├─ Compare to previous iteration
   ├─ Detect regressions
   └─ Mark for rework if regressed

6. Exit Gate Validation
   ├─ Check quality thresholds met
   ├─ Validate deliverables present
   ├─ Check for critical issues
   └─ PASS, WARNING, or FAIL

7. State Determination
   ├─ COMPLETED - All gates passed
   ├─ NEEDS_REWORK - Issues detected
   └─ FAILED - Blocking issues
```

### Accessing Phase Results

```python
# Get phase history
for phase_exec in orchestrator.phase_history:
    print(f"Phase: {phase_exec.phase.value}")
    print(f"  State: {phase_exec.state.value}")
    print(f"  Iteration: {phase_exec.iteration}")
    print(f"  Quality: {phase_exec.quality_score:.0%}")
    print(f"  Completeness: {phase_exec.completeness:.0%}")
    
    if phase_exec.exit_gate_result:
        print(f"  Exit gate: {'PASSED' if phase_exec.exit_gate_result.passed else 'FAILED'}")
        if not phase_exec.exit_gate_result.passed:
            print(f"  Issues: {phase_exec.exit_gate_result.blocking_issues}")
```

---

## Quality Management

### Progressive Quality Thresholds

```python
from progressive_quality_manager import ProgressiveQualityManager

quality_mgr = ProgressiveQualityManager()

# Get thresholds for iteration
thresholds = quality_mgr.get_thresholds_for_iteration(
    phase=SDLCPhase.IMPLEMENTATION,
    iteration=3
)

print(f"Completeness threshold: {thresholds.completeness:.0%}")
print(f"Quality threshold: {thresholds.quality:.2f}")
print(f"Test coverage threshold: {thresholds.test_coverage:.0%}")
```

### Quality Regression Detection

```python
# Check for regression
regression_check = quality_mgr.check_quality_regression(
    phase=SDLCPhase.IMPLEMENTATION,
    current_metrics={
        'completeness': 0.70,
        'quality_score': 0.75,
        'test_coverage': 0.80
    },
    previous_metrics={
        'completeness': 0.85,
        'quality_score': 0.80,
        'test_coverage': 0.75
    },
    tolerance=0.05
)

if regression_check['has_regression']:
    print("⚠️ Quality regression detected!")
    for metric in regression_check['regressed_metrics']:
        print(f"  - {metric}")
    
    print("\nRecommendations:")
    for rec in regression_check['recommendations']:
        print(f"  - {rec}")
```

### Quality Trends

```python
# Analyze quality trends
trend = quality_mgr.calculate_quality_trend(
    phase_history=orchestrator.phase_history,
    metric='completeness'
)

print(f"Trend: {trend['trend']}")  # improving, declining, stable
print(f"Velocity: {trend['velocity']:+.3f}")
print(f"Latest value: {trend['latest_value']:.0%}")
print(f"Projected next: {trend['projection']:.0%}")
```

---

## Exit Criteria

### Built-in Criteria

The system recognizes these exit criteria patterns:

- **"All tests pass"** - Quality ≥ 70%, no issues
- **"Requirements complete"** - Completeness ≥ 75%
- **"Code review approved"** - Quality ≥ 70%
- **"Security review passed"** - Security persona executed, quality ≥ 75%
- **"Documentation complete"** - ≥ 3 markdown files exist
- **"Ready for deployment"** - Completeness ≥ 90%, quality ≥ 80%, coverage ≥ 70%

### Custom Criteria

Unknown criteria **fail by default** for safety:

```python
# This will FAIL (unknown criterion)
await validator._check_exit_criterion(
    "Our custom criterion that doesn't match any pattern",
    phase_exec,
    output_dir
)
# Returns: False (logged as warning)
```

To add custom criteria, extend `PhaseGateValidator`:

```python
class CustomPhaseGateValidator(PhaseGateValidator):
    async def _check_exit_criterion(self, criterion, phase_exec, output_dir):
        # Add custom check
        if "my_custom_criterion" in criterion.lower():
            return self._check_my_custom_logic(phase_exec)
        
        # Fallback to parent
        return await super()._check_exit_criterion(criterion, phase_exec, output_dir)
```

---

## Troubleshooting

### Phase Won't Start

**Symptom:** Entry gate fails

**Causes:**
- Prerequisite phases not complete
- Entry criteria not met

**Solution:**
```python
# Check prerequisite phases
for phase_exec in orchestrator.phase_history:
    if phase_exec.state != PhaseState.COMPLETED:
        print(f"⚠️ {phase_exec.phase.value} not complete")

# Check entry gate result
if phase_exec.entry_gate_result:
    print(f"Failed criteria: {phase_exec.entry_gate_result.criteria_failed}")
    print(f"Blocking issues: {phase_exec.entry_gate_result.blocking_issues}")
```

### Phase Marked for Rework

**Symptom:** Phase state is NEEDS_REWORK

**Causes:**
- Quality regression detected
- Exit gate failed
- Critical issues found

**Solution:**
```python
# Check why rework needed
if phase_exec.state == PhaseState.NEEDS_REWORK:
    print(f"Rework reason: {phase_exec.rework_reason}")
    
    # Check issues
    for issue in phase_exec.issues:
        print(f"{issue.severity}: {issue.description}")
        print(f"  Recommendation: {issue.recommendation}")
    
    # Check exit gate
    if phase_exec.exit_gate_result:
        print(f"Exit gate issues: {phase_exec.exit_gate_result.blocking_issues}")
```

### Quality Regression

**Symptom:** Phase automatically marked for rework after execution

**Cause:** Quality metrics decreased compared to previous iteration

**Solution:**
```python
# Review regression details
regression_check = quality_mgr.check_quality_regression(...)

print(f"Regressed metrics: {regression_check['regressed_metrics']}")
print(f"Recommendations: {regression_check['recommendations']}")

# Options:
# 1. Re-run phase with --force to override
# 2. Address quality issues and retry
# 3. Rollback to previous iteration if needed
```

### Personas Not Executing

**Symptom:** team_execution.py raises RuntimeError

**Causes:**
- Claude CLI not installed
- team_execution.py not in path
- Invalid personas specified

**Solution:**
```bash
# Check Claude CLI
which claude
# If not found: npm install -g @anthropic-ai/claude-cli

# Check team_execution.py
python3 -c "import team_execution"

# Verify personas
python3 -c "from personas import SDLCPersonas; print(SDLCPersonas.get_all_personas().keys())"
```

---

## Best Practices

### 1. Always Enable Phase Gates

```python
# Good
orchestrator = PhaseWorkflowOrchestrator(
    enable_phase_gates=True  # Recommended
)

# Avoid (unless rapid prototyping)
orchestrator = PhaseWorkflowOrchestrator(
    enable_phase_gates=False  # Skip validation
)
```

### 2. Use Progressive Quality

```python
# Good
orchestrator = PhaseWorkflowOrchestrator(
    enable_progressive_quality=True  # Continuous improvement
)
```

### 3. Save Progress Frequently

The system auto-saves after each phase, but you can manually trigger:

```python
orchestrator._save_progress()
```

### 4. Monitor Quality Trends

```python
# Check trends every few iterations
if orchestrator.iteration_count % 2 == 0:
    summary = quality_mgr.get_quality_summary(orchestrator.phase_history)
    print(f"Quality trend: {summary['trends']['completeness']['trend']}")
```

### 5. Handle Rework Gracefully

```python
# Don't just retry blindly
if result.success:
    deploy()
else:
    # Analyze why it failed
    for phase_exec in result.phase_history:
        if phase_exec.state == PhaseState.NEEDS_REWORK:
            print(f"Fix needed in {phase_exec.phase.value}:")
            print(f"  {phase_exec.rework_reason}")
    
    # Address issues, then retry specific phase
```

---

## Performance Considerations

### Overhead

- Phase serialization: ~10ms per phase
- Regression check: ~50ms per iteration (iteration > 1)
- Session save: ~100ms
- **Total: < 200ms per phase iteration**

### Optimization Tips

1. **Reuse personas** when possible (handled automatically)
2. **Skip optional phases** for prototypes
3. **Batch similar work** in same phase
4. **Monitor session file size** (large histories slow load)

---

## Security

### Fail-Safe Defaults

- Unknown exit criteria **fail by default**
- Missing deliverables **block progression**
- Quality regressions **force rework**

### Audit Trail

Complete history preserved:
- Which personas executed when
- What quality scores achieved
- Why phases needed rework
- Who/what approved gates

### Access Control

(Future work - currently file-system based)

---

## Migration Guide

### From V3 (Sequential Execution)

```python
# Old way (V3)
from team_execution import AutonomousSDLCEngineV3_1_Resumable

engine = AutonomousSDLCEngineV3_1_Resumable(
    selected_personas=["requirement_analyst", "backend_developer"],
    output_dir="./output"
)
result = await engine.execute(requirement="Build app")

# New way (Phase-based)
from phase_workflow_orchestrator import PhaseWorkflowOrchestrator

orchestrator = PhaseWorkflowOrchestrator(
    session_id="my_app",
    requirement="Build app",
    output_dir=Path("./output")
)
result = await orchestrator.execute_workflow()
```

**Benefits of phase-based:**
- Automatic phase management
- Progressive quality enforcement
- Better visibility into workflow state
- Intelligent rework (not full reruns)

---

## FAQ

**Q: Can I skip phases?**  
A: Not in the standard workflow (phases are sequential). For prototypes, you can target specific phases:
```python
result = await orchestrator.execute_workflow(
    target_phases=[SDLCPhase.REQUIREMENTS, SDLCPhase.IMPLEMENTATION]
)
```

**Q: How do I force re-execution of a completed phase?**  
A: Pass `force=True` to team_execution or manually change phase state to NOT_STARTED.

**Q: Can I customize quality thresholds?**  
A: Yes, create custom `ProgressiveQualityManager`:
```python
quality_mgr = ProgressiveQualityManager(
    baseline_completeness=0.70,
    baseline_quality=0.60,
    increment_per_iteration=0.05
)
```

**Q: What happens if a persona fails?**  
A: The phase is marked as NEEDS_REWORK and will be retried in the next iteration.

**Q: How many iterations before giving up?**  
A: Configurable via `max_iterations` parameter. Default is 5.

**Q: Does this work with persona reuse (V4.1)?**  
A: Yes! The phase orchestrator uses team_execution.py which includes V4.1 persona reuse.

---

## See Also

- [Gap Analysis](PHASE_WORKFLOW_GAP_ANALYSIS.md) - Detailed analysis of issues
- [Implementation Complete](PHASE_WORKFLOW_FIXES_COMPLETE.md) - What was implemented
- [Team Organization](team_organization.py) - Phase-persona mapping
- [Progressive Quality](progressive_quality_manager.py) - Quality threshold management

---

## Support

For issues, questions, or contributions:
1. Check the gap analysis for known limitations
2. Review test cases in `test_phase_workflow_fixes.py`
3. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
4. File an issue with reproduction steps
