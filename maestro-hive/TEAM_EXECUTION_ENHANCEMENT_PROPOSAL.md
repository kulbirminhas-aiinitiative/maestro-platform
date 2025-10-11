# Team Execution Enhancement Proposal
## Integrating Blueprint Architecture + Enhanced Contract Management

**Date:** 2025
**Status:** PROPOSAL FOR REVIEW
**Priority:** HIGH - Critical for scalable team orchestration

---

## Executive Summary

This document proposes critical enhancements to `team_execution.py` by integrating the new **Blueprint Architecture** from synth and improving **Contract Management** for better parallel team coordination. The current implementation mixes persona execution with contract handling, creating tight coupling and limiting scalability.

### Key Problems Identified

1. **Hardcoded Team Patterns** - Teams are created programmatically instead of using declarative blueprints
2. **Contracts Embedded in Personas** - Contract definitions are mixed with persona logic, violating separation of concerns
3. **Limited Team Flexibility** - Cannot easily query, search, or compose teams based on project requirements
4. **No Contract-Persona Separation** - Contracts should be add-ons to personas, not embedded within them
5. **Missing Blueprint Integration** - Not leveraging the superior blueprint system from synth

---

## Current Architecture Analysis

### team_execution.py (Current State)

```python
# 2803 lines - Large monolithic file
# Main Components:
1. PersonaExecutionContext - Tracks individual persona work
2. PersonaReuseClient - ML-based artifact reuse
3. AutonomousSDLCEngineV3_1_Resumable - Main orchestrator
4. Persona execution with quality gates
5. Session management and resumable workflows
```

**Strengths:**
- ✅ Robust persona execution engine
- ✅ Quality gate validation system
- ✅ Resumable sessions
- ✅ Persona-level artifact reuse (V3.1)
- ✅ Deployment validation
- ✅ Message-based conversation history (AutoGen-inspired)

**Weaknesses:**
- ❌ No blueprint-based team composition
- ❌ Hardcoded execution order logic
- ❌ Limited team pattern flexibility
- ❌ No searchable team patterns
- ❌ Manual team assembly

### contract_manager.py (Current State)

```python
# 396 lines - Contract versioning system
# Main Components:
1. ContractManager - Handles contract lifecycle
2. Version-controlled API contracts
3. Breaking change detection
4. Consumer dependency tracking
```

**Strengths:**
- ✅ Solid contract versioning
- ✅ Breaking change detection
- ✅ Consumer tracking
- ✅ Contract evolution support

**Weaknesses:**
- ❌ No integration with persona execution
- ❌ Contracts not attached to personas
- ❌ No persona-contract metadata linking
- ❌ Limited discoverability

### personas.py (Current State)

```python
# References centralized JSON definitions from maestro-engine
# Main Components:
1. SDLCPersonas - Loads personas from JSON
2. Centralized persona definitions
3. Backward compatibility layer
```

**Strengths:**
- ✅ Centralized JSON-based definitions
- ✅ No hardcoding
- ✅ Schema validation (Pydantic)
- ✅ Single source of truth

**Weaknesses:**
- ❌ No contract attachment mechanism
- ❌ No capability/specialization metadata
- ❌ Limited team composition hints

---

## Proposed Solution Architecture

### 1. Blueprint-Based Team Orchestration

**Integrate synth's Blueprint System** into team_execution.py:

