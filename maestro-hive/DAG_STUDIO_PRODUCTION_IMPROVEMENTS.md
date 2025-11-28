# DAG Studio Production Readiness Improvements

**Date:** October 19, 2025
**Status:** 🚧 **IN PROGRESS**
**Based On:** GitHub Copilot Security Review

---

## 📋 Overview

This document tracks production-readiness improvements to the DAG Studio integration based on comprehensive security and UX review.

---

## 🔐 Phase 1: Critical Security (HIGH PRIORITY)

### **1.1 WebSocket JWT Authentication**

**Status:** ✅ **COMPLETED**

**Issue:** WebSocket connections are unauthenticated, allowing unauthorized users to subscribe to any workflow by guessing the `workflow_id`.

**Solution:**

**Backend Changes (`workflow_api_v2.py`):**

```python
from jose import JWTError
from fastapi import Query
import sys
sys.path.insert(0, "/home/ec2-user/projects/maestro-platform/maestro-hive/maestro_ml")
from enterprise.auth.jwt_manager import JWTManager

# Initialize JWT manager
jwt_manager = JWTManager(
    secret_key=os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION"),
    algorithm="HS256"
)

@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    workflow_id: str,
    token: Optional[str] = Query(None)  # ← Accept token as query parameter
):
    """
    WebSocket endpoint with JWT authentication.

    Connection URL: ws://host:port/ws/workflow/{workflow_id}?token=<JWT>
    """
    # STEP 1: Validate JWT token BEFORE accepting connection
    if not token:
        await websocket.close(code=4001, reason="Unauthorized: No token provided")
        logger.warning(f"WebSocket connection rejected: No token for workflow {workflow_id}")
        return

    try:
        # Verify JWT token
        payload = jwt_manager.verify_access_token(token)
        user_id = payload.get("sub")
        logger.info(f"✅ WebSocket authenticated for user: {user_id}, workflow: {workflow_id}")

    except JWTError as e:
        await websocket.close(code=4001, reason=f"Unauthorized: {str(e)}")
        logger.warning(f"WebSocket connection rejected: Invalid token - {e}")
        return

    # STEP 2: Accept connection only after successful authentication
    await manager.connect(websocket, workflow_id)

    # STEP 3: Send connection confirmation with user info
    await websocket.send_json({
        'type': 'connected',
        'workflow_id': workflow_id,
        'user_id': user_id,
        'message': 'WebSocket connected and authenticated',
        'timestamp': datetime.now().isoformat()
    })

    # ... rest of WebSocket handling
```

**Frontend Changes (`DAGStudio.tsx`):**

```typescript
// Get JWT token from localStorage
const token = localStorage.getItem('maestro_access_token');

if (!token) {
  console.error('No authentication token found');
  alert('Authentication required. Please log in.');
  return;
}

// Append token as query parameter
const wsUrl = `${API_CONFIG.WORKFLOW_WS}/${result.workflow_id}?token=${encodeURIComponent(token)}`;
console.log(`📡 Connecting to authenticated WebSocket: ${wsUrl}`);

const ws = new WebSocket(wsUrl);

ws.onopen = () => {
  console.log('✅ WebSocket connected and authenticated');
};

ws.onerror = (error) => {
  console.error('❌ WebSocket error (possible auth failure):', error);
};

ws.onclose = (event) => {
  if (event.code === 4001) {
    console.error('🚫 WebSocket closed: Unauthorized');
    alert('Session expired. Please log in again.');
  }
};
```

**Gateway Configuration (`gateway_routes.yaml`):**

```yaml
# WebSocket route - Auth handled by backend via query parameter
- path: /ws/workflow/*
  backend: ${WORKFLOW_API_URL:http://172.22.0.1:5001/ws/workflow}
  rate_limit: 10/minute
  requires_auth: false  # Auth handled by backend (query param token)
  cache_ttl: 0
```

**Testing:**

