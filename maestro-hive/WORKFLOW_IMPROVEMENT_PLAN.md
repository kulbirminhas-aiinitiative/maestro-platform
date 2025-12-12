# Workflow Improvement Plan: Strengthening the Autonomous SDLC

## 1. Executive Summary

The current workflow implements a **Single-Pass Team Execution** wrapped in an **External Retry Loop**. While functional, this architecture suffers from inefficiency and "late feedback." Errors are detected only after the entire team has completed their work, and the remediation strategy involves restarting the entire process rather than targeting the specific failure.

To achieve true "Level 5" autonomy, we must move from a **Retry-Based** architecture to a **Refinement-Based** architecture, where individual agents self-correct *during* execution, and the system can repair specific components without discarding successful work.

## 2. Current Architecture Analysis

### 2.1 The "Manager-Forced Retry" Pattern
*   **Mechanism:** `IterativeExecutor` calls `team_execution_v2.py`. If the result is failure (exit code != 0 or Quality Gate fail), it analyzes logs and restarts the script.
*   **Weakness:**
    *   **Wasteful:** If the Backend is perfect but the Frontend has a typo, both are discarded and re-generated.
    *   **Context Loss:** The rich structured data from BDV/ACC (e.g., specific dependency cycles) is often flattened into logs before the Manager sees it.
    *   **Latency:** Feedback loops are long (minutes) instead of short (seconds).

### 2.2 Ecosystem Integration (DDE, BDV, ACC)
*   **DDE (Dependency-Driven Execution):** Currently acts as a **Performance Tracker** and **Verdict Aggregator**. It observes but does not actively *route* work based on real-time status.
*   **BDV (Behavior-Driven Validation):** Validates contracts *post-mortem*. It checks if the final artifacts meet the criteria but doesn't guide the generation process.
*   **ACC (Architectural Conformance Checking):** Checks for structural violations (cycles, layering) at the end.

## 3. Improvement Recommendations

### 3.1 Strengthen `PersonaExecutorV2` (The "Self-Correcting Worker")
**Goal:** Catch 80% of errors *before* the persona finishes their turn.

*   **Action:** Implement an internal "Micro-Loop" within `PersonaExecutorV2.execute()`.
    1.  **Generate:** AI writes code.
    2.  **Verify:** Run syntax check (`ast.parse`), linting, and basic unit tests.
    3.  **Refine:** If verification fails, feed the error back to the AI immediately (up to 3 attempts).
    4.  **Submit:** Only return when code is valid or retries exhausted.

### 3.2 Enhance `ParallelCoordinatorV2` (The "Smart Orchestrator")
**Goal:** Enable partial re-execution and dynamic dependency management.

*   **Action:** Implement **Stateful Execution**.
    *   Save the state of *each* persona (Success/Failure) to disk (`execution_state.json`).
    *   On retry, check the state. If Backend is `SUCCESS` and unchanged, skip it and reuse artifacts. Only re-run the failed Frontend.
    *   **DDE Integration:** Use DDE to determine if a change in Backend *requires* a re-run of Frontend (dependency impact analysis).

### 3.3 Deepen Trimodal Integration (The "Guiding Rails")
**Goal:** Use DDE, BDV, and ACC as *inputs* to the AI, not just outputs for the user.

*   **BDV-Driven Prompting:**
    *   *Current:* "Here is the requirement." -> Code -> Validate.
    *   *Proposed:* "Here is the requirement AND the Gherkin acceptance criteria." -> Code (AI writes tests first) -> Validate.
    *   Inject the `acceptance_criteria` directly into the System Prompt as "Must-Pass Tests".

*   **ACC-Aware Generation:**
    *   Inject the project's architectural rules (e.g., "Domain layer cannot import Infrastructure") into the prompt.
    *   Run ACC *during* the Micro-Loop (3.1) to catch architectural drift early.

### 3.4 The "Feedback Highway"
**Goal:** Ensure the `IterativeExecutor` sees exactly what went wrong.

*   **Action:** Standardize the Failure Protocol.
    *   `team_execution_v2.py` should output a `failure_report.json` containing:
        *   `failed_persona`: "frontend_developer"
        *   `error_type`: "ACC_VIOLATION"
        *   `details`: "Circular dependency detected between A and B"
        *   `recommended_fix`: "Extract shared logic to C"
    *   `IterativeExecutor` reads this JSON and constructs a **Targeted Repair Prompt** for the next run.

## 4. Implementation Roadmap

### Phase 1: The Self-Correcting Persona
- [ ] Modify `PersonaExecutorV2` to include a `syntax_check` step.
- [ ] Add a simple `while attempts < 3` loop for self-correction.

### Phase 2: Stateful Orchestration
- [ ] Update `ParallelCoordinatorV2` to save/load `execution_state.json`.
- [ ] Add logic to skip successful personas on retry.

### Phase 3: Trimodal Injection
- [ ] Update `team_execution_v2.py` to generate Gherkin features *before* coding.
- [ ] Pass Gherkin features to `PersonaExecutorV2`.

## 5. Conclusion
By moving validation "left" (into the persona) and making orchestration "stateful" (skipping successful work), we can reduce cycle time by 50-70% and significantly increase the success rate of complex tasks. The Trimodal Validation (DDE/BDV/ACC) should evolve from a "Final Exam" to a "Continuous Tutor."