```python
# NEW: Import blueprint system from synth
from maestro_ml.modules.teams.blueprints import (
    create_team_from_blueprint,
    search_blueprints,
    TeamBlueprint,
    BLUEPRINT_REGISTRY
)

class EnhancedSDLCEngine:
    """
    Enhanced SDLC Engine with Blueprint Integration
    
    Key Changes:
    1. Teams created from blueprints (declarative)
    2. Searchable team patterns
    3. Dynamic team composition based on requirements
    4. Rich metadata for discovery
    """
    
    def __init__(self, ...):
        self.blueprint_registry = BLUEPRINT_REGISTRY
        self.team_composition_strategy = "blueprint"  # or "manual"
        
    async def select_optimal_team_blueprint(
        self,
        requirement: str,
        project_characteristics: Dict[str, Any]
    ) -> TeamBlueprint:
        """
        NEW: AI-powered blueprint selection
        
        Given requirements, automatically select optimal team blueprint:
        - Simple project → sequential-basic
        - Complex API → parallel-elastic
        - Security audit → specialized-security
        - Full SDLC → hybrid-full-sdlc
        """
        # Use ML to analyze requirements
        characteristics = await self._analyze_requirements(requirement)
        
        # Search blueprints by characteristics
        candidates = search_blueprints(
            execution_mode=characteristics.get("execution_mode"),
            scaling=characteristics.get("scaling"),
            capabilities=characteristics.get("capabilities", [])
        )
        
        # Rank by match score
        best_match = self._rank_blueprints(candidates, characteristics)
        
        return best_match
        
    async def create_team_from_blueprint(
        self,
        blueprint_id: str,
        requirement: str
    ) -> List[str]:
        """
        Create team using blueprint pattern
        
        Returns ordered list of personas to execute
        """
        blueprint = self.blueprint_registry.get_blueprint(blueprint_id)
        
        if not blueprint:
            raise ValueError(f"Blueprint not found: {blueprint_id}")
            
        # Extract personas from blueprint
        personas = blueprint.personas
        
        # Apply blueprint's coordination strategy
        execution_order = self._apply_coordination_strategy(
            personas,
            blueprint.archetype.coordination
        )
        
        return execution_order
```

**Benefits:**
- 🎯 Declarative team composition
- 📊 Searchable and queryable patterns
- 🔄 Easy to add new patterns (just data)
- 🧬 Metadata-rich for discovery
- ⚡ Consistent with synth architecture

### 2. Contract-Persona Separation (Add-On Model)

**Contracts should be add-ons to personas, not embedded:**

```python
# NEW: Contract attachment system
class PersonaContract:
    """
    Contract metadata attached to persona
    
    Separates contract concerns from persona execution logic
    """
    
    def __init__(
        self,
        persona_id: str,
        contract_id: str,
        contract_type: str,  # "provider" or "consumer"
        contract_specification: Dict[str, Any],
        mock_implementation: Optional[str] = None
    ):
        self.persona_id = persona_id
        self.contract_id = contract_id
        self.contract_type = contract_type
        self.specification = contract_specification
        self.mock = mock_implementation
        

class EnhancedPersonaExecutor:
    """
    Persona executor with contract awareness
    """
    
    async def execute_persona_with_contracts(
        self,
        persona_id: str,
        requirement: str,
        contracts: List[PersonaContract]
    ) -> PersonaExecutionContext:
        """
        Execute persona with attached contracts
        
        Contracts are provided as context, not embedded in persona logic
        """
        # Separate provider vs consumer contracts
        provider_contracts = [c for c in contracts if c.contract_type == "provider"]
        consumer_contracts = [c for c in contracts if c.contract_type == "consumer"]
        
        # Build enhanced prompt with contract context
        prompt = self._build_persona_prompt_with_contracts(
            persona_id,
            requirement,
            provider_contracts=provider_contracts,
            consumer_contracts=consumer_contracts
        )
        
        # Execute persona
        context = await self._execute_persona(persona_id, prompt)
        
        # Validate contract adherence
        await self._validate_contract_adherence(context, provider_contracts)
        
        return context
        
    def _build_persona_prompt_with_contracts(
        self,
        persona_id: str,
        requirement: str,
        provider_contracts: List[PersonaContract],
        consumer_contracts: List[PersonaContract]
    ) -> str:
        """
        Build prompt with contract context as add-on information
        """
        persona_config = self.persona_configs[persona_id]
        base_prompt = self._build_base_prompt(persona_config, requirement)
        
        # Add contract context as separate section
        contract_context = "\n\n" + "="*80 + "\n"
        contract_context += "API CONTRACTS (Add-On Context)\n"
        contract_context += "="*80 + "\n\n"
        
        if provider_contracts:
            contract_context += "YOU PROVIDE (Implement these contracts):\n"
            for contract in provider_contracts:
                contract_context += f"\n### {contract.contract_id}\n"
                contract_context += f"Type: {contract.specification.get('type')}\n"
                contract_context += f"Spec:\n```json\n{json.dumps(contract.specification, indent=2)}\n```\n"
                
        if consumer_contracts:
            contract_context += "\nYOU CONSUME (Use these mocks for now):\n"
            for contract in consumer_contracts:
                contract_context += f"\n### {contract.contract_id}\n"
                contract_context += f"Mock: {contract.mock}\n"
                contract_context += f"Spec:\n```json\n{json.dumps(contract.specification, indent=2)}\n```\n"
                
        return base_prompt + contract_context
```

