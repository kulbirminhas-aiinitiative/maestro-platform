# External Persona Integration Analysis

**Date**: 2025-10-04
**Subject**: Integration of maestro-engine JSON persona definitions into enhanced_sdlc_engine.py

---

## 📊 Current State Analysis

### Enhanced SDLC Engine (Current)

**File**: `enhanced_sdlc_engine.py`

**Persona Definition**: Hardcoded in Python classes
```python
class RequirementsAnalystAgent(SDLCPersonaAgent):
    def __init__(self, coordination_server):
        super().__init__(
            persona_id="requirements_analyst",
            coordination_server=coordination_server,
            role=AgentRole.ANALYST,
            persona_name="Requirements Analyst",
            expertise=[
                "Requirements gathering and analysis",  # HARDCODED
                "User story creation",                 # HARDCODED
                # ...
            ],
            expected_deliverables=[
                "REQUIREMENTS.md - Comprehensive requirements document",  # HARDCODED
                # ...
            ]
        )
```

**Issues**:
- ❌ Hardcoded expertise areas
- ❌ Hardcoded deliverables
- ❌ Duplicate definitions (if used elsewhere)
- ❌ No schema validation
- ❌ No versioning
- ❌ Hard to update (code changes required)

---

### Maestro-Engine Persona System (External)

**Location**: `/home/ec2-user/projects/maestro-engine/src/personas/definitions/`

**Format**: JSON Schema v3.0

**Structure**:
```json
{
  "persona_id": "requirement_analyst",
  "schema_version": "3.0",
  "version": "1.0.0",
  "display_name": "Requirement Analyst",

  "metadata": { ... },
  "role": {
    "primary_role": "business_analyst",
    "experience_level": 9,
    "autonomy_level": 8,
    "specializations": [...]
  },
  "capabilities": {
    "core": [...],
    "tools": [...]
  },
  "contracts": {
    "input": { "required": [...], "optional": [...] },
    "output": { "required": [...], "optional": [...] }
  },
  "dependencies": {
    "depends_on": [],
    "required_by": [...],
    "collaboration_with": [...]
  },
  "execution": {
    "timeout_seconds": 300,
    "max_retries": 3,
    "priority": 1,
    "parallel_capable": false,
    "estimated_duration_seconds": 120
  },
  "prompts": {
    "system_prompt": "...",
    "task_prompt_template": "..."
  },
  "quality_metrics": { ... },
  "intelligence": { ... }  // Domain intelligence for requirement_analyst
}
```

**Benefits**:
- ✅ Single source of truth
- ✅ Schema validated (Pydantic)
- ✅ Versioned (schema 3.0, version 1.0.0)
- ✅ Rich metadata
- ✅ Dependency tracking
- ✅ Execution configuration
- ✅ Quality metrics
- ✅ Domain intelligence (for requirement_analyst)
- ✅ Easy to update (edit JSON)
- ✅ Consistent across all services

---

### Existing Adapter (personas.py)

**File**: `/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/personas.py`

**How it works**:
```python
from src.personas import get_adapter, MaestroPersonaAdapter

class SDLCPersonas:
    @staticmethod
    def get_all_personas() -> Dict[str, Dict[str, Any]]:
        adapter = SDLCPersonas._get_adapter()
        personas = adapter.get_all_personas()
        return personas

    @staticmethod
    def requirement_analyst() -> Dict[str, Any]:
        return SDLCPersonas.get_all_personas()["requirement_analyst"]
```

**What it provides**:
```python
persona = SDLCPersonas.requirement_analyst()
# Returns:
{
    "persona_id": "requirement_analyst",
    "name": "Requirement Analyst",
    "role": { ... },
    "capabilities": { ... },
    "prompts": {
        "system_prompt": "...",
        "task_prompt_template": "..."
    },
    "dependencies": { ... },
    "execution": { ... },
    # etc.
}
```

---

## 🎯 Integration Benefits

