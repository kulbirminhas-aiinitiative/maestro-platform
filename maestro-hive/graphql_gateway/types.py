"""
GraphQL Types

Strawberry GraphQL type definitions for Tri-Modal Mission Control.
Maps from Pydantic models to GraphQL types.
"""

from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
import strawberry


# ============================================================================
# Enums
# ============================================================================

@strawberry.enum
class DDEEventType(Enum):
    """DDE event types."""
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRYING = "TASK_RETRYING"
    ARTIFACT_CREATED = "ARTIFACT_CREATED"
    ARTIFACT_VALIDATED = "ARTIFACT_VALIDATED"
    CONTRACT_LOCKED = "CONTRACT_LOCKED"
    CONTRACT_VALIDATED = "CONTRACT_VALIDATED"
    QUALITY_GATE_CHECKED = "QUALITY_GATE_CHECKED"


@strawberry.enum
class DDENodeType(Enum):
    """DDE node types."""
    INTERFACE = "INTERFACE"
    ACTION = "ACTION"
    QUALITY_GATE = "QUALITY_GATE"
    ARTIFACT = "ARTIFACT"


@strawberry.enum
class DDENodeStatus(Enum):
    """DDE node status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    SKIPPED = "SKIPPED"


@strawberry.enum
class BDVEventType(Enum):
    """BDV event types."""
    TEST_RUN_STARTED = "TEST_RUN_STARTED"
    TEST_RUN_COMPLETED = "TEST_RUN_COMPLETED"
    FEATURE_STARTED = "FEATURE_STARTED"
    FEATURE_COMPLETED = "FEATURE_COMPLETED"
    SCENARIO_STARTED = "SCENARIO_STARTED"
    SCENARIO_PASSED = "SCENARIO_PASSED"
    SCENARIO_FAILED = "SCENARIO_FAILED"
    SCENARIO_SKIPPED = "SCENARIO_SKIPPED"
    STEP_EXECUTED = "STEP_EXECUTED"
    CONTRACT_TAG_DETECTED = "CONTRACT_TAG_DETECTED"
    FLAKE_DETECTED = "FLAKE_DETECTED"


@strawberry.enum
class BDVScenarioStatus(Enum):
    """BDV scenario status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    FLAKY = "FLAKY"


@strawberry.enum
class ACCEventType(Enum):
    """ACC event types."""
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    GRAPH_BUILT = "GRAPH_BUILT"
    VIOLATION_DETECTED = "VIOLATION_DETECTED"
    CYCLE_DETECTED = "CYCLE_DETECTED"
    LAYERING_VIOLATION = "LAYERING_VIOLATION"
    COUPLING_ALERT = "COUPLING_ALERT"
    MODULE_ANALYZED = "MODULE_ANALYZED"


@strawberry.enum
class ACCViolationType(Enum):
    """ACC violation types."""
    FORBIDDEN_DEPENDENCY = "FORBIDDEN_DEPENDENCY"
    LAYER_VIOLATION = "LAYER_VIOLATION"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    HIGH_COUPLING = "HIGH_COUPLING"
    SIZE_VIOLATION = "SIZE_VIOLATION"
    NAMING_VIOLATION = "NAMING_VIOLATION"


@strawberry.enum
class ACCViolationSeverity(Enum):
    """ACC violation severity."""
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


@strawberry.enum
class ProvenanceType(Enum):
    """Correlation provenance types."""
    EXPLICIT_ID = "explicit_id"
    FILE_PATH_EXACT = "file_path_exact"
    FILE_PATH_FUZZY = "file_path_fuzzy"
    TAG_MATCH = "tag_match"
    HEURISTIC = "heuristic"
    MANUAL = "manual"


@strawberry.enum
class NodeTypeEnum(Enum):
    """Graph node types."""
    WORKFLOW = "WORKFLOW"
    INTERFACE = "INTERFACE"
    ACTION = "ACTION"
    QUALITY_GATE = "QUALITY_GATE"
    ARTIFACT = "ARTIFACT"
    SCENARIO = "SCENARIO"
    MODULE = "MODULE"
    CONTRACT_STAR = "CONTRACT_STAR"


@strawberry.enum
class EdgeTypeEnum(Enum):
    """Graph edge types."""
    EXECUTES = "EXECUTES"
    PRODUCES = "PRODUCES"
    VALIDATES = "VALIDATES"
    DEPENDS_ON = "DEPENDS_ON"
    CORRELATES = "CORRELATES"
    TESTED_BY = "TESTED_BY"
    ENFORCED_BY = "ENFORCED_BY"


