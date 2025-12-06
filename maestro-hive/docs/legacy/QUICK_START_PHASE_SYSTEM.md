# Phase-Based SDLC Quick Start Guide

**Get started with the phase-based SDLC system in 5 minutes**

---

## Prerequisites

```bash
# Install dependencies
pip install claude_code_sdk httpx

# Verify Claude CLI is installed
which claude

# If not installed:
npm install -g @anthropic/claude
```

---

## Quick Start

### 1. Basic Project Execution

```bash
cd /path/to/claude_team_sdk/examples/sdlc_team

python phase_integrated_executor.py \
    --session my_first_project \
    --requirement "Build a blog platform with user authentication and post management" \
    --max-iterations 3
```

**What happens:**
- System runs Requirements → Design → Implementation → Testing → Deployment
- Each phase has entry/exit gates
- Quality thresholds increase per iteration (60% → 70% → 80%)
- If phase fails, system reworks that phase only
- Output in `./sdlc_output/my_first_project/`

### 2. View Results

```bash
cd ./sdlc_output/my_first_project

# Check overall quality
cat validation_reports/FINAL_QUALITY_REPORT.md

# Check specific phase
cat validation_reports/backend_developer_validation.json

# View generated code
ls -R
```

### 3. Resume a Session

```bash
# System auto-resumes from where it left off
python phase_integrated_executor.py \
    --session my_first_project \
    --requirement "Build a blog platform..." \
    --max-iterations 5

# It will:
# - Load phase history
# - Skip completed phases
# - Continue from last incomplete phase
```

---

## Understanding the Output

### Console Output

```
================================================================================
🚀 PHASE-INTEGRATED SDLC WORKFLOW
================================================================================
📝 Requirement: Build a blog platform with user authentication...
🆔 Session: my_first_project
📁 Output: ./sdlc_output/my_first_project
🎯 Target Phases: ['requirements', 'design', 'implementation', 'testing', 'deployment']
🔄 Max Iterations: 3
================================================================================

================================================================================
🔄 ITERATION 1/3
================================================================================

--------------------------------------------------------------------------------
📍 PHASE: requirements
--------------------------------------------------------------------------------

🚪 Step 1: Validating ENTRY gate for requirements...
✅ Entry gate PASSED (100%)

👥 Step 2: Selecting personas for requirements...
Selected 1 persona(s): requirement_analyst

📊 Step 3: Getting quality thresholds...
Thresholds for iteration 1: completeness=70%, quality=0.50, test_coverage=60%

🔨 Step 4: Executing personas...
🤖 requirement_analyst is working...
✅ Persona execution complete
   Completeness: 85%
   Quality: 0.72

📦 Step 5: Validating deliverables...

🚪 Step 6: Validating EXIT gate for requirements...
✅ Exit gate PASSED (90%)

✅ COMPLETED: requirements
   Completeness: 85%
   Quality: 0.72
   Personas: requirement_analyst

... continues for each phase ...
```

### Key Indicators

**✅ Phase Completed** - Met quality thresholds, proceed to next phase
```
✅ COMPLETED: implementation
   Completeness: 82%
   Quality: 0.78
```

**⚠️ Phase Needs Rework** - Didn't meet thresholds, will retry
```
⚠️  REWORK NEEDED: implementation
Exit gate validation failed
Issues found:
  - Completeness 65% < 80% required
  - 15 commented-out routes detected
```

**🚫 Phase Blocked** - Cannot start (prerequisites not met)
```
🚫 BLOCKED: Cannot start design
Entry gate validation failed
  - Requirements phase not completed
```

### File Structure

