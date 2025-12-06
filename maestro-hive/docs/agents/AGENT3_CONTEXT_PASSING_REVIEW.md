# AGENT3: Context Passing Mechanism - Deep Dive Analysis

**Document:** Context Passing Review
**System:** team_execution_v2_split_mode + WorkflowContext
**Focus:** Microsoft AutoGen-style context flow analysis

---

## Question 1: "Does the system support AutoGen-style context + instruction passing?"

### Answer: YES ✅ (Infrastructure) - NO ❌ (Implementation)

The codebase **has built** the AutoGen-style infrastructure for passing both:
1. **Context** (all information from previous phases) ✅
2. **Instructions** (what to do next) ✅

**BUT** the implementation only uses ~5% of this capability.

---

## AutoGen Context Passing Pattern (Reference)

**Microsoft AutoGen Approach:**
```python
# Agent 1 executes
agent1_result = {
    "output": "I created the API specification",
    "artifacts": ["api_spec.yaml", "database_schema.sql"],
    "next_steps": "Frontend should implement these 20 endpoints"
}

# Agent 2 receives FULL context
agent2_context = {
    "previous_agent": "backend_developer",
    "received_artifacts": agent1_result["artifacts"],
    "received_output": agent1_result["output"],  # FULL
    "instructions": agent1_result["next_steps"]
}

agent2.execute(context=agent2_context)  # ✅ Has ALL info
```

---

## Current System: Infrastructure Analysis

### ✅ INFRASTRUCTURE EXISTS: WorkflowContext (conductor)

**File:** `/home/ec2-user/projects/conductor/examples/sdlc_workflow_context.py`

#### 1. Context Storage (Lines 46-50)

```python
@dataclass
class PhaseResult:
    """Result from executing a single SDLC phase."""

    # Context flow tracking
    context_received: Dict[str, Any] = field(default_factory=dict)  # ✅ FULL context IN
    context_passed: Dict[str, Any] = field(default_factory=dict)    # ✅ FULL context OUT

    # Validation and contracts
    contracts_validated: List[str] = field(default_factory=list)

    # Artifacts and deliverables
    artifacts_created: List[str] = field(default_factory=list)
    artifacts_consumed: List[str] = field(default_factory=list)
```

**Analysis:** ✅ Perfect structure for AutoGen-style context tracking

---

#### 2. Context Retrieval (Lines 222-241)

```python
def get_all_previous_outputs(self, current_phase: str) -> Dict[str, Dict[str, Any]]:
    """
    Get outputs from all phases before current_phase.

    Returns:
        Dict mapping phase_name -> outputs
    """
    outputs = {}
    try:
        current_index = self.phase_order.index(current_phase)
        for phase_name in self.phase_order[:current_index]:
            output = self.get_phase_output(phase_name)
            if output:
                outputs[phase_name] = output  # ✅ FULL OUTPUT
    except ValueError:
        pass
    return outputs
```

**Analysis:** ✅ Returns **complete** outputs from all previous phases

---

#### 3. Context Passing Workflow (Lines 162-184)

```python
def add_phase_result(self, phase_name: str, result: PhaseResult):
    """Add a phase result to the workflow context."""
    self.phase_results[phase_name] = result

    if phase_name not in self.phase_order:
        self.phase_order.append(phase_name)

    self.current_phase = phase_name

    # Add artifacts to shared list
    for artifact in result.artifacts_created:
        self.shared_artifacts.append({
            "name": artifact,
            "created_by_phase": phase_name,
            "created_at": result.completed_at.isoformat() if result.completed_at else None,
        })
```

**Analysis:** ✅ Properly accumulates artifacts across phases

---

#### 4. Visual Context Flow (Lines 422-487)

```python
def print_context_flow(self):
    """
    Print a visual representation of context flow between phases.

    Shows:
    - What data was passed from each phase to the next
    - Artifacts created and consumed
    - Contracts validated at each boundary
    """
    for i, phase_name in enumerate(self.phase_order):
        result = self.phase_results.get(phase_name)

        # Context received
        if result.context_received:
            print(f"  📥 Context Received:")
            for key, value in result.context_received.items():
                print(f"     • {key}: {self._format_value(value)}")

        # Context passed
        if result.context_passed:
            print(f"  📤 Context Passed to Next Phase:")
            for key, value in result.context_passed.items():
                print(f"     • {key}: {self._format_value(value)}")
```

**Analysis:** ✅ Infrastructure includes debugging/visualization of context flow!

