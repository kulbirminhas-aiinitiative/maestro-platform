"""
Persona Version Control Module

Provides version control capabilities for personas including:
- Version creation and tracking (AC-1)
- Version history queries (AC-2)
- Rollback support (AC-3)
- Version diff/comparison (AC-4)
- Semantic versioning (AC-5)

Epic: MD-2555 - Persona Version Control - Track Evolution Over Time
"""

from .version import PersonaVersion, PersonaSnapshot, VersionChange
from .version_store import PersonaVersionStore, JSONVersionStore
from .version_manager import PersonaVersionManager
from .diff_engine import PersonaDiffEngine, DiffResult, FieldDiff
from .semantic_version import SemanticVersionCalculator, SemanticVersion, ChangeType

__all__ = [
    # Core types
    "PersonaVersion",
    "PersonaSnapshot",
    "VersionChange",
    "SemanticVersion",
    "ChangeType",
    # Storage
    "PersonaVersionStore",
    "JSONVersionStore",
    # Management
    "PersonaVersionManager",
    # Diff
    "PersonaDiffEngine",
    "DiffResult",
    "FieldDiff",
    # Versioning
    "SemanticVersionCalculator",
]
