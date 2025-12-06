# Improved Architecture Plan: "Structure-First" Approach

## Executive Summary
This revised plan acknowledges the strategic need for **visibility and adoption** over immediate architectural purity. We will prioritize the **Block Interface** and **Gap Identification** capabilities to give users immediate value ("What am I missing?"), while deferring the risky "Big Bang" refactoring of the core orchestrators until a safety net is in place.

**Core Philosophy:** "Wrap, Don't Rewrite." We will wrap the existing legacy code in the new "Block" interfaces to provide the structural vision immediately, then refactor the internals incrementally.

---

## 1. The "Map vs. Territory" Fix (Corrected Paths)

Before any work begins, we must align our mental model with reality.

| Component | Plan Path (Old) | **Actual Path (Verified)** | Action |
|-----------|-----------------|----------------------------|--------|
| **Executor** | `.../epic_execute/executor.py` | `maestro-hive/epic_executor/executor.py` | **WRAP** |
| **Team Exec** | `.../teams/team_execution_v2.py` | `maestro-hive/src/maestro_hive/teams/team_execution_v2.py` | **WRAP** |
| **SDLC Engine** | `.../autonomous_sdlc_engine.py` | `maestro-hive/src/maestro_hive/sdlc/autonomous_sdlc_engine.py` | **WRAP** |
| **Phase Orch** | `.../phases/phase_workflow_orchestrator.py` | `maestro-hive/src/maestro_hive/phases/phase_workflow_orchestrator.py` | **WRAP** |

---

## 2. Revised Roadmap: The "Visibility First" Strategy

### Phase 1: The "Hollow" Block Architecture (Weeks 1-2)
*Goal: Users can see "Blocks" and "Gaps" immediately, even if the engine is legacy.*

#### MD-2506: Block Registry (The "Menu")
- Create a simple JSON/YAML registry listing all available capabilities.
- **Deliverable:** `registry.json` that lists "Jira Adapter", "Python Executor", etc.

#### MD-2514: The Interface Facade (The "Wrapper")
- Instead of rewriting `executor.py`, create a `BlockInterface` class.
- **Action:** Create `LegacyExecutorBlock` that implements `BlockInterface` but internally calls `executor.py`.
- **Value:** The system *looks* like a Block architecture to the user/CLI, but runs on the proven (albeit messy) legacy code.

#### MD-2508: The Gap Detector (The "Composer" Prototype)
- **Redefined:** Instead of a complex code generator, build a **Scanner**.
- **Function:** Scans a project, compares it to the `registry.json`, and prints a "Gap Report".
- **User Value:** "You are missing a *Testing Block* and a *Security Block*." (This drives adoption!)

### Phase 2: Observability as a Feature (Weeks 3-4)
*Goal: "See it running."*

#### MD-2497: Execution Transparency (formerly "Actual Test Execution")
- **Pivot:** Don't just "run tests." Build a **Live Status Dashboard** (CLI or Web).
- **Mechanism:** Instrument the `LegacyExecutorBlock` to emit "Block Events" (Start, Stop, Success, Fail).
- **Value:** Users see the "Blocks" lighting up green/red. This builds trust in the "Block" concept.

### Phase 3: The Engine Swap (Weeks 5+)
*Goal: Stability and Cleanliness.*

#### MD-2494: Unified Orchestrator Core
- **Now Safe:** With the `BlockInterface` in place, we can swap `LegacyExecutorBlock` with `RefactoredExecutorBlock` one piece at a time.
- **Strategy:** Refactor *behind* the interface. The user never sees the change, only improved stability.

---

## 3. Critical "Gap Analysis" Features (To Drive Adoption)

To satisfy the user's need for "Gap Identification," we will implement these specific checks in the **Gap Detector (MD-2508)**:

1.  **Lifecycle Gaps:** "You have a *Build* block but no *Deploy* block."
2.  **Quality Gaps:** "Your *Testing* block is configured for 'Unit' but missing 'Integration'."
3.  **Security Gaps:** "No *Secret Scanning* block detected in the pipeline."
4.  **Documentation Gaps:** "Phase 2 is active, but *Architecture Decision Record* block is missing."

---

## 4. Immediate Next Steps (Action Plan)

1.  **Create the Registry:** Define the `registry.json` schema.
2.  **Define the Interface:** Write `block_interface.py`.
3.  **Build the Scanner:** Write `gap_detector.py` (leveraging logic from `integration_gap_analysis.py`).
4.  **Wrap the Executor:** Create `adapters/legacy_executor_adapter.py`.

This approach gives you the **Vision** (Blocks) and **Roadmap** (Gaps) immediately, without waiting for the heavy engineering of a full rewrite.
