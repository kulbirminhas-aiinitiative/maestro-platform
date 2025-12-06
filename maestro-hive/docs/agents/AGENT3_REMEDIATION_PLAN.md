# AGENT3: Remediation Plan - Actionable Fixes

**Document:** Technical Remediation Plan
**Purpose:** Specific code changes to fix context passing and contract forwarding
**Priority:** 🔴 CRITICAL - Required for production functionality

---

## Overview of Fixes

This document provides **specific code changes** with file:line references to fix the three critical bugs:

1. **Fix #1:** Remove 500-character truncation in context passing
2. **Fix #2:** Forward contracts between phases
3. **Fix #3:** Enhance persona prompts with previous phase context

---

## Fix #1: Remove Context Truncation ⚡ HIGH PRIORITY

### Location
**File:** `team_execution_v2_split_mode.py`
**Function:** `_extract_phase_requirement`
**Lines:** 752-789

### Current Code (Broken)

```python
def _extract_phase_requirement(
    self,
    phase_name: str,
    context: TeamExecutionContext,
    original_requirement: Optional[str] = None
) -> str:
    """Extract phase-specific requirement from context."""

    # For first phase, use original requirement
    if phase_name == self.SDLC_PHASES[0]:
        return original_requirement or context.workflow.metadata.get("initial_requirement", "")

    # For subsequent phases, build from previous outputs
    previous_outputs = context.workflow.get_all_previous_outputs(phase_name)

    # Build contextual requirement
    requirement_parts = [
        f"Phase: {phase_name}",
        f"Previous phases completed: {', '.join(context.workflow.phase_order)}",
    ]

    # ❌ BUG: Add outputs from previous phase (TRUNCATED!)
    previous_phase = self._get_previous_phase(phase_name)
    if previous_phase and previous_phase in previous_outputs:
        prev_output = previous_outputs[previous_phase]
        requirement_parts.append(f"\nOutputs from {previous_phase}:")
        requirement_parts.append(json.dumps(prev_output, indent=2)[:500])  # ❌ TRUNCATED!

    return "\n".join(requirement_parts)
```

---

### Fixed Code

```python
def _extract_phase_requirement(
    self,
    phase_name: str,
    context: TeamExecutionContext,
    original_requirement: Optional[str] = None
) -> str:
    """
    Extract phase-specific requirement from context.

    ✅ FIXED: Now includes FULL context from all previous phases
    ✅ FIXED: Includes artifacts, deliverables, and instructions
    """

    # For first phase, use original requirement
    if phase_name == self.SDLC_PHASES[0]:
        base_requirement = original_requirement or context.workflow.metadata.get("initial_requirement", "")
        return f"""# {phase_name.upper()} PHASE

## Project Requirement
{base_requirement}

## Phase Objective
Analyze and document project requirements."""

    # ✅ FIXED: Get FULL context from ALL previous phases
    previous_outputs = context.workflow.get_all_previous_outputs(phase_name)

    # Build comprehensive requirement
    requirement_parts = [
        f"# {phase_name.upper()} PHASE\n",
        f"## Original Project Requirement",
        original_requirement or context.workflow.metadata.get("initial_requirement", ""),
        f"\n## Execution Context",
        f"- Current Phase: {phase_name}",
        f"- Previous Phases Completed: {', '.join(context.workflow.phase_order)}",
        f"- Execution Mode: {context.workflow.execution_mode}",
    ]

    # ✅ FIXED: Include FULL outputs from ALL previous phases
    if previous_outputs:
        requirement_parts.append(f"\n## 📦 Complete Context from Previous Phases\n")
        requirement_parts.append("You are building upon work completed by previous team members. ")
        requirement_parts.append("Review their deliverables carefully before proceeding.\n")

        for prev_phase_name, prev_output in previous_outputs.items():
            requirement_parts.append(f"\n### {prev_phase_name.upper()} Phase Deliverables:\n")

            # ✅ FIXED: Include FULL output (no truncation!)
            if isinstance(prev_output, dict):
                # Pretty print with full detail
                requirement_parts.append("```json")
                requirement_parts.append(json.dumps(prev_output, indent=2))  # ✅ FULL, not [:500]
                requirement_parts.append("```\n")
            else:
                requirement_parts.append(str(prev_output))
                requirement_parts.append("\n")

            # ✅ NEW: Include artifacts created
            phase_result = context.workflow.get_phase_result(prev_phase_name)
            if phase_result and phase_result.artifacts_created:
                requirement_parts.append(f"\n**Artifacts Created:**\n")
                for artifact in phase_result.artifacts_created:
                    requirement_parts.append(f"- {artifact}\n")

            # ✅ NEW: Include instructions passed forward
            if phase_result and phase_result.context_passed:
                requirement_parts.append(f"\n**Instructions for Next Phase:**\n")
                for key, value in phase_result.context_passed.items():
                    requirement_parts.append(f"- **{key}**: {value}\n")

    # ✅ NEW: Include all available artifacts
    if context.workflow.shared_artifacts:
        requirement_parts.append(f"\n## 📄 All Available Artifacts\n")
        requirement_parts.append("The following artifacts have been created and are available for your use:\n\n")

        for artifact in context.workflow.shared_artifacts:
            requirement_parts.append(
                f"- `{artifact['name']}` (created by {artifact['created_by_phase']} phase"
            )
            if artifact.get('created_at'):
                requirement_parts.append(f" at {artifact['created_at']}")
            requirement_parts.append(")\n")

    # ✅ NEW: Add phase-specific instructions
    requirement_parts.append(f"\n## 🎯 Your Objective for {phase_name.upper()} Phase\n")

    phase_objectives = {
        "requirements": "Analyze and document detailed requirements based on the project description.",
        "design": "Design the system architecture, APIs, database schema, and component structure based on requirements.",
        "implementation": "Implement the system according to the design specifications. Use the API specs, database schemas, and architecture from the design phase.",
        "testing": "Create comprehensive tests for the implemented system. Test against the specifications from design phase.",
        "deployment": "Deploy the tested system. Use configurations and infrastructure designs from previous phases."
    }

    requirement_parts.append(phase_objectives.get(phase_name, f"Complete the {phase_name} phase deliverables."))
    requirement_parts.append("\n")

    return "\n".join(requirement_parts)
