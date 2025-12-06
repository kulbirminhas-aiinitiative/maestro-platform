#!/usr/bin/env python3
"""
DAG Workflow API Server (Production)

Production-ready API server with comprehensive error handling, validation,
and robustness features.

Key Features:
- Database-backed persistence (PostgreSQL/SQLite)
- Comprehensive error handling
- Input validation
- Workflow caching with thread safety
- Real-time WebSocket updates
- Request timeouts
- Health checks
- Graceful shutdown
- Fail-fast on critical errors

Usage:
    # SQLite (development)
    USE_SQLITE=true python3 dag_api_server.py

    # PostgreSQL (production)
    python3 dag_api_server.py
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
import sys
import re
from pathlib import Path
from contextlib import asynccontextmanager
import threading

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from dag_executor import DAGExecutor, ExecutionEvent
from dag_workflow import WorkflowDAG
from dag_compatibility import generate_parallel_workflow, generate_linear_workflow
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

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

# Global state
context_store = DatabaseWorkflowContextStore()
active_workflows: Dict[str, WorkflowDAG] = {}
workflow_lock = threading.RLock()  # Thread-safe workflow cache
background_tasks = set()  # Track background executions

# =============================================================================
# Lifespan Management
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("="*70)
    logger.info("🚀 Starting Maestro DAG Workflow API Server")
    logger.info("="*70)

    try:
        initialize_database(create_tables=True)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ CRITICAL: Database initialization failed: {e}")
        logger.error("❌ CRITICAL: Database is required for production operation")
        logger.error("❌ CRITICAL: Server will not start without database")
        raise SystemExit(1)  # Fail fast - don't start without database

    logger.info(f"📊 Database: {'PostgreSQL' if not db_engine.config.use_sqlite else 'SQLite'}")
    logger.info(f"📚 API Docs: http://localhost:8003/docs")
    logger.info(f"🔌 WebSocket: ws://localhost:8003/ws/workflow/{{id}}")
    logger.info("="*70)

    yield

    # Shutdown
    logger.info("🛑 Shutting down gracefully...")

    # Cancel background tasks
    for task in background_tasks:
        if not task.done():
            task.cancel()

    # Wait for tasks to complete
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)

    # Dispose database
    db_engine.dispose()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Maestro DAG Workflow API",
    description="Production-ready REST API and WebSocket server for DAG workflow management",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# WebSocket Manager
# =============================================================================

class ConnectionManager:
    """Thread-safe WebSocket connection manager with limits"""

    MAX_CONNECTIONS_PER_WORKFLOW = 100  # Max connections per workflow
    MAX_TOTAL_CONNECTIONS = 1000  # Max total connections

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.lock = threading.Lock()

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        with self.lock:
            return sum(len(conns) for conns in self.active_connections.values())

    async def connect(self, websocket: WebSocket, workflow_id: str):
        """Connect WebSocket client with connection limits"""
        with self.lock:
            # Check total connection limit
            if self.get_total_connections() >= self.MAX_TOTAL_CONNECTIONS:
                await websocket.close(code=4003, reason="Server connection limit reached")
                logger.warning(f"⚠️  Connection rejected: total limit reached")
                return False

            # Check per-workflow connection limit
            if workflow_id in self.active_connections:
                if len(self.active_connections[workflow_id]) >= self.MAX_CONNECTIONS_PER_WORKFLOW:
                    await websocket.close(code=4003, reason="Workflow connection limit reached")
                    logger.warning(f"⚠️  Connection rejected for {workflow_id}: workflow limit reached")
                    return False

            # Accept connection
            await websocket.accept()
            if workflow_id not in self.active_connections:
                self.active_connections[workflow_id] = []
            self.active_connections[workflow_id].append(websocket)

        logger.info(f"📡 WebSocket connected: {workflow_id} ({len(self.active_connections[workflow_id])} total)")
        return True

    def disconnect(self, websocket: WebSocket, workflow_id: str):
        """Disconnect WebSocket client"""
        with self.lock:
            if workflow_id in self.active_connections:
                try:
                    self.active_connections[workflow_id].remove(websocket)
                    if not self.active_connections[workflow_id]:
                        del self.active_connections[workflow_id]
                except ValueError:
                    pass
        logger.info(f"📡 WebSocket disconnected: {workflow_id}")

    async def broadcast(self, workflow_id: str, message: dict):
        """Broadcast message to all connected clients"""
        with self.lock:
            connections = self.active_connections.get(workflow_id, []).copy()

        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"❌ Broadcast error: {e}")
                dead_connections.append(connection)

        # Clean up dead connections
        if dead_connections:
            with self.lock:
                for conn in dead_connections:
                    try:
                        self.active_connections[workflow_id].remove(conn)
                    except (ValueError, KeyError):
                        pass

manager = ConnectionManager()

# =============================================================================
# Pydantic Models with Validation
# =============================================================================

class WorkflowCreate(BaseModel):
    name: str
    type: str = "parallel"
    description: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Workflow name cannot be empty")
        if len(v) > 255:
            raise ValueError("Workflow name too long (max 255 chars)")
        return v.strip()

    @validator('type')
    def validate_type(cls, v):
        if v not in ['linear', 'parallel']:
            raise ValueError("Workflow type must be 'linear' or 'parallel'")
        return v


class WorkflowExecute(BaseModel):
    requirement: str
    initial_context: Optional[Dict[str, Any]] = None

    @validator('requirement')
    def validate_requirement(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Requirement cannot be empty")
        if len(v) > 10000:
            raise ValueError("Requirement too long (max 10000 chars)")
        return v.strip()


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
# Error Handlers
# =============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={"error": "validation_error", "message": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"}
    )

# =============================================================================
# Helper Functions
# =============================================================================

def validate_workflow_id(workflow_id: str) -> str:
    """Validate and sanitize workflow ID"""
    if not workflow_id:
        raise ValueError("Workflow ID cannot be empty")

    # Allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', workflow_id):
        raise ValueError("Invalid workflow ID format")

    if len(workflow_id) > 255:
        raise ValueError("Workflow ID too long")

    return workflow_id


def get_or_create_workflow(workflow_id: str, db: Session) -> WorkflowDAG:
    """
    Get workflow from cache or create it (thread-safe for single instance).

    Note: For multi-instance deployments, use distributed locking (Redis)
    or accept eventual consistency with database as source of truth.
    """
    workflow_id = validate_workflow_id(workflow_id)

    with workflow_lock:
        # Double-check pattern for thread safety
        if workflow_id in active_workflows:
            return active_workflows[workflow_id]

        # Check database
        repos = RepositoryFactory(db)
        db_workflow = repos.workflow.get(workflow_id)

        # Create real team engine
        try:
            engine = TeamExecutionEngineV2SplitMode()
            logger.info("✅ Created real TeamExecutionEngineV2SplitMode")
        except Exception as e:
            logger.error(f"❌ Failed to create real engine: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize execution engine: {str(e)}"
            )

        # Generate workflow
        try:
            if "parallel" in workflow_id:
                workflow = generate_parallel_workflow(workflow_name=workflow_id, team_engine=engine)
            else:
                workflow = generate_linear_workflow(workflow_name=workflow_id, team_engine=engine)

            logger.info(f"✅ Generated workflow: {workflow_id} with {len(workflow.nodes)} nodes")
        except Exception as e:
            logger.error(f"❌ Failed to generate workflow: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate workflow: {str(e)}"
            )

        # Store in database if not exists
        if not db_workflow:
            try:
                repos.workflow.create(workflow)
                logger.info(f"✅ Saved workflow to database: {workflow_id}")
            except Exception as e:
                logger.error(f"⚠️  Failed to save workflow to database: {e}")
                # Don't fail - workflow still works from cache

        # Cache it
        active_workflows[workflow_id] = workflow
        return workflow


def create_event_handler(workflow_id: str, execution_id: str):
    """Create event handler for workflow execution"""
    async def handler(event: ExecutionEvent):
        try:
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
            try:
                context_store.log_event(
                    execution_id=execution_id,
                    event_type=event.event_type.value,
                    node_id=event.node_id,
                    message=f"{event.event_type.value}: {event.node_id or 'workflow'}",
                    data=event.data
                )
            except Exception as e:
                logger.error(f"❌ Failed to log event to database: {e}")

            logger.info(f"📊 Event: {event.event_type.value} - {event.node_id or 'workflow'}")

        except Exception as e:
            logger.error(f"❌ Event handler error: {e}", exc_info=True)

    return handler

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Maestro DAG Workflow API",
        "version": "2.1.0",
        "status": "healthy",
        "database": "PostgreSQL" if not db_engine.config.use_sqlite else "SQLite",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check for monitoring systems.

    Returns detailed health status including database, cache, and tasks.
    Use /health/ready for Kubernetes readiness probes.
    Use /health/live for Kubernetes liveness probes.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0",
        "database": {
            "connected": False,
            "type": "PostgreSQL" if not db_engine.config.use_sqlite else "SQLite"
        },
        "cache": {
            "workflows": len(active_workflows),
            "websockets": sum(len(conns) for conns in manager.active_connections.values())
        },
        "tasks": {
            "background": len(background_tasks),
            "active": len([t for t in background_tasks if not t.done()])
        }
    }

    # Check database
    try:
        health_status["database"]["connected"] = db_engine.health_check()
    except Exception as e:
        health_status["database"]["error"] = str(e)
        health_status["status"] = "degraded"

    return health_status


@app.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe.

    Returns 200 if service is ready to accept traffic.
    Returns 503 if service is not ready (dependencies unavailable).

    Use this for Kubernetes readiness probes:
    ```yaml
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8003
      initialDelaySeconds: 10
      periodSeconds: 5
    ```
    """
    errors = []

    # Check 1: Database connection
    try:
        if not db_engine.health_check():
            errors.append("database_unavailable")
    except Exception as e:
        errors.append(f"database_error: {str(e)}")

    # Check 2: Workflows loaded
    if len(active_workflows) == 0:
        logger.warning("Readiness check: No workflows loaded yet")
        # Don't fail - workflows are lazy-loaded on first request

    # Check 3: Too many failed background tasks
    failed_tasks = [t for t in background_tasks if t.done() and t.exception()]
    if len(failed_tasks) > 10:
        errors.append(f"too_many_failed_tasks: {len(failed_tasks)}")

    if errors:
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "errors": errors,
                "message": "Service not ready to accept traffic"
            }
        )

    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "ok",
            "workflows": len(active_workflows),
            "background_tasks": len([t for t in background_tasks if not t.done()])
        }
    }


