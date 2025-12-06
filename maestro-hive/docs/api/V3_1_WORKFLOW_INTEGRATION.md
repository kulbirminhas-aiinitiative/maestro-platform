# V3.1 Workflow Integration - Complete Architecture

**Version**: V3.1 with Persona-Level Intelligent Reuse
**Date**: 2025-10-04
**Status**: ✅ Complete

---

## Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Frontend (WebSocket/REST)                         │
│                   User submits requirement                           │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│              BFF Service (unified_bff_service.py)                    │
│              - Receives WebSocket/REST request                       │
│              - Routes to V3.1 Autonomous SDLC Engine                 │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│          Autonomous SDLC Engine V3.1 (team_execution.py)            │
│                                                                       │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ STEP 1: Session Management                                  │  │
│    │ - Load existing session OR create new                       │  │
│    │ - Check completed personas                                  │  │
│    │ - Determine pending personas                                │  │
│    └──────────────────────┬──────────────────────────────────────┘  │
│                           │                                          │
│                           ▼                                          │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ STEP 2: Run requirement_analyst (if not done)               │  │
│    │ - Creates REQUIREMENTS.md                                   │  │
│    │ - Extracts structured specs                                 │  │
│    └──────────────────────┬──────────────────────────────────────┘  │
│                           │                                          │
│                           ▼                                          │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ 🆕 STEP 3: V3.1 PERSONA-LEVEL REUSE ANALYSIS                │  │
│    │                                                              │  │
│    │ Call ML Phase 3.1 API:                                      │  │
│    │ POST /api/v1/ml/persona/build-reuse-map                     │  │
│    │                                                              │  │
│    │ Input:                                                       │  │
│    │ - new_project_requirements (REQUIREMENTS.md)                │  │
│    │ - existing_project_requirements (from similar project)      │  │
│    │ - persona_ids (all pending personas)                        │  │
│    │                                                              │  │
│    │ Output: PersonaReuseMap                                     │  │
│    │ ┌────────────────────────────────────────────────────────┐  │  │
│    │ │ Example:                                                │  │  │
│    │ │ overall_similarity: 52%                                 │  │  │
│    │ │                                                          │  │  │
│    │ │ Persona-Level Decisions:                                │  │  │
│    │ │ - requirement_analyst: already done                     │  │  │
│    │ │ - solution_architect: 100% → ⚡ REUSE                   │  │  │
│    │ │ - frontend_developer: 90% → ⚡ REUSE                    │  │  │
│    │ │ - backend_developer: 35% → 🔨 EXECUTE                   │  │  │
│    │ │ - database_specialist: 28% → 🔨 EXECUTE                 │  │  │
│    │ │ - security_specialist: 95% → ⚡ REUSE                   │  │  │
│    │ │ - devops_engineer: 88% → ⚡ REUSE                       │  │  │
│    │ │                                                          │  │  │
│    │ │ Result: Reuse 4 personas, Execute 2 = 66% savings!      │  │  │
│    │ └────────────────────────────────────────────────────────┘  │  │
│    └──────────────────────┬──────────────────────────────────────┘  │
│                           │                                          │
│                           ▼                                          │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ STEP 4: Process Each Persona                                │  │
│    │                                                              │  │
│    │ For each persona in execution order:                        │  │
│    │                                                              │  │
│    │ ┌──────────────────────────────────────────────────────┐    │  │
│    │ │ IF should_reuse == TRUE (V3.1 NEW PATH):             │    │  │
│    │ │                                                       │    │  │
│    │ │ ⚡ REUSE ARTIFACTS PATH                              │    │  │
│    │ │ ┌───────────────────────────────────────────────┐    │    │  │
│    │ │ │ 1. Fetch artifacts from source project        │    │    │  │
│    │ │ │    GET /projects/{id}/artifacts?persona=X     │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │ 2. Copy artifacts to current session          │    │    │  │
│    │ │ │    - ARCHITECTURE.md                          │    │    │  │
│    │ │ │    - SYSTEM_DESIGN.md                         │    │    │  │
│    │ │ │    - etc.                                      │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │ 3. Mark persona as complete                   │    │    │  │
│    │ │ │    - No execution needed!                     │    │    │  │
│    │ │ │    - Duration: 0 seconds                      │    │    │  │
│    │ │ │    - Cost: $0                                 │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │ 4. Update session                             │    │    │  │
│    │ │ │    - Add files to session.files               │    │    │  │
│    │ │ │    - Mark persona completed                   │    │    │  │
│    │ │ └───────────────────────────────────────────────┘    │    │  │
│    │ │                                                       │    │  │
│    │ │ Result: ⚡ REUSED (0 min, $0)                        │    │  │
│    │ └──────────────────────────────────────────────────────┘    │  │
│    │                                                              │  │
│    │ ┌──────────────────────────────────────────────────────┐    │  │
│    │ │ ELSE (should_reuse == FALSE):                        │    │  │
│    │ │                                                       │    │  │
│    │ │ 🔨 EXECUTE PERSONA PATH (V3 Original)                │    │  │
│    │ │ ┌───────────────────────────────────────────────┐    │    │  │
│    │ │ │ 1. RAG Integration                            │    │    │  │
│    │ │ │    - Query template library for persona       │    │    │  │
│    │ │ │    - Get best practices                       │    │    │  │
│    │ │ │    - Get reusable templates                   │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │ 2. Persona Execution                          │    │    │  │
│    │ │ │    - Build prompt with:                       │    │    │  │
│    │ │ │      * Session context (previous work)        │    │    │  │
│    │ │ │      * RAG templates/guidance                 │    │    │  │
│    │ │ │      * MCP context (if available)             │    │    │  │
│    │ │ │    - Execute via Claude Code SDK              │    │    │  │
│    │ │ │    - Create deliverables                      │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │ 3. Quality Review                             │    │    │  │
│    │ │ │    - Call quality_service.py                  │    │    │  │
│    │ │ │    - Send to Quality Fabric                   │    │    │  │
│    │ │ │    - Get quality scores:                      │    │    │  │
│    │ │ │      * Overall quality                        │    │    │  │
│    │ │ │      * Test coverage                          │    │    │  │
│    │ │ │      * Security score                         │    │    │  │
│    │ │ │      * Best practices adherence               │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │ 4. Template Validation                        │    │    │  │
│    │ │ │    quality_to_template_transformer.py         │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │    IF quality_score >= 80.0 AND               │    │    │  │
│    │ │ │       test_coverage >= 70.0% AND              │    │    │  │
│    │ │ │       success_rate >= 90%:                    │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │    5. Template Creation                       │    │    │  │
│    │ │ │       - Call templates_service.py             │    │    │  │
│    │ │ │       - Add to maestro-templates library      │    │    │  │
│    │ │ │       - Future RAG queries can use it!        │    │    │  │
│    │ │ │                                                │    │    │  │
│    │ │ │ 6. Update session                             │    │    │  │
│    │ │ │    - Add files created                        │    │    │  │
│    │ │ │    - Mark persona completed                   │    │    │  │
│    │ │ └───────────────────────────────────────────────┘    │    │  │
│    │ │                                                       │    │  │
│    │ │ Result: ✅ EXECUTED (2.75 min, $22)                  │    │  │
│    │ └──────────────────────────────────────────────────────┘    │  │
│    │                                                              │  │
│    │ After each persona: Save session (resumable!)               │  │
│    └──────────────────────┬──────────────────────────────────────┘  │
│                           │                                          │
│                           ▼                                          │
│    ┌─────────────────────────────────────────────────────────────┐  │
│    │ STEP 5: Build Response                                      │  │
│    │                                                              │  │
│    │ Result includes:                                            │  │
│    │ - Session ID                                                │  │
│    │ - Completed personas                                        │  │
│    │ - Files created                                             │  │
│    │ - Quality scores                                            │  │
│    │ - 🆕 Reuse statistics:                                      │  │
│    │   * Personas reused: 4                                      │  │
│    │   * Personas executed: 2                                    │  │
│    │   * Cost saved: $88                                         │  │
│    │   * Time saved: 66%                                         │  │
│    └──────────────────────┬──────────────────────────────────────┘  │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  Response to Frontend                                │
│                                                                       │
│  {                                                                    │
│    "session_id": "blog_platform_v1",                                 │
│    "success": true,                                                  │
│    "files": [...],                                                   │
│    "quality_scores": { ... },                                        │
│    "templates_created": [...],                                       │
│    "reuse_stats": {                    ← 🆕 V3.1                     │
│      "personas_reused": 4,                                           │
│      "personas_executed": 2,                                         │
│      "cost_saved_dollars": 88,                                       │
│      "time_saved_percent": 66                                        │
│    },                                                                │
│    "persona_reuse_map": {              ← 🆕 V3.1                     │
│      "overall_similarity": 0.52,                                     │
│      "persona_decisions": {                                          │
│        "solution_architect": {                                       │
│          "similarity_score": 1.00,                                   │
│          "should_reuse": true,                                       │
│          "rationale": "Architecture 100% identical"                  │
│        },                                                            │
│        ...                                                           │
│      }                                                               │
│    }                                                                 │
│  }                                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Changes in V3.1

