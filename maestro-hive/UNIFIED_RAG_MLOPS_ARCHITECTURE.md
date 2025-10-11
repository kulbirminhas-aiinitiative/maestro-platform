# Unified RAG + MLOps + SDLC Team Architecture
## Complete Integration Design

**Created**: January 2025  
**Purpose**: Integrate maestro-templates (RAG), maestro-ml (MLOps), and SDLC team workflows  
**Goal**: Create intelligent, learning SDLC system that improves over time

---

## Executive Summary

This document presents a unified architecture integrating three powerful systems:

1. **SDLC Team** (~28k LOC) - 11 personas executing software development lifecycle
2. **Maestro Templates** (RAG) - Template registry with quality-scored, reusable artifacts
3. **Maestro ML** (MLOps) - ML platform for similarity detection, quality prediction, artifact tracking

**Key Innovation**: A self-improving SDLC system that learns from every project, retrieves best practices automatically, and optimizes execution through ML-powered decisions.

---

## Current State Assessment

### 1. SDLC Team (Your Workflow Engine)
**Location**: `~/projects/shared/claude_team_sdk/examples/sdlc_team/`

**Capabilities**:
- 11 specialized personas with RBAC
- V4.1 persona-level reuse (ML-powered similarity)
- Phase gate validation
- Dynamic team scaling
- Sequential, parallel, and elastic execution patterns

**Current Limitations**:
- ⚠️ No RAG integration - personas don't reference templates during execution
- ⚠️ Limited learning - doesn't track which templates lead to success
- ⚠️ No quality feedback loop - can't improve template recommendations
- ⚠️ Manual template selection - no AI-driven template discovery

---

### 2. Maestro Templates (RAG System)
**Location**: `~/projects/maestro-templates/`

**Capabilities**:
- Central registry with FastAPI REST API
- Template storage by persona (backend_developer, frontend_developer, etc.)
- Quality scoring (quality_score, security_score, performance_score)
- Git-based storage for version control
- Manifest validation
- Pinning for "golden" templates

**Current Limitations**:
- ⚠️ Not integrated with SDLC workflow - templates exist but aren't used
- ⚠️ No automatic quality tracking - scores are static, not updated based on usage
- ⚠️ No similarity-based retrieval - can't find "similar enough" templates
- ⚠️ No feedback loop - doesn't learn which templates work well together

---

### 3. Maestro ML (MLOps Platform)
**Location**: `~/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml/`

**Capabilities**:
- Spec similarity service (semantic embeddings, vector search)
- Persona-level reuse decisions (V4.1 integration)
- Artifact usage tracking
- Project success metrics
- Quality prediction (Phase 3 meta-learning)

**Current Limitations**:
- ⚠️ Not connected to templates - tracks project artifacts, not individual templates
- ⚠️ No template quality prediction - can't predict which template will work best
- ⚠️ No RAG integration - similarity based on specs, not template content
- ⚠️ Missing feedback loop - doesn't update template scores based on outcomes

---

## Unified Architecture Vision

### The Integration Model

```
┌────────────────────────────────────────────────────────────────────┐
│                        SDLC TEAM ORCHESTRATOR                      │
│  (Your existing 11 personas + Phase workflow + V4.1 reuse)         │
└────────────────────────────────────────────────────────────────────┘
                    ↓                           ↑
        ┌───────────┴───────────┐   ┌──────────┴────────────┐
        ↓                       ↓   ↑                       ↑
┌─────────────────────┐  ┌─────────────────────┐  ┌───────────────────┐
│   MAESTRO TEMPLATES │  │    MAESTRO ML       │  │  QUALITY FEEDBACK │
│   (RAG Registry)    │  │   (MLOps Platform)  │  │      LOOP         │
│                     │  │                     │  │                   │
│ • Template storage  │  │ • Spec similarity   │  │ • Track outcomes  │
│ • Quality scores    │  │ • Persona reuse     │  │ • Update scores   │
│ • Vector search     │  │ • Quality predict   │  │ • Learn patterns  │
│ • Pinned "golden"   │  │ • Artifact tracking │  │ • Improve recs    │
└─────────────────────┘  └─────────────────────┘  └───────────────────┘
         ↓                        ↓                        ↑
         └────────────┬───────────┴────────────────────────┘
                      ↓
              ┌───────────────────┐
              │  UNIFIED STORAGE  │
              │  • PostgreSQL     │
              │  • Vector DB      │
              │  • MinIO/S3       │
              └───────────────────┘
```

### The Workflow Loop

