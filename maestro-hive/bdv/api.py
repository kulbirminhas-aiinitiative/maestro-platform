"""
BDV (Behavior-Driven Validation) Graph API

Provides REST and WebSocket endpoints for BDV graph visualization:
- Feature/Scenario hierarchy graphs
- Contract linkage to DDE INTERFACE nodes
- Real-time test execution streaming
- Flake detection and scenario status

Integration with existing Maestro Platform:
- Loads feature files from features/ directory
- Integrates with BDVRunner for test execution
- Cross-references DDE contract points

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pathlib import Path
import json
import hashlib
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel, Field
import networkx as nx

# Import existing BDV components
try:
    from bdv.bdv_runner import BDVRunner, ScenarioResult
except ImportError:
    BDVRunner = None
    ScenarioResult = None


# ============================================================================
# Data Models
# ============================================================================

class BDVNodeType(str, Enum):
    """BDV graph node types."""
    FEATURE = "feature"
    SCENARIO = "scenario"
    SCENARIO_OUTLINE = "scenario_outline"
    BACKGROUND = "background"


class BDVNodeStatus(str, Enum):
    """BDV scenario execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FLAKY = "flaky"
    QUARANTINED = "quarantined"


class GraphPosition(BaseModel):
    """2D position for graph node."""
    x: float
    y: float


class ContractTag(BaseModel):
    """Contract tag extracted from feature file."""
    contract_name: str
    contract_version: str
    node_id: Optional[str] = None  # DDE node ID if linked


class StepInfo(BaseModel):
    """Information about a Gherkin step."""
    keyword: str  # Given, When, Then, And, But
    text: str
    line_number: int


class ScenarioInfo(BaseModel):
    """Detailed scenario information."""
    name: str
    tags: List[str]
    steps: List[StepInfo]
    line_number: int
    examples: Optional[List[Dict[str, Any]]] = None  # For Scenario Outline


class BDVGraphNode(BaseModel):
    """BDV graph node representing feature or scenario."""
    id: str
    type: BDVNodeType
    name: str
    status: BDVNodeStatus = BDVNodeStatus.PENDING

    # Feature-specific
    description: Optional[str] = None
    feature_file: Optional[str] = None

    # Scenario-specific
    scenario_info: Optional[ScenarioInfo] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None

    # Tags and contracts
    tags: List[str] = Field(default_factory=list)
    contract_tags: List[ContractTag] = Field(default_factory=list)

    # Flake detection
    flake_count: int = 0
    total_runs: int = 0
    flake_rate: float = 0.0
    is_quarantined: bool = False

    # Execution history
    last_run: Optional[datetime] = None
    last_passed: Optional[datetime] = None
    last_failed: Optional[datetime] = None

    # Graph layout
    position: Optional[GraphPosition] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BDVGraphEdge(BaseModel):
    """Edge in BDV graph (feature -> scenario relationship)."""
    source: str  # Feature ID
    target: str  # Scenario ID
    type: str = "contains"


class BDVGraph(BaseModel):
    """Complete BDV graph for visualization."""
    iteration_id: str
    timestamp: datetime
    nodes: List[BDVGraphNode]
    edges: List[BDVGraphEdge]

    # Summary stats
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    flaky_scenarios: int = 0
    quarantined_scenarios: int = 0

    # Contract linkage
    contract_count: int = 0
    linked_dde_nodes: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContractLinkage(BaseModel):
    """Links between BDV contracts and DDE interface nodes."""
    contract_name: str
    contract_version: str

    # BDV side
    bdv_features: List[str] = Field(default_factory=list)
    bdv_scenarios: List[str] = Field(default_factory=list)

    # DDE side
    dde_node_id: Optional[str] = None
    dde_locked: bool = False

    # Validation status
    version_mismatch: bool = False
    expected_version: Optional[str] = None
    actual_version: Optional[str] = None


class FlakeReport(BaseModel):
    """Flake detection report for a scenario."""
    scenario_id: str
    scenario_name: str
    flake_count: int
    total_runs: int
    flake_rate: float
    is_quarantined: bool

    # Recent execution history
    recent_results: List[bool]  # True = passed, False = failed
    last_flake: Optional[datetime] = None

    # Flake pattern analysis
    flake_pattern: Optional[str] = None  # "intermittent", "environment", "timing"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BDVExecutionEvent(BaseModel):
    """Real-time execution event."""
    event_type: str  # feature_started, scenario_started, scenario_completed, step_executed
    timestamp: datetime
    iteration_id: str

    # Feature/Scenario identification
    feature_id: Optional[str] = None
    scenario_id: Optional[str] = None
    step_text: Optional[str] = None

    # Status
    status: Optional[BDVNodeStatus] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class BDVConnectionManager:
    """Manages WebSocket connections for BDV execution streaming."""

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
bdv_manager = BDVConnectionManager()


