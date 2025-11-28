"""
Vanilla Workflow API Service
Simple service that accepts DAG workflow blueprints and returns immediate confirmation.
Actual execution happens in background.

Usage:
    env POSTGRES_PASSWORD=maestro_dev python3 workflow_api_vanilla.py
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class PhaseConfig(BaseModel):
    """Configuration for a workflow phase"""
    requirementText: Optional[str] = None
    architectureDesign: Optional[str] = None
    implementationDetails: Optional[str] = None
    testPlan: Optional[str] = None
    deploymentConfig: Optional[str] = None
    reviewCriteria: Optional[str] = None
    assigned_team: List[str] = Field(default_factory=list)
    executor_ai: Optional[str] = "claude-3-5-sonnet-20241022"


class WorkflowNode(BaseModel):
    """DAG workflow node definition"""
    id: str
    phase_type: str
    label: str
    phase_config: PhaseConfig


class WorkflowEdge(BaseModel):
    """DAG workflow edge (dependency)"""
    source: str
    target: str


class DAGWorkflowExecute(BaseModel):
    """DAG workflow execution request"""
    workflow_id: str
    workflow_name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# WebSocket Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections for workflow updates"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, workflow_id: str):
        """Accept and track WebSocket connection"""
        await websocket.accept()
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        self.active_connections[workflow_id].append(websocket)
        logger.info(f"📡 WebSocket connected for workflow: {workflow_id}")

    def disconnect(self, websocket: WebSocket, workflow_id: str):
        """Remove WebSocket connection"""
        if workflow_id in self.active_connections:
            self.active_connections[workflow_id].remove(websocket)
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]
        logger.info(f"📡 WebSocket disconnected for workflow: {workflow_id}")

    async def broadcast(self, workflow_id: str, message: dict):
        """Broadcast message to all connected clients for this workflow"""
        if workflow_id in self.active_connections:
            for connection in self.active_connections[workflow_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to WebSocket: {e}")


# ---------------------------------------------------------------------------
# In-Memory Execution Store
# ---------------------------------------------------------------------------

class ExecutionStore:
    """Simple in-memory store for execution status"""

    def __init__(self):
        self.executions: Dict[str, Dict[str, Any]] = {}

    def create(self, execution_id: str, workflow_id: str, workflow_name: str, nodes: int, edges: int) -> Dict[str, Any]:
        """Create new execution record"""
        execution = {
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'workflow_name': workflow_name,
            'status': 'pending',
            'nodes_count': nodes,
            'edges_count': edges,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'error': None
        }
        self.executions[execution_id] = execution
        logger.info(f"📝 Created execution record: {execution_id}")
        return execution

    def update_status(self, execution_id: str, status: str, error: Optional[str] = None):
        """Update execution status"""
        if execution_id in self.executions:
            self.executions[execution_id]['status'] = status
            self.executions[execution_id]['updated_at'] = datetime.now().isoformat()

            if status == 'running' and not self.executions[execution_id]['started_at']:
                self.executions[execution_id]['started_at'] = datetime.now().isoformat()
            elif status in ['completed', 'failed', 'cancelled']:
                self.executions[execution_id]['completed_at'] = datetime.now().isoformat()

            if error:
                self.executions[execution_id]['error'] = error

            logger.info(f"📝 Updated execution {execution_id}: {status}")

    def get(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution record"""
        return self.executions.get(execution_id)


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vanilla Workflow API",
    description="Simple workflow execution service with async background processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
manager = ConnectionManager()
execution_store = ExecutionStore()
background_tasks = set()


# ---------------------------------------------------------------------------
# Background Task Simulation
# ---------------------------------------------------------------------------

