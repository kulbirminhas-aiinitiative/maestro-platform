"""
Execution History Logger - Tracks execution history for learning.

This module provides the ExecutionHistoryLogger class that records execution
history and provides insights for continuous improvement.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3032 - Implement ExecutionHistoryLogger
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to track."""
    SUCCESS_RATE = "success_rate"
    RETRY_COUNT = "retry_count"
    DURATION = "duration"
    ERROR_FREQUENCY = "error_frequency"
    RECOVERY_RATE = "recovery_rate"


@dataclass
class ExecutionRecord:
    """A single execution record."""
    execution_id: str
    task_name: str
    status: str
    attempt_count: int
    duration_seconds: float
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    recovery_applied: bool = False
    jira_bug_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "task_name": self.task_name,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "duration_seconds": self.duration_seconds,
            "error_type": self.error_type,
            "error_message": self.error_message[:200] if self.error_message else None,
            "recovery_applied": self.recovery_applied,
            "jira_bug_key": self.jira_bug_key,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExecutionInsight:
    """Insight derived from execution history."""
    insight_type: str
    title: str
    description: str
    metric_value: float
    trend: str  # "improving", "stable", "degrading"
    recommendations: List[str] = field(default_factory=list)
    related_tasks: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "insight_type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "metric_value": self.metric_value,
            "trend": self.trend,
            "recommendations": self.recommendations,
            "related_tasks": self.related_tasks,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class AggregatedMetrics:
    """Aggregated execution metrics."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    recovered_executions: int = 0
    total_retries: int = 0
    average_duration_seconds: float = 0.0
    error_types: Dict[str, int] = field(default_factory=dict)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100

    @property
    def recovery_rate(self) -> float:
        """Calculate recovery rate."""
        failed_before_recovery = self.failed_executions + self.recovered_executions
        if failed_before_recovery == 0:
            return 0.0
        return (self.recovered_executions / failed_before_recovery) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "recovered_executions": self.recovered_executions,
            "success_rate": self.success_rate,
            "recovery_rate": self.recovery_rate,
            "total_retries": self.total_retries,
            "average_duration_seconds": self.average_duration_seconds,
            "error_types": self.error_types,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


@dataclass
class LoggerConfig:
    """Configuration for history logger."""
    storage_path: str = "/tmp/execution_history.db"
    max_records: int = 100000
    retention_days: int = 90
    enable_insights: bool = True
    insight_interval_hours: int = 24


class ExecutionHistoryLogger:
    """
    Logs and analyzes execution history for continuous learning.

    This logger:
    - Stores execution records persistently
    - Calculates aggregated metrics
    - Generates insights and recommendations
    - Tracks trends over time

    Example:
        >>> logger = ExecutionHistoryLogger()
        >>> await logger.log(execution_result)
        >>> metrics = await logger.get_metrics(days=7)
        >>> insights = await logger.generate_insights()
    """

    def __init__(self, config: Optional[LoggerConfig] = None):
        """
        Initialize the history logger.

        Args:
            config: Logger configuration
        """
        self.config = config or LoggerConfig()
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_database()

        logger.info(f"ExecutionHistoryLogger initialized at {self.config.storage_path}")

    def _initialize_database(self) -> None:
        """Initialize SQLite database."""
        self._conn = sqlite3.connect(self.config.storage_path)
        cursor = self._conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_count INTEGER DEFAULT 1,
                duration_seconds REAL,
                error_type TEXT,
                error_message TEXT,
                recovery_applied INTEGER DEFAULT 0,
                jira_bug_key TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_name ON execution_records(task_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON execution_records(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON execution_records(status)
        """)

        self._conn.commit()

    async def log(self, result: Any) -> None:
        """
        Log an execution result.

        Args:
            result: ExecutionResult object to log
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        cursor = self._conn.cursor()

        try:
            # Extract error info from last attempt if failed
            error_type = None
            error_message = None

            if hasattr(result, 'attempts') and result.attempts:
                last_attempt = result.attempts[-1]
                if hasattr(last_attempt, 'error_type'):
                    error_type = last_attempt.error_type
                if hasattr(last_attempt, 'error_message'):
                    error_message = last_attempt.error_message

            cursor.execute("""
                INSERT OR REPLACE INTO execution_records
                (execution_id, task_name, status, attempt_count, duration_seconds,
                 error_type, error_message, recovery_applied, jira_bug_key, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.execution_id,
                result.task_name,
                result.final_status.value if hasattr(result.final_status, 'value') else str(result.final_status),
                result.attempt_count if hasattr(result, 'attempt_count') else len(result.attempts) if hasattr(result, 'attempts') else 1,
                result.total_duration_seconds,
                error_type,
                error_message[:1000] if error_message else None,
                1 if result.recovery_applied else 0,
                result.jira_bug_key if hasattr(result, 'jira_bug_key') else None,
                json.dumps(result.to_dict() if hasattr(result, 'to_dict') else {}),
                datetime.utcnow().isoformat(),
            ))

            self._conn.commit()
            logger.debug(f"Logged execution: {result.execution_id}")

        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
            raise

    async def get_record(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get a specific execution record."""
        if self._conn is None:
            return None

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM execution_records WHERE execution_id = ?",
            (execution_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return ExecutionRecord(
            execution_id=row[1],
            task_name=row[2],
            status=row[3],
            attempt_count=row[4],
            duration_seconds=row[5],
            error_type=row[6],
            error_message=row[7],
            recovery_applied=bool(row[8]),
            jira_bug_key=row[9],
            metadata=json.loads(row[10]) if row[10] else {},
            created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.utcnow(),
        )

    async def get_records(
        self,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        days: int = 7,
        limit: int = 100,
    ) -> List[ExecutionRecord]:
        """
        Get execution records with filters.

        Args:
            task_name: Filter by task name
            status: Filter by status
            days: Number of days to look back
            limit: Maximum records to return

        Returns:
            List of matching ExecutionRecord objects
        """
        if self._conn is None:
            return []

        cursor = self._conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = "SELECT * FROM execution_records WHERE created_at > ?"
        params: List[Any] = [cutoff]

        if task_name:
            query += " AND task_name = ?"
            params.append(task_name)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        records = []
        for row in rows:
            records.append(ExecutionRecord(
                execution_id=row[1],
                task_name=row[2],
                status=row[3],
                attempt_count=row[4],
                duration_seconds=row[5],
                error_type=row[6],
                error_message=row[7],
                recovery_applied=bool(row[8]),
                jira_bug_key=row[9],
                metadata=json.loads(row[10]) if row[10] else {},
                created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.utcnow(),
            ))

        return records

    async def get_metrics(
        self,
        task_name: Optional[str] = None,
        days: int = 7,
    ) -> AggregatedMetrics:
        """
        Get aggregated metrics for a time period.

        Args:
            task_name: Filter by task name
            days: Number of days to aggregate

        Returns:
            AggregatedMetrics with calculated values
        """
        if self._conn is None:
            return AggregatedMetrics()

        cursor = self._conn.cursor()
        cutoff = datetime.utcnow() - timedelta(days=days)

        base_query = "FROM execution_records WHERE created_at > ?"
        params: List[Any] = [cutoff.isoformat()]

        if task_name:
            base_query += " AND task_name = ?"
            params.append(task_name)

        # Total count
        cursor.execute(f"SELECT COUNT(*) {base_query}", params)
        total = cursor.fetchone()[0]

        # Success count
        cursor.execute(
            f"SELECT COUNT(*) {base_query} AND status IN ('success', 'recovered')",
            params
        )
        successful = cursor.fetchone()[0]

        # Failed count
        cursor.execute(
            f"SELECT COUNT(*) {base_query} AND status = 'failed'",
            params
        )
        failed = cursor.fetchone()[0]

        # Recovered count
        cursor.execute(
            f"SELECT COUNT(*) {base_query} AND recovery_applied = 1",
            params
        )
        recovered = cursor.fetchone()[0]

        # Total retries
        cursor.execute(
            f"SELECT SUM(attempt_count) {base_query}",
            params
        )
        retries = cursor.fetchone()[0] or 0

        # Average duration
        cursor.execute(
            f"SELECT AVG(duration_seconds) {base_query}",
            params
        )
        avg_duration = cursor.fetchone()[0] or 0.0

        # Error types
        cursor.execute(
            f"SELECT error_type, COUNT(*) {base_query} AND error_type IS NOT NULL GROUP BY error_type",
            params
        )
        error_types = {row[0]: row[1] for row in cursor.fetchall()}

        return AggregatedMetrics(
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            recovered_executions=recovered,
            total_retries=retries,
            average_duration_seconds=avg_duration,
            error_types=error_types,
            period_start=cutoff,
            period_end=datetime.utcnow(),
        )

    async def generate_insights(
        self,
        days: int = 7,
    ) -> List[ExecutionInsight]:
        """
        Generate insights from execution history.

        Args:
            days: Number of days to analyze

        Returns:
            List of ExecutionInsight objects
        """
        if not self.config.enable_insights:
            return []

        insights: List[ExecutionInsight] = []
        metrics = await self.get_metrics(days=days)

        # Success rate insight
        if metrics.total_executions > 0:
            trend = "stable"
            if metrics.success_rate < 90:
                trend = "degrading"
            elif metrics.success_rate > 98:
                trend = "improving"

            insights.append(ExecutionInsight(
                insight_type="success_rate",
                title="Execution Success Rate",
                description=f"Overall success rate is {metrics.success_rate:.1f}%",
                metric_value=metrics.success_rate,
                trend=trend,
                recommendations=[
                    "Review failing tasks for common patterns"
                ] if metrics.success_rate < 95 else [],
            ))

        # Error frequency insight
        if metrics.error_types:
            top_error = max(metrics.error_types.items(), key=lambda x: x[1])
            insights.append(ExecutionInsight(
                insight_type="error_frequency",
                title="Most Common Error",
                description=f"{top_error[0]} occurred {top_error[1]} times",
                metric_value=top_error[1],
                trend="stable",
                recommendations=[
                    f"Investigate root cause of {top_error[0]}",
                    "Consider adding specific error handling",
                ],
            ))

        # Recovery rate insight
        if metrics.failed_executions + metrics.recovered_executions > 0:
            insights.append(ExecutionInsight(
                insight_type="recovery_rate",
                title="Auto-Recovery Rate",
                description=f"Recovery rate is {metrics.recovery_rate:.1f}%",
                metric_value=metrics.recovery_rate,
                trend="stable",
                recommendations=[
                    "Review recovery strategies"
                ] if metrics.recovery_rate < 50 else [],
            ))

        return insights

    async def get_task_statistics(self, task_name: str) -> Dict[str, Any]:
        """Get detailed statistics for a specific task."""
        metrics = await self.get_metrics(task_name=task_name, days=30)
        records = await self.get_records(task_name=task_name, days=30, limit=10)

        return {
            "task_name": task_name,
            "metrics": metrics.to_dict(),
            "recent_executions": [r.to_dict() for r in records],
        }

    async def cleanup_old_records(self) -> int:
        """
        Remove records older than retention period.

        Returns:
            Number of records deleted
        """
        if self._conn is None:
            return 0

        cursor = self._conn.cursor()
        cutoff = datetime.utcnow() - timedelta(days=self.config.retention_days)

        cursor.execute(
            "DELETE FROM execution_records WHERE created_at < ?",
            (cutoff.isoformat(),)
        )

        deleted = cursor.rowcount
        self._conn.commit()

        logger.info(f"Cleaned up {deleted} old execution records")
        return deleted

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Singleton instance
_default_logger: Optional[ExecutionHistoryLogger] = None


def get_history_logger(config: Optional[LoggerConfig] = None) -> ExecutionHistoryLogger:
    """Get or create the default ExecutionHistoryLogger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = ExecutionHistoryLogger(config=config)
    return _default_logger


def reset_history_logger() -> None:
    """Reset the default logger instance."""
    global _default_logger
    if _default_logger:
        _default_logger.close()
    _default_logger = None
