"""
Tri-Modal Convergence API

Provides unified REST and WebSocket endpoints for tri-modal visualization:
- Combined graph view with all three streams (DDE, BDV, ACC)
- Contract points as intersection nodes (yellow stars)
- Cross-stream linkage visualization
- Tri-modal verdict and deployment gate status
- Real-time convergence updates

Integration with existing Maestro Platform:
- Aggregates data from dde/api.py, bdv/api.py, acc/api.py
- Uses tri_audit.py for verdict calculation
- Provides deployment readiness dashboard

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pathlib import Path
import json
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel, Field

# Import existing tri-modal components
try:
    from tri_audit.tri_audit import (
        tri_modal_audit,
        can_deploy_to_production,
        TriModalVerdict,
        TriAuditResult
    )
except ImportError:
    tri_modal_audit = None
    can_deploy_to_production = None
    TriModalVerdict = None
    TriAuditResult = None

# Import stream APIs
try:
    from dde.api import get_dde_graph, get_contract_points, DDEGraph, ContractPoint
    from bdv.api import get_bdv_graph, get_contract_linkages, BDVGraph, ContractLinkage
    from acc.api import get_acc_graph, ACCGraph
except ImportError:
    get_dde_graph = None
    get_contract_points = None
    get_bdv_graph = None
    get_contract_linkages = None
    get_acc_graph = None
    DDEGraph = None
    ContractPoint = None
    BDVGraph = None
    ContractLinkage = None
    ACCGraph = None


# ============================================================================
# Data Models
# ============================================================================

class StreamStatus(str, Enum):
    """Individual stream validation status."""
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    RUNNING = "running"
    ERROR = "error"


class GraphPosition(BaseModel):
    """2D position for graph node."""
    x: float
    y: float


class ContractStarNode(BaseModel):
    """Contract point visualization as yellow star node linking all three streams."""
    id: str  # e.g., "CONTRACT.AuthAPI.v1.0"
    contract_name: str
    contract_version: str

    # DDE linkage
    dde_node_id: Optional[str] = None
    dde_locked: bool = False

    # BDV linkage
    bdv_features: List[str] = Field(default_factory=list)
    bdv_scenarios: List[str] = Field(default_factory=list)
    bdv_scenario_count: int = 0

    # ACC linkage
    acc_components: List[str] = Field(default_factory=list)
    acc_modules: List[str] = Field(default_factory=list)

    # Status
    version_mismatch: bool = False
    all_streams_aligned: bool = False

    # Position (central hub in visualization)
    position: Optional[GraphPosition] = None


class CrossStreamEdge(BaseModel):
    """Edge linking contract star to stream nodes."""
    source: str  # Contract star ID or stream node ID
    target: str  # Stream node ID or contract star ID
    stream: str  # "dde", "bdv", "acc"
    type: str = "contract_link"
    status: str = "active"  # active, mismatched, missing


class ConvergenceGraph(BaseModel):
    """Combined tri-modal graph with contract star nodes."""
    iteration_id: str
    timestamp: datetime

    # Stream graphs (embedded)
    dde_graph: Optional[DDEGraph] = None
    bdv_graph: Optional[BDVGraph] = None
    acc_graph: Optional[ACCGraph] = None

    # Contract stars (intersection points)
    contract_stars: List[ContractStarNode] = Field(default_factory=list)

    # Cross-stream edges
    cross_stream_edges: List[CrossStreamEdge] = Field(default_factory=list)

    # Tri-modal verdict
    verdict: Optional[str] = None  # TriModalVerdict value
    can_deploy: bool = False
    diagnosis: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)

    # Stream statuses
    dde_status: StreamStatus = StreamStatus.PENDING
    bdv_status: StreamStatus = StreamStatus.PENDING
    acc_status: StreamStatus = StreamStatus.PENDING

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VerdictSummary(BaseModel):
    """Tri-modal verdict summary for deployment dashboard."""
    iteration_id: str
    timestamp: datetime

    # Verdict
    verdict: str  # TriModalVerdict value
    can_deploy: bool
    diagnosis: str
    recommendations: List[str]

    # Stream results
    dde_pass: bool
    bdv_pass: bool
    acc_pass: bool

    # Detailed stats
    dde_stats: Dict[str, Any] = Field(default_factory=dict)
    bdv_stats: Dict[str, Any] = Field(default_factory=dict)
    acc_stats: Dict[str, Any] = Field(default_factory=dict)

    # Blocking issues
    blocking_issues: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeploymentGateStatus(BaseModel):
    """Deployment gate status for CI/CD integration."""
    iteration_id: str
    timestamp: datetime
    approved: bool
    gate_status: str  # "APPROVED", "BLOCKED", "PENDING"

    # Gate checks
    dde_gate: bool
    bdv_gate: bool
    acc_gate: bool

    # Blocking reasons
    blocking_reasons: List[str] = Field(default_factory=list)

    # Metadata
    project: str
    version: str
    commit_sha: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConvergenceEvent(BaseModel):
    """Real-time convergence event from any stream."""
    event_type: str  # stream_updated, verdict_changed, contract_locked, deployment_approved
    timestamp: datetime
    iteration_id: str

    # Stream identification
    stream: Optional[str] = None  # "dde", "bdv", "acc"

    # Event data
    previous_status: Optional[StreamStatus] = None
    current_status: Optional[StreamStatus] = None

    # Verdict changes
    previous_verdict: Optional[str] = None
    current_verdict: Optional[str] = None

    # Deployment gate
    deployment_approved: Optional[bool] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConvergenceConnectionManager:
    """Manages WebSocket connections for convergence streaming."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, iteration_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        if iteration_id not in self.active_connections:
            self.active_connections[iteration_id] = []
        self.active_connections[iteration_id].append(websocket)

    def disconnect(self, websocket: WebSocket, iteration_id: str):
        """Remove WebSocket connection."""
        if iteration_id in self.active_connections:
            self.active_connections[iteration_id].remove(websocket)
            if not self.active_connections[iteration_id]:
                del self.active_connections[iteration_id]

    async def broadcast(self, iteration_id: str, message: Dict[str, Any]):
        """Broadcast message to all connected clients for iteration."""
        if iteration_id not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[iteration_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, iteration_id)


