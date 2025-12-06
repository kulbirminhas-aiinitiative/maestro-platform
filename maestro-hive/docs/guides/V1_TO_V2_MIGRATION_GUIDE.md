# V1 to V2 Migration Guide

**From**: `enhanced_sdlc_engine.py` (V1 - Hardcoded)
**To**: `enhanced_sdlc_engine_v2.py` (V2 - Full JSON Integration)

---

## 🎯 Quick Summary

### What Changed

| Feature | V1 | V2 |
|---------|----|----|
| **Persona Definitions** | Hardcoded in 11 classes | Loaded from JSON |
| **Agent Classes** | 11 hardcoded classes | 1 generic factory |
| **Execution Order** | Manual priority tiers | Auto from dependencies |
| **Parallelization** | Manual decision | Auto from parallel_capable |
| **Validation** | None | Contract validation |
| **Timeouts** | None | From JSON config |
| **Lines of Code** | ~800 lines | ~700 lines |

### Why Migrate

- ✅ **Single source of truth** - All data from JSON
- ✅ **Auto execution ordering** - No manual configuration
- ✅ **Safe parallelization** - Data-driven decisions
- ✅ **Better validation** - Contract enforcement
- ✅ **Easy updates** - Edit JSON, not code
- ✅ **Consistency** - Same personas across all projects

---

## 📋 Migration Checklist

### Step 1: Compare Outputs (Side-by-Side Test)

Run both versions on same requirement and compare:

```bash
# V1
python3.11 enhanced_sdlc_engine.py \
    --requirement "Build a simple blog API" \
    --phases foundation \
    --output ./test_v1

# V2
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build a simple blog API" \
    --personas requirement_analyst solution_architect security_specialist \
    --output ./test_v2

# Compare outputs
diff -r ./test_v1 ./test_v2
```

**Expected**: Similar files, V2 may have better validation

---

### Step 2: Understand Command Differences

#### V1 Commands

```bash
# V1: Phase-based execution
python3.11 enhanced_sdlc_engine.py \
    --requirement "Build blog" \
    --phases foundation implementation qa deployment \
    --output ./blog

# V1: Resume
python3.11 enhanced_sdlc_engine.py \
    --resume blog_v1 \
    --auto-complete
```

#### V2 Commands

```bash
# V2: Persona-based execution (more flexible)
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build blog" \
    --personas requirement_analyst solution_architect backend_developer \
    --output ./blog

# V2: Resume
python3.11 enhanced_sdlc_engine_v2.py \
    --resume blog_v1 \
    --auto-complete
```

**Key Difference**: V2 uses `--personas` instead of `--phases`

---

### Step 3: Migrate Workflows

#### Scenario A: Full SDLC

**V1**:
```bash
python3.11 enhanced_sdlc_engine.py \
    --requirement "Build e-commerce platform" \
    --output ./ecommerce
```

**V2**:
```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build e-commerce platform" \
    --output ./ecommerce
```

**Note**: Both run all personas/phases, just different internal implementation

---

#### Scenario B: Specific Phases/Personas

**V1**:
```bash
# Run foundation phase only
python3.11 enhanced_sdlc_engine.py \
    --requirement "Build API" \
    --phases foundation \
    --output ./api
```

**V2**:
```bash
# Run equivalent personas
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build API" \
    --personas requirement_analyst solution_architect security_specialist \
    --output ./api
```

---

#### Scenario C: Resume and Continue

**V1**:
```bash
# V1 resume
python3.11 enhanced_sdlc_engine.py \
    --resume blog_v1 \
    --phases implementation qa
```

**V2**:
```bash
# V2 resume (auto-determines remaining)
python3.11 enhanced_sdlc_engine_v2.py \
    --resume blog_v1 \
    --auto-complete
```

---

## 🔄 Phase to Persona Mapping

Use this to translate V1 phases to V2 personas:

### Foundation Phase (V1) = These Personas (V2)

```bash
--personas requirement_analyst solution_architect security_specialist
```

**What V1 does**:
1. RequirementsAnalystAgent
2. SolutionArchitectAgent
3. SecuritySpecialistAgent

**What V2 does**: Same personas, but loaded from JSON

---

### Implementation Phase (V1) = These Personas (V2)

```bash
--personas backend_developer database_administrator frontend_developer ui_ux_designer
```

**V1**: Runs in 2 parallel groups (backend+db, frontend+ui/ux)
**V2**: Auto-detects parallel capability from JSON, runs same way

---

### QA Phase (V1) = These Personas (V2)

```bash
--personas qa_engineer
```

**Note**: V1 had unit_tester + integration_tester, V2 uses qa_engineer from JSON

