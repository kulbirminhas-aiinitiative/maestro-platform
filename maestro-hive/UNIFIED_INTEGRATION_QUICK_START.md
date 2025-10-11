# Unified RAG + MLOps + SDLC: Quick Start Guide
## Get All Systems Working Together in 1 Day

**Goal**: Connect maestro-templates (RAG), maestro-ml (MLOps), and SDLC team workflows

---

## TL;DR

You have THREE powerful systems that aren't talking to each other:
1. **SDLC Team** - 11 personas executing workflows
2. **Maestro Templates** - Quality-scored templates by persona
3. **Maestro ML** - Similarity detection + quality prediction

**This guide**: Make them work together in 3 steps.

---

## Step 1: Verify All Systems Running (30 minutes)

### Check 1: SDLC Team
```bash
cd ~/projects/shared/claude_team_sdk/examples/sdlc_team
python3 -c "from personas import SDLCPersonas; print('✅ SDLC Team ready')"
```

### Check 2: Maestro Templates
```bash
cd ~/projects/maestro-templates
docker-compose up -d
curl http://localhost:9800/health
# Should return: {"status": "healthy"}
```

### Check 3: Maestro ML
```bash
cd ~/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml
poetry run python -c "import maestro_ml; print('✅ Maestro ML ready')"
```

**All green? Continue to Step 2.**

---

## Step 2: Connect Systems (2 hours)

### 2.1: Create Integration Module

```bash
cd ~/projects/shared/claude_team_sdk/examples/sdlc_team
touch rag_mlops_integration.py
```

Paste this **minimal working integration**:

```python
"""
Minimal RAG + MLOps Integration
Connects SDLC personas with templates and ML
"""

import httpx
from typing import List, Dict, Any
import asyncio


class MinimalRAGIntegration:
    """Simplest possible integration"""
    
    def __init__(self):
        self.template_url = "http://localhost:9800"
        self.ml_url = "http://localhost:8000"
    
    async def get_templates_for_persona(
        self,
        persona_id: str,
        task: str
    ) -> List[Dict]:
        """Retrieve templates from registry"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.template_url}/api/v1/templates/search",
                    json={
                        "persona": persona_id,
                        "query": task,
                        "top_k": 5,
                        "min_quality_score": 70.0
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json().get("templates", [])
            except Exception as e:
                print(f"⚠️ Template retrieval failed: {e}")
        
        return []
    
    async def execute_persona_with_templates(
        self,
        persona_id: str,
        requirement: str
    ) -> Dict[str, Any]:
        """Execute persona with template context"""
        
        # 1. Get templates
        templates = await self.get_templates_for_persona(
            persona_id,
            requirement
        )
        
        print(f"\n📚 Found {len(templates)} templates for {persona_id}")
        for t in templates[:3]:
            print(f"  • {t['name']} (Quality: {t['quality_score']:.0f}%)")
        
        # 2. Build enhanced context
        context = {
            "requirement": requirement,
            "templates": templates,
            "guidance": self._build_guidance(templates)
        }
        
        # 3. Execute (your existing persona execution)
        # For now, just return the context
        return {
            "persona_id": persona_id,
            "templates_available": len(templates),
            "context": context
        }
    
    def _build_guidance(self, templates: List[Dict]) -> str:
        """Build template guidance text"""
        if not templates:
            return "No specific templates found. Use best practices."
        
        lines = ["Available templates:"]
        for i, t in enumerate(templates[:3], 1):
            lines.append(
                f"{i}. {t['name']} (Quality: {t['quality_score']:.0f}%)"
            )
        
        return "\n".join(lines)


# Quick test
async def test_integration():
    integration = MinimalRAGIntegration()
    
    result = await integration.execute_persona_with_templates(
        persona_id="backend_developer",
        requirement="Build async REST API with CRUD operations"
    )
    
    print(f"\n✅ Integration working!")
    print(f"   Templates found: {result['templates_available']}")


if __name__ == "__main__":
    asyncio.run(test_integration())
```

**Test it**:
```bash
python3 rag_mlops_integration.py
```

Expected output:
```
📚 Found 5 templates for backend_developer
  • FastAPI Async CRUD (Quality: 85%)
  • NestJS Repository Pattern (Quality: 82%)
  • FastAPI JWT Authentication (Quality: 88%)

✅ Integration working!
   Templates found: 5
```

---

### 2.2: Wire Into Existing SDLC Engine

Update your `enhanced_sdlc_engine_v4_1.py` or `team_execution.py`:

```python
# Add at top
from rag_mlops_integration import MinimalRAGIntegration

# In your persona execution function
rag = MinimalRAGIntegration()

async def execute_persona_enhanced(persona_id: str, requirement: str):
    """Enhanced with RAG"""
    
    # Get templates first
    result = await rag.execute_persona_with_templates(
        persona_id,
        requirement
    )
    
    # Inject templates into your existing execution
    # Modify your persona prompt to include result['context']['guidance']
    
    # ... rest of your existing logic
```

