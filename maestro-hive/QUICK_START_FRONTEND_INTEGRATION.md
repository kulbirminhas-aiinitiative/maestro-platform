# Quick Start: DAG Frontend Integration

## 🚀 Get Started in 15 Minutes

### Prerequisites
- Dog marketplace test running (generates real workflow data)
- Python 3.8+ with DAG modules
- Node.js 22+ (already installed)
- React frontend (maestro-frontend-new)

---

## Step 1: Start Backend API (5 min)

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Install FastAPI dependencies
pip install fastapi uvicorn websockets

# Start API server
python3 dag_api_server.py

# ✅ API running at http://localhost:8000
# ✅ Docs at http://localhost:8000/docs
# ✅ WebSocket at ws://localhost:8000/ws/workflow/{id}
```

**Test API:**
```bash
# List workflows
curl http://localhost:8000/api/workflows

# Get health
curl http://localhost:8000/health

# Open API docs in browser
open http://localhost:8000/docs
```

---

## Step 2: Create Frontend Component (5 min)

The frontend already has all necessary dependencies:
- ✅ ReactFlow (DAG visualization)
- ✅ Socket.IO (real-time updates)
- ✅ Zustand (state management)
- ✅ Axios (HTTP client)

**Copy provided components:**
```bash
cd /home/ec2-user/projects/maestro-frontend-new

# Create directories
mkdir -p src/components/workflow-canvas
mkdir -p src/stores
mkdir -p src/pages

# Copy example components from integration plan
# (See DAG_FRONTEND_INTEGRATION_PLAN.md)
```

---

## Step 3: Test Integration (5 min)

**Terminal 1: Backend**
```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive
python3 dag_api_server.py
```

**Terminal 2: Frontend**
```bash
cd /home/ec2-user/projects/maestro-frontend-new
npm run dev
# Frontend at http://localhost:4200
```

**Terminal 3: Test**
```bash
# Test API
curl http://localhost:8000/api/workflows

# Test WebSocket (using wscat)
npm install -g wscat
wscat -c ws://localhost:8000/ws/workflow/sdlc_parallel
```

---

## Architecture

```
┌────────────────────────────────────┐
│   React Frontend (Port 4200)       │
│   - ReactFlow Canvas               │
│   - Real-time Updates              │
│   - Workflow Controls              │
└────────┬────────────┬──────────────┘
         │            │
         │ REST       │ WebSocket
         │            │
┌────────▼────────────▼──────────────┐
│   FastAPI Backend (Port 8000)      │
│   - Workflow API                   │
│   - WebSocket Server               │
│   - Event Broadcasting             │
└────────┬───────────────────────────┘
         │
         │ Calls
         │
┌────────▼───────────────────────────┐
│   Python DAG Engine                │
│   - DAGExecutor                    │
│   - WorkflowDAG                    │
│   - Context Store                  │
└────────────────────────────────────┘
```

---

## Key Features

### Backend API (dag_api_server.py)

✅ **REST Endpoints:**
- `GET /api/workflows` - List all workflows
- `POST /api/workflows` - Create new workflow
- `GET /api/workflows/{id}` - Get workflow details
- `POST /api/workflows/{id}/execute` - Start execution
- `GET /api/executions/{id}` - Get execution status

✅ **WebSocket:**
- Real-time workflow events
- Node status updates
- Progress notifications
- Completion alerts

✅ **Features:**
- CORS enabled for frontend
- Event broadcasting
- In-memory storage (dev mode)
- OpenAPI documentation

### Frontend Components

✅ **DAGWorkflowCanvas**
- ReactFlow-based visualization
- Interactive node graph
- Pan/zoom controls
- Minimap

✅ **PhaseNode**
- Custom node component
- Status indicators (pending/running/completed/failed)
- Progress bars
- Quality metrics
- Artifact counts

✅ **WorkflowStore**
- Zustand state management
- WebSocket integration
- Real-time updates
- HTTP API calls

---

## Example: Watch Dog Marketplace Test

The dog marketplace test is running and generating real workflow events!

**Monitor via API:**
```bash
# Watch executions (refresh every 2 seconds)
watch -n 2 'curl -s http://localhost:8000/api/executions/exec_sdlc_parallel_123 | jq'

