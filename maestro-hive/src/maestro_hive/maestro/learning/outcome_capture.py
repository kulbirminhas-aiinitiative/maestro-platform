"""
Outcome Capture - Record Success and Failure.

EPIC: MD-2564 - [LEARNING-ENGINE] Outcome Capture

Captures and categorizes outcomes from every execution including:
- Success, partial, and failure results
- Resource usage tracking
- Failure categorization
- Human feedback integration
- Persistence to Knowledge Store

Parent Epic: MD-2546 - [FOUNDRY-CORE] Learning Engine
"""

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Callable
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# AC-1: Outcome schema captures: result, quality score, time, resources used
# =============================================================================

class OutcomeResult(str, Enum):
    """Result types for execution outcomes."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ResourceUsage:
    """
    Resource usage metrics for an execution.

    AC-1: Captures resources used including tokens, API calls, time, memory, cost.
    """
    tokens_input: int = 0
    tokens_output: int = 0
    api_calls: int = 0
    execution_time_seconds: float = 0.0
    memory_mb: Optional[float] = None
    cost_estimate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "api_calls": self.api_calls,
            "execution_time_seconds": self.execution_time_seconds,
            "memory_mb": self.memory_mb,
            "cost_estimate": self.cost_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceUsage":
        """Create from dictionary."""
        return cls(
            tokens_input=data.get("tokens_input", 0),
            tokens_output=data.get("tokens_output", 0),
            api_calls=data.get("api_calls", 0),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            memory_mb=data.get("memory_mb"),
            cost_estimate=data.get("cost_estimate"),
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.tokens_input + self.tokens_output


# =============================================================================
# AC-2: Failure categorization (user error, system error, capability gap)
# =============================================================================

class FailureCategory(str, Enum):
    """
    Categorization of failure types.

    AC-2: Enables failure categorization for learning and improvement.
    """
    USER_ERROR = "user_error"           # Invalid input, unclear requirements
    SYSTEM_ERROR = "system_error"       # Infrastructure, network, service failures
    CAPABILITY_GAP = "capability_gap"   # Task beyond current capabilities
    EXTERNAL_DEPENDENCY = "external_dependency"  # Third-party service issues
    CONFIGURATION = "configuration"     # Misconfiguration, missing settings
    TIMEOUT = "timeout"                 # Execution exceeded time limits
    RESOURCE_LIMIT = "resource_limit"   # Memory, token, or API limits exceeded
    UNKNOWN = "unknown"                 # Unclassified failures


@dataclass
class FailureDetails:
    """
    Detailed information about a failure.

    AC-2: Provides structured failure information for analysis.
    """
    category: FailureCategory
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    root_cause: Optional[str] = None
    remediation_hints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "root_cause": self.root_cause,
            "remediation_hints": self.remediation_hints,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureDetails":
        """Create from dictionary."""
        return cls(
            category=FailureCategory(data["category"]),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            stack_trace=data.get("stack_trace"),
            recovery_attempted=data.get("recovery_attempted", False),
            recovery_successful=data.get("recovery_successful", False),
            root_cause=data.get("root_cause"),
            remediation_hints=data.get("remediation_hints", []),
        )


# =============================================================================
# AC-3: Link outcomes to specific personas, tools, and contexts
# =============================================================================

@dataclass
class ExecutionContext:
    """
    Context information linking outcome to execution environment.

    AC-3: Links outcomes to specific personas, tools, and contexts.
    """
    persona_id: str
    tool_ids: List[str] = field(default_factory=list)
    workflow_id: Optional[str] = None
    phase_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    epic_key: Optional[str] = None
    environment: str = "development"  # development, staging, production
    session_id: Optional[str] = None
    parent_outcome_id: Optional[str] = None  # For nested executions
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona_id": self.persona_id,
            "tool_ids": self.tool_ids,
            "workflow_id": self.workflow_id,
            "phase_id": self.phase_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "epic_key": self.epic_key,
            "environment": self.environment,
            "session_id": self.session_id,
            "parent_outcome_id": self.parent_outcome_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """Create from dictionary."""
        return cls(
            persona_id=data["persona_id"],
            tool_ids=data.get("tool_ids", []),
            workflow_id=data.get("workflow_id"),
            phase_id=data.get("phase_id"),
            project_id=data.get("project_id"),
            task_id=data.get("task_id"),
            epic_key=data.get("epic_key"),
            environment=data.get("environment", "development"),
            session_id=data.get("session_id"),
            parent_outcome_id=data.get("parent_outcome_id"),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# AC-4: Human feedback integration (thumbs up/down, comments)
# =============================================================================

class FeedbackRating(str, Enum):
    """Rating options for human feedback."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    NEUTRAL = "neutral"


