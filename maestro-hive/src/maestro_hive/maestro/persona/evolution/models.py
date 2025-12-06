"""
Data Models for Persona Evolution.

EPIC: MD-2556 - Persona Evolution Algorithm
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SuggestionCategory(Enum):
    """Categories of persona improvements."""
    CAPABILITY = "capability"
    PROMPT = "prompt"
    BEHAVIOR = "behavior"
    PARAMETER = "parameter"
    CONFIGURATION = "configuration"


class SuggestionStatus(Enum):
    """Status of an improvement suggestion."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class Trend(Enum):
    """Trend direction for metrics."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class ExecutionOutcome:
    """
    Represents the outcome of a persona execution.

    AC-1: Execution outcomes feed into persona improvement suggestions.
    """
    persona_id: str
    task_id: str
    success: bool
    quality_score: float  # 0-100
    completion_time: float  # seconds
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_type: Optional[str] = None
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate score range."""
        if not 0 <= self.quality_score <= 100:
            raise ValueError(f"quality_score must be 0-100, got {self.quality_score}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona_id": self.persona_id,
            "task_id": self.task_id,
            "success": self.success,
            "quality_score": self.quality_score,
            "completion_time": self.completion_time,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "feedback": self.feedback,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionOutcome":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            persona_id=data["persona_id"],
            task_id=data["task_id"],
            success=data["success"],
            quality_score=data["quality_score"],
            completion_time=data["completion_time"],
            timestamp=timestamp or datetime.utcnow(),
            error_type=data.get("error_type"),
            feedback=data.get("feedback"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ImprovementSuggestion:
    """
    A suggestion for improving a persona.

    AC-2: Human approval required before persona changes applied.
    """
    suggestion_id: str
    persona_id: str
    category: SuggestionCategory
    description: str
    current_value: Any
    suggested_value: Any
    confidence: float  # 0-1
    evidence_outcomes: List[str]  # outcome IDs
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    applied_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate confidence range."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")

    def approve(self, approved_by: str) -> None:
        """Mark suggestion as approved."""
        self.status = SuggestionStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()

    def reject(self, reason: str) -> None:
        """Mark suggestion as rejected."""
        self.status = SuggestionStatus.REJECTED
        self.rejection_reason = reason

    def apply(self) -> None:
        """Mark suggestion as applied."""
        if self.status != SuggestionStatus.APPROVED:
            raise ValueError("Cannot apply unapproved suggestion")
        self.status = SuggestionStatus.APPLIED
        self.applied_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suggestion_id": self.suggestion_id,
            "persona_id": self.persona_id,
            "category": self.category.value,
            "description": self.description,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "confidence": self.confidence,
            "evidence_outcomes": self.evidence_outcomes,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }


