# Resumable Workflow Guide - V3.1

## Overview

V3.1 introduces **session-based, resumable workflows** that allow you to build projects **incrementally across multiple days/runs**.

Each persona's work is saved to a session. You can resume anytime and add more personas.

---

## Key Features

✅ **Session Persistence** - All work saved to disk + MCP cache
✅ **Incremental Execution** - Add personas one at a time or in groups
✅ **Context Propagation** - New personas see all previous work
✅ **No Duplication** - Automatically skips already-completed personas
✅ **Cross-Day Resume** - Come back anytime and continue

---

## Real-World Workflow Example

### Day 1: Requirements Analysis

```bash
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "Create a blog platform with authentication and comments" \
    --session-id blog_platform_v1
```

**Output:**
- Session created: `blog_platform_v1`
- Files: requirements.md, user_stories.md, acceptance_criteria.md
- Saved to: `./generated_v3_project/` + MCP cache

---

### Day 2: Add UX Design

```bash
# Resume existing session
python autonomous_sdlc_engine_v3_resumable.py ui_ux_designer \
    --resume blog_platform_v1
```

**What happens:**
- ✅ Loads session `blog_platform_v1`
- ✅ Sees requirements from Day 1
- ✅ Executes `ui_ux_designer` only
- ✅ Creates wireframes, mockups
- ✅ Saves updated session

---

### Day 3: Add Architecture + Backend

```bash
# Resume and add multiple personas
python autonomous_sdlc_engine_v3_resumable.py solution_architect backend_developer \
    --resume blog_platform_v1
```

**What happens:**
- ✅ Loads all previous work (requirements + UX)
- ✅ Executes architect → designs system
- ✅ Executes backend → implements APIs
- ✅ All personas see previous context
- ✅ Saves updated session

---

### Day 4: Add Frontend + DevOps

```bash
python autonomous_sdlc_engine_v3_resumable.py frontend_developer devops_engineer \
    --resume blog_platform_v1
```

---

### Day 5: Add Testing + Documentation

```bash
python autonomous_sdlc_engine_v3_resumable.py unit_tester integration_tester technical_writer \
    --resume blog_platform_v1
```

---

### Shortcut: Run ALL Remaining Personas

Instead of specifying personas one by one, use `--all-remaining`:

```bash
# After Day 1 (only requirement_analyst completed)
# This will run ALL other 10 personas automatically:
python autonomous_sdlc_engine_v3_resumable.py \
    --resume blog_platform_v1 \
    --all-remaining
```

**What happens:**
- ✅ Loads session
- ✅ Identifies completed personas: `requirement_analyst`
- ✅ Automatically runs remaining 10 personas in optimal order:
  - solution_architect
  - security_specialist
  - backend_developer
  - database_specialist
  - frontend_developer
  - ui_ux_designer
  - unit_tester
  - integration_tester
  - devops_engineer
  - technical_writer

---

## Session Management

### List All Sessions

```bash
python autonomous_sdlc_engine_v3_resumable.py --list-sessions
```

**Output:**
```
================================================================================
📋 AVAILABLE SESSIONS
================================================================================

1. Session: blog_platform_v1
   Requirement: Create a blog platform with authentication and comments
   Created: 2025-10-02T10:00:00
   Last Updated: 2025-10-05T14:30:00
   Completed Personas: 7
   Files: 45

2. Session: ecommerce_shop_v1
   Requirement: Create an e-commerce platform
   Created: 2025-10-01T09:00:00
   Last Updated: 2025-10-01T11:00:00
   Completed Personas: 2
   Files: 12
================================================================================
```

### Check Session Status

```bash
# Session files are stored in:
./sdlc_sessions/blog_platform_v1.json

# Also in MCP cache:
/tmp/mcp_shared_context/blog_platform_v1_session.json
```

### View Session Details

```bash
cat ./sdlc_sessions/blog_platform_v1.json
```

---

## Workflow Patterns

### Pattern 0: Review-Then-Complete (Recommended)

Run one phase, review, then complete everything else:

```bash
# Day 1: Requirements only
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "Create a task management app" \
    --session-id task_app_v1

# Review requirements.md, user_stories.md...
# Happy with it? Run everything else:

# Day 2: Complete the rest
python autonomous_sdlc_engine_v3_resumable.py \
    --resume task_app_v1 \
    --all-remaining
```

**Benefits:**
- ✅ Review requirements before committing to full build
- ✅ One command to finish entire project
- ✅ No need to list all personas manually

### Pattern 1: Sequential Phases (Safest)

Execute one persona at a time, reviewing output before continuing:

```bash
# Phase 1: Requirements
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "..." --session-id my_project

# Review output, then Phase 2: Architecture
python autonomous_sdlc_engine_v3_resumable.py solution_architect \
    --resume my_project

# Review output, then Phase 3: Security
python autonomous_sdlc_engine_v3_resumable.py security_specialist \
    --resume my_project

# And so on...
```

### Pattern 2: Batched Phases

Group related personas together:

```bash
# Phase 1: Analysis + Architecture
python autonomous_sdlc_engine_v3_resumable.py \
    requirement_analyst solution_architect security_specialist \
    --requirement "..." --session-id my_project

# Phase 2: Development
python autonomous_sdlc_engine_v3_resumable.py \
    backend_developer frontend_developer database_specialist \
    --resume my_project

# Phase 3: Testing + Deployment
python autonomous_sdlc_engine_v3_resumable.py \
    unit_tester integration_tester devops_engineer technical_writer \
    --resume my_project
```