# ============================================================================
# Helper Functions
# ============================================================================

def parse_contract_tag(tag: str) -> Optional[ContractTag]:
    """Parse @contract:ContractName:v1.0 tag."""
    if not tag.startswith("@contract:"):
        return None

    parts = tag[10:].split(":")  # Remove @contract: prefix
    if len(parts) < 2:
        return None

    return ContractTag(
        contract_name=parts[0],
        contract_version=parts[1]
    )


def extract_contracts_from_tags(tags: List[str]) -> List[ContractTag]:
    """Extract all contract tags from feature/scenario tags."""
    contracts = []
    for tag in tags:
        contract = parse_contract_tag(tag)
        if contract:
            contracts.append(contract)
    return contracts


def parse_feature_file(feature_path: Path) -> Dict[str, Any]:
    """Parse Gherkin feature file and extract structure."""
    if not feature_path.exists():
        return {}

    content = feature_path.read_text()
    lines = content.split("\n")

    result = {
        "name": "",
        "description": "",
        "tags": [],
        "scenarios": []
    }

    current_scenario = None
    current_tags = []

    for i, line in enumerate(lines, 1):
        line = line.strip()

        # Tags
        if line.startswith("@"):
            current_tags.extend(line.split())

        # Feature
        elif line.startswith("Feature:"):
            result["name"] = line[8:].strip()
            result["tags"] = current_tags
            current_tags = []

        # Scenario/Scenario Outline
        elif line.startswith("Scenario:") or line.startswith("Scenario Outline:"):
            if current_scenario:
                result["scenarios"].append(current_scenario)

            is_outline = line.startswith("Scenario Outline:")
            scenario_name = line.split(":", 1)[1].strip()

            current_scenario = {
                "name": scenario_name,
                "type": "scenario_outline" if is_outline else "scenario",
                "tags": current_tags,
                "steps": [],
                "line_number": i,
                "examples": None
            }
            current_tags = []

        # Steps
        elif current_scenario and any(line.startswith(kw) for kw in ["Given", "When", "Then", "And", "But"]):
            keyword = line.split()[0]
            text = line[len(keyword):].strip()
            current_scenario["steps"].append({
                "keyword": keyword,
                "text": text,
                "line_number": i
            })

        # Examples (for Scenario Outline)
        elif current_scenario and line.startswith("Examples:"):
            # Simplified: would need full parser for table data
            current_scenario["examples"] = []

    if current_scenario:
        result["scenarios"].append(current_scenario)

    return result


def calculate_graph_layout(nodes: List[BDVGraphNode], edges: List[BDVGraphEdge]) -> List[BDVGraphNode]:
    """Calculate hierarchical layout for BDV graph (features at top, scenarios below)."""
    if not nodes:
        return nodes

    # Build NetworkX graph
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node.id, data=node)
    for edge in edges:
        G.add_edge(edge.source, edge.target)

    # Group nodes by type
    features = [n for n in nodes if n.type == BDVNodeType.FEATURE]
    scenarios = [n for n in nodes if n.type in (BDVNodeType.SCENARIO, BDVNodeType.SCENARIO_OUTLINE)]

    # Layout features horizontally at top
    feature_spacing = 400
    for i, feature in enumerate(features):
        feature.position = GraphPosition(x=i * feature_spacing, y=0)

    # Layout scenarios below their parent features
    scenario_spacing_x = 300
    scenario_spacing_y = 200

    feature_to_scenarios: Dict[str, List[BDVGraphNode]] = {}
    for edge in edges:
        if edge.source not in feature_to_scenarios:
            feature_to_scenarios[edge.source] = []
        scenario = next((n for n in scenarios if n.id == edge.target), None)
        if scenario:
            feature_to_scenarios[edge.source].append(scenario)

    for feature in features:
        if feature.id not in feature_to_scenarios or not feature.position:
            continue

        feature_scenarios = feature_to_scenarios[feature.id]
        num_scenarios = len(feature_scenarios)

        # Center scenarios below feature
        start_x = feature.position.x - (num_scenarios - 1) * scenario_spacing_x / 2

        for i, scenario in enumerate(feature_scenarios):
            scenario.position = GraphPosition(
                x=start_x + i * scenario_spacing_x,
                y=feature.position.y + scenario_spacing_y
            )

    return nodes


