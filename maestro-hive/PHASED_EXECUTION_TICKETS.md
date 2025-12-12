# Phased Execution Implementation Plan

**Epic:** [MD-3157] Phased Execution & Rerunnability Implementation

This document tracks the JIRA tickets created to implement the recommendations from `DESIGN_REVIEW_PHASED_EXECUTION.md`.

## Implementation Tasks

| Ticket | Summary | Description |
|--------|---------|-------------|
| **MD-3158** | Standardize SDLC Phases | Create a single source of truth for SDLC phases (`src/maestro_hive/config/phases.py`) and unify `TeamExecutionEngineV2SplitMode` and `resume_failed_workflow.py`. |
| **MD-3159** | Refactor Resume Script | Update `resume_failed_workflow.py` to use `TeamExecutionEngineV2SplitMode.resume_from_checkpoint()` for correct context hydration. |
| **MD-3160** | Add JIRA Task Wrapper | Implement `execute_jira_task()` in SplitMode engine to support JIRA-driven workflows (wrapping `execute_batch`). |
| **MD-3161** | Expose Resume API | Add `POST /api/workflow/{id}/resume` endpoint to `workflow_api_v2.py`. |
| **MD-3162** | Synthetic Checkpoint Generator | Create utility to generate checkpoints from external inputs (e.g., Design Doc) for partial execution. |
| **MD-3163** | Checkpoint Rotation | Implement cleanup policy for checkpoint files (last N or TTL). |
| **MD-3164** | Integration Tests | Create test suite for the full Create -> Fail -> Resume lifecycle. |

## Next Steps

1.  **Review**: Confirm the scope of these tickets matches the design review.
2.  **Assignment**: Assign tickets to development agents.
3.  **Execution**: Begin work on MD-3158 (Standardization) as it is a dependency for others.
