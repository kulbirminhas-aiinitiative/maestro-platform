# Design: Phased Execution & Rerunnability for Maestro Hive

## 1. Problem Statement
The current `TeamExecutionEngineV2` executes workflows monolithically. If a failure occurs (e.g., networking issue) midway through execution, the entire workflow must be restarted from the beginning. There is no built-in mechanism to resume from the last successful state.

Additionally, there is a requirement to support flexible execution models:
- **Phased Execution**: Running only specific phases (e.g., "requirements" only).
- **Partial Execution**: Starting from a later phase (e.g., "development") using external inputs.
- **End-to-End**: Running the full lifecycle but with checkpointing for safety.

## 2. Solution Overview
We will promote the "partially built" `TeamExecutionEngineV2SplitMode` from deprecated code to the production codebase. This engine is designed specifically to handle phase-by-phase execution with state persistence.

### Key Features of Split Mode Engine:
1.  **Checkpoints**: Saves state (context, artifacts, decisions) after each phase to a JSON file.
2.  **Resumability**: Can load a checkpoint and resume execution from the next phase.
3.  **Granular Control**: `execute_phase()` method allows running a single phase in isolation.
4.  **Flexibility**: Supports `execute_batch()` for continuous runs and `execute_mixed()` for hybrid approaches.

## 3. Architecture

### 3.1 Class Structure
The `TeamExecutionEngineV2SplitMode` will be located in `src/maestro_hive/teams/team_execution_v2_split_mode.py`.

It interacts with:
-   **`TeamExecutionEngineV2`**: The base engine used for the actual work within a phase.
-   **`TeamExecutionContext`**: A data class (already in `src/maestro_hive/teams/`) that holds the state, including:
    -   `session_id`
    -   `current_phase`
    -   `artifacts` (files created)
    -   `decisions` (AI choices like blueprints)
    -   `phase_results` (history of completed phases)

### 3.2 Execution Flow (Rerunnability)
1.  **Start**: User starts a job. Engine creates a session and `checkpoint_init.json`.
2.  **Phase 1 (Requirements)**: Engine runs analysis. On success, saves `checkpoint_requirements.json`.
3.  **Failure**: Network fails during Phase 2 (Design).
4.  **Resume**: User requests resume with Session ID.
5.  **Recovery**: Engine loads `checkpoint_requirements.json`.
6.  **Continue**: Engine detects Phase 1 is done, skips it, and starts Phase 2.

### 3.3 Execution Flow (Phased/DAG)
The engine exposes methods that map directly to DAG nodes:
-   `execute_phase("requirements", ...)`
-   `execute_phase("design", ...)`
-   `execute_phase("implementation", ...)`

This allows a DAG orchestrator (like the one in `run_dag_workflow_direct.py`) to call these methods individually, managing dependencies externally if needed, or letting the engine manage the linear sequence.

## 4. Implementation Plan

1.  **Restore Code**: Move `deprecated_code/versioned_files/team_execution_v2_split_mode.py` to `src/maestro_hive/teams/team_execution_v2_split_mode.py`.
2.  **Update Imports**: Ensure it imports `TeamExecutionEngineV2` and `TeamExecutionContext` correctly from the `src` structure.
3.  **Integration**: Verify that `run_dag_workflow_direct.py` (which already tries to import this) works correctly once the file is in place.
4.  **Verification**: Create a test script `test_phased_execution.py` to simulate a multi-step run with a simulated interruption.

## 5. Future Enhancements
-   **API Integration**: Expose the `resume` functionality via the `workflow_api_v2.py` endpoints.
-   **UI Support**: Allow frontend to list available checkpoints and trigger resumption.