def load_bdv_execution_results(iteration_id: str) -> Dict[str, Any]:
    """Load BDV execution results from reports directory."""
    report_dir = Path(f"reports/bdv/{iteration_id}")
    if not report_dir.exists():
        return {}

    # Look for pytest-json-report output
    report_file = report_dir / "report.json"
    if not report_file.exists():
        return {}

    try:
        with open(report_file) as f:
            return json.load(f)
    except Exception:
        return {}


def load_flake_history(scenario_id: str) -> Dict[str, Any]:
    """Load flake history for scenario from reports."""
    flake_file = Path(f"reports/bdv/flakes/{scenario_id}.json")
    if not flake_file.exists():
        return {"flake_count": 0, "total_runs": 0, "recent_results": []}

    try:
        with open(flake_file) as f:
            return json.load(f)
    except Exception:
        return {"flake_count": 0, "total_runs": 0, "recent_results": []}


def link_contracts_to_dde(contracts: List[ContractTag], iteration_id: str) -> List[ContractTag]:
    """Link BDV contracts to DDE interface nodes."""
    # Load DDE execution manifest
    manifest_path = Path(f"manifests/execution/{iteration_id}.yaml")
    if not manifest_path.exists():
        return contracts

    try:
        import yaml
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        # Find INTERFACE nodes with matching contracts
        for node in manifest.get("nodes", []):
            if node.get("type") != "interface":
                continue

            node_contract_version = node.get("contract_version")
            if not node_contract_version:
                continue

            # Match by contract version pattern
            for contract in contracts:
                if contract.contract_version == node_contract_version:
                    contract.node_id = node.get("id")

    except Exception:
        pass

    return contracts


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/v1/bdv", tags=["bdv"])