### Pattern 3: Iterative Refinement

Run personas, review, then re-run if needed:

```bash
# First pass
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "..." --session-id my_project

# Review requirements, not happy? Create new session with refined requirement
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "... (more detailed)" --session-id my_project_v2
```

---

## Session Persistence

### Storage Locations

1. **Local disk**: `./sdlc_sessions/<session_id>.json`
2. **MCP cache**: `/tmp/mcp_shared_context/<session_id>_session.json`

### Session Contents

Each session stores:
- Session ID
- Original requirement
- Output directory
- List of completed personas
- Files created by each persona
- Execution timestamps
- Deliverables produced

### Session Lifecycle

```
1. Create Session
   ↓
2. Execute Persona(s)
   ↓
3. Save Session State ← After each persona!
   ↓
4. Resume Session (add more personas)
   ↓
5. Save Updated State
   ↓
6. Repeat 4-5 as needed
```

---

## Benefits of Resumable Workflow

### 1. **Incremental Development**
Build complex projects step-by-step without overwhelming the system

### 2. **Review Between Phases**
Review each persona's output before proceeding to next phase

### 3. **Flexible Scheduling**
Work on project across days/weeks without losing context

### 4. **Resource Management**
Don't run all 11 personas if you only need 3

### 5. **Cost Control**
Only execute personas you need, when you need them

### 6. **Error Recovery**
If a persona fails, resume from that point without re-running everything

---

## Advanced Usage

### Custom Session ID

```bash
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "Create blog" \
    --session-id client_acme_blog_2025
```

### Custom Output Directory

```bash
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "Create blog" \
    --session-id my_blog \
    --output-dir /path/to/custom/output
```

### Skip Already Completed Personas

If you accidentally request personas already completed, they're automatically skipped:

```bash
# Day 1: Run requirement_analyst
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "..." --session-id blog_v1

# Day 2: Request requirement_analyst again (will skip) + ui_ux_designer (will run)
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst ui_ux_designer \
    --resume blog_v1

# Output: "requirement_analyst already completed, skipping. Running ui_ux_designer..."
```

---

## Integration with MCP Cache

Sessions are stored in MCP cache (`/tmp/mcp_shared_context/`), enabling:

- **Cross-process access**: Other tools can read session state
- **Event observation**: MCP-aware tools can monitor progress
- **Distributed workflows**: Multiple agents can collaborate on same session

---

## Best Practices

### 1. Use Descriptive Session IDs
```bash
# Good
--session-id client_acme_ecommerce_mvp_oct2025

# Less good
--session-id proj1
```

### 2. Review Between Phases
Don't blindly execute all personas. Review output after each phase.

### 3. Save Session ID
After creating a session, save the session ID for future resume:

```bash
echo "blog_platform_v1" > .current_session
# Later:
python ... --resume $(cat .current_session)
```

### 4. Use --list-sessions Regularly
Check what sessions you have and their status

### 5. Clean Up Old Sessions
Delete sessions you no longer need (manually delete JSON files)

---

## Troubleshooting

### Session Not Found

```bash
❌ Error: Session not found: blog_v1
```

**Solution**: Check `./sdlc_sessions/` or run `--list-sessions`

### Persona Already Completed

```bash
✅ Persona requirement_analyst already completed, skipping
```

**Solution**: This is expected behavior. Request different personas.

### Context Not Propagating

If new personas don't see previous work, check:
1. Output directory matches session's output_dir
2. Files were actually created in previous runs
3. Session was saved successfully

---

## Example: Complete Project Lifecycle

```bash
# Week 1: Requirements
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "Create a task management SaaS platform" \
    --session-id task_mgmt_saas_v1

# Week 2: Architecture
python autonomous_sdlc_engine_v3_resumable.py solution_architect security_specialist \
    --resume task_mgmt_saas_v1

# Week 3: Development
python autonomous_sdlc_engine_v3_resumable.py \
    backend_developer frontend_developer database_specialist \
    --resume task_mgmt_saas_v1

# Week 4: UX
python autonomous_sdlc_engine_v3_resumable.py ui_ux_designer \
    --resume task_mgmt_saas_v1

# Week 5: Testing
python autonomous_sdlc_engine_v3_resumable.py unit_tester integration_tester \
    --resume task_mgmt_saas_v1

# Week 6: Deployment
python autonomous_sdlc_engine_v3_resumable.py devops_engineer technical_writer \
    --resume task_mgmt_saas_v1

# Final result: Complete SaaS platform built incrementally over 6 weeks!
```

---

## Comparison: V2 vs V3 vs V3.1

| Feature | V2 | V3 | V3.1 (Resumable) |
|---------|----|----|------------------|
| Dynamic personas | ❌ | ✅ | ✅ |
| Session persistence | ❌ | ❌ | ✅ |
| Incremental execution | ❌ | ❌ | ✅ |
| Resume capability | ❌ | ❌ | ✅ |
| MCP cache integration | ❌ | ❌ | ✅ |
| Cross-day workflows | ❌ | ❌ | ✅ |

---

## Next Steps

Try V3.1 now:

```bash
cd /home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team

# Create your first resumable session
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \
    --requirement "Create a modern web application for task management" \
    --session-id my_first_session

# List sessions to see it
python autonomous_sdlc_engine_v3_resumable.py --list-sessions

# Resume and add more work
python autonomous_sdlc_engine_v3_resumable.py ui_ux_designer \
    --resume my_first_session
```

Happy incremental development! 🚀