@dataclass
class CapabilityScore:
    """
    Score for a specific capability.

    AC-4: Capability matrix updated based on demonstrated performance.
    """
    capability_name: str
    current_score: float  # 0-100
    historical_scores: List[Tuple[datetime, float]] = field(default_factory=list)
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def update(self, new_score: float) -> None:
        """Update the score with a new measurement."""
        self.historical_scores.append((self.last_updated, self.current_score))
        # Keep only last 100 historical scores
        if len(self.historical_scores) > 100:
            self.historical_scores = self.historical_scores[-100:]
        self.current_score = new_score
        self.sample_count += 1
        self.last_updated = datetime.utcnow()

    def get_trend(self) -> Trend:
        """Calculate trend from historical scores."""
        if len(self.historical_scores) < 5:
            return Trend.STABLE

        recent = [s for _, s in self.historical_scores[-5:]]
        older = [s for _, s in self.historical_scores[-10:-5]] if len(self.historical_scores) >= 10 else recent

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        diff = recent_avg - older_avg
        if diff > 2:
            return Trend.IMPROVING
        elif diff < -2:
            return Trend.DECLINING
        return Trend.STABLE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "capability_name": self.capability_name,
            "current_score": self.current_score,
            "trend": self.get_trend().value,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class CapabilityMatrix:
    """
    Complete capability matrix for a persona.

    AC-4: Capability matrix updated based on demonstrated performance.
    """
    persona_id: str
    capabilities: Dict[str, CapabilityScore] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def overall_score(self) -> float:
        """Calculate overall score from all capabilities."""
        if not self.capabilities:
            return 0.0
        scores = [c.current_score for c in self.capabilities.values()]
        return sum(scores) / len(scores)

    @property
    def evolution_trend(self) -> Trend:
        """Calculate overall evolution trend."""
        if not self.capabilities:
            return Trend.STABLE

        trends = [c.get_trend() for c in self.capabilities.values()]
        improving = sum(1 for t in trends if t == Trend.IMPROVING)
        declining = sum(1 for t in trends if t == Trend.DECLINING)

        if improving > declining * 2:
            return Trend.IMPROVING
        elif declining > improving * 2:
            return Trend.DECLINING
        return Trend.STABLE

    def get_capability(self, name: str) -> Optional[CapabilityScore]:
        """Get a capability by name."""
        return self.capabilities.get(name)

    def update_capability(self, name: str, score: float) -> None:
        """Update or create a capability score."""
        if name in self.capabilities:
            self.capabilities[name].update(score)
        else:
            self.capabilities[name] = CapabilityScore(
                capability_name=name,
                current_score=score,
                sample_count=1,
            )
        self.last_updated = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona_id": self.persona_id,
            "overall_score": self.overall_score,
            "evolution_trend": self.evolution_trend.value,
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class EvolutionMetrics:
    """
    Evolution metrics for a persona.

    AC-3: Evolution metrics tracked (success rate improvement over time).
    """
    persona_id: str
    total_executions: int = 0
    successful_executions: int = 0
    average_quality_score: float = 0.0
    evolution_count: int = 0
    last_evolution: Optional[datetime] = None
    weekly_success_rates: List[float] = field(default_factory=list)
    weekly_quality_scores: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate current success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    @property
    def success_rate_trend(self) -> Trend:
        """Calculate success rate trend."""
        if len(self.weekly_success_rates) < 2:
            return Trend.STABLE

        recent = self.weekly_success_rates[-3:] if len(self.weekly_success_rates) >= 3 else self.weekly_success_rates
        older = self.weekly_success_rates[-6:-3] if len(self.weekly_success_rates) >= 6 else self.weekly_success_rates[:len(self.weekly_success_rates)//2]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else recent_avg

        diff = recent_avg - older_avg
        if diff > 0.05:
            return Trend.IMPROVING
        elif diff < -0.05:
            return Trend.DECLINING
        return Trend.STABLE

    @property
    def quality_trend(self) -> Trend:
        """Calculate quality score trend."""
        if len(self.weekly_quality_scores) < 2:
            return Trend.STABLE

        recent = self.weekly_quality_scores[-3:] if len(self.weekly_quality_scores) >= 3 else self.weekly_quality_scores
        older = self.weekly_quality_scores[-6:-3] if len(self.weekly_quality_scores) >= 6 else self.weekly_quality_scores[:len(self.weekly_quality_scores)//2]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else recent_avg

        diff = recent_avg - older_avg
        if diff > 2:
            return Trend.IMPROVING
        elif diff < -2:
            return Trend.DECLINING
        return Trend.STABLE

    def record_execution(self, success: bool, quality_score: float) -> None:
        """Record an execution result."""
        self.total_executions += 1
        if success:
            self.successful_executions += 1

        # Update rolling average
        if self.total_executions == 1:
            self.average_quality_score = quality_score
        else:
            self.average_quality_score = (
                (self.average_quality_score * (self.total_executions - 1) + quality_score)
                / self.total_executions
            )

    def record_evolution(self) -> None:
        """Record an evolution event."""
        self.evolution_count += 1
        self.last_evolution = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona_id": self.persona_id,
            "total_executions": self.total_executions,
            "success_rate": self.success_rate,
            "success_rate_trend": self.success_rate_trend.value,
            "average_quality_score": self.average_quality_score,
            "quality_trend": self.quality_trend.value,
            "evolution_count": self.evolution_count,
            "last_evolution": self.last_evolution.isoformat() if self.last_evolution else None,
            "weekly_success_rates": self.weekly_success_rates,
            "weekly_quality_scores": self.weekly_quality_scores,
        }