**Benefits:**
- ✅ Clean separation: Personas focus on execution, contracts on interfaces
- ✅ Flexible: Contracts can be attached/detached dynamically
- ✅ Discoverable: Query personas by contract requirements
- ✅ Testable: Mock contracts for parallel development
- ✅ Evolvable: Update contracts without changing persona logic

### 3. Enhanced Contract Management Integration

**Integrate contract_manager.py with persona execution:**

```python
class ContractAwareSDLCEngine:
    """
    SDLC Engine with first-class contract support
    """
    
    def __init__(self, ...):
        self.contract_manager = ContractManager(state_manager)
        self.persona_contract_map: Dict[str, List[PersonaContract]] = {}
        
    async def execute_with_contracts(
        self,
        requirement: str,
        team_blueprint_id: str = None
    ) -> Dict[str, Any]:
        """
        Execute SDLC with contract-first approach
        
        Flow:
        1. Analyze requirements
        2. Select team blueprint
        3. Generate contracts (architecture phase)
        4. Attach contracts to personas
        5. Execute personas with contract context
        6. Validate contract adherence
        """
        
        # Step 1: Select team blueprint
        if not team_blueprint_id:
            blueprint = await self.select_optimal_team_blueprint(requirement, {})
            team_blueprint_id = blueprint.id
            
        execution_order = await self.create_team_from_blueprint(
            team_blueprint_id,
            requirement
        )
        
        # Step 2: Execute architecture phase to define contracts
        # requirement_analyst + solution_architect define contracts
        architecture_personas = [
            p for p in execution_order 
            if p in ["requirement_analyst", "solution_architect"]
        ]
        
        for persona_id in architecture_personas:
            await self._execute_persona(persona_id, requirement, session)
            
        # Step 3: Extract and register contracts
        contracts = await self._extract_contracts_from_architecture()
        
        for contract_spec in contracts:
            await self.contract_manager.create_contract(
                team_id=session.session_id,
                contract_name=contract_spec["name"],
                version="v0.1",
                contract_type=contract_spec["type"],
                specification=contract_spec["spec"],
                owner_role=contract_spec["owner_role"],
                owner_agent=contract_spec["owner_agent"]
            )
            
        # Step 4: Map contracts to personas
        await self._build_persona_contract_map(contracts, execution_order)
        
        # Step 5: Execute remaining personas with contract context
        development_personas = [
            p for p in execution_order
            if p not in architecture_personas
        ]
        
        for persona_id in development_personas:
            persona_contracts = self.persona_contract_map.get(persona_id, [])
            
            await self.execute_persona_with_contracts(
                persona_id,
                requirement,
                contracts=persona_contracts
            )
            
        return result
        
    async def _extract_contracts_from_architecture(self) -> List[Dict]:
        """
        Extract contract definitions from architecture docs
        
        Reads ARCHITECTURE.md and API_SPEC.md to find:
        - REST API endpoints
        - GraphQL schemas
        - Event streams
        - gRPC services
        """
        contracts = []
        
        # Parse architecture documents
        arch_file = self.output_dir / "ARCHITECTURE.md"
        if arch_file.exists():
            content = arch_file.read_text()
            
            # Use AI to extract contract specifications
            # (Could use Claude Code SDK or regex patterns)
            extracted = await self._ai_extract_contracts(content)
            contracts.extend(extracted)
            
        # Parse OpenAPI specs if exist
        api_spec = self.output_dir / "openapi.yaml"
        if api_spec.exists():
            spec = yaml.safe_load(api_spec.read_text())
            contracts.append({
                "name": "MainAPI",
                "type": "REST_API",
                "spec": spec,
                "owner_role": "backend_developer",
                "owner_agent": "backend_dev_001"
            })
            
        return contracts
        
    async def _build_persona_contract_map(
        self,
        contracts: List[Dict],
        personas: List[str]
    ):
        """
        Map contracts to personas (who provides, who consumes)
        
        Rules:
        - backend_developer provides REST APIs
        - frontend_developer consumes REST APIs
        - database_specialist provides data schemas
        - backend_developer consumes data schemas
        """
        for contract in contracts:
            contract_type = contract["type"]
            
            if contract_type == "REST_API":
                # Backend provides, Frontend consumes
                if "backend_developer" in personas:
                    self._add_contract_to_persona(
                        "backend_developer",
                        contract,
                        "provider"
                    )
                    
                if "frontend_developer" in personas:
                    self._add_contract_to_persona(
                        "frontend_developer",
                        contract,
                        "consumer"
                    )
                    
            elif contract_type == "DATABASE_SCHEMA":
                # Database specialist provides, Backend consumes
                if "database_specialist" in personas:
                    self._add_contract_to_persona(
                        "database_specialist",
                        contract,
                        "provider"
                    )
                    
                if "backend_developer" in personas:
                    self._add_contract_to_persona(
                        "backend_developer",
                        contract,
                        "consumer"
                    )
```