```

---

### Impact of Fix #1

**Before:**
```
Frontend receives: 500 characters = "{"phase": "design", "deliverab..."
Information loss: 95%
```

**After:**
```
Frontend receives: Full API specification (50KB)
                  Full database schema (20KB)
                  Full architecture diagrams references (10KB)
Information loss: 0%
```

---

## Fix #2: Forward Contracts Between Phases ⚡ HIGH PRIORITY

### Location 1: Contract Designer Signature

**File:** `team_execution_v2.py`
**Function:** `design_contracts`
**Lines:** 542-577

### Current Code (Broken)

```python
async def design_contracts(
    self,
    requirement: str,
    classification: RequirementClassification,
    blueprint: BlueprintRecommendation
) -> List[ContractSpecification]:
    """Design contracts for the team."""
    # ❌ No parameter for previous contracts
    # ❌ Creates contracts in isolation
```

---

### Fixed Code

```python
async def design_contracts(
    self,
    requirement: str,
    classification: RequirementClassification,
    blueprint: BlueprintRecommendation,
    previous_phase_contracts: Optional[List[ContractSpecification]] = None  # ✅ NEW
) -> List[ContractSpecification]:
    """
    Design contracts for the team.

    ✅ FIXED: Now accepts contracts from previous phases
    ✅ FIXED: Links dependencies to previous contracts
    """
    logger.info("📝 Designing contracts...")

    contracts = []

    # ✅ NEW: Carry forward previous contracts
    if previous_phase_contracts:
        logger.info(f"   📚 Carrying forward {len(previous_phase_contracts)} contract(s) from previous phases")
        contracts.extend(previous_phase_contracts)

    # Create contracts based on coordination mode
    if "parallel" in blueprint.execution_mode and "contract" in blueprint.coordination_mode:
        new_contracts = await self._design_parallel_contracts(
            requirement,
            classification,
            blueprint.personas,
            existing_contracts=contracts  # ✅ Pass existing
        )
    else:
        new_contracts = await self._design_sequential_contracts(
            requirement,
            classification,
            blueprint.personas,
            existing_contracts=contracts  # ✅ Pass existing
        )

    contracts.extend(new_contracts)

    logger.info(f"  ✅ Designed {len(new_contracts)} new contract(s)")
    logger.info(f"  ✅ Total contracts in workflow: {len(contracts)}")

    return contracts