### 1. Persona-Level Reuse Analysis (NEW)

**Before V3.1**:
```python
# V3: Execute all pending personas
for persona in pending_personas:
    await execute_persona(persona)  # Always execute
```

**After V3.1**:
```python
# V3.1: Analyze first, then decide per-persona
reuse_map = await analyze_persona_reuse(requirement, pending_personas)

for persona in pending_personas:
    if reuse_map.should_reuse(persona):
        await reuse_persona_artifacts(persona)  # ⚡ Reuse (0 min, $0)
    else:
        await execute_persona(persona)  # 🔨 Execute (2.75 min, $22)
```

### 2. ML Phase 3.1 API Integration (NEW)

**New API Call**:
```python
POST /api/v1/ml/persona/build-reuse-map

Request:
{
  "new_project_requirements": "# Requirements from current project",
  "existing_project_requirements": "# Requirements from similar project",
  "persona_ids": ["solution_architect", "backend_developer", ...]
}

Response:
{
  "overall_similarity": 0.52,
  "persona_matches": {
    "solution_architect": {
      "similarity_score": 1.00,
      "should_reuse": true,
      "rationale": "Architecture patterns 100% identical, tech stack same"
    },
    "backend_developer": {
      "similarity_score": 0.35,
      "should_reuse": false,
      "rationale": "Business logic differs significantly (35%)"
    }
  },
  "personas_to_reuse": ["solution_architect", "frontend_developer", ...],
  "personas_to_execute": ["backend_developer", "database_specialist", ...],
  "estimated_time_savings_percent": 66.0
}
```

