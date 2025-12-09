"""Learning Engine Models - Core data structures for learning."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class FeedbackType(Enum):
    """Types of feedback signals."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTION = "correction"


class PatternType(Enum):
    """Types of learned patterns."""
    SUCCESS = "success"
    FAILURE = "failure"
    PREFERENCE = "preference"
    WORKFLOW = "workflow"


@dataclass
class FeedbackSignal:
    """Feedback signal for learning."""
    id: UUID = field(default_factory=uuid4)
    feedback_type: FeedbackType = FeedbackType.NEUTRAL
    source: str = ""  # user, system, self
    context: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # -1 to 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "type": self.feedback_type.value, "source": self.source,
                "context": self.context, "score": self.score, "timestamp": self.timestamp.isoformat()}


@dataclass
class LearningEvent:
    """Event capturing an experience for learning."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    action: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    feedback: Optional[FeedbackSignal] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "agent_id": str(self.agent_id), "action": self.action,
                "input": self.input_data, "output": self.output_data,
                "feedback": self.feedback.to_dict() if self.feedback else None,
                "context": self.context, "timestamp": self.timestamp.isoformat()}


@dataclass
class LearningPattern:
    """Learned pattern from experiences."""
    id: UUID = field(default_factory=uuid4)
    pattern_type: PatternType = PatternType.SUCCESS
    trigger: str = ""  # What triggers this pattern
    action: str = ""   # What action to take
    confidence: float = 0.5
    occurrence_count: int = 1
    success_rate: float = 0.0
    examples: List[UUID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update_stats(self, success: bool):
        """Update pattern statistics."""
        self.occurrence_count += 1
        n = self.occurrence_count
        self.success_rate = ((n - 1) * self.success_rate + (1.0 if success else 0.0)) / n
        self.confidence = min(0.99, self.confidence + 0.01 if success else max(0.1, self.confidence - 0.02))
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "type": self.pattern_type.value, "trigger": self.trigger,
                "action": self.action, "confidence": self.confidence, "occurrences": self.occurrence_count,
                "success_rate": self.success_rate}