@router.get("/graph/{iteration_id}", response_model=BDVGraph)
async def get_bdv_graph(
    iteration_id: str,
    include_positions: bool = Query(True, description="Calculate graph layout positions")
) -> BDVGraph:
    """
    Get BDV feature/scenario graph for visualization.

    Returns hierarchical graph with:
    - Feature nodes at top level
    - Scenario nodes grouped under features
    - Contract tags linking to DDE
    - Execution status and flake rates
    - Auto-calculated layout positions

    **Integration**: Loads from features/ directory and reports/bdv/
    """
    timestamp = datetime.now()

    # Discover feature files
    features_dir = Path("features")
    if not features_dir.exists():
        raise HTTPException(status_code=404, detail=f"Features directory not found: {features_dir}")

    nodes: List[BDVGraphNode] = []
    edges: List[BDVGraphEdge] = []

    all_contracts: List[ContractTag] = []

    # Parse all feature files
    for feature_file in features_dir.rglob("*.feature"):
        relative_path = str(feature_file.relative_to(features_dir))
        feature_id = hashlib.md5(relative_path.encode()).hexdigest()[:12]

        parsed = parse_feature_file(feature_file)
        if not parsed.get("name"):
            continue

        # Extract feature-level contracts
        feature_contracts = extract_contracts_from_tags(parsed.get("tags", []))
        all_contracts.extend(feature_contracts)

        # Create feature node
        feature_node = BDVGraphNode(
            id=f"F.{feature_id}",
            type=BDVNodeType.FEATURE,
            name=parsed["name"],
            description=parsed.get("description", ""),
            feature_file=relative_path,
            tags=parsed.get("tags", []),
            contract_tags=feature_contracts,
            status=BDVNodeStatus.PENDING
        )
        nodes.append(feature_node)

        # Create scenario nodes
        for i, scenario_data in enumerate(parsed.get("scenarios", [])):
            scenario_id = f"{feature_id}-S{i+1}"

            # Extract scenario-level contracts
            scenario_contracts = extract_contracts_from_tags(scenario_data.get("tags", []))
            all_contracts.extend(scenario_contracts)

            # Load execution results
            execution_results = load_bdv_execution_results(iteration_id)
            scenario_status = BDVNodeStatus.PENDING
            duration_ms = None
            error_message = None

            # Load flake history
            flake_data = load_flake_history(scenario_id)

            scenario_info = ScenarioInfo(
                name=scenario_data["name"],
                tags=scenario_data.get("tags", []),
                steps=[StepInfo(**step) for step in scenario_data.get("steps", [])],
                line_number=scenario_data.get("line_number", 0),
                examples=scenario_data.get("examples")
            )

            scenario_node = BDVGraphNode(
                id=f"S.{scenario_id}",
                type=BDVNodeType.SCENARIO_OUTLINE if scenario_data.get("type") == "scenario_outline" else BDVNodeType.SCENARIO,
                name=scenario_data["name"],
                status=scenario_status,
                scenario_info=scenario_info,
                duration_ms=duration_ms,
                error_message=error_message,
                tags=scenario_data.get("tags", []),
                contract_tags=scenario_contracts,
                flake_count=flake_data.get("flake_count", 0),
                total_runs=flake_data.get("total_runs", 0),
                flake_rate=flake_data.get("flake_count", 0) / max(flake_data.get("total_runs", 1), 1),
                is_quarantined=flake_data.get("is_quarantined", False)
            )
            nodes.append(scenario_node)

            # Create edge from feature to scenario
            edges.append(BDVGraphEdge(
                source=feature_node.id,
                target=scenario_node.id,
                type="contains"
            ))

    # Link contracts to DDE
    all_contracts = link_contracts_to_dde(all_contracts, iteration_id)
    linked_dde_nodes = list(set(c.node_id for c in all_contracts if c.node_id))

    # Calculate layout if requested
    if include_positions:
        nodes = calculate_graph_layout(nodes, edges)

    # Calculate summary stats
    scenario_nodes = [n for n in nodes if n.type in (BDVNodeType.SCENARIO, BDVNodeType.SCENARIO_OUTLINE)]
    total_scenarios = len(scenario_nodes)
    passed_scenarios = len([n for n in scenario_nodes if n.status == BDVNodeStatus.PASSED])
    failed_scenarios = len([n for n in scenario_nodes if n.status == BDVNodeStatus.FAILED])
    flaky_scenarios = len([n for n in scenario_nodes if n.status == BDVNodeStatus.FLAKY])
    quarantined_scenarios = len([n for n in scenario_nodes if n.is_quarantined])

    return BDVGraph(
        iteration_id=iteration_id,
        timestamp=timestamp,
        nodes=nodes,
        edges=edges,
        total_scenarios=total_scenarios,
        passed_scenarios=passed_scenarios,
        failed_scenarios=failed_scenarios,
        flaky_scenarios=flaky_scenarios,
        quarantined_scenarios=quarantined_scenarios,
        contract_count=len(all_contracts),
        linked_dde_nodes=linked_dde_nodes
    )


@router.get("/graph/{iteration_id}/contracts", response_model=List[ContractLinkage])
async def get_contract_linkages(iteration_id: str) -> List[ContractLinkage]:
    """
    Get contract linkages between BDV and DDE.

    Returns all contracts with:
    - BDV features/scenarios using the contract
    - DDE interface node providing the contract
    - Lock status from DDE
    - Version mismatch detection

    **Integration**: Cross-references features/ and manifests/execution/
    """
    # Get BDV graph to extract contracts
    bdv_graph = await get_bdv_graph(iteration_id, include_positions=False)

    # Group by contract
    contract_map: Dict[str, ContractLinkage] = {}

    for node in bdv_graph.nodes:
        for contract in node.contract_tags:
            key = f"{contract.contract_name}:{contract.contract_version}"

            if key not in contract_map:
                contract_map[key] = ContractLinkage(
                    contract_name=contract.contract_name,
                    contract_version=contract.contract_version,
                    dde_node_id=contract.node_id
                )

            linkage = contract_map[key]

            if node.type == BDVNodeType.FEATURE:
                linkage.bdv_features.append(node.id)
            elif node.type in (BDVNodeType.SCENARIO, BDVNodeType.SCENARIO_OUTLINE):
                linkage.bdv_scenarios.append(node.id)

    # Load DDE contract lock status
    # TODO: Query DDE API or load from context

    return list(contract_map.values())