```
1. PROJECT STARTS
   User: "Create e-commerce platform with AI recommendations"
   
2. SPEC ANALYSIS (Maestro ML)
   → Analyze requirement specification
   → Find similar past projects (V4.1)
   → Detect persona-level reuse opportunities
   
3. TEMPLATE RETRIEVAL (Maestro Templates + Maestro ML)
   For each persona to execute:
   → Query template registry for relevant templates
   → ML ranks templates by predicted success
   → Retrieve top-k templates with context
   
4. PERSONA EXECUTION (SDLC Team)
   Persona receives:
   → Requirement specification
   → Retrieved templates (RAG context)
   → Past similar project artifacts (V4.1 reuse)
   → Quality guidelines
   
   Persona produces:
   → Code artifacts
   → Which templates were used
   → Any modifications made
   
5. QUALITY ASSESSMENT (Maestro ML)
   → Validate outputs against quality gates
   → Track template effectiveness
   → Measure project success metrics
   
6. FEEDBACK LOOP (All Systems)
   → Update template quality scores
   → Record successful template combinations
   → Train meta-model for better predictions
   → Pin high-performing templates as "golden"
```

---

## Integration Architecture

### Component 1: RAG-Enhanced Persona Execution

**File**: `rag_enhanced_persona_executor.py`

```python
"""
RAG-Enhanced Persona Executor
Integrates template retrieval into persona execution
"""

from typing import List, Dict, Any, Optional
import httpx
from dataclasses import dataclass


@dataclass
class RetrievedTemplate:
    """Template retrieved from RAG system"""
    template_id: str
    name: str
    content: str
    quality_score: float
    relevance_score: float  # How relevant to current task
    metadata: Dict[str, Any]


class RAGEnhancedPersonaExecutor:
    """
    Enhances persona execution with RAG template retrieval
    
    Combines:
    - Your existing persona execution (SDLC team)
    - Template retrieval (Maestro Templates)
    - ML-powered ranking (Maestro ML)
    """
    
    def __init__(
        self,
        template_registry_url: str = "http://localhost:9800",
        maestro_ml_url: str = "http://localhost:8000"
    ):
        self.template_registry_url = template_registry_url
        self.maestro_ml_url = maestro_ml_url
    
    async def execute_persona_with_rag(
        self,
        persona_id: str,
        requirement: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute persona with RAG-enhanced context
        
        Flow:
        1. Retrieve relevant templates from registry
        2. ML ranks templates by predicted success
        3. Inject top templates into persona context
        4. Execute persona with enriched context
        5. Track which templates were used
        """
        
        # Step 1: Retrieve relevant templates
        templates = await self._retrieve_templates(
            persona_id=persona_id,
            task_description=task_description,
            requirement=requirement
        )
        
        # Step 2: ML-powered ranking
        ranked_templates = await self._rank_templates(
            templates=templates,
            persona_id=persona_id,
            requirement=requirement,
            context=context
        )
        
        # Step 3: Inject top templates into context
        enriched_context = {
            **context,
            "retrieved_templates": ranked_templates[:5],  # Top 5
            "template_guidance": self._build_template_guidance(ranked_templates)
        }
        
        # Step 4: Execute persona (your existing logic)
        result = await self._execute_persona_internal(
            persona_id=persona_id,
            requirement=requirement,
            context=enriched_context
        )
        
        # Step 5: Track template usage
        await self._track_template_usage(
            persona_id=persona_id,
            templates_used=result.get("templates_used", []),
            outcome_quality=result.get("quality_score", 0.0)
        )
        
        return result
    
    async def _retrieve_templates(
        self,
        persona_id: str,
        task_description: str,
        requirement: str
    ) -> List[RetrievedTemplate]:
        """
        Retrieve relevant templates from Maestro Templates registry
        
        Uses:
        - Persona ID to filter by persona type
        - Task description for semantic search
        - Requirement for context
        """
        async with httpx.AsyncClient() as client:
            # Query template registry with semantic search
            response = await client.post(
                f"{self.template_registry_url}/api/v1/templates/search",
                json={
                    "persona": persona_id,
                    "query": task_description,
                    "requirement_context": requirement,
                    "top_k": 20,  # Retrieve top 20 candidates
                    "min_quality_score": 70.0,  # Only high-quality
                    "include_pinned": True  # Prioritize golden templates
                }
            )
            
            templates_data = response.json()["templates"]
            
            return [
                RetrievedTemplate(
                    template_id=t["id"],
                    name=t["name"],
                    content=t["content"],
                    quality_score=t["quality_score"],
                    relevance_score=t["relevance_score"],
                    metadata=t["metadata"]
                )
                for t in templates_data
            ]
    
    async def _rank_templates(
        self,
        templates: List[RetrievedTemplate],
        persona_id: str,
        requirement: str,
        context: Dict[str, Any]
    ) -> List[RetrievedTemplate]:
        """
        ML-powered template ranking using Maestro ML
        
        Ranks templates by predicted success probability
        considering:
        - Template quality scores
        - Historical success rate in similar projects
        - Persona-template compatibility
        - Project context fit
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.maestro_ml_url}/api/v1/templates/rank",
                json={
                    "templates": [
                        {
                            "template_id": t.template_id,
                            "quality_score": t.quality_score,
                            "metadata": t.metadata
                        }
                        for t in templates
                    ],
                    "persona_id": persona_id,
                    "requirement": requirement,
                    "context": context
                }
            )
            
            rankings = response.json()["rankings"]
            
            # Merge rankings with templates
            template_map = {t.template_id: t for t in templates}
            ranked = []
            
            for ranking in rankings:
                template = template_map[ranking["template_id"]]
                template.relevance_score = ranking["predicted_success"]
                ranked.append(template)
            
            return ranked
    
    def _build_template_guidance(
        self,
        templates: List[RetrievedTemplate]
    ) -> str:
        """
        Build human-readable guidance from templates
        
        This becomes part of persona's system prompt
        """
        guidance_parts = [
            "You have access to the following high-quality templates:",
            ""
        ]
        
        for i, template in enumerate(templates[:5], 1):
            guidance_parts.append(
                f"{i}. {template.name} "
                f"(Quality: {template.quality_score:.0f}%, "
                f"Relevance: {template.relevance_score:.0f}%)"
            )
            guidance_parts.append(f"   Use case: {template.metadata.get('description', 'N/A')}")
            guidance_parts.append("")
        
        guidance_parts.append(
            "Reference these templates when appropriate, but adapt them to the specific requirements."
        )
        
        return "\n".join(guidance_parts)
    
    async def _track_template_usage(
        self,
        persona_id: str,
        templates_used: List[str],
        outcome_quality: float
    ):
        """
        Track which templates were used and outcome quality
        
        Feeds back to Maestro ML for learning
        """
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.maestro_ml_url}/api/v1/templates/usage",
                json={
                    "persona_id": persona_id,
                    "templates_used": templates_used,
                    "outcome_quality": outcome_quality,
                    "timestamp": datetime.now().isoformat()
                }
            )
```