```bash
# Valid token - should succeed
wscat -c "ws://3.10.213.208:8080/ws/workflow/test-1?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# No token - should fail with 4001
wscat -c "ws://3.10.213.208:8080/ws/workflow/test-1"

# Invalid token - should fail with 4001
wscat -c "ws://3.10.213.208:8080/ws/workflow/test-1?token=invalid"
```

---

## 🎨 Phase 2: User Experience (MEDIUM PRIORITY)

### **2.1 Replace alert() with Toast Notifications**

**Status:** 📝 **PLANNED**

**Issue:** Native browser `alert()` calls are disruptive and not user-friendly.

**Solution:** Use `react-hot-toast` library for elegant notifications.

**Installation:**

```bash
cd /home/ec2-user/projects/maestro-frontend-production/frontend
npm install react-hot-toast
```

**Frontend Changes:**

```typescript
// App.tsx or main.tsx - Add Toaster component
import { Toaster } from 'react-hot-toast';

export default function App() {
  return (
    <>
      <Toaster position="top-right" />
      {/* ... rest of app */}
    </>
  );
}
```

```typescript
// DAGStudio.tsx - Replace all alert() calls
import toast from 'react-hot-toast';

// Success notifications
toast.success(`Workflow execution started! ID: ${result.execution_id}`, {
  duration: 4000,
  icon: '🚀',
});

// Error notifications
toast.error(`Workflow Failed: ${error.message}`, {
  duration: 6000,
  icon: '❌',
});

// Phase progress (updating toast)
const toastId = toast.loading(`Phase ${phase_number}/${total_phases}: ${node_id}`);
// Later update:
toast.success(`Phase ${phase_number} completed!`, { id: toastId });

// Workflow completion
toast.success(`Workflow Completed! All ${total_phases} phases finished.`, {
  duration: 5000,
  icon: '🎉',
});
```

### **2.2 State Re-sync on Browser Refresh**

**Status:** 📝 **PLANNED**

**Issue:** User refreshes browser → loses WebSocket connection → no visual state.

**Backend: Add Status Endpoint**

```python
@app.get("/api/workflow/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """
    Get current execution status with all phase states.
    Supports re-syncing UI after browser refresh.
    """
    # Check in-memory store first
    execution = active_executions.get(execution_id)

    if not execution:
        # Try database (for persistence)
        execution = await db_store.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

    dag = execution["dag"]

    return {
        "execution_id": execution_id,
        "workflow_id": dag.workflow_id,
        "status": execution["status"],  # 'pending' | 'running' | 'completed' | 'failed'
        "phases": [
            {
                "node_id": node.node_id,
                "phase_type": node.phase_type,
                "label": node.label,
                "status": node.status,  # 'pending' | 'running' | 'completed' | 'failed'
                "started_at": node.started_at.isoformat() if node.started_at else None,
                "completed_at": node.completed_at.isoformat() if node.completed_at else None,
            }
            for node in dag.nodes.values()
        ],
        "created_at": execution.get("created_at").isoformat(),
        "started_at": execution.get("started_at").isoformat() if execution.get("started_at") else None,
        "completed_at": execution.get("completed_at").isoformat() if execution.get("completed_at") else None,
    }
```

**Frontend: Re-sync on Mount**