### 1. Single Source of Truth

**Before (Hardcoded)**:
- Persona definitions in enhanced_sdlc_engine.py
- Possibly duplicated in other files
- Different definitions in different projects

**After (External JSON)**:
- One JSON file per persona
- All projects reference same definitions
- Update JSON → all projects benefit

---

### 2. Rich Metadata

**JSON provides**:
```json
{
  "dependencies": {
    "depends_on": ["requirement_analyst", "solution_architect"],
    "required_by": ["qa_engineer", "devops_engineer"],
    "collaboration_with": ["frontend_developer", "database_administrator"]
  },
  "execution": {
    "parallel_capable": true,  // Can run in parallel!
    "estimated_duration_seconds": 200,
    "priority": 4
  }
}
```

**Can use for**:
- ✅ Auto-determine execution order (based on dependencies)
- ✅ Auto-detect parallel execution opportunities (parallel_capable)
- ✅ Timeout management (timeout_seconds)
- ✅ Priority-based scheduling

---

### 3. Contract Validation

**JSON contracts**:
```json
{
  "contracts": {
    "input": {
      "required": ["architecture_design", "functional_requirements"],
      "optional": ["database_requirements"]
    },
    "output": {
      "required": ["api_implementation", "database_schema"],
      "optional": ["unit_tests"]
    }
  }
}
```

**Can validate**:
- ✅ Input requirements met before execution
- ✅ Output deliverables created after execution
- ✅ Fail fast if dependencies missing

---

### 4. Execution Configuration

**JSON provides**:
```json
{
  "execution": {
    "timeout_seconds": 300,
    "max_retries": 3,
    "priority": 1,
    "parallel_capable": false,
    "estimated_duration_seconds": 120
  }
}
```

**Can use for**:
- ✅ Automatic timeout enforcement
- ✅ Retry logic on failures
- ✅ Progress estimation
- ✅ Priority-based scheduling

---

### 5. Domain Intelligence

**requirement_analyst.json includes**:
```json
{
  "intelligence": {
    "domains": {
      "ecommerce": {
        "keywords": ["product", "cart", "checkout", "payment"],
        "platforms": ["shopify", "woocommerce"],
        "complexity_weight": 0.8,
        "typical_features": ["product_catalog", "shopping_cart"]
      }
    },
    "platform_indicators": {
      "monday.com": ["board", "pulse", "workspace"],
      "salesforce": ["salesforce", "sfdc", "apex"]
    }
  }
}
```

**Can use for**:
- ✅ Automatic domain detection
- ✅ Platform recognition
- ✅ Complexity assessment
- ✅ Feature suggestions

---

## 🔧 Integration Strategy

### Option 1: Full Integration (Recommended)

**Completely replace hardcoded personas with JSON-loaded definitions**

**Architecture**:
```python
class SDLCPersonaAgent(TeamAgent):
    def __init__(self, persona_id: str, coordination_server):
        # Load from JSON
        persona_def = SDLCPersonas.get_all_personas()[persona_id]

        # Extract from JSON
        role = self._map_role(persona_def["role"]["primary_role"])
        system_prompt = persona_def["prompts"]["system_prompt"]

        config = AgentConfig(
            agent_id=persona_id,
            role=role,
            system_prompt=system_prompt  # From JSON
        )
        super().__init__(config, coordination_server)

        # Store persona definition
        self.persona_def = persona_def
```

**Benefits**:
- ✅ Single source of truth
- ✅ Rich metadata available
- ✅ Easy to update personas
- ✅ Consistent across projects

**Changes Required**:
- Refactor agent __init__ to load from JSON
- Map JSON roles to AgentRole enum
- Use JSON system_prompt instead of hardcoded

---

### Option 2: Hybrid Approach

**Use JSON for data, keep class structure**

