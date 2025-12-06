"""
State Management Consolidation - Unified State Store

EPIC: MD-2528 - [CRITICAL-FIX] State Management Consolidation
EPIC: MD-2514 - [MAESTRO] Sub-EPIC 6: Workflow State Persistence

Provides:
- Unified state store interface
- JSON and PostgreSQL backends
- State synchronization between components
- State versioning and history
- State recovery on restart
- Checkpoint creation with atomic writes (MD-2514)
- State serialization with complex types (MD-2514)
- State diff and merge for branches (MD-2514)
"""

from .store import StateStore, StateEntry
from .json_backend import JSONStateStore
from .postgres_backend import PostgreSQLStateStore
from .manager import StateManager
from .sync import StateSync
from .versioning import StateVersioning

# MD-2514: Checkpoint and recovery
from .serializer import (
    StateSerializer,
    StateEncoder,
    SerializationError,
    DeserializationError,
)
from .checkpoint import (
    CheckpointManager,
    Checkpoint,
    WorkflowState,
    StateMetadata,
    CheckpointError,
    CheckpointNotFoundError,
    ChecksumValidationError,
)
from .recovery import (
    StateRecovery,
    RecoveryResult,
    RecoveryError,
    NoCheckpointAvailable,
)
from .diff import (
    StateDiff,
    StateDiffResult,
    DiffEntry,
    DiffOperation,
    Conflict,
    ConflictResolution,
    MergeResult,
)

__all__ = [
    # Core store (MD-2528)
    "StateStore",
    "StateEntry",
    "JSONStateStore",
    "PostgreSQLStateStore",
    "StateManager",
    "StateSync",
    "StateVersioning",
    # Serialization (MD-2514 AC-1)
    "StateSerializer",
    "StateEncoder",
    "SerializationError",
    "DeserializationError",
    # Checkpoint (MD-2514 AC-2)
    "CheckpointManager",
    "Checkpoint",
    "WorkflowState",
    "StateMetadata",
    "CheckpointError",
    "CheckpointNotFoundError",
    "ChecksumValidationError",
    # Recovery (MD-2514 AC-3)
    "StateRecovery",
    "RecoveryResult",
    "RecoveryError",
    "NoCheckpointAvailable",
    # Diff and Merge (MD-2514 AC-4)
    "StateDiff",
    "StateDiffResult",
    "DiffEntry",
    "DiffOperation",
    "Conflict",
    "ConflictResolution",
    "MergeResult",
]