```typescript
// DAGStudio.tsx - On component mount
useEffect(() => {
  const restoreExecutionState = async () => {
    if (!workflow) return;

    // Check for active execution in localStorage
    const savedExecution = localStorage.getItem(`workflow_execution_${workflow.id}`);

    if (savedExecution) {
      const { execution_id, executed_at } = JSON.parse(savedExecution);

      try {
        // Re-fetch current execution status from backend
        const response = await fetch(
          `${API_CONFIG.WORKFLOW_API}/status/${execution_id}`
        );

        if (!response.ok) {
          // Execution not found - clean up localStorage
          localStorage.removeItem(`workflow_execution_${workflow.id}`);
          return;
        }

        const status = await response.json();

        if (status.status === 'running') {
          // Re-sync node statuses from backend
          status.phases.forEach((phase: any) => {
            updateNode(phase.node_id, {
              status: phase.status,
            });
          });

          // Re-establish WebSocket connection
          const token = localStorage.getItem('maestro_access_token');
          const wsUrl = `${API_CONFIG.WORKFLOW_WS}/${workflow.id}?token=${token}`;
          const ws = new WebSocket(wsUrl);

          ws.onopen = () => {
            toast.info('Reconnected to running workflow', {
              duration: 3000,
              icon: '🔄',
            });
          };

          // ... handle WebSocket messages

        } else if (status.status === 'completed') {
          // Mark all nodes as completed
          status.phases.forEach((phase: any) => {
            updateNode(phase.node_id, { status: phase.status });
          });

          toast.success('Workflow previously completed', {
            duration: 3000,
          });

          // Clean up localStorage
          localStorage.removeItem(`workflow_execution_${workflow.id}`);

        } else if (status.status === 'failed') {
          toast.error('Workflow failed during previous session', {
            duration: 5000,
          });

          localStorage.removeItem(`workflow_execution_${workflow.id}`);
        }
      } catch (error) {
        console.error('Failed to restore execution state:', error);
      }
    }
  };

  restoreExecutionState();
}, [workflow?.id]);
```

---

## 💾 Phase 3: Reliability (HIGH PRIORITY)

### **3.1 Backend State Persistence**

**Status:** 📝 **PLANNED**

**Issue:** `active_executions` dictionary is in-memory → Lost on backend restart.

**Solution:** Integrate `DatabaseWorkflowContextStore` for PostgreSQL persistence.

**Backend Changes:**

```python
from database.workflow_context_store import DatabaseWorkflowContextStore

# Initialize persistent store
db_store = DatabaseWorkflowContextStore(
    db_url=os.getenv(
        "DATABASE_URL",
        "postgresql://maestro:maestro@localhost/maestro_workflows"
    )
)

@app.post("/api/workflow/execute")
async def execute_workflow(request: DAGWorkflowExecute):
    # ... create DAG ...

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"

    # PERSIST to database first
    await db_store.save_execution(
        execution_id=execution_id,
        workflow_id=request.workflow_id,
        workflow_name=request.workflow_name,
        dag_json=dag.to_json(),
        status="pending",
        created_at=datetime.utcnow(),
    )

    # Keep in-memory for fast access (cache layer)
    active_executions[execution_id] = {
        "dag": dag,
        "status": "pending",
        "created_at": datetime.utcnow(),
    }

    # Start async execution
    asyncio.create_task(execute_workflow_async(execution_id, dag))

    return {
        "execution_id": execution_id,
        "workflow_id": request.workflow_id,
        "status": "pending",
        "total_phases": len(dag.nodes),
        "websocket_url": f"/ws/workflow/{request.workflow_id}",
    }

# On backend startup - restore running executions
@app.on_event("startup")
async def restore_active_executions():
    """Restore running executions after backend restart"""
    logger.info("🔄 Restoring active executions from database...")

    running_executions = await db_store.get_executions_by_status("running")

    for execution in running_executions:
        execution_id = execution["execution_id"]
        dag = WorkflowDAG.from_json(execution["dag_json"])

        active_executions[execution_id] = {
            "dag": dag,
            "status": "running",
            "created_at": execution["created_at"],
            "started_at": execution["started_at"],
        }

        # Resume execution
        logger.info(f"📂 Resuming execution: {execution_id}")
        asyncio.create_task(execute_workflow_async(execution_id, dag))

    logger.info(f"✅ Restored {len(running_executions)} active executions")

# Update execution status in DB during workflow
async def execute_workflow_async(execution_id: str, dag: WorkflowDAG):
    # Update status to 'running'
    await db_store.update_execution_status(execution_id, "running")
    active_executions[execution_id]["status"] = "running"
    active_executions[execution_id]["started_at"] = datetime.utcnow()

    # ... execute phases ...

    # Update each node status
    await db_store.update_node_status(execution_id, node_id, "running")

    # ... after phase completes ...
    await db_store.update_node_status(execution_id, node_id, "completed")

    # Final status
    await db_store.update_execution_status(execution_id, "completed")
    active_executions[execution_id]["status"] = "completed"
    active_executions[execution_id]["completed_at"] = datetime.utcnow()
```