```python
class RequirementsAnalystAgent(SDLCPersonaAgent):
    PERSONA_ID = "requirement_analyst"

    def __init__(self, coordination_server):
        # Load definition from JSON
        persona_def = SDLCPersonas.requirement_analyst()

        super().__init__(
            persona_id=self.PERSONA_ID,
            coordination_server=coordination_server,
            persona_definition=persona_def  # Pass JSON
        )
```

**Benefits**:
- ✅ Type safety (specific classes)
- ✅ JSON data source
- ✅ Easy migration

---

### Option 3: Dynamic Factory

**No hardcoded classes, create dynamically**

```python
def create_persona_agent(persona_id: str, coordination_server):
    """Factory: creates any persona agent from JSON definition"""
    persona_def = SDLCPersonas.get_all_personas()[persona_id]

    # Create generic agent with JSON config
    agent = SDLCPersonaAgent(
        persona_id=persona_id,
        coordination_server=coordination_server,
        persona_definition=persona_def
    )

    return agent

# Usage:
analyst = create_persona_agent("requirement_analyst", coord_server)
backend = create_persona_agent("backend_developer", coord_server)
```

**Benefits**:
- ✅ No class per persona
- ✅ Add new personas without code changes
- ✅ Fully data-driven

**Drawbacks**:
- ❌ Less type safety
- ❌ No IDE autocomplete

---

## 🚨 Critical Recommendations

### 1. **Use External JSON Definitions** (Critical)

**Recommendation**: Migrate from hardcoded to JSON-based personas

**Why**:
- Single source of truth across all projects
- Schema validation ensures quality
- Version control for persona definitions
- Easy updates without code changes
- Rich metadata not available in hardcoded approach

**Action**:
```python
# BEFORE (hardcoded)
expertise=[
    "Requirements gathering and analysis",
    "User story creation"
]

# AFTER (from JSON)
expertise = persona_def["role"]["specializations"]
# Loaded from requirement_analyst.json
```

---

### 2. **Leverage Dependency Information** (High Priority)

**Recommendation**: Use JSON `dependencies` to auto-determine execution order

**Why**:
- No manual priority configuration needed
- Automatic dependency resolution
- Ensures proper execution order

**Implementation**:
```python
def _determine_execution_order(self, personas: List[str]) -> List[str]:
    """Auto-determine order based on JSON dependencies"""

    # Load all persona definitions
    persona_defs = {p: SDLCPersonas.get_all_personas()[p] for p in personas}

    # Build dependency graph
    graph = {}
    for p_id, p_def in persona_defs.items():
        depends_on = p_def["dependencies"]["depends_on"]
        graph[p_id] = [d for d in depends_on if d in personas]

    # Topological sort
    return topological_sort(graph)
```

**Benefit**: Automatic execution ordering!

---

### 3. **Use Parallel Execution Hints** (High Priority)

**Recommendation**: Use JSON `execution.parallel_capable` flag

**Why**:
- JSON already tells us which personas can run in parallel
- No manual configuration needed

**Implementation**:
```python
async def _execute_implementation_phase(self, requirement: str):
    personas = ["backend_developer", "database_administrator",
                "frontend_developer", "ui_ux_designer"]

    # Check which can run in parallel
    persona_defs = {p: SDLCPersonas.get_all_personas()[p] for p in personas}

    parallel_capable = [
        p for p, def_ in persona_defs.items()
        if def_["execution"]["parallel_capable"]
    ]

    # Execute parallel-capable personas in parallel
    if parallel_capable:
        results = await asyncio.gather(*[
            create_persona_agent(p, self.coord_server).execute_work(...)
            for p in parallel_capable
        ])
```

**Benefit**: Data-driven parallelization!

---

### 4. **Implement Contract Validation** (Medium Priority)

**Recommendation**: Validate inputs/outputs against JSON contracts

**Why**:
- Fail fast if dependencies missing
- Ensure deliverables created
- Better error messages