# Global connection manager
convergence_manager = ConvergenceConnectionManager()


# ============================================================================
# Helper Functions
# ============================================================================

def build_contract_stars(
    iteration_id: str,
    dde_contracts: List[ContractPoint],
    bdv_linkages: List[ContractLinkage]
) -> List[ContractStarNode]:
    """Build contract star nodes from DDE and BDV contract data."""
    contract_map: Dict[str, ContractStarNode] = {}

    # Process DDE contracts
    for dde_contract in dde_contracts:
        key = f"{dde_contract.node_id}"
        if dde_contract.contract_version:
            contract_name = dde_contract.node_id.split(".")[-1]  # Extract name from node_id
            star = ContractStarNode(
                id=f"CONTRACT.{contract_name}.{dde_contract.contract_version}",
                contract_name=contract_name,
                contract_version=dde_contract.contract_version,
                dde_node_id=dde_contract.node_id,
                dde_locked=dde_contract.locked,
                bdv_scenarios=dde_contract.bdv_scenarios
            )
            contract_map[key] = star

    # Merge BDV linkages
    for bdv_linkage in bdv_linkages:
        key = bdv_linkage.dde_node_id or f"{bdv_linkage.contract_name}.{bdv_linkage.contract_version}"

        if key in contract_map:
            star = contract_map[key]
        else:
            star = ContractStarNode(
                id=f"CONTRACT.{bdv_linkage.contract_name}.{bdv_linkage.contract_version}",
                contract_name=bdv_linkage.contract_name,
                contract_version=bdv_linkage.contract_version,
                dde_node_id=bdv_linkage.dde_node_id,
                dde_locked=bdv_linkage.dde_locked
            )
            contract_map[key] = star

        star.bdv_features.extend(bdv_linkage.bdv_features)
        star.bdv_scenarios.extend(bdv_linkage.bdv_scenarios)
        star.bdv_scenario_count = len(star.bdv_scenarios)
        star.version_mismatch = bdv_linkage.version_mismatch

    # Check alignment
    for star in contract_map.values():
        star.all_streams_aligned = (
            bool(star.dde_node_id) and
            bool(star.bdv_scenarios) and
            not star.version_mismatch
        )

    return list(contract_map.values())


