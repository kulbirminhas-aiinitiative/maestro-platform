# JIRA Issues Report

## MD-3054: `team_execution_v2.py` fails with EBADF in background execution
**Type:** Bug
**Priority:** High
**Component:** Team Execution Engine / Claude Integration
**Status:** Open

**Description:**
The `team_execution_v2.py` script fails when executed in the background (e.g., via `nohup` or systemd) because the underlying `ClaudeCLIClient` attempts to read from `stdin`, which is invalid or closed in background contexts.

**Symptoms:**
- Log files show `Error: EBADF: bad file descriptor, read` coming from the `claude` CLI.
- The process crashes during "Step 1: AI Requirement Analysis".

**Root Cause:**
The `ClaudeCLIClient` (imported from `claude_code_api_layer`) uses `subprocess.run` without explicitly handling `stdin`. By default, it inherits the parent's `stdin`. When the parent is `nohup`, `stdin` is not a valid stream for reading, causing the Node.js-based Claude CLI to crash.

**Proposed Fix:**
Update the `ClaudeCLIClient` to explicitly set `stdin=subprocess.DEVNULL` when invoking the subprocess.

---

## MD-3055: Duplicate Claude SDK Implementations causing maintenance issues
**Type:** Technical Debt
**Priority:** Medium
**Component:** Infrastructure
**Status:** Open

**Description:**
There are at least two distinct implementations of the Claude SDK in the codebase/environment:
1. `claude_code_sdk.py` (Local, Asyncio-based)
2. `claude_code_api_layer` (External package, Subprocess-based)

`team_execution_v2.py` currently relies on the external `claude_code_api_layer`, while other parts of the system might be using the local SDK. Fixes applied to one (like the `stdin` fix) do not propagate to the other, leading to confusion and regression.

**Proposed Fix:**
Consolidate usage to a single, robust SDK implementation within the `maestro-hive` repository.
