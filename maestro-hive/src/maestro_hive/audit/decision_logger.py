"""
Decision Logger for AI decision audit trail.

EU AI Act Article 12 Compliance:
Records all AI decisions with reasoning for traceability.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from .models import (
    DecisionCandidate,
    DecisionRecord,
    DecisionType,
    AuditQueryResult
)


logger = logging.getLogger(__name__)


class DecisionLogger:
    """
    Logs AI decisions with full context and reasoning.

    Captures why agent X was selected, what alternatives were
    considered, and the factors that influenced the decision.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_records_in_memory: int = 10000,
        auto_persist: bool = True,
        algorithm_version: str = "1.0"
    ):
        """
        Initialize the decision logger.

        Args:
            storage_path: Path for persistent storage
            max_records_in_memory: Maximum records to keep in memory
            auto_persist: Whether to auto-persist on threshold
            algorithm_version: Version of the decision algorithm
        """
        self.storage_path = storage_path or Path("./audit/decisions")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.max_records_in_memory = max_records_in_memory
        self.auto_persist = auto_persist
        self.algorithm_version = algorithm_version

        self._records: List[DecisionRecord] = []
        self._records_by_context: Dict[str, List[DecisionRecord]] = {}

        logger.info(
            f"DecisionLogger initialized with storage at {self.storage_path}"
        )

    def log_decision(
        self,
        decision_type: DecisionType,
        context_id: str,
        context_type: str,
        selected_id: str,
        selected_type: str,
        selected_score: float,
        candidates: List[DecisionCandidate],
        decision_factors: Dict[str, float],
        reasoning_summary: str,
        confidence_score: float = 0.0,
        requesting_user: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> DecisionRecord:
        """
        Log an AI decision with full context.

        Args:
            decision_type: Type of decision being made
            context_id: ID of the context (task, workflow, etc.)
            context_type: Type of context
            selected_id: ID of the selected option
            selected_type: Type of selected option
            selected_score: Score of the selected option
            candidates: List of all candidates considered
            decision_factors: Factors and their weights in the decision
            reasoning_summary: Human-readable summary of reasoning
            confidence_score: Confidence in the decision (0-1)
            requesting_user: User who triggered the decision
            session_id: Session identifier

        Returns:
            The created DecisionRecord
        """
        record = DecisionRecord(
            decision_type=decision_type,
            context_id=context_id,
            context_type=context_type,
            selected_id=selected_id,
            selected_type=selected_type,
            selected_score=selected_score,
            candidates=candidates,
            decision_factors=decision_factors,
            reasoning_summary=reasoning_summary,
            confidence_score=confidence_score,
            algorithm_version=self.algorithm_version,
            requesting_user=requesting_user,
            session_id=session_id
        )

        self._records.append(record)

        # Index by context
        if context_id not in self._records_by_context:
            self._records_by_context[context_id] = []
        self._records_by_context[context_id].append(record)

        logger.debug(
            f"Logged {decision_type.value} decision: "
            f"selected {selected_id} from {len(candidates)} candidates"
        )

        # Auto-persist if threshold reached
        if self.auto_persist and len(self._records) >= self.max_records_in_memory:
            self._persist_to_storage()

        return record

    def log_agent_selection(
        self,
        task_id: str,
        selected_agent_id: str,
        agent_scores: Dict[str, float],
        selection_factors: Dict[str, float],
        reasoning: str,
        requesting_user: Optional[str] = None
    ) -> DecisionRecord:
        """
        Convenience method for logging agent selection decisions.

        Args:
            task_id: ID of the task
            selected_agent_id: ID of the selected agent
            agent_scores: Scores for all candidate agents
            selection_factors: Factors considered in selection
            reasoning: Human-readable reasoning
            requesting_user: User who triggered selection

        Returns:
            The created DecisionRecord
        """
        # Build candidate list from scores
        sorted_agents = sorted(
            agent_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        candidates = []
        for rank, (agent_id, score) in enumerate(sorted_agents, 1):
            candidate = DecisionCandidate(
                candidate_id=agent_id,
                candidate_type="agent",
                score=score,
                ranking=rank,
                factors=selection_factors.copy(),
                disqualification_reason=None if score > 0 else "Score below threshold"
            )
            candidates.append(candidate)

        return self.log_decision(
            decision_type=DecisionType.AGENT_SELECTION,
            context_id=task_id,
            context_type="task",
            selected_id=selected_agent_id,
            selected_type="agent",
            selected_score=agent_scores.get(selected_agent_id, 0.0),
            candidates=candidates,
            decision_factors=selection_factors,
            reasoning_summary=reasoning,
            confidence_score=self._calculate_confidence(agent_scores),
            requesting_user=requesting_user
        )

    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """
        Calculate confidence based on score distribution.

        Higher confidence when there's a clear winner.
        """
        if not scores:
            return 0.0

        sorted_scores = sorted(scores.values(), reverse=True)

        if len(sorted_scores) == 1:
            return 1.0

        # Confidence based on gap between top two
        top_score = sorted_scores[0]
        second_score = sorted_scores[1]

        if top_score == 0:
            return 0.0

        gap_ratio = (top_score - second_score) / top_score
        return min(1.0, 0.5 + gap_ratio * 0.5)

    def get_decisions_for_context(
        self,
        context_id: str,
        decision_type: Optional[DecisionType] = None
    ) -> List[DecisionRecord]:
        """
        Get all decisions for a specific context.

        Args:
            context_id: The context ID to filter by
            decision_type: Optional filter by decision type

        Returns:
            List of matching DecisionRecords
        """
        records = self._records_by_context.get(context_id, [])

        if decision_type:
            records = [r for r in records if r.decision_type == decision_type]

        return records

    def query_decisions(
        self,
        decision_type: Optional[DecisionType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        context_type: Optional[str] = None,
        requesting_user: Optional[str] = None,
        min_confidence: Optional[float] = None,
        page: int = 1,
        page_size: int = 100
    ) -> AuditQueryResult:
        """
        Query decision records with filters.

        Args:
            decision_type: Filter by decision type
            start_time: Start of time range
            end_time: End of time range
            context_type: Filter by context type
            requesting_user: Filter by user
            min_confidence: Minimum confidence threshold
            page: Page number (1-indexed)
            page_size: Records per page

        Returns:
            AuditQueryResult with matching records
        """
        import time
        start = time.time()

        filtered = self._records.copy()

        # Apply filters
        if decision_type:
            filtered = [r for r in filtered if r.decision_type == decision_type]

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]

        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        if context_type:
            filtered = [r for r in filtered if r.context_type == context_type]

        if requesting_user:
            filtered = [r for r in filtered if r.requesting_user == requesting_user]

        if min_confidence is not None:
            filtered = [r for r in filtered if r.confidence_score >= min_confidence]

        # Pagination
        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_records = filtered[start_idx:end_idx]

        query_time_ms = int((time.time() - start) * 1000)

        return AuditQueryResult(
            records=[r.to_dict() for r in page_records],
            total_count=total_count,
            page=page,
            page_size=page_size,
            query_time_ms=query_time_ms,
            filters_applied={
                "decision_type": decision_type.value if decision_type else None,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "context_type": context_type,
                "requesting_user": requesting_user,
                "min_confidence": min_confidence
            }
        )

    def get_decision_by_id(self, decision_id: UUID) -> Optional[DecisionRecord]:
        """Get a specific decision by ID."""
        for record in self._records:
            if record.id == decision_id:
                return record
        return None

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about logged decisions.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary of statistics
        """
        filtered = self._records.copy()

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        # Count by type
        by_type = {}
        for record in filtered:
            type_key = record.decision_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

        # Average confidence
        confidences = [r.confidence_score for r in filtered]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Average candidates considered
        candidate_counts = [len(r.candidates) for r in filtered]
        avg_candidates = sum(candidate_counts) / len(candidate_counts) if candidate_counts else 0.0

        return {
            "total_decisions": len(filtered),
            "decisions_by_type": by_type,
            "average_confidence": round(avg_confidence, 3),
            "average_candidates_considered": round(avg_candidates, 2),
            "unique_contexts": len(set(r.context_id for r in filtered)),
            "unique_users": len(set(r.requesting_user for r in filtered if r.requesting_user)),
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }

    def _persist_to_storage(self) -> None:
        """Persist records to storage and clear memory."""
        if not self._records:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"decisions_{timestamp}.json"
        filepath = self.storage_path / filename

        records_data = [r.to_dict() for r in self._records]

        with open(filepath, "w") as f:
            json.dump(records_data, f, indent=2)

        logger.info(f"Persisted {len(self._records)} decisions to {filepath}")

        # Clear memory
        self._records = []
        self._records_by_context = {}

    def export_for_audit(
        self,
        start_time: datetime,
        end_time: datetime,
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Export decisions for external audit.

        Args:
            start_time: Start of export range
            end_time: End of export range
            output_path: Path for export file

        Returns:
            Export metadata
        """
        result = self.query_decisions(
            start_time=start_time,
            end_time=end_time,
            page_size=100000  # Large page to get all
        )

        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "date_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_records": result.total_count,
            "algorithm_version": self.algorithm_version,
            "records": result.records
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        # Calculate hash for integrity
        import hashlib
        with open(output_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        return {
            "export_path": str(output_path),
            "record_count": result.total_count,
            "file_hash": file_hash,
            "exported_at": datetime.utcnow().isoformat()
        }

    def clear(self) -> None:
        """Clear all in-memory records (for testing)."""
        self._records = []
        self._records_by_context = {}
