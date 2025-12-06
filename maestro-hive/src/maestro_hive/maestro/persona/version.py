"""
Persona Version Data Structures

Core data structures for persona version control.
Implements AC-1 (version creation) and AC-2 (history tracking).

Epic: MD-2555
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import uuid
import hashlib


class VersionChange(str, Enum):
    """Type of version change for semantic versioning (AC-5)"""
    MAJOR = "major"     # Breaking changes: role, personality, core_traits
    MINOR = "minor"     # New features: capabilities, tools additions
    PATCH = "patch"     # Bug fixes: description, metadata tweaks


@dataclass
class PersonaSnapshot:
    """
    Immutable snapshot of a persona at a point in time.

    This captures the complete state of a persona for versioning.
    """
    persona_id: str
    name: str
    role: str
    personality: str
    core_traits: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaSnapshot":
        """Create from dictionary"""
        return cls(
            persona_id=data.get("persona_id", ""),
            name=data.get("name", ""),
            role=data.get("role", ""),
            personality=data.get("personality", ""),
            core_traits=data.get("core_traits", []),
            capabilities=data.get("capabilities", []),
            tools=data.get("tools", []),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )

    def compute_hash(self) -> str:
        """Compute content hash for change detection"""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class PersonaVersion:
    """
    A single version of a persona.

    Implements AC-1 (version creation) and AC-2 (history tracking).
    Each version is immutable once created.
    """
    version_id: str
    persona_id: str
    version_number: str  # Semantic version: major.minor.patch (AC-5)
    snapshot: PersonaSnapshot
    change_summary: str
    change_type: VersionChange
    author: str
    timestamp: datetime
    parent_version_id: Optional[str] = None
    content_hash: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Compute content hash if not provided"""
        if not self.content_hash:
            self.content_hash = self.snapshot.compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "version_id": self.version_id,
            "persona_id": self.persona_id,
            "version_number": self.version_number,
            "snapshot": self.snapshot.to_dict(),
            "change_summary": self.change_summary,
            "change_type": self.change_type.value,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "parent_version_id": self.parent_version_id,
            "content_hash": self.content_hash,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaVersion":
        """Create from dictionary"""
        return cls(
            version_id=data["version_id"],
            persona_id=data["persona_id"],
            version_number=data["version_number"],
            snapshot=PersonaSnapshot.from_dict(data["snapshot"]),
            change_summary=data["change_summary"],
            change_type=VersionChange(data["change_type"]),
            author=data["author"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            parent_version_id=data.get("parent_version_id"),
            content_hash=data.get("content_hash", ""),
            tags=data.get("tags", [])
        )

    @staticmethod
    def generate_version_id() -> str:
        """Generate unique version ID"""
        return f"pv-{uuid.uuid4().hex[:12]}"

    def is_breaking_change(self) -> bool:
        """Check if this is a breaking (major) change"""
        return self.change_type == VersionChange.MAJOR

    def __repr__(self) -> str:
        return f"PersonaVersion({self.persona_id}@{self.version_number})"
