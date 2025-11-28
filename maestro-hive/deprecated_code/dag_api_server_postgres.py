#!/usr/bin/env python3
"""
DAG Workflow API Server with PostgreSQL Backend

Enhanced version of dag_api_server.py with PostgreSQL persistence.
Supports production deployment with database-backed workflow storage.

Usage:
    # With PostgreSQL (production):
    python3 dag_api_server_postgres.py

    # With SQLite (development):
    export USE_SQLITE=true
    python3 dag_api_server_postgres.py

API will be available at:
    - REST API: http://localhost:8000/api
    - WebSocket: ws://localhost:8000/ws/workflow/{workflow_id}
    - API Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from dag_executor import DAGExecutor, ExecutionEvent
from dag_workflow import WorkflowDAG, WorkflowContext, NodeStatus
from dag_compatibility import generate_parallel_workflow, generate_linear_workflow

# Database imports
from database import (
    initialize_database,
    get_db,
    db_engine,
    DatabaseWorkflowContextStore,
    RepositoryFactory,
    WorkflowStatus as DBWorkflowStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
try:
    initialize_database(create_tables=True)
    logger.info("✅ Database initialized successfully")
except Exception as e:
    logger.error(f"❌ Database initialization failed: {e}")
    logger.info("Falling back to SQLite...")
    import os
    os.environ['USE_SQLITE'] = 'true'
    initialize_database(create_tables=True)

# Create FastAPI app
app = FastAPI(
    title="Maestro DAG Workflow API (PostgreSQL)",
    description="REST API and WebSocket server for DAG workflow visualization and control with PostgreSQL persistence",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:3000",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database-backed storage
context_store = DatabaseWorkflowContextStore()

# In-memory cache for active workflows (definitions)
active_workflows: Dict[str, WorkflowDAG] = {}

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

        for connection in self.active_connections[workflow_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")

manager = ConnectionManager()


# =============================================================================
# Pydantic Models (same as original)
# =============================================================================

class WorkflowCreate(BaseModel):
    name: str
    type: str = "parallel"
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

def create_event_handler(workflow_id: str, execution_id: str):
    """Create event handler that broadcasts to WebSocket clients and logs to DB"""
    async def handler(event: ExecutionEvent):
        event_data = {
            'type': event.event_type.value,
            'timestamp': event.timestamp.isoformat(),
            'workflow_id': workflow_id,
            'execution_id': execution_id,
            'node_id': event.node_id,
            'data': event.data or {}
        }

        # Broadcast to WebSocket clients
        await manager.broadcast(workflow_id, event_data)

        # Log to database
        context_store.log_event(
            execution_id=execution_id,
            event_type=event.event_type.value,
            node_id=event.node_id,
            message=f"{event.event_type.value}: {event.node_id or 'workflow'}",
            data=event.data
        )

        logger.info(f"Event: {event.event_type.value} - {event.node_id or 'workflow'}")

    return handler


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "service": "Maestro DAG Workflow API (PostgreSQL)",
        "version": "2.0.0",
        "database": "PostgreSQL" if not db_engine.config.use_sqlite else "SQLite",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check with database connectivity"""
    db_healthy = db_engine.health_check()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "database_type": "PostgreSQL" if not db_engine.config.use_sqlite else "SQLite"
    }


# -----------------------------------------------------------------------------
# Workflow Management
# -----------------------------------------------------------------------------