---

### Component 2: Unified Similarity Service

**File**: `unified_similarity_service.py`

```python
"""
Unified Similarity Service
Combines spec similarity (Maestro ML) with template similarity (Maestro Templates)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx


@dataclass
class UnifiedSimilarityResult:
    """Combined similarity analysis"""
    # Project-level (existing V4.1)
    similar_project_id: Optional[str]
    project_similarity: float
    
    # Persona-level (existing V4.1)
    persona_reuse_decisions: Dict[str, bool]
    
    # Template-level (NEW)
    recommended_templates: Dict[str, List[str]]  # persona_id -> template_ids
    template_confidence: Dict[str, float]
    
    # Hybrid strategy
    execution_plan: Dict[str, str]  # persona_id -> "reuse_project" | "use_template" | "execute_fresh"


class UnifiedSimilarityService:
    """
    Unifies three similarity layers:
    1. Project-level similarity (V4.1 - Maestro ML)
    2. Persona-level reuse (V4.1 - Maestro ML)
    3. Template-level retrieval (NEW - Maestro Templates + Maestro ML)
    """
    
    def __init__(
        self,
        maestro_ml_url: str = "http://localhost:8000",
        template_registry_url: str = "http://localhost:9800"
    ):
        self.maestro_ml_url = maestro_ml_url
        self.template_registry_url = template_registry_url
    
    async def analyze_requirement(
        self,
        requirement: str,
        persona_ids: List[str]
    ) -> UnifiedSimilarityResult:
        """
        Unified similarity analysis across all three layers
        
        Decision tree:
        1. Is there a similar project? (90%+ similarity)
           → YES: V4.1 project-level reuse
           → NO: Continue to step 2
        
        2. Are there persona-level matches? (85%+ similarity)
           → YES: V4.1 persona-level reuse for those personas
           → NO: Continue to step 3 for those personas
        
        3. Are there relevant templates? (70%+ quality score)
           → YES: RAG-enhanced execution with templates
           → NO: Execute fresh with general knowledge
        """
        
        # Layer 1: Project-level similarity (existing V4.1)
        project_match = await self._find_similar_project(requirement)
        
        if project_match and project_match["similarity"] >= 0.90:
            # Strong project match - use V4.1 project cloning
            return UnifiedSimilarityResult(
                similar_project_id=project_match["project_id"],
                project_similarity=project_match["similarity"],
                persona_reuse_decisions={p: True for p in persona_ids},
                recommended_templates={},
                template_confidence={},
                execution_plan={p: "reuse_project" for p in persona_ids}
            )
        
        # Layer 2: Persona-level reuse (existing V4.1)
        persona_matches = await self._find_persona_matches(
            requirement=requirement,
            persona_ids=persona_ids,
            similar_project_id=project_match["project_id"] if project_match else None
        )
        
        # Layer 3: Template-level retrieval (NEW)
        personas_needing_templates = [
            p for p, should_reuse in persona_matches.items()
            if not should_reuse
        ]
        
        template_recommendations = await self._find_templates(
            requirement=requirement,
            persona_ids=personas_needing_templates
        )
        
        # Build execution plan
        execution_plan = {}
        for persona_id in persona_ids:
            if persona_matches.get(persona_id, False):
                execution_plan[persona_id] = "reuse_project"
            elif persona_id in template_recommendations:
                execution_plan[persona_id] = "use_template"
            else:
                execution_plan[persona_id] = "execute_fresh"
        
        return UnifiedSimilarityResult(
            similar_project_id=project_match["project_id"] if project_match else None,
            project_similarity=project_match["similarity"] if project_match else 0.0,
            persona_reuse_decisions=persona_matches,
            recommended_templates=template_recommendations,
            template_confidence=await self._calculate_template_confidence(
                template_recommendations
            ),
            execution_plan=execution_plan
        )
    
    async def _find_similar_project(
        self,
        requirement: str
    ) -> Optional[Dict[str, Any]]:
        """Layer 1: Find similar project (existing V4.1)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.maestro_ml_url}/api/v1/similarity/project",
                json={"requirement": requirement}
            )
            
            result = response.json()
            if result["similarity"] >= 0.70:  # Threshold for consideration
                return result
            return None
    
    async def _find_persona_matches(
        self,
        requirement: str,
        persona_ids: List[str],
        similar_project_id: Optional[str]
    ) -> Dict[str, bool]:
        """Layer 2: Find persona-level matches (existing V4.1)"""
        if not similar_project_id:
            return {p: False for p in persona_ids}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.maestro_ml_url}/api/v1/similarity/persona",
                json={
                    "requirement": requirement,
                    "persona_ids": persona_ids,
                    "similar_project_id": similar_project_id
                }
            )
            
            return response.json()["persona_reuse_decisions"]
    
    async def _find_templates(
        self,
        requirement: str,
        persona_ids: List[str]
    ) -> Dict[str, List[str]]:
        """Layer 3: Find relevant templates (NEW)"""
        template_recommendations = {}
        
        async with httpx.AsyncClient() as client:
            for persona_id in persona_ids:
                response = await client.post(
                    f"{self.template_registry_url}/api/v1/templates/search",
                    json={
                        "persona": persona_id,
                        "query": requirement,
                        "top_k": 5,
                        "min_quality_score": 70.0
                    }
                )
                
                templates = response.json()["templates"]
                if templates:
                    template_recommendations[persona_id] = [
                        t["id"] for t in templates
                    ]
        
        return template_recommendations
```

