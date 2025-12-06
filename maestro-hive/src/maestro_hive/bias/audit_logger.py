"""
Bias Audit Logger (MD-2157)

EU AI Act Compliance - Article 10

Records all task assignment, evaluation, and scoring decisions
for audit and analysis purposes.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json
from pathlib import Path

from .models import (
    AuditRecord,
    AuditEventType,
    BiasVectorType
)

logger = logging.getLogger(__name__)


class BiasAuditLogger:
    """
    Audit logger for bias-related decisions.

    Records all decisions made by the DDE for post-hoc
    fairness analysis and compliance auditing.
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        max_records: int = 10000,
        auto_persist: bool = True
    ):
        """
        Initialize the audit logger.

        Args:
            log_dir: Directory for persisting audit logs
            max_records: Maximum records to keep in memory
            auto_persist: Whether to automatically persist records
        """
        self.log_dir = Path(log_dir) if log_dir else None
        self.max_records = max_records
        self.auto_persist = auto_persist

        # In-memory storage
        self._records: List[AuditRecord] = []
        self._records_by_agent: Dict[str, List[str]] = defaultdict(list)
        self._records_by_task: Dict[str, List[str]] = defaultdict(list)
        self._records_by_type: Dict[AuditEventType, List[str]] = defaultdict(list)

        # Statistics
        self._stats = {
            'total_records': 0,
            'records_by_type': defaultdict(int),
            'bias_indicators_count': 0
        }

        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info("BiasAuditLogger initialized")

    def log_task_assignment(
        self,
        agent_id: str,
        task_id: str,
        task_type: str,
        decision_factors: Dict[str, float],
        alternatives: List[str],
        fairness_score: float = 1.0,
        fairness_adjustments: Optional[Dict[str, float]] = None,
        bias_indicators: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """
        Log a task assignment decision.

        Args:
            agent_id: ID of the selected agent
            task_id: ID of the assigned task
            task_type: Type of task
            decision_factors: Factors contributing to the decision
            alternatives: Alternative agents considered
            fairness_score: Computed fairness score
            fairness_adjustments: Any fairness adjustments applied
            bias_indicators: Any detected bias indicators
            context: Additional context

        Returns:
            Created audit record
        """
        record = AuditRecord(
            event_type=AuditEventType.TASK_ASSIGNMENT,
            agent_id=agent_id,
            task_id=task_id,
            task_type=task_type,
            decision=f"Assigned task {task_id} to agent {agent_id}",
            decision_factors=decision_factors,
            alternatives_considered=alternatives,
            fairness_score=fairness_score,
            fairness_adjustments=fairness_adjustments or {},
            bias_indicators=bias_indicators or [],
            context=context or {}
        )

        return self._store_record(record)

    def log_agent_evaluation(
        self,
        agent_id: str,
        evaluation_scores: Dict[str, float],
        overall_score: float,
        fairness_adjustments: Optional[Dict[str, float]] = None,
        bias_indicators: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """
        Log an agent evaluation decision.

        Args:
            agent_id: ID of the evaluated agent
            evaluation_scores: Scores for each evaluation dimension
            overall_score: Overall evaluation score
            fairness_adjustments: Any fairness adjustments applied
            bias_indicators: Any detected bias indicators
            context: Additional context

        Returns:
            Created audit record
        """
        record = AuditRecord(
            event_type=AuditEventType.AGENT_EVALUATION,
            agent_id=agent_id,
            decision=f"Evaluated agent {agent_id} with score {overall_score:.2f}",
            decision_factors=evaluation_scores,
            fairness_score=overall_score,
            fairness_adjustments=fairness_adjustments or {},
            bias_indicators=bias_indicators or [],
            context=context or {}
        )

        return self._store_record(record)

    def log_quality_scoring(
        self,
        agent_id: str,
        task_id: str,
        quality_factors: Dict[str, float],
        quality_score: float,
        fairness_adjustments: Optional[Dict[str, float]] = None,
        bias_indicators: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """
        Log a quality scoring decision.

        Args:
            agent_id: ID of the scored agent
            task_id: ID of the scored task
            quality_factors: Factors contributing to quality score
            quality_score: Final quality score
            fairness_adjustments: Any fairness adjustments applied
            bias_indicators: Any detected bias indicators
            context: Additional context

        Returns:
            Created audit record
        """
        record = AuditRecord(
            event_type=AuditEventType.QUALITY_SCORING,
            agent_id=agent_id,
            task_id=task_id,
            decision=f"Quality score for {agent_id}/{task_id}: {quality_score:.2f}",
            decision_factors=quality_factors,
            fairness_score=quality_score,
            fairness_adjustments=fairness_adjustments or {},
            bias_indicators=bias_indicators or [],
            context=context or {}
        )

        return self._store_record(record)

    def log_threshold_decision(
        self,
        threshold_name: str,
        threshold_value: float,
        actual_value: float,
        decision: str,
        adaptive_adjustment: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """
        Log a threshold-based decision.

        Args:
            threshold_name: Name of the threshold
            threshold_value: Threshold value used
            actual_value: Actual value compared against threshold
            decision: Decision made (pass/fail)
            adaptive_adjustment: Any adaptive threshold adjustment
            context: Additional context

        Returns:
            Created audit record
        """
        record = AuditRecord(
            event_type=AuditEventType.THRESHOLD_DECISION,
            decision=f"{threshold_name}: {actual_value:.2f} vs {threshold_value:.2f} -> {decision}",
            decision_factors={
                'threshold_name': threshold_name,
                'threshold_value': threshold_value,
                'actual_value': actual_value
            },
            fairness_adjustments={'adaptive_adjustment': adaptive_adjustment} if adaptive_adjustment else {},
            context=context or {}
        )

        return self._store_record(record)

    def log_fairness_adjustment(
        self,
        agent_id: str,
        adjustment_type: BiasVectorType,
        original_value: float,
        adjusted_value: float,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """
        Log a fairness adjustment.

        Args:
            agent_id: ID of the affected agent
            adjustment_type: Type of bias being addressed
            original_value: Original value before adjustment
            adjusted_value: Value after adjustment
            reason: Reason for the adjustment
            context: Additional context

        Returns:
            Created audit record
        """
        record = AuditRecord(
            event_type=AuditEventType.FAIRNESS_ADJUSTMENT,
            agent_id=agent_id,
            decision=f"Fairness adjustment for {agent_id}: {original_value:.2f} -> {adjusted_value:.2f}",
            decision_factors={
                'original_value': original_value,
                'adjusted_value': adjusted_value,
                'delta': adjusted_value - original_value
            },
            fairness_adjustments={adjustment_type.value: adjusted_value - original_value},
            context={'reason': reason, **(context or {})}
        )

        return self._store_record(record)

    def log_cooling_off(
        self,
        agent_id: str,
        duration_seconds: float,
        reason: str,
        recent_assignments: int,
        context: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """
        Log a cooling-off period application.

        Args:
            agent_id: ID of the agent in cooling-off
            duration_seconds: Duration of the cooling-off period
            reason: Reason for the cooling-off
            recent_assignments: Number of recent assignments
            context: Additional context

        Returns:
            Created audit record
        """
        record = AuditRecord(
            event_type=AuditEventType.COOLING_OFF_APPLIED,
            agent_id=agent_id,
            decision=f"Cooling-off for {agent_id}: {duration_seconds:.0f}s",
            decision_factors={
                'duration_seconds': duration_seconds,
                'recent_assignments': recent_assignments
            },
            bias_indicators=[f"High assignment frequency: {recent_assignments}"],
            context={'reason': reason, **(context or {})}
        )

        return self._store_record(record)

    def _store_record(self, record: AuditRecord) -> AuditRecord:
        """Store an audit record."""
        self._records.append(record)

        # Update indexes
        if record.agent_id:
            self._records_by_agent[record.agent_id].append(record.record_id)
        if record.task_id:
            self._records_by_task[record.task_id].append(record.record_id)
        self._records_by_type[record.event_type].append(record.record_id)

        # Update stats
        self._stats['total_records'] += 1
        self._stats['records_by_type'][record.event_type.value] += 1
        if record.bias_indicators:
            self._stats['bias_indicators_count'] += len(record.bias_indicators)

        # Trim if needed
        if len(self._records) > self.max_records:
            self._trim_records()

        # Auto-persist if enabled
        if self.auto_persist and self.log_dir:
            self._persist_record(record)

        return record

    def _trim_records(self):
        """Trim old records to stay within max_records limit."""
        trim_count = len(self._records) - self.max_records
        if trim_count > 0:
            # Remove oldest records
            removed = self._records[:trim_count]
            self._records = self._records[trim_count:]

            # Update indexes
            for record in removed:
                if record.agent_id and record.record_id in self._records_by_agent[record.agent_id]:
                    self._records_by_agent[record.agent_id].remove(record.record_id)
                if record.task_id and record.record_id in self._records_by_task[record.task_id]:
                    self._records_by_task[record.task_id].remove(record.record_id)
                if record.record_id in self._records_by_type[record.event_type]:
                    self._records_by_type[record.event_type].remove(record.record_id)

    def _persist_record(self, record: AuditRecord):
        """Persist a record to disk."""
        if not self.log_dir:
            return

        date_str = record.timestamp.strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{date_str}.jsonl"

        with open(log_file, 'a') as f:
            f.write(json.dumps(record.to_dict()) + '\n')

    def get_records(
        self,
        event_type: Optional[AuditEventType] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """
        Query audit records.

        Args:
            event_type: Filter by event type
            agent_id: Filter by agent ID
            task_id: Filter by task ID
            since: Filter records after this time
            limit: Maximum records to return

        Returns:
            List of matching audit records
        """
        records = self._records

        if event_type:
            record_ids = set(self._records_by_type.get(event_type, []))
            records = [r for r in records if r.record_id in record_ids]

        if agent_id:
            record_ids = set(self._records_by_agent.get(agent_id, []))
            records = [r for r in records if r.record_id in record_ids]

        if task_id:
            record_ids = set(self._records_by_task.get(task_id, []))
            records = [r for r in records if r.record_id in record_ids]

        if since:
            records = [r for r in records if r.timestamp >= since]

        # Sort by timestamp descending and limit
        records = sorted(records, key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def get_bias_indicators(
        self,
        since: Optional[datetime] = None,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all bias indicators from recent records.

        Args:
            since: Filter records after this time
            agent_id: Filter by agent ID

        Returns:
            List of bias indicators with context
        """
        records = self.get_records(
            agent_id=agent_id,
            since=since,
            limit=self.max_records
        )

        indicators = []
        for record in records:
            for indicator in record.bias_indicators:
                indicators.append({
                    'indicator': indicator,
                    'record_id': record.record_id,
                    'event_type': record.event_type.value,
                    'agent_id': record.agent_id,
                    'task_id': record.task_id,
                    'timestamp': record.timestamp.isoformat()
                })

        return indicators

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics."""
        return {
            'total_records': self._stats['total_records'],
            'records_by_type': dict(self._stats['records_by_type']),
            'bias_indicators_count': self._stats['bias_indicators_count'],
            'unique_agents': len(self._records_by_agent),
            'unique_tasks': len(self._records_by_task),
            'in_memory_records': len(self._records)
        }

    def export_records(
        self,
        output_path: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> int:
        """
        Export records to a JSON file.

        Args:
            output_path: Path to output file
            since: Export records after this time
            until: Export records before this time

        Returns:
            Number of records exported
        """
        records = self._records

        if since:
            records = [r for r in records if r.timestamp >= since]
        if until:
            records = [r for r in records if r.timestamp <= until]

        output_path = Path(output_path)
        with open(output_path, 'w') as f:
            json.dump(
                [r.to_dict() for r in records],
                f,
                indent=2
            )

        return len(records)


# Global instance
_audit_logger: Optional[BiasAuditLogger] = None


def get_audit_logger() -> BiasAuditLogger:
    """Get or create global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = BiasAuditLogger()
    return _audit_logger
