"""
Enterprise database monitoring for MAESTRO.

Provides:
- DatabaseMetrics for Prometheus metrics collection
- DatabaseMonitor for health checks and slow query detection
- QueryLogger for SQL query performance tracking
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine

from .exceptions import HealthCheckException


def _get_logger():
    """Lazy logger initialization to avoid circular imports."""
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except ImportError:
        import logging
        return logging.getLogger(__name__)


logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


# =============================================================================
# Enums
# =============================================================================

class HealthStatus(str, Enum):
    """Database health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MetricType(str, Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class QueryInfo:
    """Information about a single query execution."""

    query: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    params: Optional[Dict] = None
    rows_affected: int = 0
    is_slow: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query[:200] + "..." if len(self.query) > 200 else self.query,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp.isoformat(),
            "rows_affected": self.rows_affected,
            "is_slow": self.is_slow,
            "error": self.error,
        }


@dataclass
class PoolStats:
    """Connection pool statistics."""

    pool_size: int = 0
    checked_in: int = 0
    checked_out: int = 0
    overflow: int = 0
    invalid: int = 0
    recycled: int = 0

    @property
    def utilization(self) -> float:
        """Calculate pool utilization percentage."""
        total = self.pool_size + self.overflow
        if total == 0:
            return 0.0
        return (self.checked_out / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pool_size": self.pool_size,
            "checked_in": self.checked_in,
            "checked_out": self.checked_out,
            "overflow": self.overflow,
            "invalid": self.invalid,
            "utilization_percent": round(self.utilization, 2),
        }


