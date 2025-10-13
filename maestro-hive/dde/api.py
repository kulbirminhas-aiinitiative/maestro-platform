"""
DDE Graph API

FastAPI endpoints for DDE (Dependency-Driven Execution) graph visualization.
Provides graph data, execution streams, and contract/lineage information.

Integrates with existing Maestro Platform DAG infrastructure.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import asyncio

from pydantic import BaseModel, Field

# Import existing infrastructure
try:
    from dag_workflow import WorkflowDAG, NodeType, NodeStatus
    from dag_executor import WorkflowContextStore, ExecutionEvent, ExecutionEventType
    from dde.artifact_stamper import ArtifactStamper, ArtifactMetadata
    from dde.capability_matcher import CapabilityMatcher, AgentProfile
except ImportError as e:
    print(f"Warning: Some DDE dependencies not available: {e}")


# ============================================================================
# Pydantic Models for API
# ============================================================================

class GraphPosition(BaseModel):
    """Position of a node in the graph"""
    x: float
    y: float


class GateStatus(BaseModel):
    """Status of a quality gate"""
    name: str
    status: str = Field(..., pattern="^(pending|running|passed|failed)$")
    severity: str = Field(..., pattern="^(BLOCKING|WARNING|INFO)$")
    message: Optional[str] = None


class ArtifactInfo(BaseModel):
    """Artifact information"""
    name: str
    path: str
    sha256: Optional[str] = None
    stamped_at: Optional[str] = None
    size_bytes: Optional[int] = None


class DDEGraphNode(BaseModel):
    """DDE Graph Node for visualization"""
    id: str
    type: str = Field(..., pattern="^(INTERFACE|ACTION|CHECKPOINT|NOTIFICATION|PHASE|CUSTOM)$")
    label: str
    capability: Optional[str] = None
    status: str = Field(..., pattern="^(pending|ready|running|completed|failed|skipped|blocked|retry)$")
    retry_count: int = 0
    max_retries: int = 1
    gates: List[GateStatus] = []
    outputs: List[ArtifactInfo] = []
    contract_version: Optional[str] = None
    contract_locked: bool = False
    estimated_effort: Optional[int] = None
    assigned_agent: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error_message: Optional[str] = None
    position: Optional[GraphPosition] = None


class DDEGraphEdge(BaseModel):
    """DDE Graph Edge for visualization"""
    id: str
    source: str
    target: str
    type: str = Field(default="dependency", pattern="^(dependency|contract|artifact_flow)$")
    label: Optional[str] = None
    animated: bool = False


class DDEGraph(BaseModel):
    """Complete DDE Graph"""
    iteration_id: str
    workflow_id: str
    nodes: List[DDEGraphNode]
    edges: List[DDEGraphEdge]
    execution_status: str = Field(..., pattern="^(pending|running|completed|failed|paused|cancelled)$")
    progress_percent: float = 0.0
    metadata: Dict[str, Any] = {}


class ContractPoint(BaseModel):
    """Contract point linking DDE to BDV/ACC"""
    node_id: str
    contract_name: str
    contract_version: str
    locked: bool
    locked_at: Optional[str] = None
    dependents: List[str] = []
    artifacts: List[ArtifactInfo] = []
    bdv_scenarios: List[str] = []  # Cross-reference to BDV


class LineageNode(BaseModel):
    """Node in artifact lineage graph"""
    id: str
    type: str = Field(..., pattern="^(source|intermediate|consumer)$")
    label: str
    artifacts: List[ArtifactInfo]
    position: Optional[GraphPosition] = None


class LineageEdge(BaseModel):
    """Edge in artifact lineage graph"""
    id: str
    source: str
    target: str
    artifact_name: str
    flow_type: str = Field(default="direct", pattern="^(direct|derived|transformed)$")


class LineageGraph(BaseModel):
    """Artifact lineage graph"""
    iteration_id: str
    nodes: List[LineageNode]
    edges: List[LineageEdge]


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/v1/dde", tags=["DDE Graph"])

# In-memory storage for active WebSocket connections (move to Redis in production)
active_connections: Dict[str, List[WebSocket]] = {}


# ============================================================================
# Graph Data Endpoints
# ============================================================================

@router.get("/graph/{iteration_id}", response_model=DDEGraph)
async def get_dde_graph(
    iteration_id: str,
    include_positions: bool = Query(True, description="Calculate auto-layout positions")
) -> DDEGraph:
    """
    Get DDE workflow graph for visualization.

    Returns complete graph with nodes, edges, execution state, and optional positions.
    """
    try:
        # Load execution context
        context = await load_execution_context(iteration_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Iteration {iteration_id} not found")

        # Load workflow DAG
        workflow = await load_workflow_dag(context['workflow_id'])

        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow {context['workflow_id']} not found")

        # Build graph nodes
        nodes = []
        for node_id, node in workflow.nodes.items():
            # Get node state from context
            node_state = context.get('node_states', {}).get(node_id, {})

            # Extract gate statuses
            gates = []
            if hasattr(node, 'gates') and node.gates:
                for gate_name in node.gates:
                    gate_status = extract_gate_status(node_state, gate_name)
                    gates.append(gate_status)

            # Extract artifacts
            artifacts = []
            if node_state.get('artifacts'):
                for artifact_path in node_state['artifacts']:
                    artifact_info = await load_artifact_metadata(artifact_path)
                    if artifact_info:
                        artifacts.append(artifact_info)

            # Determine contract lock status
            contract_locked = False
            if node.node_type == NodeType.INTERFACE and hasattr(node, 'contract_version'):
                contract_locked = is_contract_locked(context, node_id)

            # Map status
            status = map_node_status(node_state.get('status', 'pending'))

            graph_node = DDEGraphNode(
                id=node_id,
                type=node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
                label=node.name,
                capability=getattr(node, 'capability', None),
                status=status,
                retry_count=node_state.get('attempt_count', 0),
                max_retries=node.retry_policy.max_attempts if hasattr(node, 'retry_policy') else 1,
                gates=gates,
                outputs=artifacts,
                contract_version=getattr(node, 'contract_version', None),
                contract_locked=contract_locked,
                estimated_effort=getattr(node, 'estimated_effort', None),
                assigned_agent=node_state.get('assigned_agent'),
                start_time=node_state.get('start_time'),
                end_time=node_state.get('end_time'),
                error_message=node_state.get('error_message'),
                position=None  # Will be calculated if include_positions=True
            )
            nodes.append(graph_node)

        # Build graph edges
        edges = []
        for node_id, node in workflow.nodes.items():
            for dep_id in node.dependencies:
                edge_type = "dependency"

                # Check if this is a contract dependency (INTERFACE -> impl)
                if dep_id in workflow.nodes:
                    dep_node = workflow.nodes[dep_id]
                    if dep_node.node_type == NodeType.INTERFACE:
                        edge_type = "contract"

                edge = DDEGraphEdge(
                    id=f"{dep_id}->{node_id}",
                    source=dep_id,
                    target=node_id,
                    type=edge_type,
                    animated=is_node_running(context, node_id)
                )
                edges.append(edge)

        # Calculate positions if requested
        if include_positions:
            nodes = calculate_graph_layout(nodes, edges, layout="hierarchical")

        # Calculate progress
        total_nodes = len(nodes)
        completed_nodes = len([n for n in nodes if n.status in ['completed', 'skipped']])
        progress = (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0

        graph = DDEGraph(
            iteration_id=iteration_id,
            workflow_id=context['workflow_id'],
            nodes=nodes,
            edges=edges,
            execution_status=context.get('execution_status', 'pending'),
            progress_percent=round(progress, 2),
            metadata={
                'created_at': context.get('created_at'),
                'started_at': context.get('started_at'),
                'completed_at': context.get('completed_at')
            }
        )

        return graph

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load DDE graph: {str(e)}")


@router.get("/graph/{iteration_id}/lineage", response_model=LineageGraph)
async def get_artifact_lineage(iteration_id: str) -> LineageGraph:
    """
    Get artifact lineage graph showing flow from interface nodes through implementation.
    """
    try:
        context = await load_execution_context(iteration_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Iteration {iteration_id} not found")

        # Build lineage graph
        nodes = []
        edges = []
        artifact_map = {}  # artifact_name -> node_id

        # Load artifact stamper
        stamper = ArtifactStamper()
        all_artifacts = stamper.list_artifacts(iteration_id=iteration_id)

        # Group artifacts by node
        node_artifacts = {}
        for artifact_meta in all_artifacts:
            node_id = artifact_meta.node_id
            if node_id not in node_artifacts:
                node_artifacts[node_id] = []
            node_artifacts[node_id].append(artifact_meta)

        # Create nodes
        for node_id, artifacts in node_artifacts.items():
            # Determine node type based on whether it produces or consumes
            node_type = "intermediate"
            if any(a.node_id.startswith("IF.") for a in artifacts):
                node_type = "source"

            artifacts_info = [
                ArtifactInfo(
                    name=a.artifact_name,
                    path=a.stamped_path,
                    sha256=a.sha256,
                    stamped_at=a.timestamp,
                    size_bytes=a.size_bytes
                )
                for a in artifacts
            ]

            lineage_node = LineageNode(
                id=node_id,
                type=node_type,
                label=node_id,
                artifacts=artifacts_info
            )
            nodes.append(lineage_node)

            # Map artifacts to nodes
            for artifact in artifacts:
                artifact_map[artifact.artifact_name] = node_id

        # Create edges based on artifact flow
        workflow = await load_workflow_dag(context['workflow_id'])
        if workflow:
            for node_id, node in workflow.nodes.items():
                # Find artifacts consumed by this node (from dependencies)
                for dep_id in node.dependencies:
                    if dep_id in node_artifacts:
                        for artifact in node_artifacts[dep_id]:
                            edge = LineageEdge(
                                id=f"{dep_id}->{node_id}:{artifact.artifact_name}",
                                source=dep_id,
                                target=node_id,
                                artifact_name=artifact.artifact_name,
                                flow_type="direct"
                            )
                            edges.append(edge)

        # Calculate positions
        nodes_with_pos = calculate_graph_layout(
            [n.dict() for n in nodes],
            [e.dict() for e in edges],
            layout="hierarchical"
        )

        for i, node in enumerate(nodes):
            if i < len(nodes_with_pos):
                node.position = nodes_with_pos[i].get('position')

        return LineageGraph(
            iteration_id=iteration_id,
            nodes=nodes,
            edges=edges
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load lineage graph: {str(e)}")


@router.get("/graph/{iteration_id}/contracts", response_model=List[ContractPoint])
async def get_contract_points(iteration_id: str) -> List[ContractPoint]:
    """
    Get all contract points (INTERFACE nodes) with their lock status and dependents.
    """
    try:
        context = await load_execution_context(iteration_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Iteration {iteration_id} not found")

        workflow = await load_workflow_dag(context['workflow_id'])
        contract_points = []

        for node_id, node in workflow.nodes.items():
            if node.node_type == NodeType.INTERFACE:
                # Get dependents
                dependents = [
                    n_id for n_id, n in workflow.nodes.items()
                    if node_id in n.dependencies
                ]

                # Get artifacts
                artifacts = []
                node_state = context.get('node_states', {}).get(node_id, {})
                if node_state.get('artifacts'):
                    for artifact_path in node_state['artifacts']:
                        artifact_info = await load_artifact_metadata(artifact_path)
                        if artifact_info:
                            artifacts.append(artifact_info)

                # Get BDV scenario references (from contract tags)
                bdv_scenarios = await get_bdv_scenarios_for_contract(
                    f"{node_id.replace('IF.', '')}:{getattr(node, 'contract_version', 'v1.0')}"
                )

                contract_point = ContractPoint(
                    node_id=node_id,
                    contract_name=node_id.replace("IF.", ""),
                    contract_version=getattr(node, 'contract_version', 'v1.0'),
                    locked=is_contract_locked(context, node_id),
                    locked_at=get_contract_lock_time(context, node_id),
                    dependents=dependents,
                    artifacts=artifacts,
                    bdv_scenarios=bdv_scenarios
                )
                contract_points.append(contract_point)

        return contract_points

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load contract points: {str(e)}")


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@router.websocket("/execution/{iteration_id}/stream")
async def execution_stream(websocket: WebSocket, iteration_id: str):
    """
    WebSocket endpoint for real-time DDE execution updates.

    Emits events:
    - node_started, node_completed, node_failed, node_retry
    - gate_started, gate_passed, gate_failed
    - contract_locked
    - artifact_stamped
    """
    await websocket.accept()

    # Register connection
    if iteration_id not in active_connections:
        active_connections[iteration_id] = []
    active_connections[iteration_id].append(websocket)

    try:
        # Send initial state
        graph = await get_dde_graph(iteration_id, include_positions=False)
        await websocket.send_json({
            "type": "initial_state",
            "timestamp": datetime.utcnow().isoformat(),
            "data": graph.dict()
        })

        # Keep connection alive and listen for events
        while True:
            # Wait for messages from client (ping, subscribe, etc.)
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                if message == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})

    except WebSocketDisconnect:
        # Remove connection
        if iteration_id in active_connections:
            active_connections[iteration_id].remove(websocket)
            if not active_connections[iteration_id]:
                del active_connections[iteration_id]


async def broadcast_execution_event(iteration_id: str, event: Dict[str, Any]):
    """
    Broadcast execution event to all connected WebSocket clients.

    This should be called from the DAGExecutor event handler.
    """
    if iteration_id not in active_connections:
        return

    # Send to all connected clients
    dead_connections = []
    for websocket in active_connections[iteration_id]:
        try:
            await websocket.send_json(event)
        except Exception:
            dead_connections.append(websocket)

    # Clean up dead connections
    for websocket in dead_connections:
        active_connections[iteration_id].remove(websocket)


# ============================================================================
# Helper Functions
# ============================================================================

async def load_execution_context(iteration_id: str) -> Optional[Dict[str, Any]]:
    """Load execution context from storage"""
    # This should integrate with your existing WorkflowContextStore
    # For now, return stub data
    return {
        'iteration_id': iteration_id,
        'workflow_id': 'sample_workflow',
        'execution_status': 'running',
        'node_states': {},
        'created_at': datetime.utcnow().isoformat()
    }


async def load_workflow_dag(workflow_id: str) -> Optional[WorkflowDAG]:
    """Load workflow DAG definition"""
    # This should integrate with your existing workflow storage
    return None


async def load_artifact_metadata(artifact_path: str) -> Optional[ArtifactInfo]:
    """Load artifact metadata"""
    meta_path = Path(artifact_path).with_suffix(Path(artifact_path).suffix + ".meta.json")

    if not meta_path.exists():
        return None

    with open(meta_path) as f:
        meta = json.load(f)

    return ArtifactInfo(
        name=meta.get('artifact_name', Path(artifact_path).name),
        path=artifact_path,
        sha256=meta.get('sha256'),
        stamped_at=meta.get('timestamp'),
        size_bytes=meta.get('size_bytes')
    )


def extract_gate_status(node_state: Dict[str, Any], gate_name: str) -> GateStatus:
    """Extract gate status from node state"""
    # Look for gate results in validation_results
    validation = node_state.get('output', {}).get('validation_results', {})

    # Check policy validation
    policy_val = validation.get('policy_validation', {})
    if policy_val:
        for gate in policy_val.get('gates_failed', []):
            if gate.get('gate_name') == gate_name or gate.get('gate') == gate_name:
                return GateStatus(
                    name=gate_name,
                    status="failed",
                    severity=gate.get('severity', 'WARNING'),
                    message=gate.get('condition')
                )

    # Default to passed if node completed
    if node_state.get('status') == 'completed':
        return GateStatus(name=gate_name, status="passed", severity="INFO")

    return GateStatus(name=gate_name, status="pending", severity="INFO")


def is_contract_locked(context: Dict[str, Any], node_id: str) -> bool:
    """Check if interface contract is locked"""
    # Check if node is completed (contracts lock on completion)
    node_state = context.get('node_states', {}).get(node_id, {})
    return node_state.get('status') == 'completed'


def get_contract_lock_time(context: Dict[str, Any], node_id: str) -> Optional[str]:
    """Get contract lock timestamp"""
    node_state = context.get('node_states', {}).get(node_id, {})
    if is_contract_locked(context, node_id):
        return node_state.get('end_time')
    return None


def is_node_running(context: Dict[str, Any], node_id: str) -> bool:
    """Check if node is currently running"""
    node_state = context.get('node_states', {}).get(node_id, {})
    return node_state.get('status') == 'running'


def map_node_status(status: str) -> str:
    """Map internal status to graph status"""
    status_map = {
        'pending': 'pending',
        'ready': 'ready',
        'running': 'running',
        'completed': 'completed',
        'failed': 'failed',
        'skipped': 'skipped',
        'blocked': 'blocked'
    }
    return status_map.get(status, 'pending')


async def get_bdv_scenarios_for_contract(contract_ref: str) -> List[str]:
    """Get BDV scenarios that reference this contract"""
    # This will be implemented when we add BDV API
    # For now, return empty list
    return []


def calculate_graph_layout(
    nodes: List[Any],
    edges: List[Any],
    layout: str = "hierarchical"
) -> List[Any]:
    """
    Calculate auto-layout positions for graph nodes.

    Supports:
    - hierarchical: Top-down flow (good for DDE/BDV)
    - force: Force-directed layout (good for ACC)
    """
    import networkx as nx

    # Build NetworkX graph
    G = nx.DiGraph()

    for node in nodes:
        node_id = node['id'] if isinstance(node, dict) else node.id
        G.add_node(node_id)

    for edge in edges:
        source = edge['source'] if isinstance(edge, dict) else edge.source
        target = edge['target'] if isinstance(edge, dict) else edge.target
        G.add_edge(source, target)

    # Calculate positions based on layout type
    if layout == "hierarchical":
        # Use graphviz dot layout for hierarchical
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        except:
            # Fallback to spring layout
            pos = nx.spring_layout(G, k=2, iterations=50)
    else:
        # Force-directed layout
        pos = nx.spring_layout(G, k=1.5, iterations=50)

    # Scale positions to reasonable viewport
    if pos:
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        # Scale to 0-1000 range
        for node_id in pos:
            x = (pos[node_id][0] - x_min) / (x_max - x_min) * 1000 if x_max > x_min else 500
            y = (pos[node_id][1] - y_min) / (y_max - y_min) * 800 if y_max > y_min else 400
            pos[node_id] = (x, y)

    # Update nodes with positions
    for node in nodes:
        node_id = node['id'] if isinstance(node, dict) else node.id
        if node_id in pos:
            x, y = pos[node_id]
            if isinstance(node, dict):
                node['position'] = {'x': x, 'y': y}
            else:
                node.position = GraphPosition(x=x, y=y)

    return nodes


# ============================================================================
# Export
# ============================================================================

__all__ = [
    'router',
    'DDEGraph',
    'DDEGraphNode',
    'DDEGraphEdge',
    'ContractPoint',
    'LineageGraph',
    'broadcast_execution_event'
]
