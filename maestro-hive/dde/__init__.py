"""
DDE - Dependency-Driven Execution

Core execution infrastructure for AI agent workflows.
ML-ready architecture for scoring and routing.

Modules:
- performance_tracker: Agent performance metrics (MD-882)
- agent_registry: Agent profiles and capabilities (MD-883)
- task_matcher: Task-agent matching service (MD-884)
- execution_manifest: Execution plan definition (MD-885)
- correlation_service: DDE-BDV result synchronization (MD-2023)
- capability_matcher: Capability matching (existing)
- artifact_stamper: Artifact traceability (existing)
- api: DDE API endpoints (existing)
"""

from dde.performance_tracker import (
    PerformanceTracker,
    get_performance_tracker,
    ExecutionMetric,
    ExecutionOutcome,
    AgentPerformanceSummary
)

from dde.agent_registry import (
    AgentRegistry,
    get_agent_registry,
    AgentProfile,
    AgentCapability
)

from dde.task_matcher import (
    TaskMatcher,
    get_task_matcher,
    TaskRequirements,
    MatchResult
)

from dde.execution_manifest import (
    ExecutionManifest,
    ManifestNode,
    ManifestPolicy,
    ManifestBuilder,
    NodeType,
    NodeStatus,
    PolicySeverity
)

from dde.agent_evaluator import (
    AgentEvaluator,
    get_agent_evaluator,
    AgentEvaluation,
    EvaluationScore
)

from dde.routing_engine import (
    RoutingEngine,
    get_routing_engine,
    RoutingDecision,
    RoutingStrategy
)

# MD-2023: DDE-BDV Correlation Service
from dde.correlation_service import (
    DDEBDVCorrelationService,
    get_correlation_service,
    ContractFulfillmentStatus,
    CorrelatedValidationResult,
    CorrelationStatus,
    FulfillmentSource
)

# MD-2119: Bidirectional Status Sync (DDE ↔ JIRA)
from dde.status_sync import (
    StatusSyncService,
    DDEStatus,
    JIRAStatus,
    SyncBinding,
    StatusSyncEvent,
    DDE_TO_JIRA_STATUS,
    JIRA_TO_DDE_STATUS,
    map_dde_to_jira,
    map_jira_to_dde
)

__all__ = [
    # Performance Tracker
    'PerformanceTracker',
    'get_performance_tracker',
    'ExecutionMetric',
    'ExecutionOutcome',
    'AgentPerformanceSummary',

    # Agent Registry
    'AgentRegistry',
    'get_agent_registry',
    'AgentProfile',
    'AgentCapability',

    # Task Matcher
    'TaskMatcher',
    'get_task_matcher',
    'TaskRequirements',
    'MatchResult',

    # Execution Manifest
    'ExecutionManifest',
    'ManifestNode',
    'ManifestPolicy',
    'ManifestBuilder',
    'NodeType',
    'NodeStatus',
    'PolicySeverity',

    # Agent Evaluator
    'AgentEvaluator',
    'get_agent_evaluator',
    'AgentEvaluation',
    'EvaluationScore',

    # Routing Engine
    'RoutingEngine',
    'get_routing_engine',
    'RoutingDecision',
    'RoutingStrategy',

    # MD-2023: Correlation Service
    'DDEBDVCorrelationService',
    'get_correlation_service',
    'ContractFulfillmentStatus',
    'CorrelatedValidationResult',
    'CorrelationStatus',
    'FulfillmentSource',

    # MD-2119: Status Sync
    'StatusSyncService',
    'DDEStatus',
    'JIRAStatus',
    'SyncBinding',
    'StatusSyncEvent',
    'DDE_TO_JIRA_STATUS',
    'JIRA_TO_DDE_STATUS',
    'map_dde_to_jira',
    'map_jira_to_dde',
]
