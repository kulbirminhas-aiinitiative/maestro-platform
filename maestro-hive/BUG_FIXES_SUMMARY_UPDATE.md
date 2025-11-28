# Bug Fixes Summary - Update

**Date**: 2025-10-12
**Status**: 4 of 5 bugs fixed, 1 remaining

---

## ✅ Bugs Fixed (1-4)

### Bug 1: BlueprintMetadata Dict Access
**Status**: ✅ FIXED
**File**: `team_execution_v2.py:441-450`
**Fix**: Changed dict subscript to object attribute access

### Bug 2: PackageRecommendation Wrong Attributes
**Status**: ✅ FIXED
**File**: `team_execution_v2.py:890-897, 992-997`
**Fix**: Updated to correct attribute names from dataclass definition

### Bug 3: Wrong maestro-engine Path
**Status**: ✅ FIXED
**File**: `personas.py:27`
**Fix**: Updated path from `maestro-engine` to `maestro-engine-new`

### Bug 4: Personas Not Loaded (CLI)
**Status**: ✅ FIXED
**File**: `personas.py:72-76`
**Fix**: Added async loading logic for CLI context

---

## ⚠️ Bug 5: Personas Loading in FastAPI Async Context

**Status**: 🔧 IN PROGRESS
**Error**: `asyncio.run() cannot be called from a running event loop`

**Root Cause**: The persona loading system uses `asyncio.run()` which doesn't work inside FastAPI's running event loop.

**Files Affected**:
- `personas.py` - Async loading logic
- `dag_api_server_robust.py` - Server startup
- `persona_executor_v2.py` - Persona initialization

**Problem**: When TeamExecutionEngineV2 is initialized inside the FastAPI server:
1. Request comes in → creates TeamExecutionEngineV2
2. Team engine loads personas via SDLCPersonas.get_all_personas()
3. personas.py tries to use asyncio.run() to load personas
4. asyncio.run() fails because FastAPI already has a running event loop
5. Request hangs indefinitely

**Attempted Fixes**:
1. ❌ Threading with asyncio.run() - Still hangs in certain contexts
2. ❌ Pre-loading during server startup - Pre-loading itself hangs
3. 🔧 Need different approach

**Next Steps**:
- Option A: Use sync persona loading (no async)
- Option B: Use fallback personas in server context
- Option C: Pre-initialize engine before FastAPI starts

---

## Working Context

**CLI Context**: ✅ All personas load successfully
**Server Context**: ❌ Hangs on persona loading

This suggests the async loading mechanism needs to be redesigned for dual-context usage (CLI + FastAPI).

---

## Test Command

```bash
# CLI - Works
python3 -c "from personas import SDLCPersonas; print(len(SDLCPersonas.get_all_personas()))"

# Server - Hangs
curl -X POST http://localhost:5001/api/workflows/sdlc_parallel/execute \
  -H "Content-Type: application/json" \
  -d '{"requirement": "test", "initial_context": {}}'
```