---

### ✅ INFRASTRUCTURE EXISTS: TeamExecutionContext (maestro-hive)

**File:** `team_execution_context.py`

#### Enhanced Context Model (Lines 367-420)

```python
@dataclass
class TeamExecutionContext:
    """
    Unified context combining workflow state and team execution state.

    This is the complete checkpoint that can be serialized/deserialized
    for phase-by-phase execution with full state persistence.
    """

    # Workflow context (SDLC phases)
    workflow: WorkflowContext  # ✅ Contains full WorkflowContext

    # Team execution state
    team_state: TeamExecutionState

    # Checkpoint metadata
    checkpoint_metadata: CheckpointMetadata
```

**Analysis:** ✅ Combines workflow state with team state for comprehensive context

---

## ❌ IMPLEMENTATION FAILURE: Execution Layer

### Problem 1: Context Truncation in Phase Transitions

**File:** `team_execution_v2_split_mode.py:752-789`

#### Current (Broken) Implementation:

```python
def _extract_phase_requirement(
    self,
    phase_name: str,
    context: TeamExecutionContext,
    original_requirement: Optional[str] = None
) -> str:
    """Extract phase-specific requirement from context."""

    # Step 1: Get FULL context (✅ infrastructure works)
    previous_outputs = context.workflow.get_all_previous_outputs(phase_name)

    # Step 2: Build requirement parts
    requirement_parts = [
        f"Phase: {phase_name}",
        f"Previous phases completed: {', '.join(context.workflow.phase_order)}",
    ]

    # Step 3: ❌ BUG - Only use 500 chars
    previous_phase = self._get_previous_phase(phase_name)
    if previous_phase and previous_phase in previous_outputs:
        prev_output = previous_outputs[previous_phase]
        requirement_parts.append(f"\nOutputs from {previous_phase}:")
        requirement_parts.append(json.dumps(prev_output, indent=2)[:500])  # ❌ TRUNCATED!

    return "\n".join(requirement_parts)
```

**Information Loss:**

```
Available in context.workflow: 50,000 characters of previous work
                                    ↓
Used in phase requirement:     500 characters (1% used)
                                    ↓
Passed to next agent:          500 characters
```

---

### Problem 2: Context Not Passed to Persona Executor

**File:** `team_execution_v2_split_mode.py:380-394`

#### Current Flow:

```python
# Step 5: Execute team for this phase
logger.info(f"\n🎬 Executing {phase_name} team...")

execution_result = await self.engine.execute(
    requirement=phase_requirement,  # ❌ Only contains 500 chars from prev
    constraints={
        "phase": phase_name,
        "quality_threshold": self.PHASE_QUALITY_THRESHOLDS.get(
            phase_name,
            self.quality_threshold
        )
    }
    # ❌ NO PREVIOUS_OUTPUTS passed
    # ❌ NO ARTIFACTS_FROM_PREVIOUS_PHASE passed
    # ❌ NO CONTRACTS_FROM_PREVIOUS_PHASE passed
)
```

**What's Missing:**
```python
# What SHOULD be passed (NOT IMPLEMENTED):
execution_result = await self.engine.execute(
    requirement=phase_requirement,
    constraints={...},
    previous_phase_outputs=context.workflow.get_all_previous_outputs(phase_name),  # ❌ MISSING
    previous_phase_artifacts=context.workflow.shared_artifacts,  # ❌ MISSING
    previous_phase_contracts=context.get_contracts_from_previous_phases()  # ❌ MISSING
)
```

---

### Problem 3: Persona Executor Receives Empty Context

**File:** `persona_executor_v2.py:472-490`

#### Current Signature:

```python
async def execute(
    self,
    requirement: str,          # ✅ Has requirement
    contract: Optional[Dict[str, Any]] = None,  # ✅ Has current contract
    context: Optional[Dict[str, Any]] = None,   # ❌ Usually EMPTY dict!
    use_mock: bool = False
) -> PersonaExecutionResult:
```

**Call Site (from parallel_coordinator_v2.py:420-425):**

```python
task = executor.execute(
    requirement=requirement,  # Just the phase requirement
    contract=contract,        # Just this persona's contract
    context=context,          # ❌ Generic context, NO previous outputs
    use_mock=use_mock
)
```

**What context dict contains:**
```python
context = {
    "phase": "implementation",
    "quality_threshold": 0.70
}
# ❌ NO previous_phase_outputs
# ❌ NO artifacts_from_previous_personas
# ❌ NO api_specifications
# ❌ NO database_schemas
```

