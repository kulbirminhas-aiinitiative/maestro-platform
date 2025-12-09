"""
JIRA Bidirectional Sync Module.

Provides:
- Full sync between Maestro workflows and JIRA issues
- Conflict detection and resolution
- Field mapping and transformation
"""

from .sync_engine import JIRASyncEngine, SyncResult, SyncDirection
from .conflict import ConflictResolver, SyncConflict, Resolution, ResolutionStrategy
from .mapper import FieldMapper, FieldMapping, MappingDirection

__all__ = [
    "JIRASyncEngine",
    "SyncResult",
    "SyncDirection",
    "ConflictResolver",
    "SyncConflict",
    "Resolution",
    "ResolutionStrategy",
    "FieldMapper",
    "FieldMapping",
    "MappingDirection",
]
