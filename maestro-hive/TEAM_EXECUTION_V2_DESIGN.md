# Team Execution V2 - Modern Architecture with Blueprint System

## Executive Summary

Current `team_execution.py` is a monolithic V3.1 SDLC engine focused on persona-level reuse. It mixes concerns and lacks proper team management architecture. This proposal modernizes it using the superior blueprint system from `synth` and proper contract management.

---

## Critical Analysis of Current team_execution.py

### What It Does Well ✅
- **Session Management**: Resumable workflows with state persistence
- **Quality Gates**: Comprehensive validation after each persona execution  
- **Deployment Validation**: Build testing and configuration checks
- **File Tracking**: Accurate deliverable mapping
- **Conversation History**: Rich context via AutoGen-inspired message system

### Architectural Issues ⚠️

#### 1. **Hardcoded Decision Logic** (Critical Issue)
```python
def _analyze_requirements(self, requirement: str) -> str:
    """Returns hardcoded 'parallel' or 'sequential'"""
    # This should be AI-driven!
```

**Problem**: Uses keyword matching ("login", "frontend", "backend") to classify requirements. This violates the AI-first principle you emphasized.

**Solution**: Use agent AI with contract to determine:
- Requirement classification
- Team composition
- Execution strategy

#### 2. **No Blueprint Integration**
Current system doesn't use the superior blueprint architecture available in `synth`:
- No access to 12+ predefined team patterns
- No archetype-based team creation
- No searchable team catalog
- Missing elastic scaling, performance tracking, etc.

#### 3. **Personas vs Contracts Confusion**
```python
# Current: Personas have embedded behavior
persona_config = {
    "system_prompt": "...",  # Embedded
    "deliverables": [...],   # Embedded
    "expertise": [...]       # Embedded
}
```

**Problem**: Personas ARE profiles (who you are), not contracts (what you deliver). Current mixing leads to:
- Tight coupling
- Hard to change deliverables
- Can't reuse personas in different contracts

**Solution**: Separate concerns:
```python
# Persona (identity)
persona = {
    "id": "backend_developer",
    "expertise": ["Node.js", "APIs", "Databases"],
    "system_prompt": "You are an expert backend developer"
}

# Contract (obligation)
contract = {
    "id": "backend_api_contract_v1",
    "deliverables": ["api_implementation", "database_schema"],
    "acceptance_criteria": {...},
    "dependencies": ["architecture_design"],
    "consumers": ["frontend_team", "qa_team"]
}

# Assignment
assignment = {
    "persona_id": "backend_developer",
    "contract_id": "backend_api_contract_v1",
    "role": "provider"
}
```

#### 4. **Manual Team Composition**
```python
# Current: Manually list personas
selected_personas = ["requirement_analyst", "backend_developer", "frontend_developer"]
```

**Should be**: AI agent determines optimal team based on:
- Requirement complexity
- Available blueprints
- Resource constraints
- Timeline requirements

---

## Proposed Architecture: Team Execution V2

### Core Principles

1. **AI-Driven, Not Scripted**
   - AI agent analyzes requirements
   - AI agent selects team blueprint
   - AI agent creates contracts
   - AI agent validates fulfillment

2. **Blueprint-Based Team Management**
   - Use `synth/blueprints` architecture
   - 12+ predefined patterns available
   - Searchable and queryable
   - Declarative, not imperative

3. **Contract-First Execution**
   - Personas augmented with contracts, not embedded
   - Contracts are independent artifacts
   - Clear provider/consumer relationships
   - Validation against contracts

4. **Separation of Concerns**
   ```
   Personas (WHO)  +  Contracts (WHAT)  =  Team (HOW)
   Identity           Obligation            Execution
   ```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                 Team Execution V2 Engine                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. AI-Driven Requirement Analysis                   │   │
