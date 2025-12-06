"""
Tests for Execution History Store Module

EPIC: MD-2500
Tests for AC-1 through AC-4 implementation.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from src.maestro_hive.history import (
    ExecutionHistoryStore,
    ExecutionRecord,
    ExecutionStatus,
    ExportFormat,
    ExportService,
    QualityScores,
    RetentionConfig,
    RetentionManager,
)
from src.maestro_hive.history.export import ExportOptions
from src.maestro_hive.history.retention import RetentionStrategy


class TestExecutionRecord:
    """Tests for ExecutionRecord model."""

    def test_create_record(self):
        """Test creating an execution record."""
        record = ExecutionRecord(
            epic_key="MD-2500",
            input_text="Test input",
        )

        assert record.epic_key == "MD-2500"
        assert record.input_text == "Test input"
        assert record.status == ExecutionStatus.PENDING
        assert record.id is not None
        assert record.created_at is not None

    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        record = ExecutionRecord(
            epic_key="MD-2500",
            input_text="Test input",
            status=ExecutionStatus.SUCCESS,
        )

        data = record.to_dict()

        assert data["epic_key"] == "MD-2500"
        assert data["input_text"] == "Test input"
        assert data["status"] == "success"
        assert "id" in data
        assert "created_at" in data

    def test_record_from_dict(self):
        """Test creating record from dictionary."""
        data = {
            "id": str(uuid4()),
            "epic_key": "MD-2500",
            "input_text": "Test input",
            "status": "success",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        record = ExecutionRecord.from_dict(data)

        assert record.epic_key == "MD-2500"
        assert record.input_text == "Test input"
        assert record.status == ExecutionStatus.SUCCESS

    def test_mark_completed(self):
        """Test marking record as completed."""
        record = ExecutionRecord(epic_key="MD-2500")

        record.mark_completed(ExecutionStatus.SUCCESS)

        assert record.status == ExecutionStatus.SUCCESS
        assert record.completed_at is not None

    def test_mark_failed(self):
        """Test marking record as failed."""
        record = ExecutionRecord(epic_key="MD-2500")

        record.mark_failed("Test failure", {"code": 500})

        assert record.status == ExecutionStatus.FAILED
        assert record.failure_reason == "Test failure"
        assert record.error_details == {"code": 500}
        assert record.completed_at is not None


class TestQualityScores:
    """Tests for QualityScores model."""

    def test_create_scores(self):
        """Test creating quality scores."""
        scores = QualityScores(
            overall_score=0.85,
            documentation_score=0.9,
            implementation_score=0.8,
        )

        assert scores.overall_score == 0.85
        assert scores.documentation_score == 0.9
        assert scores.implementation_score == 0.8

    def test_scores_to_dict(self):
        """Test converting scores to dictionary."""
        scores = QualityScores(overall_score=0.85)

        data = scores.to_dict()

        assert data["overall_score"] == 0.85
        assert "documentation_score" in data

    def test_scores_from_dict(self):
        """Test creating scores from dictionary."""
        data = {"overall_score": 0.85, "test_coverage_score": 0.7}

        scores = QualityScores.from_dict(data)

        assert scores.overall_score == 0.85
        assert scores.test_coverage_score == 0.7


class TestExecutionHistoryStore:
    """Tests for ExecutionHistoryStore (AC-1, AC-2)."""

    @pytest.fixture
    def store(self):
        """Create an in-memory store for testing."""
        return ExecutionHistoryStore(use_memory=True)

    @pytest.mark.asyncio
    async def test_initialize(self, store):
        """Test store initialization."""
        await store.initialize()
        assert store._initialized is True

    @pytest.mark.asyncio
    async def test_store_execution(self, store):
        """Test storing an execution record (AC-1)."""
        await store.initialize()

        record = ExecutionRecord(
            epic_key="MD-2500",
            input_text="Test input",
        )

        stored = await store.store_execution(record)

        assert stored.id == record.id
        assert stored.epic_key == "MD-2500"

    @pytest.mark.asyncio
    async def test_get_execution(self, store):
        """Test retrieving an execution by ID."""
        await store.initialize()

        record = ExecutionRecord(epic_key="MD-2500")
        await store.store_execution(record)

        retrieved = await store.get_execution(record.id)

        assert retrieved is not None
        assert retrieved.id == record.id
        assert retrieved.epic_key == "MD-2500"

    @pytest.mark.asyncio
    async def test_get_by_epic(self, store):
        """Test retrieving executions by EPIC key."""
        await store.initialize()

        # Create multiple records
        for i in range(5):
            record = ExecutionRecord(
                epic_key="MD-2500",
                status=ExecutionStatus.SUCCESS if i % 2 == 0 else ExecutionStatus.FAILED,
            )
            await store.store_execution(record)

        # Get all for EPIC
        results = await store.get_by_epic("MD-2500")
        assert len(results) == 5

        # Get only successful
        results = await store.get_by_epic("MD-2500", status=ExecutionStatus.SUCCESS)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_similar(self, store):
        """Test finding similar executions by embedding (AC-2)."""
        await store.initialize()

        # Create records with embeddings
        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding2 = [0.11, 0.21, 0.31, 0.41, 0.51]  # Similar
        embedding3 = [0.9, 0.8, 0.7, 0.6, 0.5]  # Different

        record1 = ExecutionRecord(epic_key="MD-2500", input_embedding=embedding1)
        record2 = ExecutionRecord(epic_key="MD-2500", input_embedding=embedding2)
        record3 = ExecutionRecord(epic_key="MD-2500", input_embedding=embedding3)

        await store.store_execution(record1)
        await store.store_execution(record2)
        await store.store_execution(record3)

        # Find similar to embedding1
        results = await store.find_similar(embedding1, limit=2, min_score=0.5)

        assert len(results) >= 1
        # First result should be most similar
        assert results[0][1] >= results[-1][1]

    @pytest.mark.asyncio
    async def test_delete_execution(self, store):
        """Test deleting an execution record."""
        await store.initialize()

        record = ExecutionRecord(epic_key="MD-2500")
        await store.store_execution(record)

        # Verify it exists
        assert await store.get_execution(record.id) is not None

        # Delete
        result = await store.delete_execution(record.id)
        assert result is True

        # Verify it's gone
        assert await store.get_execution(record.id) is None

    @pytest.mark.asyncio
    async def test_count(self, store):
        """Test counting records."""
        await store.initialize()

        for i in range(10):
            record = ExecutionRecord(
                epic_key="MD-2500",
                status=ExecutionStatus.SUCCESS if i < 7 else ExecutionStatus.FAILED,
            )
            await store.store_execution(record)

        # Count all
        assert await store.count() == 10

        # Count by status
        assert await store.count(status=ExecutionStatus.SUCCESS) == 7
        assert await store.count(status=ExecutionStatus.FAILED) == 3

    @pytest.mark.asyncio
    async def test_cosine_similarity(self, store):
        """Test cosine similarity calculation."""
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]

        # Identical vectors should have similarity 1.0
        assert store._cosine_similarity(a, b) == 1.0

        c = [0.0, 1.0, 0.0]
        # Orthogonal vectors should have similarity 0.0
        assert store._cosine_similarity(a, c) == 0.0


class TestRetentionManager:
    """Tests for RetentionManager (AC-3)."""

    @pytest.fixture
    def store(self):
        """Create an in-memory store for testing."""
        return ExecutionHistoryStore(use_memory=True)

    @pytest.fixture
    def retention_config(self):
        """Create a test retention config."""
        return RetentionConfig(
            strategy=RetentionStrategy.HYBRID,
            max_age_days=30,
            max_records_per_epic=5,
            dry_run=False,
        )

    @pytest.mark.asyncio
    async def test_time_based_cleanup(self, store):
        """Test time-based retention cleanup."""
        await store.initialize()

        # Create old records
        old_record = ExecutionRecord(epic_key="MD-2500")
        old_record.created_at = datetime.utcnow() - timedelta(days=100)
        await store.store_execution(old_record)

        # Create recent record
        new_record = ExecutionRecord(epic_key="MD-2500")
        await store.store_execution(new_record)

        config = RetentionConfig(
            strategy=RetentionStrategy.TIME_BASED,
            max_age_days=30,
        )
        manager = RetentionManager(store, config)

        result = await manager.cleanup()

        assert result.records_deleted == 1
        # Old record should be gone
        assert await store.get_execution(old_record.id) is None
        # New record should remain
        assert await store.get_execution(new_record.id) is not None

    @pytest.mark.asyncio
    async def test_count_based_cleanup(self, store):
        """Test count-based retention cleanup."""
        await store.initialize()

        # Create more records than the limit
        records = []
        for i in range(10):
            record = ExecutionRecord(epic_key="MD-2500")
            record.created_at = datetime.utcnow() - timedelta(hours=i)
            await store.store_execution(record)
            records.append(record)

        config = RetentionConfig(
            strategy=RetentionStrategy.COUNT_BASED,
            max_records_per_epic=5,
        )
        manager = RetentionManager(store, config)

        result = await manager.cleanup()

        assert result.records_deleted == 5
        # Should keep the 5 newest records
        remaining = await store.get_by_epic("MD-2500")
        assert len(remaining) == 5

    @pytest.mark.asyncio
    async def test_keep_failed_longer(self, store):
        """Test that failed records are kept longer."""
        await store.initialize()

        # Create old failed record
        failed_record = ExecutionRecord(epic_key="MD-2500", status=ExecutionStatus.FAILED)
        failed_record.created_at = datetime.utcnow() - timedelta(days=100)
        await store.store_execution(failed_record)

        # Create old successful record
        success_record = ExecutionRecord(epic_key="MD-2500", status=ExecutionStatus.SUCCESS)
        success_record.created_at = datetime.utcnow() - timedelta(days=100)
        await store.store_execution(success_record)

        config = RetentionConfig(
            strategy=RetentionStrategy.TIME_BASED,
            max_age_days=30,
            keep_failed_longer=True,
            failed_retention_days=365,
        )
        manager = RetentionManager(store, config)

        result = await manager.cleanup()

        # Only successful record should be deleted
        assert result.records_deleted == 1
        assert await store.get_execution(failed_record.id) is not None
        assert await store.get_execution(success_record.id) is None

    @pytest.mark.asyncio
    async def test_dry_run(self, store):
        """Test dry run mode doesn't delete records."""
        await store.initialize()

        old_record = ExecutionRecord(epic_key="MD-2500")
        old_record.created_at = datetime.utcnow() - timedelta(days=100)
        await store.store_execution(old_record)

        config = RetentionConfig(
            strategy=RetentionStrategy.TIME_BASED,
            max_age_days=30,
            dry_run=True,
        )
        manager = RetentionManager(store, config)

        result = await manager.cleanup()

        assert result.records_deleted == 1
        assert result.dry_run is True
        # Record should still exist
        assert await store.get_execution(old_record.id) is not None

    @pytest.mark.asyncio
    async def test_retention_stats(self, store):
        """Test getting retention statistics."""
        await store.initialize()

        for i in range(5):
            record = ExecutionRecord(
                epic_key="MD-2500",
                status=ExecutionStatus.SUCCESS if i < 3 else ExecutionStatus.FAILED,
            )
            await store.store_execution(record)

        manager = RetentionManager(store)
        stats = await manager.get_retention_stats()

        assert stats["total_records"] == 5
        assert stats["by_status"]["success"] == 3
        assert stats["by_status"]["failed"] == 2


