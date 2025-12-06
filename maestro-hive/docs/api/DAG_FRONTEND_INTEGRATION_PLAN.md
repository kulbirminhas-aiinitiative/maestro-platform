# DAG Workflow Frontend Integration Plan

## Executive Summary

Integrate the Python-based DAG workflow engine with the React frontend to provide real-time workflow visualization, monitoring, and control.

**Current Stack Compatibility:** ✅ Excellent
- Frontend: React 18.2 + TypeScript
- Graph Visualization: **ReactFlow 11.10.1** (Perfect for DAG!)
- Real-time: **Socket.IO 4.7.2**
- State: **Zustand 4.4.7**
- HTTP: Axios 1.12.2

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                            │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐  │
│  │ DAG Canvas   │    │ Workflow     │   │ Real-time    │  │
│  │ (ReactFlow)  │◄──►│ Store        │◄──│ Events       │  │
│  │              │    │ (Zustand)    │   │ (Socket.IO)  │  │
│  └──────────────┘    └──────────────┘   └──────────────┘  │
│         │                    │                   │          │
└─────────┼────────────────────┼───────────────────┼──────────┘
          │                    │                   │
          │ REST API           │ REST API          │ WebSocket
          │                    │                   │
┌─────────▼────────────────────▼───────────────────▼──────────┐
│               FastAPI Backend (Python)                       │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐  │
│  │ Workflow API │    │ DAG Executor │   │ WebSocket    │  │
│  │ Endpoints    │◄──►│ Engine       │──►│ Manager      │  │
│  └──────────────┘    └──────────────┘   └──────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Recommendation

### ✅ Use Existing Stack (Optimal)

**Frontend:**
1. **ReactFlow** - Already installed! Perfect for DAG visualization
   - Node-based graph editor
   - Built-in pan/zoom
   - Customizable nodes and edges
   - Minimap support

2. **Socket.IO Client** - Already installed! For real-time updates
   - Event-driven architecture
   - Automatic reconnection
   - Room-based broadcasting

3. **Zustand** - Already installed! Lightweight state management
   - Simple API
   - No boilerplate
   - TypeScript support

4. **Axios** - Already installed! HTTP client for REST API

**Backend (New Components):**
1. **FastAPI** - Python web framework for REST API
   - Async support (matches DAG engine)
   - Auto-generated OpenAPI docs
   - WebSocket support

2. **Socket.IO (Python)** - For WebSocket server
   - Compatible with Socket.IO client
   - Room support for multi-user

3. **Pydantic** - Data validation and serialization
   - Type hints
   - JSON schema generation

### Additional Libraries (Optional)

**Frontend Enhancements:**
- **React Query** - Already installed! Cache workflow data
- **D3.js** - For custom visualizations (types already installed)
- **Mermaid** - Already installed! For static diagrams

---

## Implementation Plan

### Phase 1: Backend API Layer (2-3 days)

Create FastAPI service to expose DAG engine functionality.

**Components:**
1. **Workflow API** - CRUD operations for workflows
2. **Execution API** - Start/stop/pause workflows
3. **WebSocket Server** - Real-time event broadcasting
4. **Event System** - Convert DAG events to WebSocket messages

**Endpoints:**
```
GET    /api/workflows                    # List all workflows
POST   /api/workflows                    # Create workflow
GET    /api/workflows/{id}               # Get workflow details
DELETE /api/workflows/{id}               # Delete workflow

POST   /api/workflows/{id}/execute       # Start execution
POST   /api/workflows/{id}/pause         # Pause execution
POST   /api/workflows/{id}/resume        # Resume execution
POST   /api/workflows/{id}/cancel        # Cancel execution

GET    /api/executions/{exec_id}         # Get execution status
GET    /api/executions/{exec_id}/nodes   # Get node states
GET    /api/executions/{exec_id}/events  # Get event history

WS     /ws/workflow/{id}                 # WebSocket for real-time updates
```

### Phase 2: Frontend Components (3-4 days)

**Core Components:**

1. **`DAGWorkflowCanvas`** - Main visualization
   ```typescript
   import ReactFlow, { Node, Edge } from 'reactflow';

   interface WorkflowNode extends Node {
     data: {
       phase: string;
       status: 'pending' | 'running' | 'completed' | 'failed';
       quality: number;
       artifacts: string[];
     };
   }
   ```