│  │   • TeamComposerAgent analyzes requirement           │   │
│  │   • Identifies complexity, dependencies, timeline    │   │
│  │   • Returns: RequirementClassification               │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 2. Blueprint Selection                              │   │
│  │   • Search blueprint catalog by attributes          │   │
│  │   • Match execution mode, scaling, capabilities     │   │
│  │   • Returns: TeamBlueprint                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 3. Contract Generation                              │   │
│  │   • ContractDesignerAgent creates contracts          │   │
│  │   • Defines deliverables, acceptance criteria       │   │
│  │   • Establishes dependencies and interfaces         │   │
│  │   • Returns: List[Contract]                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 4. Team Instantiation                               │   │
│  │   • Use team_factory.from_blueprint()               │   │
│  │   • Assign personas to contracts                    │   │
│  │   • Configure coordination and scaling              │   │
│  │   • Returns: ExecutableTeam                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 5. Execution with Contract Validation               │   │
│  │   • Execute according to blueprint pattern          │   │
│  │   • Each persona works against their contract       │   │
│  │   • Validate deliverables vs contract terms         │   │
│  │   • Quality gates on contract fulfillment           │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 6. Contract Verification & Integration              │   │
│  │   • Validate provider delivered per contract        │   │
│  │   • Verify consumers can use deliverables           │   │
│  │   • Integration tests where contracts connect       │   │
│  │   • Returns: ValidationReport                       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. TeamComposerAgent (AI-Driven)
```python
class TeamComposerAgent:
    """AI agent that analyzes requirements and recommends team composition"""
    
    async def analyze_requirement(self, requirement: str) -> RequirementClassification:
        """
        Use AI to classify requirement:
        - Type: feature_development, bug_fix, refactoring, etc.
        - Complexity: simple, moderate, complex
        - Parallelizability: fully_parallel, partially_parallel, sequential
        - Required expertise: [list of skills needed]
        - Estimated effort: hours/days
        - Dependencies: what needs to be done first
        """
        
    async def recommend_blueprint(
        self,
        classification: RequirementClassification
    ) -> BlueprintRecommendation:
        """
        Search blueprint catalog and return best match:
        - Blueprint ID
        - Match score
        - Rationale
        - Alternative options
        """
```

#### 2. ContractDesignerAgent (AI-Driven)
```python
class ContractDesignerAgent:
    """AI agent that designs contracts between team members"""
    
    async def design_contracts(
        self,
        requirement: str,
        team_blueprint: TeamBlueprint,
        personas: List[str]
    ) -> List[Contract]:
        """
        Create contracts with:
        - Deliverables (what must be produced)
        - Acceptance criteria (how to validate)
        - Dependencies (what's needed first)
        - Interfaces (APIs, schemas, protocols)
        - Timeline (when it's due)
        - Provider (who creates it)
        - Consumers (who uses it)
        """
```

#### 3. Enhanced ContractManager
```python
class ContractManager:
    """Manages contract lifecycle and validation"""
    
    async def create_contract(
        self,
        contract: ContractSpecification
    ) -> Contract:
        """Create and version a contract"""
    
    async def validate_fulfillment(
        self,
        contract_id: str,
        deliverables: Dict[str, List[str]]
    ) -> ValidationResult:
        """
        Validate deliverables against contract:
        - Completeness (all deliverables present)
        - Quality (meets acceptance criteria)
        - Interface compliance (matches spec)
        - No breaking changes (vs previous version)
        """
    
    async def generate_mock_from_contract(
        self,
        contract_id: str
    ) -> MockImplementation:
        """
        Generate mock for consumers while provider works:
        - Mock API server (from OpenAPI spec)
        - Mock data generators
        - Test harness
        """
```

#### 4. Team Factory Integration
```python
from synth.maestro_ml.modules.teams.blueprints import (
    create_team_from_blueprint,
    search_blueprints
)

class TeamExecutionEngineV2:
    
    async def create_team(
        self,
        requirement: str
    ) -> ExecutableTeam:
        """
        End-to-end team creation:
        1. AI analyzes requirement
        2. Search blueprint catalog
        3. Design contracts
        4. Instantiate team from blueprint
        5. Assign contracts to personas
        """
        
        # Step 1: AI-driven analysis
        classification = await self.composer_agent.analyze_requirement(requirement)
        
        # Step 2: Find matching blueprint
        blueprint_rec = await self.composer_agent.recommend_blueprint(classification)
        
        # Step 3: Design contracts
        contracts = await self.contract_designer.design_contracts(
            requirement,
            blueprint_rec.blueprint,
            blueprint_rec.personas
        )
        
        # Step 4: Create team from blueprint
        team = create_team_from_blueprint(
            blueprint_id=blueprint_rec.blueprint_id,
            name=f"team_{uuid4().hex[:8]}"
        )
        
        # Step 5: Assign contracts
        for persona_id, contract in zip(blueprint_rec.personas, contracts):
            team.assign_contract(persona_id, contract)
        
        return team
```