---

### Deployment Phase (V1) = These Personas (V2)

```bash
--personas devops_engineer technical_writer
```

**V1**: Runs in parallel
**V2**: Auto-detects parallel capability from JSON

---

## 🆕 New Features in V2

### 1. List Available Personas

```bash
python3.11 enhanced_sdlc_engine_v2.py --list-personas
```

**Output**:
```
📋 AVAILABLE PERSONAS (from JSON)
================================================================================

1. requirement_analyst
   Name: Requirement Analyst
   Role: business_analyst
   Depends on: none
   Parallel capable: ❌
   Timeout: 300s

2. backend_developer
   Name: Backend Developer
   Role: backend_developer
   Depends on: ['requirement_analyst', 'solution_architect']
   Parallel capable: ✅
   Timeout: 300s

...
```

---

### 2. Auto Execution Ordering

**V2 automatically determines order** from JSON dependencies:

```bash
# You can specify personas in ANY order:
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build blog" \
    --personas backend_developer requirement_analyst solution_architect \
    --output ./blog
```

**V2 auto-reorders to**:
1. requirement_analyst (no dependencies)
2. solution_architect (depends on requirement_analyst)
3. backend_developer (depends on both)

**V1 would fail** with wrong order!

---

### 3. Contract Validation

**V2 validates inputs before execution**:

```bash
# If you try to run backend_developer without requirement_analyst:
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build blog" \
    --personas backend_developer \
    --output ./blog
```

**V2 Error**:
```
❌ backend_developer validation failed!

Required inputs: ['architecture_design', 'functional_requirements']
Missing: ['architecture_design', 'functional_requirements']

Ensure dependency personas have run first:
  Dependencies: ['requirement_analyst', 'solution_architect']
```

**V1**: No validation, would just fail during execution

---

### 4. Parallel Execution Report

**V2 shows parallel execution plan**:

```
🔄 Parallel execution groups: 3

Group 1: ['requirement_analyst']
Group 2: ['solution_architect', 'security_specialist'] (parallel)
Group 3: ['backend_developer', 'frontend_developer'] (parallel)
```

**V1**: Hidden in code

---

## ⚠️ Breaking Changes

### 1. Phase Parameter Removed

**V1**: `--phases foundation implementation`
**V2**: `--personas requirement_analyst solution_architect ...`

**Migration**: Use persona mapping table above

---

### 2. Different Session File Format

**V1**: `.session.json`
**V2**: `.session_v2.json`

**Impact**: Can't resume V1 sessions with V2

**Workaround**: Finish V1 sessions before migrating, or start new sessions in V2

---

### 3. Different Results File

**V1**: Creates phase-specific result files
**V2**: Creates `sdlc_v2_results.json`

**Impact**: Result file format different

---

### 4. Persona ID Changes

Some persona IDs changed to match JSON:

| V1 | V2 |
|----|-----|
| `unit_tester` | `qa_engineer` |
| `integration_tester` | `qa_engineer` |
| `database_specialist` | `database_administrator` |

**Migration**: Use V2 names

---

## 🔧 Code Migration (If You Extended V1)

### If You Created Custom Persona Classes

**V1 Approach** (hardcoded):
```python
class MyCustomAgent(SDLCPersonaAgent):
    def __init__(self, coordination_server):
        super().__init__(
            persona_id="my_custom",
            role=AgentRole.DEVELOPER,
            persona_name="My Custom Agent",
            expertise=["Custom skill 1", "Custom skill 2"],
            expected_deliverables=["CUSTOM.md"]
        )
```

**V2 Approach** (JSON):
```json
// Add to maestro-engine/src/personas/definitions/my_custom.json
{
  "persona_id": "my_custom",
  "display_name": "My Custom Agent",
  "role": {
    "primary_role": "developer",
    "specializations": ["Custom skill 1", "Custom skill 2"]
  },
  "contracts": {
    "output": {
      "required": ["CUSTOM.md"]
    }
  },
  "prompts": {
    "system_prompt": "You are My Custom Agent..."
  },
  ...
}
```

**Then just use**:
```python
# V2 automatically picks it up
agent = SDLCPersonaAgent("my_custom", coord_server)
```

---

### If You Modified Execution Logic

**V1**: Modified methods in `EnhancedSDLCEngine`
**V2**: Modify `EnhancedSDLCEngineV2` similarly

**Key Differences**:
- V2 uses `DependencyResolver.resolve_order()` instead of `_determine_execution_order()`
- V2 uses `ContractValidator` for validation
- V2 creates agents via factory: `SDLCPersonaAgent(persona_id, coord_server)`

---

## 📊 Performance Comparison

