"""
Persona Models - Core data structures for AI Personas

Implements:
- AC-2542-1: Persona schema with capabilities, tone, constraints
- AC-2542-2: Semantic versioning for personas
- AC-2542-4: Capability inheritance from parent personas
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4
import json
import hashlib


class PersonaStatus(Enum):
    """Status of a persona in its lifecycle."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class CapabilityLevel(Enum):
    """Proficiency level for a capability."""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class PersonaCapability:
    """
    A specific capability that a persona possesses.
    
    Capabilities can be inherited from parent personas
    and can be overridden or extended by child personas.
    """
    name: str
    description: str
    level: CapabilityLevel = CapabilityLevel.INTERMEDIATE
    domain: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    inherited_from: Optional[str] = None  # Parent persona ID if inherited
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize capability to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "level": self.level.value,
            "domain": self.domain,
            "tools": self.tools,
            "constraints": self.constraints,
            "inherited_from": self.inherited_from,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaCapability":
        """Deserialize capability from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            level=CapabilityLevel(data.get("level", "intermediate")),
            domain=data.get("domain"),
            tools=data.get("tools", []),
            constraints=data.get("constraints", {}),
            inherited_from=data.get("inherited_from"),
        )


@dataclass
class ToneProfile:
    """Defines the communication tone and style of a persona."""
    formality: float = 0.5  # 0 = casual, 1 = formal
    verbosity: float = 0.5  # 0 = terse, 1 = verbose
    empathy: float = 0.5    # 0 = direct, 1 = empathetic
    humor: float = 0.3      # 0 = serious, 1 = humorous
    technical_depth: float = 0.5  # 0 = simplified, 1 = technical
    custom_traits: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize tone profile to dictionary."""
        return {
            "formality": self.formality,
            "verbosity": self.verbosity,
            "empathy": self.empathy,
            "humor": self.humor,
            "technical_depth": self.technical_depth,
            "custom_traits": self.custom_traits,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToneProfile":
        """Deserialize tone profile from dictionary."""
        return cls(
            formality=data.get("formality", 0.5),
            verbosity=data.get("verbosity", 0.5),
            empathy=data.get("empathy", 0.5),
            humor=data.get("humor", 0.3),
            technical_depth=data.get("technical_depth", 0.5),
            custom_traits=data.get("custom_traits", {}),
        )


@dataclass
class PersonaConstraint:
    """Defines operational constraints for a persona."""
    name: str
    rule: str
    severity: str = "warning"  # warning, error, block
    scope: str = "all"  # all, specific domains, specific tools
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize constraint to dictionary."""
        return {
            "name": self.name,
            "rule": self.rule,
            "severity": self.severity,
            "scope": self.scope,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaConstraint":
        """Deserialize constraint from dictionary."""
        return cls(
            name=data["name"],
            rule=data["rule"],
            severity=data.get("severity", "warning"),
            scope=data.get("scope", "all"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PersonaVersion:
    """
    Represents a specific version of a persona.
    
    Implements semantic versioning (major.minor.patch):
    - Major: Breaking changes to capabilities or constraints
    - Minor: New capabilities or non-breaking changes
    - Patch: Bug fixes or documentation updates
    """
    major: int = 1
    minor: int = 0
    patch: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    changelog: str = ""
    checksum: Optional[str] = None
    
    def __str__(self) -> str:
        """Return version as semantic version string."""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def bump_major(self) -> "PersonaVersion":
        """Create new version with bumped major."""
        return PersonaVersion(
            major=self.major + 1,
            minor=0,
            patch=0,
            created_by=self.created_by,
        )
    
    def bump_minor(self) -> "PersonaVersion":
        """Create new version with bumped minor."""
        return PersonaVersion(
            major=self.major,
            minor=self.minor + 1,
            patch=0,
            created_by=self.created_by,
        )
    
    def bump_patch(self) -> "PersonaVersion":
        """Create new version with bumped patch."""
        return PersonaVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch + 1,
            created_by=self.created_by,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize version to dictionary."""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "changelog": self.changelog,
            "checksum": self.checksum,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaVersion":
        """Deserialize version from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
        return cls(
            major=data.get("major", 1),
            minor=data.get("minor", 0),
            patch=data.get("patch", 0),
            created_at=created_at,
            created_by=data.get("created_by"),
            changelog=data.get("changelog", ""),
            checksum=data.get("checksum"),
        )
    
    @classmethod
    def from_string(cls, version_str: str) -> "PersonaVersion":
        """Parse version from string like '1.2.3'."""
        parts = version_str.split(".")
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 1,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
        )


@dataclass
class PersonaConfig:
    """Configuration for persona behavior and limits."""
    max_response_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    allowed_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to dictionary."""
        return {
            "max_response_tokens": self.max_response_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "allowed_tools": self.allowed_tools,
            "blocked_tools": self.blocked_tools,
            "allowed_domains": self.allowed_domains,
            "blocked_domains": self.blocked_domains,
            "rate_limits": self.rate_limits,
            "custom_settings": self.custom_settings,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaConfig":
        """Deserialize config from dictionary."""
        return cls(
            max_response_tokens=data.get("max_response_tokens", 4096),
            temperature=data.get("temperature", 0.7),
            top_p=data.get("top_p", 0.9),
            allowed_tools=data.get("allowed_tools", []),
            blocked_tools=data.get("blocked_tools", []),
            allowed_domains=data.get("allowed_domains", []),
            blocked_domains=data.get("blocked_domains", []),
            rate_limits=data.get("rate_limits", {}),
            custom_settings=data.get("custom_settings", {}),
        )


@dataclass
class Persona:
    """
    Core Persona entity representing an AI agent's identity and capabilities.
    
    A persona defines:
    - Identity (name, description, role)
    - Capabilities (skills, tools, knowledge domains)
    - Tone and communication style
    - Constraints and guardrails
    - Version history for evolution tracking
    
    Personas can inherit from parent personas to share common
    capabilities while specializing for specific use cases.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    role: str = ""
    status: PersonaStatus = PersonaStatus.DRAFT
    
    # Core components
    capabilities: List[PersonaCapability] = field(default_factory=list)
    tone: ToneProfile = field(default_factory=ToneProfile)
    constraints: List[PersonaConstraint] = field(default_factory=list)
    config: PersonaConfig = field(default_factory=PersonaConfig)
    
    # Inheritance
    parent_id: Optional[UUID] = None
    children_ids: List[UUID] = field(default_factory=list)
    
    # Versioning
    version: PersonaVersion = field(default_factory=PersonaVersion)
    version_history: List[PersonaVersion] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure proper types after initialization."""
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        if isinstance(self.parent_id, str):
            self.parent_id = UUID(self.parent_id)
        if isinstance(self.status, str):
            self.status = PersonaStatus(self.status)
    
    def compute_checksum(self) -> str:
        """Compute SHA256 checksum of persona content."""
        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_capability(self, name: str) -> Optional[PersonaCapability]:
        """Get a capability by name."""
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None
    
    def has_capability(self, name: str) -> bool:
        """Check if persona has a specific capability."""
        return self.get_capability(name) is not None
    
    def add_capability(self, capability: PersonaCapability) -> None:
        """Add a new capability to the persona."""
        if not self.has_capability(capability.name):
            self.capabilities.append(capability)
            self.updated_at = datetime.utcnow()
    
    def remove_capability(self, name: str) -> bool:
        """Remove a capability by name."""
        for i, cap in enumerate(self.capabilities):
            if cap.name == name:
                self.capabilities.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def add_constraint(self, constraint: PersonaConstraint) -> None:
        """Add a new constraint to the persona."""
        self.constraints.append(constraint)
        self.updated_at = datetime.utcnow()
    
    def activate(self) -> None:
        """Set persona status to active."""
        self.status = PersonaStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def deprecate(self, reason: str = "") -> None:
        """Deprecate the persona."""
        self.status = PersonaStatus.DEPRECATED
        self.metadata["deprecation_reason"] = reason
        self.metadata["deprecated_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow()
    
    def archive(self) -> None:
        """Archive the persona."""
        self.status = PersonaStatus.ARCHIVED
        self.metadata["archived_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize persona to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "status": self.status.value,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "tone": self.tone.to_dict(),
            "constraints": [c.to_dict() for c in self.constraints],
            "config": self.config.to_dict(),
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "children_ids": [str(cid) for cid in self.children_ids],
            "version": self.version.to_dict(),
            "version_history": [v.to_dict() for v in self.version_history],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "tags": self.tags,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Persona":
        """Deserialize persona from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
            
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()
        
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            name=data.get("name", ""),
            description=data.get("description", ""),
            role=data.get("role", ""),
            status=PersonaStatus(data.get("status", "draft")),
            capabilities=[
                PersonaCapability.from_dict(c) 
                for c in data.get("capabilities", [])
            ],
            tone=ToneProfile.from_dict(data.get("tone", {})),
            constraints=[
                PersonaConstraint.from_dict(c) 
                for c in data.get("constraints", [])
            ],
            config=PersonaConfig.from_dict(data.get("config", {})),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None,
            children_ids=[UUID(cid) for cid in data.get("children_ids", [])],
            version=PersonaVersion.from_dict(data.get("version", {})),
            version_history=[
                PersonaVersion.from_dict(v) 
                for v in data.get("version_history", [])
            ],
            created_at=created_at,
            updated_at=updated_at,
            created_by=data.get("created_by"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize persona to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Persona":
        """Deserialize persona from JSON string."""
        return cls.from_dict(json.loads(json_str))