@app.get("/api/workflows", response_model=List[WorkflowResponse])
async def list_workflows(db: Session = Depends(get_db)):
    """List all workflow definitions"""
    repos = RepositoryFactory(db)
    db_workflows = repos.workflow.list(limit=100)

    workflows = [
        WorkflowResponse(
            workflow_id=wf.id,
            name=wf.name,
            type=wf.workflow_type,
            nodes=len(wf.nodes),
            edges=len(wf.edges),
            created_at=wf.created_at.isoformat()
        )
        for wf in db_workflows
    ]

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
async def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    """Create a new workflow definition"""
    repos = RepositoryFactory(db)

    # Create mock engine for workflow generation
    class MockEngine:
        async def _execute_single_phase(self, phase_name, context, requirement):
            logger.info(f"Mock executing: {phase_name}")
            await asyncio.sleep(0.5)
            return {"phase": phase_name, "status": "completed"}

    engine = MockEngine()

    # Generate workflow DAG
    if workflow.type == "parallel":
        dag = generate_parallel_workflow(workflow_name=workflow.name, team_engine=engine)
    else:
        dag = generate_linear_workflow(workflow_name=workflow.name, team_engine=engine)

    # Store in database
    db_workflow = repos.workflow.create(dag)

    # Cache in memory
    active_workflows[dag.workflow_id] = dag

    return WorkflowResponse(
        workflow_id=db_workflow.id,
        name=db_workflow.name,
        type=db_workflow.workflow_type,
        nodes=len(db_workflow.nodes),
        edges=len(db_workflow.edges),
        created_at=db_workflow.created_at.isoformat()
    )


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Get workflow details with nodes and edges for visualization"""
    repos = RepositoryFactory(db)

    # Try to get from database
    db_workflow = repos.workflow.get(workflow_id)

    if not db_workflow:
        # Create default workflow if it doesn't exist
        class MockEngine:
            async def _execute_single_phase(self, phase_name, context, requirement):
                await asyncio.sleep(0.5)
                return {"phase": phase_name, "status": "completed"}

        engine = MockEngine()

        if "parallel" in workflow_id:
            workflow = generate_parallel_workflow(workflow_id, engine)
        else:
            workflow = generate_linear_workflow(workflow_id, engine)

        # Store in database
        db_workflow = repos.workflow.create(workflow)
        active_workflows[workflow_id] = workflow
    else:
        # Load workflow from cache or create from DB definition
        if workflow_id not in active_workflows:
            # Would need to reconstruct WorkflowDAG from DB
            # For now, create fresh workflow
            class MockEngine:
                async def _execute_single_phase(self, phase_name, context, requirement):
                    await asyncio.sleep(0.5)
                    return {"phase": phase_name, "status": "completed"}

            engine = MockEngine()
            if db_workflow.workflow_type == "parallel":
                workflow = generate_parallel_workflow(workflow_id, engine)
            else:
                workflow = generate_linear_workflow(workflow_id, engine)
            active_workflows[workflow_id] = workflow

    workflow = active_workflows[workflow_id]

    # Convert to frontend format
    nodes = []
    for node_id, node in workflow.nodes.items():
        nodes.append({
            'id': node_id,
            'type': 'phase',
            'position': {'x': 0, 'y': 0},
            'data': {
                'phase': node.name,
                'label': node.name.replace('_', ' ').title(),
                'status': 'pending',
                'node_type': node.node_type.value,
            }
        })

    edges = []
    for source, target in workflow.graph.edges():
        edges.append({
            'id': f"{source}-{target}",
            'source': source,
            'target': target,
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
async def execute_workflow(
    workflow_id: str,
    params: WorkflowExecute,
    db: Session = Depends(get_db)
):
    """Start workflow execution with database persistence"""
    # Get or create workflow
    if workflow_id not in active_workflows:
        repos = RepositoryFactory(db)
        db_workflow = repos.workflow.get(workflow_id)

        if not db_workflow:
            # Create default workflow
            class MockEngine:
                async def _execute_single_phase(self, phase_name, context, requirement):
                    await asyncio.sleep(0.5)
                    return {"phase": phase_name, "status": "completed"}

            engine = MockEngine()
            if "parallel" in workflow_id:
                workflow = generate_parallel_workflow(workflow_id, engine)
            else:
                workflow = generate_linear_workflow(workflow_id, engine)

            repos.workflow.create(workflow)
            active_workflows[workflow_id] = workflow
        else:
            # Reconstruct from DB
            class MockEngine:
                async def _execute_single_phase(self, phase_name, context, requirement):
                    await asyncio.sleep(0.5)
                    return {"phase": phase_name, "status": "completed"}

            engine = MockEngine()
            if db_workflow.workflow_type == "parallel":
                workflow = generate_parallel_workflow(workflow_id, engine)
            else:
                workflow = generate_linear_workflow(workflow_id, engine)
            active_workflows[workflow_id] = workflow

    workflow = active_workflows[workflow_id]

    # Create execution in database
    repos = RepositoryFactory(db)
    initial_context = params.initial_context or {}
    initial_context['requirement'] = params.requirement

    db_execution = repos.execution.create(
        workflow_id=workflow_id,
        initial_context=initial_context
    )
    execution_id = db_execution.id

    # Create executor with event handler
    event_handler = create_event_handler(workflow_id, execution_id)
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store,
        event_handler=event_handler
    )

    # Start execution in background
    async def run_execution():
        try:
            # Update status to running
            context_store.update_execution_status(execution_id, 'running')

            # Execute workflow
            context = await executor.execute(initial_context=initial_context)

            # Update status to completed
            context_store.update_execution_status(execution_id, 'completed')

            logger.info(f"Execution {execution_id} completed")

            # Broadcast completion
            await manager.broadcast(workflow_id, {
                'type': 'workflow_completed',
                'execution_id': execution_id,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            # Update status to failed
            context_store.update_execution_status(
                execution_id, 'failed', error_message=str(e)
            )

            logger.error(f"Execution failed: {e}", exc_info=True)

            # Broadcast failure
            await manager.broadcast(workflow_id, {
                'type': 'workflow_failed',
                'execution_id': execution_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    asyncio.create_task(run_execution())

    return {
        'execution_id': execution_id,
        'workflow_id': workflow_id,
        'status': 'running',
        'started_at': db_execution.created_at.isoformat()
    }


@app.get("/api/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str, db: Session = Depends(get_db)):
    """Get execution status from database"""
    repos = RepositoryFactory(db)

    execution = repos.execution.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Get node states
    node_states = repos.node_state.get_by_execution(execution_id)

    node_state_responses = [
        NodeStateResponse(
            node_id=ns.node_id,
            status=ns.status.value,
            attempt_count=ns.attempt_count,
            started_at=ns.started_at.isoformat() if ns.started_at else None,
            completed_at=ns.completed_at.isoformat() if ns.completed_at else None,
            duration=ns.duration_seconds,
            outputs=ns.outputs,
            artifacts=[],  # Would load from artifacts table
            error=ns.error_message
        )
        for ns in node_states
    ]

    return ExecutionStatusResponse(
        execution_id=execution_id,
        workflow_id=execution.workflow_id,
        status=execution.status.value,
        completed_nodes=execution.completed_nodes,
        total_nodes=execution.total_nodes,
        progress_percent=execution.progress_percent,
        node_states=node_state_responses,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None
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
            data = await websocket.receive_text()
            logger.info(f"Received from client: {data}")

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

    logger.info("="*70)
    logger.info("Starting Maestro DAG Workflow API Server (PostgreSQL Edition)...")
    logger.info("="*70)
    logger.info(f"Database: {'PostgreSQL' if not db_engine.config.use_sqlite else 'SQLite'}")
    logger.info(f"API Docs: http://localhost:8000/docs")
    logger.info(f"WebSocket: ws://localhost:8000/ws/workflow/{{workflow_id}}")
    logger.info("="*70)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