# ============================================================================
# Event Types
# ============================================================================

@strawberry.type
class DDEEvent:
    """DDE workflow execution event."""
    event_id: strawberry.ID
    iteration_id: strawberry.ID
    timestamp: datetime
    workflow_id: strawberry.ID
    event_type: DDEEventType
    node_id: Optional[strawberry.ID] = None
    node_type: Optional[DDENodeType] = None
    node_status: Optional[DDENodeStatus] = None
    artifact_path: Optional[str] = None
    artifact_hash: Optional[str] = None
    contract_id: Optional[str] = None
    quality_gate_name: Optional[str] = None
    quality_gate_passed: Optional[bool] = None
    retry_count: Optional[int] = None
    error_message: Optional[str] = None
    trace_id: str
    span_id: str
    traceparent: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None

    @strawberry.field
    async def correlations(self, info: strawberry.Info) -> List["CorrelationLink"]:
        """Get correlations for this event."""
        loader = info.context.dataloaders.correlations
        return await loader.load(self.event_id)


@strawberry.type
class BDVEvent:
    """BDV test scenario event."""
    event_id: strawberry.ID
    iteration_id: strawberry.ID
    timestamp: datetime
    event_type: BDVEventType
    feature_path: Optional[str] = None
    feature_name: Optional[str] = None
    scenario_id: Optional[strawberry.ID] = None
    scenario_name: Optional[str] = None
    scenario_tags: Optional[List[str]] = None
    scenario_status: Optional[BDVScenarioStatus] = None
    step_text: Optional[str] = None
    contract_tags: Optional[List[str]] = None
    error_message: Optional[str] = None
    flake_rate: Optional[float] = None
    duration_ms: Optional[int] = None
    trace_id: str
    span_id: str
    traceparent: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None

    @strawberry.field
    async def correlations(self, info: strawberry.Info) -> List["CorrelationLink"]:
        """Get correlations for this event."""
        loader = info.context.dataloaders.correlations
        return await loader.load(self.event_id)


@strawberry.type
class ACCEvent:
    """ACC architectural conformance event."""
    event_id: strawberry.ID
    iteration_id: strawberry.ID
    timestamp: datetime
    manifest_name: str
    event_type: ACCEventType
    module_path: Optional[str] = None
    module_name: Optional[str] = None
    violation_type: Optional[ACCViolationType] = None
    violation_severity: Optional[ACCViolationSeverity] = None
    violation_message: Optional[str] = None
    rule_id: Optional[str] = None
    source_module: Optional[str] = None
    target_module: Optional[str] = None
    cycle_modules: Optional[List[str]] = None
    coupling_score: Optional[float] = None
    total_modules: Optional[int] = None
    total_dependencies: Optional[int] = None
    total_violations: Optional[int] = None
    blocking_violations: Optional[int] = None
    trace_id: str
    span_id: str
    traceparent: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None

    @strawberry.field
    async def correlations(self, info: strawberry.Info) -> List["CorrelationLink"]:
        """Get correlations for this event."""
        loader = info.context.dataloaders.correlations
        return await loader.load(self.event_id)


# ============================================================================
# Correlation Types
# ============================================================================

@strawberry.type
class ConfidenceScore:
    """Confidence score for a correlation link."""
    value: float
    provenance: ProvenanceType
    reasoning: Optional[str] = None
    created_at: datetime


@strawberry.type
class CorrelationLink:
    """Correlation link between events from different streams."""
    link_id: strawberry.ID
    source_stream: str
    source_event_id: strawberry.ID
    source_entity_id: str
    target_stream: str
    target_event_id: strawberry.ID
    target_entity_id: str
    confidence: ConfidenceScore
    link_type: str
    iteration_id: strawberry.ID
    created_at: datetime
    metadata: Optional[strawberry.scalars.JSON] = None


@strawberry.type
class ContractStar:
    """Contract star (tri-modal convergence point)."""
    contract_id: str
    iteration_id: strawberry.ID

    # DDE side
    dde_interface_node_id: Optional[strawberry.ID] = None
    dde_contract_locked: bool
    dde_contract_validated: bool

    # BDV side
    bdv_contract_tag: Optional[str] = None
    bdv_scenarios: List[str]
    bdv_all_passed: bool

    # ACC side
    acc_component_boundary: Optional[str] = None
    acc_violations: List[str]
    acc_clean: bool

    # Status
    is_complete: bool
    is_valid: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Graph Types