```
sdlc_output/
└── my_first_project/
    ├── REQUIREMENTS.md            ← Requirements doc
    ├── ARCHITECTURE.md            ← System design
    ├── backend/                   ← Backend code
    │   ├── src/
    │   │   ├── routes/
    │   │   ├── services/
    │   │   └── models/
    │   ├── package.json
    │   └── tsconfig.json
    ├── frontend/                  ← Frontend code
    │   ├── src/
    │   │   ├── pages/
    │   │   ├── components/
    │   │   └── services/
    │   └── package.json
    ├── tests/                     ← Test suites
    │   ├── unit/
    │   └── integration/
    ├── validation_reports/        ← Quality reports
    │   ├── summary.json
    │   ├── backend_developer_validation.json
    │   ├── frontend_developer_validation.json
    │   ├── qa_engineer_validation.json
    │   └── FINAL_QUALITY_REPORT.md
    └── sdlc_sessions/             ← Session state
        └── my_first_project.json
```

---

## Common Scenarios

### Scenario 1: Quick Prototype (Iteration 1 Only)

```bash
# Lower quality expectations
python phase_integrated_executor.py \
    --session prototype_v1 \
    --requirement "Blog platform prototype" \
    --max-iterations 1

# Iteration 1 accepts:
# - 60% completeness
# - 0.50 quality score
# Good for rapid prototyping!
```

### Scenario 2: Production-Ready (5 Iterations)

```bash
# High quality expectations
python phase_integrated_executor.py \
    --session production_blog \
    --requirement "Blog platform with enterprise features" \
    --max-iterations 5

# Iteration 5 requires:
# - 95% completeness
# - 0.90 quality score
# Perfect for production deployment!
```

### Scenario 3: Debug Failed Phase

```bash
# Run with detailed logging
python phase_integrated_executor.py \
    --session debug_project \
    --requirement "..." \
    --max-iterations 3 2>&1 | tee debug.log

# Check what failed
cat sdlc_output/debug_project/validation_reports/FINAL_QUALITY_REPORT.md

# Focus on specific persona
cat sdlc_output/debug_project/validation_reports/backend_developer_validation.json

# Common issues:
# - Commented routes → Uncomment in backend/src/routes/
# - "Coming Soon" pages → Implement in frontend/src/pages/
# - Stub functions → Complete in backend/src/services/
```

### Scenario 4: Disable Phase Gates (Testing)

```bash
# For testing/debugging only
python phase_integrated_executor.py \
    --session test_no_gates \
    --requirement "..." \
    --disable-phase-gates \
    --max-iterations 1

# Skips all validation
# Useful for testing persona execution
```

---

## Progressive Quality in Action

### How It Works

| Iteration | Requirements | Implementation | Deployment |
|-----------|-------------|----------------|------------|
| 1         | 70% OK      | 60% OK         | 70% OK     |
| 2         | 80% OK      | 70% OK         | 80% OK     |
| 3         | 90% OK      | 80% OK         | 90% OK     |
| 4         | 95% OK      | 90% OK         | 95% OK     |
| 5         | 95% OK      | 95% OK         | 98% OK     |

**Key Points:**
- Thresholds increase +10% per iteration
- Requirements phase always +10% higher
- Deployment phase always +10% higher
- Allows rapid iteration while ensuring quality

### Example: Implementation Phase

**Iteration 1** (Exploratory):
```
Required: 60% completeness, 0.50 quality
Acceptable:
  ✅ Some routes implemented
  ✅ Basic functionality working
  ⚠️  Some stubs/TODOs OK
```

**Iteration 3** (Refinement):
```
Required: 80% completeness, 0.70 quality
Acceptable:
  ✅ Most routes implemented
  ✅ Error handling added
  ❌ Stubs/TODOs not acceptable
```

**Iteration 5** (Production):
```
Required: 95% completeness, 0.90 quality
Acceptable:
  ✅ All routes implemented
  ✅ Full error handling
  ✅ Tests passing
  ✅ Documentation complete
  ❌ Any shortcuts rejected
```

---

## Troubleshooting

### Issue: "team_execution module required"

**Cause:** claude_code_sdk not installed

**Fix:**
```bash
pip install claude_code_sdk
```

### Issue: "Claude CLI not found"

**Cause:** Claude CLI not in PATH

**Fix:**
```bash
npm install -g @anthropic/claude

# Or specify path manually
export PATH=$PATH:~/.nvm/versions/node/v22.19.0/bin
```

### Issue: "Phase needs rework" loop

