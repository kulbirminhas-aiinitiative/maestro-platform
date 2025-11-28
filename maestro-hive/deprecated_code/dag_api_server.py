#!/usr/bin/env python3
"""
DAG Workflow API Server

Exposes DAG workflow engine via REST API and WebSocket for frontend integration.

Usage:
    python3 dag_api_server.py

API will be available at:
    - REST API: http://localhost:8000/api
    - WebSocket: ws://localhost:8000/ws/workflow/{workflow_id}
    - API Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from dag_executor import DAGExecutor, WorkflowContextStore, ExecutionEvent
from dag_workflow import WorkflowDAG, WorkflowContext, NodeStatus
from dag_compatibility import generate_parallel_workflow, generate_linear_workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Maestro DAG Workflow API",
    description="REST API and WebSocket server for DAG workflow visualization and control",
    version="1.0.0"
)

# CORS middleware (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",  # Frontend dev server
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:4200",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (use Redis/PostgreSQL in production)
active_workflows: Dict[str, WorkflowDAG] = {}
active_executions: Dict[str, tuple[DAGExecutor, WorkflowContext]] = {}
context_store = WorkflowContextStore()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, workflow_id: str):
        await websocket.accept()
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        self.active_connections[workflow_id].append(websocket)
        logger.info(f"WebSocket connected: {workflow_id}")

    def disconnect(self, websocket: WebSocket, workflow_id: str):
        if workflow_id in self.active_connections:
            self.active_connections[workflow_id].remove(websocket)
        logger.info(f"WebSocket disconnected: {workflow_id}")

    async def broadcast(self, workflow_id: str, message: dict):
        if workflow_id not in self.active_connections:
            return

        # Broadcast to all connected clients
        for connection in self.active_connections[workflow_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")

manager = ConnectionManager()

# =============================================================================
# Pydantic Models
# =============================================================================

class WorkflowCreate(BaseModel):
    name: str
    type: str = "parallel"  # 'linear' or 'parallel'
    description: Optional[str] = None


class WorkflowExecute(BaseModel):
    requirement: str
    initial_context: Optional[Dict[str, Any]] = None


class NodeStateResponse(BaseModel):
    node_id: str
    status: str
    attempt_count: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration: Optional[float] = None
    outputs: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[str]] = None
    error: Optional[str] = None


class ExecutionStatusResponse(BaseModel):
    execution_id: str
    workflow_id: str
    status: str
    completed_nodes: int
    total_nodes: int
    progress_percent: float
    node_states: List[NodeStateResponse]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    name: str
    type: str
    nodes: int
    edges: int
    created_at: str


# =============================================================================
# Helper Functions
# =============================================================================

def format_node_state(node_id: str, state: Any, context: WorkflowContext) -> NodeStateResponse:
    """Format node state for API response"""
    return NodeStateResponse(
        node_id=node_id,
        status=state.status.value,
        attempt_count=state.attempt_count,
        started_at=state.started_at.isoformat() if state.started_at else None,
        completed_at=state.completed_at.isoformat() if state.completed_at else None,
        duration=(state.completed_at - state.started_at).total_seconds()
            if state.completed_at and state.started_at else None,
        outputs=context.node_outputs.get(node_id),
        artifacts=context.artifacts.get(node_id, []),
        error=state.error
    )


def create_event_handler(workflow_id: str):
    """Create event handler that broadcasts to WebSocket clients"""
    async def handler(event: ExecutionEvent):
        event_data = {
            'type': event.event_type.value,
            'timestamp': event.timestamp.isoformat(),
            'workflow_id': workflow_id,
            'node_id': event.node_id,
            'data': event.data or {}
        }
        await manager.broadcast(workflow_id, event_data)
        logger.info(f"Event: {event.event_type.value} - {event.node_id or 'workflow'}")

    return handler


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "service": "Maestro DAG Workflow API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_workflows": len(active_workflows),
        "active_executions": len(active_executions)
    }


# -----------------------------------------------------------------------------
# Workflow Management
# -----------------------------------------------------------------------------

@app.get("/api/workflows", response_model=List[WorkflowResponse])
async def list_workflows():
    """List all workflow definitions"""
    workflows = []

    # Add active workflows
    for wf_id, workflow in active_workflows.items():
        workflows.append(WorkflowResponse(
            workflow_id=wf_id,
            name=workflow.name,
            type=workflow.metadata.get('type', 'unknown'),
            nodes=len(workflow.nodes),
            edges=len(workflow.edges),
            created_at=datetime.now().isoformat()
        ))

    # Add default workflows if none exist
    if not workflows:
        workflows = [
            WorkflowResponse(
                workflow_id="sdlc_parallel",
                name="SDLC Parallel Workflow",
                type="parallel",
                nodes=6,
                edges=7,
                created_at=datetime.now().isoformat()
            ),
            WorkflowResponse(
                workflow_id="sdlc_linear",
                name="SDLC Linear Workflow",
                type="linear",
                nodes=6,
                edges=5,
                created_at=datetime.now().isoformat()
            )
        ]

    return workflows


@app.post("/api/workflows", response_model=WorkflowResponse)
async def create_workflow(workflow: WorkflowCreate):
    """Create a new workflow definition"""
    from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

    # Create team engine (mock for now)
    class MockEngine:
        async def _execute_single_phase(self, phase_name, context, requirement):
            logger.info(f"Mock executing: {phase_name}")
            await asyncio.sleep(0.5)
            return {"phase": phase_name, "status": "completed"}

    engine = MockEngine()

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

    # Store workflow
    active_workflows[dag.workflow_id] = dag

    return WorkflowResponse(
        workflow_id=dag.workflow_id,
        name=workflow.name,
        type=workflow.type,
        nodes=len(dag.nodes),
        edges=len(dag.edges),
        created_at=datetime.now().isoformat()
    )


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details with nodes and edges for visualization"""
    if workflow_id not in active_workflows:
        # Create default workflow
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

        class MockEngine:
            async def _execute_single_phase(self, phase_name, context, requirement):
                await asyncio.sleep(0.5)
                return {"phase": phase_name, "status": "completed"}

        engine = MockEngine()

        if "parallel" in workflow_id:
            workflow = generate_parallel_workflow(workflow_id, engine)
        else:
            workflow = generate_linear_workflow(workflow_id, engine)

        active_workflows[workflow_id] = workflow
    else:
        workflow = active_workflows[workflow_id]

    # Convert to frontend format
    nodes = []
    for node_id, node in workflow.nodes.items():
        nodes.append({
            'id': node_id,
            'type': 'phase',
            'position': {'x': 0, 'y': 0},  # Frontend will layout
            'data': {
                'phase': node.name,
                'label': node.name.replace('_', ' ').title(),
                'status': 'pending',
                'node_type': node.node_type.value,
            }
        })

    edges = []
    for edge in workflow.edges:
        edges.append({
            'id': f"{edge.source}-{edge.target}",
            'source': edge.source,
            'target': edge.target,
            'type': 'smoothstep',
        })

    return {
        'workflow_id': workflow.workflow_id,
        'name': workflow.name,
        'type': workflow.metadata.get('type', 'unknown'),
        'nodes': nodes,
        'edges': edges
    }