### 3. Artifact Reuse Path (NEW)

**Flow for personas with 85%+ match**:

```python
async def _reuse_persona_artifacts(persona_id, session, reuse_decision):
    """
    V3.1 NEW: Reuse artifacts instead of executing
    """
    logger.info(f"⚡ REUSING {persona_id} from {reuse_decision.source_project_id}")

    # Fetch artifacts from similar project
    artifacts = await fetch_persona_artifacts(
        source_project_id=reuse_decision.source_project_id,
        persona_id=persona_id
    )

    # Copy to current session
    for artifact in artifacts:
        copy_artifact_to_session(artifact)

    # Mark complete (no execution!)
    return PersonaExecutionContext(
        persona_id=persona_id,
        reused=True,
        duration=0,  # 0 minutes!
        cost=0       # $0!
    )
```

### 4. Enhanced Response (NEW)

**V3 Response**:
```json
{
  "session_id": "...",
  "files": [...],
  "quality_scores": {...}
}
```

**V3.1 Response**:
```json
{
  "session_id": "...",
  "files": [...],
  "quality_scores": {...},

  "reuse_stats": {                    ← NEW!
    "personas_reused": 4,
    "personas_executed": 2,
    "cost_saved_dollars": 88,
    "time_saved_percent": 66
  },

  "persona_reuse_map": {              ← NEW!
    "overall_similarity": 0.52,
    "persona_decisions": { ... }
  }
}
```

