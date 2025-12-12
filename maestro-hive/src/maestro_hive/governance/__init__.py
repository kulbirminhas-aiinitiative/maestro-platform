"""
Governance Layer - The Constitution & Immune System

EPIC: MD-3115 - Implement the Governance Layer
Sub-Tasks:
- MD-3201: The Enforcer Middleware (Synchronous)
- MD-3202: The Auditor Service (Asynchronous)
- MD-3203: Reputation System & Identity
- MD-3204: Chaos Agents (Loki & Janitor)
- MD-3205: Emergency Override (God Mode)

This module provides the governance infrastructure for the Maestro Hive,
implementing the "Constitution" defined in config/governance/policy.yaml.
"""

from maestro_hive.governance.enforcer import (
    AgentAction,
    AgentContext,
    BudgetExceededError,
    ConcurrencyError,
    Enforcer,
    EnforcerMiddleware,
    EnforcerResult,
    EnforcementResult,
    PermissionDeniedError,
    PolicyLoadError,
    ViolationType,
)
from maestro_hive.governance.reputation import (
    ReputationEngine,
    ReputationEvent,
    ReputationScore,
)
from maestro_hive.governance.file_locker import (
    FileLocker,
    FileLock,
    LockStatus,
)
from maestro_hive.governance.audit_logger import (
    AuditLogger,
    AuditEntry,
    AuditAction,
)
from maestro_hive.governance.chaos_agents import (
    ChaosManager,
    LokiAgent,
    JanitorAgent,
    ChaosEvent,
    ChaosActionType,
)
from maestro_hive.governance.identity import (
    IdentityManager,
    AgentIdentity,
    SignedAction,
)
from maestro_hive.governance.persistence import (
    GovernancePersistence,
    StorageBackend,
    FileStorageBackend,
    get_persistence,
)

__all__ = [
    # Enforcer (MD-3116 / MD-3201)
    "AgentAction",
    "AgentContext",
    "Enforcer",
    "EnforcerMiddleware",
    "EnforcerResult",
    "EnforcementResult",
    "ViolationType",
    # Exceptions
    "BudgetExceededError",
    "ConcurrencyError",
    "PermissionDeniedError",
    "PolicyLoadError",
    # Reputation (MD-3203)
    "ReputationEngine",
    "ReputationEvent",
    "ReputationScore",
    # File Locking (AC-3)
    "FileLocker",
    "FileLock",
    "LockStatus",
    # Audit (AC-5)
    "AuditLogger",
    "AuditEntry",
    "AuditAction",
    # Chaos Agents (MD-3204, AC-4)
    "ChaosManager",
    "LokiAgent",
    "JanitorAgent",
    "ChaosEvent",
    "ChaosActionType",
    # Identity (MD-3118)
    "IdentityManager",
    "AgentIdentity",
    "SignedAction",
    # Persistence (MD-3118, AC-5)
    "GovernancePersistence",
    "StorageBackend",
    "FileStorageBackend",
    "get_persistence",
]