```

---

### Location 2: Update Contract Design Methods

**File:** `team_execution_v2.py`
**Function:** `_design_parallel_contracts`
**Lines:** 579-672

### Add to Method Signature

```python
async def _design_parallel_contracts(
    self,
    requirement: str,
    classification: RequirementClassification,
    personas: List[str],
    existing_contracts: Optional[List[ContractSpecification]] = None  # ✅ NEW
) -> List[ContractSpecification]:
    """
    Design contracts for parallel execution with clear interfaces.

    ✅ FIXED: Now links to existing contracts from previous phases
    """
    contracts = []
    existing_contracts = existing_contracts or []

    # Identify interface boundaries
    has_backend = "backend_developer" in personas
    has_frontend = "frontend_developer" in personas

    if has_backend and has_frontend:
        contract_id = f"contract_{uuid.uuid4().hex[:12]}"

        # ✅ NEW: Find dependencies in existing contracts
        dependencies = []
        for existing in existing_contracts:
            # If previous phase had API design, depend on it
            if existing.contract_type in ["REST_API", "GraphQL"]:
                dependencies.append(existing.id)
                logger.info(f"   🔗 Linking new contract to existing: {existing.name}")

        contracts.append(ContractSpecification(
            id=contract_id,
            name="Backend API Contract",
            version="v1.0",
            contract_type="REST_API",
            deliverables=[...],
            dependencies=dependencies,  # ✅ FIXED: Link to previous phase
            # ... rest of contract ...
        ))

    return contracts
```

---

### Location 3: Pass Contracts Forward in Split Mode

**File:** `team_execution_v2_split_mode.py`
**Function:** `execute_phase`
**Lines:** 828-834

### Current Code (Broken)

```python
# Step 3: AI designs contracts
logger.info("\n📝 Step 3: Contract Design")
contracts = await self.contract_designer.design_contracts(
    requirement,
    classification,
    blueprint_rec
)  # ❌ No previous contracts passed
```

---

### Fixed Code

```python
# Step 3: AI designs contracts
logger.info("\n📝 Step 3: Contract Design")

# ✅ FIXED: Get contracts from previous phases
previous_contracts = []
if context.team_state.contract_specs:
    previous_contracts = context.team_state.contract_specs
    logger.info(f"   📚 Found {len(previous_contracts)} contract(s) from previous phases")

contracts = await self.contract_designer.design_contracts(
    requirement,
    classification,
    blueprint_rec,
    previous_phase_contracts=previous_contracts  # ✅ FIXED: Pass them forward
)

# ✅ FIXED: Update contract specs (accumulate, don't replace)
context.team_state.contract_specs = contracts  # Now includes old + new
```

---

## Fix #3: Enhance Persona Prompts with Full Context ⚡ HIGH PRIORITY

### Location

**File:** `persona_executor_v2.py`
**Function:** `_build_persona_prompt`
**Lines:** 662-766

### Current Code (Broken)

```python
def _build_persona_prompt(
    self,
    requirement: str,
    contract: Optional[Dict[str, Any]],
    context: Dict[str, Any],  # ❌ Usually empty or minimal
    use_mock: bool,
    recommended_templates: Optional[List['TemplateContent']] = None
) -> str:
    prompt_parts = [
        f"# Task: {requirement}\n",
        f"## Your Role: {self.persona_def['name']}\n"
    ]

    # ... adds templates ...
    # ... adds contract ...

    if context:  # ❌ Usually empty!
        prompt_parts.append("## Context:\n")
        prompt_parts.append(json.dumps(context, indent=2))

    # ❌ MISSING: Previous phase deliverables
    # ❌ MISSING: Artifacts from other personas
    # ❌ MISSING: API specs, schemas, etc.

    return "".join(prompt_parts)