@dataclass
class DatabaseMetrics:
    """
    Aggregated database metrics.

    Collects metrics for:
    - Query performance
    - Connection pool usage
    - Error rates
    - Health checks
    """

    # Query metrics
    total_queries: int = 0
    slow_queries: int = 0
    failed_queries: int = 0
    total_query_time_ms: float = 0.0

    # Connection metrics
    total_connections: int = 0
    connection_errors: int = 0
    connection_timeouts: int = 0

    # Health metrics
    health_check_count: int = 0
    health_check_failures: int = 0

    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def avg_query_time_ms(self) -> float:
        """Calculate average query time."""
        if self.total_queries == 0:
            return 0.0
        return self.total_query_time_ms / self.total_queries

    @property
    def slow_query_rate(self) -> float:
        """Calculate slow query percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.slow_queries / self.total_queries) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.failed_queries / self.total_queries) * 100

    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "queries": {
                "total": self.total_queries,
                "slow": self.slow_queries,
                "failed": self.failed_queries,
                "avg_time_ms": round(self.avg_query_time_ms, 2),
                "slow_rate_percent": round(self.slow_query_rate, 2),
                "error_rate_percent": round(self.error_rate, 2),
            },
            "connections": {
                "total": self.total_connections,
                "errors": self.connection_errors,
                "timeouts": self.connection_timeouts,
            },
            "health_checks": {
                "total": self.health_check_count,
                "failures": self.health_check_failures,
            },
            "uptime_seconds": round(self.uptime_seconds, 0),
            "last_updated": self.last_updated.isoformat(),
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_queries = 0
        self.slow_queries = 0
        self.failed_queries = 0
        self.total_query_time_ms = 0.0
        self.total_connections = 0
        self.connection_errors = 0
        self.connection_timeouts = 0
        self.health_check_count = 0
        self.health_check_failures = 0
        self.start_time = datetime.utcnow()
        self.last_updated = datetime.utcnow()


# =============================================================================
# Query Logger
# =============================================================================

class QueryLogger:
    """
    SQL query performance logger.

    Tracks query execution times and identifies slow queries.

    Example:
        ```python
        query_logger = QueryLogger(slow_threshold_ms=100)
        query_logger.attach_to_engine(engine)

        # Queries are automatically logged
        await session.execute(select(User))

        # Get slow queries
        slow = query_logger.get_slow_queries(limit=10)
        ```
    """

    def __init__(
        self,
        slow_threshold_ms: float = 100.0,
        max_history: int = 1000,
        log_all_queries: bool = False,
        log_params: bool = False
    ):
        """
        Initialize query logger.

        Args:
            slow_threshold_ms: Threshold for slow query detection (ms)
            max_history: Maximum queries to keep in history
            log_all_queries: Log all queries (not just slow ones)
            log_params: Include query parameters in logs
        """
        self._slow_threshold_ms = slow_threshold_ms
        self._max_history = max_history
        self._log_all_queries = log_all_queries
        self._log_params = log_params

        self._history: Deque[QueryInfo] = deque(maxlen=max_history)
        self._slow_queries: Deque[QueryInfo] = deque(maxlen=max_history)

        # Query timing tracking
        self._active_queries: Dict[int, float] = {}

    def attach_to_engine(self, engine: AsyncEngine) -> None:
        """
        Attach query logging to SQLAlchemy engine.

        Args:
            engine: Async SQLAlchemy engine
        """
        sync_engine = engine.sync_engine

        @event.listens_for(sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault("query_start_time", []).append(time.perf_counter())

        @event.listens_for(sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            start_times = conn.info.get("query_start_time", [])
            if start_times:
                start_time = start_times.pop()
                duration_ms = (time.perf_counter() - start_time) * 1000

                self._record_query(
                    query=statement,
                    duration_ms=duration_ms,
                    params=parameters if self._log_params else None,
                    rows_affected=cursor.rowcount if cursor.rowcount >= 0 else 0
                )

        @event.listens_for(sync_engine, "handle_error")
        def handle_error(exception_context):
            self._record_query(
                query=str(exception_context.statement or ""),
                duration_ms=0,
                error=str(exception_context.original_exception)
            )

        logger.info(
            "Query logger attached to engine",
            slow_threshold_ms=self._slow_threshold_ms
        )

    def _record_query(
        self,
        query: str,
        duration_ms: float,
        params: Optional[Dict] = None,
        rows_affected: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Record a query execution."""
        is_slow = duration_ms >= self._slow_threshold_ms

        query_info = QueryInfo(
            query=query,
            duration_ms=duration_ms,
            params=params,
            rows_affected=rows_affected,
            is_slow=is_slow,
            error=error
        )

        # Add to history if logging all or if slow/error
        if self._log_all_queries or is_slow or error:
            self._history.append(query_info)

        # Track slow queries separately
        if is_slow:
            self._slow_queries.append(query_info)
            logger.warning(
                "Slow query detected",
                duration_ms=round(duration_ms, 2),
                query=query[:100] + "..." if len(query) > 100 else query
            )

        # Log errors
        if error:
            logger.error(
                "Query error",
                error=error,
                query=query[:100] + "..." if len(query) > 100 else query
            )

    def get_history(self, limit: int = 100) -> List[QueryInfo]:
        """Get recent query history."""
        return list(self._history)[-limit:]

    def get_slow_queries(self, limit: int = 100) -> List[QueryInfo]:
        """Get recent slow queries."""
        return list(self._slow_queries)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        total = len(self._history)
        slow = len(self._slow_queries)
        errors = sum(1 for q in self._history if q.error)

        if total > 0:
            avg_duration = sum(q.duration_ms for q in self._history) / total
            max_duration = max(q.duration_ms for q in self._history)
        else:
            avg_duration = 0
            max_duration = 0

        return {
            "total_queries": total,
            "slow_queries": slow,
            "error_queries": errors,
            "avg_duration_ms": round(avg_duration, 2),
            "max_duration_ms": round(max_duration, 2),
            "slow_threshold_ms": self._slow_threshold_ms,
        }

    def clear(self) -> None:
        """Clear query history."""
        self._history.clear()
        self._slow_queries.clear()


# =============================================================================
# Database Monitor
# =============================================================================