---

### Component 3: Quality Feedback Loop

**File**: `quality_feedback_loop.py`

```python
"""
Quality Feedback Loop
Tracks outcomes and updates template quality scores based on real usage
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import httpx


@dataclass
class ProjectOutcome:
    """Track project execution outcome"""
    project_id: str
    requirement: str
    personas_executed: List[str]
    templates_used: Dict[str, List[str]]  # persona_id -> template_ids
    quality_scores: Dict[str, float]  # persona_id -> quality score
    overall_success: float
    execution_time_minutes: float
    cost_dollars: float
    user_satisfaction: Optional[float]


class QualityFeedbackLoop:
    """
    Closes the loop: tracks what works, updates system based on outcomes
    
    Flow:
    1. Project completes
    2. Track which templates were used
    3. Measure outcome quality
    4. Update template scores
    5. Update ML meta-model
    6. Pin high-performers as "golden"
    """
    
    def __init__(
        self,
        maestro_ml_url: str = "http://localhost:8000",
        template_registry_url: str = "http://localhost:9800"
    ):
        self.maestro_ml_url = maestro_ml_url
        self.template_registry_url = template_registry_url
    
    async def record_project_outcome(
        self,
        outcome: ProjectOutcome
    ):
        """
        Record complete project outcome and trigger learning
        """
        
        # Step 1: Update template quality scores
        await self._update_template_scores(outcome)
        
        # Step 2: Update ML meta-model
        await self._update_ml_model(outcome)
        
        # Step 3: Identify and pin high-performers
        await self._update_golden_templates(outcome)
        
        # Step 4: Learn template combinations
        await self._learn_template_combinations(outcome)
    
    async def _update_template_scores(
        self,
        outcome: ProjectOutcome
    ):
        """
        Update template quality scores based on usage outcomes
        
        Formula:
        new_score = (old_score * usage_count + outcome_quality * weight) / (usage_count + weight)
        
        Higher weight for recent outcomes
        """
        for persona_id, template_ids in outcome.templates_used.items():
            persona_quality = outcome.quality_scores.get(persona_id, 0.0)
            
            for template_id in template_ids:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.template_registry_url}/api/v1/templates/{template_id}/record-usage",
                        json={
                            "outcome_quality": persona_quality,
                            "persona_id": persona_id,
                            "project_id": outcome.project_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
    
    async def _update_ml_model(
        self,
        outcome: ProjectOutcome
    ):
        """
        Update Maestro ML meta-model with new training data
        
        Learns:
        - Which templates work well for which requirement types
        - Which template combinations are successful
        - Persona-template compatibility patterns
        """
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.maestro_ml_url}/api/v1/meta-learning/record-outcome",
                json={
                    "project_id": outcome.project_id,
                    "requirement": outcome.requirement,
                    "templates_used": outcome.templates_used,
                    "quality_scores": outcome.quality_scores,
                    "overall_success": outcome.overall_success,
                    "execution_time": outcome.execution_time_minutes,
                    "cost": outcome.cost_dollars
                }
            )
    
    async def _update_golden_templates(
        self,
        outcome: ProjectOutcome
    ):
        """
        Identify high-performing templates and pin as "golden"
        
        Criteria for golden status:
        - Quality score > 90
        - Success rate > 85% over last 20 uses
        - Positive user feedback
        - No security issues
        """
        for persona_id, template_ids in outcome.templates_used.items():
            persona_quality = outcome.quality_scores.get(persona_id, 0.0)
            
            if persona_quality >= 90.0:
                for template_id in template_ids:
                    # Check if template qualifies for golden status
                    async with httpx.AsyncClient() as client:
                        stats_response = await client.get(
                            f"{self.template_registry_url}/api/v1/templates/{template_id}/stats"
                        )
                        
                        stats = stats_response.json()
                        
                        if (stats["success_rate"] >= 0.85 and 
                            stats["usage_count"] >= 20 and
                            stats["security_score"] >= 80):
                            
                            # Pin as golden template
                            await client.post(
                                f"{self.template_registry_url}/api/v1/templates/{template_id}/pin",
                                json={
                                    "quality_tier": "gold",
                                    "pin_reason": f"Consistent high performance: {stats['success_rate']:.0%} success rate over {stats['usage_count']} uses",
                                    "pinned_by": "quality_feedback_loop"
                                }
                            )
    
    async def _learn_template_combinations(
        self,
        outcome: ProjectOutcome
    ):
        """
        Learn which template combinations work well together
        
        Example insights:
        - FastAPI async CRUD + PostgreSQL async driver = 95% success
        - React + TailwindCSS + TypeScript = 92% success
        - NestJS + TypeORM + PostgreSQL = 88% success
        """
        if outcome.overall_success >= 85.0:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.maestro_ml_url}/api/v1/patterns/record-combination",
                    json={
                        "templates_used": outcome.templates_used,
                        "success_score": outcome.overall_success,
                        "project_type": outcome.requirement[:100],  # Truncated
                        "timestamp": datetime.now().isoformat()
                    }
                )
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal**: Connect systems, enable basic RAG retrieval

**Tasks**:
1. Create unified APIs
   - Template search endpoint (Maestro Templates)
   - Template ranking endpoint (Maestro ML)
   - Usage tracking endpoint (both systems)

2. Implement `RAGEnhancedPersonaExecutor`
   - Basic template retrieval
   - Inject templates into persona context
   - Track usage

3. Test with 2-3 personas
   - Backend developer with CRUD templates
   - Frontend developer with React templates
   - DevOps with Docker templates

**Deliverable**: Personas can retrieve and reference templates

---

### Phase 2: ML-Powered Ranking (Week 3-4)

**Goal**: Smart template selection based on ML predictions

**Tasks**:
1. Build template ranking model (Maestro ML)
   - Features: quality score, usage history, persona fit, requirement match
   - Target: predicted success probability
   - Train on historical data (if available)

2. Implement `UnifiedSimilarityService`
   - Three-layer similarity (project, persona, template)
   - Hybrid execution plans
   - Confidence scoring

3. A/B test
   - Run same requirements with/without ML ranking
   - Compare quality outcomes
   - Validate improvement

**Deliverable**: ML-powered template recommendations

---

### Phase 3: Quality Feedback Loop (Week 5-6)

**Goal**: System learns and improves over time

**Tasks**:
1. Implement `QualityFeedbackLoop`
   - Track project outcomes
   - Update template scores
   - Pin golden templates
   - Learn combinations

2. Build analytics dashboard
   - Template success rates
   - Quality trends over time
   - Golden template catalog
   - Persona-template compatibility matrix

3. Automated quality gates
   - Flag declining templates
   - Suggest template updates
   - Recommend new template creation

**Deliverable**: Self-improving system with feedback loop

---

### Phase 4: AutoGen Patterns Integration (Week 7-10)

**Goal**: Add collaborative and reflection patterns

**Tasks**:
1. Group Chat for template selection
   - Multiple personas discuss which templates to use
   - Debate trade-offs
   - Reach consensus

2. Reflection for template refinement
   - Persona uses template
   - Critic reviews output
   - Persona refines
   - Iterate until quality threshold

3. Human-in-loop for template approval
   - Human reviews recommended templates
   - Approves/rejects
   - Provides guidance

**Deliverable**: Advanced workflow patterns operational

---

## Database Schema Extensions

### New Tables (Maestro ML)

```sql
-- Template usage tracking
CREATE TABLE template_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id VARCHAR(255) NOT NULL,
    persona_id VARCHAR(100) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    outcome_quality FLOAT,
    execution_time_seconds INT,
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_template_id (template_id),
    INDEX idx_persona_id (persona_id),
    INDEX idx_created_at (created_at)
);