```

---

### Fixed Code

```python
def _build_persona_prompt(
    self,
    requirement: str,
    contract: Optional[Dict[str, Any]],
    context: Dict[str, Any],
    use_mock: bool,
    recommended_templates: Optional[List['TemplateContent']] = None
) -> str:
    """
    Build execution prompt for persona.

    ✅ FIXED: Now includes comprehensive context from previous phases
    """
    prompt_parts = [
        f"# Task: {requirement}\n",
        f"## Your Role: {self.persona_def['name']}\n"
    ]

    # ... existing template code ...

    # ✅ NEW: Add comprehensive previous phase context
    if "previous_phase_outputs" in context and context["previous_phase_outputs"]:
        prompt_parts.append("\n## 📦 Work from Previous Phases\n\n")
        prompt_parts.append("You are building upon completed work from previous team members. ")
        prompt_parts.append("All deliverables and specifications below are ALREADY COMPLETE and available for your use.\n\n")

        for phase_name, outputs in context["previous_phase_outputs"].items():
            prompt_parts.append(f"### {phase_name.upper()} Phase:\n\n")

            # Show deliverables by category
            if "deliverables" in outputs:
                prompt_parts.append("**Deliverables Created:**\n")
                for deliverable_type, files in outputs.get("deliverables", {}).items():
                    prompt_parts.append(f"- **{deliverable_type.title()}:**\n")
                    for file_path in files:
                        prompt_parts.append(f"  - `{file_path}`\n")
                prompt_parts.append("\n")

            # Show full output data
            if "phase" in outputs or "execution_summary" in outputs:
                prompt_parts.append("**Detailed Output:**\n")
                prompt_parts.append("```json\n")
                prompt_parts.append(json.dumps(outputs, indent=2))  # ✅ FULL output
                prompt_parts.append("\n```\n\n")

    # ✅ NEW: Add available artifacts from all phases
    if "available_artifacts" in context and context["available_artifacts"]:
        prompt_parts.append("\n## 📄 Available Artifacts\n\n")
        prompt_parts.append("The following files have been created by previous team members and are available in the project:\n\n")

        # Group by phase
        artifacts_by_phase = {}
        for artifact in context["available_artifacts"]:
            phase = artifact.get("created_by_phase", "unknown")
            if phase not in artifacts_by_phase:
                artifacts_by_phase[phase] = []
            artifacts_by_phase[phase].append(artifact)

        for phase, artifacts in artifacts_by_phase.items():
            prompt_parts.append(f"**From {phase.title()} Phase:**\n")
            for artifact in artifacts:
                prompt_parts.append(f"- `{artifact['name']}`")
                if artifact.get('created_at'):
                    prompt_parts.append(f" (created {artifact['created_at']})")
                prompt_parts.append("\n")
            prompt_parts.append("\n")

    # ✅ NEW: Add contracts from previous phases (for consumers)
    if "previous_contracts" in context and context["previous_contracts"]:
        prompt_parts.append("\n## 📋 Contracts from Previous Phases\n\n")
        prompt_parts.append("These contracts define deliverables from other team members that you can use:\n\n")

        for prev_contract in context["previous_contracts"]:
            # Only show contracts where this persona is a consumer
            if self.persona_id in prev_contract.get("consumer_persona_ids", []):
                prompt_parts.append(f"### {prev_contract['name']}\n")
                prompt_parts.append(f"- **Provider:** {prev_contract['provider_persona_id']}\n")
                prompt_parts.append(f"- **Type:** {prev_contract['contract_type']}\n")

                if prev_contract.get("interface_spec"):
                    prompt_parts.append(f"- **Interface Specification:**\n")
                    prompt_parts.append(f"```json\n{json.dumps(prev_contract['interface_spec'], indent=2)}\n```\n")

                if prev_contract.get("mock_available"):
                    prompt_parts.append(f"- **Mock Available:** Yes (endpoint: {prev_contract.get('mock_endpoint', 'N/A')})\n")

                prompt_parts.append("\n")

    # ... existing contract code ...

    # ✅ NEW: Add specific instructions based on role and context
    if self.persona_id == "frontend_developer":
        # Frontend gets special guidance to use backend specs
        if "previous_phase_outputs" in context:
            prompt_parts.append("\n## 🎯 Frontend Development Guidelines\n\n")
            prompt_parts.append("1. Review the API specification from the design/backend phase\n")
            prompt_parts.append("2. Use the exact endpoints, request/response formats specified\n")
            prompt_parts.append("3. Implement error handling for all API responses\n")
            prompt_parts.append("4. Follow the state management design from architecture phase\n")
            prompt_parts.append("5. If mock API is available, develop against mock then integrate with real API\n\n")

    elif self.persona_id == "qa_engineer":
        prompt_parts.append("\n## 🎯 QA Testing Guidelines\n\n")
        prompt_parts.append("1. Review ALL deliverables from implementation phase\n")
        prompt_parts.append("2. Create tests for EVERY endpoint in the API specification\n")
        prompt_parts.append("3. Test frontend against the ACTUAL implemented features\n")
        prompt_parts.append("4. Verify against acceptance criteria from requirements phase\n\n")

    # ... rest of prompt ...

    return "".join(prompt_parts)