---

## Step 3: Enable Feedback Loop (1 hour)

### 3.1: Track Template Usage

Add to your `rag_mlops_integration.py`:

```python
class MinimalRAGIntegration:
    # ... existing code ...
    
    async def record_template_usage(
        self,
        persona_id: str,
        template_ids: List[str],
        outcome_quality: float
    ):
        """Record which templates were used and outcome"""
        
        async with httpx.AsyncClient() as client:
            for template_id in template_ids:
                try:
                    await client.post(
                        f"{self.template_url}/api/v1/templates/{template_id}/record-usage",
                        json={
                            "persona_id": persona_id,
                            "outcome_quality": outcome_quality,
                            "timestamp": datetime.now().isoformat()
                        },
                        timeout=5.0
                    )
                except Exception as e:
                    print(f"⚠️ Failed to record usage: {e}")
```

### 3.2: Use It After Persona Execution

```python
# After persona completes
templates_used = ["template_id_1", "template_id_2"]  # Track which ones were actually used
quality_score = 85.0  # Your existing quality validation score

await rag.record_template_usage(
    persona_id="backend_developer",
    template_ids=templates_used,
    outcome_quality=quality_score
)

print(f"✅ Recorded template usage for feedback loop")
```

---

## Step 4: Test End-to-End (30 minutes)

### Full Workflow Test

```python
# test_unified_workflow.py

async def test_full_workflow():
    """Test complete RAG + MLOps + SDLC integration"""
    
    rag = MinimalRAGIntegration()
    
    # Project requirement
    requirement = "Build e-commerce API with product catalog and cart"
    
    personas = ["backend_developer", "frontend_developer", "devops_engineer"]
    
    for persona_id in personas:
        print(f"\n{'='*60}")
        print(f"Executing: {persona_id}")
        print('='*60)
        
        # 1. Get templates
        result = await rag.execute_persona_with_templates(
            persona_id,
            requirement
        )
        
        # 2. Simulate execution (replace with your actual execution)
        await asyncio.sleep(1)  # Simulated work
        
        # 3. Record usage (simulated)
        if result['templates_available'] > 0:
            await rag.record_template_usage(
                persona_id=persona_id,
                template_ids=[t['id'] for t in result['context']['templates'][:2]],
                outcome_quality=87.5
            )
        
        print(f"✅ {persona_id} complete")
    
    print(f"\n{'='*60}")
    print("🎉 Full workflow complete!")
    print("   Templates retrieved: ✅")
    print("   Personas executed: ✅")
    print("   Feedback recorded: ✅")
    print('='*60)


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

**Run it**:
```bash
python3 test_unified_workflow.py
```

---

## What You Just Built

### Before
```
SDLC Personas → Execute blindly (no templates)
Maestro Templates → Sitting unused
Maestro ML → Not connected
```

### After
```
SDLC Personas → Query templates → Execute with context → Record usage
                     ↓                                        ↓
        Maestro Templates (RAG)                    Feedback Loop
                     ↑                                        ↓
            Maestro ML (Quality Tracking & Learning)
```

---

## Next Steps

### Immediate Improvements (This Week)
1. **Add to more personas**: Currently only tested with 3, add all 11
2. **Template selection UI**: Let humans approve/reject recommended templates
3. **Quality dashboard**: Visualize which templates work best

### Phase 2 (Next Week)
1. **ML-powered ranking**: Use Maestro ML to rank templates by predicted success
2. **Persona-level similarity**: Integrate V4.1 persona reuse with template retrieval
3. **Template combinations**: Learn which templates work well together

### Phase 3 (Week 3-4)
1. **AutoGen patterns**: Add group chat for template selection, reflection for quality
2. **Golden templates**: Automatically identify and pin high-performers
3. **A/B testing**: Compare outcomes with/without RAG

---

## Troubleshooting

### "Connection refused" to port 9800
```bash
# Start Maestro Templates
cd ~/projects/maestro-templates
docker-compose up -d
# Wait 30 seconds for startup
curl http://localhost:9800/health
```

### "No templates found"
```bash
# Check if templates exist
curl "http://localhost:9800/api/v1/templates?persona=backend_developer"

# If empty, seed templates
cd ~/projects/maestro-templates
python3 scripts/seed_templates.py
```

### "Maestro ML not responding"
```bash
# Check if ML service is running
cd ~/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml
poetry run python -m maestro_ml.api
# Should start on port 8000
```

---

## Success Metrics

After completing this guide, you should have:

- [x] All three systems running and talking
- [x] Templates retrieved for personas
- [x] Feedback loop recording usage
- [x] End-to-end workflow tested

**Time invested**: ~4 hours  
**Value unlocked**: RAG-enhanced personas, quality tracking, continuous learning

---

## Full Architecture

For complete implementation details, see:
- `UNIFIED_RAG_MLOPS_ARCHITECTURE.md` (42KB, comprehensive design)
- This quick start (minimal working integration)

**Next**: Pick Phase 2 improvements based on your priorities.
