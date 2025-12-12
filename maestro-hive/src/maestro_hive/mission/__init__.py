"""
Mission execution module for orchestrating team-based mission workflows.

This module provides:
- ExecutionFlowManager: Orchestrates mission execution with teams
- ProgressTracker: Real-time progress monitoring with WebSocket support
- CompletionVerifier: Validates mission completion against criteria
- ExecutionConfig: Configuration for execution parameters
- HandoffCoordinator: Mission to execution handoff (MD-3024)
- ContextPackager: State serialization for handoff (MD-3024)
- ExecutionTrigger: Execution triggering (MD-3024)
"""

from .execution_flow_manager import (
    ExecutionFlowManager,
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
    ExecutionState,
)
from .progress_tracker import (
    ProgressTracker,
    ProgressReport,
    TaskStatus,
    ProgressUpdate,
)
from .completion_verifier import (
    CompletionVerifier,
    VerificationResult,
    VerificationRule,
    VerificationStatus,
)

# MD-3024: Mission to Execution Handoff
from .handoff_coordinator import (
    HandoffState,
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
    MissionConstraints,
    Artifact,
    MissionContext,
    HandoffConfig,
    HandoffStatus,
    HandoffResult,
    HandoffCoordinator,
)
from .context_packager import (
    PackageFormat,
    CompressionAlgorithm,
    PackagerConfig,
    PackageMetadata,
    PackedContext,
    SchemaValidator,
    ContextPackager,
)
from .execution_trigger import (
    ExecutionStatus as TriggerExecutionStatus,
    ExecutionPriority,
    TriggerConfig,
    ExecutionHandle,
    ExecutionUpdate,
    ExecutionResult as TriggerExecutionResult,
    ExecutionTrigger,
    create_trigger,
)

__all__ = [
    # Execution Flow
    "ExecutionFlowManager",
    "ExecutionConfig",
    "ExecutionResult",
    "ExecutionStatus",
    "ExecutionState",
    # Progress Tracking
    "ProgressTracker",
    "ProgressReport",
    "TaskStatus",
    "ProgressUpdate",
    # Completion Verification
    "CompletionVerifier",
    "VerificationResult",
    "VerificationRule",
    "VerificationStatus",
    # MD-3024: Handoff Coordinator
    "HandoffState",
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
    "MissionConstraints",
    "Artifact",
    "MissionContext",
    "HandoffConfig",
    "HandoffStatus",
    "HandoffResult",
    "HandoffCoordinator",
    # MD-3024: Context Packager
    "PackageFormat",
    "CompressionAlgorithm",
    "PackagerConfig",
    "PackageMetadata",
    "PackedContext",
    "SchemaValidator",
    "ContextPackager",
    # MD-3024: Execution Trigger
    "TriggerExecutionStatus",
    "TriggerExecutionResult",
    "ExecutionPriority",
    "TriggerConfig",
    "ExecutionHandle",
    "ExecutionUpdate",
    "ExecutionTrigger",
    "create_trigger",
]