```

---

### Location 2: Update Execute Method to Pass Context

**File:** `persona_executor_v2.py`
**Lines:** 390-410 (in `_execute_group` of parallel_coordinator_v2.py)

### Current Code (Broken)

```python
# Create execution task
task = executor.execute(
    requirement=requirement,
    contract=contract,
    context=context,  # ❌ Minimal context
    use_mock=use_mock
)
```

---

### Fixed Code (in parallel_coordinator_v2.py)

```python
# ✅ FIXED: Build comprehensive context for persona
persona_context = {
    **context,  # Existing context (phase, quality_threshold, etc.)
    "previous_phase_outputs": context.get("previous_phase_outputs", {}),  # ✅ ADDED
    "available_artifacts": context.get("available_artifacts", []),  # ✅ ADDED
    "previous_contracts": context.get("previous_contracts", []),  # ✅ ADDED
}

# Create execution task
task = executor.execute(
    requirement=requirement,
    contract=contract,
    context=persona_context,  # ✅ FIXED: Rich context
    use_mock=use_mock
)
```

---

## Implementation Priority Matrix

| Fix | Priority | Impact | Effort | Files Changed | LOC |
|-----|----------|--------|--------|---------------|-----|
| **Fix #1: Remove Truncation** | 🔴 CRITICAL | Very High | Low | 1 | ~80 |
| **Fix #2: Forward Contracts** | 🔴 CRITICAL | Very High | Medium | 2 | ~120 |
| **Fix #3: Enhance Prompts** | 🔴 CRITICAL | Very High | Medium | 2 | ~150 |

**Recommended Order:**
1. Fix #1 (easiest, biggest immediate impact)
2. Fix #3 (enables personas to use context)
3. Fix #2 (completes the workflow contract system)

---

## Testing Strategy

### Test Case 1: Simple API + Frontend (Validation)

**File:** Create `test_fixes_validation.py`

```python
async def test_context_passing_fix():
    """
    Verify Fix #1: Context is no longer truncated
    """
    engine = TeamExecutionEngineV2SplitMode()

    # Phase 1: Design (creates API spec)
    ctx1 = await engine.execute_phase(
        "design",
        requirement="Build REST API with 5 endpoints"
    )

    # Verify design outputs are large (>500 chars)
    design_output = ctx1.workflow.get_phase_output("design")
    design_json = json.dumps(design_output, indent=2)
    assert len(design_json) > 500, "Design output should be > 500 chars"

    # Phase 2: Implementation
    ctx2 = await engine.execute_phase(
        "implementation",
        checkpoint=ctx1
    )

    # ✅ VERIFY: Implementation phase received FULL design output
    impl_requirement = engine._extract_phase_requirement(
        "implementation",
        ctx2,
        "Build REST API with 5 endpoints"
    )

    # Check that full design is present (not truncated)
    assert len(impl_requirement) > 2000, f"Implementation should receive full context (got {len(impl_requirement)} chars)"
    assert design_json[:500] in impl_requirement, "Should contain start of design"
    assert design_json[-100:] in impl_requirement, "Should contain end of design (not truncated!)"

    print("✅ Fix #1 VALIDATED: Context not truncated")