**Cause:** Not meeting quality thresholds

**Fix:**
```bash
# 1. Check what's wrong
cat sdlc_output/SESSION_ID/validation_reports/FINAL_QUALITY_REPORT.md

# 2. Check specific issues
cat sdlc_output/SESSION_ID/validation_reports/PERSONA_validation.json

# 3. Common fixes:
# - Uncomment routes: grep -r "// router" backend/
# - Remove stubs: grep -r "Coming Soon" frontend/
# - Fix TODOs: grep -r "TODO" .

# 4. Increase iterations if making progress
python phase_integrated_executor.py \
    --session SESSION_ID \
    --requirement "..." \
    --max-iterations 7  # More iterations
```

### Issue: "No progress across iterations"

**Cause:** Personas not understanding requirements

**Fix:**
```bash
# 1. Make requirements more specific
python phase_integrated_executor.py \
    --session new_session \
    --requirement "Build blog platform with:
    - User registration (email/password)
    - Post CRUD (create, read, update, delete)
    - Comment system
    - Like/unlike posts
    - User profiles
    - Search functionality" \
    --max-iterations 5

# 2. Or run specific phases manually
python team_execution.py \
    requirement_analyst solution_architect \
    --session SESSION_ID \
    --output ./output \
    --force
```

---

## Best Practices

### 1. Start with Clear Requirements

**Good:**
```
"Build blog platform with:
- User authentication (JWT)
- Post CRUD API
- React frontend
- PostgreSQL database
- Docker deployment"
```

**Bad:**
```
"Build a blog"
```

### 2. Use Appropriate Iterations

- **Prototype:** 1-2 iterations (60-70% quality)
- **MVP:** 3 iterations (80% quality)
- **Production:** 4-5 iterations (90-95% quality)

### 3. Monitor Phase Transitions

```bash
# Watch for phase transitions
python phase_integrated_executor.py ... 2>&1 | grep "PHASE:\|COMPLETED:\|REWORK:"

# Good sign:
# ✅ COMPLETED: requirements
# ✅ COMPLETED: design
# ✅ COMPLETED: implementation

# Warning sign:
# ⚠️  REWORK NEEDED: implementation (3x in a row)
```

### 4. Check Quality Reports

```bash
# After each run
cat sdlc_output/SESSION/validation_reports/FINAL_QUALITY_REPORT.md

# Key metrics to watch:
# - Average completeness (aim for 80%+)
# - Average quality (aim for 0.70+)
# - Critical issues (should be 0)
```

### 5. Use Sessions Wisely

```bash
# One session per project
python phase_integrated_executor.py \
    --session blog_v1 \
    --requirement "Blog platform" \
    --max-iterations 5

# If making major changes, start new session
python phase_integrated_executor.py \
    --session blog_v2 \
    --requirement "Blog platform with AI features" \
    --max-iterations 5
```

---

## Advanced Features

### Custom Quality Thresholds

```python
from phase_integrated_executor import PhaseIntegratedExecutor
from progressive_quality_manager import ProgressiveQualityManager

# Create custom quality manager
quality_mgr = ProgressiveQualityManager(
    baseline_completeness=0.70,  # Start at 70% instead of 60%
    baseline_quality=0.60,        # Start at 0.60 instead of 0.50
    increment_per_iteration=0.08, # Increase 8% per iteration instead of 10%
    max_completeness=0.98,        # Cap at 98% instead of 95%
    max_quality=0.95              # Cap at 0.95 instead of 0.90
)

# Use in executor
executor = PhaseIntegratedExecutor(
    session_id="custom_quality_project",
    requirement="...",
)
executor.quality_manager = quality_mgr

result = await executor.execute_workflow(max_iterations=5)
```

### Selective Phase Execution

```python
from phase_models import SDLCPhase

# Run only specific phases
executor = PhaseIntegratedExecutor(
    session_id="design_only",
    requirement="..."
)

result = await executor.execute_workflow(
    max_iterations=3,
    target_phases=[SDLCPhase.REQUIREMENTS, SDLCPhase.DESIGN]
)
```

