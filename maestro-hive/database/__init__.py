#!/usr/bin/env python3
"""
Database package for DAG workflow persistence.

Provides PostgreSQL-backed storage for workflows, executions, and events.
"""

from database.config import (
    DatabaseConfig,
    DatabaseEngine,
    db_engine,
    get_db,
    initialize_database,
    reset_database
)

from database.models import (
    Base,
    WorkflowDefinition,
    WorkflowExecution,
    NodeState,
    ExecutionEvent,
    Artifact,
    WorkflowStatus,
    NodeStatus,
    EventType
)

from database.repository import (
    WorkflowRepository,
    ExecutionRepository,
    NodeStateRepository,
    EventRepository,
    ArtifactRepository,
    RepositoryFactory
)

from database.workflow_store import (
    DatabaseWorkflowContextStore,
    migrate_from_memory_store
)

# MD-2063: Capability Registry Models
from database.capability_models import (
    CapabilityAgent,
    Capability,
    AgentCapability,
    AgentQualityHistory,
    CapabilityGroup,
    AvailabilityStatus,
    CapabilitySource,
)

__all__ = [
    # Config
    'DatabaseConfig',
    'DatabaseEngine',
    'db_engine',
    'get_db',
    'initialize_database',
    'reset_database',

    # Models
    'Base',
    'WorkflowDefinition',
    'WorkflowExecution',
    'NodeState',
    'ExecutionEvent',
    'Artifact',
    'WorkflowStatus',
    'NodeStatus',
    'EventType',

    # Repositories
    'WorkflowRepository',
    'ExecutionRepository',
    'NodeStateRepository',
    'EventRepository',
    'ArtifactRepository',
    'RepositoryFactory',

    # Workflow Store
    'DatabaseWorkflowContextStore',
    'migrate_from_memory_store',

    # Capability Registry Models (MD-2063)
    'CapabilityAgent',
    'Capability',
    'AgentCapability',
    'AgentQualityHistory',
    'CapabilityGroup',
    'AvailabilityStatus',
    'CapabilitySource',
]

__version__ = '1.0.0'