---

## Contract vs Persona: Clear Separation

### Current (Embedded) ❌
```python
# persona = identity + obligations mixed together
backend_dev_persona = {
    "id": "backend_developer",
    "system_prompt": "You are backend developer...",
    "expertise": ["Node.js", "PostgreSQL"],
    "deliverables": [  # ← EMBEDDED (bad)
        "api_implementation",
        "database_schema",
        "business_logic"
    ]
}
```

### Proposed (Separated) ✅
```python
# 1. Persona = Identity (WHO)
backend_dev_persona = {
    "id": "backend_developer",
    "name": "Backend Developer",
    "expertise": ["Node.js", "PostgreSQL", "REST APIs"],
    "system_prompt": "You are an expert backend developer specializing in Node.js...",
    "capabilities": ["coding", "architecture", "database_design"],
    "experience_level": "senior"
}

# 2. Contract = Obligation (WHAT)
backend_api_contract = {
    "id": "contract_backend_api_v1",
    "name": "Backend API Implementation Contract",
    "version": "v1.0",
    "type": "REST_API",
    
    # What must be delivered
    "deliverables": [
        {
            "name": "api_implementation",
            "description": "RESTful API endpoints per spec",
            "artifacts": ["src/routes/*.ts", "src/controllers/*.ts"],
            "acceptance_criteria": [
                "All endpoints respond with correct status codes",
                "Input validation implemented",
                "Error handling for all paths",
                "Unit tests with >80% coverage"
            ]
        },
        {
            "name": "database_schema",
            "description": "PostgreSQL schema and migrations",
            "artifacts": ["prisma/schema.prisma", "migrations/*.sql"],
            "acceptance_criteria": [
                "Schema normalized to 3NF",
                "Indexes on foreign keys",
                "Migration scripts reversible"
            ]
        }
    ],
    
    # What's needed first
    "dependencies": [
        {
            "contract_id": "contract_architecture_v1",
            "deliverables": ["api_specifications", "database_design"]
        }
    ],
    
    # Interface specification (enables parallel work)
    "interface": {
        "type": "openapi",
        "spec_url": "contracts/backend_api_v1.yaml",
        "mock_server": "http://localhost:3001"  # For frontend to use while backend builds
    },
    
    # Who uses this
    "consumers": [
        {
            "persona_id": "frontend_developer",
            "usage": "Consumes API for UI integration"
        },
        {
            "persona_id": "qa_engineer",
            "usage": "Tests API endpoints"
        }
    ],
    
    # Provider
    "provider": {
        "persona_id": "backend_developer",
        "role": "implementer"
    },
    
    # Timeline
    "estimated_effort_hours": 12,
    "deadline": "2024-01-15T18:00:00Z"
}

# 3. Assignment = Persona + Contract (HOW)
assignment = {
    "id": "assignment_001",
    "persona_id": "backend_developer",
    "contract_id": "contract_backend_api_v1",
    "role": "provider",  # or "consumer", "reviewer"
    "status": "in_progress",
    "started_at": "2024-01-15T10:00:00Z"
}
```

### Benefits of Separation

1. **Reusability**
   - Same persona can fulfill different contracts
   - Same contract can be fulfilled by different personas
   - Personas reusable across projects

2. **Flexibility**
   - Change deliverables without changing persona
   - Swap personas mid-project
   - Version contracts independently

3. **Parallel Work**
   - Contract defines interface
   - Frontend uses mock while backend builds real API
   - Both test against contract specification

4. **Clear Validation**
   - Validate deliverables against contract terms
   - Check acceptance criteria objectively
   - Track contract version compatibility

5. **Better Testing**
   - Contract tests verify provider meets spec
   - Consumer tests verify they can use interface
   - Integration tests verify contract compatibility

---

## Parallel Execution with Contracts: How It Works