**Implementation**:
```python
async def execute_work(self, requirement: str, output_dir: Path, coordinator: TeamCoordinator):
    # Validate inputs
    self._validate_inputs(coordinator)

    # Execute
    result = await self._do_work(requirement, output_dir, coordinator)

    # Validate outputs
    self._validate_outputs(result, output_dir)

    return result

def _validate_inputs(self, coordinator):
    """Validate required inputs from contracts"""
    required_inputs = self.persona_def["contracts"]["input"]["required"]

    # Check knowledge items exist
    knowledge = coordinator.shared_workspace["knowledge"]

    for req_input in required_inputs:
        if req_input not in knowledge:
            raise ValueError(
                f"{self.agent_id} requires '{req_input}' but it's not available. "
                f"Ensure dependency personas have run first."
            )
```

**Benefit**: Robust validation!

---

### 5. **Use System Prompts from JSON** (Critical)

**Recommendation**: Use `prompts.system_prompt` from JSON

**Why**:
- Single source of truth for prompts
- Can A/B test prompts by updating JSON
- Consistency across projects

**Implementation**:
```python
class SDLCPersonaAgent(TeamAgent):
    def __init__(self, persona_id: str, coordination_server, persona_def: Dict):

        # Use system prompt from JSON
        system_prompt = persona_def["prompts"]["system_prompt"]

        config = AgentConfig(
            agent_id=persona_id,
            role=self._map_role(persona_def["role"]["primary_role"]),
            system_prompt=system_prompt  # From JSON!
        )
        super().__init__(config, coordination_server)
```

---

### 6. **Leverage Quality Metrics** (Low Priority - Future)

**Recommendation**: Use JSON quality metrics for validation

**Implementation** (future):
```python
def _validate_output_quality(self, result):
    """Validate output meets quality thresholds"""
    metrics = self.persona_def["quality_metrics"]["expected_output_quality"]

    # Check code quality threshold
    if "code_quality_threshold" in metrics:
        quality_score = analyze_code_quality(result)
        if quality_score < metrics["code_quality_threshold"]:
            raise QualityError(f"Code quality {quality_score} below threshold")
```

---

### 7. **Use Timeout Configuration** (Medium Priority)

**Recommendation**: Use `execution.timeout_seconds` from JSON

**Implementation**:
```python
async def execute_work(self, requirement: str, output_dir: Path, coordinator: TeamCoordinator):
    timeout = self.persona_def["execution"]["timeout_seconds"]

    try:
        result = await asyncio.wait_for(
            self._do_work(requirement, output_dir, coordinator),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise PersonaTimeoutError(
            f"{self.agent_id} exceeded timeout of {timeout}s"
        )
```

---

## 📝 Implementation Plan

### Phase 1: Basic Integration (Week 1)

**Goal**: Replace hardcoded data with JSON

**Tasks**:
1. ✅ Refactor `SDLCPersonaAgent` to accept `persona_definition` dict
2. ✅ Load system_prompt from JSON
3. ✅ Load expertise/specializations from JSON
4. ✅ Map JSON roles to AgentRole enum
5. ✅ Test with one persona (requirement_analyst)
6. ✅ Migrate all 11 personas

**Result**: All personas use JSON definitions

---

### Phase 2: Dependency-Based Execution (Week 2)

**Goal**: Auto-determine execution order

**Tasks**:
1. ✅ Parse `dependencies.depends_on` from JSON
2. ✅ Implement topological sort
3. ✅ Replace hardcoded execution order
4. ✅ Test dependency resolution
5. ✅ Handle circular dependencies

**Result**: Data-driven execution ordering

---

### Phase 3: Contract Validation (Week 3)

**Goal**: Validate inputs/outputs

**Tasks**:
1. ✅ Implement input validation
2. ✅ Implement output validation
3. ✅ Add helpful error messages
4. ✅ Test validation logic

**Result**: Robust contract enforcement

---

### Phase 4: Advanced Features (Week 4)

**Goal**: Leverage all JSON metadata

