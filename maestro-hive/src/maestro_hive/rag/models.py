"""
RAG Service Data Models.

EPIC: MD-2499
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionOutcome(Enum):
    """Outcome of an execution."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


@dataclass
class PhaseResult:
    """Result of a single execution phase."""
    phase_name: str
    status: str  # passed, failed, skipped
    score: Optional[float] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRecord:
    """Record of a past execution stored for RAG retrieval."""
    execution_id: str
    requirement_text: str
    outcome: ExecutionOutcome
    timestamp: datetime
    duration_seconds: float = 0.0
    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "requirement_text": self.requirement_text,
            "outcome": self.outcome.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "phase_results": {
                k: {
                    "phase_name": v.phase_name,
                    "status": v.status,
                    "score": v.score,
                    "duration_seconds": v.duration_seconds,
                    "error_message": v.error_message,
                    "metadata": v.metadata,
                }
                for k, v in self.phase_results.items()
            },
            "metadata": self.metadata,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        """Create from dictionary."""
        phase_results = {}
        for k, v in data.get("phase_results", {}).items():
            phase_results[k] = PhaseResult(
                phase_name=v.get("phase_name", k),
                status=v.get("status", "unknown"),
                score=v.get("score"),
                duration_seconds=v.get("duration_seconds", 0.0),
                error_message=v.get("error_message"),
                metadata=v.get("metadata", {}),
            )

        return cls(
            execution_id=data["execution_id"],
            requirement_text=data["requirement_text"],
            outcome=ExecutionOutcome(data["outcome"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            duration_seconds=data.get("duration_seconds", 0.0),
            phase_results=phase_results,
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )


@dataclass
class RetrievalResult:
    """Result of a retrieval query."""
    execution: ExecutionRecord
    similarity_score: float  # 0.0 to 1.0
    match_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuccessPattern:
    """A pattern extracted from successful executions."""
    pattern_id: str
    description: str
    frequency: int  # How many executions showed this pattern
    confidence: float  # 0.0 to 1.0
    context: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)


@dataclass
class FailurePattern:
    """A pattern extracted from failed executions."""
    pattern_id: str
    description: str
    failure_type: str  # e.g., "test_failure", "build_error", "timeout"
    frequency: int
    confidence: float
    mitigation: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)


@dataclass
class PatternSummary:
    """Summary of extracted patterns."""
    success_patterns: List[SuccessPattern]
    failure_patterns: List[FailurePattern]
    total_executions_analyzed: int
    confidence_score: float  # Overall confidence in patterns


@dataclass
class FormattedContext:
    """Formatted context ready for persona injection."""
    formatted_text: str
    token_count: int  # Approximate token count
    execution_count: int  # Number of executions analyzed
    patterns_included: int  # Number of patterns in context
    truncated: bool = False  # Whether content was truncated


@dataclass
class RetrievalConfig:
    """Configuration for retrieval service."""
    default_top_k: int = 5
    similarity_threshold: float = 0.7
    max_results: int = 20
    timeout_seconds: float = 30.0
    cache_embeddings: bool = True


@dataclass
class ContextConfig:
    """Configuration for context formatting."""
    max_tokens: int = 2000
    format_style: str = "structured"  # structured, narrative, bullet
    include_metadata: bool = True
    prioritize_failures: bool = True