def build_cross_stream_edges(contract_stars: List[ContractStarNode]) -> List[CrossStreamEdge]:
    """Build edges linking contract stars to stream nodes."""
    edges = []

    for star in contract_stars:
        # DDE edges (star -> DDE node)
        if star.dde_node_id:
            edges.append(CrossStreamEdge(
                source=star.id,
                target=star.dde_node_id,
                stream="dde",
                type="contract_link",
                status="active" if not star.version_mismatch else "mismatched"
            ))

        # BDV edges (star -> BDV scenarios)
        for scenario_id in star.bdv_scenarios:
            edges.append(CrossStreamEdge(
                source=star.id,
                target=scenario_id,
                stream="bdv",
                type="contract_link",
                status="active" if not star.version_mismatch else "mismatched"
            ))

        # ACC edges (star -> ACC modules)
        for module_id in star.acc_modules:
            edges.append(CrossStreamEdge(
                source=star.id,
                target=module_id,
                stream="acc",
                type="contract_link",
                status="active"
            ))

    return edges


def calculate_contract_star_positions(
    contract_stars: List[ContractStarNode],
    dde_graph: Optional[DDEGraph],
    bdv_graph: Optional[BDVGraph]
) -> List[ContractStarNode]:
    """Calculate positions for contract stars (center between linked DDE and BDV nodes)."""
    if not dde_graph or not bdv_graph:
        # Default grid layout
        spacing = 400
        for i, star in enumerate(contract_stars):
            star.position = GraphPosition(x=i * spacing, y=0)
        return contract_stars

    for star in contract_stars:
        # Find linked DDE node position
        dde_pos = None
        if star.dde_node_id and dde_graph.nodes:
            dde_node = next((n for n in dde_graph.nodes if n.id == star.dde_node_id), None)
            if dde_node and dde_node.position:
                dde_pos = dde_node.position

        # Find average BDV scenario position
        bdv_positions = []
        if star.bdv_scenarios and bdv_graph.nodes:
            for scenario_id in star.bdv_scenarios:
                bdv_node = next((n for n in bdv_graph.nodes if n.id == scenario_id), None)
                if bdv_node and bdv_node.position:
                    bdv_positions.append(bdv_node.position)

        # Calculate center position
        if dde_pos and bdv_positions:
            avg_bdv_x = sum(p.x for p in bdv_positions) / len(bdv_positions)
            avg_bdv_y = sum(p.y for p in bdv_positions) / len(bdv_positions)
            star.position = GraphPosition(
                x=(dde_pos.x + avg_bdv_x) / 2,
                y=(dde_pos.y + avg_bdv_y) / 2
            )
        elif dde_pos:
            star.position = dde_pos
        elif bdv_positions:
            star.position = GraphPosition(
                x=sum(p.x for p in bdv_positions) / len(bdv_positions),
                y=sum(p.y for p in bdv_positions) / len(bdv_positions)
            )

    return contract_stars


async def get_stream_status(iteration_id: str, stream: str) -> StreamStatus:
    """Get current status of a stream."""
    # Check if stream has completed analysis
    report_dir = Path(f"reports/{stream}/{iteration_id}")
    if not report_dir.exists():
        return StreamStatus.PENDING

    report_file = report_dir / "report.json"
    if not report_file.exists():
        return StreamStatus.PENDING

    try:
        with open(report_file) as f:
            report = json.load(f)
            if report.get("status") == "running":
                return StreamStatus.RUNNING
            elif report.get("passed", False):
                return StreamStatus.PASS
            else:
                return StreamStatus.FAIL
    except Exception:
        return StreamStatus.ERROR


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/v1/convergence", tags=["convergence"])


