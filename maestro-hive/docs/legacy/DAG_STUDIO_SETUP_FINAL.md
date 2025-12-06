# DAG Studio Integration - Final Setup Guide

**Status:** ✅ **READY TO TEST**
**Date:** October 19, 2025

---

## 🎯 What's Working

### **Backend: workflow_api_v2.py** ✅
- **Running on:** `http://3.10.213.208:5001`
- **Process:** PID 160679
- **Endpoints:**
  - ✅ `POST /api/workflow/execute` - Execute DAG workflows
  - ✅ `GET /api/workflow/status/{execution_id}` - Get execution status
  - ✅ `WS /ws/workflow/{workflow_id}` - Real-time updates
  - ✅ `GET /health` - Health check
  - ✅ `GET /docs` - Swagger UI

### **Frontend Configuration** ✅
- **.env file configured:**
  ```bash
  VITE_DAG_API_URL=http://3.10.213.208:5001
  ```
- **Store updated:** Using `VITE_DAG_API_URL` for both HTTP and WebSocket
- **Service updated:** Correct payload format

---

## 🚀 How to Test (3 Steps)

### **Step 1: Restart Frontend**

The `.env` file was updated, so you need to restart the frontend dev server:

```bash
# Stop current frontend (Ctrl+C in terminal)

# Restart it:
cd /home/ec2-user/projects/maestro-frontend-production
npm run dev

# Should start on port 4300 (or check output for actual port)
```

---

### **Step 2: Open DAG Studio**

```bash
# Open in browser:
http://3.10.213.208:4300/dag-studio
```

Expected: DAG Studio canvas should load

---

### **Step 3: Create & Execute Simple Workflow**

1. **Add Requirements Phase:**
   - Drag "Requirements" from left palette onto canvas
   - Click the node
   - In right panel, set:
     - Label: "User API Requirements"
     - Requirement Text: "Build REST API for user management"
     - Assigned Team: Pick any AI agent

2. **Add Architecture Phase:**
   - Drag "Architecture" onto canvas
   - Configure:
     - Label: "API Architecture"
     - Architecture Design: "Design microservices"
     - Assigned Team: Pick any AI agent

3. **Connect Nodes:**
   - Drag from Requirements output to Architecture input
   - You should see a connecting edge

4. **Execute:**
   - Click "▶ Execute Workflow" button in toolbar
   - **Expected Alert:** "Workflow execution started! Execution ID: exec_xxx"

5. **Watch Real-Time Updates:**
   - Nodes should change colors:
     - BLUE = Running
     - GREEN = Completed
     - RED = Failed
   - Check browser console (F12) for:
     ```
     [DAGStudio] WebSocket connected
     [DAGStudio] WebSocket message: { type: 'node_started', ... }
     [DAGStudio] Updating node to RUNNING: node-xxx
     [DAGStudio] WebSocket message: { type: 'node_completed', ... }
     ```

---

## ✅ Verification Checklist

After restarting frontend, verify these in browser console:

**On Page Load:**
```
[DAGStudio] Loading personas from backend...
[DAGStudio] Loaded X personas from backend
```

**On Execute:**
```
[DAGStudio] Executing workflow: My Workflow Name
✅ Workflow execution queued: { execution_id: "exec_xxx", ... }
[DAGStudio] Saved execution_id to localStorage: exec_xxx
[DAGStudio] Connecting WebSocket: ws://3.10.213.208:5001/ws/workflow/...
[DAGStudio] WebSocket connected
```

**During Execution:**
```
[DAGStudio] WebSocket message: { type: 'workflow_started', ... }
[DAGStudio] WebSocket message: { type: 'node_started', node_id: 'node-xxx' }
[DAGStudio] Updating node to RUNNING: node-xxx
[DAGStudio] WebSocket message: { type: 'node_completed', node_id: 'node-xxx' }
[DAGStudio] Updating node to COMPLETED: node-xxx
...
[DAGStudio] Workflow completed
```

---

## 🐛 Troubleshooting

### Issue: "Network error. Backend may be unavailable"

**Check:**
```bash
curl http://3.10.213.208:5001/health
```

Should return:
```json
{
  "status": "healthy",
  "service": "workflow-api-v2",
  "version": "2.0.0"
}
```

If not working, restart backend:
```bash
ps aux | grep workflow_api_v2
kill <PID>
python3 workflow_api_v2.py
```

---

### Issue: WebSocket not connecting

**Check browser console:**
- Look for: `WebSocket connection to 'ws://3.10.213.208:5001/ws/workflow/xxx' failed`

**Solution:**
1. Verify backend is running (curl health check above)
2. Check firewall allows WebSocket connections
3. Try accessing from same network as server

---

### Issue: Nodes don't update during execution

**Check:**
1. **Browser console** - Are WebSocket messages arriving?
2. **Backend logs:**
   ```bash
   # Check if workflow is actually executing
   curl http://3.10.213.208:5001/api/workflow/status/exec_xxx
   ```

---

## 📊 Backend API Testing

You can test the backend directly:

### Execute Test Workflow
```bash
curl -X POST http://3.10.213.208:5001/api/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "test-1",
    "workflow_name": "Test Workflow",
    "nodes": [
      {
        "id": "node-1",
        "phase_type": "requirements",
        "label": "Requirements",
        "phase_config": {
          "requirementText": "Test requirement",
          "executor_ai": "claude-3-5-sonnet-20241022"
        }
      }
    ],
    "edges": []
  }'
```

Expected response:
```json
{
  "execution_id": "exec_xxx",
  "workflow_id": "test-1",
  "status": "pending",
  "total_phases": 1,
  "websocket_url": "/ws/workflow/test-1"
}
```

### Check Execution Status
```bash
curl http://3.10.213.208:5001/api/workflow/status/exec_xxx
```

---

## 📁 Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `frontend/.env` | `VITE_DAG_API_URL=http://3.10.213.208:5001` | Point to backend |
| `dagExecutionService.ts` | Use `VITE_DAG_API_URL` | Correct env var |
| `dagStudioStore.ts` | WebSocket uses `VITE_DAG_API_URL` | Consistent config |

---

## 🎉 What Happens When It Works

1. **User clicks Execute** → Frontend sends workflow to `http://3.10.213.208:5001/api/workflow/execute`
2. **Backend returns execution_id** → Frontend gets `exec_xxx`
3. **WebSocket connects** → `ws://3.10.213.208:5001/ws/workflow/xxx`
4. **Backend executes phases** → TeamExecutionEngineV2SplitMode runs each phase
5. **Real-time events** → Backend broadcasts `node_started`, `node_completed` to frontend
6. **Frontend updates canvas** → Nodes change color in real-time
7. **Workflow completes** → All nodes green, alert shown

---

## 🔗 Important URLs

- **Frontend:** `http://3.10.213.208:4300/dag-studio` (or your actual port)
- **Backend API:** `http://3.10.213.208:5001`
- **Backend Docs:** `http://3.10.213.208:5001/docs`
- **Health Check:** `http://3.10.213.208:5001/health`

---

## ✅ Success Criteria

You know it's working when:

1. ✅ DAG Studio loads in browser
2. ✅ You can drag phases onto canvas
3. ✅ Execute button appears in toolbar
4. ✅ Clicking Execute shows alert with execution_id
5. ✅ Browser console shows "WebSocket connected"
6. ✅ Nodes change color (blue → green) during execution
7. ✅ Final alert: "Workflow completed successfully!"

---

**That's it! Your integration is complete. Just restart the frontend and test!** 🚀
