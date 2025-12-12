"""
Tests for ExecutionHistoryLogger - Execution history and insights.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3032 - Implement ExecutionHistoryLogger
"""

import os
import pytest
import tempfile
from datetime import datetime

from maestro_hive.execution.history_logger import (
    ExecutionHistoryLogger,
    LoggerConfig,
    ExecutionRecord,
    ExecutionInsight,
    AggregatedMetrics,
    MetricType,
    get_history_logger,
    reset_history_logger,
)


class TestMetricType:
    """Tests for MetricType enum."""

    def test_all_types_defined(self):
        """Test all expected metric types are defined."""
        types = [
            MetricType.SUCCESS_RATE,
            MetricType.RETRY_COUNT,
            MetricType.DURATION,
            MetricType.ERROR_FREQUENCY,
            MetricType.RECOVERY_RATE,
        ]
        assert len(types) == 5


class TestLoggerConfig:
    """Tests for LoggerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggerConfig()
        assert config.max_records == 100000
        assert config.retention_days == 90
        assert config.enable_insights is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LoggerConfig(
            storage_path="/custom/path.db",
            max_records=1000,
            retention_days=30,
        )
        assert config.storage_path == "/custom/path.db"
        assert config.max_records == 1000


class TestExecutionRecord:
    """Tests for ExecutionRecord dataclass."""

    def test_create_record(self):
        """Test creating an execution record."""
        record = ExecutionRecord(
            execution_id="exec-001",
            task_name="test_task",
            status="success",
            attempt_count=1,
            duration_seconds=5.0,
        )
        assert record.execution_id == "exec-001"
        assert record.status == "success"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        record = ExecutionRecord(
            execution_id="exec-001",
            task_name="test_task",
            status="failed",
            attempt_count=3,
            duration_seconds=10.0,
            error_type="ValueError",
            error_message="Invalid value",
        )
        data = record.to_dict()
        assert data["execution_id"] == "exec-001"
        assert data["error_type"] == "ValueError"


class TestExecutionInsight:
    """Tests for ExecutionInsight dataclass."""

    def test_create_insight(self):
        """Test creating an execution insight."""
        insight = ExecutionInsight(
            insight_type="success_rate",
            title="Success Rate Analysis",
            description="Overall success rate is 95%",
            metric_value=95.0,
            trend="stable",
        )
        assert insight.insight_type == "success_rate"
        assert insight.metric_value == 95.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        insight = ExecutionInsight(
            insight_type="error_frequency",
            title="Error Analysis",
            description="Most common error",
            metric_value=10,
            trend="improving",
            recommendations=["Fix root cause"],
        )
        data = insight.to_dict()
        assert data["insight_type"] == "error_frequency"
        assert "Fix root cause" in data["recommendations"]


class TestAggregatedMetrics:
    """Tests for AggregatedMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating aggregated metrics."""
        metrics = AggregatedMetrics(
            total_executions=100,
            successful_executions=90,
            failed_executions=8,
            recovered_executions=2,
        )
        assert metrics.total_executions == 100
        assert metrics.successful_executions == 90

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = AggregatedMetrics(
            total_executions=100,
            successful_executions=85,
        )
        assert metrics.success_rate == 85.0

    def test_success_rate_zero_executions(self):
        """Test success rate with no executions."""
        metrics = AggregatedMetrics()
        assert metrics.success_rate == 0.0

    def test_recovery_rate_calculation(self):
        """Test recovery rate calculation."""
        metrics = AggregatedMetrics(
            failed_executions=8,
            recovered_executions=2,
        )
        assert metrics.recovery_rate == 20.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        metrics = AggregatedMetrics(
            total_executions=50,
            successful_executions=45,
            error_types={"ValueError": 3, "TimeoutError": 2},
        )
        data = metrics.to_dict()
        assert data["total_executions"] == 50
        assert data["error_types"]["ValueError"] == 3


class TestExecutionHistoryLogger:
    """Tests for ExecutionHistoryLogger class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def logger(self, temp_db):
        """Create logger with temp database."""
        config = LoggerConfig(storage_path=temp_db)
        return ExecutionHistoryLogger(config=config)

    @pytest.mark.asyncio
    async def test_log_execution(self, logger):
        """Test logging an execution."""
        # Create mock result object
        class MockResult:
            execution_id = "exec-001"
            task_name = "test_task"
            final_status = type('Status', (), {'value': 'success'})()
            attempt_count = 1
            total_duration_seconds = 5.0
            recovery_applied = False
            jira_bug_key = None
            attempts = []

            def to_dict(self):
                return {"execution_id": self.execution_id}

        result = MockResult()
        await logger.log(result)

        # Verify logged
        record = await logger.get_record("exec-001")
        assert record is not None
        assert record.task_name == "test_task"

    @pytest.mark.asyncio
    async def test_get_records(self, logger):
        """Test getting execution records."""
        records = await logger.get_records(days=7)
        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_get_records_with_filters(self, logger):
        """Test getting records with filters."""
        records = await logger.get_records(
            task_name="specific_task",
            status="success",
            days=30,
            limit=10,
        )
        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_get_metrics(self, logger):
        """Test getting aggregated metrics."""
        metrics = await logger.get_metrics(days=7)
        assert isinstance(metrics, AggregatedMetrics)

    @pytest.mark.asyncio
    async def test_get_metrics_with_task_filter(self, logger):
        """Test getting metrics for specific task."""
        metrics = await logger.get_metrics(task_name="specific_task", days=30)
        assert isinstance(metrics, AggregatedMetrics)

    @pytest.mark.asyncio
    async def test_generate_insights(self, logger):
        """Test generating insights."""
        insights = await logger.generate_insights(days=7)
        assert isinstance(insights, list)

    @pytest.mark.asyncio
    async def test_insights_disabled(self, temp_db):
        """Test insights when disabled."""
        config = LoggerConfig(
            storage_path=temp_db,
            enable_insights=False,
        )
        logger = ExecutionHistoryLogger(config=config)

        insights = await logger.generate_insights()
        assert insights == []

    @pytest.mark.asyncio
    async def test_get_task_statistics(self, logger):
        """Test getting task statistics."""
        stats = await logger.get_task_statistics("test_task")
        assert "task_name" in stats
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_cleanup_old_records(self, logger):
        """Test cleaning up old records."""
        deleted = await logger.cleanup_old_records()
        assert isinstance(deleted, int)

    def test_close(self, logger):
        """Test closing database connection."""
        logger.close()
        assert logger._conn is None


class TestSingleton:
    """Tests for singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_history_logger()
        yield
        reset_history_logger()

    def test_get_history_logger(self):
        """Test singleton getter."""
        logger1 = get_history_logger()
        logger2 = get_history_logger()
        assert logger1 is logger2

    def test_reset_history_logger(self):
        """Test singleton reset."""
        logger1 = get_history_logger()
        reset_history_logger()
        logger2 = get_history_logger()
        assert logger1 is not logger2