@dataclass
class HumanFeedback:
    """
    Human feedback on an execution outcome.

    AC-4: Integrates human feedback including ratings and comments.
    """
    rating: FeedbackRating
    comment: Optional[str] = None
    provided_by: str = "anonymous"
    provided_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)  # e.g., ["accuracy", "speed", "usability"]
    improvement_suggestions: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rating": self.rating.value,
            "comment": self.comment,
            "provided_by": self.provided_by,
            "provided_at": self.provided_at.isoformat(),
            "tags": self.tags,
            "categories": self.categories,
            "improvement_suggestions": self.improvement_suggestions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HumanFeedback":
        """Create from dictionary."""
        provided_at = data.get("provided_at")
        if isinstance(provided_at, str):
            provided_at = datetime.fromisoformat(provided_at)
        return cls(
            rating=FeedbackRating(data["rating"]),
            comment=data.get("comment"),
            provided_by=data.get("provided_by", "anonymous"),
            provided_at=provided_at or datetime.utcnow(),
            tags=data.get("tags", []),
            categories=data.get("categories", []),
            improvement_suggestions=data.get("improvement_suggestions"),
        )


# =============================================================================
# Main CapturedOutcome Model
# =============================================================================

@dataclass
class CapturedOutcome:
    """
    Complete captured outcome record.

    Implements all 5 Acceptance Criteria:
    - AC-1: Schema with result, quality score, time, resources
    - AC-2: Failure categorization
    - AC-3: Links to personas, tools, contexts
    - AC-4: Human feedback integration
    - AC-5: Persistence tracking
    """
    outcome_id: str
    result: OutcomeResult
    quality_score: float  # 0-100
    completion_time_seconds: float
    resources: ResourceUsage
    context: ExecutionContext
    captured_at: datetime = field(default_factory=datetime.utcnow)

    # AC-2: Failure details (optional, only for failures)
    failure: Optional[FailureDetails] = None

    # AC-4: Human feedback (optional, added after capture)
    human_feedback: List[HumanFeedback] = field(default_factory=list)

    # AC-5: Persistence tracking
    persisted_to_knowledge_store: bool = False
    knowledge_store_id: Optional[str] = None

    # Additional metadata
    description: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None  # For similarity search

    def __post_init__(self):
        """Validate outcome data."""
        if not 0 <= self.quality_score <= 100:
            raise ValueError(f"quality_score must be 0-100, got {self.quality_score}")
        if self.completion_time_seconds < 0:
            raise ValueError(f"completion_time_seconds must be non-negative")

    @property
    def is_success(self) -> bool:
        """Check if outcome was successful."""
        return self.result == OutcomeResult.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if outcome was a failure."""
        return self.result == OutcomeResult.FAILURE

    @property
    def has_feedback(self) -> bool:
        """Check if outcome has human feedback."""
        return len(self.human_feedback) > 0

    @property
    def average_feedback_score(self) -> float:
        """Calculate average feedback score (1 = thumbs_up, 0 = neutral, -1 = thumbs_down)."""
        if not self.human_feedback:
            return 0.0
        scores = {
            FeedbackRating.THUMBS_UP: 1.0,
            FeedbackRating.NEUTRAL: 0.0,
            FeedbackRating.THUMBS_DOWN: -1.0,
        }
        total = sum(scores[f.rating] for f in self.human_feedback)
        return total / len(self.human_feedback)

    def add_feedback(self, feedback: HumanFeedback) -> None:
        """Add human feedback to this outcome."""
        self.human_feedback.append(feedback)
        logger.info(f"Added feedback to outcome {self.outcome_id}: {feedback.rating.value}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "outcome_id": self.outcome_id,
            "result": self.result.value,
            "quality_score": self.quality_score,
            "completion_time_seconds": self.completion_time_seconds,
            "resources": self.resources.to_dict(),
            "context": self.context.to_dict(),
            "captured_at": self.captured_at.isoformat(),
            "failure": self.failure.to_dict() if self.failure else None,
            "human_feedback": [f.to_dict() for f in self.human_feedback],
            "persisted_to_knowledge_store": self.persisted_to_knowledge_store,
            "knowledge_store_id": self.knowledge_store_id,
            "description": self.description,
            "artifacts": self.artifacts,
            # Embedding excluded from dict for size reasons
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapturedOutcome":
        """Create from dictionary."""
        captured_at = data.get("captured_at")
        if isinstance(captured_at, str):
            captured_at = datetime.fromisoformat(captured_at)

        return cls(
            outcome_id=data["outcome_id"],
            result=OutcomeResult(data["result"]),
            quality_score=data["quality_score"],
            completion_time_seconds=data["completion_time_seconds"],
            resources=ResourceUsage.from_dict(data["resources"]),
            context=ExecutionContext.from_dict(data["context"]),
            captured_at=captured_at or datetime.utcnow(),
            failure=FailureDetails.from_dict(data["failure"]) if data.get("failure") else None,
            human_feedback=[HumanFeedback.from_dict(f) for f in data.get("human_feedback", [])],
            persisted_to_knowledge_store=data.get("persisted_to_knowledge_store", False),
            knowledge_store_id=data.get("knowledge_store_id"),
            description=data.get("description"),
            artifacts=data.get("artifacts", []),
        )


# =============================================================================
# AC-5: Outcome persistence to Knowledge Store
# =============================================================================

class KnowledgeStorePersistence:
    """
    Persistence layer for outcomes to Knowledge Store.

    AC-5: Handles outcome persistence to Knowledge Store.
    """

    def __init__(
        self,
        storage_path: str = "data/outcomes",
        on_persist: Optional[Callable[[CapturedOutcome], None]] = None,
    ):
        """
        Initialize persistence layer.

        Args:
            storage_path: Path for file-based storage
            on_persist: Callback when outcome is persisted
        """
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._on_persist = on_persist
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

        logger.info(f"KnowledgeStorePersistence initialized at {storage_path}")

    def _load_index(self) -> None:
        """Load index from disk."""
        index_path = self._storage_path / "index.json"
        if index_path.exists():
            try:
                with open(index_path) as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load index: {e}")
                self._index = {}

    def _save_index(self) -> None:
        """Save index to disk."""
        index_path = self._storage_path / "index.json"
        try:
            with open(index_path, "w") as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def persist(self, outcome: CapturedOutcome) -> str:
        """
        Persist outcome to Knowledge Store.

        Args:
            outcome: Outcome to persist

        Returns:
            Knowledge Store ID
        """
        knowledge_store_id = f"ks_{outcome.outcome_id}"
        file_path = self._storage_path / f"{outcome.outcome_id}.json"

        try:
            with open(file_path, "w") as f:
                json.dump(outcome.to_dict(), f, indent=2)

            # Update index
            self._index[outcome.outcome_id] = {
                "knowledge_store_id": knowledge_store_id,
                "result": outcome.result.value,
                "persona_id": outcome.context.persona_id,
                "captured_at": outcome.captured_at.isoformat(),
                "quality_score": outcome.quality_score,
            }
            self._save_index()

            # Update outcome
            outcome.persisted_to_knowledge_store = True
            outcome.knowledge_store_id = knowledge_store_id

            logger.info(f"Persisted outcome {outcome.outcome_id} to Knowledge Store")

            if self._on_persist:
                self._on_persist(outcome)

            return knowledge_store_id

        except Exception as e:
            logger.error(f"Failed to persist outcome: {e}")
            raise

    def retrieve(self, outcome_id: str) -> Optional[CapturedOutcome]:
        """
        Retrieve outcome from Knowledge Store.

        Args:
            outcome_id: Outcome ID to retrieve

        Returns:
            CapturedOutcome or None if not found
        """
        file_path = self._storage_path / f"{outcome_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)
            return CapturedOutcome.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to retrieve outcome {outcome_id}: {e}")
            return None

    def list_outcomes(
        self,
        persona_id: Optional[str] = None,
        result: Optional[OutcomeResult] = None,
        limit: int = 100,
    ) -> List[CapturedOutcome]:
        """
        List outcomes with optional filters.

        Args:
            persona_id: Filter by persona
            result: Filter by result type
            limit: Maximum results

        Returns:
            List of matching outcomes
        """
        outcomes = []

        for outcome_id, meta in self._index.items():
            if persona_id and meta.get("persona_id") != persona_id:
                continue
            if result and meta.get("result") != result.value:
                continue

            outcome = self.retrieve(outcome_id)
            if outcome:
                outcomes.append(outcome)

            if len(outcomes) >= limit:
                break

        # Sort by captured_at descending
        outcomes.sort(key=lambda o: o.captured_at, reverse=True)
        return outcomes[:limit]

    def get_statistics(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics.

        Args:
            persona_id: Filter by persona (optional)

        Returns:
            Statistics dictionary
        """
        outcomes = self.list_outcomes(persona_id=persona_id, limit=1000)

        if not outcomes:
            return {
                "total": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_quality": 0.0,
                "avg_time": 0.0,
            }

        success_count = sum(1 for o in outcomes if o.is_success)
        quality_scores = [o.quality_score for o in outcomes]
        completion_times = [o.completion_time_seconds for o in outcomes]

        return {
            "total": len(outcomes),
            "success_count": success_count,
            "failure_count": len(outcomes) - success_count,
            "success_rate": success_count / len(outcomes),
            "avg_quality": sum(quality_scores) / len(quality_scores),
            "avg_time": sum(completion_times) / len(completion_times),
            "min_quality": min(quality_scores),
            "max_quality": max(quality_scores),
        }


