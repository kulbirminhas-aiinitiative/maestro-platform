"""
DDE Agent Performance Tracking Service (MD-882)

Tracks AI agent performance metrics for ML-ready scoring.
Foundation for all ML-driven agent evaluation and routing.

Metrics tracked:
- Execution duration per task type
- Quality scores from contracts
- Success/failure rates
- Files generated count
- Error frequencies
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class ExecutionOutcome(Enum):
    """Outcome of an agent execution"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ExecutionMetric:
    """Single execution metric record"""
    execution_id: str
    agent_id: str
    task_type: str
    task_complexity: str  # simple, moderate, complex
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    outcome: str
    quality_score: float  # 0.0 to 1.0
    contract_fulfilled: bool
    files_generated: int
    error_count: int
    error_messages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'execution_id': self.execution_id,
            'agent_id': self.agent_id,
            'task_type': self.task_type,
            'task_complexity': self.task_complexity,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat(),
            'duration_seconds': self.duration_seconds,
            'outcome': self.outcome,
            'quality_score': self.quality_score,
            'contract_fulfilled': self.contract_fulfilled,
            'files_generated': self.files_generated,
            'error_count': self.error_count,
            'error_messages': self.error_messages,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionMetric':
        """Create from dictionary"""
        return cls(
            execution_id=data['execution_id'],
            agent_id=data['agent_id'],
            task_type=data['task_type'],
            task_complexity=data.get('task_complexity', 'moderate'),
            started_at=datetime.fromisoformat(data['started_at']),
            completed_at=datetime.fromisoformat(data['completed_at']),
            duration_seconds=data['duration_seconds'],
            outcome=data['outcome'],
            quality_score=data['quality_score'],
            contract_fulfilled=data['contract_fulfilled'],
            files_generated=data['files_generated'],
            error_count=data['error_count'],
            error_messages=data.get('error_messages', []),
            metadata=data.get('metadata', {})
        )


@dataclass
class AgentPerformanceSummary:
    """Aggregated performance summary for an agent"""
    agent_id: str
    total_executions: int
    success_rate: float
    avg_duration_seconds: float
    avg_quality_score: float
    avg_files_per_execution: float
    error_rate: float
    contract_fulfillment_rate: float
    last_execution: Optional[datetime]
    executions_by_task_type: Dict[str, int] = field(default_factory=dict)
    avg_duration_by_task_type: Dict[str, float] = field(default_factory=dict)
    quality_trend: str = "stable"  # improving, stable, declining

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'total_executions': self.total_executions,
            'success_rate': round(self.success_rate, 4),
            'avg_duration_seconds': round(self.avg_duration_seconds, 2),
            'avg_quality_score': round(self.avg_quality_score, 4),
            'avg_files_per_execution': round(self.avg_files_per_execution, 2),
            'error_rate': round(self.error_rate, 4),
            'contract_fulfillment_rate': round(self.contract_fulfillment_rate, 4),
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'executions_by_task_type': self.executions_by_task_type,
            'avg_duration_by_task_type': {k: round(v, 2) for k, v in self.avg_duration_by_task_type.items()},
            'quality_trend': self.quality_trend
        }


