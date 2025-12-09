# Maestro Localized TaaS: Architecture & Vision

**Date:** December 7, 2025  
**Status:** Implemented (Alpha)  
**Context:** Self-Improving Platform / Quality Assurance

---

## 1. Executive Summary

The **Maestro Localized TaaS (Testing as a Service)** is a paradigm shift in how we approach quality assurance within the Maestro ecosystem. 

**The Core Insight:**  
Previously, we viewed "Testing" as a task of *generating* test code.  
**The New Vision:** Testing is a **Platform Service**. The "Architects" (DDE, ACC) define the *scope* of what needs to be tested, and the TaaS Platform provides the *infrastructure* to execute that scope reliably, securely, and transparently.

We are moving from **"Guessing what to test"** to **"Executing a defined Verification Contract."**

---

## 2. Core Philosophy

1.  **Separation of Concerns**:
    *   **The Architect (DDE/ACC)**: Knows *why* the software exists and *what* it must do. It defines the **Test Scope**.
    *   **The Platform (TaaS)**: Knows *how* to run tests, capture logs, and report results. It executes the **Test Scope**.

2.  **Testing as a Contract**:
    *   The interface between the Architect and the Platform is a strict JSON contract called the `TestScope`.
    *   This contract defines scenarios, expected outcomes, and execution parameters.

3.  **Localized Execution**:
    *   TaaS runs locally within the development environment (Shift Left).
    *   It provides a "Sandbox" (Docker/Venv) to ensure tests are reproducible and do not pollute the host system.

---

## 3. Architecture

```mermaid
graph TD
    subgraph "Upstream: The Architects"
        DDE[DDE Orchestrator]
        ACC[Adaptive Code Composer]
        Registry[Registry.json]
    end

    subgraph "The Contract"
        Scope[TestScope (JSON)]
    end

    subgraph "Downstream: The Platform (TaaS)"
        Harness[TaaS Harness]
        Sandbox[Execution Sandbox]
        Reporter[Result Reporter]
    end

    subgraph "Feedback Loop"
        Healer[The Healer (Future)]
        Quality[Quality Fabric]
    end

    DDE -->|Defines| Scope
    ACC -->|Defines| Scope
    Registry -->|Informs| DDE

    Scope -->|Input| Harness
    Harness -->|Spawns| Sandbox
    Sandbox -->|Logs/Artifacts| Reporter
    Reporter -->|TaaSReport| Quality
    Reporter -->|Failures| Healer
    Healer -->|Fixes| ACC
```

---

## 4. Component Breakdown

### A. The Request (`TestScope` Schema 2.0)
A JSON object defining the constraints, environment, and lifecycle.

```json
{
  "scope_id": "scope-v2",
  "environment": {
    "type": "docker",
    "image": "python:3.11-slim",
    "dependencies": ["pytest", "requests"] 
  },
  "lifecycle": {
    "setup": ["python scripts/seed_db.py"],
    "teardown": ["python scripts/clean_db.py"]
  },
  "scenarios": [
    {
      "id": "UNIT-001",
      "type": "unit",
      "execution": {
        "runner": "pytest",
        "target": "tests/test_core.py" 
      }
    },
    {
      "id": "API-001",
      "type": "integration",
      "command": "curl -f http://localhost:3000/health",
      "retry_policy": { "attempts": 3, "backoff": "linear" }
    }
  ]
}
```

### B. The Platform (TaaS Harness)
*   **File**: `src/maestro_hive/testing/harness.py`
*   **Role**: The "Muscle". It executes the contract.
*   **Capabilities**:
    *   **Multi-Type Support**: Unit (Pytest), Integration (Curl/Scripts), E2E.
    *   **Sandboxing**: **CRITICAL**. Must run in isolated containers to prevent host pollution.
    *   **Lifecycle Management**: Executes `setup` -> `tests` -> `teardown`.

---

## 5. Workflow: The "Adversarial" Lifecycle

1.  **The Legislator (DDE)**: 
    *   Defines the `TestScope` (The Law).
    *   Example: "Must pass these 5 unit tests and this integration scenario."

2.  **The Citizen (ACC)**:
    *   Writes the Code to satisfy the Law.
    *   **Constraint**: ACC cannot modify the `TestScope`.

3.  **The Judge (TaaS)**:
    *   Executes the Scope in a **Sandbox**.
    *   Returns a verdict (Pass/Fail).

---

## 6. Implementation Plan (Revised)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **TaaS Harness** | 🟡 Beta | `src/maestro_hive/testing/harness.py` | Updating to Schema 2.0. |
| **Test Scope** | ✅ Defined | `dde_pilot_projects.py` | Updating to Schema 2.0. |
| **Docker Sandbox** | 🔴 P0 Priority | `src/maestro_hive/testing/sandbox.py` | **Required** for safe execution. |
| **The Healer** | ⏸️ Paused | `src/maestro_hive/testing/healer.py` | Paused until Sandbox is stable. |

---

## 7. Critical Advisory & Roadmap

**Status:** 🟢 **Conceptually Strong** / 🔴 **Implementation Dangerous**

**Immediate Priorities:**
1.  **The Jail**: Implement Docker Sandbox. Stop using local shell execution immediately.
2.  **The Contract**: Update Schema to handle State and Environment.
3.  **The Loop**: Traffic Replay for "Shift Right".


---

## 5. Workflow: The "Pilot" Lifecycle

1.  **Inception**: 
    *   User requests "Pilot 1: API Gateway".
    *   `dde_pilot_projects.py` loads the project definition.
    *   **New**: It also loads the `test_scope` defined in the project.

2.  **Construction**:
    *   DDE builds the code (scaffolding, implementation).

3.  **Verification (The TaaS Handoff)**:
    *   DDE calls `TaaSHarness.execute_scope(project.test_scope)`.
    *   TaaS spins up the environment.
    *   TaaS executes `API-001`, `API-002`, etc.

4.  **Result**:
    *   TaaS returns a `TaaSReport`.
    *   If **PASS**: DDE marks the phase as complete.
    *   If **FAIL**: DDE triggers the "Healer" (or halts for human review).

---

## 6. Implementation Status

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **TaaS Harness** | ✅ Alpha | `src/maestro_hive/testing/harness.py` | Supports shell execution, JSON reporting. |
| **Test Scope** | ✅ Defined | `dde_pilot_projects.py` | Added `test_scope` to Pilot 1. |
| **DDE Integration** | 🟡 Pending | `dde_orchestrator.py` | Needs to call Harness during execution. |
| **Docker Sandbox** | 🔴 Planned | `src/maestro_hive/testing/sandbox.py` | Currently runs in local shell. |
| **The Healer** | 🔴 Planned | `src/maestro_hive/testing/healer.py` | Auto-fix logic for failed tests. |

---

## 7. Future Roadmap

1.  **The Healer**:
    *   When TaaS reports a failure, the Healer analyzes the stack trace and diff.
    *   It determines: *Is the code broken?* OR *Is the test outdated?*
    *   It attempts one auto-correction cycle.

2.  **Observability Integration**:
    *   TaaS should emit OpenTelemetry traces.
    *   A failed test becomes a trace with an error span, visible in the same dashboard as production errors.

3.  **Shift Right**:
    *   Production incidents (logs) should be converted into `TestScenario` objects automatically, feeding back into the TaaS regression suite.