# Stream WebSocket events
wscat -c ws://localhost:8000/ws/workflow/dog_marketplace

# Check active workflows
curl http://localhost:8000/api/workflows | jq
```

**Expected Events:**
```json
{
  "type": "node_started",
  "node_id": "phase_requirements",
  "timestamp": "2025-10-11T12:00:00",
  "workflow_id": "dog_marketplace"
}

{
  "type": "node_completed",
  "node_id": "phase_requirements",
  "outputs": { "artifacts": 6, "quality": 0.43 },
  "timestamp": "2025-10-11T12:09:00"
}
```

---

## Visualization

### ReactFlow Layout

**Linear Workflow:**
```
Requirements → Design → Implementation → Testing → Deployment
```

**Parallel Workflow:**
```
Requirements → Design → ┌─ Backend Dev ─┐
                        │                ├→ Testing → Deployment
                        └─ Frontend Dev ┘
```

### Node States

🔵 **Pending** - Not started
🟡 **Running** - In progress (with spinner)
🟢 **Completed** - Success (with checkmark)
🔴 **Failed** - Error (with X)

### Real-time Updates

- Node changes color as status updates
- Progress bar shows completion percentage
- Metrics update live (quality, duration, artifacts)
- Events stream in sidebar

---

## Production Considerations

### Backend Scaling

**Current (Development):**
- In-memory storage
- Single server
- No authentication

**Production:**
- PostgreSQL for workflows
- Redis for WebSocket pub/sub
- Authentication (JWT/OAuth)
- Rate limiting
- Load balancing

### Frontend Optimization

**Current:**
- Direct WebSocket connection
- No caching

**Production:**
- React Query for API caching
- WebSocket reconnection logic
- Optimistic updates
- Error boundaries
- Progressive loading

---

## Testing

### Backend Tests

```bash
# Test API endpoints
pytest api/tests/test_workflow_api.py

# Load test WebSocket
python3 scripts/load_test_websocket.py
```

### Frontend Tests

```bash
# Component tests
npm run test

# E2E tests
npm run test:e2e

# Integration tests
npm run test:integration
```

---

## Next Steps

### Immediate (Today)

1. ✅ Start backend API server
2. ✅ Test endpoints with curl
3. ✅ Copy frontend components
4. ✅ Test with dog marketplace workflow

### Short-term (This Week)

1. Add node click handlers (show details)
2. Implement pause/resume controls
3. Add event timeline sidebar
4. Style improvements

### Medium-term (Next Week)

1. Workflow builder (drag-and-drop)
2. Template library
3. Analytics dashboard
4. Multi-user support

---

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Find process
lsof -ti:8000

# Kill it
kill $(lsof -ti:8000)

# Or use different port
uvicorn dag_api_server:app --port 8001
```

**CORS errors:**
```python
# Update allowed origins in dag_api_server.py
allow_origins=[
    "http://localhost:4200",
    "http://your-frontend-url:port"
]
```

### Frontend Issues

**WebSocket connection failed:**
```typescript
// Check WebSocket URL in workflowStore.ts
const socket = io('http://localhost:8000', {
  path: '/ws/workflow/${workflowId}',
  transports: ['websocket']  // Force WebSocket
});
```

**ReactFlow not displaying:**
```bash
# Ensure ReactFlow CSS is imported
import 'reactflow/dist/style.css';
```

---

## Resources

**Documentation:**
- Full Integration Plan: `DAG_FRONTEND_INTEGRATION_PLAN.md`
- API Server Code: `dag_api_server.py`
- Backend API Docs: http://localhost:8000/docs
- ReactFlow Docs: https://reactflow.dev/
- Socket.IO Docs: https://socket.io/docs/v4/

**Example Code:**
- DAG Canvas: See integration plan
- Phase Node: See integration plan
- Workflow Store: See integration plan

---

**Ready to start! Follow the 3 steps above and you'll have a working DAG visualization in 15 minutes.** 🚀

**Questions?** Check the full integration plan or API docs.