### Phase-Level Metrics

```python
# Extract phase metrics
for phase_exec in result['phase_history']:
    print(f"Phase: {phase_exec['phase']}")
    print(f"  Iteration: {phase_exec['iteration']}")
    print(f"  Completeness: {phase_exec['completeness']:.0%}")
    print(f"  Quality: {phase_exec['quality_score']:.2f}")
    print(f"  Personas: {', '.join(phase_exec['personas'])}")
```

---

## Examples

### Example 1: E-Commerce Platform

```bash
python phase_integrated_executor.py \
    --session ecommerce_v1 \
    --requirement "Build e-commerce platform with:
    - Product catalog with categories
    - Shopping cart
    - Stripe payment integration
    - Order management
    - User accounts
    - Admin dashboard
    - PostgreSQL database
    - Next.js frontend
    - Node.js/Express backend" \
    --max-iterations 5
```

**Expected Phases:**
- Requirements: 1 iteration (~15 min)
- Design: 1 iteration (~20 min)
- Implementation: 2 iterations (~90 min, rework on routes)
- Testing: 1 iteration (~30 min)
- Deployment: 1 iteration (~20 min)
**Total: ~3 hours, 95% quality**

### Example 2: REST API Service

```bash
python phase_integrated_executor.py \
    --session api_service_v1 \
    --requirement "Build REST API service with:
    - User authentication (JWT)
    - CRUD endpoints for resources
    - Rate limiting
    - API documentation (Swagger)
    - Docker deployment
    - PostgreSQL + Redis
    - Express.js/TypeScript" \
    --max-iterations 4
```

**Expected Phases:**
- Requirements: 1 iteration (~10 min)
- Design: 1 iteration (~15 min)
- Implementation: 1 iteration (~45 min)
- Testing: 1 iteration (~20 min)
- Deployment: 1 iteration (~15 min)
**Total: ~2 hours, 90% quality**

### Example 3: Dashboard Application

```bash
python phase_integrated_executor.py \
    --session dashboard_v1 \
    --requirement "Build analytics dashboard with:
    - Real-time data visualization (Chart.js)
    - User authentication
    - Multiple data sources
    - Export to CSV/PDF
    - React frontend
    - Node.js backend
    - WebSocket for real-time updates" \
    --max-iterations 4
```

---

## Getting Help

### Check Logs

```bash
# Detailed logs
python phase_integrated_executor.py ... 2>&1 | tee execution.log

# Search for errors
grep -i "error\|failed" execution.log

# Search for quality issues
grep -i "quality\|completeness" execution.log
```

### Review Documentation

```bash
# System overview
cat PHASE_BASED_SYSTEM_COMPLETE.md

# Gap analysis (why this system was built)
cat COMPREHENSIVE_GAP_ANALYSIS_AND_SOLUTION.md

# Component documentation
cat phase_workflow_orchestrator.py  # Read docstrings
```

### Validation

```bash
# Verify system integrity
python validate_phase_system.py

# Expected: 6/6 validations passed (100%)
```

---

## Summary

**Three commands to remember:**

1. **Start a project:**
   ```bash
   python phase_integrated_executor.py \
       --session PROJECT_NAME \
       --requirement "DESCRIPTION" \
       --max-iterations 5
   ```

2. **Check quality:**
   ```bash
   cat sdlc_output/PROJECT_NAME/validation_reports/FINAL_QUALITY_REPORT.md
   ```

3. **Resume/retry:**
   ```bash
   python phase_integrated_executor.py \
       --session PROJECT_NAME \
       --requirement "SAME DESCRIPTION" \
       --max-iterations 7
   ```

**Key Concepts:**

- ✅ **Phases:** Requirements → Design → Implementation → Testing → Deployment
- ✅ **Progressive Quality:** 60% → 70% → 80% → 90% → 95%
- ✅ **Early Failure:** Caught at phase boundaries, not at end
- ✅ **Cost Savings:** 50-60% via early detection
- ✅ **Clear Feedback:** Specific recommendations per phase

**You're ready to build production-grade software with the phase-based SDLC system!**
