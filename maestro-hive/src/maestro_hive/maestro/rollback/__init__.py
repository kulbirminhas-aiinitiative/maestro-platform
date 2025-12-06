"""
Rollback Mechanism - Error Handling and State Recovery

EPIC: MD-2527 - [CRITICAL-FIX] Rollback Mechanism

Provides transaction-like rollback for failed orchestration phases:
- State checkpoint before each phase
- Rollback execution on failure
- Artifact cleanup on rollback
- Recovery notification system
"""

from .manager import RollbackManager
from .checkpoint import PhaseCheckpoint, CheckpointStore
from .executor import RollbackExecutor
from .notifications import RecoveryNotificationService

__all__ = [
    "RollbackManager",
    "PhaseCheckpoint",
    "CheckpointStore",
    "RollbackExecutor",
    "RecoveryNotificationService",
]
