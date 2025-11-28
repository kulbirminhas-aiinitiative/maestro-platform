# DEPRECATION NOTICE

**Date**: 2025-10-11
**Status**: ❌ DEPRECATED - DO NOT USE

---

## Deprecated Files

The following files have been deprecated and moved to this directory as part of Phase 1 critical fixes:

### 1. `dag_api_server.py` (Legacy)
- **Reason**: Used MockEngine instead of real TeamExecutionEngineV2SplitMode
- **Risk**: Simulated results, not production-ready
- **Replacement**: `/dag_api_server.py` (canonical)

### 2. `dag_api_server_postgres.py` (Intermediate)
- **Reason**: Contains silent fallback to in-memory store
- **Risk**: Data loss if database unavailable
- **Replacement**: `/dag_api_server.py` (canonical)

---

## Why These Were Deprecated

### Issue: Code Duplication
Having 3 API server implementations created confusion:
- Which file should developers use?
- Which file is production-ready?
- Inconsistent behavior between versions

### Issue: MockEngine Usage
The legacy `dag_api_server.py` used a `MockEngine` for workflow generation:
```python
# DEPRECATED PATTERN
engine = MockEngine()  # ❌ Not real execution
workflow = generate_parallel_workflow(team_engine=engine)
```

This produced simulated results instead of real execution.

### Issue: Silent Fallback
The intermediate `dag_api_server_postgres.py` had dangerous fallback logic:
```python
# DEPRECATED PATTERN
try:
    context_store = DatabaseWorkflowContextStore()
except Exception:
    context_store = WorkflowContextStore()  # ❌ Silent fallback to memory
```

This caused:
- Data loss on server restart
- Inconsistent behavior between instances
- No alerts that system was degraded

---

## Migration Path

### If You're Using `dag_api_server.py` (Legacy)

**Replace**:
```bash
python3 dag_api_server.py
```

**With**:
```bash
# SQLite (development)
USE_SQLITE=true python3 dag_api_server.py

# PostgreSQL (production)
python3 dag_api_server.py
```

**Changes**:
- Now uses real `TeamExecutionEngineV2SplitMode`
- Requires database connection (fails fast if unavailable)
- Version 3.0.0 with production-ready features

---

### If You're Using `dag_api_server_postgres.py` (Intermediate)

**Replace**:
```bash
python3 dag_api_server_postgres.py
```

**With**:
```bash
python3 dag_api_server.py
```

**Changes**:
- No more silent fallback to in-memory store
- Fails fast if database unavailable
- Same PostgreSQL/SQLite support
- Version 3.0.0

---

### If You're Using `dag_api_server_robust.py`

**Replace**:
```bash
python3 dag_api_server_robust.py
```

**With**:
```bash
python3 dag_api_server.py
```

**Note**: `dag_api_server_robust.py` still exists in the root directory for backward compatibility, but `dag_api_server.py` is now the canonical version with the critical fixes applied.

---

## What Changed in the New Canonical Version

### 1. ✅ Fail-Fast on Database Errors

**Before** (dag_api_server_postgres.py):
```python
try:
    initialize_database(create_tables=True)
except Exception as e:
    logger.warning("Falling back to in-memory store")  # ❌ Silent failure
    context_store = WorkflowContextStore()
```

**After** (dag_api_server.py):
```python
try:
    initialize_database(create_tables=True)
except Exception as e:
    logger.error("❌ CRITICAL: Database is required")
    raise SystemExit(1)  # ✅ Fail fast
```

---

### 2. ✅ Real Engine (Not Mock)

**Before** (dag_api_server.py - legacy):
```python
engine = MockEngine()  # ❌ Simulated
```

**After** (dag_api_server.py - canonical):
```python
engine = TeamExecutionEngineV2SplitMode()  # ✅ Real execution
```

---

### 3. ✅ Required ContextStore

The canonical version uses `DAGExecutor` which now requires a `context_store`:

```python
# DAGExecutor now requires context_store (not Optional)
executor = DAGExecutor(
    workflow=workflow,
    context_store=context_store,  # ✅ REQUIRED
    event_handler=event_handler
)
```

This prevents accidental data loss from missing persistence.

---

## Testing the New Version

### 1. Health Check
```bash
# Start server
USE_SQLITE=true python3 dag_api_server.py

# Check health
curl http://localhost:8003/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "type": "SQLite"
  }
}
```

### 2. Execute Workflow
```bash
curl -X POST http://localhost:8003/api/workflows/sdlc_parallel/execute \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Test workflow with new canonical server"
  }'
```

Expected response:
```json
{
  "execution_id": "exec_...",
  "workflow_id": "sdlc_parallel",
  "status": "running"
}
```

### 3. Verify No Fallback
```bash
# Stop database (if using PostgreSQL)
# Restart server - should FAIL immediately with:
# "❌ CRITICAL: Database is required for production operation"
# "❌ CRITICAL: Server will not start without database"
```

✅ **Success**: Server refuses to start without database

---

## Rollback Plan (If Needed)

If you need to temporarily rollback to the old version:

```bash
# Restore from deprecated_code
cp deprecated_code/dag_api_server_postgres.py dag_api_server_temp.py
python3 dag_api_server_temp.py
```

**WARNING**: Only use this for emergency rollback. The deprecated versions have known issues:
- Data loss risk (in-memory fallback)
- MockEngine usage (simulated results)
- No fail-fast behavior

---

## Timeline

- **2025-10-11**: Files deprecated and moved to `deprecated_code/`
- **2025-10-11**: Canonical `dag_api_server.py` created with critical fixes
- **2025-11-11** (30 days): Deprecated files will be permanently deleted
- **2025-11-11** (30 days): `dag_api_server_robust.py` will be removed (replaced by `dag_api_server.py`)

---

## Related Documentation

- [Executive Feedback Action Plan](../DAG_EXECUTIVE_FEEDBACK_ACTION_PLAN.md)
- [DAG Architecture](../AGENT3_DAG_WORKFLOW_ARCHITECTURE.md)
- [Workflow Initiation Guide](../DAG_WORKFLOW_INITIATION_AND_CONTRACTS_GUIDE.md)

---

## Questions?

If you have questions about this deprecation or the migration path, refer to:
- `DAG_EXECUTIVE_FEEDBACK_ACTION_PLAN.md` - Why these changes were made
- `PHASE_1_COMPLETION_REPORT.md` - Implementation details
- GitHub Issues - For specific migration problems

---

**Status**: ✅ Migration Complete - Use `/dag_api_server.py` (canonical)
**Version**: 3.0.0
**Last Updated**: 2025-10-11
