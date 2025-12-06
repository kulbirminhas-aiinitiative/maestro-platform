# Enhanced SDLC Engine - Usage Guide

**Complete guide to using the SDK-powered SDLC workflow engine**

---

## 🚀 Quick Start

### 1. Complete SDLC Workflow

```bash
python3.11 enhanced_sdlc_engine.py \
    --requirement "Build a blog platform with user authentication and markdown editor" \
    --output ./blog_project
```

**What happens**:
- All 4 phases execute automatically
- 11 personas work together
- Parallel execution where possible
- Real agent collaboration via SDK
- Output in `./blog_project/`

**Duration**: ~30-35 minutes (vs 50 minutes in V3)

---

### 2. Phase-by-Phase Execution

**Day 1 - Foundation**:
```bash
python3.11 enhanced_sdlc_engine.py \
    --requirement "Build a blog platform with user authentication" \
    --phases foundation \
    --session-id blog_v1 \
    --output ./blog_project
```

**Executes**:
- Requirements Analyst
- Solution Architect
- Security Specialist

**Duration**: ~15 minutes

---

**Day 2 - Implementation**:
```bash
python3.11 enhanced_sdlc_engine.py \
    --resume blog_v1 \
    --phases implementation
```

**Executes** (in parallel):
- Backend Developer + Database Specialist
- Frontend Developer + UI/UX Designer

**Duration**: ~5 minutes (parallel!)

---

**Day 3 - QA & Deployment**:
```bash
python3.11 enhanced_sdlc_engine.py \
    --resume blog_v1 \
    --auto-complete
```

**Executes**:
- QA: Unit Tester → Integration Tester
- Deployment: DevOps + Tech Writer (parallel)

**Duration**: ~12 minutes

---

## 📋 Command Reference

### New SDLC Session

```bash
python3.11 enhanced_sdlc_engine.py \
    --requirement "Your project requirement" \
    [--output OUTPUT_DIR] \
    [--session-id SESSION_ID] \
    [--phases PHASE1 PHASE2 ...]
```

**Required**:
- `--requirement` - Project requirement description

**Optional**:
- `--output` - Output directory (default: `./sdlc_output`)
- `--session-id` - Custom session ID (default: auto-generated)
- `--phases` - Specific phases to run (default: all 4 phases)

---

### Resume Existing Session

```bash
python3.11 enhanced_sdlc_engine.py \
    --resume SESSION_ID \
    [--phases PHASE1 PHASE2 ...] \
    [--auto-complete]
```

**Required**:
- `--resume` - Session ID to resume

**Optional**:
- `--phases` - Specific phases to execute
- `--auto-complete` - Run all remaining phases

---

## 🎯 Available Phases

### Phase 1: `foundation`
**Personas**: Requirements Analyst → Solution Architect → Security Specialist
**Pattern**: Sequential Pipeline
**Duration**: ~15 minutes

**Deliverables**:
- `REQUIREMENTS.md` - Comprehensive requirements
- `USER_STORIES.md` - User stories
- `ARCHITECTURE.md` - System architecture
- `TECH_STACK.md` - Technology choices
- `SECURITY_REVIEW.md` - Security analysis
- `THREAT_MODEL.md` - Threat modeling

---

### Phase 2: `implementation`
**Personas**: Backend + Database || Frontend + UI/UX
**Pattern**: Parallel Execution + Messaging
**Duration**: ~5 minutes (parallel)

**Deliverables**:
- `backend/` - Backend source code
- `database/schema.sql` - Database schema
- `frontend/` - Frontend source code
- `design/WIREFRAMES.md` - UI wireframes
- `API_DOCUMENTATION.md` - API docs
- `DATABASE_DESIGN.md` - Database docs

---

### Phase 3: `qa`
**Personas**: Unit Tester → Integration Tester
**Pattern**: Sequential Pipeline
**Duration**: ~10 minutes

**Deliverables**:
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `UNIT_TEST_PLAN.md` - Unit test strategy
- `INTEGRATION_TEST_PLAN.md` - Integration test strategy

---

### Phase 4: `deployment`
**Personas**: DevOps Engineer || Technical Writer
**Pattern**: Parallel Execution
**Duration**: ~2.5 minutes (parallel)

**Deliverables**:
- `deploy/` - Deployment configs
- `Dockerfile` - Container definition
- `.github/workflows/` - CI/CD pipelines
- `README.md` - Project README
- `docs/USER_GUIDE.md` - User guide
- `docs/DEVELOPER_GUIDE.md` - Developer guide
- `DEPLOYMENT_GUIDE.md` - Deployment docs

---

## 💡 Real-World Examples