### The Problem
Traditional sequential execution:
```
Timeline: 0────────────135 minutes
          ├────────┤
          │Backend │ (60 min)
               ├────────┤
               │Frontend│ (45 min)
                    ├───┤
                    │QA │ (30 min)
Total: 135 minutes ❌ (slow!)
```

### The Solution: Contract-First Parallel

```
Timeline: 0────60 min
          ├────────┤
          │Backend │  ← Real API
          │────────│
          │Frontend│  ← Mock API (from contract)
          └────────┘
               │QA │  ← Tests real API
               └───┘
Total: 60 minutes ✅ (56% faster!)
```

### Step-by-Step Flow

#### Phase 1: Contract Creation (10 min)
```python
# AI creates API contract
contract = await contract_designer.design_contracts(
    requirement="Build user authentication"
)

# Contract includes OpenAPI spec
contract.interface = {
    "type": "openapi",
    "spec": {
        "POST /api/auth/login": {
            "request": {"email": "string", "password": "string"},
            "response": {"token": "string", "user": {...}}
        }
    }
}

# Generate mock server from contract
mock_server = await contract_manager.generate_mock_from_contract(contract.id)
# Mock server runs on http://localhost:3001 (returns fake data per spec)
```

#### Phase 2: Parallel Execution (60 min)
```python
# Backend builds REAL API
backend_assignment = {
    "persona": "backend_developer",
    "contract": contract,
    "role": "provider",
    "deliverables": ["real API implementation"]
}

# Frontend builds against MOCK API
frontend_assignment = {
    "persona": "frontend_developer",
    "contract": contract,
    "role": "consumer",
    "mock_endpoint": "http://localhost:3001",  # Uses mock while backend works
    "deliverables": ["UI components", "API integration"]
}

# Execute in parallel
await asyncio.gather(
    execute_persona(backend_assignment),
    execute_persona(frontend_assignment)
)
```

#### Phase 3: Integration & Validation (15 min)
```python
# Validate backend fulfilled contract
backend_validation = await contract_manager.validate_fulfillment(
    contract_id=contract.id,
    deliverables=backend_result.deliverables
)

# Switch frontend from mock to real API
await frontend_team.switch_endpoint(
    from_url="http://localhost:3001",  # Mock
    to_url="http://localhost:3000"     # Real backend
)

# Run integration tests
integration_tests = await qa_engineer.test_integration(
    frontend_url="http://localhost:5173",
    backend_url="http://localhost:3000"
)

# Verify contract compatibility
assert backend_validation.passed
assert integration_tests.passed
```

### Understanding "Assuming Backend Fulfills"

**Question**: "When Frontend tests with Mock API, it's assuming backend fulfills conditions already?"

**Answer**: Yes, **but** with validation:

1. **During Development (Parallel Phase)**
   ```python
   # Frontend assumes contract WILL be fulfilled
   # Works against mock that CONFORMS to contract
   frontend.test_against_mock()
   # ✅ Tests pass (mock always conforms to contract)
   ```

2. **After Integration (Verification Phase)**
   ```python
   # Now we verify backend ACTUALLY fulfilled contract
   backend_validation = contract_manager.validate_fulfillment(backend_deliverables)
   
   if not backend_validation.passed:
       # Backend didn't fulfill contract!
       # This is a CONTRACT VIOLATION
       raise ContractViolationError(
           f"Backend failed: {backend_validation.failures}"
       )
   
   # Switch to real backend
   integration_tests = frontend.test_against_real_backend()
   
   if not integration_tests.passed:
       # Backend API doesn't match contract spec!
       # This is an INTERFACE MISMATCH
       raise InterfaceMismatchError(
           f"Real API differs from contract: {integration_tests.failures}"
       )
   ```

3. **Trust But Verify** ✅
   - During parallel work: Trust the contract (use mock)
   - After parallel work: Verify the contract (test real)
   - If verification fails: Provider violated contract

This is exactly how microservices work in production:
- Teams define contracts (OpenAPI, gRPC, GraphQL)
- Consumers use mocks during development
- Contract tests verify providers fulfill obligations
- Integration tests verify real compatibility

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
```python
# Files to create:
1. team_execution_v2.py              # New engine
2. ai_agents/team_composer.py        # AI requirement analysis
3. ai_agents/contract_designer.py    # AI contract creation
4. contracts/contract_models.py      # Enhanced contract data models
5. integration/blueprint_adapter.py  # Adapt synth blueprints
```