2. **`WorkflowStore`** - Zustand store
   ```typescript
   interface WorkflowState {
     workflows: Workflow[];
     currentExecution: Execution | null;
     nodes: WorkflowNode[];
     edges: Edge[];
     events: ExecutionEvent[];
   }
   ```

3. **`useWorkflowWebSocket`** - Socket.IO hook
   ```typescript
   const useWorkflowWebSocket = (workflowId: string) => {
     // Connect to WebSocket
     // Listen for events
     // Update store
   };
   ```

4. **`WorkflowMonitor`** - Dashboard component
   - Live execution status
   - Phase progress bars
   - Event timeline
   - Performance metrics

### Phase 3: Real-time Integration (2 days)

**WebSocket Events:**
```typescript
// Events from backend to frontend
{
  'workflow:started': { execution_id, workflow_id, timestamp }
  'node:started': { node_id, phase, timestamp }
  'node:progress': { node_id, progress, message }
  'node:completed': { node_id, outputs, artifacts, duration }
  'node:failed': { node_id, error, retry_count }
  'workflow:completed': { execution_id, summary, metrics }
}
```

### Phase 4: Advanced Features (3-4 days)

1. **Interactive Controls**
   - Pause/Resume buttons
   - Node-level retry
   - Parameter adjustment

2. **Analytics Dashboard**
   - Execution history
   - Performance trends
   - Bottleneck analysis

3. **Workflow Builder**
   - Drag-and-drop workflow creation
   - Template library
   - Validation

---

## Detailed Implementation

### 1. Backend: FastAPI Service

**File:** `maestro-hive/api/workflow_api.py`