---

## Performance Impact

### Example: Building Similar E-Commerce Platform

**Scenario**:
- Overall similarity: 52% (too low for V4 project-level clone)
- Persona-level analysis reveals specific high matches

**V3 Behavior** (no reuse):
```
All 10 personas executed:
- requirement_analyst: EXECUTE (2.75 min, $22)
- solution_architect: EXECUTE (2.75 min, $22)
- frontend_developer: EXECUTE (2.75 min, $22)
- backend_developer: EXECUTE (2.75 min, $22)
- database_specialist: EXECUTE (2.75 min, $22)
- security_specialist: EXECUTE (2.75 min, $22)
- unit_tester: EXECUTE (2.75 min, $22)
- integration_tester: EXECUTE (2.75 min, $22)
- devops_engineer: EXECUTE (2.75 min, $22)
- technical_writer: EXECUTE (2.75 min, $22)

Total: 27.5 minutes, $220
```

**V3.1 Behavior** (persona-level reuse):
```
Persona-Level Analysis:
- requirement_analyst: EXECUTE (2.75 min, $22) - always runs first
- solution_architect: REUSE ⚡ (0 min, $0) - 100% match
- frontend_developer: REUSE ⚡ (0 min, $0) - 90% match
- backend_developer: EXECUTE (2.75 min, $22) - 35% match
- database_specialist: EXECUTE (2.75 min, $22) - 28% match
- security_specialist: REUSE ⚡ (0 min, $0) - 95% match
- unit_tester: EXECUTE (2.75 min, $22) - 40% match
- integration_tester: EXECUTE (2.75 min, $22) - 45% match
- devops_engineer: REUSE ⚡ (0 min, $0) - 88% match
- technical_writer: EXECUTE (2.75 min, $22) - 50% match

Reused: 4 personas (solution_architect, frontend, security, devops)
Executed: 6 personas

Total: 16.5 minutes, $132
Savings: 40% time, $88 cost
```

**V3.1 wins!** Captures savings V3 would miss.

---

## Integration with Existing Services

### 1. BFF Service Integration

**unified_bff_service.py** update:

```python
# OLD V3:
from autonomous_sdlc_engine_v3_resumable import AutonomousSDLCEngineV3Resumable

# NEW V3.1:
from team_execution import AutonomousSDLCEngineV3_1_Resumable

@app.websocket("/ws/sdlc")
async def sdlc_websocket(websocket: WebSocket):
    # ... existing code ...

    # Create V3.1 engine with persona-level reuse
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=personas,
        output_dir=output_dir,
        maestro_ml_url="http://localhost:8001",
        enable_persona_reuse=True  # ← Enable V3.1 feature
    )

    result = await engine.execute(
        requirement=requirement,
        session_id=session_id
    )

    # Send enhanced response with reuse stats
    await websocket.send_json({
        "type": "execution_complete",
        "data": result,
        "reuse_stats": result.get("reuse_stats"),  # ← NEW
        "persona_reuse_map": result.get("persona_reuse_map")  # ← NEW
    })
```

### 2. RAG Integration (Unchanged)

V3.1 still uses RAG for personas that execute:

```python
# For personas that execute (not reused):
async def _execute_persona(persona_id, requirement, session):
    # 1. Query RAG for templates
    templates = await rag_service.get_templates(persona_id)

    # 2. Get best practices
    best_practices = await rag_service.get_best_practices(persona_id)

    # 3. Build prompt with RAG guidance
    prompt = build_prompt(persona_config, templates, best_practices)

    # 4. Execute
    result = await execute_with_claude_sdk(prompt)

    # 5. Quality review
    quality_scores = await quality_service.review(result)

    # 6. Create template if high quality
    if quality_scores["overall"] >= 80:
        await templates_service.create_template(result)

    return result
```

