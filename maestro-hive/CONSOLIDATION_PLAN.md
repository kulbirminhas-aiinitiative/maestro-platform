# 🏗️ Maestro Platform Consolidation Plan

**Version:** 1.0.0
**Date:** December 6, 2025
**Status:** DRAFT

## 1. Vision: The "One Brain" Architecture

The goal is to transition Maestro from a collection of disconnected scripts into a unified **Self-Improving AI Platform**. The current state suffers from "Schizophrenic Architecture" with three competing executors. The future state will have a single, layered architecture.

### Target Architecture Layers

1.  **Layer 1: The Unified Orchestrator (The Boss)**
    *   **Responsibility:** Lifecycle management, Compliance, Reporting (JIRA/Confluence).
    *   **Core Component:** `src/maestro_hive/core/orchestrator.py` (wrapping `epic_executor`).
    *   **Source of Truth:** JIRA EPICs.

2.  **Layer 2: The Team Engine (The Manager)**
    *   **Responsibility:** Team composition, Persona assignment, Contract negotiation.
    *   **Core Component:** `src/maestro_hive/core/team_engine.py` (refactored from `team_execution_v2.py`).
    *   **Source of Truth:** `personas.py` (Centralized Registry).

3.  **Layer 3: The Capability Blocks (The Workers)**
    *   **Responsibility:** Atomic tasks (Code Gen, Testing, Deployment).
    *   **Core Component:** `src/maestro_hive/blocks/*` (Standardized Block Interface).

---

## 2. Cleanup Strategy: Archiving the Noise

To clear the path for this vision, we are archiving redundant or conflicting modules. **No code is deleted**, only moved to `archive/` for reference.

### 📦 Archived Files & Value Retention Plan

#### A. `src/maestro_hive/sdlc/autonomous_sdlc_engine.py`
*   **Status:** **ARCHIVED**
*   **Reason:** Primitive linear script. Superseded by `team_execution_v2.py`.
*   **💎 Valuable Features to Retain (JIRA Candidates):**
    *   **Simple "Pass-the-Baton" Logic:** Useful for simple tasks where full contract negotiation is overkill.
    *   **Direct Claude SDK Integration:** The `_execute_with_claude` method has good prompt engineering for direct LLM calls.
    *   **Fallback Simulation:** The `_execute_simulated` method is useful for offline testing.

#### B. `src/maestro_hive/phases/phase_workflow_orchestrator.py`
*   **Status:** **ARCHIVED**
*   **Reason:** Redundant with `epic_executor`. Creates a competing "Phase" model.
*   **💎 Valuable Features to Retain (JIRA Candidates):**
    *   **Progressive Quality Gates:** The `ProgressiveQualityManager` integration is superior to `epic_executor`'s static checks.
    *   **Phase State Machine:** The explicit `PhaseState` (Entry/Exit gates) is cleaner than the implicit logic in `epic_executor`.
    *   **Rework Logic:** The "Targeted Rework" capability (re-running just one phase) is missing from the main orchestrator.

---

## 3. Migration Roadmap (JIRA Tickets)

We will create the following tasks to migrate the valuable features from the archive into the main branch.

| ID | Title | Source | Target | Priority |
|----|-------|--------|--------|----------|
| **MIG-001** | **Port Progressive Quality Gates** | `phase_workflow_orchestrator.py` | `src/maestro_hive/quality/quality_fabric_client.py` | HIGH |
| **MIG-002** | **Implement Targeted Rework** | `phase_workflow_orchestrator.py` | `src/maestro_hive/core/orchestrator.py` | MEDIUM |
| **MIG-003** | **Refactor Team Engine** | `team_execution_v2.py` | `src/maestro_hive/core/team_engine.py` | HIGH |
| **MIG-004** | **Integrate Central Personas** | `personas.py` | `src/maestro_hive/core/team_engine.py` | HIGH |

---

## 4. Immediate Next Steps

1.  **Execute Archive:** Move identified files to `archive/`.
2.  **Verify Stability:** Run `gap_detector.py` to ensure no critical dependencies were broken.
3.  **Begin MIG-003:** Start refactoring `team_execution_v2.py` into the new `TeamEngine` class.
