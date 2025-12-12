# Bug Report: MD-3051 - Claude CLI EBADF Error

## Problem Description
When running the self-healing loop (`trigger_healing.py`) in the background (via `nohup`), the execution fails during the AI Requirement Analysis phase.

**Error Log:**
```
2025-12-10 17:30:35,115 [ERROR] Claude CLI error: node:events:497
      throw er; // Unhandled 'error' event
      ^

Error: EBADF: bad file descriptor, read
Emitted 'error' event on ReadStream instance at:
    at emitErrorNT (node:internal/streams/destroy:170:8)
    at errorOrDestroy (node:internal/streams/destroy:239:7)
    at node:internal/fs/streams:275:9
    at FSReqCallback.wrapper [as oncomplete] (node:fs:671:5) {
  errno: -9,
  code: 'EBADF',
  syscall: 'read'
}
```

## Analysis
The error `EBADF: bad file descriptor, read` indicates that the Node.js process (Claude CLI) is attempting to read from a file descriptor that is not valid or open.

This occurs because:
1. The script is run with `nohup ... &`, which typically redirects `stdin` to `/dev/null` or closes it.
2. The `claude_code_sdk.py` uses `asyncio.create_subprocess_exec` but does not explicitly configure `stdin`.
3. The `claude` CLI tool likely attempts to read from `stdin` (perhaps to check for interactivity or input), and fails when the descriptor is in a "bad" state.

## Proposed Fix
Modify `src/maestro_hive/claude_code_sdk.py` (or the root `claude_code_sdk.py` if that's the one being used - checking paths shows `claude_code_sdk.py` in root) to explicitly set `stdin` to `DEVNULL`.

**File:** `claude_code_sdk.py`

**Change:**
```python
        # Execute Claude CLI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(work_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL  # <--- Add this
        )
```

## Verification Plan
1. Apply the fix.
2. Re-run the `trigger_healing.py` command in the background.
3. Verify that the `EBADF` error is gone and the process proceeds past the AI analysis step.