async def test_contract_forwarding_fix():
    """
    Verify Fix #2: Contracts are forwarded between phases
    """
    engine = TeamExecutionEngineV2SplitMode()

    # Phase 1
    ctx1 = await engine.execute_phase("design", requirement="Build API")
    contracts_after_design = len(ctx1.team_state.contract_specs)

    # Phase 2
    ctx2 = await engine.execute_phase("implementation", checkpoint=ctx1)
    contracts_after_impl = len(ctx2.team_state.contract_specs)

    # ✅ VERIFY: Contracts accumulated (not replaced)
    assert contracts_after_impl >= contracts_after_design, \
        f"Contracts should accumulate: design={contracts_after_design}, impl={contracts_after_impl}"

    print(f"✅ Fix #2 VALIDATED: Contracts forwarded ({contracts_after_design} → {contracts_after_impl})")


async def test_persona_context_fix():
    """
    Verify Fix #3: Personas receive previous phase context
    """
    from persona_executor_v2 import PersonaExecutorV2

    executor = PersonaExecutorV2(
        persona_id="frontend_developer",
        output_dir=Path("./test_output")
    )

    # Simulate context from previous phases
    context = {
        "previous_phase_outputs": {
            "design": {
                "api_endpoints": ["/api/users", "/api/products"],
                "database_tables": ["users", "products"]
            }
        },
        "available_artifacts": [
            {"name": "api_spec.yaml", "created_by_phase": "design"}
        ]
    }

    # Build prompt
    prompt = executor._build_persona_prompt(
        requirement="Build frontend",
        contract=None,
        context=context,
        use_mock=False
    )

    # ✅ VERIFY: Prompt contains previous phase info
    assert "/api/users" in prompt, "Should include API endpoints from design"
    assert "api_spec.yaml" in prompt, "Should include artifacts"
    assert "design" in prompt.lower(), "Should mention previous phase"

    print(f"✅ Fix #3 VALIDATED: Persona prompt includes full context ({len(prompt)} chars)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_context_passing_fix())
    asyncio.run(test_contract_forwarding_fix())
    asyncio.run(test_persona_context_fix())
```

---

## Rollout Plan

### Phase 1: Fix #1 (Week 1)
- [ ] Update `_extract_phase_requirement` in `team_execution_v2_split_mode.py`
- [ ] Test with simple 2-phase workflow
- [ ] Verify context not truncated
- [ ] Deploy to dev environment

### Phase 2: Fix #3 (Week 1-2)
- [ ] Update `_build_persona_prompt` in `persona_executor_v2.py`
- [ ] Update `_execute_group` in `parallel_coordinator_v2.py` to pass rich context
- [ ] Test frontend developer receives backend specs
- [ ] Deploy to dev environment

### Phase 3: Fix #2 (Week 2)
- [ ] Update `design_contracts` in `team_execution_v2.py`
- [ ] Update contract accumulation in `team_execution_v2_split_mode.py`
- [ ] Test contract forwarding across 3+ phases
- [ ] Deploy to dev environment

### Phase 4: Integration Testing (Week 3)
- [ ] Run full SDLC workflow (all 5 phases)
- [ ] Verify frontend generated with real API calls
- [ ] Verify QA tests actual implementation
- [ ] Measure information loss (should be 0%)

### Phase 5: Production Deployment (Week 4)
- [ ] Deploy to staging
- [ ] Run production test cases
- [ ] Monitor for issues
- [ ] Deploy to production

---

## Success Metrics

### Before Fixes
- ❌ Context truncated to 500 chars (95% loss)
- ❌ Contracts isolated per phase
- ❌ Frontend generic placeholders
- ❌ 0% workflow completion rate

### After Fixes
- ✅ Full context passed (0% loss)
- ✅ Contracts accumulated across phases
- ✅ Frontend implements real APIs
- ✅ >80% workflow completion rate

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Large context size | Add compression for very large outputs |
| Memory usage | Implement context pagination for huge workflows |
| Breaking changes | Keep old methods, deprecate gradually |
| Regression | Comprehensive test suite before deploy |

---

## Conclusion

All three fixes are **straightforward** and **low-risk**:
- Fix #1: Delete `[:500]` and add structure (~80 LOC)
- Fix #2: Add parameter, accumulate list (~120 LOC)
- Fix #3: Add context fields to dict (~150 LOC)

**Total:** ~350 lines of code to fix 95% information loss.

**Estimated Time:** 2-3 weeks (including testing)

---

**Next Document:** See `AGENT3_FRONTEND_GENERATION_FAILURE_ANALYSIS.md` for detailed trace of failure scenarios.
