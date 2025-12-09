"""
Enterprise Admin Module - Project Administration Utilities.

This module provides centralized administration utilities for:
- Repository management (migration, cloning, archiving)
- Resource cleanup (storage, subscriptions)
- Migration operations with verification

EU AI Act Article 52 Compliance:
- All operations are logged for audit trail
- Dry-run mode enabled by default for safety
- Human oversight required for destructive operations
"""

from .config import AdminConfig, AdminOperation, OperationType
from .repository import RepositoryManager, MigrationResult, CloneResult, ArchiveResult, AuditReport
from .cleanup import ResourceCleanup, CleanupResult, CancellationResult, Resource
from .migration import MigrationRunner, MigrationPlan, MigrationStatus

__all__ = [
    # Configuration
    "AdminConfig",
    "AdminOperation",
    "OperationType",
    # Repository Management
    "RepositoryManager",
    "MigrationResult",
    "CloneResult",
    "ArchiveResult",
    "AuditReport",
    # Resource Cleanup
    "ResourceCleanup",
    "CleanupResult",
    "CancellationResult",
    "Resource",
    # Migration
    "MigrationRunner",
    "MigrationPlan",
    "MigrationStatus",
]

__version__ = "1.0.0"
