"""Innovation Engine Models - Core data structures for innovation."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class InnovationType(Enum):
    """Types of innovations."""
    INCREMENTAL = "incremental"
    COMBINATION = "combination"
    TRANSFORMATION = "transformation"
    NOVEL = "novel"


class CombinationStrategy(Enum):
    """Strategies for combining concepts."""
    MERGE = "merge"
    BLEND = "blend"
    CHAIN = "chain"
    SUBSTITUTE = "substitute"


@dataclass
class InnovationSeed:
    """Seed concept for innovation."""
    id: UUID = field(default_factory=uuid4)
    concept: str = ""
    domain: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    relationships: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "concept": self.concept, "domain": self.domain,
                "attributes": self.attributes, "relationships": self.relationships}


@dataclass
class Innovation:
    """Generated innovation."""
    id: UUID = field(default_factory=uuid4)
    innovation_type: InnovationType = InnovationType.INCREMENTAL
    title: str = ""
    description: str = ""
    source_seeds: List[UUID] = field(default_factory=list)
    strategy_used: Optional[CombinationStrategy] = None
    novelty_score: float = 0.0
    feasibility_score: float = 0.0
    impact_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def overall_score(self) -> float:
        """Calculate overall innovation score."""
        return (self.novelty_score * 0.4 + self.feasibility_score * 0.3 + self.impact_score * 0.3)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "type": self.innovation_type.value, "title": self.title,
                "description": self.description, "novelty": self.novelty_score,
                "feasibility": self.feasibility_score, "impact": self.impact_score,
                "overall": self.overall_score}