```python
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio

from dag_executor import DAGExecutor, WorkflowContextStore
from dag_workflow import WorkflowDAG, WorkflowContext
from dag_compatibility import generate_parallel_workflow, generate_linear_workflow

app = FastAPI(title="Maestro DAG API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (use Redis/PostgreSQL in production)
active_executions: Dict[str, DAGExecutor] = {}
context_store = WorkflowContextStore()

# WebSocket connections
websocket_connections: Dict[str, List[WebSocket]] = {}


# ============================================================================
# Models
# ============================================================================

class WorkflowCreate(BaseModel):
    name: str
    type: str  # 'linear' or 'parallel'
    requirement: str


class WorkflowExecute(BaseModel):
    initial_context: Optional[Dict] = None


class NodeState(BaseModel):
    node_id: str
    status: str
    attempt_count: int
    started_at: Optional[str]
    completed_at: Optional[str]
    outputs: Optional[Dict] = None
    error: Optional[str] = None


class ExecutionStatus(BaseModel):
    execution_id: str
    workflow_id: str
    status: str
    completed_nodes: int
    total_nodes: int
    node_states: List[NodeState]
    current_phase: Optional[str] = None


# ============================================================================
# Workflow Endpoints
# ============================================================================

@app.post("/api/workflows")
async def create_workflow(workflow: WorkflowCreate):
    """Create a new workflow definition"""
    from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

    # Create team engine
    engine = TeamExecutionEngineV2SplitMode()

    # Generate workflow DAG
    if workflow.type == "parallel":
        dag = generate_parallel_workflow(
            workflow_name=workflow.name,
            team_engine=engine
        )
    else:
        dag = generate_linear_workflow(
            workflow_name=workflow.name,
            team_engine=engine
        )

    return {
        "workflow_id": dag.workflow_id,
        "name": workflow.name,
        "type": workflow.type,
        "nodes": len(dag.nodes),
        "created_at": datetime.now().isoformat()
    }


@app.get("/api/workflows")
async def list_workflows():
    """List all workflow definitions"""
    # In production, fetch from database
    return {
        "workflows": [
            {
                "workflow_id": "sdlc_parallel",
                "name": "SDLC Parallel Workflow",
                "type": "parallel",
                "nodes": 6
            },
            {
                "workflow_id": "sdlc_linear",
                "name": "SDLC Linear Workflow",
                "type": "linear",
                "nodes": 6
            }
        ]
    }


# ============================================================================
# Execution Endpoints
# ============================================================================

@app.post("/api/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, params: WorkflowExecute):
    """Start workflow execution"""
    from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

    # Create engine and workflow
    engine = TeamExecutionEngineV2SplitMode()

    if "parallel" in workflow_id:
        dag = generate_parallel_workflow(team_engine=engine)
    else:
        dag = generate_linear_workflow(team_engine=engine)

    # Create executor with event handler
    async def event_handler(event):
        # Broadcast to WebSocket clients
        await broadcast_event(workflow_id, event.to_dict())

    executor = DAGExecutor(
        workflow=dag,
        context_store=context_store,
        event_handler=event_handler
    )

    # Store executor
    execution_id = f"exec_{workflow_id}_{datetime.now().timestamp()}"
    active_executions[execution_id] = executor

    # Execute in background
    asyncio.create_task(
        executor.execute(initial_context=params.initial_context or {})
    )

    return {
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "status": "running",
        "started_at": datetime.now().isoformat()
    }


@app.get("/api/executions/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get execution status"""
    if execution_id not in active_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    executor = active_executions[execution_id]
    context = executor.context

    if not context:
        return {"status": "initializing"}

    # Build node states
    node_states = []
    for node_id, state in context.node_states.items():
        node_states.append(NodeState(
            node_id=node_id,
            status=state.status.value,
            attempt_count=state.attempt_count,
            started_at=state.started_at.isoformat() if state.started_at else None,
            completed_at=state.completed_at.isoformat() if state.completed_at else None,
            outputs=context.node_outputs.get(node_id),
            error=state.error
        ))

    return ExecutionStatus(
        execution_id=execution_id,
        workflow_id=context.workflow_id,
        status="running",  # Determine from context
        completed_nodes=len(context.get_completed_nodes()),
        total_nodes=len(context.node_states),
        node_states=node_states,
        current_phase=None  # Extract from context
    )


@app.post("/api/executions/{execution_id}/pause")
async def pause_execution(execution_id: str):
    """Pause workflow execution"""
    if execution_id not in active_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Implement pause logic
    return {"status": "paused"}


@app.post("/api/executions/{execution_id}/resume")
async def resume_execution(execution_id: str):
    """Resume workflow execution"""
    # Load context and resume
    return {"status": "resumed"}


# ============================================================================
# WebSocket
# ============================================================================

@app.websocket("/ws/workflow/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()

    # Add to connections
    if workflow_id not in websocket_connections:
        websocket_connections[workflow_id] = []
    websocket_connections[workflow_id].append(websocket)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle client messages if needed
    except:
        # Remove connection
        websocket_connections[workflow_id].remove(websocket)


async def broadcast_event(workflow_id: str, event: Dict):
    """Broadcast event to all WebSocket clients"""
    if workflow_id not in websocket_connections:
        return

    for ws in websocket_connections[workflow_id]:
        try:
            await ws.send_json(event)
        except:
            pass


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "maestro-dag-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Run:**
```bash
pip install fastapi uvicorn websockets
python3 workflow_api.py
```

---

### 2. Frontend: DAG Canvas Component

**File:** `maestro-frontend-new/src/components/workflow-canvas/DAGWorkflowCanvas.tsx`

```typescript
import React, { useCallback, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  NodeProps,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useWorkflowStore } from '../../stores/workflowStore';
import { PhaseNode } from './PhaseNode';
import { WorkflowControls } from './WorkflowControls';

const nodeTypes = {
  phase: PhaseNode,
};

interface DAGWorkflowCanvasProps {
  workflowId: string;
  executionId?: string;
}

export const DAGWorkflowCanvas: React.FC<DAGWorkflowCanvasProps> = ({
  workflowId,
  executionId,
}) => {
  const { nodes: storeNodes, edges: storeEdges, fetchWorkflow } = useWorkflowStore();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Fetch workflow data
  useEffect(() => {
    fetchWorkflow(workflowId);
  }, [workflowId, fetchWorkflow]);

  // Update local state when store changes
  useEffect(() => {
    setNodes(storeNodes);
    setEdges(storeEdges);
  }, [storeNodes, storeEdges, setNodes, setEdges]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    console.log('Node clicked:', node);
    // Show node details in sidebar
  }, []);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>

      {executionId && (
        <WorkflowControls executionId={executionId} />
      )}
    </div>
  );
};
```

**File:** `maestro-frontend-new/src/components/workflow-canvas/PhaseNode.tsx`

```typescript
import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { CheckCircle2, Circle, AlertCircle, Loader2 } from 'lucide-react';

export interface PhaseNodeData {
  phase: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  quality?: number;
  duration?: number;
  artifacts?: number;
  progress?: number;
}