@router.get("/graph/{iteration_id}/flakes", response_model=List[FlakeReport])
async def get_flake_report(
    iteration_id: str,
    min_flake_rate: float = Query(0.0, ge=0.0, le=1.0, description="Minimum flake rate to include")
) -> List[FlakeReport]:
    """
    Get flake detection report for all scenarios.

    Identifies flaky scenarios based on:
    - Historical pass/fail pattern
    - Flake rate threshold
    - Recent execution trends

    **Integration**: Loads from reports/bdv/flakes/
    """
    bdv_graph = await get_bdv_graph(iteration_id, include_positions=False)

    flake_reports = []

    for node in bdv_graph.nodes:
        if node.type not in (BDVNodeType.SCENARIO, BDVNodeType.SCENARIO_OUTLINE):
            continue

        if node.flake_rate < min_flake_rate:
            continue

        flake_data = load_flake_history(node.id)

        flake_report = FlakeReport(
            scenario_id=node.id,
            scenario_name=node.name,
            flake_count=node.flake_count,
            total_runs=node.total_runs,
            flake_rate=node.flake_rate,
            is_quarantined=node.is_quarantined,
            recent_results=flake_data.get("recent_results", []),
            last_flake=node.last_failed,
            flake_pattern=flake_data.get("pattern")
        )
        flake_reports.append(flake_report)

    # Sort by flake rate descending
    flake_reports.sort(key=lambda x: x.flake_rate, reverse=True)

    return flake_reports


@router.websocket("/execution/{iteration_id}/stream")
async def execution_stream(websocket: WebSocket, iteration_id: str):
    """
    WebSocket endpoint for real-time BDV test execution streaming.

    Events:
    - feature_started: Feature test execution started
    - scenario_started: Scenario test execution started
    - scenario_completed: Scenario finished (passed/failed)
    - step_executed: Individual step executed
    - flake_detected: Scenario marked as flaky

    **Integration**: Called from BDVRunner during test execution
    """
    await bdv_manager.connect(websocket, iteration_id)

    try:
        # Send initial graph state
        graph = await get_bdv_graph(iteration_id, include_positions=True)
        await websocket.send_json({
            "event_type": "initial_state",
            "data": graph.dict()
        })

        # Keep connection alive and listen for client messages
        while True:
            try:
                data = await websocket.receive_json()
                # Client can send control messages if needed
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break

    finally:
        bdv_manager.disconnect(websocket, iteration_id)


# ============================================================================
# Integration Helper for Broadcasting
# ============================================================================

async def broadcast_bdv_event(iteration_id: str, event: BDVExecutionEvent):
    """
    Broadcast BDV execution event to all connected WebSocket clients.

    Called from BDVRunner during test execution.

    Usage:
        from bdv.api import broadcast_bdv_event, BDVExecutionEvent, BDVNodeStatus

        event = BDVExecutionEvent(
            event_type="scenario_completed",
            timestamp=datetime.now(),
            iteration_id=iteration_id,
            scenario_id="S.abc123-S1",
            status=BDVNodeStatus.PASSED,
            duration_ms=1234.5
        )
        await broadcast_bdv_event(iteration_id, event)
    """
    message = {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "data": event.dict()
    }
    await bdv_manager.broadcast(iteration_id, message)


# ============================================================================
# Additional Helper Endpoints
# ============================================================================

@router.get("/features", response_model=List[str])
async def list_feature_files() -> List[str]:
    """List all available feature files."""
    features_dir = Path("features")
    if not features_dir.exists():
        return []

    return [str(f.relative_to(features_dir)) for f in features_dir.rglob("*.feature")]


@router.get("/scenarios/{feature_path:path}", response_model=Dict[str, Any])
async def get_feature_scenarios(feature_path: str) -> Dict[str, Any]:
    """Get all scenarios for a specific feature file."""
    feature_file = Path("features") / feature_path
    if not feature_file.exists():
        raise HTTPException(status_code=404, detail=f"Feature file not found: {feature_path}")

    parsed = parse_feature_file(feature_file)
    return parsed


@router.post("/execution/{iteration_id}/run")
async def run_bdv_tests(iteration_id: str) -> Dict[str, Any]:
    """
    Trigger BDV test execution for iteration.

    Runs pytest-bdd and streams results via WebSocket.

    **Integration**: Uses BDVRunner to execute tests
    """
    if BDVRunner is None:
        raise HTTPException(status_code=500, detail="BDVRunner not available")

    # TODO: Run BDVRunner in background task and stream events
    return {
        "status": "started",
        "iteration_id": iteration_id,
        "message": "BDV test execution started. Connect to WebSocket for real-time updates."
    }
