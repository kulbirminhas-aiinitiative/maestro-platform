"""
Retention Policy Manager for Execution History Store

EPIC: MD-2500
AC-3: Retention policy (configurable)

This module provides configurable retention policies for execution history,
supporting time-based and count-based retention with cleanup scheduling.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .models import ExecutionStatus

logger = logging.getLogger(__name__)


class RetentionStrategy(str, Enum):
    """Retention strategy types."""
    TIME_BASED = "time_based"      # Keep records for X days
    COUNT_BASED = "count_based"    # Keep last N records per EPIC
    HYBRID = "hybrid"              # Combination of time and count
    STATUS_BASED = "status_based"  # Different retention per status


@dataclass
class RetentionConfig:
    """
    Configuration for retention policies.

    Example:
        config = RetentionConfig(
            strategy=RetentionStrategy.HYBRID,
            max_age_days=90,
            max_records_per_epic=1000,
            keep_failed_longer=True,
            failed_retention_days=365,
        )
    """
    # Strategy selection
    strategy: RetentionStrategy = RetentionStrategy.HYBRID

    # Time-based settings
    max_age_days: int = 90

    # Count-based settings
    max_records_per_epic: int = 1000
    max_total_records: int = 100000

    # Status-specific retention
    keep_failed_longer: bool = True
    failed_retention_days: int = 365
    keep_successful_days: int = 90

    # Cleanup settings
    cleanup_batch_size: int = 100
    cleanup_interval_hours: int = 24
    dry_run: bool = False

    # Callbacks
    on_delete_callback: Optional[Callable[[str], None]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy": self.strategy.value,
            "max_age_days": self.max_age_days,
            "max_records_per_epic": self.max_records_per_epic,
            "max_total_records": self.max_total_records,
            "keep_failed_longer": self.keep_failed_longer,
            "failed_retention_days": self.failed_retention_days,
            "keep_successful_days": self.keep_successful_days,
            "cleanup_batch_size": self.cleanup_batch_size,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "dry_run": self.dry_run,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetentionConfig":
        """Create from dictionary."""
        return cls(
            strategy=RetentionStrategy(data.get("strategy", "hybrid")),
            max_age_days=data.get("max_age_days", 90),
            max_records_per_epic=data.get("max_records_per_epic", 1000),
            max_total_records=data.get("max_total_records", 100000),
            keep_failed_longer=data.get("keep_failed_longer", True),
            failed_retention_days=data.get("failed_retention_days", 365),
            keep_successful_days=data.get("keep_successful_days", 90),
            cleanup_batch_size=data.get("cleanup_batch_size", 100),
            cleanup_interval_hours=data.get("cleanup_interval_hours", 24),
            dry_run=data.get("dry_run", False),
        )


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    records_deleted: int = 0
    records_archived: int = 0
    space_freed_bytes: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "records_deleted": self.records_deleted,
            "records_archived": self.records_archived,
            "space_freed_bytes": self.space_freed_bytes,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "dry_run": self.dry_run,
        }


class RetentionManager:
    """
    Manages retention policies for execution history.

    Supports:
    - Time-based retention (delete records older than X days)
    - Count-based retention (keep last N records per EPIC)
    - Hybrid retention (both time and count limits)
    - Status-based retention (different retention per status)

    Usage:
        manager = RetentionManager(store, config)
        await manager.start_scheduler()

        # Manual cleanup
        result = await manager.cleanup()
    """

    def __init__(self, store: Any, config: Optional[RetentionConfig] = None):
        """
        Initialize the retention manager.

        Args:
            store: ExecutionHistoryStore instance
            config: Retention configuration (uses defaults if None)
        """
        self.store = store
        self.config = config or RetentionConfig()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(f"RetentionManager created (strategy={self.config.strategy.value})")

    async def start_scheduler(self) -> None:
        """Start the background cleanup scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Retention scheduler started (interval={self.config.cleanup_interval_hours}h)")

    async def stop_scheduler(self) -> None:
        """Stop the background cleanup scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Retention scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Background scheduler loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                if self._running:
                    result = await self.cleanup()
                    logger.info(f"Scheduled cleanup completed: {result.records_deleted} deleted")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

    async def cleanup(self) -> CleanupResult:
        """
        Run cleanup based on configured retention policy.

        Returns:
            CleanupResult with statistics
        """
        start_time = datetime.utcnow()
        result = CleanupResult(dry_run=self.config.dry_run)

        try:
            if self.config.strategy == RetentionStrategy.TIME_BASED:
                await self._cleanup_time_based(result)
            elif self.config.strategy == RetentionStrategy.COUNT_BASED:
                await self._cleanup_count_based(result)
            elif self.config.strategy == RetentionStrategy.HYBRID:
                await self._cleanup_time_based(result)
                await self._cleanup_count_based(result)
            elif self.config.strategy == RetentionStrategy.STATUS_BASED:
                await self._cleanup_status_based(result)

        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Cleanup error: {e}")

        result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        return result

    async def _cleanup_time_based(self, result: CleanupResult) -> None:
        """Delete records older than max_age_days."""
        cutoff = datetime.utcnow() - timedelta(days=self.config.max_age_days)

        if self.store.use_memory:
            # In-memory cleanup
            to_delete = []
            for record_id, record in self.store._records.items():
                if record.created_at < cutoff:
                    # Check if failed records should be kept longer
                    if self.config.keep_failed_longer and record.status == ExecutionStatus.FAILED:
                        failed_cutoff = datetime.utcnow() - timedelta(days=self.config.failed_retention_days)
                        if record.created_at >= failed_cutoff:
                            continue
                    to_delete.append(record_id)

            if not self.config.dry_run:
                for record_id in to_delete:
                    del self.store._records[record_id]
                    if self.config.on_delete_callback:
                        self.config.on_delete_callback(str(record_id))

            result.records_deleted += len(to_delete)
        else:
            # PostgreSQL cleanup
            await self._pg_cleanup_time_based(result, cutoff)

    async def _pg_cleanup_time_based(self, result: CleanupResult, cutoff: datetime) -> None:
        """PostgreSQL time-based cleanup."""
        async with self.store._db_pool.acquire() as conn:
            # Build query based on configuration
            if self.config.keep_failed_longer:
                failed_cutoff = datetime.utcnow() - timedelta(days=self.config.failed_retention_days)

                if self.config.dry_run:
                    count = await conn.fetchval("""
                        SELECT COUNT(*) FROM execution_history
                        WHERE (created_at < $1 AND status != 'failed')
                           OR (created_at < $2 AND status = 'failed')
                    """, cutoff, failed_cutoff)
                    result.records_deleted += count
                else:
                    deleted = await conn.execute("""
                        DELETE FROM execution_history
                        WHERE (created_at < $1 AND status != 'failed')
                           OR (created_at < $2 AND status = 'failed')
                    """, cutoff, failed_cutoff)
                    result.records_deleted += int(deleted.split()[-1])
            else:
                if self.config.dry_run:
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM execution_history WHERE created_at < $1",
                        cutoff
                    )
                    result.records_deleted += count
                else:
                    deleted = await conn.execute(
                        "DELETE FROM execution_history WHERE created_at < $1",
                        cutoff
                    )
                    result.records_deleted += int(deleted.split()[-1])

    async def _cleanup_count_based(self, result: CleanupResult) -> None:
        """Keep only max_records_per_epic records per EPIC."""
        if self.store.use_memory:
            # Group by EPIC
            by_epic: Dict[str, List] = {}
            for record in self.store._records.values():
                if record.epic_key not in by_epic:
                    by_epic[record.epic_key] = []
                by_epic[record.epic_key].append(record)

            to_delete = []
            for epic_key, records in by_epic.items():
                if len(records) > self.config.max_records_per_epic:
                    # Sort by created_at, keep newest
                    sorted_records = sorted(records, key=lambda r: r.created_at, reverse=True)
                    for record in sorted_records[self.config.max_records_per_epic:]:
                        to_delete.append(record.id)

            if not self.config.dry_run:
                for record_id in to_delete:
                    if record_id in self.store._records:
                        del self.store._records[record_id]

            result.records_deleted += len(to_delete)
        else:
            await self._pg_cleanup_count_based(result)

    async def _pg_cleanup_count_based(self, result: CleanupResult) -> None:
        """PostgreSQL count-based cleanup."""
        async with self.store._db_pool.acquire() as conn:
            # Get EPICs with too many records
            epics = await conn.fetch("""
                SELECT epic_key, COUNT(*) as cnt
                FROM execution_history
                GROUP BY epic_key
                HAVING COUNT(*) > $1
            """, self.config.max_records_per_epic)

            for row in epics:
                epic_key = row["epic_key"]
                excess = row["cnt"] - self.config.max_records_per_epic

                if self.config.dry_run:
                    result.records_deleted += excess
                else:
                    # Delete oldest records for this EPIC
                    deleted = await conn.execute("""
                        DELETE FROM execution_history
                        WHERE id IN (
                            SELECT id FROM execution_history
                            WHERE epic_key = $1
                            ORDER BY created_at ASC
                            LIMIT $2
                        )
                    """, epic_key, excess)
                    result.records_deleted += int(deleted.split()[-1])

    async def _cleanup_status_based(self, result: CleanupResult) -> None:
        """Apply different retention per status."""
        status_retention = {
            ExecutionStatus.SUCCESS: self.config.keep_successful_days,
            ExecutionStatus.FAILED: self.config.failed_retention_days,
            ExecutionStatus.CANCELLED: 30,
            ExecutionStatus.PENDING: 7,
            ExecutionStatus.RUNNING: 7,
            ExecutionStatus.PARTIAL: self.config.max_age_days,
        }

        if self.store.use_memory:
            to_delete = []
            for record_id, record in self.store._records.items():
                retention_days = status_retention.get(record.status, self.config.max_age_days)
                cutoff = datetime.utcnow() - timedelta(days=retention_days)
                if record.created_at < cutoff:
                    to_delete.append(record_id)

            if not self.config.dry_run:
                for record_id in to_delete:
                    del self.store._records[record_id]

            result.records_deleted += len(to_delete)
        else:
            # PostgreSQL status-based cleanup
            async with self.store._db_pool.acquire() as conn:
                for status, days in status_retention.items():
                    cutoff = datetime.utcnow() - timedelta(days=days)
                    if self.config.dry_run:
                        count = await conn.fetchval(
                            "SELECT COUNT(*) FROM execution_history WHERE status = $1 AND created_at < $2",
                            status.value, cutoff
                        )
                        result.records_deleted += count
                    else:
                        deleted = await conn.execute(
                            "DELETE FROM execution_history WHERE status = $1 AND created_at < $2",
                            status.value, cutoff
                        )
                        result.records_deleted += int(deleted.split()[-1])

    async def get_retention_stats(self) -> Dict[str, Any]:
        """Get statistics about current retention state."""
        stats = {
            "config": self.config.to_dict(),
            "scheduler_running": self._running,
        }

        if self.store.use_memory:
            total = len(self.store._records)
            by_status = {}
            oldest = None
            newest = None

            for record in self.store._records.values():
                status = record.status.value
                by_status[status] = by_status.get(status, 0) + 1

                if oldest is None or record.created_at < oldest:
                    oldest = record.created_at
                if newest is None or record.created_at > newest:
                    newest = record.created_at

            stats["total_records"] = total
            stats["by_status"] = by_status
            stats["oldest_record"] = oldest.isoformat() if oldest else None
            stats["newest_record"] = newest.isoformat() if newest else None
        else:
            async with self.store._db_pool.acquire() as conn:
                stats["total_records"] = await conn.fetchval(
                    "SELECT COUNT(*) FROM execution_history"
                )

                rows = await conn.fetch("""
                    SELECT status, COUNT(*) as cnt
                    FROM execution_history
                    GROUP BY status
                """)
                stats["by_status"] = {row["status"]: row["cnt"] for row in rows}

                oldest = await conn.fetchval(
                    "SELECT MIN(created_at) FROM execution_history"
                )
                newest = await conn.fetchval(
                    "SELECT MAX(created_at) FROM execution_history"
                )
                stats["oldest_record"] = oldest.isoformat() if oldest else None
                stats["newest_record"] = newest.isoformat() if newest else None

        return stats