class TestExportService:
    """Tests for ExportService (AC-4)."""

    @pytest.fixture
    def store(self):
        """Create an in-memory store for testing."""
        return ExecutionHistoryStore(use_memory=True)

    @pytest.fixture
    async def populated_store(self, store):
        """Create a store with test data."""
        await store.initialize()

        for i in range(5):
            record = ExecutionRecord(
                epic_key=f"MD-250{i % 3}",
                input_text=f"Test input {i}",
                status=ExecutionStatus.SUCCESS if i % 2 == 0 else ExecutionStatus.FAILED,
                quality_scores=QualityScores(overall_score=0.8 + i * 0.02),
            )
            await store.store_execution(record)

        return store

    @pytest.mark.asyncio
    async def test_export_to_memory_json(self, populated_store):
        """Test exporting to JSON in memory."""
        service = ExportService(populated_store)

        options = ExportOptions(format=ExportFormat.JSON)
        result = await service.export_to_memory(options)

        data = json.loads(result)
        assert len(data) == 5
        assert all("epic_key" in r for r in data)

    @pytest.mark.asyncio
    async def test_export_to_memory_csv(self, populated_store):
        """Test exporting to CSV in memory."""
        service = ExportService(populated_store)

        options = ExportOptions(format=ExportFormat.CSV)
        result = await service.export_to_memory(options)

        lines = result.strip().split("\n")
        assert len(lines) == 6  # Header + 5 records
        assert "epic_key" in lines[0]

    @pytest.mark.asyncio
    async def test_export_to_file_json(self, populated_store):
        """Test exporting to JSON file."""
        service = ExportService(populated_store)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "export.json"
            options = ExportOptions(format=ExportFormat.JSON, pretty_print=True)

            result = await service.export_to_file(file_path, options)

            assert result.records_exported == 5
            assert result.file_path == str(file_path)
            assert result.file_size_bytes > 0
            assert result.error is None

            # Verify file contents
            with open(file_path) as f:
                data = json.load(f)
            assert len(data) == 5

    @pytest.mark.asyncio
    async def test_export_to_file_jsonl(self, populated_store):
        """Test exporting to JSON Lines file."""
        service = ExportService(populated_store)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "export.jsonl"
            options = ExportOptions(format=ExportFormat.JSONL)

            result = await service.export_to_file(file_path, options)

            assert result.records_exported == 5

            # Verify file contents
            with open(file_path) as f:
                lines = f.readlines()
            assert len(lines) == 5
            for line in lines:
                data = json.loads(line)
                assert "epic_key" in data

    @pytest.mark.asyncio
    async def test_export_with_status_filter(self, populated_store):
        """Test exporting with status filter."""
        service = ExportService(populated_store)

        options = ExportOptions(
            format=ExportFormat.JSON,
            status_filter=[ExecutionStatus.SUCCESS],
        )
        result = await service.export_to_memory(options)

        data = json.loads(result)
        assert len(data) == 3  # Only successful records
        assert all(r["status"] == "success" for r in data)

    @pytest.mark.asyncio
    async def test_export_with_epic_filter(self, populated_store):
        """Test exporting with EPIC filter."""
        service = ExportService(populated_store)

        options = ExportOptions(
            format=ExportFormat.JSON,
            epic_filter=["MD-2500"],
        )
        result = await service.export_to_memory(options)

        data = json.loads(result)
        assert all(r["epic_key"] == "MD-2500" for r in data)

    @pytest.mark.asyncio
    async def test_export_without_embeddings(self, populated_store):
        """Test that embeddings are excluded by default."""
        service = ExportService(populated_store)

        options = ExportOptions(include_embeddings=False)
        result = await service.export_to_memory(options)

        data = json.loads(result)
        assert all("input_embedding" not in r for r in data)

    @pytest.mark.asyncio
    async def test_export_with_limit(self, populated_store):
        """Test exporting with record limit."""
        service = ExportService(populated_store)

        options = ExportOptions(format=ExportFormat.JSON, limit=2)
        result = await service.export_to_memory(options)

        data = json.loads(result)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_export_stats(self, populated_store):
        """Test getting export statistics."""
        service = ExportService(populated_store)
        stats = await service.get_export_stats()

        assert stats["total_records"] == 5
        assert "by_status" in stats
        assert "by_epic" in stats
        assert "date_range" in stats


