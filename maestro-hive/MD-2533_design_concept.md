# MD-2533: Self-Healing & Auto-Refactoring Design
## Parallelism with Gap-to-JIRA (MD-2501)

You correctly identified the parallelism between `gap_to_jira.py` and the requirements for MD-2533. They represent the two halves of the **Self-Improving Platform** vision.

| Feature | `gap_to_jira.py` (MD-2501) | `auto_heal.py` (MD-2533) |
| :--- | :--- | :--- |
| **Loop Type** | **Administrative Feedback Loop** | **Technical Feedback Loop** |
| **Trigger** | Static Analysis Gaps (Missing Files/Caps) | Runtime Failures (Test Failures/Exceptions) |
| **Input Source** | `GapDetector` | `ExecutionHistory` / `TestRunner` |
| **Decision Engine** | Deterministic Rules (If missing -> Ticket) | AI/RAG (Analyze Error -> Generate Fix) |
| **Action** | Create/Update JIRA Ticket | Apply Code Patch / Refactor |
| **Outcome** | Human Task Created | Automated Fix Applied |

## Proposed Architecture for MD-2533

We can leverage the architectural pattern of `gap_to_jira.py` to implement MD-2533.

### 1. The Loop (`auto_heal.py`)
Similar to `gap_to_jira.py`, this script will:
1.  **Scan**: Read failure patterns (from logs or `execution_history`).
2.  **Deduplicate**: Check if this failure is already being handled (hash of error trace).
3.  **Act**: Instead of calling JIRA, call the `RefactoringEngine`.

### 2. The Components
*   **FailureDetector**: (Analogous to `GapDetector`) Parses logs/test results to identify distinct failures.
*   **RefactoringEngine**: (The "Client")
    *   Retrieves context (RAG).
    *   Generates a fix (LLM).
    *   Applies the fix (File Edit).
    *   Verifies the fix (Run Test).

### 3. Integration
*   **Gap-to-JIRA** handles the "Unknown Unknowns" or structural gaps.
*   **Auto-Heal** handles the "Known Unknowns" or runtime breaks.

## Next Steps
1.  Scaffold `src/maestro_hive/core/self_reflection/auto_heal.py` using `gap_to_jira.py` as a template.
2.  Implement `FailureDetector` to parse `pytest` output or application logs.
3.  Implement a basic `RefactoringEngine` (initially just for simple patterns, e.g., missing imports).
