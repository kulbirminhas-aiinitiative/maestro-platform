"""
Maestro Services Package

Provides service abstractions for external integrations and governance.
"""

from .integration import (
    ITaskAdapter,
    IDocumentAdapter,
    AdapterRegistry,
    get_adapter_registry
)
from .governance_service import (
    GovernanceService,
    GovernanceCheckResult,
    PhaseGate,
    Approval,
    ValidationResult,
    get_governance_service
)

# MD-2118: Epic Generation from DDE Workflows
from .epic_generator import (
    EpicGeneratorService,
    GeneratedIssue,
    EpicGenerationResult,
    NODE_TYPE_TO_JIRA,
    JIRAIssueType,
    JIRAPriority
)

# MD-2120: Task Management Service
from .task_management_service import (
    TaskManagementService,
    ClosureResult,
    EpicClosureResult,
    ClosureReason,
    get_task_management_service,
    reset_task_management_service
)

__all__ = [
    # Integration
    'ITaskAdapter',
    'IDocumentAdapter',
    'AdapterRegistry',
    'get_adapter_registry',
    # Governance
    'GovernanceService',
    'GovernanceCheckResult',
    'PhaseGate',
    'Approval',
    'ValidationResult',
    'get_governance_service',
    # Epic Generator (MD-2118)
    'EpicGeneratorService',
    'GeneratedIssue',
    'EpicGenerationResult',
    'NODE_TYPE_TO_JIRA',
    'JIRAIssueType',
    'JIRAPriority',
    # Task Management (MD-2120)
    'TaskManagementService',
    'ClosureResult',
    'EpicClosureResult',
    'ClosureReason',
    'get_task_management_service',
    'reset_task_management_service'
]