async def execute_workflow_background(
    execution_id: str,
    workflow_id: str,
    workflow_name: str,
    nodes: List[WorkflowNode],
    edges: List[WorkflowEdge]
):
    """
    Background task that simulates workflow execution.
    In real implementation, this would call the actual execution engine.
    """
    try:
        logger.info(f"🚀 Background execution started: {execution_id}")

        # Update status to running
        execution_store.update_status(execution_id, 'running')
        await manager.broadcast(workflow_id, {
            'type': 'workflow_started',
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'timestamp': datetime.now().isoformat()
        })

        # Simulate processing each node
        for i, node in enumerate(nodes, 1):
            logger.info(f"📦 Processing node {i}/{len(nodes)}: {node.id} ({node.phase_type})")

            # Broadcast node started
            await manager.broadcast(workflow_id, {
                'type': 'node_started',
                'execution_id': execution_id,
                'node_id': node.id,
                'phase_type': node.phase_type,
                'progress': f"{i}/{len(nodes)}",
                'timestamp': datetime.now().isoformat()
            })

            # Simulate work (in real implementation, call execution engine here)
            await asyncio.sleep(2)  # Simulate processing time

            # Broadcast node completed
            await manager.broadcast(workflow_id, {
                'type': 'node_completed',
                'execution_id': execution_id,
                'node_id': node.id,
                'phase_type': node.phase_type,
                'status': 'completed',
                'progress': f"{i}/{len(nodes)}",
                'timestamp': datetime.now().isoformat()
            })

        # Mark as completed
        execution_store.update_status(execution_id, 'completed')
        await manager.broadcast(workflow_id, {
            'type': 'workflow_completed',
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"✅ Background execution completed: {execution_id}")

    except asyncio.CancelledError:
        logger.warning(f"🛑 Execution cancelled: {execution_id}")
        execution_store.update_status(execution_id, 'cancelled')
        raise

    except Exception as e:
        logger.error(f"❌ Execution failed: {execution_id} - {e}", exc_info=True)
        execution_store.update_status(execution_id, 'failed', error=str(e))
        await manager.broadcast(workflow_id, {
            'type': 'workflow_failed',
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "workflow-api-vanilla",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/workflow/execute")
async def execute_workflow(params: DAGWorkflowExecute):
    """
    Execute DAG workflow (vanilla implementation).
    Returns immediately with execution_id, actual execution happens in background.
    """
    try:
        # Generate execution ID
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"

        logger.info(f"🎨 Workflow execution request: {params.workflow_id}")
        logger.info(f"   - Workflow name: {params.workflow_name}")
        logger.info(f"   - Nodes: {len(params.nodes)}")
        logger.info(f"   - Edges: {len(params.edges)}")
        logger.info(f"   - Execution ID: {execution_id}")

        # Validate input
        if not params.nodes:
            raise HTTPException(status_code=400, detail="Workflow must have at least one node")

        # Create execution record
        execution = execution_store.create(
            execution_id=execution_id,
            workflow_id=params.workflow_id,
            workflow_name=params.workflow_name,
            nodes=len(params.nodes),
            edges=len(params.edges)
        )

        # Start background execution
        task = asyncio.create_task(
            execute_workflow_background(
                execution_id=execution_id,
                workflow_id=params.workflow_id,
                workflow_name=params.workflow_name,
                nodes=params.nodes,
                edges=params.edges
            )
        )
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        # Return immediately
        logger.info(f"✅ Execution {execution_id} started in background, returning immediately")

        return {
            'execution_id': execution_id,
            'workflow_id': params.workflow_id,
            'workflow_name': params.workflow_name,
            'status': 'pending',
            'message': 'Workflow execution started in background',
            'started_at': execution['created_at']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting workflow execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@app.get("/api/workflow/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get execution status"""
    execution = execution_store.get(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return execution


@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    await manager.connect(websocket, workflow_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            'type': 'connected',
            'workflow_id': workflow_id,
            'timestamp': datetime.now().isoformat()
        })

        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            logger.debug(f"📨 Received from client: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, workflow_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket, workflow_id)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "5001"))
    logger.info(f"🚀 Starting Vanilla Workflow API on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
