"""
Data models for Execution History Store

EPIC: MD-2500
AC-1: pgvector for embeddings storage

Defines the core data models used throughout the history store.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ExecutionStatus(str, Enum):
    """Status of an execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass
class QualityScores:
    """Quality metrics for an execution."""
    overall_score: float = 0.0
    documentation_score: float = 0.0
    implementation_score: float = 0.0
    test_coverage_score: float = 0.0
    correctness_score: float = 0.0
    build_score: float = 0.0
    evidence_score: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "overall_score": self.overall_score,
            "documentation_score": self.documentation_score,
            "implementation_score": self.implementation_score,
            "test_coverage_score": self.test_coverage_score,
            "correctness_score": self.correctness_score,
            "build_score": self.build_score,
            "evidence_score": self.evidence_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "QualityScores":
        """Create from dictionary."""
        return cls(
            overall_score=data.get("overall_score", 0.0),
            documentation_score=data.get("documentation_score", 0.0),
            implementation_score=data.get("implementation_score", 0.0),
            test_coverage_score=data.get("test_coverage_score", 0.0),
            correctness_score=data.get("correctness_score", 0.0),
            build_score=data.get("build_score", 0.0),
            evidence_score=data.get("evidence_score", 0.0),
        )


@dataclass
class OutputArtifact:
    """An artifact produced by execution."""
    name: str
    artifact_type: str  # "code", "docs", "tests", "config"
    file_path: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRecord:
    """
    Complete record of a single execution.

    This is the core data model for the execution history store.
    It stores all information needed for RAG retrieval and audit.
    """
    # Primary identifiers
    id: UUID = field(default_factory=uuid4)
    epic_key: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Execution status
    status: ExecutionStatus = ExecutionStatus.PENDING

    # Input data
    input_text: str = ""
    input_embedding: Optional[List[float]] = None  # Vector for similarity search
    input_metadata: Dict[str, Any] = field(default_factory=dict)

    # Output data
    output_artifacts: List[OutputArtifact] = field(default_factory=list)
    output_summary: str = ""

    # Quality metrics
    quality_scores: Optional[QualityScores] = None

    # Error handling
    failure_reason: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # Execution context
    executor_version: str = ""
    parent_execution_id: Optional[UUID] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "epic_key": self.epic_key,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "input_text": self.input_text,
            "input_embedding": self.input_embedding,
            "input_metadata": self.input_metadata,
            "output_artifacts": [
                {
                    "name": a.name,
                    "artifact_type": a.artifact_type,
                    "file_path": a.file_path,
                    "content_hash": a.content_hash,
                    "metadata": a.metadata,
                }
                for a in self.output_artifacts
            ],
            "output_summary": self.output_summary,
            "quality_scores": self.quality_scores.to_dict() if self.quality_scores else None,
            "failure_reason": self.failure_reason,
            "error_details": self.error_details,
            "executor_version": self.executor_version,
            "parent_execution_id": str(self.parent_execution_id) if self.parent_execution_id else None,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        """Create from dictionary."""
        record = cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            epic_key=data.get("epic_key", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            status=ExecutionStatus(data.get("status", "pending")),
            input_text=data.get("input_text", ""),
            input_embedding=data.get("input_embedding"),
            input_metadata=data.get("input_metadata", {}),
            output_summary=data.get("output_summary", ""),
            failure_reason=data.get("failure_reason"),
            error_details=data.get("error_details"),
            executor_version=data.get("executor_version", ""),
            parent_execution_id=UUID(data["parent_execution_id"]) if data.get("parent_execution_id") else None,
            retry_count=data.get("retry_count", 0),
        )

        # Parse output artifacts
        if data.get("output_artifacts"):
            record.output_artifacts = [
                OutputArtifact(
                    name=a.get("name", ""),
                    artifact_type=a.get("artifact_type", ""),
                    file_path=a.get("file_path"),
                    content_hash=a.get("content_hash"),
                    metadata=a.get("metadata", {}),
                )
                for a in data["output_artifacts"]
            ]

        # Parse quality scores
        if data.get("quality_scores"):
            record.quality_scores = QualityScores.from_dict(data["quality_scores"])

        return record

    def mark_completed(self, status: ExecutionStatus = ExecutionStatus.SUCCESS):
        """Mark the execution as completed."""
        self.status = status
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, reason: str, error_details: Optional[Dict[str, Any]] = None):
        """Mark the execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.failure_reason = reason
        self.error_details = error_details
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