@app.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe.

    Returns 200 if service is alive (not deadlocked/hung).
    Returns 503 if service should be restarted.

    Use this for Kubernetes liveness probes:
    ```yaml
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8003
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
    ```

    This is a lightweight check that doesn't verify dependencies.
    It only checks if the service process is responsive.
    """
    # Simple check: Can we respond?
    # If we can return this response, the service is alive
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_checks": {
            "api_responsive": True,
            "background_tasks_total": len(background_tasks),
            "active_connections": manager.get_total_connections()
        }
    }


@app.get("/health/startup")
async def startup_check(db: Session = Depends(get_db)):
    """
    Kubernetes startup probe.

    Returns 200 when service has completed initialization.
    Returns 503 during startup phase.

    Use this for Kubernetes startup probes:
    ```yaml
    startupProbe:
      httpGet:
        path: /health/startup
        port: 8003
      initialDelaySeconds: 5
      periodSeconds: 2
      failureThreshold: 30
    ```

    Allows up to 60 seconds for startup (30 * 2s).
    """
    errors = []

    # Check 1: Database initialized
    try:
        if not db_engine.health_check():
            errors.append("database_not_initialized")
    except Exception as e:
        errors.append(f"database_initialization_error: {str(e)}")

    # Check 2: Can create workflow (startup test)
    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
        engine = TeamExecutionEngineV2SplitMode()
        # If we can instantiate engine, startup is complete
    except Exception as e:
        errors.append(f"engine_initialization_error: {str(e)}")

    if errors:
        raise HTTPException(
            status_code=503,
            detail={
                "started": False,
                "errors": errors,
                "message": "Service still starting up"
            }
        )

    return {
        "started": True,
        "timestamp": datetime.utcnow().isoformat(),
        "initialization": {
            "database": "initialized",
            "engine": "initialized",
            "workflows": "ready"
        }
    }


# -----------------------------------------------------------------------------
# Workflow Management
# -----------------------------------------------------------------------------

@app.get("/api/workflows", response_model=List[WorkflowResponse])
async def list_workflows(db: Session = Depends(get_db)):
    """List all workflow definitions"""
    try:
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

    except Exception as e:
        logger.error(f"❌ Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list workflows")


@app.get("/api/workflows/{workflow_id}")
async def get_workflow_details(workflow_id: str, db: Session = Depends(get_db)):
    """Get workflow details with nodes and edges for visualization"""
    try:
        workflow = get_or_create_workflow(workflow_id, db)

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

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error getting workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get workflow")


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
    try:
        # Get or create workflow
        workflow = get_or_create_workflow(workflow_id, db)

        # Create execution in database
        repos = RepositoryFactory(db)
        initial_context = params.initial_context or {}
        initial_context['requirement'] = params.requirement

        db_execution = repos.execution.create(
            workflow_id=workflow_id,
            initial_context=initial_context
        )
        execution_id = db_execution.id

        logger.info(f"🚀 Starting execution: {execution_id}")

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

                # Execute workflow with timeout (default: 2 hours)
                timeout_seconds = params.initial_context.get('timeout_seconds', 7200) if params.initial_context else 7200

                try:
                    context = await asyncio.wait_for(
                        executor.execute(initial_context=initial_context),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    error_msg = f"Execution timeout after {timeout_seconds} seconds"
                    logger.error(f"⏱️  {error_msg}: {execution_id}")

                    # Update status to failed
                    context_store.update_execution_status(
                        execution_id, 'failed', error_message=error_msg
                    )

                    # Broadcast timeout
                    await manager.broadcast(workflow_id, {
                        'type': 'workflow_failed',
                        'execution_id': execution_id,
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    return

                # Update status to completed
                context_store.update_execution_status(execution_id, 'completed')

                logger.info(f"✅ Execution {execution_id} completed")

                # Broadcast completion
                await manager.broadcast(workflow_id, {
                    'type': 'workflow_completed',
                    'execution_id': execution_id,
                    'timestamp': datetime.now().isoformat()
                })

            except asyncio.CancelledError:
                logger.warning(f"🛑 Execution {execution_id} cancelled")
                context_store.update_execution_status(
                    execution_id, 'cancelled', error_message="Execution cancelled"
                )
                raise

            except Exception as e:
                # Update status to failed
                context_store.update_execution_status(
                    execution_id, 'failed', error_message=str(e)
                )

                logger.error(f"❌ Execution {execution_id} failed: {e}", exc_info=True)

                # Broadcast failure
                await manager.broadcast(workflow_id, {
                    'type': 'workflow_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

        # Track background task
        task = asyncio.create_task(run_execution())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        return {
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'status': 'running',
            'started_at': db_execution.created_at.isoformat()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error starting execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start execution")


@app.get("/api/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str, db: Session = Depends(get_db)):
    """Get execution status from database"""
    try:
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
                artifacts=[],
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get execution status")


# -----------------------------------------------------------------------------
# WebSocket
# -----------------------------------------------------------------------------

@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    try:
        workflow_id = validate_workflow_id(workflow_id)
    except ValueError as e:
        await websocket.close(code=4000, reason=str(e))
        return

    await manager.connect(websocket, workflow_id)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            logger.debug(f"📨 Received from client: {data}")

            # Echo back
            await websocket.send_json({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket, workflow_id)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket, workflow_id)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        log_level="info",
        access_log=True
    )
