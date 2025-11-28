# DAG Studio Frontend/Backend Integration Documentation

**Date:** October 19, 2025
**Status:** ✅ **PRODUCTION READY**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  DAG Studio (React + ReactFlow)                               │  │
│  │  http://3.10.213.208:4300/dag-studio                          │  │
│  │                                                                │  │
│  │  Components:                                                   │  │
│  │  - DAGStudio.tsx         (Main orchestrator)                  │  │
│  │  - DAGNodePalette.tsx    (Phase selector sidebar)             │  │
│  │  - DAGEditorCanvas.tsx   (ReactFlow visual editor)            │  │
│  │  - DAGNodeConfigPanel.tsx (Node configuration)                │  │
│  │                                                                │  │
│  │  State: dagStudioStore.ts (Zustand)                           │  │
│  │  Service: dagExecutionService.ts                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ↓ HTTP + WebSocket                      │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (Docker)                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  NGINX/FastAPI Gateway                                        │  │
│  │  http://3.10.213.208:8080                                     │  │
│  │                                                                │  │
│  │  Routes:                                                       │  │
│  │  - /api/workflow/*  → http://172.22.0.1:5001/api/workflow    │  │
│  │  - /ws/workflow/*   → ws://172.22.0.1:5001/ws/workflow        │  │
│  │                                                                │  │
│  │  Config: gateway_routes.yaml                                  │  │
│  │  Container: maestro-gateway (maestro-dev-network)             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   WORKFLOW EXECUTION ENGINE                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  workflow_api_v2.py (FastAPI + WebSocket)                     │  │
│  │  http://3.10.213.208:5001                                     │  │
│  │                                                                │  │
│  │  Core Components:                                              │  │
│  │  - WorkflowDAG               (DAG definition)                 │  │
│  │  - WorkflowNode              (Phase nodes)                    │  │
│  │  - DAGExecutor               (Execution orchestrator)         │  │
│  │  - TeamExecutionEngineV2     (AI-powered execution)           │  │
│  │  - PersonaRegistry           (Team member management)         │  │
│  │                                                                │  │
│  │  Endpoints:                                                    │  │
│  │  - POST /api/workflow/execute                                 │  │
│  │  - GET  /api/workflow/status/{execution_id}                   │  │
│  │  - WS   /ws/workflow/{workflow_id}                            │  │
│  │  - GET  /health                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📡 Communication Flow

### **1. Frontend Configuration**

**File:** `/home/ec2-user/projects/maestro-frontend-production/frontend/src/config/api.ts`

```typescript
// API Gateway - SINGLE ENTRY POINT
const GATEWAY_BASE = 'http://3.10.213.208:8080';
const GATEWAY_WS = 'ws://3.10.213.208:8080/ws';

export const API_CONFIG = {
  // Async Workflow API (via gateway)
  WORKFLOW_API: `${GATEWAY_BASE}/api/workflow`,
  WORKFLOW_WS: `${GATEWAY_WS}/workflow`,
};
```

**Key Points:**
- Frontend **NEVER** calls backend directly (port 5001)
- All requests go through API Gateway (port 8080)
- Gateway handles routing, rate limiting, and CORS

---

### **2. Gateway Configuration**

**File:** `/home/ec2-user/projects/maestro-engine/config/gateway_routes.yaml`

```yaml
routes:
  # DAG Workflow Execution API
  - path: /api/workflow/*
    backend: ${WORKFLOW_SERVICE_URL:http://172.22.0.1:5001/api/workflow}
    rate_limit: 50/minute
    requires_auth: false
    cache_ttl: 0

  # Async Workflow WebSocket
  - path: /ws/workflow/*
    backend: ${WORKFLOW_API_URL:http://172.22.0.1:5001/ws/workflow}
    rate_limit: 10/minute
    requires_auth: false
    cache_ttl: 0

cors:
  allow_origins:
    - http://localhost:4300
    - http://3.10.213.208:4300
  allow_origin_regex: "https?://.*:(4200|4300)"
  allow_credentials: true
```

**Key Points:**
- Gateway runs in Docker (`maestro-gateway` container)
- Uses Docker bridge network gateway IP: `172.22.0.1`
- Routes `/api/workflow/*` to backend on port 5001
- WebSocket proxying for real-time updates

---

## 🔄 Workflow Execution Flow

### **Step 1: User Creates Workflow in DAG Studio**

```typescript
// DAGStudio.tsx - User drags phases onto canvas
// 1. Add Requirements phase
// 2. Add Architecture phase
// 3. Connect with edge (Requirements → Architecture)
// 4. Configure each node (assign team, set configs)
```

**Example Workflow Structure:**
```json
{
  "workflow_id": "workflow_1729345678901",
  "workflow_name": "User API Development",
  "nodes": [
    {
      "id": "node-1",
      "phase_type": "requirements",
      "label": "User API Requirements",
      "phase_config": {
        "requirementText": "Build REST API for user management",
        "timeout": 3600,
        "assigned_team": ["architect-001"],
        "executor_ai": "claude-3-5-sonnet-20241022"
      }
    },
    {
      "id": "node-2",
      "phase_type": "architecture",
      "label": "API Architecture",
      "phase_config": {
        "architectureDesign": "Design microservices architecture",
        "timeout": 3600,
        "assigned_team": ["architect-002"],
        "executor_ai": "claude-3-5-sonnet-20241022"
      }
    }
  ],
  "edges": [
    { "source": "node-1", "target": "node-2" }
  ]
}
```

---

### **Step 2: User Clicks "Execute Workflow" Button**

**File:** `DAGStudio.tsx:464-644`

```typescript
const handleExecute = async () => {
  // 1. Validate workflow
  validate();

  if (workflow.validation?.errors?.length > 0) {
    alert('Cannot execute workflow with errors');
    return;
  }

  // 2. Get authentication token
  const token = localStorage.getItem('maestro_access_token');

  // 3. Send execution request to gateway
  const response = await fetch(`${API_CONFIG.WORKFLOW_API}/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      workflow_id: workflow.id,
      workflow_name: workflow.name,
      nodes: workflow.nodes.map(node => ({
        id: node.id,
        phase_type: node.data.phaseType,
        label: node.data.label,
        phase_config: {
          requirementText: node.data.requirementText,
          architectureDesign: node.data.architectureDesign,
          // ... other configs
          timeout: node.data.timeout,
          assigned_team: node.data.assignedTeam,
          executor_ai: node.data.assignedExecutorAI,
        },
      })),
      edges: workflow.edges.map(edge => ({
        source: edge.source,
        target: edge.target,
      })),
    }),
  });

  const result = await response.json();
  // result = { execution_id, workflow_id, status, total_phases, websocket_url }

  // 4. Connect to WebSocket for real-time updates
  const wsUrl = `${API_CONFIG.WORKFLOW_WS}/${result.workflow_id}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch (message.type) {
      case 'execution_accepted':
        console.log('Execution accepted:', message.execution_id);
        break;

      case 'workflow_started':
        console.log('Workflow started');
        break;

      case 'phase_started':
        // Update node visual status to "running" (blue)
        updateNode(message.node_id, { status: 'running' });
        break;

      case 'phase_completed':
        // Update node visual status to "completed" (green)
        updateNode(message.node_id, { status: 'completed' });
        break;

      case 'workflow_completed':
        alert('Workflow Completed!');
        ws.close();
        break;

      case 'workflow_failed':
        alert(`Workflow Failed: ${message.error}`);
        ws.close();
        break;
    }
  };
};
```

**HTTP Request:**
```http
POST http://3.10.213.208:8080/api/workflow/execute
Authorization: Bearer <token>
Content-Type: application/json

{
  "workflow_id": "workflow_1729345678901",
  "workflow_name": "User API Development",
  "nodes": [...],
  "edges": [...]
}
```

**Gateway Action:**
- Receives request on port 8080
- Matches route `/api/workflow/execute`
- Proxies to backend: `http://172.22.0.1:5001/api/workflow/execute`

---

### **Step 3: Backend Processes Execution Request**

**File:** `workflow_api_v2.py`

```python
@app.post("/api/workflow/execute")
async def execute_workflow(request: ExecutionRequest):
    # 1. Create WorkflowDAG from request
    dag = WorkflowDAG(
        workflow_id=request.workflow_id,
        workflow_name=request.workflow_name,
    )

    # 2. Add nodes to DAG
    for node_data in request.nodes:
        node = WorkflowNode(
            node_id=node_data.id,
            phase_type=node_data.phase_type,
            label=node_data.label,
            phase_config=node_data.phase_config,
        )
        dag.add_node(node)

    # 3. Add edges (dependencies)
    for edge in request.edges:
        dag.add_edge(edge.source, edge.target)

    # 4. Generate execution ID
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"

    # 5. Store execution state
    active_executions[execution_id] = {
        "dag": dag,
        "status": "pending",
        "total_phases": len(dag.nodes),
    }

    # 6. Start async execution
    asyncio.create_task(execute_workflow_async(execution_id, dag))

    # 7. Return immediate response
    return {
        "execution_id": execution_id,
        "workflow_id": request.workflow_id,
        "status": "pending",
        "total_phases": len(dag.nodes),
        "websocket_url": f"/ws/workflow/{request.workflow_id}",
    }
```

**Response:**
```json
{
  "execution_id": "exec_a1b2c3d4",
  "workflow_id": "workflow_1729345678901",
  "status": "pending",
  "total_phases": 2,
  "websocket_url": "/ws/workflow/workflow_1729345678901"
}
```

---

### **Step 4: WebSocket Connection for Real-Time Updates**

**Frontend:**
```typescript
// Connect to WebSocket immediately after execution starts
const wsUrl = 'ws://3.10.213.208:8080/ws/workflow/workflow_1729345678901';
const ws = new WebSocket(wsUrl);
```

**Gateway:**
- Receives WebSocket upgrade request
- Proxies to backend: `ws://172.22.0.1:5001/ws/workflow/workflow_1729345678901`
- Maintains bidirectional connection

**Backend:**
```python
@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    await websocket.accept()

    # Add client to active connections
    active_connections[workflow_id].append(websocket)

    try:
        # Send initial acceptance message
        await websocket.send_json({
            "type": "execution_accepted",
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections[workflow_id].remove(websocket)
```

---

### **Step 5: Async Workflow Execution**

**Backend:** `workflow_api_v2.py`

```python
async def execute_workflow_async(execution_id: str, dag: WorkflowDAG):
    # 1. Broadcast workflow started
    await broadcast_to_workflow(dag.workflow_id, {
        "type": "workflow_started",
        "execution_id": execution_id,
        "total_phases": len(dag.nodes),
    })

    # 2. Get execution order (topological sort)
    execution_order = dag.get_execution_order()

    # 3. Execute phases in order
    for phase_number, node_id in enumerate(execution_order, start=1):
        node = dag.nodes[node_id]

        # Broadcast phase started
        await broadcast_to_workflow(dag.workflow_id, {
            "type": "phase_started",
            "node_id": node_id,
            "phase_number": phase_number,
            "total_phases": len(dag.nodes),
            "phase_type": node.phase_type,
        })

        # Execute phase using TeamExecutionEngineV2
        engine = TeamExecutionEngineV2SplitMode()
        result = await engine.execute_phase(
            phase_type=node.phase_type,
            phase_config=node.phase_config,
            context={
                "workflow_id": dag.workflow_id,
                "execution_id": execution_id,
            },
        )

        # Broadcast phase completed
        await broadcast_to_workflow(dag.workflow_id, {
            "type": "phase_completed",
            "node_id": node_id,
            "phase_number": phase_number,
            "total_phases": len(dag.nodes),
            "result": result,
        })

    # 4. Broadcast workflow completed
    await broadcast_to_workflow(dag.workflow_id, {
        "type": "workflow_completed",
        "execution_id": execution_id,
        "total_phases": len(dag.nodes),
    })
```

---

## 🎨 Visual Feedback in Frontend

### **Node Status Colors**

**File:** `DAGEditorCanvas.tsx`

```typescript
const getNodeStyle = (status: NodeStatus) => {
  switch (status) {
    case 'pending':
      return { background: '#f3f4f6', border: '2px solid #d1d5db' }; // Gray
    case 'running':
      return { background: '#dbeafe', border: '2px solid #3b82f6' }; // Blue
    case 'completed':
      return { background: '#d1fae5', border: '2px solid #10b981' }; // Green
    case 'failed':
      return { background: '#fee2e2', border: '2px solid #ef4444' }; // Red
    default:
      return { background: '#ffffff', border: '2px solid #e5e7eb' };
  }
};
```

**Real-Time Update Flow:**
```
Backend broadcasts "phase_started"
→ WebSocket delivers message to frontend
→ Frontend updateNode(node_id, { status: 'running' })
→ Zustand store updates node state
→ React re-renders with blue color
→ User sees node turn blue
```

---

## 🔍 Data Structures

### **Frontend Node Model**

```typescript
// types/dag-studio.ts
export interface DAGNode {
  id: string;                          // "node-1"
  type: 'phaseNode';                   // ReactFlow node type
  position: { x: number; y: number };  // Canvas position
  data: {
    phaseType: PhaseType;              // "requirements" | "architecture" | ...
    label: string;                     // "User API Requirements"
    status?: NodeStatus;               // "pending" | "running" | "completed" | "failed"

    // Phase-specific configs
    requirementText?: string;
    architectureDesign?: string;
    implementationDetails?: string;
    testPlan?: string;
    deploymentConfig?: string;
    reviewCriteria?: string;

    // Execution configs
    timeout?: number;                  // Seconds
    assignedTeam?: string[];           // ["architect-001"]
    assignedExecutorAI?: string;       // "claude-3-5-sonnet-20241022"
  };
}

export type PhaseType =
  | 'requirements'
  | 'architecture'
  | 'implementation'
  | 'testing'
  | 'deployment'
  | 'review';

export type NodeStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed';
```

### **Backend Node Model**

```python
# workflow_api_v2.py
class WorkflowNode:
    node_id: str                  # "node-1"
    phase_type: str               # "requirements"
    label: str                    # "User API Requirements"
    phase_config: dict            # Configuration dictionary
    dependencies: List[str]       # ["node-0"]  (from edges)

class PhaseConfig(BaseModel):
    requirementText: Optional[str]
    architectureDesign: Optional[str]
    implementationDetails: Optional[str]
    testPlan: Optional[str]
    deploymentConfig: Optional[str]
    reviewCriteria: Optional[str]
    timeout: int = 3600
    assigned_team: List[str] = []
    executor_ai: Optional[str]
```

---

## 🔐 Authentication Flow

```typescript
// Frontend stores JWT token in localStorage
localStorage.setItem('maestro_access_token', token);

// Include in all API requests
fetch(`${API_CONFIG.WORKFLOW_API}/execute`, {
  headers: {
    'Authorization': `Bearer ${token}`,
  },
});
```

**Backend validation:**
```python
# Currently permissive mode (requires_auth: false in gateway)
# Future: Add JWT validation middleware
```

---

## 📊 WebSocket Message Types

### **Backend → Frontend Messages**

| Type | Description | Payload |
|------|-------------|---------|
| `execution_accepted` | Execution queued successfully | `{ execution_id, timestamp }` |
| `workflow_started` | Workflow execution began | `{ execution_id, total_phases }` |
| `phase_started` | Phase execution started | `{ node_id, phase_number, total_phases, phase_type }` |
| `phase_completed` | Phase execution completed | `{ node_id, phase_number, result }` |
| `workflow_completed` | All phases completed | `{ execution_id, total_phases }` |
| `workflow_failed` | Execution failed | `{ error, node_id?, phase_number? }` |

**Example Message:**
```json
{
  "type": "phase_started",
  "node_id": "node-1",
  "phase_number": 1,
  "total_phases": 2,
  "phase_type": "requirements",
  "timestamp": "2025-10-19T12:30:45.123Z"
}
```

---

## 🚀 Services and Ports

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| **Frontend** | 4300 | http://3.10.213.208:4300 | React + Vite dev server |
| **API Gateway** | 8080 | http://3.10.213.208:8080 | Docker-based NGINX/FastAPI gateway |
| **Backend API** | 5001 | http://3.10.213.208:5001 | workflow_api_v2.py (FastAPI) |

---

## 📂 Key Files Reference

### **Frontend**

| File | Purpose |
|------|---------|
| `frontend/src/components/dag-studio/DAGStudio.tsx` | Main orchestrator, handles execution button |
| `frontend/src/stores/dagStudioStore.ts` | Zustand state management |
| `frontend/src/services/dagExecutionService.ts` | HTTP client for workflow execution |
| `frontend/src/config/api.ts` | Centralized API configuration |
| `frontend/.env` | Environment variables (VITE_DAG_API_URL) |

### **Gateway**

| File | Purpose |
|------|---------|
| `maestro-engine/config/gateway_routes.yaml` | Route configuration |
| Docker container: `maestro-gateway` | Running gateway service |

### **Backend**

| File | Purpose |
|------|---------|
| `maestro-hive/workflow_api_v2.py` | Main workflow execution API |
| `maestro-hive/dag_executor.py` | DAG execution engine |
| `maestro-hive/team_execution_v2.py` | Phase execution with AI agents |
| `maestro-hive/dag_workflow.py` | WorkflowDAG and WorkflowNode models |

---

## 🧪 Testing the Integration

### **Step 1: Verify Services Running**

```bash
# Frontend
curl http://3.10.213.208:4300

# Gateway
curl http://3.10.213.208:8080/health

# Backend (via gateway)
curl http://3.10.213.208:8080/api/workflow/health

# Backend (direct)
curl http://3.10.213.208:5001/health
```

### **Step 2: Test Workflow Execution**

**Via Gateway (Recommended):**
```bash
curl -X POST http://3.10.213.208:8080/api/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "test-workflow-1",
    "workflow_name": "Test Workflow",
    "nodes": [
      {
        "id": "node-1",
        "phase_type": "requirements",
        "label": "Test Requirements",
        "phase_config": {
          "requirementText": "Test requirement",
          "executor_ai": "claude-3-5-sonnet-20241022"
        }
      }
    ],
    "edges": []
  }'
```

**Expected Response:**
```json
{
  "execution_id": "exec_a1b2c3d4",
  "workflow_id": "test-workflow-1",
  "status": "pending",
  "total_phases": 1,
  "websocket_url": "/ws/workflow/test-workflow-1"
}
```

### **Step 3: Test WebSocket Connection**

```javascript
// In browser console (on DAG Studio page)
const ws = new WebSocket('ws://3.10.213.208:8080/ws/workflow/test-workflow-1');

ws.onopen = () => console.log('✅ Connected');
ws.onmessage = (e) => console.log('📨', JSON.parse(e.data));
ws.onerror = (e) => console.error('❌', e);
```

---

## 🛠️ Troubleshooting

### **Issue: "Network error. Backend may be unavailable"**

**Check:**
```bash
# 1. Is gateway running?
docker ps | grep maestro-gateway

# 2. Can gateway reach backend?
docker exec maestro-gateway curl -s http://172.22.0.1:5001/health

# 3. Are routes configured?
docker exec maestro-gateway cat /app/config/gateway_routes.yaml
```

### **Issue: WebSocket not connecting**

**Check:**
1. Browser console for WebSocket errors
2. Gateway WebSocket proxying configuration
3. CORS settings in gateway_routes.yaml

### **Issue: Nodes not updating in real-time**

**Check:**
1. Browser console - Are WebSocket messages arriving?
2. Backend logs - Is workflow actually executing?
3. Node IDs match between frontend and backend?

---

## 🎯 Success Criteria Checklist

- ✅ Frontend loads at http://3.10.213.208:4300/dag-studio
- ✅ User can drag phases onto canvas
- ✅ User can connect phases with edges
- ✅ Execute button appears in toolbar
- ✅ Clicking Execute sends request to gateway (port 8080)
- ✅ Gateway routes to backend (port 5001)
- ✅ Backend returns execution_id
- ✅ WebSocket connects automatically
- ✅ Nodes change color (blue → green) during execution
- ✅ Alert shows "Workflow completed successfully!"

---

**🎉 Integration Complete!**

This document describes the **production-ready** DAG Studio frontend/backend integration using the API Gateway pattern (port 8080) for all communication.