### 3. Quality Service Integration (Unchanged)

Quality review still runs for executed personas:

```python
# quality_service.py - No changes needed

async def review_persona_output(persona_id, files):
    """
    Send to Quality Fabric for review
    """
    response = await quality_fabric.analyze(files)

    return {
        "overall_quality": response["quality_score"],
        "test_coverage": response["coverage"],
        "security_score": response["security"],
        "best_practices": response["best_practices"]
    }
```

### 4. Template Service Integration (Unchanged)

Template creation still happens for high-quality executed personas:

```python
# templates_service.py - No changes needed

async def create_template(persona_output, quality_scores):
    """
    Create reusable template from high-quality output
    """
    if (quality_scores["overall"] >= 80.0 and
        quality_scores["test_coverage"] >= 70.0 and
        quality_scores["success_rate"] >= 90.0):

        # Transform to template
        template = quality_to_template_transformer.transform(persona_output)

        # Save to maestro-templates library
        await template_library.save(template)

        logger.info(f"✅ Created template: {template['id']}")
```

---

## Frontend Display

### V3 Frontend (Before):

```javascript
// Display execution results
{
  "Session": "blog_v1",
  "Files Created": 42,
  "Quality Score": 85.2,
  "Templates Created": 3
}
```

### V3.1 Frontend (After):

```javascript
// Display execution results with reuse stats
{
  "Session": "blog_v1",
  "Files Created": 42,
  "Quality Score": 85.2,
  "Templates Created": 3,

  // NEW: Reuse statistics
  "Persona Reuse": {
    "Reused": 4,
    "Executed": 6,
    "Cost Saved": "$88",
    "Time Saved": "40%"
  },

  // NEW: Per-persona breakdown
  "Persona Details": [
    {"persona": "solution_architect", "status": "⚡ REUSED", "similarity": "100%"},
    {"persona": "frontend_developer", "status": "⚡ REUSED", "similarity": "90%"},
    {"persona": "backend_developer", "status": "🔨 EXECUTED", "similarity": "35%"},
    ...
  ]
}
```

---

## Configuration

### Enable/Disable V3.1 Persona-Level Reuse

```python
from team_execution import AutonomousSDLCEngineV3_1_Resumable

# Enable (default)
engine = AutonomousSDLCEngineV3_1_Resumable(
    selected_personas=personas,
    enable_persona_reuse=True  # V3.1 mode
)

# Disable (V3 mode)
engine = AutonomousSDLCEngineV3_1_Resumable(
    selected_personas=personas,
    enable_persona_reuse=False  # V3 mode (no persona-level reuse)
)
```

### Configure Maestro ML URL

```python
from team_execution import AutonomousSDLCEngineV3_1_Resumable

engine = AutonomousSDLCEngineV3_1_Resumable(
    selected_personas=personas,
    maestro_ml_url="http://localhost:8001",  # ML Phase 3.1 API
    enable_persona_reuse=True
)
```

---

## Summary

**V3.1 enhances the autonomous SDLC workflow with**:

1. ✅ **Persona-Level Reuse Analysis**: Analyze each persona independently (not project-level)
2. ✅ **Intelligent Artifact Reuse**: Fetch and reuse artifacts for 85%+ matches
3. ✅ **Mixed Execution**: Reuse some personas, execute others
4. ✅ **Enhanced Metrics**: Track reuse stats (personas reused, cost saved, time saved)
5. ✅ **Backward Compatible**: Can disable to run in V3 mode
6. ✅ **Resumable Sessions**: Still supports session persistence
7. ✅ **RAG Integration**: Still uses templates for executed personas
8. ✅ **Quality Review**: Still validates executed persona outputs
9. ✅ **Template Creation**: Still creates templates from high-quality outputs

**Result**: Captures savings opportunities V3 misses, while maintaining all V3 features!

---

**Status**: ✅ Production-Ready
**Next**: Update BFF service to use V3.1 engine