-- Template combinations that work well together
CREATE TABLE template_combinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    templates JSONB NOT NULL,  -- Array of template IDs
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    avg_quality_score FLOAT,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_templates (templates USING GIN)
);

-- Template quality history (time-series)
CREATE TABLE template_quality_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id VARCHAR(255) NOT NULL,
    quality_score FLOAT NOT NULL,
    success_rate FLOAT,
    usage_count INT,
    recorded_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_template_id_time (template_id, recorded_at)
);
```

### Updated Tables (Maestro Templates)

```sql
-- Add dynamic quality tracking to templates table
ALTER TABLE templates ADD COLUMN usage_count INT DEFAULT 0;
ALTER TABLE templates ADD COLUMN success_count INT DEFAULT 0;
ALTER TABLE templates ADD COLUMN failure_count INT DEFAULT 0;
ALTER TABLE templates ADD COLUMN avg_outcome_quality FLOAT;
ALTER TABLE templates ADD COLUMN last_used_at TIMESTAMP;
ALTER TABLE templates ADD COLUMN quality_tier VARCHAR(20) DEFAULT 'standard';
```

---

## API Specifications

### Maestro Templates API Extensions

#### POST /api/v1/templates/search
```json
{
  "persona": "backend_developer",
  "query": "async CRUD operations with pagination",
  "requirement_context": "Build e-commerce platform...",
  "top_k": 10,
  "min_quality_score": 70.0,
  "include_pinned": true
}