class TestIntegration:
    """Integration tests for the history module."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow: store, retrieve, cleanup, export."""
        # Initialize store
        store = ExecutionHistoryStore(use_memory=True)
        await store.initialize()

        # Store records
        for i in range(10):
            record = ExecutionRecord(
                epic_key="MD-2500",
                input_text=f"Test input {i}",
                input_embedding=[0.1 * i, 0.2 * i, 0.3 * i],
                status=ExecutionStatus.SUCCESS if i < 7 else ExecutionStatus.FAILED,
                quality_scores=QualityScores(overall_score=0.7 + i * 0.03),
            )
            record.created_at = datetime.utcnow() - timedelta(days=i * 10)
            await store.store_execution(record)

        # Verify storage
        assert await store.count() == 10

        # Find similar
        similar = await store.find_similar([0.5, 1.0, 1.5], limit=3, min_score=0.1)
        assert len(similar) > 0

        # Run retention
        config = RetentionConfig(max_age_days=50)
        manager = RetentionManager(store, config)
        cleanup_result = await manager.cleanup()
        assert cleanup_result.records_deleted >= 2  # Records older than 50 days

        # Export remaining
        export_service = ExportService(store)
        export_result = await export_service.export_to_memory(
            ExportOptions(format=ExportFormat.JSON)
        )
        data = json.loads(export_result)
        assert len(data) == 10 - cleanup_result.records_deleted

        # Close store
        await store.close()
        assert store._initialized is False