**Tasks**:
1. ✅ Use `parallel_capable` flag
2. ✅ Implement timeout enforcement
3. ✅ Add retry logic
4. ✅ Progress estimation
5. ✅ Quality metrics (future)

**Result**: Full JSON integration

---

## 🔍 Code Example: Integrated Version

```python
class SDLCPersonaAgent(TeamAgent):
    """Base class for SDLC personas - loads from JSON definitions"""

    def __init__(self, persona_id: str, coordination_server):
        # Load persona definition from JSON
        persona_def = SDLCPersonas.get_all_personas()[persona_id]

        # Extract configuration
        system_prompt = persona_def["prompts"]["system_prompt"]
        role = self._map_role(persona_def["role"]["primary_role"])

        config = AgentConfig(
            agent_id=persona_id,
            role=role,
            system_prompt=system_prompt
        )
        super().__init__(config, coordination_server)

        # Store persona definition for later use
        self.persona_def = persona_def
        self.persona_name = persona_def["display_name"]
        self.specializations = persona_def["role"]["specializations"]
        self.timeout = persona_def["execution"]["timeout_seconds"]
        self.parallel_capable = persona_def["execution"]["parallel_capable"]

    @staticmethod
    def _map_role(primary_role: str) -> AgentRole:
        """Map JSON role to SDK AgentRole enum"""
        role_mapping = {
            "business_analyst": AgentRole.ANALYST,
            "architect": AgentRole.ARCHITECT,
            "backend_developer": AgentRole.DEVELOPER,
            "frontend_developer": AgentRole.DEVELOPER,
            "qa_engineer": AgentRole.TESTER,
            "devops_engineer": AgentRole.DEPLOYER,
            "security_specialist": AgentRole.REVIEWER,
            "technical_writer": AgentRole.DEVELOPER,
            "database_administrator": AgentRole.DEVELOPER,
            "ui_ux_designer": AgentRole.DEVELOPER
        }
        return role_mapping.get(primary_role, AgentRole.DEVELOPER)

    def _validate_inputs(self, coordinator: TeamCoordinator):
        """Validate required inputs are available"""
        required = self.persona_def["contracts"]["input"]["required"]
        knowledge = coordinator.shared_workspace["knowledge"]

        missing = [r for r in required if r not in knowledge]
        if missing:
            raise ValueError(
                f"{self.agent_id} requires: {missing}\n"
                f"Available knowledge: {list(knowledge.keys())}"
            )

    async def execute_work(self, requirement: str, output_dir: Path,
                          coordinator: TeamCoordinator) -> Dict[str, Any]:
        """Execute with timeout and validation"""

        # Validate inputs
        if self.persona_def["contracts"]["input"]["required"]:
            self._validate_inputs(coordinator)

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                self._do_work(requirement, output_dir, coordinator),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise PersonaTimeoutError(
                f"{self.agent_id} exceeded timeout of {self.timeout}s"
            )

        return result


class EnhancedSDLCEngine:
    """SDK-powered SDLC with JSON persona definitions"""

    def _determine_execution_order(self, personas: List[str]) -> List[str]:
        """Auto-determine order based on JSON dependencies"""

        # Load definitions
        persona_defs = {
            p: SDLCPersonas.get_all_personas()[p]
            for p in personas
        }

        # Build dependency graph
        graph = {}
        for p_id, p_def in persona_defs.items():
            depends_on = p_def["dependencies"]["depends_on"]
            # Only include dependencies that are in our persona list
            graph[p_id] = [d for d in depends_on if d in personas]

        # Topological sort
        return self._topological_sort(graph)

    def _get_parallel_groups(self, personas: List[str]) -> List[List[str]]:
        """Group personas that can run in parallel"""

        persona_defs = {
            p: SDLCPersonas.get_all_personas()[p]
            for p in personas
        }

        # Group by parallel capability and dependencies
        groups = []
        for p_id, p_def in persona_defs.items():
            if p_def["execution"]["parallel_capable"]:
                # Can run in parallel
                # Group with others at same dependency level
                ...

        return groups
```