Response:
{
  "templates": [
    {
      "id": "uuid",
      "name": "FastAPI Async CRUD",
      "content": "...",
      "quality_score": 85.0,
      "relevance_score": 92.0,
      "metadata": {...}
    }
  ],
  "total_found": 25,
  "retrieval_time_ms": 45
}
```

#### POST /api/v1/templates/{id}/record-usage
```json
{
  "outcome_quality": 87.5,
  "persona_id": "backend_developer",
  "project_id": "proj_12345",
  "timestamp": "2025-01-15T10:30:00Z"
}

Response:
{
  "template_id": "uuid",
  "updated_quality_score": 85.2,
  "usage_count": 156,
  "success_rate": 0.89
}
```

---

### Maestro ML API Extensions

#### POST /api/v1/templates/rank
```json
{
  "templates": [
    {
      "template_id": "uuid1",
      "quality_score": 85.0,
      "metadata": {...}
    }
  ],
  "persona_id": "backend_developer",
  "requirement": "Build e-commerce platform...",
  "context": {...}
}

Response:
{
  "rankings": [
    {
      "template_id": "uuid1",
      "predicted_success": 0.92,
      "confidence": 0.85,
      "reasoning": "High historical success for similar requirements"
    }
  ]
}
```

#### POST /api/v1/meta-learning/record-outcome
```json
{
  "project_id": "proj_12345",
  "requirement": "...",
  "templates_used": {
    "backend_developer": ["uuid1", "uuid2"],
    "frontend_developer": ["uuid3"]
  },
  "quality_scores": {
    "backend_developer": 87.5,
    "frontend_developer": 92.0
  },
  "overall_success": 89.2,
  "execution_time": 45.5,
  "cost": 12.50
}

