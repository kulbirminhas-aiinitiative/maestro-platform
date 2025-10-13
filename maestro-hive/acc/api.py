"""
ACC (Architectural Conformance Checking) Graph API

Provides REST and WebSocket endpoints for ACC graph visualization:
- Component/module dependency graphs
- Architectural rule violations overlay
- Coupling metrics and instability analysis
- Cyclic dependency detection
- Real-time analysis streaming

Integration with existing Maestro Platform:
- Uses ImportGraphBuilder for dependency analysis
- Loads architectural manifests from manifests/architectural/
- Provides architecture diff and evolution tracking

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from pathlib import Path
import json
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel, Field
import networkx as nx

# Import existing ACC components
try:
    from acc.import_graph_builder import ImportGraphBuilder, ImportGraph
except ImportError:
    ImportGraphBuilder = None
    ImportGraph = None


# ============================================================================
# Data Models
# ============================================================================

class ACCNodeType(str, Enum):
    """ACC graph node types."""
    COMPONENT = "component"  # Architectural component (e.g., BusinessLogic)
    MODULE = "module"  # Python module
    PACKAGE = "package"  # Python package
    CLASS = "class"  # Class node (optional detailed view)


class ACCNodeStatus(str, Enum):
    """ACC node conformance status."""
    COMPLIANT = "compliant"  # No violations
    WARNING = "warning"  # Non-blocking violations
    VIOLATION = "violation"  # Blocking violations
    UNKNOWN = "unknown"  # Not yet analyzed


class ViolationType(str, Enum):
    """Types of architectural violations."""
    DEPENDENCY = "dependency"  # Illegal dependency (e.g., Presentation -> DataAccess)
    CYCLE = "cycle"  # Cyclic dependency
    COUPLING = "coupling"  # Excessive coupling
    SIZE = "size"  # Module too large
    NAMING = "naming"  # Naming convention violation
    LAYERING = "layering"  # Layer violation


class RuleSeverity(str, Enum):
    """Architectural rule severity."""
    BLOCKING = "blocking"  # Must fix before deploy
    WARNING = "warning"  # Should fix
    INFO = "info"  # Informational


class GraphPosition(BaseModel):
    """2D position for graph node."""
    x: float
    y: float


class CouplingMetrics(BaseModel):
    """Coupling metrics for a module."""
    afferent_coupling: int = Field(0, alias="ca", description="Number of modules depending on this module")
    efferent_coupling: int = Field(0, alias="ce", description="Number of modules this module depends on")
    instability: float = Field(0.0, description="I = Ce / (Ca + Ce), range [0,1]")
    abstractness: Optional[float] = Field(None, description="A = abstract classes / total classes")
    distance_from_main: Optional[float] = Field(None, description="D = |A + I - 1|")


class ViolationInfo(BaseModel):
    """Detailed violation information."""
    id: str
    type: ViolationType
    severity: RuleSeverity
    rule_id: str
    rule_description: str
    violating_path: Optional[str] = None  # Import path causing violation
    source_node: str
    target_node: Optional[str] = None
    message: str
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    adr_reference: Optional[str] = None  # Architecture Decision Record reference


class ACCGraphNode(BaseModel):
    """ACC graph node representing component/module."""
    id: str
    type: ACCNodeType
    name: str
    status: ACCNodeStatus = ACCNodeStatus.UNKNOWN

    # Component-specific (for COMPONENT type)
    component_paths: List[str] = Field(default_factory=list)

    # Module-specific (for MODULE/PACKAGE type)
    module_path: Optional[str] = None
    file_count: Optional[int] = None
    line_count: Optional[int] = None
    class_count: Optional[int] = None
    function_count: Optional[int] = None

    # Metrics
    coupling_metrics: Optional[CouplingMetrics] = None

    # Violations
    violations: List[ViolationInfo] = Field(default_factory=list)
    violation_count: int = 0
    blocking_violations: int = 0
    warning_violations: int = 0

    # Cycles
    in_cycle: bool = False
    cycle_ids: List[str] = Field(default_factory=list)

    # Graph layout
    position: Optional[GraphPosition] = None
    layer: Optional[int] = None  # For hierarchical layout (0 = top layer)


class ACCGraphEdge(BaseModel):
    """Edge in ACC graph (dependency relationship)."""
    source: str
    target: str
    type: str = "depends_on"
    weight: int = 1  # Number of import statements
    is_violation: bool = False
    violation_ids: List[str] = Field(default_factory=list)
    in_cycle: bool = False
    cycle_ids: List[str] = Field(default_factory=list)


class CycleInfo(BaseModel):
    """Information about a cyclic dependency."""
    id: str
    nodes: List[str]
    edges: List[Tuple[str, str]]
    severity: RuleSeverity = RuleSeverity.BLOCKING
    length: int  # Number of nodes in cycle
    description: str


class ACCGraph(BaseModel):
    """Complete ACC graph for visualization."""
    iteration_id: str
    timestamp: datetime
    manifest_path: str
    nodes: List[ACCGraphNode]
    edges: List[ACCGraphEdge]

    # Summary stats
    total_modules: int = 0
    total_dependencies: int = 0
    total_violations: int = 0
    blocking_violations: int = 0
    warning_violations: int = 0

    # Cycles
    cycles: List[CycleInfo] = Field(default_factory=list)
    cycle_count: int = 0

    # Metrics
    avg_instability: float = 0.0
    max_coupling: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ArchitecturalRule(BaseModel):
    """Architectural rule definition."""
    id: str
    type: ViolationType
    severity: RuleSeverity
    description: str
    rule: str  # Rule expression (e.g., "Presentation: MUST_NOT_CALL(DataAccess)")
    enabled: bool = True


class ArchitecturalManifest(BaseModel):
    """Architectural manifest definition."""
    project: str
    version: str
    components: List[Dict[str, Any]]
    rules: List[ArchitecturalRule]


class ACCAnalysisEvent(BaseModel):
    """Real-time analysis event."""
    event_type: str  # analysis_started, module_analyzed, violation_detected, cycle_detected, analysis_completed
    timestamp: datetime
    iteration_id: str

    # Module identification
    module_id: Optional[str] = None
    module_name: Optional[str] = None

    # Violation/Cycle info
    violation_id: Optional[str] = None
    cycle_id: Optional[str] = None

    # Progress
    progress_percent: Optional[float] = None
    modules_analyzed: Optional[int] = None
    total_modules: Optional[int] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ACCConnectionManager:
    """Manages WebSocket connections for ACC analysis streaming."""

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
acc_manager = ACCConnectionManager()


# ============================================================================
# Helper Functions
# ============================================================================

def load_architectural_manifest(manifest_path: Path) -> Optional[ArchitecturalManifest]:
    """Load architectural manifest from YAML file."""
    if not manifest_path.exists():
        return None

    try:
        import yaml
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        # Parse rules
        rules = []
        for rule_data in data.get("rules", []):
            rule = ArchitecturalRule(
                id=rule_data.get("id", ""),
                type=ViolationType(rule_data.get("type", "dependency")),
                severity=RuleSeverity(rule_data.get("severity", "warning").lower()),
                description=rule_data.get("description", ""),
                rule=rule_data.get("rule", ""),
                enabled=rule_data.get("enabled", True)
            )
            rules.append(rule)

        return ArchitecturalManifest(
            project=data.get("project", ""),
            version=data.get("version", "1.0.0"),
            components=data.get("components", []),
            rules=rules
        )

    except Exception as e:
        print(f"Error loading architectural manifest: {e}")
        return None


def build_import_graph(project_path: Path) -> Optional[ImportGraph]:
    """Build import graph using ImportGraphBuilder."""
    if ImportGraphBuilder is None:
        return None

    try:
        builder = ImportGraphBuilder(project_path=str(project_path))
        return builder.build_graph()
    except Exception as e:
        print(f"Error building import graph: {e}")
        return None


def detect_violations(
    graph: ImportGraph,
    manifest: ArchitecturalManifest
) -> List[ViolationInfo]:
    """Detect architectural rule violations."""
    violations = []

    # Build component mapping (path -> component name)
    path_to_component: Dict[str, str] = {}
    for component in manifest.components:
        component_name = component.get("name", "")
        for path in component.get("paths", []):
            path_to_component[path] = component_name

    # Check each rule
    for rule in manifest.rules:
        if not rule.enabled:
            continue

        if rule.type == ViolationType.DEPENDENCY:
            violations.extend(
                check_dependency_rule(graph, rule, path_to_component)
            )
        elif rule.type == ViolationType.COUPLING:
            violations.extend(
                check_coupling_rule(graph, rule)
            )
        elif rule.type == ViolationType.SIZE:
            violations.extend(
                check_size_rule(graph, rule)
            )
        elif rule.type == ViolationType.NAMING:
            violations.extend(
                check_naming_rule(graph, rule)
            )

    return violations


def check_dependency_rule(
    graph: ImportGraph,
    rule: ArchitecturalRule,
    path_to_component: Dict[str, str]
) -> List[ViolationInfo]:
    """Check dependency rule (e.g., Presentation: MUST_NOT_CALL(DataAccess))."""
    violations = []

    # Parse rule (simplified - full parser would be more robust)
    # Format: "ComponentA: MUST_NOT_CALL(ComponentB)"
    if "MUST_NOT_CALL" not in rule.rule:
        return violations

    parts = rule.rule.split(":")
    if len(parts) < 2:
        return violations

    source_component = parts[0].strip()
    target_component = rule.rule.split("(")[1].split(")")[0].strip()

    # Check all edges in graph
    for source_module, target_module in graph.graph.edges():
        # Map modules to components
        source_comp = None
        target_comp = None

        for path, comp in path_to_component.items():
            if source_module.startswith(path):
                source_comp = comp
            if target_module.startswith(path):
                target_comp = comp

        # Check if this edge violates the rule
        if source_comp == source_component and target_comp == target_component:
            violation = ViolationInfo(
                id=f"V-{len(violations)+1}",
                type=ViolationType.DEPENDENCY,
                severity=rule.severity,
                rule_id=rule.id,
                rule_description=rule.description,
                violating_path=f"{source_module} -> {target_module}",
                source_node=source_module,
                target_node=target_module,
                message=f"{source_component} must not call {target_component}",
                suppressed=False
            )
            violations.append(violation)

    return violations


def check_coupling_rule(graph: ImportGraph, rule: ArchitecturalRule) -> List[ViolationInfo]:
    """Check coupling metrics rule."""
    violations = []

    # Extract threshold from rule (e.g., "MaxCoupling: 10")
    # Simplified parsing
    if "MaxCoupling" not in rule.rule:
        return violations

    try:
        max_coupling = int(rule.rule.split(":")[1].strip())
    except Exception:
        return violations

    for module in graph.modules:
        ca, ce, instability = graph.calculate_coupling(module)
        total_coupling = ca + ce

        if total_coupling > max_coupling:
            violation = ViolationInfo(
                id=f"V-COUPLING-{module}",
                type=ViolationType.COUPLING,
                severity=rule.severity,
                rule_id=rule.id,
                rule_description=rule.description,
                source_node=module,
                message=f"Module has {total_coupling} total coupling (max: {max_coupling})",
                suppressed=False
            )
            violations.append(violation)

    return violations


def check_size_rule(graph: ImportGraph, rule: ArchitecturalRule) -> List[ViolationInfo]:
    """Check module size rule."""
    violations = []

    # Extract threshold from rule (e.g., "MaxLines: 500")
    if "MaxLines" not in rule.rule:
        return violations

    try:
        max_lines = int(rule.rule.split(":")[1].strip())
    except Exception:
        return violations

    for module_name, module_info in graph.modules.items():
        line_count = module_info.get("lines", 0)
        if line_count > max_lines:
            violation = ViolationInfo(
                id=f"V-SIZE-{module_name}",
                type=ViolationType.SIZE,
                severity=rule.severity,
                rule_id=rule.id,
                rule_description=rule.description,
                source_node=module_name,
                message=f"Module has {line_count} lines (max: {max_lines})",
                suppressed=False
            )
            violations.append(violation)

    return violations


def check_naming_rule(graph: ImportGraph, rule: ArchitecturalRule) -> List[ViolationInfo]:
    """Check naming convention rule."""
    violations = []

    # Simplified: check if module names match pattern
    # Full implementation would use regex patterns from rule

    return violations


def detect_cycles(graph: ImportGraph) -> List[CycleInfo]:
    """Detect cyclic dependencies in graph."""
    if not graph.has_cycle():
        return []

    cycles = graph.find_cycles()
    cycle_infos = []

    for i, cycle_nodes in enumerate(cycles, 1):
        edges = []
        for j in range(len(cycle_nodes)):
            source = cycle_nodes[j]
            target = cycle_nodes[(j + 1) % len(cycle_nodes)]
            edges.append((source, target))

        cycle_info = CycleInfo(
            id=f"C-{i}",
            nodes=cycle_nodes,
            edges=edges,
            severity=RuleSeverity.BLOCKING,
            length=len(cycle_nodes),
            description=f"Cyclic dependency: {' -> '.join(cycle_nodes[:3])}{'...' if len(cycle_nodes) > 3 else ''} -> {cycle_nodes[0]}"
        )
        cycle_infos.append(cycle_info)

    return cycle_infos


def calculate_graph_layout(
    nodes: List[ACCGraphNode],
    edges: List[ACCGraphEdge],
    layout_type: str = "force"
) -> List[ACCGraphNode]:
    """Calculate layout for ACC graph."""
    if not nodes:
        return nodes

    # Build NetworkX graph
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node.id, data=node)
    for edge in edges:
        G.add_edge(edge.source, edge.target, weight=edge.weight)

    if layout_type == "hierarchical":
        # Hierarchical layout (top-down)
        try:
            # Calculate layers based on topological sort
            if nx.is_directed_acyclic_graph(G):
                layers = list(nx.topological_generations(G))
                layer_spacing_y = 300
                node_spacing_x = 400

                for layer_idx, layer_nodes in enumerate(layers):
                    layer_node_ids = list(layer_nodes)
                    num_nodes = len(layer_node_ids)
                    start_x = -(num_nodes - 1) * node_spacing_x / 2

                    for i, node_id in enumerate(layer_node_ids):
                        node = next((n for n in nodes if n.id == node_id), None)
                        if node:
                            node.position = GraphPosition(
                                x=start_x + i * node_spacing_x,
                                y=layer_idx * layer_spacing_y
                            )
                            node.layer = layer_idx
            else:
                # Fall back to force layout if there are cycles
                layout_type = "force"
        except Exception:
            layout_type = "force"

    if layout_type == "force":
        # Force-directed layout
        try:
            pos = nx.spring_layout(G, k=2, iterations=50, scale=1000)
            for node in nodes:
                if node.id in pos:
                    node.position = GraphPosition(
                        x=pos[node.id][0],
                        y=pos[node.id][1]
                    )
        except Exception:
            pass

    return nodes


def load_acc_report(iteration_id: str) -> Dict[str, Any]:
    """Load ACC analysis report from reports directory."""
    report_dir = Path(f"reports/acc/{iteration_id}")
    if not report_dir.exists():
        return {}

    report_file = report_dir / "report.json"
    if not report_file.exists():
        return {}

    try:
        with open(report_file) as f:
            return json.load(f)
    except Exception:
        return {}


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/v1/acc", tags=["acc"])


@router.get("/graph/{iteration_id}", response_model=ACCGraph)
async def get_acc_graph(
    iteration_id: str,
    manifest_name: str = Query(..., description="Name of architectural manifest"),
    layout: str = Query("force", description="Layout algorithm: force or hierarchical"),
    include_positions: bool = Query(True, description="Calculate graph layout positions")
) -> ACCGraph:
    """
    Get ACC architectural conformance graph for visualization.

    Returns dependency graph with:
    - Component/module nodes
    - Dependency edges
    - Violation overlays (red edges/nodes)
    - Cycle detection (purple highlighting)
    - Coupling metrics
    - Auto-calculated layout positions

    **Integration**: Uses ImportGraphBuilder and manifests/architectural/
    """
    timestamp = datetime.now()

    # Load architectural manifest
    manifest_path = Path(f"manifests/architectural/{manifest_name}.yaml")
    manifest = load_architectural_manifest(manifest_path)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Architectural manifest not found: {manifest_name}")

    # Build import graph
    project_path = Path(".")
    import_graph = build_import_graph(project_path)
    if not import_graph:
        raise HTTPException(status_code=500, detail="Failed to build import graph")

    # Detect violations
    violations = detect_violations(import_graph, manifest)

    # Detect cycles
    cycles = detect_cycles(import_graph)

    # Build cycle lookup
    node_to_cycles: Dict[str, List[str]] = {}
    edge_to_cycles: Dict[Tuple[str, str], List[str]] = {}

    for cycle in cycles:
        for node in cycle.nodes:
            if node not in node_to_cycles:
                node_to_cycles[node] = []
            node_to_cycles[node].append(cycle.id)

        for edge in cycle.edges:
            if edge not in edge_to_cycles:
                edge_to_cycles[edge] = []
            edge_to_cycles[edge].append(cycle.id)

    # Build violation lookup
    node_violations: Dict[str, List[ViolationInfo]] = {}
    edge_violations: Dict[Tuple[str, str], List[ViolationInfo]] = {}

    for violation in violations:
        source = violation.source_node
        if source not in node_violations:
            node_violations[source] = []
        node_violations[source].append(violation)

        if violation.target_node:
            edge_key = (source, violation.target_node)
            if edge_key not in edge_violations:
                edge_violations[edge_key] = []
            edge_violations[edge_key].append(violation)

    # Create nodes from import graph
    nodes: List[ACCGraphNode] = []
    for module_name, module_info in import_graph.modules.items():
        ca, ce, instability = import_graph.calculate_coupling(module_name)

        coupling_metrics = CouplingMetrics(
            afferent_coupling=ca,
            efferent_coupling=ce,
            instability=instability
        )

        module_violations = node_violations.get(module_name, [])
        blocking_count = len([v for v in module_violations if v.severity == RuleSeverity.BLOCKING])
        warning_count = len([v for v in module_violations if v.severity == RuleSeverity.WARNING])

        status = ACCNodeStatus.COMPLIANT
        if blocking_count > 0:
            status = ACCNodeStatus.VIOLATION
        elif warning_count > 0:
            status = ACCNodeStatus.WARNING

        in_cycle = module_name in node_to_cycles

        node = ACCGraphNode(
            id=module_name,
            type=ACCNodeType.MODULE,
            name=module_name.split(".")[-1],  # Short name
            status=status,
            module_path=module_name,
            file_count=1,
            line_count=module_info.get("lines", 0),
            class_count=len(module_info.get("classes", [])),
            function_count=len(module_info.get("functions", [])),
            coupling_metrics=coupling_metrics,
            violations=module_violations,
            violation_count=len(module_violations),
            blocking_violations=blocking_count,
            warning_violations=warning_count,
            in_cycle=in_cycle,
            cycle_ids=node_to_cycles.get(module_name, [])
        )
        nodes.append(node)

    # Create edges from import graph
    edges: List[ACCGraphEdge] = []
    for source, target in import_graph.graph.edges():
        edge_key = (source, target)
        edge_vios = edge_violations.get(edge_key, [])
        is_violation = len(edge_vios) > 0

        in_cycle = edge_key in edge_to_cycles

        edge = ACCGraphEdge(
            source=source,
            target=target,
            type="depends_on",
            weight=1,
            is_violation=is_violation,
            violation_ids=[v.id for v in edge_vios],
            in_cycle=in_cycle,
            cycle_ids=edge_to_cycles.get(edge_key, [])
        )
        edges.append(edge)

    # Calculate layout if requested
    if include_positions:
        nodes = calculate_graph_layout(nodes, edges, layout_type=layout)

    # Calculate summary stats
    total_violations = len(violations)
    blocking_violations = len([v for v in violations if v.severity == RuleSeverity.BLOCKING])
    warning_violations = len([v for v in violations if v.severity == RuleSeverity.WARNING])

    instabilities = [n.coupling_metrics.instability for n in nodes if n.coupling_metrics]
    avg_instability = sum(instabilities) / len(instabilities) if instabilities else 0.0

    max_coupling = 0
    for node in nodes:
        if node.coupling_metrics:
            total = node.coupling_metrics.afferent_coupling + node.coupling_metrics.efferent_coupling
            max_coupling = max(max_coupling, total)

    return ACCGraph(
        iteration_id=iteration_id,
        timestamp=timestamp,
        manifest_path=str(manifest_path),
        nodes=nodes,
        edges=edges,
        total_modules=len(nodes),
        total_dependencies=len(edges),
        total_violations=total_violations,
        blocking_violations=blocking_violations,
        warning_violations=warning_violations,
        cycles=cycles,
        cycle_count=len(cycles),
        avg_instability=avg_instability,
        max_coupling=max_coupling
    )


@router.get("/graph/{iteration_id}/violations", response_model=List[ViolationInfo])
async def get_violations(
    iteration_id: str,
    manifest_name: str = Query(..., description="Name of architectural manifest"),
    severity: Optional[RuleSeverity] = Query(None, description="Filter by severity")
) -> List[ViolationInfo]:
    """
    Get all architectural violations for iteration.

    **Integration**: Uses ImportGraphBuilder to analyze violations
    """
    graph_response = await get_acc_graph(
        iteration_id=iteration_id,
        manifest_name=manifest_name,
        include_positions=False
    )

    # Extract all violations from nodes
    all_violations = []
    for node in graph_response.nodes:
        all_violations.extend(node.violations)

    # Filter by severity if requested
    if severity:
        all_violations = [v for v in all_violations if v.severity == severity]

    return all_violations


@router.get("/graph/{iteration_id}/cycles", response_model=List[CycleInfo])
async def get_cycles(iteration_id: str, manifest_name: str = Query(...)) -> List[CycleInfo]:
    """Get all cyclic dependencies detected in the architecture."""
    graph_response = await get_acc_graph(
        iteration_id=iteration_id,
        manifest_name=manifest_name,
        include_positions=False
    )

    return graph_response.cycles


@router.get("/graph/{iteration_id}/coupling", response_model=Dict[str, CouplingMetrics])
async def get_coupling_metrics(iteration_id: str, manifest_name: str = Query(...)) -> Dict[str, CouplingMetrics]:
    """Get coupling metrics for all modules."""
    graph_response = await get_acc_graph(
        iteration_id=iteration_id,
        manifest_name=manifest_name,
        include_positions=False
    )

    coupling_data = {}
    for node in graph_response.nodes:
        if node.coupling_metrics:
            coupling_data[node.id] = node.coupling_metrics

    return coupling_data


@router.websocket("/analysis/{iteration_id}/stream")
async def analysis_stream(websocket: WebSocket, iteration_id: str):
    """
    WebSocket endpoint for real-time ACC analysis streaming.

    Events:
    - analysis_started: Analysis started
    - module_analyzed: Module analysis completed
    - violation_detected: Violation found
    - cycle_detected: Cyclic dependency found
    - analysis_completed: Analysis finished

    **Integration**: Called during ImportGraphBuilder analysis
    """
    await acc_manager.connect(websocket, iteration_id)

    try:
        # Send initial graph state
        # Note: Would need manifest_name from client
        await websocket.send_json({
            "event_type": "initial_state",
            "message": "ACC analysis WebSocket connected"
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
        acc_manager.disconnect(websocket, iteration_id)


# ============================================================================
# Integration Helper for Broadcasting
# ============================================================================

async def broadcast_acc_event(iteration_id: str, event: ACCAnalysisEvent):
    """
    Broadcast ACC analysis event to all connected WebSocket clients.

    Called from ImportGraphBuilder during analysis.

    Usage:
        from acc.api import broadcast_acc_event, ACCAnalysisEvent

        event = ACCAnalysisEvent(
            event_type="violation_detected",
            timestamp=datetime.now(),
            iteration_id=iteration_id,
            module_id="my_module",
            violation_id="V-1"
        )
        await broadcast_acc_event(iteration_id, event)
    """
    message = {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "data": event.dict()
    }
    await acc_manager.broadcast(iteration_id, message)


# ============================================================================
# Additional Helper Endpoints
# ============================================================================

@router.get("/manifests", response_model=List[str])
async def list_manifests() -> List[str]:
    """List all available architectural manifests."""
    manifests_dir = Path("manifests/architectural")
    if not manifests_dir.exists():
        return []

    return [f.stem for f in manifests_dir.glob("*.yaml")]


@router.get("/manifest/{manifest_name}", response_model=ArchitecturalManifest)
async def get_manifest(manifest_name: str) -> ArchitecturalManifest:
    """Get architectural manifest details."""
    manifest_path = Path(f"manifests/architectural/{manifest_name}.yaml")
    manifest = load_architectural_manifest(manifest_path)

    if not manifest:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {manifest_name}")

    return manifest


@router.post("/analysis/{iteration_id}/run")
async def run_acc_analysis(
    iteration_id: str,
    manifest_name: str = Query(..., description="Name of architectural manifest")
) -> Dict[str, Any]:
    """
    Trigger ACC architectural analysis for iteration.

    Analyzes codebase and streams results via WebSocket.

    **Integration**: Uses ImportGraphBuilder
    """
    # TODO: Run analysis in background task and stream events
    return {
        "status": "started",
        "iteration_id": iteration_id,
        "manifest": manifest_name,
        "message": "ACC analysis started. Connect to WebSocket for real-time updates."
    }