class DatabaseMonitor:
    """
    Comprehensive database monitoring.

    Provides:
    - Health checks
    - Metrics collection
    - Query logging
    - Alerting hooks

    Example:
        ```python
        monitor = DatabaseMonitor(
            write_engine=primary_engine,
            read_engines=[replica_engine]
        )

        await monitor.start()

        # Get health status
        health = await monitor.health_check()

        # Get metrics
        metrics = monitor.get_metrics()

        await monitor.stop()
        ```
    """

    def __init__(
        self,
        write_engine: AsyncEngine,
        read_engines: Optional[List[AsyncEngine]] = None,
        health_check_interval: int = 30,
        slow_query_threshold_ms: float = 100.0,
        enable_query_logging: bool = True,
        on_health_change: Optional[Callable[[HealthStatus], None]] = None
    ):
        """
        Initialize database monitor.

        Args:
            write_engine: Primary database engine
            read_engines: Replica database engines
            health_check_interval: Seconds between health checks
            slow_query_threshold_ms: Slow query threshold (ms)
            enable_query_logging: Enable query performance logging
            on_health_change: Callback when health status changes
        """
        self._write_engine = write_engine
        self._read_engines = read_engines or []
        self._health_check_interval = health_check_interval
        self._on_health_change = on_health_change

        # Components
        self._metrics = DatabaseMetrics()
        self._query_logger = QueryLogger(
            slow_threshold_ms=slow_query_threshold_ms,
            log_all_queries=False
        ) if enable_query_logging else None

        # State
        self._running = False
        self._health_task: Optional[asyncio.Task] = None
        self._current_health = HealthStatus.UNKNOWN

        # Pool tracking for each engine
        self._engine_health: Dict[str, bool] = {}

    @property
    def metrics(self) -> DatabaseMetrics:
        """Get metrics instance."""
        return self._metrics

    @property
    def query_logger(self) -> Optional[QueryLogger]:
        """Get query logger instance."""
        return self._query_logger

    @property
    def health_status(self) -> HealthStatus:
        """Get current health status."""
        return self._current_health

    async def start(self) -> None:
        """Start monitoring."""
        if self._running:
            return

        logger.info("Starting database monitor")

        # Attach query logging to engines
        if self._query_logger:
            self._query_logger.attach_to_engine(self._write_engine)
            for engine in self._read_engines:
                self._query_logger.attach_to_engine(engine)

        # Start health check loop
        self._running = True
        self._health_task = asyncio.create_task(self._health_check_loop())

        logger.info("Database monitor started")

    async def stop(self) -> None:
        """Stop monitoring."""
        if not self._running:
            return

        logger.info("Stopping database monitor")

        self._running = False

        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        logger.info("Database monitor stopped")

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._running:
            try:
                await self.health_check()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check loop error", error=str(e))
                await asyncio.sleep(self._health_check_interval)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.

        Returns:
            Health check results
        """
        self._metrics.health_check_count += 1
        self._metrics.last_updated = datetime.utcnow()

        results = {
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "write_engine": await self._check_engine("write", self._write_engine),
            "read_engines": [],
        }

        # Check write engine
        if not results["write_engine"]["healthy"]:
            results["status"] = HealthStatus.UNHEALTHY
            self._metrics.health_check_failures += 1

        # Check read engines
        for i, engine in enumerate(self._read_engines):
            engine_result = await self._check_engine(f"read_{i}", engine)
            results["read_engines"].append(engine_result)

            if not engine_result["healthy"]:
                if results["status"] == HealthStatus.HEALTHY:
                    results["status"] = HealthStatus.DEGRADED

        # Update current health status
        previous_health = self._current_health
        self._current_health = HealthStatus(results["status"])

        # Trigger callback if health changed
        if previous_health != self._current_health and self._on_health_change:
            try:
                self._on_health_change(self._current_health)
            except Exception as e:
                logger.warning("Health change callback error", error=str(e))

        return results

    async def _check_engine(self, name: str, engine: AsyncEngine) -> Dict[str, Any]:
        """Check single engine health."""
        start_time = time.perf_counter()
        result = {
            "name": name,
            "healthy": False,
            "response_time_ms": 0,
            "pool": {},
            "error": None,
        }

        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            duration_ms = (time.perf_counter() - start_time) * 1000
            result["healthy"] = True
            result["response_time_ms"] = round(duration_ms, 2)

            # Get pool stats
            pool = engine.pool
            result["pool"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }

            self._engine_health[name] = True

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            result["response_time_ms"] = round(duration_ms, 2)
            result["error"] = str(e)
            self._engine_health[name] = False
            self._metrics.connection_errors += 1

            logger.warning(
                "Engine health check failed",
                engine=name,
                error=str(e)
            )

        return result

    def get_pool_stats(self) -> Dict[str, PoolStats]:
        """Get pool statistics for all engines."""
        stats = {}

        # Write engine
        pool = self._write_engine.pool
        stats["write"] = PoolStats(
            pool_size=pool.size(),
            checked_in=pool.checkedin(),
            checked_out=pool.checkedout(),
            overflow=pool.overflow(),
        )

        # Read engines
        for i, engine in enumerate(self._read_engines):
            pool = engine.pool
            stats[f"read_{i}"] = PoolStats(
                pool_size=pool.size(),
                checked_in=pool.checkedin(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
            )

        return stats

    def get_metrics(self) -> Dict[str, Any]:
        """Get all monitoring metrics."""
        metrics = self._metrics.to_dict()

        # Add pool stats
        metrics["pools"] = {
            name: stats.to_dict()
            for name, stats in self.get_pool_stats().items()
        }

        # Add query stats
        if self._query_logger:
            metrics["queries"] = self._query_logger.get_stats()

        # Add health status
        metrics["health_status"] = self._current_health.value

        return metrics

    def record_query(self, duration_ms: float, is_error: bool = False) -> None:
        """
        Record a query execution (for external tracking).

        Args:
            duration_ms: Query duration in milliseconds
            is_error: Whether query resulted in error
        """
        self._metrics.total_queries += 1
        self._metrics.total_query_time_ms += duration_ms
        self._metrics.last_updated = datetime.utcnow()

        if is_error:
            self._metrics.failed_queries += 1

    async def record_connection_error(self, engine_name: str) -> None:
        """
        Record a connection error.

        Args:
            engine_name: Name of the engine with error
        """
        self._metrics.connection_errors += 1
        self._metrics.last_updated = datetime.utcnow()
        self._engine_health[engine_name] = False

        logger.warning("Connection error recorded", engine=engine_name)


# =============================================================================
# Prometheus Integration
# =============================================================================

class PrometheusExporter:
    """
    Export database metrics in Prometheus format.

    Example:
        ```python
        exporter = PrometheusExporter(monitor)

        @app.get("/metrics")
        async def metrics():
            return Response(
                content=exporter.export(),
                media_type="text/plain"
            )
        ```
    """

    def __init__(self, monitor: DatabaseMonitor, prefix: str = "maestro_db"):
        """
        Initialize Prometheus exporter.

        Args:
            monitor: Database monitor instance
            prefix: Metric name prefix
        """
        self._monitor = monitor
        self._prefix = prefix

    def export(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        metrics = self._monitor.get_metrics()

        # Query metrics
        lines.append(f"# HELP {self._prefix}_queries_total Total number of queries")
        lines.append(f"# TYPE {self._prefix}_queries_total counter")
        lines.append(f'{self._prefix}_queries_total {metrics["queries"]["total"]}')

        lines.append(f"# HELP {self._prefix}_slow_queries_total Total slow queries")
        lines.append(f"# TYPE {self._prefix}_slow_queries_total counter")
        lines.append(f'{self._prefix}_slow_queries_total {metrics["queries"]["slow"]}')

        lines.append(f"# HELP {self._prefix}_query_duration_avg_ms Average query duration")
        lines.append(f"# TYPE {self._prefix}_query_duration_avg_ms gauge")
        lines.append(f'{self._prefix}_query_duration_avg_ms {metrics["queries"]["avg_time_ms"]}')

        # Connection metrics
        lines.append(f"# HELP {self._prefix}_connection_errors_total Total connection errors")
        lines.append(f"# TYPE {self._prefix}_connection_errors_total counter")
        lines.append(f'{self._prefix}_connection_errors_total {metrics["connections"]["errors"]}')

        # Pool metrics (per engine)
        for pool_name, pool_stats in metrics.get("pools", {}).items():
            labels = f'engine="{pool_name}"'

            lines.append(f"# HELP {self._prefix}_pool_size Connection pool size")
            lines.append(f"# TYPE {self._prefix}_pool_size gauge")
            lines.append(f'{self._prefix}_pool_size{{{labels}}} {pool_stats["pool_size"]}')

            lines.append(f"# HELP {self._prefix}_pool_checked_out Connections in use")
            lines.append(f"# TYPE {self._prefix}_pool_checked_out gauge")
            lines.append(f'{self._prefix}_pool_checked_out{{{labels}}} {pool_stats["checked_out"]}')

            lines.append(f"# HELP {self._prefix}_pool_utilization Pool utilization percent")
            lines.append(f"# TYPE {self._prefix}_pool_utilization gauge")
            lines.append(f'{self._prefix}_pool_utilization{{{labels}}} {pool_stats["utilization_percent"]}')

        # Health status (1=healthy, 0=unhealthy)
        health_value = 1 if metrics["health_status"] == "healthy" else 0
        lines.append(f"# HELP {self._prefix}_health Database health status")
        lines.append(f"# TYPE {self._prefix}_health gauge")
        lines.append(f'{self._prefix}_health {health_value}')

        # Uptime
        lines.append(f"# HELP {self._prefix}_uptime_seconds Monitor uptime")
        lines.append(f"# TYPE {self._prefix}_uptime_seconds counter")
        lines.append(f'{self._prefix}_uptime_seconds {metrics["uptime_seconds"]}')

        return "\n".join(lines)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "HealthStatus",
    "MetricType",

    # Data classes
    "QueryInfo",
    "PoolStats",
    "DatabaseMetrics",

    # Components
    "QueryLogger",
    "DatabaseMonitor",
    "PrometheusExporter",
]
