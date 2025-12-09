"""
Knowledge Store Models - Core data structures for knowledge artifacts

Implements:
- AC-2543-1: Knowledge artifact storage structure
- AC-2543-2: Multiple knowledge types support
- AC-2543-3: Version control for knowledge updates
- AC-2543-4: Relevance scoring data structures
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4
import json
import hashlib


class KnowledgeType(Enum):
    """Types of knowledge that can be stored."""
    PATTERN = "pattern"           # Design patterns, best practices
    FACT = "fact"                 # Verified factual information
    EXAMPLE = "example"           # Code examples, demonstrations
    PROCEDURE = "procedure"       # Step-by-step procedures
    CONCEPT = "concept"           # Abstract concepts, definitions
    RULE = "rule"                 # Business rules, constraints
    EXPERIENCE = "experience"     # Learned behaviors, insights
    TEMPLATE = "template"         # Reusable templates
    REFERENCE = "reference"       # External references, links


class KnowledgeStatus(Enum):
    """Status of a knowledge artifact."""
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ContributorType(Enum):
    """Type of entity contributing knowledge."""
    HUMAN = "human"
    AI_AGENT = "ai_agent"
    SYSTEM = "system"
    IMPORT = "import"


@dataclass
class KnowledgeMetadata:
    """Metadata associated with a knowledge artifact."""
    domain: str = ""
    subdomain: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    confidence: float = 1.0  # 0-1, how confident we are in this knowledge
    source: Optional[str] = None
    source_url: Optional[str] = None
    last_validated: Optional[datetime] = None
    validation_count: int = 0
    usage_count: int = 0
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to dictionary."""
        return {
            "domain": self.domain,
            "subdomain": self.subdomain,
            "tags": self.tags,
            "language": self.language,
            "confidence": self.confidence,
            "source": self.source,
            "source_url": self.source_url,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "validation_count": self.validation_count,
            "usage_count": self.usage_count,
            "custom": self.custom,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeMetadata":
        """Deserialize metadata from dictionary."""
        last_validated = data.get("last_validated")
        if isinstance(last_validated, str):
            last_validated = datetime.fromisoformat(last_validated)
        
        return cls(
            domain=data.get("domain", ""),
            subdomain=data.get("subdomain"),
            tags=data.get("tags", []),
            language=data.get("language", "en"),
            confidence=data.get("confidence", 1.0),
            source=data.get("source"),
            source_url=data.get("source_url"),
            last_validated=last_validated,
            validation_count=data.get("validation_count", 0),
            usage_count=data.get("usage_count", 0),
            custom=data.get("custom", {}),
        )


@dataclass
class KnowledgeVersion:
    """
    Version information for a knowledge artifact.
    
    Implements semantic versioning with full history tracking.
    """
    major: int = 1
    minor: int = 0
    patch: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    contributor_type: ContributorType = ContributorType.HUMAN
    changelog: str = ""
    checksum: Optional[str] = None
    parent_version: Optional[str] = None  # Previous version string
    
    def __str__(self) -> str:
        """Return version as semantic version string."""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def bump_major(self, created_by: str = None, contributor_type: ContributorType = None) -> "KnowledgeVersion":
        """Create new version with bumped major."""
        return KnowledgeVersion(
            major=self.major + 1,
            minor=0,
            patch=0,
            created_by=created_by or self.created_by,
            contributor_type=contributor_type or self.contributor_type,
            parent_version=str(self),
        )
    
    def bump_minor(self, created_by: str = None, contributor_type: ContributorType = None) -> "KnowledgeVersion":
        """Create new version with bumped minor."""
        return KnowledgeVersion(
            major=self.major,
            minor=self.minor + 1,
            patch=0,
            created_by=created_by or self.created_by,
            contributor_type=contributor_type or self.contributor_type,
            parent_version=str(self),
        )
    
    def bump_patch(self, created_by: str = None, contributor_type: ContributorType = None) -> "KnowledgeVersion":
        """Create new version with bumped patch."""
        return KnowledgeVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch + 1,
            created_by=created_by or self.created_by,
            contributor_type=contributor_type or self.contributor_type,
            parent_version=str(self),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize version to dictionary."""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "contributor_type": self.contributor_type.value,
            "changelog": self.changelog,
            "checksum": self.checksum,
            "parent_version": self.parent_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeVersion":
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
            contributor_type=ContributorType(data.get("contributor_type", "human")),
            changelog=data.get("changelog", ""),
            checksum=data.get("checksum"),
            parent_version=data.get("parent_version"),
        )
    
    @classmethod
    def from_string(cls, version_str: str) -> "KnowledgeVersion":
        """Parse version from string like '1.2.3'."""
        parts = version_str.split(".")
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 1,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
        )


@dataclass
class RelevanceScore:
    """
    Relevance scoring for knowledge retrieval.
    
    Combines multiple factors to determine how relevant
    a piece of knowledge is to a query.
    """
    semantic_similarity: float = 0.0  # 0-1, embedding similarity
    keyword_match: float = 0.0        # 0-1, keyword overlap
    domain_relevance: float = 0.0     # 0-1, domain match
    recency_score: float = 0.0        # 0-1, how recent
    usage_score: float = 0.0          # 0-1, how often used
    confidence_score: float = 0.0     # 0-1, source confidence
    custom_scores: Dict[str, float] = field(default_factory=dict)
    
    # Weights for combining scores
    weights: Dict[str, float] = field(default_factory=lambda: {
        "semantic_similarity": 0.35,
        "keyword_match": 0.20,
        "domain_relevance": 0.20,
        "recency_score": 0.10,
        "usage_score": 0.10,
        "confidence_score": 0.05,
    })
    
    def overall_score(self) -> float:
        """Calculate weighted overall relevance score."""
        score = (
            self.semantic_similarity * self.weights["semantic_similarity"] +
            self.keyword_match * self.weights["keyword_match"] +
            self.domain_relevance * self.weights["domain_relevance"] +
            self.recency_score * self.weights["recency_score"] +
            self.usage_score * self.weights["usage_score"] +
            self.confidence_score * self.weights["confidence_score"]
        )
        
        # Add custom scores
        for name, value in self.custom_scores.items():
            weight = self.weights.get(f"custom_{name}", 0.0)
            score += value * weight
        
        return round(min(1.0, score), 4)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize score to dictionary."""
        return {
            "semantic_similarity": self.semantic_similarity,
            "keyword_match": self.keyword_match,
            "domain_relevance": self.domain_relevance,
            "recency_score": self.recency_score,
            "usage_score": self.usage_score,
            "confidence_score": self.confidence_score,
            "custom_scores": self.custom_scores,
            "overall": self.overall_score(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelevanceScore":
        """Deserialize score from dictionary."""
        return cls(
            semantic_similarity=data.get("semantic_similarity", 0.0),
            keyword_match=data.get("keyword_match", 0.0),
            domain_relevance=data.get("domain_relevance", 0.0),
            recency_score=data.get("recency_score", 0.0),
            usage_score=data.get("usage_score", 0.0),
            confidence_score=data.get("confidence_score", 0.0),
            custom_scores=data.get("custom_scores", {}),
        )


@dataclass
class KnowledgeContribution:
    """Record of a contribution to the knowledge store."""
    id: UUID = field(default_factory=uuid4)
    artifact_id: UUID = field(default_factory=uuid4)
    contributor_id: str = ""
    contributor_type: ContributorType = ContributorType.HUMAN
    contribution_type: str = "create"  # create, update, validate, deprecate
    timestamp: datetime = field(default_factory=datetime.utcnow)
    changes: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize contribution to dictionary."""
        return {
            "id": str(self.id),
            "artifact_id": str(self.artifact_id),
            "contributor_id": self.contributor_id,
            "contributor_type": self.contributor_type.value,
            "contribution_type": self.contribution_type,
            "timestamp": self.timestamp.isoformat(),
            "changes": self.changes,
            "rationale": self.rationale,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeContribution":
        """Deserialize contribution from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()
            
        approved_at = data.get("approved_at")
        if isinstance(approved_at, str):
            approved_at = datetime.fromisoformat(approved_at)
        
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            artifact_id=UUID(data["artifact_id"]) if data.get("artifact_id") else uuid4(),
            contributor_id=data.get("contributor_id", ""),
            contributor_type=ContributorType(data.get("contributor_type", "human")),
            contribution_type=data.get("contribution_type", "create"),
            timestamp=timestamp,
            changes=data.get("changes", {}),
            rationale=data.get("rationale", ""),
            approved=data.get("approved", False),
            approved_by=data.get("approved_by"),
            approved_at=approved_at,
        )


@dataclass
class KnowledgeArtifact:
    """
    Core knowledge artifact entity.
    
    Represents a single piece of knowledge in the store,
    including its content, type, metadata, and version history.
    """
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    content: str = ""
    knowledge_type: KnowledgeType = KnowledgeType.FACT
    status: KnowledgeStatus = KnowledgeStatus.DRAFT
    
    # Metadata and versioning
    metadata: KnowledgeMetadata = field(default_factory=KnowledgeMetadata)
    version: KnowledgeVersion = field(default_factory=KnowledgeVersion)
    version_history: List[KnowledgeVersion] = field(default_factory=list)
    
    # Relationships
    related_ids: List[UUID] = field(default_factory=list)
    parent_id: Optional[UUID] = None
    
    # Indexing
    keywords: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None  # Vector embedding for semantic search
    
    # Contributions
    contributions: List[KnowledgeContribution] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Ensure proper types after initialization."""
        if isinstance(self.id, str):
            self.id = UUID(self.id)
        if isinstance(self.parent_id, str):
            self.parent_id = UUID(self.parent_id)
        if isinstance(self.knowledge_type, str):
            self.knowledge_type = KnowledgeType(self.knowledge_type)
        if isinstance(self.status, str):
            self.status = KnowledgeStatus(self.status)
    
    def compute_checksum(self) -> str:
        """Compute SHA256 checksum of artifact content."""
        content = f"{self.title}:{self.content}:{self.knowledge_type.value}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def extract_keywords(self) -> List[str]:
        """Extract keywords from title and content."""
        # Simple keyword extraction (can be enhanced with NLP)
        text = f"{self.title} {self.content}".lower()
        # Remove common words and punctuation
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "must", "shall",
                     "can", "to", "of", "in", "for", "on", "with", "at", "by",
                     "from", "as", "into", "through", "during", "before", "after",
                     "above", "below", "between", "under", "again", "further",
                     "then", "once", "here", "there", "when", "where", "why",
                     "how", "all", "each", "few", "more", "most", "other", "some",
                     "such", "no", "nor", "not", "only", "own", "same", "so",
                     "than", "too", "very", "just", "and", "but", "if", "or",
                     "because", "until", "while", "this", "that", "these", "those"}
        
        import re
        words = re.findall(r'\b[a-z]+\b', text)
        keywords = [w for w in words if len(w) > 2 and w not in stopwords]
        
        # Get unique keywords, preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        
        return unique[:50]  # Limit to top 50
    
    def approve(self, approved_by: str) -> None:
        """Approve the knowledge artifact."""
        self.status = KnowledgeStatus.APPROVED
        self.metadata.last_validated = datetime.utcnow()
        self.metadata.validation_count += 1
        self.updated_at = datetime.utcnow()
    
    def deprecate(self, reason: str = "") -> None:
        """Deprecate the knowledge artifact."""
        self.status = KnowledgeStatus.DEPRECATED
        self.metadata.custom["deprecation_reason"] = reason
        self.metadata.custom["deprecated_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow()
    
    def archive(self) -> None:
        """Archive the knowledge artifact."""
        self.status = KnowledgeStatus.ARCHIVED
        self.metadata.custom["archived_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow()
    
    def record_usage(self) -> None:
        """Record that this artifact was used/retrieved."""
        self.metadata.usage_count += 1
        self.updated_at = datetime.utcnow()
    
    def add_contribution(self, contribution: KnowledgeContribution) -> None:
        """Add a contribution record."""
        contribution.artifact_id = self.id
        self.contributions.append(contribution)
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize artifact to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "knowledge_type": self.knowledge_type.value,
            "status": self.status.value,
            "metadata": self.metadata.to_dict(),
            "version": self.version.to_dict(),
            "version_history": [v.to_dict() for v in self.version_history],
            "related_ids": [str(rid) for rid in self.related_ids],
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "keywords": self.keywords,
            "embedding": self.embedding,
            "contributions": [c.to_dict() for c in self.contributions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeArtifact":
        """Deserialize artifact from dictionary."""
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
            title=data.get("title", ""),
            content=data.get("content", ""),
            knowledge_type=KnowledgeType(data.get("knowledge_type", "fact")),
            status=KnowledgeStatus(data.get("status", "draft")),
            metadata=KnowledgeMetadata.from_dict(data.get("metadata", {})),
            version=KnowledgeVersion.from_dict(data.get("version", {})),
            version_history=[
                KnowledgeVersion.from_dict(v) 
                for v in data.get("version_history", [])
            ],
            related_ids=[UUID(rid) for rid in data.get("related_ids", [])],
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None,
            keywords=data.get("keywords", []),
            embedding=data.get("embedding"),
            contributions=[
                KnowledgeContribution.from_dict(c) 
                for c in data.get("contributions", [])
            ],
            created_at=created_at,
            updated_at=updated_at,
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize artifact to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "KnowledgeArtifact":
        """Deserialize artifact from JSON string."""
        return cls.from_dict(json.loads(json_str))
