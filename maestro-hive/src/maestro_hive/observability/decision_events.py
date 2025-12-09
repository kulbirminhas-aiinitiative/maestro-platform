"""
Core data models for the Visibility System.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4


class VerbosityLevel(IntEnum):
    """Verbosity levels for the adaptive model."""
    LEARNING = 1      # Maximum - log everything
    SATURATION = 2    # High - track patterns
    OPTIMIZED = 3     # Medium - novel decisions only
    PRODUCTION = 4    # Minimal - exceptions only


@dataclass
class DecisionEvent:
    """
    Represents a decision made by an AI agent.
    
    This is the core unit of visibility - every significant decision
    is captured and can be:
    - Logged to JIRA as a subtask
    - Published to Confluence
    - Stored in learning stores
    """
    epic_id: str
    decision_id: UUID = field(default_factory=uuid4)
    persona: str = ""
    decision_type: str = "implementation"  # implementation, design, coordination
    description: str = ""
    rationale: str = ""
    artifacts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    verbosity_level: VerbosityLevel = VerbosityLevel.LEARNING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def should_log(self, current_level: VerbosityLevel) -> bool:
        """Determine if this decision should be logged at current verbosity."""
        if current_level == VerbosityLevel.LEARNING:
            return True
        elif current_level == VerbosityLevel.SATURATION:
            return True  # Still logging but tracking patterns
        elif current_level == VerbosityLevel.OPTIMIZED:
            return self.metadata.get("is_novel", True)
        else:  # PRODUCTION
            return self.metadata.get("is_exception", False)


@dataclass
class LearningEntry:
    """
    Entry in a learning store (template, quality, or coordination).
    """
    id: UUID = field(default_factory=uuid4)
    entry_type: str = "template"  # template, quality, coordination
    content: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    effectiveness_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "entry_type": self.entry_type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "effectiveness_score": self.effectiveness_score,
        }


@dataclass
class SaturationMetrics:
    """
    Metrics for determining when saturation has been reached.
    """
    total_decisions: int = 0
    unique_patterns: int = 0
    similarity_score: float = 0.0
    saturation_threshold: float = 0.95
    
    @property
    def is_saturated(self) -> bool:
        """Check if saturation threshold has been reached."""
        return self.similarity_score >= self.saturation_threshold
    
    @property
    def saturation_percentage(self) -> float:
        """Get saturation as a percentage."""
        return min(100.0, (self.similarity_score / self.saturation_threshold) * 100)