---

## 🎯 Critical Recommendations Summary

### Must Do (Critical)

1. **✅ Use External JSON Definitions**
   - Replace all hardcoded persona data
   - Load from maestro-engine JSON files
   - Single source of truth

2. **✅ Use JSON System Prompts**
   - Load `prompts.system_prompt` from JSON
   - Consistency across projects
   - Easy prompt updates

3. **✅ Map JSON Roles to SDK AgentRole**
   - Create mapping function
   - `business_analyst` → `AgentRole.ANALYST`
   - `backend_developer` → `AgentRole.DEVELOPER`

### Should Do (High Priority)

4. **✅ Leverage Dependency Information**
   - Auto-determine execution order
   - Parse `dependencies.depends_on`
   - Topological sort

5. **✅ Use Parallel Execution Hints**
   - Check `execution.parallel_capable`
   - Auto-parallelize where possible
   - Data-driven optimization

6. **✅ Implement Contract Validation**
   - Validate `contracts.input.required`
   - Validate `contracts.output.required`
   - Better error messages

### Could Do (Medium Priority)

7. **✅ Use Timeout Configuration**
   - Enforce `execution.timeout_seconds`
   - Prevent hanging personas
   - Better UX

8. **✅ Implement Retry Logic**
   - Use `execution.max_retries`
   - Handle transient failures
   - More robust

### Future (Low Priority)

9. **○ Quality Metrics**
   - Validate output quality
   - Use `quality_metrics` thresholds
   - Future enhancement

10. **○ Domain Intelligence**
    - Use requirement_analyst's domain intelligence
    - Auto-detect project type
    - Feature suggestions

---

## 📊 Impact Analysis

### Code Changes Required

| File | Changes | Effort |
|------|---------|--------|
| `enhanced_sdlc_engine.py` | Refactor agent classes, add JSON loading | Medium |
| `personas.py` | Already done! ✅ | None |
| New: `persona_factory.py` | Create agent factory | Low |
| New: `dependency_resolver.py` | Topological sort | Low |

### Benefits

| Benefit | Impact | Timeline |
|---------|--------|----------|
| Single source of truth | High | Immediate |
| Easy persona updates | High | Immediate |
| Auto execution ordering | High | Week 2 |
| Contract validation | Medium | Week 3 |
| Parallel optimization | Medium | Week 2 |
| Timeout enforcement | Low | Week 3 |

### Risks

| Risk | Mitigation |
|------|-----------|
| JSON file not found | Check file existence, helpful error |
| Invalid JSON schema | Pydantic validation in adapter |
| Circular dependencies | Detect and fail with clear error |
| Role mapping incomplete | Add default fallback |

---

## 🎉 Conclusion

**Critical Recommendations**:

1. ✅ **MUST**: Migrate to JSON persona definitions
2. ✅ **MUST**: Use JSON system prompts
3. ✅ **SHOULD**: Leverage dependency auto-ordering
4. ✅ **SHOULD**: Use parallel_capable hints
5. ✅ **COULD**: Implement contract validation

**Why This Matters**:
- Single source of truth across all projects
- Rich metadata enables advanced features
- Easy to update (edit JSON, not code)
- Schema validated (Pydantic)
- Future-proof (version 3.0)

**Recommended Approach**: **Option 1 - Full Integration**
- Completely replace hardcoded with JSON
- Maximum benefit from metadata
- Consistent with maestro-engine

**Next Step**: Create `enhanced_sdlc_engine_v2.py` with full JSON integration

---

**Files to Review**:
- ✅ `personas.py` - External JSON adapter (already done!)
- ✅ `/home/ec2-user/projects/maestro-engine/src/personas/definitions/*.json` - Persona definitions
- 📝 `enhanced_sdlc_engine.py` - Current hardcoded version
- 📝 `enhanced_sdlc_engine_v2.py` - New JSON-integrated version (to create)