### Example 1: E-Commerce Platform

```bash
python3.11 enhanced_sdlc_engine.py \
    --requirement "Build an e-commerce platform with product catalog, shopping cart, checkout, payment integration (Stripe), and admin dashboard" \
    --session-id ecommerce_v1 \
    --output ./ecommerce_project
```

**Result**:
- Complete e-commerce system
- All SDLC deliverables
- ~32 minutes total execution
- Knowledge shared across team
- Parallel implementation

---

### Example 2: API Gateway Service

```bash
# Day 1 - Planning
python3.11 enhanced_sdlc_engine.py \
    --requirement "API Gateway with rate limiting, authentication, request routing, and monitoring" \
    --phases foundation \
    --session-id api_gateway_v1 \
    --output ./api_gateway

# Day 2 - Build
python3.11 enhanced_sdlc_engine.py \
    --resume api_gateway_v1 \
    --phases implementation

# Day 3 - Complete
python3.11 enhanced_sdlc_engine.py \
    --resume api_gateway_v1 \
    --auto-complete
```

---

### Example 3: Real-Time Chat Application

```bash
python3.11 enhanced_sdlc_engine.py \
    --requirement "Real-time chat application with WebSockets, user presence, message history, file sharing, and notifications" \
    --output ./chat_app
```

**Features Used**:
- Foundation: Architecture decisions (WebSocket vs polling)
- Implementation: Backend + Frontend work in parallel
- QA: Unit and integration tests
- Deployment: Kubernetes configs + user docs

---

## 🔍 Understanding Output

### Directory Structure

```
blog_project/
├── .session.json                      # Session metadata (for resume)
├── REQUIREMENTS.md                    # Phase 1: Requirements
├── USER_STORIES.md
├── ARCHITECTURE.md                    # Phase 1: Architecture
├── TECH_STACK.md
├── SECURITY_REVIEW.md                 # Phase 1: Security
├── THREAT_MODEL.md
├── backend/                           # Phase 2: Backend
│   ├── src/
│   │   ├── api.py
│   │   ├── auth.py
│   │   └── models.py
│   └── README.md
├── database/                          # Phase 2: Database
│   ├── schema.sql
│   ├── migrations/
│   └── DATABASE_DESIGN.md
├── frontend/                          # Phase 2: Frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.js
│   └── README.md
├── design/                            # Phase 2: UI/UX
│   ├── WIREFRAMES.md
│   ├── DESIGN_SYSTEM.md
│   └── USER_FLOWS.md
├── tests/                             # Phase 3: Testing
│   ├── unit/
│   ├── integration/
│   └── README.md
├── deploy/                            # Phase 4: Deployment
│   ├── kubernetes/
│   ├── docker-compose.yml
│   └── DEPLOYMENT_GUIDE.md
├── docs/                              # Phase 4: Documentation
│   ├── USER_GUIDE.md
│   └── DEVELOPER_GUIDE.md
├── README.md                          # Phase 4: Main README
├── Dockerfile
└── .github/
    └── workflows/
        └── ci.yml
```

---

### Session File (.session.json)

```json
{
  "session_id": "blog_v1",
  "requirement": "Build a blog platform with user authentication and markdown editor",
  "completed_phases": [
    "foundation",
    "implementation"
  ],
  "timestamp": "2025-10-04T10:30:00"
}
```

**Use**: Resume capability - tracks completed phases

---

## 🧪 SDK Features in Action

### Knowledge Sharing

**Requirements Analyst** shares findings:
```python
await analyst.share_knowledge(
    key="user_requirements",
    value=requirements_doc,
    category="analysis"
)
```

**Solution Architect** retrieves them:
```python
requirements = await architect.get_knowledge("user_requirements")
# Builds architecture based on requirements
```

---

### Inter-Agent Messaging

**Backend Developer** notifies Frontend:
```python
await backend_dev.post_message(
    to_agent="frontend_developer",
    message="API endpoints ready: /api/v1/users, /api/v1/posts, /api/v1/auth"
)
```

**Frontend Developer** receives:
```python
messages = await frontend_dev.get_messages()
# Uses API endpoint info in implementation
```

---

### Parallel Execution

```python
# 4 personas work simultaneously
results = await asyncio.gather(
    backend_dev.execute_work(...),
    database_specialist.execute_work(...),
    frontend_dev.execute_work(...),
    ui_ux.execute_work(...)
)
```

**Speedup**: 4× faster than sequential

---

### Status Monitoring

```python
await agent.update_status(AgentStatus.WORKING, "Implementing authentication")
team_status = await coordinator.get_team_status()
# Real-time visibility into all agents
```

---

