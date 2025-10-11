# Team Execution V2 - Quick Start Guide

## TL;DR

Team Execution V2 replaces hardcoded logic with AI-driven decision making, introduces blueprint-based team patterns, and enables true parallel execution through contract-first architecture.

## Running V2

```bash
# Basic usage
python3 team_execution_v2.py \
  --requirement "Your requirement here" \
  --output ./project

# With options
python3 team_execution_v2.py \
  --requirement "Build REST API with authentication" \
  --prefer-parallel \
  --quality-threshold 0.85 \
  --session-id my_project_v1 \
  --output ./my_project
```

## What V2 Does

### 1. AI Analyzes Requirement
```
Input:  "Build user authentication with frontend and backend"
Output: RequirementClassification
  - Type: feature_development
  - Complexity: moderate
  - Parallelizability: fully_parallel (90% can run in parallel!)
  - Effort: 12 hours
  - Confidence: 0.85
```

### 2. AI Recommends Blueprint
```
Input:  RequirementClassification
Output: BlueprintRecommendation
  - Blueprint: "parallel-contract-first"
  - Team: [requirement_analyst, backend_developer, frontend_developer, qa_engineer]
  - Time savings: 40% vs sequential
```

### 3. AI Designs Contracts
```
Input:  Requirement + Blueprint
Output: List[Contract]
  - Backend API Contract (provider: backend, consumers: [frontend, qa])
  - Frontend UI Contract (provider: frontend, consumers: [qa])
  - Mock API endpoint: http://localhost:3001
```

### 4. Creates Session
```
Output: Session created with team composition and contracts
  - Session ID: sdlc_abc123_20241008_163955
  - Team size: 4 personas
  - Contracts: 2 main contracts + dependencies
```

## Key Concepts

### Persona vs Contract

**OLD (Embedded - Bad)**:
```python
persona = {
    "id": "backend_developer",
    "deliverables": ["api_implementation"]  # Embedded!
}
```

**NEW (Separated - Good)**:
```python
# WHO
persona = {"id": "backend_developer", "expertise": ["Node.js"]}

# WHAT  
contract = {
    "id": "backend_api_v1",
    "provider": "backend_developer",
    "deliverables": ["api_implementation"],
    "interface_spec": {...},
    "mock_available": true
}

# HOW
assignment = assign_persona_to_contract(persona, contract)
```

### Parallel Execution with Contracts

```
Without Contracts (Sequential):
Backend (60min) → Frontend (45min) → QA (30min) = 135 minutes

With Contracts (Parallel):
Backend (60min)  ← Real API
Frontend (60min) ← Mock API (from contract)
QA (30min)       ← Tests real API
= 60 minutes (56% faster!)
```

**How**:
1. AI creates OpenAPI contract
2. Mock server generated from contract
3. Frontend uses mock while backend builds real API
4. After 60min: Validate backend fulfilled contract
5. Switch frontend from mock to real API
6. Run integration tests

## Architecture

```
User Requirement
      ↓
TeamComposerAgent (AI)
   → Analyzes complexity
   → Identifies parallelizability  
   → Recommends blueprint
      ↓
ContractDesignerAgent (AI)
   → Designs contracts
   → Defines deliverables
   → Creates interfaces
      ↓
Blueprint Factory
   → Instantiates team pattern
   → Assigns personas to contracts
      ↓
Execution (Phase 2 - Coming Soon)
   → Parallel/sequential execution
   → Contract validation
   → Integration testing
```

## V1 vs V2 Comparison

| Feature | V1 | V2 |
|---------|----|----|
| Requirement Analysis | Keyword matching | AI classification |
| Team Composition | Manual list | AI + blueprint search |
| Parallel Execution | Limited | Contract-enabled |
| Personas | Embedded deliverables | Separated from contracts |
| Scalability | Fixed patterns | 12+ blueprints |
| Code | 2800 lines | 800 lines |

## Files

- `team_execution_v2.py` - Main engine
- `TEAM_EXECUTION_V2_DESIGN.md` - Full architecture (23 KB)
- `TEAM_EXECUTION_V2_COMPLETE.md` - Summary and results (15 KB)
- `TEAM_EXECUTION_V2_QUICK_START.md` - This file

## What's Implemented

✅ AI requirement analysis  
✅ Blueprint recommendation  
✅ Contract design  
✅ Session creation  
✅ Fallback behavior (works without Claude SDK/blueprints)  

## What's Coming (Phase 2)

⏳ Actual persona execution with contracts  
⏳ Contract validation (verify fulfillment)  
⏳ Mock generation (auto-generate from contracts)  
⏳ Integration testing (verify contract compatibility)  
⏳ Parallel coordinator (orchestrate parallel execution)  

## Example Output

```json
{
  "success": true,
  "classification": {
    "type": "feature_development",
    "complexity": "moderate",
    "parallelizability": "fully_parallel",
    "effort_hours": 12.0,
    "confidence": 0.85
  },
  "blueprint": {
    "name": "Contract-First Parallel Team",
    "match_score": 0.92,
    "execution_mode": "parallel",
    "estimated_time_savings": 0.40
  },
  "team": {
    "personas": ["requirement_analyst", "backend_developer", "frontend_developer", "qa_engineer"],
    "size": 4
  },
  "contracts": [
    {
      "name": "Backend API Contract",
      "provider": "backend_developer",
      "consumers": ["frontend_developer", "qa_engineer"],
      "mock_available": true
    }
  ]
}
```

## Key Innovation

**Separation of Concerns**: Persona (WHO) + Contract (WHAT) = Team (HOW)

This enables:
- Reusability (same persona, different contracts)
- Flexibility (change deliverables without changing personas)
- Parallel work (contracts define interfaces, mocks enable simultaneous work)
- Clear validation (verify against contract terms)
- Versioning (track contract evolution)

## Questions?

See full documentation:
- Architecture: `TEAM_EXECUTION_V2_DESIGN.md`
- Results: `TEAM_EXECUTION_V2_COMPLETE.md`

Ready for Phase 2 implementation! 🚀