class PerformanceTracker:
    """
    Agent Performance Tracking Service

    Tracks and aggregates performance metrics for AI agents.
    Provides data for ML model training and rule-based scoring.
    """

    def __init__(self, storage_path: str = "data/performance"):
        """
        Initialize performance tracker.

        Args:
            storage_path: Path to store performance data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache of metrics
        self._metrics: Dict[str, List[ExecutionMetric]] = {}  # agent_id -> metrics
        self._load_metrics()

        logger.info(f"✅ PerformanceTracker initialized")
        logger.info(f"   Storage: {self.storage_path}")
        logger.info(f"   Agents tracked: {len(self._metrics)}")

    def _load_metrics(self):
        """Load metrics from storage"""
        metrics_file = self.storage_path / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file) as f:
                    data = json.load(f)
                    for agent_id, metrics_list in data.items():
                        self._metrics[agent_id] = [
                            ExecutionMetric.from_dict(m) for m in metrics_list
                        ]
                logger.info(f"   Loaded {sum(len(m) for m in self._metrics.values())} metrics")
            except Exception as e:
                logger.warning(f"   Failed to load metrics: {e}")

    def _save_metrics(self):
        """Save metrics to storage"""
        metrics_file = self.storage_path / "metrics.json"
        try:
            data = {
                agent_id: [m.to_dict() for m in metrics]
                for agent_id, metrics in self._metrics.items()
            }
            with open(metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def record_execution(
        self,
        execution_id: str,
        agent_id: str,
        task_type: str,
        task_complexity: str,
        started_at: datetime,
        completed_at: datetime,
        outcome: ExecutionOutcome,
        quality_score: float,
        contract_fulfilled: bool,
        files_generated: int,
        error_count: int = 0,
        error_messages: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ExecutionMetric:
        """
        Record an execution metric.

        Args:
            execution_id: Unique execution ID
            agent_id: Agent that performed the execution
            task_type: Type of task (e.g., 'backend_development', 'testing')
            task_complexity: Complexity level (simple, moderate, complex)
            started_at: When execution started
            completed_at: When execution completed
            outcome: Execution outcome
            quality_score: Quality score (0.0 to 1.0)
            contract_fulfilled: Whether contract was fulfilled
            files_generated: Number of files generated
            error_count: Number of errors encountered
            error_messages: List of error messages
            metadata: Additional metadata

        Returns:
            ExecutionMetric that was recorded
        """
        duration = (completed_at - started_at).total_seconds()

        metric = ExecutionMetric(
            execution_id=execution_id,
            agent_id=agent_id,
            task_type=task_type,
            task_complexity=task_complexity,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            outcome=outcome.value,
            quality_score=quality_score,
            contract_fulfilled=contract_fulfilled,
            files_generated=files_generated,
            error_count=error_count,
            error_messages=error_messages or [],
            metadata=metadata or {}
        )

        # Store metric
        if agent_id not in self._metrics:
            self._metrics[agent_id] = []
        self._metrics[agent_id].append(metric)

        # Persist to storage
        self._save_metrics()

        logger.info(f"📊 Recorded metric for {agent_id}: {outcome.value} in {duration:.1f}s (quality: {quality_score:.2f})")

        return metric

    def get_agent_summary(
        self,
        agent_id: str,
        time_window_days: int = 30
    ) -> Optional[AgentPerformanceSummary]:
        """
        Get aggregated performance summary for an agent.

        Args:
            agent_id: Agent ID
            time_window_days: Number of days to consider

        Returns:
            AgentPerformanceSummary or None if no data
        """
        if agent_id not in self._metrics:
            return None

        # Filter by time window
        cutoff = datetime.now() - timedelta(days=time_window_days)
        metrics = [m for m in self._metrics[agent_id] if m.completed_at >= cutoff]

        if not metrics:
            return None

        # Calculate aggregates
        total = len(metrics)
        successes = sum(1 for m in metrics if m.outcome == ExecutionOutcome.SUCCESS.value)
        errors = sum(m.error_count for m in metrics)
        total_possible_errors = total  # simplified
        fulfilled = sum(1 for m in metrics if m.contract_fulfilled)

        # Duration by task type
        duration_by_type: Dict[str, List[float]] = {}
        count_by_type: Dict[str, int] = {}
        for m in metrics:
            if m.task_type not in duration_by_type:
                duration_by_type[m.task_type] = []
                count_by_type[m.task_type] = 0
            duration_by_type[m.task_type].append(m.duration_seconds)
            count_by_type[m.task_type] += 1

        avg_duration_by_type = {
            k: statistics.mean(v) for k, v in duration_by_type.items()
        }

        # Quality trend (compare last 5 vs previous 5)
        quality_scores = [m.quality_score for m in sorted(metrics, key=lambda x: x.completed_at)]
        trend = "stable"
        if len(quality_scores) >= 10:
            recent = statistics.mean(quality_scores[-5:])
            previous = statistics.mean(quality_scores[-10:-5])
            if recent > previous + 0.05:
                trend = "improving"
            elif recent < previous - 0.05:
                trend = "declining"

        return AgentPerformanceSummary(
            agent_id=agent_id,
            total_executions=total,
            success_rate=successes / total if total > 0 else 0,
            avg_duration_seconds=statistics.mean([m.duration_seconds for m in metrics]),
            avg_quality_score=statistics.mean([m.quality_score for m in metrics]),
            avg_files_per_execution=statistics.mean([m.files_generated for m in metrics]),
            error_rate=errors / total_possible_errors if total_possible_errors > 0 else 0,
            contract_fulfillment_rate=fulfilled / total if total > 0 else 0,
            last_execution=max(m.completed_at for m in metrics),
            executions_by_task_type=count_by_type,
            avg_duration_by_task_type=avg_duration_by_type,
            quality_trend=trend
        )

    def get_all_agents_summary(
        self,
        time_window_days: int = 30
    ) -> List[AgentPerformanceSummary]:
        """
        Get performance summary for all agents.

        Args:
            time_window_days: Number of days to consider

        Returns:
            List of AgentPerformanceSummary
        """
        summaries = []
        for agent_id in self._metrics.keys():
            summary = self.get_agent_summary(agent_id, time_window_days)
            if summary:
                summaries.append(summary)

        # Sort by quality score descending
        summaries.sort(key=lambda x: x.avg_quality_score, reverse=True)
        return summaries

    def get_task_type_stats(
        self,
        task_type: str,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get statistics for a specific task type across all agents.

        Args:
            task_type: Task type to analyze
            time_window_days: Number of days to consider

        Returns:
            Statistics dictionary
        """
        cutoff = datetime.now() - timedelta(days=time_window_days)

        all_metrics = []
        for metrics in self._metrics.values():
            for m in metrics:
                if m.task_type == task_type and m.completed_at >= cutoff:
                    all_metrics.append(m)

        if not all_metrics:
            return {'task_type': task_type, 'count': 0}

        return {
            'task_type': task_type,
            'count': len(all_metrics),
            'avg_duration': statistics.mean([m.duration_seconds for m in all_metrics]),
            'avg_quality': statistics.mean([m.quality_score for m in all_metrics]),
            'success_rate': sum(1 for m in all_metrics if m.outcome == ExecutionOutcome.SUCCESS.value) / len(all_metrics),
            'agents': list(set(m.agent_id for m in all_metrics))
        }

    def get_metrics_for_ml_training(
        self,
        time_window_days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get metrics in format suitable for ML model training.

        Args:
            time_window_days: Number of days to include

        Returns:
            List of feature dictionaries for ML training
        """
        cutoff = datetime.now() - timedelta(days=time_window_days)

        training_data = []
        for agent_id, metrics in self._metrics.items():
            for m in metrics:
                if m.completed_at >= cutoff:
                    # Extract features for ML
                    training_data.append({
                        # Task features
                        'task_type': m.task_type,
                        'task_complexity': m.task_complexity,

                        # Agent features (would be joined with agent profile)
                        'agent_id': m.agent_id,

                        # Execution features
                        'duration_seconds': m.duration_seconds,
                        'files_generated': m.files_generated,
                        'error_count': m.error_count,

                        # Labels for training
                        'quality_score': m.quality_score,  # Regression target
                        'success': 1 if m.outcome == ExecutionOutcome.SUCCESS.value else 0,  # Classification target
                        'contract_fulfilled': 1 if m.contract_fulfilled else 0
                    })

        return training_data

    def get_best_agent_for_task(
        self,
        task_type: str,
        time_window_days: int = 30
    ) -> Optional[str]:
        """
        Get the best performing agent for a task type.

        This is a simple rule-based selection.
        ML model will replace this in MD-884.

        Args:
            task_type: Task type
            time_window_days: Number of days to consider

        Returns:
            Best agent ID or None
        """
        cutoff = datetime.now() - timedelta(days=time_window_days)

        agent_scores: Dict[str, List[float]] = {}

        for agent_id, metrics in self._metrics.items():
            for m in metrics:
                if m.task_type == task_type and m.completed_at >= cutoff:
                    if agent_id not in agent_scores:
                        agent_scores[agent_id] = []
                    # Combine quality and success
                    score = m.quality_score * (1 if m.contract_fulfilled else 0.5)
                    agent_scores[agent_id].append(score)

        if not agent_scores:
            return None

        # Find agent with best average score
        best_agent = max(
            agent_scores.keys(),
            key=lambda a: statistics.mean(agent_scores[a])
        )

        return best_agent

    def export_to_parquet(self, output_path: str) -> str:
        """
        Export metrics to Parquet format for ML training.

        Args:
            output_path: Path for output file

        Returns:
            Path to exported file
        """
        try:
            import pandas as pd

            training_data = self.get_metrics_for_ml_training()
            if not training_data:
                logger.warning("No training data to export")
                return ""

            df = pd.DataFrame(training_data)
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_file, index=False)

            logger.info(f"✅ Exported {len(training_data)} records to {output_file}")
            return str(output_file)

        except ImportError:
            logger.warning("pandas not available for Parquet export")
            # Fallback to JSON
            json_path = output_path.replace('.parquet', '.json')
            with open(json_path, 'w') as f:
                json.dump(self.get_metrics_for_ml_training(), f, indent=2)
            return json_path


# Global instance
_tracker: Optional[PerformanceTracker] = None


def get_performance_tracker(storage_path: str = "data/performance") -> PerformanceTracker:
    """Get or create global performance tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker(storage_path)
    return _tracker


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create tracker
    tracker = get_performance_tracker()

    # Record some sample executions
    tracker.record_execution(
        execution_id="exec-001",
        agent_id="requirement_analyst",
        task_type="requirements_analysis",
        task_complexity="simple",
        started_at=datetime.now() - timedelta(minutes=5),
        completed_at=datetime.now(),
        outcome=ExecutionOutcome.SUCCESS,
        quality_score=0.92,
        contract_fulfilled=True,
        files_generated=3,
        error_count=0
    )

    tracker.record_execution(
        execution_id="exec-002",
        agent_id="backend_developer",
        task_type="backend_development",
        task_complexity="moderate",
        started_at=datetime.now() - timedelta(minutes=10),
        completed_at=datetime.now(),
        outcome=ExecutionOutcome.SUCCESS,
        quality_score=0.98,
        contract_fulfilled=True,
        files_generated=6,
        error_count=0
    )

    # Get summaries
    print("\n=== Agent Summaries ===")
    for summary in tracker.get_all_agents_summary():
        print(f"\n{summary.agent_id}:")
        print(f"  Executions: {summary.total_executions}")
        print(f"  Success rate: {summary.success_rate:.1%}")
        print(f"  Avg quality: {summary.avg_quality_score:.2f}")
        print(f"  Trend: {summary.quality_trend}")

    # Get ML training data
    print("\n=== ML Training Data ===")
    training_data = tracker.get_metrics_for_ml_training()
    print(f"Records available: {len(training_data)}")