## 🎓 Best Practices

### 1. Clear Requirements

**Good**:
```bash
--requirement "Build a REST API for task management with user authentication (JWT), CRUD operations for tasks, task categories, due dates, and PostgreSQL database"
```

**Bad**:
```bash
--requirement "Task app"
```

---

### 2. Phase Selection

For **rapid prototyping**, run foundation only:
```bash
--phases foundation
```

For **implementation testing**, skip QA/deployment:
```bash
--phases foundation implementation
```

For **complete project**, run all phases:
```bash
# No --phases argument = all phases
```

---

### 3. Session Management

**Use custom session IDs** for projects:
```bash
--session-id project_name_v1
```

**Resume by ID**:
```bash
--resume project_name_v1
```

**Version iterations**:
```bash
--session-id project_name_v2  # New iteration
```

---

### 4. Output Organization

**Organize by project**:
```bash
--output ./projects/blog_platform
--output ./projects/api_gateway
--output ./projects/chat_app
```

---

## 🐛 Troubleshooting

### Issue: "Session not found"

**Cause**: Session file doesn't exist
**Solution**: Check output directory has `.session.json`

```bash
ls -la ./blog_project/.session.json
```

---

### Issue: "No agents initialized"

**Cause**: TeamCoordinator not created properly
**Solution**: Check output directory permissions

```bash
mkdir -p ./blog_project
chmod 755 ./blog_project
```

---

### Issue: Slow execution

**Cause**: Sequential execution instead of parallel
**Solution**: Ensure using `enhanced_sdlc_engine.py`, not V3

```bash
# Should see "Parallel execution" logs
grep -i "parallel" logs.txt
```

---

### Issue: No knowledge sharing

**Cause**: Agents not using SDK tools
**Solution**: Check agents extend `SDLCPersonaAgent`

```python
class MyAgent(SDLCPersonaAgent):  # ✅ Correct
    ...
```

---

## 📊 Performance Tips

### 1. Run Phases in Parallel Days

**Efficient**:
```bash
# Day 1 AM: Foundation
python3.11 enhanced_sdlc_engine.py --requirement "..." --phases foundation

# Day 1 PM: Implementation
python3.11 enhanced_sdlc_engine.py --resume ... --phases implementation

# Day 2: QA + Deployment
python3.11 enhanced_sdlc_engine.py --resume ... --auto-complete
```

---

### 2. Use Auto-Complete for Remaining Work

```bash
# Instead of manually specifying remaining phases
python3.11 enhanced_sdlc_engine.py --resume blog_v1 --auto-complete
```

---

### 3. Skip Unnecessary Phases

For **documentation-only updates**:
```bash
--phases deployment  # Only runs DevOps + Tech Writer
```

For **code-only projects**:
```bash
--phases foundation implementation qa  # Skip deployment
```

---

## 🎯 Advanced Usage

### Custom Phase Order

```bash
# Foundation first
python3.11 enhanced_sdlc_engine.py \
    --requirement "..." \
    --phases foundation \
    --session-id proj_v1

# Jump to deployment (if implementation done manually)
python3.11 enhanced_sdlc_engine.py \
    --resume proj_v1 \
    --phases deployment
```

---

### Partial Re-execution

**Delete phase files** and re-run:
```bash
# Remove QA files
rm -rf blog_project/tests/

# Re-run QA phase
python3.11 enhanced_sdlc_engine.py \
    --resume blog_v1 \
    --phases qa
```

---

## 📚 Related Documentation

- **Architecture Analysis**: `SDLC_ENGINE_ANALYSIS.md` - Why enhanced version was needed
- **Feature Comparison**: `ENHANCED_VS_V3_COMPARISON.md` - V3 vs Enhanced
- **SDK Patterns**: `../sdk_patterns/README.md` - Underlying patterns used
- **Original Version**: `autonomous_sdlc_engine_v3_resumable.py` - For reference

---

## 🎉 Summary

Enhanced SDLC Engine provides:
- ✅ **True multi-agent collaboration** via SDK
- ✅ **35% faster execution** with parallel phases
- ✅ **Structured knowledge** management
- ✅ **Inter-agent messaging** for coordination
- ✅ **Session persistence** for resumability
- ✅ **Best practices** with TeamCoordinator + TeamAgent

**Get Started**:
```bash
python3.11 enhanced_sdlc_engine.py \
    --requirement "Your amazing project idea" \
    --output ./my_project
```

**Need Help?** Check `SDLC_ENGINE_ANALYSIS.md` and `ENHANCED_VS_V3_COMPARISON.md`

---

**Last Updated**: 2025-10-04
**Version**: 1.0.0