# -----------------------------------------------------------------------------
# Workflow Execution
# -----------------------------------------------------------------------------

@app.post("/api/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, params: WorkflowExecute):
    """Start workflow execution"""
    if workflow_id not in active_workflows:
        # Create workflow if it doesn't exist
        await get_workflow(workflow_id)

    workflow = active_workflows[workflow_id]

    # Create executor with event handler
    event_handler = create_event_handler(workflow_id)
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store,
        event_handler=event_handler
    )

    # Start execution in background
    initial_context = params.initial_context or {}
    initial_context['requirement'] = params.requirement

    async def run_execution():
        try:
            context = await executor.execute(initial_context=initial_context)
            execution_id = context.execution_id
            active_executions[execution_id] = (executor, context)
            logger.info(f"Execution {execution_id} completed")

            # Broadcast completion
            await manager.broadcast(workflow_id, {
                'type': 'workflow_completed',
                'execution_id': execution_id,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            await manager.broadcast(workflow_id, {
                'type': 'workflow_failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    asyncio.create_task(run_execution())

    execution_id = f"exec_{workflow_id}_{int(datetime.now().timestamp())}"

    return {
        'execution_id': execution_id,
        'workflow_id': workflow_id,
        'status': 'running',
        'started_at': datetime.now().isoformat()
    }


@app.get("/api/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str):
    """Get execution status"""
    if execution_id not in active_executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    executor, context = active_executions[execution_id]

    # Build node states
    node_states = [
        format_node_state(node_id, state, context)
        for node_id, state in context.node_states.items()
    ]

    completed = len(context.get_completed_nodes())
    total = len(context.node_states)

    return ExecutionStatusResponse(
        execution_id=execution_id,
        workflow_id=context.workflow_id,
        status="completed" if completed == total else "running",
        completed_nodes=completed,
        total_nodes=total,
        progress_percent=(completed / total * 100) if total > 0 else 0,
        node_states=node_states,
        started_at=datetime.now().isoformat(),
        completed_at=None
    )


# -----------------------------------------------------------------------------
# WebSocket
# -----------------------------------------------------------------------------

@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    await manager.connect(websocket, workflow_id)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            logger.info(f"Received from client: {data}")

            # Echo back for testing
            await websocket.send_json({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, workflow_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, workflow_id)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Maestro DAG Workflow API Server...")
    logger.info("API Docs: http://localhost:8000/docs")
    logger.info("WebSocket: ws://localhost:8000/ws/workflow/{workflow_id}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