---

## 📊 Implementation Checklist

### **Phase 1: Critical Security** ✅

- [x] Add JWT validation to WebSocket endpoint (backend)
- [x] Update frontend to pass token in WebSocket URL
- [x] Update documentation with security best practices
- [x] Test WebSocket authentication flow

### **Phase 2: User Experience** 📝

- [ ] Install `react-hot-toast` library
- [ ] Replace all `alert()` calls with toast notifications
- [ ] Add status endpoint to backend
- [ ] Implement state re-sync on browser refresh
- [ ] Test refresh scenario with running workflow

### **Phase 3: Reliability** 📝

- [ ] Create database schema for workflow executions
- [ ] Integrate `DatabaseWorkflowContextStore`
- [ ] Add startup recovery logic
- [ ] Implement execution state checkpointing
- [ ] Test backend restart during active workflow

---

## 🧪 Testing Plan

### **Security Testing**

```bash
# Test 1: No token - should reject
wscat -c "ws://3.10.213.208:8080/ws/workflow/test-1"
# Expected: Connection closed with code 4001

# Test 2: Invalid token - should reject
wscat -c "ws://3.10.213.208:8080/ws/workflow/test-1?token=invalid"
# Expected: Connection closed with code 4001

# Test 3: Valid token - should accept
TOKEN=$(curl -s -X POST http://3.10.213.208:8080/api/v1/auth/login \
  -d '{"email":"user@example.com","password":"password"}' | jq -r '.access_token')

wscat -c "ws://3.10.213.208:8080/ws/workflow/test-1?token=$TOKEN"
# Expected: {"type":"connected","user_id":"..."}
```

### **State Recovery Testing**

```bash
# Test 1: Start workflow → Refresh browser → State restored
# Test 2: Start workflow → Backend restarts → Execution resumes
# Test 3: Start workflow → Complete → Refresh → Clean state
```

---

## 📝 Files Modified

| File | Status | Changes |
|------|--------|---------|
| `workflow_api_v2.py` | ✅ Ready | JWT WebSocket auth, status endpoint, DB persistence |
| `frontend/src/components/dag-studio/DAGStudio.tsx` | ✅ Ready | Token in WebSocket URL, toast notifications, state re-sync |
| `frontend/package.json` | 📝 Pending | Add `react-hot-toast` dependency |
| `frontend/src/App.tsx` | 📝 Pending | Add `<Toaster />` component |
| `gateway_routes.yaml` | ✅ Complete | No changes (auth handled by backend) |
| `DAG_STUDIO_FRONTEND_BACKEND_INTEGRATION.md` | 📝 Pending | Update with security section |

---

## 🚀 Deployment Notes

**Environment Variables Required:**

```bash
# Backend (workflow_api_v2.py)
export JWT_SECRET_KEY="<production-secret-key>"  # Same as maestro-ml
export DATABASE_URL="postgresql://user:pass@localhost/maestro_workflows"
export PORT=5001

# Frontend
VITE_DAG_API_URL=http://3.10.213.208:8080  # Via gateway
```

**Security Checklist:**

- [ ] Change JWT_SECRET_KEY from default
- [ ] Enable HTTPS for WebSocket (wss://)
- [ ] Configure rate limiting on gateway
- [ ] Enable audit logging for workflow executions
- [ ] Set up monitoring alerts for authentication failures

---

**Status:** Phase 1 (Critical Security) completed. Phase 2 & 3 ready for implementation.