**Benefits:**
- 🔗 Contracts managed as first-class citizens
- 🔄 Contract evolution tracked across versions
- 🎯 Clear provider/consumer relationships
- ⚡ Enables true parallel development
- 📊 Contract adherence validation

---

## Proposed File Structure

### Enhanced team_execution.py

```
team_execution.py (refactored into modules):
├── core/
│   ├── engine.py                    # Main orchestrator
│   ├── persona_executor.py          # Persona execution logic
│   └── session_manager.py           # Session persistence
├── blueprints/
│   ├── team_selector.py             # Blueprint selection logic
│   ├── team_builder.py              # Team composition from blueprints
│   └── archetype_matcher.py         # Match requirements to archetypes
├── contracts/
│   ├── contract_extractor.py        # Extract contracts from architecture
│   ├── contract_mapper.py           # Map contracts to personas
│   ├── contract_validator.py        # Validate contract adherence
│   └── persona_contract.py          # PersonaContract model
└── quality/
    ├── quality_gate.py              # Quality validation
    ├── deployment_validator.py      # Deployment readiness
    └── validation_reporter.py       # Quality reports
```

### Enhanced contract_manager.py

```python
contract_manager.py (enhanced):
├── ContractManager                  # Existing contract lifecycle
├── PersonaContractRegistry          # NEW: Persona-contract mapping
├── ContractDiscovery                # NEW: Query contracts by persona
└── ContractEvolutionTracker         # NEW: Track contract changes
```

### Enhanced personas.py

```python
personas.py (metadata additions):
├── SDLCPersonas                     # Existing persona loader
├── PersonaContractMetadata          # NEW: Contract requirements per persona
├── PersonaCapabilityRegistry        # NEW: Searchable capabilities
└── PersonaTeamHints                 # NEW: Team composition hints
```

---

## Implementation Roadmap

### Phase 1: Blueprint Integration (Week 1)
- [ ] Import blueprint system from synth
- [ ] Add blueprint selection logic to team_execution.py
- [ ] Implement `select_optimal_team_blueprint()`
- [ ] Implement `create_team_from_blueprint()`
- [ ] Test with existing blueprints (sequential, parallel, hybrid)

### Phase 2: Contract-Persona Separation (Week 2)
- [ ] Create `PersonaContract` model
- [ ] Add contract attachment mechanism
- [ ] Implement `execute_persona_with_contracts()`
- [ ] Update prompt builder for contract context
- [ ] Test with mock contracts

### Phase 3: Contract Manager Integration (Week 3)
- [ ] Implement contract extraction from architecture docs
- [ ] Build persona-contract mapping logic
- [ ] Integrate contract versioning with personas
- [ ] Add contract adherence validation
- [ ] Test end-to-end contract-first workflow