const statusConfig = {
  pending: {
    icon: Circle,
    color: 'text-gray-400',
    bg: 'bg-gray-50',
    border: 'border-gray-300',
  },
  running: {
    icon: Loader2,
    color: 'text-blue-500',
    bg: 'bg-blue-50',
    border: 'border-blue-500',
    animate: 'animate-spin',
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-green-500',
    bg: 'bg-green-50',
    border: 'border-green-500',
  },
  failed: {
    icon: AlertCircle,
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-500',
  },
};

export const PhaseNode: React.FC<NodeProps<PhaseNodeData>> = memo(({ data }) => {
  const config = statusConfig[data.status];
  const Icon = config.icon;

  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 shadow-lg min-w-[200px]
        ${config.bg} ${config.border}
        transition-all duration-200 hover:shadow-xl
      `}
    >
      <Handle type="target" position={Position.Top} />

      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-5 h-5 ${config.color} ${config.animate || ''}`} />
        <span className="font-semibold text-gray-900">
          {data.phase.replace('_', ' ').toUpperCase()}
        </span>
      </div>

      {data.status === 'running' && data.progress !== undefined && (
        <div className="mb-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${data.progress}%` }}
            />
          </div>
          <span className="text-xs text-gray-600">{data.progress}%</span>
        </div>
      )}

      <div className="text-xs text-gray-600 space-y-1">
        {data.quality !== undefined && (
          <div>Quality: {(data.quality * 100).toFixed(0)}%</div>
        )}
        {data.duration !== undefined && (
          <div>Duration: {data.duration.toFixed(1)}s</div>
        )}
        {data.artifacts !== undefined && (
          <div>Artifacts: {data.artifacts}</div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
});

PhaseNode.displayName = 'PhaseNode';
```

---

### 3. Frontend: Workflow Store

**File:** `maestro-frontend-new/src/stores/workflowStore.ts`

```typescript
import { create } from 'zustand';
import { Node, Edge } from 'reactflow';
import axios from 'axios';
import { io, Socket } from 'socket.io-client';

const API_BASE = 'http://localhost:8000/api';

interface WorkflowState {
  // Data
  workflows: any[];
  currentWorkflow: any | null;
  currentExecution: any | null;
  nodes: Node[];
  edges: Edge[];
  events: any[];

  // WebSocket
  socket: Socket | null;

  // Actions
  fetchWorkflows: () => Promise<void>;
  fetchWorkflow: (id: string) => Promise<void>;
  executeWorkflow: (id: string, context?: any) => Promise<string>;
  pauseExecution: (execId: string) => Promise<void>;
  resumeExecution: (execId: string) => Promise<void>;
  connectWebSocket: (workflowId: string) => void;
  disconnectWebSocket: () => void;
  updateNodeStatus: (nodeId: string, status: any) => void;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  // Initial state
  workflows: [],
  currentWorkflow: null,
  currentExecution: null,
  nodes: [],
  edges: [],
  events: [],
  socket: null,

  // Fetch all workflows
  fetchWorkflows: async () => {
    const response = await axios.get(`${API_BASE}/workflows`);
    set({ workflows: response.data.workflows });
  },

  // Fetch specific workflow
  fetchWorkflow: async (id: string) => {
    const response = await axios.get(`${API_BASE}/workflows/${id}`);
    set({ currentWorkflow: response.data });

    // Convert to ReactFlow format
    const nodes = convertToReactFlowNodes(response.data);
    const edges = convertToReactFlowEdges(response.data);
    set({ nodes, edges });
  },

  // Execute workflow
  executeWorkflow: async (id: string, context?: any) => {
    const response = await axios.post(`${API_BASE}/workflows/${id}/execute`, {
      initial_context: context,
    });

    set({ currentExecution: response.data });

    // Connect WebSocket for real-time updates
    get().connectWebSocket(id);

    return response.data.execution_id;
  },

  // Pause execution
  pauseExecution: async (execId: string) => {
    await axios.post(`${API_BASE}/executions/${execId}/pause`);
  },

  // Resume execution
  resumeExecution: async (execId: string) => {
    await axios.post(`${API_BASE}/executions/${execId}/resume`);
  },

  // Connect to WebSocket
  connectWebSocket: (workflowId: string) => {
    const socket = io('http://localhost:8000', {
      path: `/ws/workflow/${workflowId}`,
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    socket.on('node:started', (data) => {
      get().updateNodeStatus(data.node_id, { status: 'running', ...data });
    });

    socket.on('node:completed', (data) => {
      get().updateNodeStatus(data.node_id, { status: 'completed', ...data });
    });

    socket.on('node:failed', (data) => {
      get().updateNodeStatus(data.node_id, { status: 'failed', ...data });
    });

    socket.on('workflow:completed', (data) => {
      console.log('Workflow completed:', data);
    });

    set({ socket });
  },

  // Disconnect WebSocket
  disconnectWebSocket: () => {
    const { socket } = get();
    if (socket) {
      socket.disconnect();
      set({ socket: null });
    }
  },

  // Update node status
  updateNodeStatus: (nodeId: string, status: any) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...status } }
          : node
      ),
      events: [...state.events, { nodeId, ...status, timestamp: Date.now() }],
    }));
  },
}));