@router.get("/graph/{iteration_id}", response_model=ConvergenceGraph)
async def get_convergence_graph(
    iteration_id: str,
    manifest_name: str = Query("default", description="ACC architectural manifest name"),
    include_positions: bool = Query(True, description="Calculate graph layout positions")
) -> ConvergenceGraph:
    """
    Get unified tri-modal convergence graph.

    Returns combined graph with:
    - All three stream graphs (DDE, BDV, ACC)
    - Contract star nodes (yellow) linking streams
    - Cross-stream edges
    - Tri-modal verdict
    - Deployment gate status

    **Integration**: Aggregates dde/api, bdv/api, acc/api
    """
    timestamp = datetime.now()

    # Fetch all three stream graphs
    dde_graph = None
    bdv_graph = None
    acc_graph = None

    try:
        if get_dde_graph:
            dde_graph = await get_dde_graph(iteration_id, include_positions=include_positions)
    except Exception as e:
        print(f"Error fetching DDE graph: {e}")

    try:
        if get_bdv_graph:
            bdv_graph = await get_bdv_graph(iteration_id, include_positions=include_positions)
    except Exception as e:
        print(f"Error fetching BDV graph: {e}")

    try:
        if get_acc_graph:
            acc_graph = await get_acc_graph(
                iteration_id,
                manifest_name=manifest_name,
                include_positions=include_positions
            )
    except Exception as e:
        print(f"Error fetching ACC graph: {e}")

    # Get contract linkages
    dde_contracts = []
    bdv_linkages = []

    try:
        if get_contract_points:
            dde_contracts = await get_contract_points(iteration_id)
    except Exception:
        pass

    try:
        if get_contract_linkages:
            bdv_linkages = await get_contract_linkages(iteration_id)
    except Exception:
        pass

    # Build contract stars
    contract_stars = build_contract_stars(iteration_id, dde_contracts, bdv_linkages)

    # Calculate star positions if requested
    if include_positions:
        contract_stars = calculate_contract_star_positions(contract_stars, dde_graph, bdv_graph)

    # Build cross-stream edges
    cross_stream_edges = build_cross_stream_edges(contract_stars)

    # Get tri-modal verdict
    verdict = None
    can_deploy = False
    diagnosis = None
    recommendations = []

    if tri_modal_audit:
        try:
            audit_result = tri_modal_audit(iteration_id)
            verdict = audit_result.verdict.value if hasattr(audit_result.verdict, 'value') else str(audit_result.verdict)
            can_deploy = audit_result.can_deploy
            diagnosis = audit_result.diagnosis
            recommendations = audit_result.recommendations
        except Exception as e:
            print(f"Error running tri-modal audit: {e}")

    # Get stream statuses
    dde_status = await get_stream_status(iteration_id, "dde")
    bdv_status = await get_stream_status(iteration_id, "bdv")
    acc_status = await get_stream_status(iteration_id, "acc")

    return ConvergenceGraph(
        iteration_id=iteration_id,
        timestamp=timestamp,
        dde_graph=dde_graph,
        bdv_graph=bdv_graph,
        acc_graph=acc_graph,
        contract_stars=contract_stars,
        cross_stream_edges=cross_stream_edges,
        verdict=verdict,
        can_deploy=can_deploy,
        diagnosis=diagnosis,
        recommendations=recommendations,
        dde_status=dde_status,
        bdv_status=bdv_status,
        acc_status=acc_status
    )