# =============================================================================
# Outcome Capture Service
# =============================================================================

class OutcomeCaptureService:
    """
    Main service for capturing execution outcomes.

    Implements all 5 Acceptance Criteria:
    - AC-1: Outcome schema with result, quality score, time, resources
    - AC-2: Failure categorization
    - AC-3: Links to personas, tools, contexts
    - AC-4: Human feedback integration
    - AC-5: Persistence to Knowledge Store
    """

    def __init__(
        self,
        persistence: Optional[KnowledgeStorePersistence] = None,
        auto_persist: bool = True,
        on_capture: Optional[Callable[[CapturedOutcome], None]] = None,
    ):
        """
        Initialize the outcome capture service.

        Args:
            persistence: Persistence layer (default: file-based)
            auto_persist: Automatically persist on capture
            on_capture: Callback when outcome is captured
        """
        self._persistence = persistence or KnowledgeStorePersistence()
        self._auto_persist = auto_persist
        self._on_capture = on_capture
        self._in_memory_cache: Dict[str, CapturedOutcome] = {}

        logger.info("OutcomeCaptureService initialized")

    def capture(
        self,
        result: OutcomeResult,
        quality_score: float,
        completion_time_seconds: float,
        context: ExecutionContext,
        resources: Optional[ResourceUsage] = None,
        failure: Optional[FailureDetails] = None,
        description: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> CapturedOutcome:
        """
        Capture an execution outcome.

        AC-1: Captures result, quality score, time, resources.
        AC-2: Optionally captures failure details.
        AC-3: Links to context (personas, tools, etc.).

        Args:
            result: Execution result
            quality_score: Quality score 0-100
            completion_time_seconds: Execution time
            context: Execution context
            resources: Resource usage (default: empty)
            failure: Failure details (for failures)
            description: Optional description
            artifacts: List of artifact paths/IDs

        Returns:
            CapturedOutcome with unique ID
        """
        outcome_id = f"out_{uuid.uuid4().hex[:12]}"

        outcome = CapturedOutcome(
            outcome_id=outcome_id,
            result=result,
            quality_score=quality_score,
            completion_time_seconds=completion_time_seconds,
            resources=resources or ResourceUsage(),
            context=context,
            failure=failure,
            description=description,
            artifacts=artifacts or [],
        )

        # Cache in memory
        self._in_memory_cache[outcome_id] = outcome

        logger.info(
            f"Captured outcome {outcome_id}: "
            f"result={result.value}, quality={quality_score}, "
            f"persona={context.persona_id}"
        )

        # Auto-persist if enabled (AC-5)
        if self._auto_persist:
            self._persistence.persist(outcome)

        # Trigger callback
        if self._on_capture:
            try:
                self._on_capture(outcome)
            except Exception as e:
                logger.error(f"Capture callback failed: {e}")

        return outcome

    def capture_success(
        self,
        quality_score: float,
        completion_time_seconds: float,
        context: ExecutionContext,
        resources: Optional[ResourceUsage] = None,
        description: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> CapturedOutcome:
        """
        Convenience method to capture a successful outcome.

        Args:
            quality_score: Quality score 0-100
            completion_time_seconds: Execution time
            context: Execution context
            resources: Resource usage
            description: Optional description
            artifacts: List of artifact paths/IDs

        Returns:
            CapturedOutcome
        """
        return self.capture(
            result=OutcomeResult.SUCCESS,
            quality_score=quality_score,
            completion_time_seconds=completion_time_seconds,
            context=context,
            resources=resources,
            description=description,
            artifacts=artifacts,
        )

    def capture_failure(
        self,
        category: FailureCategory,
        completion_time_seconds: float,
        context: ExecutionContext,
        error_message: Optional[str] = None,
        resources: Optional[ResourceUsage] = None,
        quality_score: float = 0.0,
        description: Optional[str] = None,
    ) -> CapturedOutcome:
        """
        Convenience method to capture a failure outcome.

        AC-2: Captures failure with categorization.

        Args:
            category: Failure category
            completion_time_seconds: Execution time
            context: Execution context
            error_message: Error message
            resources: Resource usage
            quality_score: Quality score (default 0)
            description: Optional description

        Returns:
            CapturedOutcome
        """
        failure = FailureDetails(
            category=category,
            error_message=error_message,
        )

        return self.capture(
            result=OutcomeResult.FAILURE,
            quality_score=quality_score,
            completion_time_seconds=completion_time_seconds,
            context=context,
            resources=resources,
            failure=failure,
            description=description,
        )

    def add_feedback(
        self,
        outcome_id: str,
        rating: FeedbackRating,
        comment: Optional[str] = None,
        provided_by: str = "anonymous",
        tags: Optional[List[str]] = None,
    ) -> CapturedOutcome:
        """
        Add human feedback to an outcome.

        AC-4: Integrates human feedback.

        Args:
            outcome_id: Outcome to add feedback to
            rating: Feedback rating
            comment: Optional comment
            provided_by: Who provided feedback
            tags: Optional tags

        Returns:
            Updated CapturedOutcome
        """
        # Try cache first
        outcome = self._in_memory_cache.get(outcome_id)

        # Fall back to persistence
        if not outcome:
            outcome = self._persistence.retrieve(outcome_id)

        if not outcome:
            raise ValueError(f"Outcome {outcome_id} not found")

        feedback = HumanFeedback(
            rating=rating,
            comment=comment,
            provided_by=provided_by,
            tags=tags or [],
        )

        outcome.add_feedback(feedback)

        # Re-persist with feedback
        self._persistence.persist(outcome)

        logger.info(f"Added feedback to outcome {outcome_id}: {rating.value}")

        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[CapturedOutcome]:
        """
        Retrieve an outcome by ID.

        Args:
            outcome_id: Outcome ID

        Returns:
            CapturedOutcome or None
        """
        # Check cache first
        if outcome_id in self._in_memory_cache:
            return self._in_memory_cache[outcome_id]

        # Fall back to persistence
        return self._persistence.retrieve(outcome_id)

    def list_outcomes(
        self,
        persona_id: Optional[str] = None,
        result: Optional[OutcomeResult] = None,
        limit: int = 100,
    ) -> List[CapturedOutcome]:
        """
        List outcomes with filters.

        Args:
            persona_id: Filter by persona
            result: Filter by result type
            limit: Maximum results

        Returns:
            List of outcomes
        """
        return self._persistence.list_outcomes(
            persona_id=persona_id,
            result=result,
            limit=limit,
        )

    def get_statistics(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics.

        Args:
            persona_id: Filter by persona

        Returns:
            Statistics dictionary
        """
        return self._persistence.get_statistics(persona_id=persona_id)

    def get_failure_breakdown(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Get breakdown of failures by category.

        AC-2: Provides failure analysis.

        Args:
            persona_id: Filter by persona

        Returns:
            Category to count mapping
        """
        outcomes = self.list_outcomes(
            persona_id=persona_id,
            result=OutcomeResult.FAILURE,
            limit=1000,
        )

        breakdown: Dict[str, int] = {}
        for outcome in outcomes:
            if outcome.failure:
                category = outcome.failure.category.value
                breakdown[category] = breakdown.get(category, 0) + 1

        return breakdown