Response:
{
  "recorded": true,
  "insights": [
    "Template combination uuid1+uuid2 has 95% success rate",
    "Frontend template uuid3 consistently performs well"
  ]
}
```

---

## Configuration Files

### config/rag_integration.yaml
```yaml
# RAG Integration Configuration

template_registry:
  url: "http://localhost:9800"
  api_version: "v1"
  timeout_seconds: 30
  retry_attempts: 3

maestro_ml:
  url: "http://localhost:8000"
  api_version: "v1"
  timeout_seconds: 60
  enable_ranking: true
  enable_feedback_loop: true

retrieval:
  top_k_templates: 10
  min_quality_score: 70.0
  prioritize_golden: true
  semantic_search: true
  
ranking:
  enable_ml_ranking: true
  confidence_threshold: 0.70
  fallback_to_quality_score: true

feedback_loop:
  enable: true
  update_frequency: "realtime"  # or "batch"
  golden_threshold:
    quality_score: 90.0
    success_rate: 0.85
    min_usage: 20
    security_score: 80.0

personas:
  # Per-persona RAG configuration
  backend_developer:
    enable_rag: true
    top_k: 5
    categories: ["api", "database", "authentication"]
  
  frontend_developer:
    enable_rag: true
    top_k: 5
    categories: ["ui", "components", "styling"]
  
  devops_engineer:
    enable_rag: true
    top_k: 3
    categories: ["infrastructure", "ci-cd", "monitoring"]
```

---

## Usage Examples

### Example 1: E-Commerce Platform with RAG

```python
from rag_enhanced_persona_executor import RAGEnhancedPersonaExecutor
from unified_similarity_service import UnifiedSimilarityService
from quality_feedback_loop import QualityFeedbackLoop, ProjectOutcome

# Initialize integrated system
rag_executor = RAGEnhancedPersonaExecutor(
    template_registry_url="http://localhost:9800",
    maestro_ml_url="http://localhost:8000"
)

similarity_service = UnifiedSimilarityService(
    maestro_ml_url="http://localhost:8000",
    template_registry_url="http://localhost:9800"
)

feedback_loop = QualityFeedbackLoop(
    maestro_ml_url="http://localhost:8000",
    template_registry_url="http://localhost:9800"
)

# Step 1: Analyze requirement for similarity and templates
requirement = """
Create e-commerce platform with:
- Product catalog with search and filters
- Shopping cart with checkout
- User authentication and profiles
- Payment processing (Stripe)
- Admin dashboard
- Real-time inventory tracking
"""

similarity_result = await similarity_service.analyze_requirement(
    requirement=requirement,
    persona_ids=[
        "backend_developer",
        "frontend_developer",
        "devops_engineer",
        "qa_engineer"
    ]
)

print(f"Similar project: {similarity_result.similar_project_id}")
print(f"Execution plan:")
for persona, strategy in similarity_result.execution_plan.items():
    print(f"  {persona}: {strategy}")

# Step 2: Execute with RAG enhancement
results = {}
for persona_id in ["backend_developer", "frontend_developer"]:
    if similarity_result.execution_plan[persona_id] == "use_template":
        result = await rag_executor.execute_persona_with_rag(
            persona_id=persona_id,
            requirement=requirement,
            task_description=f"{persona_id} work for e-commerce platform",
            context={}
        )
        results[persona_id] = result
        print(f"{persona_id} used templates: {result['templates_used']}")

# Step 3: Record outcome for feedback loop
outcome = ProjectOutcome(
    project_id="ecommerce_project_123",
    requirement=requirement,
    personas_executed=list(results.keys()),
    templates_used={
        persona: result['templates_used']
        for persona, result in results.items()
    },
    quality_scores={
        persona: result['quality_score']
        for persona, result in results.items()
    },
    overall_success=sum(r['quality_score'] for r in results.values()) / len(results),
    execution_time_minutes=sum(r['execution_time'] for r in results.values()),
    cost_dollars=sum(r['cost'] for r in results.values()),
    user_satisfaction=None
)