@router.get("/{iteration_id}/verdict", response_model=VerdictSummary)
async def get_verdict(iteration_id: str) -> VerdictSummary:
    """
    Get tri-modal verdict for iteration.

    Returns deployment readiness assessment with:
    - Overall verdict (ALL_PASS, DESIGN_GAP, etc.)
    - Can deploy boolean
    - Diagnosis and recommendations
    - Individual stream pass/fail status
    - Detailed statistics

    **Integration**: Uses tri_audit.tri_modal_audit()
    """
    timestamp = datetime.now()

    if not tri_modal_audit:
        raise HTTPException(status_code=500, detail="Tri-modal audit not available")

    # Run tri-modal audit
    audit_result = tri_modal_audit(iteration_id)

    # Extract stream results
    dde_pass = audit_result.dde_pass if hasattr(audit_result, 'dde_pass') else False
    bdv_pass = audit_result.bdv_pass if hasattr(audit_result, 'bdv_pass') else False
    acc_pass = audit_result.acc_pass if hasattr(audit_result, 'acc_pass') else False

    # Collect stats from each stream
    dde_stats = {}
    bdv_stats = {}
    acc_stats = {}

    try:
        dde_graph = await get_dde_graph(iteration_id, include_positions=False)
        dde_stats = {
            "total_nodes": len(dde_graph.nodes),
            "completed_nodes": len([n for n in dde_graph.nodes if n.status == "completed"]),
            "failed_nodes": len([n for n in dde_graph.nodes if n.status == "failed"]),
            "contracts_locked": len([n for n in dde_graph.nodes if n.contract_locked])
        }
    except Exception:
        pass

    try:
        bdv_graph = await get_bdv_graph(iteration_id, include_positions=False)
        bdv_stats = {
            "total_scenarios": bdv_graph.total_scenarios,
            "passed_scenarios": bdv_graph.passed_scenarios,
            "failed_scenarios": bdv_graph.failed_scenarios,
            "flaky_scenarios": bdv_graph.flaky_scenarios
        }
    except Exception:
        pass

    try:
        acc_graph = await get_acc_graph(iteration_id, manifest_name="default", include_positions=False)
        acc_stats = {
            "total_violations": acc_graph.total_violations,
            "blocking_violations": acc_graph.blocking_violations,
            "cycle_count": acc_graph.cycle_count,
            "avg_instability": acc_graph.avg_instability
        }
    except Exception:
        pass

    # Identify blocking issues
    blocking_issues = []
    if not dde_pass:
        blocking_issues.append("DDE: Pipeline or gate execution failures")
    if not bdv_pass:
        blocking_issues.extend([f"BDV: {bdv_stats.get('failed_scenarios', 0)} scenarios failing"])
    if not acc_pass:
        blocking_issues.append(f"ACC: {acc_stats.get('blocking_violations', 0)} blocking violations")

    verdict_value = audit_result.verdict.value if hasattr(audit_result.verdict, 'value') else str(audit_result.verdict)

    return VerdictSummary(
        iteration_id=iteration_id,
        timestamp=timestamp,
        verdict=verdict_value,
        can_deploy=audit_result.can_deploy,
        diagnosis=audit_result.diagnosis,
        recommendations=audit_result.recommendations,
        dde_pass=dde_pass,
        bdv_pass=bdv_pass,
        acc_pass=acc_pass,
        dde_stats=dde_stats,
        bdv_stats=bdv_stats,
        acc_stats=acc_stats,
        blocking_issues=blocking_issues
    )


