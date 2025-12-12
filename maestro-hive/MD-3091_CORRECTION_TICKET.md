# JIRA Ticket: MD-3091-CORRECTION

**Title:** Fix Missing State Persistence in Unified Execution Foundation
**Type:** Bug / Technical Debt
**Priority:** **Blocker**
**Component:** Unified Execution
**Epic:** MD-3091 (Unified Execution Foundation)

## Description
The initial implementation of MD-3091 (`PersonaExecutor` and `SafetyRetryWrapper`) failed to implement the critical requirement of **State Persistence**. The current implementation runs entirely in-memory, meaning any process restart results in total loss of execution state. This violates the core architectural goal of "Smart Resume".

This ticket tracks the work to integrate the existing `StateManager` infrastructure into the new unified execution classes.

## Current Gaps
1.  `PersonaExecutor` does not import or use `StateManager`.
2.  `SafetyRetryWrapper` does not persist circuit breaker state.
3.  `config.py` defines state paths (`/var/maestro/state`), but they are ignored by the code.

## Acceptance Criteria
1.  **StateManager Integration:**
    *   `PersonaExecutor` must initialize `StateManager` using the path from `self.config.state.state_dir`.
    *   `PersonaExecutor` must save its state (attempts, status, output) to disk after every significant state change.
2.  **Smart Resume:**
    *   On initialization, `PersonaExecutor` must check for existing state for the given `execution_id` or `task_name`.
    *   If valid state exists, it must load it and resume (e.g., skip already successful steps).
3.  **Circuit Breaker Persistence:**
    *   `SafetyRetryWrapper` must persist the `CircuitBreaker` state (open/closed, failure counts) so that cooldowns survive restarts.
4.  **Verification:**
    *   A test case must demonstrate: Start Execution -> Kill Process -> Restart Execution -> Resume from last state.

## Technical Implementation Plan
1.  **Modify `src/maestro_hive/unified_execution/persona_executor.py`**:
    *   Import `StateManager` from `src.maestro_hive.core.state_manager`.
    *   Add `_load_state()` and `_save_state()` methods.
    *   Call `_save_state()` in `execute()` loop.
2.  **Modify `src/maestro_hive/unified_execution/safety_retry.py`**:
    *   Integrate `StateManager` to persist `CircuitBreaker` data.

## Dependencies
*   `src/maestro_hive/core/state_manager.py` (Existing)

## Definition of Done
*   Code implemented.
*   Unit tests added for state persistence.
*   Manual verification of "Kill & Resume" scenario.