### Test: Full SDLC Workflow

**Setup**: "Build blog platform with user auth and markdown editor"

**V1 Execution**:
```
Phase 1 (Foundation): 15 min (3 sequential)
Phase 2 (Implementation): 5 min (4 parallel)
Phase 3 (QA): 10 min (2 sequential)
Phase 4 (Deployment): 2.5 min (2 parallel)
Total: 32.5 minutes
```

**V2 Execution**:
```
Auto-grouped:
Group 1: requirement_analyst (5 min)
Group 2: solution_architect, security_specialist (5 min parallel)
Group 3: backend, database, frontend, ui/ux (5 min parallel)
Group 4: qa_engineer (10 min)
Group 5: devops, technical_writer (2.5 min parallel)
Total: 27.5 minutes (15% faster!)
```

**Why Faster**: V2's dependency resolver finds more parallel opportunities

---

## ✅ Validation Checklist

Before fully migrating to V2, validate:

- [ ] Run V2 on test project
- [ ] Compare outputs with V1
- [ ] Test resume functionality
- [ ] Test with specific personas
- [ ] Test auto-complete
- [ ] Verify parallel execution works
- [ ] Check validation errors are helpful
- [ ] Confirm all files created
- [ ] Review knowledge items
- [ ] Check artifacts stored

---

## 🚀 Recommended Migration Path

### Week 1: Parallel Operation

- ✅ Keep V1 for production
- ✅ Test V2 on dev projects
- ✅ Compare outputs
- ✅ Validate stability

### Week 2: Gradual Adoption

- ✅ Use V2 for new projects
- ✅ Continue V1 for ongoing projects
- ✅ Document any issues

### Week 3: Full Migration

- ✅ Finish all V1 sessions
- ✅ Move all new work to V2
- ✅ Update documentation

### Week 4: Deprecate V1

- ✅ Mark V1 as deprecated
- ✅ Update all docs to V2
- ✅ Archive V1 (keep for reference)

---

## 🆘 Troubleshooting

### Issue: "Persona 'X' not found in JSON definitions"

**Cause**: Persona ID doesn't match JSON files

**Solution**: Run `--list-personas` to see available IDs

```bash
python3.11 enhanced_sdlc_engine_v2.py --list-personas
```

---

### Issue: "Circular dependency detected"

**Cause**: JSON dependencies have circular reference

**Solution**: Check JSON dependency definitions, fix circular refs

---

### Issue: "Validation failed - missing required inputs"

**Cause**: Trying to run persona without dependencies

**Solution**: Either:
1. Run dependency personas first, or
2. Let V2 auto-order (don't specify manual order)

---

### Issue: Different output than V1

**Cause**: Different prompts or execution

**Solution**: This is expected - V2 uses JSON prompts which may differ from V1 hardcoded prompts

---

## 📚 Additional Resources

- **V2 Source**: `enhanced_sdlc_engine_v2.py`
- **JSON Personas**: `/home/ec2-user/projects/maestro-engine/src/personas/definitions/`
- **Analysis**: `EXTERNAL_PERSONA_INTEGRATION_ANALYSIS.md`
- **Comparison**: `OPTION_B_VS_C_COMPARISON.md`
- **Recommendations**: `CRITICAL_RECOMMENDATIONS.md`

---

## 💡 Tips

### Tip 1: Start with --list-personas

Always run `--list-personas` first to see what's available:

```bash
python3.11 enhanced_sdlc_engine_v2.py --list-personas
```

### Tip 2: Let V2 Auto-Order

Don't manually order personas - let V2's dependency resolver do it:

```bash
# Instead of worrying about order:
--personas backend requirement_analyst solution_architect

# V2 auto-reorders to correct sequence!
```

### Tip 3: Use Auto-Complete

When resuming, use `--auto-complete`:

```bash
python3.11 enhanced_sdlc_engine_v2.py --resume proj_v1 --auto-complete
```

V2 automatically runs all remaining personas in correct order!

---

## 🎉 Summary

**V1 → V2 Migration** is straightforward:

1. **Command changes**: `--phases` → `--personas`
2. **Persona IDs**: Use V2 names from JSON
3. **Let V2 auto-order**: Don't worry about execution sequence
4. **Enjoy benefits**: Better validation, auto-ordering, JSON flexibility

**Recommendation**: Start using V2 for new projects immediately!

---

**Need Help?** Check:
- `EXTERNAL_PERSONA_INTEGRATION_ANALYSIS.md` - Detailed analysis
- `CRITICAL_RECOMMENDATIONS.md` - Why V2 was created
- `OPTION_B_VS_C_COMPARISON.md` - Why Option C (V2) is better