### Phase 4: Enhanced Persona Metadata (Week 4)
- [ ] Add contract metadata to JSON persona definitions
- [ ] Implement capability-based persona search
- [ ] Add team composition hints
- [ ] Update maestro-engine persona schema (v3.1)
- [ ] Test persona discoverability

### Phase 5: Quality Integration (Week 5)
- [ ] Integrate contract validation with quality gates
- [ ] Add contract coverage metrics
- [ ] Validate contract-persona alignment
- [ ] Generate contract quality reports
- [ ] Test with quality-fabric

---

## Migration Strategy

### Backward Compatibility

Keep existing workflow operational during migration:

```python
class UnifiedSDLCEngine:
    """
    Unified engine supporting both legacy and enhanced modes
    """
    
    def __init__(
        self,
        mode: str = "enhanced",  # "legacy" or "enhanced"
        ...
    ):
        self.mode = mode
        
    async def execute(
        self,
        requirement: str,
        ...
    ) -> Dict[str, Any]:
        if self.mode == "legacy":
            return await self._legacy_execute(requirement)
        else:
            return await self._enhanced_execute_with_blueprints(requirement)
```

### Gradual Rollout

1. **Week 1-2**: Enhanced mode opt-in (--mode enhanced flag)
2. **Week 3-4**: Enhanced mode default, legacy fallback available
3. **Week 5-6**: Full migration, deprecate legacy mode

---

## Example: Enhanced Workflow

### Current Workflow (Manual)

```python
# Current: Manual team assembly
engine = AutonomousSDLCEngineV3_1_Resumable(
    selected_personas=[
        "requirement_analyst",
        "solution_architect",
        "backend_developer",
        "frontend_developer",
        "qa_engineer"
    ],
    ...
)

result = await engine.execute(requirement="Build blog platform")
```

### Enhanced Workflow (Blueprint-Based)

```python
# Enhanced: Automatic team selection + contracts
engine = EnhancedSDLCEngine(
    mode="enhanced",
    enable_contracts=True,
    ...
)

# Engine automatically:
# 1. Analyzes requirements
# 2. Selects optimal blueprint (e.g., parallel-elastic)
# 3. Extracts contracts from architecture
# 4. Maps contracts to personas
# 5. Executes with contract context

result = await engine.execute(
    requirement="Build blog platform with real-time comments",
    auto_select_blueprint=True  # Let AI choose best pattern
)

print(f"Selected blueprint: {result['blueprint_used']}")
# >>> "parallel-elastic"

print(f"Contracts created: {len(result['contracts'])}")
# >>> 3 (BlogAPI, CommentStream, UserAuth)

print(f"Parallel execution enabled: {result['parallel_enabled']}")
# >>> True (frontend/backend worked simultaneously)
```

---

## Critical Recommendations

### ⭐ Top Priority: Contract-Persona Separation

**Problem:** Currently, profiles ARE personas, and contracts are embedded within them.

**Solution:** 
```python
# WRONG (current approach)
class BackendDeveloper:
    def __init__(self):
        self.contracts = [...]  # Embedded - tight coupling
        
# RIGHT (proposed approach)
class BackendDeveloper:
    def __init__(self):
        pass  # Clean persona - no contract logic
        
# Contracts attached externally
persona_contracts = {
    "backend_developer": [
        PersonaContract("BlogAPI", type="provider"),
        PersonaContract("DatabaseSchema", type="consumer")
    ]
}
```

**Benefits:**
- ✅ Personas remain focused on execution
- ✅ Contracts can be reused across personas
- ✅ Clear separation of concerns
- ✅ Easier to test and maintain

### ⭐ Adopt Blueprint System Immediately

The blueprint system from synth is production-ready and superior:
- Declarative team patterns (data, not code)
- Searchable and queryable
- Rich metadata for discovery
- Easy to extend (just add JSON)
- 74% smaller factory code

**Action:** Import and integrate blueprints this week.

### ⭐ Contract-First for Parallel Teams

For true parallel execution:
1. Architecture phase defines ALL contracts upfront
2. Contracts registered in ContractManager
3. Frontend/Backend receive contract context
4. Both work simultaneously using mocks
5. Integration happens at the end

**Critical:** Don't let backend/frontend execute without contracts defined first.

---

## Success Metrics