// Helper functions
function convertToReactFlowNodes(workflow: any): Node[] {
  // Convert workflow definition to ReactFlow nodes
  // Position nodes in a grid or use layout algorithm
  return [];
}

function convertToReactFlowEdges(workflow: any): Edge[] {
  // Convert workflow dependencies to ReactFlow edges
  return [];
}
```

---

### 4. Frontend: Main Dashboard Page

**File:** `maestro-frontend-new/src/pages/WorkflowDashboard.tsx`

```typescript
import React, { useState } from 'react';
import { DAGWorkflowCanvas } from '../components/workflow-canvas/DAGWorkflowCanvas';
import { WorkflowSidebar } from '../components/workflow-canvas/WorkflowSidebar';
import { useWorkflowStore } from '../stores/workflowStore';

export const WorkflowDashboard: React.FC = () => {
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const { executeWorkflow } = useWorkflowStore();

  const handleStartWorkflow = async (workflowId: string, requirement: string) => {
    const execId = await executeWorkflow(workflowId, { requirement });
    setExecutionId(execId);
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <WorkflowSidebar
        onSelectWorkflow={setSelectedWorkflow}
        onStartWorkflow={handleStartWorkflow}
      />

      {/* Main Canvas */}
      <div className="flex-1">
        {selectedWorkflow ? (
          <DAGWorkflowCanvas
            workflowId={selectedWorkflow}
            executionId={executionId || undefined}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Select a workflow to visualize
          </div>
        )}
      </div>
    </div>
  );
};
```

---

## Quick Start Guide

### 1. Start Backend API

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Install dependencies
pip install fastapi uvicorn websockets python-socketio

# Run API server
python3 workflow_api.py

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 2. Update Frontend

```bash
cd /home/ec2-user/projects/maestro-frontend-new

# Dependencies already installed (ReactFlow, Socket.IO, Zustand)

# Create components (copy code above)
mkdir -p src/components/workflow-canvas
mkdir -p src/stores

# Run frontend
npm run dev

# Frontend at http://localhost:4200
```

### 3. Test Integration

```bash
# Terminal 1: Backend
python3 workflow_api.py

# Terminal 2: Frontend
npm run dev

# Terminal 3: Test API
curl http://localhost:8000/api/workflows

# Open browser
open http://localhost:4200/workflow-dashboard
```

---

## Features to Implement

### Phase 1 (MVP) - 1 week
- [ ] Basic REST API for workflows
- [ ] ReactFlow visualization
- [ ] WebSocket real-time updates
- [ ] Start/stop workflow controls

### Phase 2 (Enhanced) - 1 week
- [ ] Workflow builder (drag-and-drop)
- [ ] Node details panel
- [ ] Event timeline
- [ ] Performance metrics

### Phase 3 (Advanced) - 2 weeks
- [ ] Multi-user collaboration
- [ ] Workflow templates
- [ ] Analytics dashboard
- [ ] Export/import workflows

---

## Best Practices

**Frontend:**
1. Use React Query for API caching
2. Implement optimistic updates
3. Handle WebSocket reconnection
4. Lazy load workflow data

**Backend:**
5. Use Redis for WebSocket pub/sub (production)
6. Implement rate limiting
7. Add authentication/authorization
8. Use PostgreSQL for persistence

**Performance:**
9. Paginate large workflow lists
10. Limit WebSocket message frequency
11. Use virtual scrolling for event lists
12. Implement progressive loading

---

## Next Steps

1. **Review this plan** with your team
2. **Start with Phase 1** (Backend API + Basic Canvas)
3. **Test with dog marketplace workflow** (currently running!)
4. **Iterate based on feedback**

---

**Document Version:** 1.0
**Last Updated:** 2025-10-11
**Status:** Ready for Implementation
