# Enhanced SDLC Engine V2 - Quick Reference

**One-page cheat sheet for daily use**

---

## 🚀 Quick Start

```bash
# Full SDLC (all personas)
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Your project description" \
    --output ./my_project

# Specific personas only
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Your project description" \
    --personas requirement_analyst backend_developer \
    --output ./my_project

# Resume and auto-complete
python3.11 enhanced_sdlc_engine_v2.py \
    --resume my_project_session \
    --auto-complete
```

---

## 📋 Common Commands

| Task | Command |
|------|---------|
| **List available personas** | `--list-personas` |
| **Full SDLC** | `--requirement "..." --output ./dir` |
| **Specific personas** | `--personas p1 p2 p3 --requirement "..."` |
| **Resume session** | `--resume session_id` |
| **Auto-complete** | `--resume session_id --auto-complete` |
| **Custom session ID** | `--session-id my_id` |

---

## 👥 Available Personas (from JSON)

| Persona ID | Display Name | Depends On | Parallel? |
|-----------|--------------|-----------|-----------|
| `requirement_analyst` | Requirement Analyst | none | ❌ |
| `solution_architect` | Solution Architect | requirement_analyst | ❌ |
| `security_specialist` | Security Specialist | solution_architect | ✅ |
| `backend_developer` | Backend Developer | requirement_analyst, solution_architect | ✅ |
| `database_administrator` | Database Administrator | requirement_analyst, solution_architect | ✅ |
| `frontend_developer` | Frontend Developer | solution_architect | ✅ |
| `ui_ux_designer` | UI/UX Designer | requirement_analyst | ✅ |
| `qa_engineer` | QA Engineer | backend_developer, frontend_developer | ❌ |
| `devops_engineer` | DevOps Engineer | backend_developer | ✅ |
| `technical_writer` | Technical Writer | - | ✅ |

---

## 🎯 Common Workflows

### Workflow 1: Analysis Only

```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build e-commerce platform" \
    --personas requirement_analyst solution_architect \
    --output ./ecommerce_analysis
```

**Result**: Requirements + Architecture docs

---

### Workflow 2: Backend Development

```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build REST API for blog" \
    --personas requirement_analyst solution_architect backend_developer database_administrator \
    --output ./blog_api
```

**Result**: Backend code + Database schema

---

### Workflow 3: Full Stack

```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build task management app" \
    --personas requirement_analyst solution_architect backend_developer frontend_developer ui_ux_designer \
    --output ./task_app
```

**Result**: Complete frontend + backend

---

### Workflow 4: Complete SDLC

```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build complete SaaS application" \
    --output ./saas_app
```

**Result**: Analysis → Development → Testing → Deployment (all personas)

---

## 🔄 Resume Workflows

### Scenario: Multi-Day Development

**Day 1**:
```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --requirement "Build CRM system" \
    --personas requirement_analyst solution_architect \
    --session-id crm_v1 \
    --output ./crm
```

**Day 2**:
```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --resume crm_v1 \
    --personas backend_developer database_administrator \
    --output ./crm
```

**Day 3**:
```bash
python3.11 enhanced_sdlc_engine_v2.py \
    --resume crm_v1 \
    --auto-complete
```

---

## 📊 Output Files

Every execution creates:

```
output_directory/
├── .session_v2.json              # Session state (for resume)
├── sdlc_v2_results.json          # Execution results
├── REQUIREMENTS.md               # From requirement_analyst
├── ARCHITECTURE.md               # From solution_architect
├── backend/                      # From backend_developer
│   ├── src/
│   └── README.md
├── database/                     # From database_administrator
│   └── schema.sql
├── frontend/                     # From frontend_developer
│   └── src/
└── ... (other persona outputs)
```

---

## 🎨 V2 Features

### ✅ What V2 Does Automatically

1. **Auto-orders personas** from JSON dependencies
2. **Parallel execution** where JSON says safe
3. **Validates inputs** before execution
4. **Enforces timeouts** from JSON config
5. **Tracks progress** in session file

### ✅ Key Advantages

- **No hardcoding** - All data from JSON
- **Smart ordering** - Can specify personas in any order
- **Safe parallelization** - Based on JSON metadata
- **Better errors** - Clear validation messages
- **Flexible** - Add personas without code changes

---

## ⚡ Performance Tips

### Tip 1: Don't Worry About Order

V2 auto-orders based on dependencies:

```bash
# These all produce same result:
--personas backend requirement_analyst solution_architect
--personas requirement_analyst solution_architect backend
--personas solution_architect backend requirement_analyst

# V2 always runs in correct order:
# 1. requirement_analyst
# 2. solution_architect
# 3. backend_developer
```