# ============================================================================

@strawberry.type
class GraphNode:
    """Bi-temporal graph node."""
    node_id: strawberry.ID
    iteration_id: strawberry.ID
    node_type: NodeTypeEnum

    # Bi-temporal timestamps
    valid_from: datetime
    valid_to: Optional[datetime] = None
    observed_at: datetime

    # Properties
    properties: strawberry.scalars.JSON


@strawberry.type
class GraphEdge:
    """Bi-temporal graph edge."""
    edge_id: strawberry.ID
    iteration_id: strawberry.ID
    source_node_id: strawberry.ID
    target_node_id: strawberry.ID
    edge_type: EdgeTypeEnum

    # Bi-temporal timestamps
    valid_from: datetime
    valid_to: Optional[datetime] = None
    observed_at: datetime

    # Properties
    properties: strawberry.scalars.JSON


@strawberry.type
class GraphSnapshot:
    """Time-travel graph snapshot."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    iteration_id: strawberry.ID
    snapshot_time: datetime
    node_count: int
    edge_count: int


# ============================================================================
# Iteration Types
# ============================================================================

@strawberry.type
class Iteration:
    """Workflow iteration."""
    iteration_id: strawberry.ID
    workflow_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    total_events: int
    dde_events: int
    bdv_events: int
    acc_events: int
    correlations: int
    contract_stars: int


# ============================================================================
# Pagination Types
# ============================================================================

@strawberry.type
class PageInfo:
    """Page information for cursor-based pagination."""
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None


@strawberry.type
class DDEEventEdge:
    """DDE event edge for pagination."""
    node: DDEEvent
    cursor: str


@strawberry.type
class DDEEventConnection:
    """DDE event connection for pagination."""
    edges: List[DDEEventEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class BDVEventEdge:
    """BDV event edge for pagination."""
    node: BDVEvent
    cursor: str


@strawberry.type
class BDVEventConnection:
    """BDV event connection for pagination."""
    edges: List[BDVEventEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class ACCEventEdge:
    """ACC event edge for pagination."""
    node: ACCEvent
    cursor: str


@strawberry.type
class ACCEventConnection:
    """ACC event connection for pagination."""
    edges: List[ACCEventEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class CorrelationLinkEdge:
    """Correlation link edge for pagination."""
    node: CorrelationLink
    cursor: str


@strawberry.type
class CorrelationLinkConnection:
    """Correlation link connection for pagination."""
    edges: List[CorrelationLinkEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class ContractStarEdge:
    """Contract star edge for pagination."""
    node: ContractStar
    cursor: str


@strawberry.type
class ContractStarConnection:
    """Contract star connection for pagination."""
    edges: List[ContractStarEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class GraphNodeEdge:
    """Graph node edge for pagination."""
    node: GraphNode
    cursor: str


@strawberry.type
class GraphNodeConnection:
    """Graph node connection for pagination."""
    edges: List[GraphNodeEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class IterationEdge:
    """Iteration edge for pagination."""
    node: Iteration
    cursor: str


@strawberry.type
class IterationConnection:
    """Iteration connection for pagination."""
    edges: List[IterationEdge]
    page_info: PageInfo
    total_count: int


# ============================================================================
# Filter Input Types
# ============================================================================

@strawberry.input
class Pagination:
    """Pagination input."""
    first: Optional[int] = None
    after: Optional[str] = None
    last: Optional[int] = None
    before: Optional[str] = None


@strawberry.input
class DDEEventFilter:
    """Filter for DDE events."""
    iteration_id: Optional[strawberry.ID] = None
    workflow_id: Optional[strawberry.ID] = None
    event_type: Optional[DDEEventType] = None
    node_id: Optional[strawberry.ID] = None
    node_type: Optional[DDENodeType] = None
    contract_id: Optional[str] = None
    timestamp_from: Optional[datetime] = None
    timestamp_to: Optional[datetime] = None


@strawberry.input
class BDVEventFilter:
    """Filter for BDV events."""
    iteration_id: Optional[strawberry.ID] = None
    event_type: Optional[BDVEventType] = None
    scenario_id: Optional[strawberry.ID] = None
    feature_path: Optional[str] = None
    scenario_status: Optional[BDVScenarioStatus] = None
    contract_tags: Optional[List[str]] = None
    timestamp_from: Optional[datetime] = None
    timestamp_to: Optional[datetime] = None


@strawberry.input
class ACCEventFilter:
    """Filter for ACC events."""
    iteration_id: Optional[strawberry.ID] = None
    event_type: Optional[ACCEventType] = None
    manifest_name: Optional[str] = None
    violation_type: Optional[ACCViolationType] = None
    violation_severity: Optional[ACCViolationSeverity] = None
    module_path: Optional[str] = None
    timestamp_from: Optional[datetime] = None
    timestamp_to: Optional[datetime] = None


@strawberry.input
class CorrelationLinkFilter:
    """Filter for correlation links."""
    iteration_id: Optional[strawberry.ID] = None
    source_stream: Optional[str] = None
    target_stream: Optional[str] = None
    link_type: Optional[str] = None
    min_confidence: Optional[float] = None


@strawberry.input
class ContractStarFilter:
    """Filter for contract stars."""
    iteration_id: Optional[strawberry.ID] = None
    contract_id: Optional[str] = None
    is_complete: Optional[bool] = None
    is_valid: Optional[bool] = None
    dde_contract_validated: Optional[bool] = None
    bdv_all_passed: Optional[bool] = None
    acc_clean: Optional[bool] = None


@strawberry.input
class GraphNodeFilter:
    """Filter for graph nodes."""
    iteration_id: Optional[strawberry.ID] = None
    node_type: Optional[NodeTypeEnum] = None
    valid_at: Optional[datetime] = None


@strawberry.input
class IterationFilter:
    """Filter for iterations."""
    workflow_id: Optional[str] = None
    status: Optional[str] = None
    started_after: Optional[datetime] = None
    started_before: Optional[datetime] = None


# ============================================================================
# Statistics Types
# ============================================================================

@strawberry.type
class ServiceHealth:
    """Service health status."""
    name: str
    status: str
    latency_ms: int
    error: Optional[str] = None


@strawberry.type
class HealthStatus:
    """Overall health status."""
    status: str
    timestamp: datetime
    services: List[ServiceHealth]


@strawberry.type
class ThroughputMetrics:
    """Throughput metrics."""
    events_per_second: float
    correlations_per_second: float


@strawberry.type
class LatencyMetrics:
    """Latency metrics."""
    p50_ms: float
    p95_ms: float
    p99_ms: float


@strawberry.type
class SystemStats:
    """System-wide statistics."""
    total_events: int
    total_correlations: int
    total_contract_stars: int
    events_by_stream: strawberry.scalars.JSON
    correlation_rate: float
    throughput: ThroughputMetrics
    latency: LatencyMetrics


@strawberry.type
class IterationStats:
    """Per-iteration statistics."""
    iteration_id: strawberry.ID
    total_events: int
    dde_events: int
    bdv_events: int
    acc_events: int
    correlations: int
    contract_stars: int
    contract_stars_valid: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


# ============================================================================
# Mutation Input/Output Types
# ============================================================================

@strawberry.input
class RebuildGraphInput:
    """Input for rebuild graph mutation."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    iteration_id: Optional[strawberry.ID] = None


@strawberry.type
class RebuildGraphStats:
    """Statistics from graph rebuild."""
    dde_events: int
    bdv_events: int
    acc_events: int
    total_events: int
    nodes_created: int
    edges_created: int
    errors: int


@strawberry.type
class RebuildGraphResult:
    """Result from rebuild graph mutation."""
    success: bool
    message: str
    stats: Optional[RebuildGraphStats] = None


@strawberry.input
class RebuildCacheInput:
    """Input for rebuild cache mutation."""
    iteration_id: Optional[strawberry.ID] = None


@strawberry.type
class RebuildCacheResult:
    """Result from rebuild cache mutation."""
    success: bool
    message: str
    keys_rebuilt: int


@strawberry.type
class IntegrityCheckResult:
    """Result from integrity check."""
    integrity_ok: bool
    kafka_events: int
    neo4j_nodes: int
    redis_keys: int
    missing_in_neo4j: List[str]
    missing_in_redis: List[str]


# ============================================================================
# Subscription Types
# ============================================================================

@strawberry.type
class SystemEvent:
    """System event for subscriptions."""
    event_type: str
    severity: str
    message: str
    timestamp: datetime
    details: Optional[strawberry.scalars.JSON] = None