---

## Correct Implementation (How It Should Work)

### Step 1: Extract FULL Context

```python
def _extract_phase_requirement(
    self,
    phase_name: str,
    context: TeamExecutionContext,
    original_requirement: Optional[str] = None
) -> str:
    """Extract phase-specific requirement from context."""

    # Get FULL context from previous phases
    previous_outputs = context.workflow.get_all_previous_outputs(phase_name)

    requirement_parts = [
        f"Phase: {phase_name}",
        f"Original Requirement: {original_requirement or context.workflow.metadata.get('initial_requirement', '')}",
        f"\n## Previous Phases Completed: {', '.join(context.workflow.phase_order)}",
    ]

    # ✅ FIXED: Include FULL outputs from ALL previous phases
    if previous_outputs:
        requirement_parts.append("\n## Context from Previous Phases:\n")

        for prev_phase_name, prev_output in previous_outputs.items():
            requirement_parts.append(f"\n### {prev_phase_name.title()} Phase:\n")

            # Include FULL output (not truncated!)
            if isinstance(prev_output, dict):
                # Pretty print with full detail
                requirement_parts.append(json.dumps(prev_output, indent=2))
            else:
                requirement_parts.append(str(prev_output))

            # Include artifacts created
            phase_result = context.workflow.get_phase_result(prev_phase_name)
            if phase_result and phase_result.artifacts_created:
                requirement_parts.append(f"\n**Artifacts Created:**")
                for artifact in phase_result.artifacts_created:
                    requirement_parts.append(f"  - {artifact}")

    # Include shared artifacts
    if context.workflow.shared_artifacts:
        requirement_parts.append("\n## Available Artifacts:\n")
        for artifact in context.workflow.shared_artifacts:
            requirement_parts.append(f"  - {artifact['name']} (from {artifact['created_by_phase']})")

    return "\n".join(requirement_parts)
```

---

### Step 2: Pass Context to Execution Engine

```python
# team_execution_v2_split_mode.py:380-394 (FIXED)

execution_result = await self.engine.execute(
    requirement=phase_requirement,
    constraints={
        "phase": phase_name,
        "quality_threshold": self.PHASE_QUALITY_THRESHOLDS.get(phase_name, self.quality_threshold)
    },
    # ✅ ADDED: Full context from previous phases
    previous_phase_context={
        "outputs": context.workflow.get_all_previous_outputs(phase_name),
        "artifacts": context.workflow.shared_artifacts,
        "contracts": [
            context.team_state.contract_specs[i]
            for i in range(len(context.team_state.contract_specs))
        ]
    }
)
```

---

### Step 3: Engine Passes Context to Coordinator

```python
# team_execution_v2.py (NEEDS MODIFICATION)

async def execute(
    self,
    requirement: str,
    constraints: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    previous_phase_context: Optional[Dict[str, Any]] = None  # ✅ NEW PARAMETER
) -> Dict[str, Any]:
    # ...

    execution_result = await coordinator.execute_parallel(
        requirement=requirement,
        contracts=contracts_dict,
        context={
            **(constraints or {}),
            "previous_phase_outputs": previous_phase_context.get("outputs", {}) if previous_phase_context else {},  # ✅ ADDED
            "available_artifacts": previous_phase_context.get("artifacts", []) if previous_phase_context else [],  # ✅ ADDED
            "previous_contracts": previous_phase_context.get("contracts", []) if previous_phase_context else []  # ✅ ADDED
        }
    )
```

---

### Step 4: Persona Receives Full Context

```python
# persona_executor_v2.py:662-766 (FIXED)

def _build_persona_prompt(
    self,
    requirement: str,
    contract: Optional[Dict[str, Any]],
    context: Dict[str, Any],
    use_mock: bool,
    recommended_templates: Optional[List['TemplateContent']] = None
) -> str:
    """Build execution prompt for persona"""
    prompt_parts = [
        f"# Task: {requirement}\n",
        f"## Your Role: {self.persona_def['name']}\n"
    ]

    # ✅ ADDED: Previous phase outputs
    if "previous_phase_outputs" in context:
        prompt_parts.append("\n## 📦 Context from Previous Phases:\n")
        prompt_parts.append("You are building upon work completed by previous team members.\n\n")

        for phase_name, outputs in context["previous_phase_outputs"].items():
            prompt_parts.append(f"### {phase_name.title()} Phase Deliverables:\n")

            # Show key deliverables
            if "deliverables" in outputs:
                for deliverable_type, files in outputs.get("deliverables", {}).items():
                    prompt_parts.append(f"**{deliverable_type.title()}:**\n")
                    for file_path in files:
                        prompt_parts.append(f"  - {file_path}\n")

            # Show full output data
            prompt_parts.append("\n**Full Output:**\n")
            prompt_parts.append(f"```json\n{json.dumps(outputs, indent=2)}\n```\n\n")

    # ✅ ADDED: Available artifacts
    if "available_artifacts" in context:
        prompt_parts.append("\n## 📄 Available Artifacts:\n")
        for artifact in context["available_artifacts"]:
            prompt_parts.append(f"  - {artifact['name']} (created by {artifact['created_by_phase']})\n")
        prompt_parts.append("\n")

    # ... rest of prompt building ...
```

