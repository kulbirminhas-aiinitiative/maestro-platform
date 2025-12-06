# 🗺️ Team Engine Refactoring Roadmap

**Version:** 1.0.0
**Date:** December 6, 2025
**Objective:** Transform the experimental `team_execution_v2.py` script into a robust, reusable `TeamEngine` library that powers the "One Brain" architecture.

---

## 1. Strategic Context

### The Problem
Currently, `team_execution_v2.py` is a "God Script." It defines its own personas, manages its own execution loop, and handles its own logging. It is disconnected from the rest of the platform (JIRA, Confluence, Central Personas).

### The Solution
We will extract the **intelligence** (Blueprints, Contracts, AI Composition) from the script and package it into a library: `src/maestro_hive/core/team_engine.py`. This library will be consumed by the `UnifiedOrchestrator`.

### The "One Brain" Flow
1.  **Orchestrator:** "I have a JIRA EPIC (MD-123)."
2.  **Team Engine:** "I have analyzed the requirements. I recommend the 'Microservices Squad' blueprint."
3.  **Orchestrator:** "Approved. Execute."
4.  **Team Engine:** "Assigning 'Backend Developer' (from `personas.py`) to Task A."
5.  **Block:** "Executing Task A."

---

## 2. Architecture Design

### Class Structure

```python
class TeamEngine:
    """
    The Manager Layer.
    Responsible for WHO does the work and HOW they coordinate.
    """
    def __init__(self, persona_registry: SDLCPersonas):
        self.registry = persona_registry

    def analyze_requirements(self, requirement: str) -> RequirementClassification:
        """Uses AI to classify complexity and required expertise."""
        pass

    def recommend_blueprint(self, classification: RequirementClassification) -> BlueprintRecommendation:
        """Selects the best team structure (e.g., 'Pair Programming', 'Mob', 'Waterfall')."""
        pass

    def compose_team(self, blueprint_id: str) -> TeamComposition:
        """Instantiates the team using real personas from the registry."""
        pass

    def create_contracts(self, team: TeamComposition, requirement: str) -> List[Contract]:
        """Defines the 'Handshake' between personas (API Specs, Data Models)."""
        pass
```

### Key Dependencies
*   **Input:** `personas.py` (Central Identity)
*   **Input:** `blueprints/` (JSON definitions of team patterns)
*   **Output:** `Contract` objects (passed to Blocks for execution)

---

## 3. Execution Roadmap (Step-by-Step)

### Phase 1: Foundation (The "Skeleton")
*Goal: Create the library structure without migrating complex logic yet.*

*   **Task 1.1:** Create `src/maestro_hive/core/team_engine/` directory.
*   **Task 1.2:** Define data models (`models.py`) extracted from `team_execution_v2.py`:
    *   `RequirementClassification`
    *   `BlueprintRecommendation`
    *   `ContractSpecification`
*   **Task 1.3:** Create the `TeamEngine` class stub in `engine.py`.

### Phase 2: Intelligence Extraction (The "Brain Transplant")
*Goal: Move the AI logic from the script to the library.*

*   **Task 2.1:** Port `TeamComposerAgent` logic.
    *   Extract the prompt engineering that analyzes requirements.
    *   Refactor to use `personas.py` instead of hardcoded strings.
*   **Task 2.2:** Port `ContractDesignerAgent` logic.
    *   Extract the logic that defines API specs and deliverables.
*   **Task 2.3:** Externalize Blueprints.
    *   Move hardcoded blueprints from the script into `src/maestro_hive/core/team_engine/blueprints/*.json`.

### Phase 3: Integration (The "Handshake")
*Goal: Connect the new Engine to the Orchestrator.*

*   **Task 3.1:** Update `UnifiedOrchestrator` to instantiate `TeamEngine`.
*   **Task 3.2:** Replace the legacy "Phase" logic in the Orchestrator with `TeamEngine.recommend_blueprint()`.
*   **Task 3.3:** Verify that JIRA tickets flow into the Team Engine and produce valid Team Compositions.

---

## 4. JIRA Ticket Breakdown

| ID | Title | Description | Dependencies |
|----|-------|-------------|--------------|
| **TE-001** | **Define Team Engine Models** | Create Pydantic models for Requirements, Blueprints, and Contracts. | None |
| **TE-002** | **Externalize Blueprints** | Extract team patterns to JSON files. | TE-001 |
| **TE-003** | **Implement Team Composer** | Port AI logic for team selection, integrating `personas.py`. | TE-002 |
| **TE-004** | **Implement Contract Designer** | Port AI logic for contract negotiation. | TE-003 |
| **TE-005** | **Orchestrator Integration** | Wire `TeamEngine` into `UnifiedOrchestrator`. | TE-004 |

---

## 5. Success Criteria

1.  **No Hardcoded Personas:** The system *must* use `personas.py`.
2.  **Separation of Concerns:** `TeamEngine` decides *who* and *how*; `Orchestrator` decides *when* and *what*.
3.  **Testability:** We can test "Team Composition" without running a full execution.

