# Proposed Fix for MD-3162: AI-Driven Contract Design (Strict Mode)

**Ticket:** MD-3162
**Component:** TeamExecutionEngineV2 (`src/maestro_hive/teams/team_execution_v2.py`)
**Status:** Proposed (Pending Approval)
**Mode:** STRICT (No Fallback)

## Problem

The `ContractDesignerAgent` currently uses hardcoded templates for generating contracts. This causes issues when specific requirements (like "create a Python class") are passed, as the hardcoded templates (e.g., "Deliverables from {persona}") are too generic and do not instruct the executing agents to produce the specific files requested.

**Evidence:**
In the execution of MD-3162, the `backend_developer` received a generic contract and failed to write the `SyntheticCheckpointBuilder` class, instead just creating a placeholder file.

## Proposed Solution

Update `ContractDesignerAgent._design_sequential_contracts` to use the `ClaudeCLIClient` to dynamically generate contract specifications. **If AI fails, raise an explicit error rather than falling back to hardcoded behavior.**

### Design Principle: Fail Fast, Not Silent

```
REJECTED:  AI fails → Use hardcoded template → Produce garbage → Discover later
APPROVED:  AI fails → Raise AIContractDesignError → Stop immediately → User knows why
```

### New Exception Class

```python
class AIContractDesignError(Exception):
    """Raised when AI cannot design contracts in strict mode."""
    def __init__(self, requirement: str, reason: str):
        self.requirement = requirement
        self.reason = reason
        super().__init__(
            f"AI contract design failed (strict mode).\n"
            f"Requirement: {requirement[:100]}...\n"
            f"Reason: {reason}\n"
            f"Resolution: Provide explicit contracts via constraints['contracts']"
        )
```

### Code Change

```python
async def _design_sequential_contracts(
    self,
    requirement: str,
    classification: RequirementClassification,
    personas: List[str],
    previous_phase_contracts: Optional[List[ContractSpecification]] = None
) -> List[ContractSpecification]:
    """
    Design contracts for sequential execution using AI.

    STRICT MODE: Raises AIContractDesignError if AI fails.
    No fallback to hardcoded templates.
    """

    # Validate AI is available
    if not CLAUDE_SDK_AVAILABLE:
        raise AIContractDesignError(
            requirement=requirement,
            reason="Claude SDK not available - cannot design contracts"
        )

    previous_contract_ids = [c.id for c in previous_phase_contracts] if previous_phase_contracts else []

    try:
        client = ClaudeCLIClient()

        prompt = f"""You are a contract designer for a software development team.

REQUIREMENT:
{requirement}

CLASSIFICATION:
- Type: {classification.requirement_type}
- Complexity: {classification.complexity.value}
- Expertise needed: {', '.join(classification.required_expertise)}

PERSONAS TO ASSIGN WORK:
{json.dumps(personas, indent=2)}

Design specific contracts for each persona. Each contract MUST include:
1. Explicit file paths to create (e.g., "src/module/class_name.py")
2. Specific acceptance criteria tied to the requirement
3. Clear deliverables with artifact patterns

Return JSON array of contracts:
[
  {{
    "persona_id": "backend_developer",
    "name": "Backend Implementation Contract",
    "deliverables": [
      {{
        "name": "source_code",
        "description": "Implementation of requested feature",
        "artifacts": ["src/path/to/file.py"],
        "acceptance_criteria": ["Class X exists", "Method Y implemented"]
      }}
    ]
  }}
]

CRITICAL: Artifacts must match the requirement. If requirement mentions Python, artifacts must be .py files.
"""

        result = client.query(prompt=prompt, skip_permissions=True, timeout=300)

        if not result.get('success'):
            raise AIContractDesignError(
                requirement=requirement,
                reason=f"Claude query failed: {result.get('error', 'Unknown error')}"
            )

        # Parse and validate response
        response_text = result.get('output', '')
        contracts = self._parse_contract_response(response_text, requirement)

        # Validate contracts match requirement
        self._validate_contracts(contracts, requirement)

        return contracts

    except AIContractDesignError:
        raise  # Re-raise our exceptions

    except Exception as e:
        # NO FALLBACK - convert to explicit error
        raise AIContractDesignError(
            requirement=requirement,
            reason=f"Contract design failed: {str(e)}"
        ) from e


def _validate_contracts(self, contracts: List[ContractSpecification], requirement: str) -> None:
    """Validate that contracts match the requirement. Raises on mismatch."""
    req_lower = requirement.lower()

    # Check for language-specific artifacts
    if "python" in req_lower or "class" in req_lower:
        has_python = any(
            any(".py" in str(artifact) for artifact in d.get("artifacts", []))
            for c in contracts
            for d in c.deliverables
        )
        if not has_python:
            raise AIContractDesignError(
                requirement=requirement,
                reason="Contracts missing Python artifacts (.py) for Python requirement"
            )

    # Check for empty deliverables
    for contract in contracts:
        if not contract.deliverables:
            raise AIContractDesignError(
                requirement=requirement,
                reason=f"Contract '{contract.name}' has no deliverables"
            )
```

## User Override (Escape Hatch)

Users can bypass AI contract design by providing explicit contracts:

```python
result = await engine.execute(
    requirement="Build SyntheticCheckpointBuilder",
    constraints={
        "contracts": [
            {
                "persona_id": "backend_developer",
                "deliverables": [
                    {
                        "artifacts": ["src/maestro_hive/unified_execution/synthetic_checkpoint.py"],
                        "acceptance_criteria": ["Class SyntheticCheckpointBuilder exists"]
                    }
                ]
            }
        ]
    }
)
```

## Benefits

1. **Fail Fast:** Errors surface in planning phase, not after execution
2. **Specificity:** AI-generated contracts explicitly list files to create
3. **Debuggable:** Clear error messages explain what failed and why
4. **No Garbage:** Never produce substandard artifacts from hardcoded templates

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| AI latency | +10-20s planning | Acceptable trade-off for quality |
| AI failure stops execution | No output | User can provide explicit contracts |
| Malformed AI response | Error raised | Clear error message with resolution |

## Approval Request

Please approve this change to `src/maestro_hive/teams/team_execution_v2.py`:
1. Remove hardcoded contract templates
2. Implement AI-driven contract design with strict mode
3. Add `AIContractDesignError` exception
4. Add contract validation