---

### Tip 2: Use Auto-Complete for Resume

```bash
# Instead of manually listing remaining personas:
python3.11 enhanced_sdlc_engine_v2.py \
    --resume proj_v1 \
    --personas qa_engineer devops_engineer technical_writer

# Just use auto-complete:
python3.11 enhanced_sdlc_engine_v2.py \
    --resume proj_v1 \
    --auto-complete

# V2 runs all remaining personas automatically!
```

---

### Tip 3: Check Available Personas First

```bash
# Always run this first when unsure:
python3.11 enhanced_sdlc_engine_v2.py --list-personas

# Shows all available personas with dependencies
```

---

## 🐛 Troubleshooting

### Error: "Persona 'X' not found"

**Solution**: Run `--list-personas` to see valid IDs

---

### Error: "Validation failed - missing required inputs"

**Solution**: Either:
1. Include dependency personas in `--personas` list, or
2. Run dependencies first, then resume

**Example**:
```bash
# ❌ This fails:
--personas backend_developer

# ✅ This works:
--personas requirement_analyst solution_architect backend_developer

# ✅ Or this:
# First run:
--personas requirement_analyst solution_architect
# Then resume:
--resume session_id --personas backend_developer
```

---

### Error: "Circular dependency detected"

**Solution**: This is a bug in JSON definitions. Report to team.

---

### Slow Execution

**Check**: Are personas running in parallel?

```bash
# V2 logs show:
🔄 Parallel execution groups: 3
Group 1: ['requirement_analyst']
Group 2: ['solution_architect', 'security_specialist'] (parallel)
Group 3: ['backend_developer', 'frontend_developer'] (parallel)
```

If all sequential, check JSON `parallel_capable` flags.

---

## 📈 Example Output Logs

### Successful Execution

```
================================================================================
🚀 ENHANCED SDLC ENGINE V2 - Full JSON Integration
================================================================================
📝 Requirement: Build a blog platform...
🆔 Session: sdlc_v2_20251004_103000
👥 Personas to execute: 3
📁 Output: ./blog_project
================================================================================

📋 Auto-resolved execution order (from JSON dependencies):
   1. requirement_analyst (depends on: none)
   2. solution_architect (depends on: ['requirement_analyst'])
   3. backend_developer (depends on: ['requirement_analyst', 'solution_architect'])

🔄 Parallel execution groups: 3
   Group 1: ['requirement_analyst']
   Group 2: ['solution_architect']
   Group 3: ['backend_developer']

================================================================================
🎯 GROUP 1/3: 1 persona(s)
================================================================================
[requirement_analyst] 🤖 Starting Requirement Analyst...
[requirement_analyst] 📦 Expected outputs: REQUIREMENTS.md, USER_STORIES.md, ...
[requirement_analyst] 📄 Created: REQUIREMENTS.md
[requirement_analyst] ✅ Completed: 3 files in 45.2s

... (more groups)

================================================================================
📊 SDLC EXECUTION COMPLETE (V2)
================================================================================
✅ Success: True
🆔 Session: sdlc_v2_20251004_103000
👥 Personas executed: 3
   ✅ Successful: 3
   ❌ Failed: 0
📁 Files created: 12
📚 Knowledge items: 8
📦 Artifacts: 6
💬 Messages: 15
⏱️  Duration: 95.30s
📂 Output: ./blog_project
================================================================================
```

---

## 🔗 Related Files

- **V2 Source**: `enhanced_sdlc_engine_v2.py`
- **Migration Guide**: `V1_TO_V2_MIGRATION_GUIDE.md`
- **JSON Personas**: `/home/ec2-user/projects/maestro-engine/src/personas/definitions/`
- **Analysis**: `EXTERNAL_PERSONA_INTEGRATION_ANALYSIS.md`

---

## 💡 Pro Tips

1. **Always use `--list-personas`** when starting a new project
2. **Let V2 auto-order** - don't manually sequence personas
3. **Use `--auto-complete`** for easy resume
4. **Check logs** for parallel execution confirmation
5. **Review `sdlc_v2_results.json`** for detailed metrics

---

## 🎯 When to Use What

| Scenario | Command Pattern |
|----------|----------------|
| **Quick analysis** | `--personas requirement_analyst solution_architect` |
| **Backend only** | `--personas req... sol... backend database` |
| **Frontend only** | `--personas req... sol... frontend ui_ux` |
| **Full stack** | `--personas req... sol... backend frontend database ui_ux` |
| **Complete SDLC** | No `--personas` (runs all) |
| **Resume & finish** | `--resume id --auto-complete` |

---

**Last Updated**: 2025-10-04
**Version**: 2.0