await feedback_loop.record_project_outcome(outcome)
print("Feedback loop updated")
```

---

### Example 2: Template Discovery and Selection

```python
# Discover templates for specific task
async def discover_templates(persona_id: str, task: str):
    """Interactive template discovery"""
    
    # Retrieve candidates
    templates = await rag_executor._retrieve_templates(
        persona_id=persona_id,
        task_description=task,
        requirement=""
    )
    
    print(f"Found {len(templates)} templates for {persona_id}:")
    for i, template in enumerate(templates[:5], 1):
        print(f"\n{i}. {template.name}")
        print(f"   Quality: {template.quality_score:.0f}%")
        print(f"   Description: {template.metadata.get('description', 'N/A')[:100]}...")
        print(f"   Tags: {', '.join(template.metadata.get('tags', []))}")
    
    # ML ranks them
    ranked = await rag_executor._rank_templates(
        templates=templates,
        persona_id=persona_id,
        requirement=task,
        context={}
    )
    
    print(f"\nTop ML-ranked template: {ranked[0].name}")
    print(f"Predicted success: {ranked[0].relevance_score:.0f}%")
    
    return ranked[0]

# Use it
best_template = await discover_templates(
    "backend_developer",
    "async CRUD operations with PostgreSQL"
)
```

---

## Success Metrics

### Before Integration (Current State)
- Template retrieval: Manual, ad-hoc
- Quality tracking: Static scores
- Learning: None (no feedback loop)
- Template selection: Random or manual
- Improvement: Manual template updates

### After Integration (Target State)
- Template retrieval: Automatic, RAG-powered
- Quality tracking: Dynamic, usage-based
- Learning: Continuous (feedback loop)
- Template selection: ML-predicted success
- Improvement: Automatic (golden pinning, quality updates)

### Measurable KPIs

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Template usage rate | 0% | 80%+ | Week 2 |
| Quality score accuracy | N/A | ±5% | Week 4 |
| Golden template identification | Manual | Auto | Week 6 |
| Template recommendation accuracy | N/A | 85%+ | Week 8 |
| System learning rate | 0 | Continuous | Week 6 |
| Time savings (with RAG) | 0% | 30%+ | Week 10 |
| Quality improvement | N/A | +15% | Week 10 |

---

## Risk Mitigation

### Risk 1: Template Quality Drift
**Risk**: Templates become outdated as frameworks evolve  
**Mitigation**: 
- Track template usage over time
- Flag templates with declining success rates
- Automatic deprecation alerts
- Version control integration for updates

### Risk 2: ML Model Accuracy
**Risk**: ML predictions lead to wrong template selection  
**Mitigation**:
- Confidence thresholds (only use predictions with >70% confidence)
- Fallback to quality scores if ML unavailable
- A/B testing to validate improvements
- Human-in-loop for critical decisions

### Risk 3: Feedback Loop Bias
**Risk**: Successful templates get more usage, creating echo chamber  
**Mitigation**:
- Exploration vs exploitation balance (10% random selection)
- Track diversity metrics
- Periodic revalidation of all templates
- User feedback integration

### Risk 4: Integration Complexity
**Risk**: Three systems increase complexity and failure points  
**Mitigation**:
- Graceful degradation (each system can work independently)
- Circuit breakers for external calls
- Comprehensive monitoring
- Fallback modes for all integrations

---

## Next Steps

### Immediate (This Week)
1. Review this architecture with team
2. Prioritize features (recommend Phase 1-3 first)
3. Set up development environment with all three systems running
4. Create integration test plan

### Short-term (Next 2 Weeks)
1. Implement Phase 1: RAG integration
2. Test with 2-3 personas
3. Measure baseline metrics
4. Validate improvement

### Medium-term (Weeks 3-6)
1. Implement Phase 2: ML ranking
2. Implement Phase 3: Feedback loop
3. Build analytics dashboard
4. Deploy to production

### Long-term (Weeks 7-10)
1. Implement Phase 4: AutoGen patterns
2. Expand to all 11 personas
3. Optimize based on learnings
4. Scale system

---

## Conclusion

This unified architecture brings together three powerful systems into a cohesive, self-improving SDLC platform:

**Maestro Templates (RAG)** provides the knowledge base
**Maestro ML (MLOps)** provides the intelligence
**SDLC Team** provides the execution

Together, they create a system that:
- Learns from every project
- Retrieves best practices automatically
- Makes ML-powered decisions
- Improves continuously through feedback
- Delivers higher quality faster

The integration is designed to be incremental, with each phase delivering value independently while building toward the complete vision of an intelligent, self-improving SDLC platform.

**Recommended Start**: Phase 1 (RAG integration) - 2 weeks, immediate value, low risk.