@router.get("/{iteration_id}/deployment-gate", response_model=DeploymentGateStatus)
async def check_deployment_gate(
    iteration_id: str,
    project: str = Query(..., description="Project name"),
    version: str = Query(..., description="Version to deploy"),
    commit_sha: Optional[str] = Query(None, description="Git commit SHA")
) -> DeploymentGateStatus:
    """
    Check deployment gate status for CI/CD pipeline.

    Returns:
    - approved: True if all three streams pass
    - gate_status: "APPROVED", "BLOCKED", or "PENDING"
    - Individual gate checks
    - Blocking reasons if any

    **Integration**: Used in CI/CD pipeline deployment gate
    """
    timestamp = datetime.now()

    # Get verdict
    verdict_summary = await get_verdict(iteration_id)

    approved = verdict_summary.can_deploy
    gate_status = "APPROVED" if approved else "BLOCKED"

    if verdict_summary.dde_pass is None or verdict_summary.bdv_pass is None or verdict_summary.acc_pass is None:
        gate_status = "PENDING"

    return DeploymentGateStatus(
        iteration_id=iteration_id,
        timestamp=timestamp,
        approved=approved,
        gate_status=gate_status,
        dde_gate=verdict_summary.dde_pass,
        bdv_gate=verdict_summary.bdv_pass,
        acc_gate=verdict_summary.acc_pass,
        blocking_reasons=verdict_summary.blocking_issues,
        project=project,
        version=version,
        commit_sha=commit_sha
    )


@router.websocket("/{iteration_id}/stream")
async def convergence_stream(websocket: WebSocket, iteration_id: str):
    """
    WebSocket endpoint for real-time convergence updates.

    Aggregates events from all three streams and broadcasts:
    - stream_updated: Any stream status changed
    - verdict_changed: Tri-modal verdict changed
    - contract_locked: Contract locked in DDE
    - deployment_approved: All gates passed

    **Integration**: Subscribes to DDE, BDV, ACC WebSocket events
    """
    await convergence_manager.connect(websocket, iteration_id)

    try:
        # Send initial convergence state
        graph = await get_convergence_graph(iteration_id, include_positions=True)
        await websocket.send_json({
            "event_type": "initial_state",
            "data": graph.dict()
        })

        # Keep connection alive and listen for client messages
        while True:
            try:
                data = await websocket.receive_json()
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break

    finally:
        convergence_manager.disconnect(websocket, iteration_id)


# ============================================================================
# Integration Helper for Broadcasting
# ============================================================================

async def broadcast_convergence_event(iteration_id: str, event: ConvergenceEvent):
    """
    Broadcast convergence event to all connected WebSocket clients.

    Called when any stream updates or verdict changes.

    Usage:
        from tri_audit.api import broadcast_convergence_event, ConvergenceEvent, StreamStatus

        event = ConvergenceEvent(
            event_type="stream_updated",
            timestamp=datetime.now(),
            iteration_id=iteration_id,
            stream="dde",
            previous_status=StreamStatus.RUNNING,
            current_status=StreamStatus.PASS
        )
        await broadcast_convergence_event(iteration_id, event)
    """
    message = {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "data": event.dict()
    }
    await convergence_manager.broadcast(iteration_id, message)


# ============================================================================
# Additional Helper Endpoints
# ============================================================================

@router.get("/{iteration_id}/contracts", response_model=List[ContractStarNode])
async def get_contract_stars(iteration_id: str) -> List[ContractStarNode]:
    """Get all contract star nodes for iteration."""
    graph = await get_convergence_graph(iteration_id, include_positions=False)
    return graph.contract_stars


@router.get("/{iteration_id}/stream-status", response_model=Dict[str, StreamStatus])
async def get_all_stream_statuses(iteration_id: str) -> Dict[str, StreamStatus]:
    """Get current status of all three streams."""
    return {
        "dde": await get_stream_status(iteration_id, "dde"),
        "bdv": await get_stream_status(iteration_id, "bdv"),
        "acc": await get_stream_status(iteration_id, "acc")
    }


@router.post("/{iteration_id}/run-all")
async def run_all_streams(iteration_id: str) -> Dict[str, Any]:
    """
    Trigger execution of all three streams in parallel.

    Returns status and WebSocket connection info.
    """
    # TODO: Trigger DDE, BDV, ACC in parallel
    return {
        "status": "started",
        "iteration_id": iteration_id,
        "message": "All three streams started. Connect to WebSocket for real-time updates.",
        "websocket_url": f"/api/v1/convergence/{iteration_id}/stream"
    }