### Before Enhancement
- ❌ Manual team assembly
- ❌ Sequential execution by default
- ❌ Contracts embedded in personas
- ❌ Limited team pattern flexibility
- ⏱️ Average project time: 45 minutes

### After Enhancement
- ✅ Automatic team selection via blueprints
- ✅ Parallel execution enabled
- ✅ Contracts as first-class add-ons
- ✅ Searchable team patterns
- ⏱️ Target project time: 25 minutes (45% reduction)

---

## Conclusion

The proposed enhancements represent a significant architectural upgrade:

1. **Blueprint Integration** - Move from manual to declarative team composition
2. **Contract-Persona Separation** - Clean architecture with add-on contracts
3. **Enhanced Contract Management** - First-class contract support
4. **Parallel Execution** - True concurrent team work with contracts

These changes align with industry best practices (contract-first development, declarative configuration, separation of concerns) and leverage the superior blueprint architecture already built in synth.

**Recommendation: Proceed with phased implementation starting with Blueprint Integration.**

---

## Appendix A: Code Examples

### Example 1: Blueprint-Based Team Creation

```python
# Select blueprint based on requirements
blueprint = await engine.select_optimal_team_blueprint(
    requirement="Build e-commerce platform with real-time inventory",
    project_characteristics={
        "complexity": "high",
        "real_time": True,
        "scale": "large"
    }
)

print(f"Selected: {blueprint.id}")
# >>> "parallel-elastic"

print(f"Execution mode: {blueprint.archetype.execution}")
# >>> "parallel"

print(f"Personas: {blueprint.personas}")
# >>> ["requirement_analyst", "solution_architect", "backend_developer", 
#      "frontend_developer", "database_specialist", "qa_engineer"]
```

### Example 2: Contract Attachment

```python
# Extract contracts from architecture
contracts = await engine._extract_contracts_from_architecture()

# Contract 1: E-commerce API
{
    "name": "EcommerceAPI",
    "type": "REST_API",
    "version": "v0.1",
    "spec": {
        "endpoints": [
            {"path": "/api/products", "method": "GET"},
            {"path": "/api/cart", "method": "POST"},
            {"path": "/api/checkout", "method": "POST"}
        ]
    },
    "owner_role": "backend_developer",
    "consumers": ["frontend_developer", "mobile_developer"]
}

# Attach to personas
await engine._build_persona_contract_map(contracts, execution_order)

# backend_developer receives:
{
    "persona_id": "backend_developer",
    "contracts": [
        PersonaContract("EcommerceAPI", type="provider", spec=...),
        PersonaContract("DatabaseSchema", type="consumer", spec=...)
    ]
}

# frontend_developer receives:
{
    "persona_id": "frontend_developer",
    "contracts": [
        PersonaContract("EcommerceAPI", type="consumer", mock="http://localhost:3001/api")
    ]
}
```

### Example 3: Parallel Execution with Contracts

```python
# Frontend and Backend execute in parallel
# Both have contract context, so no blocking

async def execute_parallel_phase():
    # Define contracts first (architecture phase)
    contracts = await define_contracts()
    
    # Execute frontend and backend concurrently
    backend_task = asyncio.create_task(
        execute_persona_with_contracts(
            "backend_developer",
            contracts=[
                PersonaContract("API", type="provider")
            ]
        )
    )
    
    frontend_task = asyncio.create_task(
        execute_persona_with_contracts(
            "frontend_developer",
            contracts=[
                PersonaContract("API", type="consumer", mock=True)
            ]
        )
    )
    
    # Wait for both to complete
    backend_result, frontend_result = await asyncio.gather(
        backend_task,
        frontend_task
    )
    
    # Validate contract adherence
    await validate_contracts(backend_result, frontend_result)
```

---

**End of Proposal**

*For questions or clarifications, please review the synth blueprint architecture at:*
- `synth/maestro_ml/modules/teams/archetypes.py`
- `synth/maestro_ml/modules/teams/team_blueprints.py`
- `synth/maestro_ml/modules/teams/team_factory.py`

*And current implementations at:*
- `maestro-hive/team_execution.py`
- `maestro-hive/contract_manager.py`
- `maestro-hive/personas.py`