### Phase 2: Contract System (Week 2)
```python
6. contracts/contract_validator.py   # Validate deliverables vs contracts
7. contracts/mock_generator.py       # Generate mocks from contracts
8. contracts/integration_tester.py   # Test contract compatibility
```

### Phase 3: Migration (Week 3)
```python
9. migration/v1_to_v2_adapter.py     # Backward compatibility
10. tests/test_team_execution_v2.py  # Comprehensive tests
11. docs/TEAM_EXECUTION_V2_GUIDE.md  # Usage documentation
```

---

## Example Usage

### Old Way (V1 - Scripted)
```python
# Hardcoded, manual, scripted
engine = AutonomousSDLCEngine(
    selected_personas=["requirement_analyst", "backend_developer", "frontend_developer"],
    output_dir="./project"
)
result = await engine.execute("Build login system")
```

### New Way (V2 - AI-Driven)
```python
# AI-driven, blueprint-based, contract-first
engine = TeamExecutionEngineV2()

# AI analyzes and creates optimal team
result = await engine.execute(
    requirement="Build user authentication with social login",
    constraints={
        "timeline": "3 days",
        "quality_threshold": 0.85,
        "prefer_parallel": True
    }
)

# Behind the scenes:
# 1. AI analyzes: "feature_development, moderate complexity, parallelizable"
# 2. Searches blueprints: "parallel-contract-first" (best match)
# 3. Designs contracts: backend_api_contract, frontend_ui_contract
# 4. Creates team: 3 personas with 2 contracts
# 5. Executes: Backend builds API, Frontend uses mock simultaneously
# 6. Validates: Contracts fulfilled, integration tests pass
# 7. Returns: result with timeline savings and quality scores
```

---

## Migration Strategy

### Backward Compatibility
Keep `team_execution.py` (V1) for existing workflows:
```python
# V1 still works
from team_execution import AutonomousSDLCEngineV3_1_Resumable
```

### Gradual Migration
Add V2 alongside V1:
```python
# V2 for new features
from team_execution_v2 import TeamExecutionEngineV2
```

### Feature Flag
```python
if USE_V2_ENGINE:
    engine = TeamExecutionEngineV2()
else:
    engine = AutonomousSDLCEngineV3_1_Resumable()
```

---

## Benefits Summary

| Aspect | V1 (Current) | V2 (Proposed) |
|--------|--------------|---------------|
| **Requirement Analysis** | Hardcoded keyword matching | AI-driven classification |
| **Team Composition** | Manual persona selection | AI + blueprint selection |
| **Contracts** | Embedded in personas | Separate, versioned artifacts |
| **Parallel Execution** | Limited, manual | Blueprint-driven, automatic |
| **Reusability** | Low (tight coupling) | High (persona + contract separation) |
| **Scalability** | Fixed patterns | 12+ blueprints + elastic scaling |
| **Validation** | Quality gates only | Quality gates + contract verification |
| **Testability** | Hard (integrated) | Easy (mocks from contracts) |
| **Maintainability** | 2800 lines, complex | Modular, declarative |
| **AI-Driven** | 20% (quality only) | 80% (analysis, design, validation) |

---

## Next Steps

1. **Review & Approve**: Confirm this design aligns with your vision
2. **Implement Foundation**: Create V2 engine skeleton
3. **Build AI Agents**: TeamComposer and ContractDesigner
4. **Integrate Blueprints**: Adapt synth blueprint system
5. **Test & Validate**: Comprehensive testing
6. **Deploy**: Gradual rollout with V1 fallback

---

## Questions for Clarification

1. **Contract Storage**: Should contracts be stored in database (PostgreSQL via StateManager) or file-based (JSON/YAML)?

2. **Blueprint Customization**: Should users be able to create custom blueprints, or only use predefined ones?

3. **Persona Repository**: Where are persona definitions stored? maestro-engine/src/personas/ or hive/personas.py?

4. **AI Agent Implementation**: Use Claude Code SDK for AI agents, or different approach?

5. **Migration Timeline**: Aggressive (replace V1 in 2 weeks) or conservative (run parallel for 2 months)?

Ready to proceed with implementation! 🚀