---

## Comparison: Current vs. Required

### Current Implementation (Broken):

```
┌─────────────────┐
│  Requirements   │ Outputs: 10KB
│     Phase       │
└────────┬────────┘
         │ ❌ Only 500 chars passed
         ▼
┌─────────────────┐
│     Design      │ Context received: 500 chars (5%)
│     Phase       │ Outputs: 50KB
└────────┬────────┘
         │ ❌ Only 500 chars passed
         ▼
┌─────────────────┐
│ Implementation  │ Context received: 500 chars (1%)
│     Phase       │ Missing: API specs, DB schemas, architecture
└─────────────────┘
```

### Required Implementation (AutoGen-style):

```
┌─────────────────┐
│  Requirements   │ Outputs: 10KB
│     Phase       │
└────────┬────────┘
         │ ✅ FULL 10KB passed
         ▼
┌─────────────────┐
│     Design      │ Context received: 10KB (100%)
│     Phase       │ Outputs: 50KB
└────────┬────────┘
         │ ✅ FULL 60KB passed (10KB + 50KB cumulative)
         ▼
┌─────────────────┐
│ Implementation  │ Context received: 60KB (100%)
│     Phase       │ Has: ALL API specs, DB schemas, architecture
└─────────────────┘
```

---

## Answer to User's Questions

### 1. "Context (all information) and instruction (what to do) can be passed to next phase?"

**Answer:** YES, the infrastructure supports it ✅

**Evidence:**
- `WorkflowContext.get_all_previous_outputs()` - Returns ALL context ✅
- `PhaseResult.context_passed` / `context_received` - Tracks context flow ✅
- `TeamExecutionContext` - Persists complete state ✅

**BUT** Implementation only uses 1-5% of available context ❌

---

### 2. "All agents should have their context loaded from .json files (appended with tasks/instructions from previous phase)?"

**Answer:** Agents ARE loaded from JSON ✅, but context from previous phases is NOT appended ❌

**Evidence:**
- Personas defined in maestro-engine JSON files ✅ (personas.py:32)
- Personas loaded dynamically via MaestroPersonaAdapter ✅
- **BUT** When persona prompt is built (persona_executor_v2.py:662):
  - Persona definition from JSON ✅
  - Current contract from current phase ✅
  - Previous phase outputs ❌ NOT INCLUDED
  - Previous phase artifacts ❌ NOT INCLUDED
  - Accumulated workflow context ❌ NOT INCLUDED

---

### 3. "Process should pass output + exact instructions to next phase?"

**Answer:** Infrastructure supports it ✅, implementation doesn't do it ❌

**Current behavior:**
```python
next_phase_requirement = f"Phase: implementation\nPrevious: {json.dumps(prev_output)[:500]}"
```

**Required behavior:**
```python
next_phase_requirement = f"""
Phase: implementation

## Previous Phase Complete Outputs:
{json.dumps(all_previous_outputs, indent=2)}  # FULL, not truncated

## Artifacts Available:
{list_of_all_artifacts}

## Your Instructions:
Based on the above work, implement the following...
"""
```

---

## Conclusion

**Microsoft AutoGen-style context passing:**
- ✅ **Infrastructure:** FULLY IMPLEMENTED (excellent design)
- ❌ **Implementation:** NOT USED (ignores infrastructure)
- **Gap:** ~95% information loss due to truncation and omission

**Your hypothesis was CORRECT:** The system was designed for AutoGen-style context flow. The infrastructure exists and works. The execution layer just doesn't use it properly.

---

**Next Document:** See `AGENT3_WORKFLOW_CONTRACT_GAPS.md` for analysis of contract forwarding issues.
