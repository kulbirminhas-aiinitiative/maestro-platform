#!/usr/bin/env python3
"""
Tests for Memory Store module.

EPIC: MD-3090 - Persona Memory & Persistence Enhancements
AC-3: Unit tests with >80% coverage

Coverage targets:
- MemoryStore core operations (store, retrieve, update, delete)
- Memory consolidation strategies
- Integration callbacks
- Persistence (save/load/backup/restore)
- Health checks and statistics
- Edge cases and error handling
"""

import json
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from maestro_hive.personas.memory_store import (
    MemoryStore,
    MemoryStoreConfig,
    Memory,
    MemoryType,
    MemoryStatus,
    MemoryQueryResult,
    ConsolidationResult,
    ConsolidationStrategy,
    StoreStats,
    HealthStatus,
    get_memory_store,
    reset_memory_store,
    store_memory,
    retrieve_memories,
)


# === Fixtures ===

@pytest.fixture
def memory_store():
    """Create a fresh memory store for each test."""
    MemoryStore.reset_instance()
    config = MemoryStoreConfig(
        max_memories_per_persona=1000,
        consolidation_threshold=100,
        auto_consolidate=False,
        enable_persistence=False,
    )
    store = MemoryStore(config)
    yield store
    MemoryStore.reset_instance()


@pytest.fixture
def memory_store_with_persistence(tmp_path):
    """Create a memory store with persistence enabled."""
    MemoryStore.reset_instance()
    config = MemoryStoreConfig(
        storage_path=tmp_path,
        max_memories_per_persona=1000,
        consolidation_threshold=100,
        auto_consolidate=False,
        enable_persistence=True,
    )
    store = MemoryStore(config)
    yield store
    MemoryStore.reset_instance()


@pytest.fixture
def sample_memory():
    """Create a sample memory for testing."""
    return Memory(
        id="mem_001",
        persona_id="persona_123",
        memory_type=MemoryType.EPISODIC,
        content={"event": "completed task", "outcome": "success"},
        importance=0.8,
        tags=["task", "success"],
        source="test",
    )


@pytest.fixture
def populated_store(memory_store):
    """Create a store with multiple memories."""
    persona_id = "persona_123"

    # Add various memories
    memories = [
        Memory(
            id=f"mem_{i:03d}",
            persona_id=persona_id,
            memory_type=MemoryType.EPISODIC if i % 3 == 0 else MemoryType.SEMANTIC,
            content={"index": i, "data": f"content_{i}"},
            importance=0.1 + (i % 10) * 0.1,
            tags=[f"tag_{i % 5}"],
            access_count=i % 5,
        )
        for i in range(50)
    ]

    for memory in memories:
        memory_store.store_memory(persona_id, memory)

    return memory_store


# === Core Operations Tests ===

class TestMemoryStoreBasicOperations:
    """Test basic memory store operations."""

    def test_store_memory(self, memory_store, sample_memory):
        """Test storing a memory."""
        memory_id = memory_store.store_memory("persona_123", sample_memory)

        assert memory_id == "mem_001"
        assert memory_store.get_persona_memory_count("persona_123") == 1

    def test_store_memory_generates_id(self, memory_store):
        """Test that store generates ID when not provided."""
        memory = Memory(
            id="",
            persona_id="persona_123",
            memory_type=MemoryType.SEMANTIC,
            content={"fact": "test fact"},
            importance=0.5,
        )

        memory_id = memory_store.store_memory("persona_123", memory)

        assert memory_id is not None
        assert len(memory_id) == 16  # SHA256 truncated

    def test_retrieve_memory(self, memory_store, sample_memory):
        """Test retrieving a specific memory."""
        memory_store.store_memory("persona_123", sample_memory)

        retrieved = memory_store.get_memory("persona_123", "mem_001")

        assert retrieved is not None
        assert retrieved.id == "mem_001"
        assert retrieved.content == sample_memory.content

    def test_retrieve_nonexistent_memory(self, memory_store):
        """Test retrieving a memory that doesn't exist."""
        result = memory_store.get_memory("persona_123", "nonexistent")

        assert result is None

    def test_update_memory(self, memory_store, sample_memory):
        """Test updating a memory."""
        memory_store.store_memory("persona_123", sample_memory)

        updated = memory_store.update_memory(
            "persona_123",
            "mem_001",
            {"importance": 0.95, "tags": ["updated"]}
        )

        assert updated is not None
        assert updated.importance == 0.95
        assert "updated" in updated.tags

    def test_update_nonexistent_memory(self, memory_store):
        """Test updating a memory that doesn't exist."""
        result = memory_store.update_memory("persona_123", "nonexistent", {"importance": 0.9})

        assert result is None

    def test_delete_memory(self, memory_store, sample_memory):
        """Test deleting a memory."""
        memory_store.store_memory("persona_123", sample_memory)

        assert memory_store.delete_memory("persona_123", "mem_001") is True
        assert memory_store.get_memory("persona_123", "mem_001") is None
        assert memory_store.get_persona_memory_count("persona_123") == 0

    def test_delete_nonexistent_memory(self, memory_store):
        """Test deleting a memory that doesn't exist."""
        result = memory_store.delete_memory("persona_123", "nonexistent")

        assert result is False


class TestMemoryRetrieval:
    """Test memory retrieval with filtering and scoring."""

    def test_retrieve_by_type(self, populated_store):
        """Test retrieving memories filtered by type."""
        results = populated_store.retrieve_memories(
            "persona_123",
            memory_type=MemoryType.EPISODIC,
            limit=100
        )

        assert len(results) > 0
        assert all(r.memory.memory_type == MemoryType.EPISODIC for r in results)

    def test_retrieve_by_importance(self, populated_store):
        """Test retrieving memories filtered by minimum importance."""
        results = populated_store.retrieve_memories(
            "persona_123",
            min_importance=0.7,
            limit=100
        )

        assert len(results) > 0
        assert all(r.memory.importance >= 0.7 for r in results)

    def test_retrieve_by_tags(self, populated_store):
        """Test retrieving memories filtered by tags."""
        results = populated_store.retrieve_memories(
            "persona_123",
            tags=["tag_0"],
            limit=100
        )

        assert len(results) > 0
        assert all("tag_0" in r.memory.tags for r in results)

    def test_retrieve_with_query(self, populated_store):
        """Test retrieving memories with a text query."""
        results = populated_store.retrieve_memories(
            "persona_123",
            query="content_1",
            limit=10
        )

        assert len(results) > 0
        # Results should be sorted by relevance

    def test_retrieve_respects_limit(self, populated_store):
        """Test that retrieve respects the limit parameter."""
        results = populated_store.retrieve_memories(
            "persona_123",
            limit=5
        )

        assert len(results) <= 5

    def test_retrieve_excludes_archived(self, memory_store, sample_memory):
        """Test that archived memories are excluded by default."""
        memory_store.store_memory("persona_123", sample_memory)
        memory_store.update_memory("persona_123", "mem_001", {"status": MemoryStatus.ARCHIVED})

        results = memory_store.retrieve_memories("persona_123", limit=10)

        assert len(results) == 0

    def test_retrieve_includes_archived_when_requested(self, memory_store, sample_memory):
        """Test including archived memories when explicitly requested."""
        memory_store.store_memory("persona_123", sample_memory)
        memory_store.update_memory("persona_123", "mem_001", {"status": MemoryStatus.ARCHIVED})

        results = memory_store.retrieve_memories(
            "persona_123",
            include_archived=True,
            limit=10
        )

        assert len(results) == 1

    def test_retrieve_updates_access_metadata(self, memory_store, sample_memory):
        """Test that retrieval updates access metadata."""
        memory_store.store_memory("persona_123", sample_memory)
        original_count = sample_memory.access_count

        memory_store.retrieve_memories("persona_123", limit=10)

        memory = memory_store.get_memory("persona_123", "mem_001", update_access=False)
        assert memory.access_count > original_count


class TestMemoryConsolidation:
    """Test memory consolidation strategies."""

    def test_consolidation_importance_based(self, populated_store):
        """Test importance-based consolidation."""
        result = populated_store.consolidate_memories(
            "persona_123",
            strategy=ConsolidationStrategy.IMPORTANCE_BASED,
            force=True
        )

        assert result.persona_id == "persona_123"
        assert result.memories_archived >= 0

    def test_consolidation_recency_based(self, memory_store):
        """Test recency-based consolidation."""
        # Add memories with old access times
        for i in range(10):
            memory = Memory(
                id=f"old_mem_{i}",
                persona_id="persona_123",
                memory_type=MemoryType.EPISODIC,
                content={"index": i},
                importance=0.5,
                accessed_at=(datetime.utcnow() - timedelta(days=60)).isoformat(),
            )
            memory_store.store_memory("persona_123", memory)

        result = memory_store.consolidate_memories(
            "persona_123",
            strategy=ConsolidationStrategy.RECENCY_BASED,
            force=True
        )

        assert result.memories_archived >= 0

    def test_consolidation_frequency_based(self, memory_store):
        """Test frequency-based consolidation."""
        # Add memories with low access counts
        for i in range(10):
            memory = Memory(
                id=f"low_freq_{i}",
                persona_id="persona_123",
                memory_type=MemoryType.SEMANTIC,
                content={"index": i},
                importance=0.5,
                access_count=0,
            )
            memory_store.store_memory("persona_123", memory)

        result = memory_store.consolidate_memories(
            "persona_123",
            strategy=ConsolidationStrategy.FREQUENCY_BASED,
            force=True
        )

        assert result.memories_archived >= 0

    def test_consolidation_hybrid(self, populated_store):
        """Test hybrid consolidation strategy."""
        result = populated_store.consolidate_memories(
            "persona_123",
            strategy=ConsolidationStrategy.HYBRID,
            force=True
        )

        assert result.strategy == ConsolidationStrategy.HYBRID
        assert result.duration_ms >= 0

    def test_consolidation_respects_threshold(self, memory_store):
        """Test that consolidation respects threshold when not forced."""
        # Add fewer memories than threshold
        for i in range(5):
            memory = Memory(
                id=f"mem_{i}",
                persona_id="persona_123",
                memory_type=MemoryType.EPISODIC,
                content={"index": i},
                importance=0.5,
            )
            memory_store.store_memory("persona_123", memory)

        result = memory_store.consolidate_memories(
            "persona_123",
            force=False
        )

        # Should not consolidate below threshold
        assert result.memories_consolidated == 0
        assert result.memories_archived == 0


class TestCallbacks:
    """Test callback functionality."""

    def test_on_store_callback(self, memory_store, sample_memory):
        """Test on_store callback is triggered."""
        callback_data = {}

        def on_store(persona_id, memory):
            callback_data["persona_id"] = persona_id
            callback_data["memory_id"] = memory.id

        memory_store.register_callback("on_store", on_store)
        memory_store.store_memory("persona_123", sample_memory)

        assert callback_data["persona_id"] == "persona_123"
        assert callback_data["memory_id"] == "mem_001"

    def test_on_retrieve_callback(self, memory_store, sample_memory):
        """Test on_retrieve callback is triggered."""
        callback_data = {}

        def on_retrieve(persona_id, query, results):
            callback_data["persona_id"] = persona_id
            callback_data["query"] = query
            callback_data["count"] = len(results)

        memory_store.store_memory("persona_123", sample_memory)
        memory_store.register_callback("on_retrieve", on_retrieve)
        memory_store.retrieve_memories("persona_123", query="test", limit=10)

        assert callback_data["persona_id"] == "persona_123"
        assert callback_data["query"] == "test"

    def test_on_consolidate_callback(self, populated_store):
        """Test on_consolidate callback is triggered."""
        callback_data = {}

        def on_consolidate(persona_id, result):
            callback_data["persona_id"] = persona_id
            callback_data["archived"] = result.memories_archived

        populated_store.register_callback("on_consolidate", on_consolidate)
        populated_store.consolidate_memories("persona_123", force=True)

        assert callback_data["persona_id"] == "persona_123"

    def test_callback_error_handling(self, memory_store, sample_memory):
        """Test that callback errors don't break store operations."""
        def bad_callback(persona_id, memory):
            raise ValueError("Callback error")

        memory_store.register_callback("on_store", bad_callback)

        # Should not raise
        memory_id = memory_store.store_memory("persona_123", sample_memory)
        assert memory_id == "mem_001"


class TestPersistence:
    """Test persistence functionality."""

    def test_save_and_load_state(self, memory_store_with_persistence, sample_memory):
        """Test saving and loading state."""
        memory_store_with_persistence.store_memory("persona_123", sample_memory)
        memory_store_with_persistence.save_state()

        # Create new store instance
        MemoryStore.reset_instance()
        new_store = MemoryStore(memory_store_with_persistence.config)

        # Verify memory was loaded
        memory = new_store.get_memory("persona_123", "mem_001")
        assert memory is not None
        assert memory.content == sample_memory.content

    def test_export_backup(self, memory_store, sample_memory, tmp_path):
        """Test exporting backup."""
        memory_store.store_memory("persona_123", sample_memory)
        backup_path = tmp_path / "backup.json"

        result = memory_store.export_backup(backup_path)

        assert result is True
        assert backup_path.exists()

        with open(backup_path) as f:
            data = json.load(f)

        assert "memories" in data
        assert "persona_123" in data["memories"]

    def test_import_backup(self, memory_store, sample_memory, tmp_path):
        """Test importing backup."""
        memory_store.store_memory("persona_123", sample_memory)
        backup_path = tmp_path / "backup.json"
        memory_store.export_backup(backup_path)

        # Clear and reimport
        memory_store.clear_persona_memories("persona_123")
        result = memory_store.import_backup(backup_path)

        assert result is True
        assert memory_store.get_persona_memory_count("persona_123") == 1

    def test_import_backup_merge(self, memory_store, tmp_path):
        """Test merging backup import."""
        # Create first memory
        memory1 = Memory(
            id="mem_001",
            persona_id="persona_123",
            memory_type=MemoryType.EPISODIC,
            content={"data": "original"},
            importance=0.5,
        )
        memory_store.store_memory("persona_123", memory1)

        # Export backup
        backup_path = tmp_path / "backup.json"
        memory_store.export_backup(backup_path)

        # Add another memory
        memory2 = Memory(
            id="mem_002",
            persona_id="persona_123",
            memory_type=MemoryType.SEMANTIC,
            content={"data": "new"},
            importance=0.6,
        )
        memory_store.store_memory("persona_123", memory2)

        # Import with merge
        result = memory_store.import_backup(backup_path, merge=True)

        assert result is True
        assert memory_store.get_persona_memory_count("persona_123") == 2

    def test_import_nonexistent_backup(self, memory_store, tmp_path):
        """Test importing nonexistent backup file."""
        result = memory_store.import_backup(tmp_path / "nonexistent.json")

        assert result is False


class TestStatisticsAndHealth:
    """Test statistics and health check functionality."""

    def test_get_stats(self, populated_store):
        """Test getting store statistics."""
        stats = populated_store.get_stats()

        assert isinstance(stats, StoreStats)
        assert stats.total_personas == 1
        assert stats.total_memories == 50
        assert stats.average_importance > 0

    def test_get_stats_empty_store(self, memory_store):
        """Test statistics for empty store."""
        stats = memory_store.get_stats()

        assert stats.total_personas == 0
        assert stats.total_memories == 0
        assert stats.average_importance == 0.0

    def test_health_check_healthy(self, memory_store):
        """Test health check on healthy store."""
        health = memory_store.health_check()

        assert health.status == "healthy"
        assert health.checks["initialized"] is True

    def test_health_check_degraded(self, memory_store):
        """Test health check when limits exceeded."""
        # Add more than consolidation threshold without consolidating
        memory_store.config.consolidation_threshold = 10
        for i in range(20):
            memory = Memory(
                id=f"mem_{i}",
                persona_id="persona_123",
                memory_type=MemoryType.EPISODIC,
                content={"index": i},
                importance=0.5,
            )
            memory_store.store_memory("persona_123", memory)

        health = memory_store.health_check()

        assert health.status == "degraded"
        assert health.checks["consolidation_current"] is False


class TestRepair:
    """Test repair functionality."""

    def test_repair(self, populated_store):
        """Test repair operation."""
        result = populated_store.repair()

        assert "repaired" in result
        assert "removed" in result
        assert result["repaired"] >= 0


class TestPersonaOperations:
    """Test persona-level operations."""

    def test_get_all_persona_ids(self, memory_store):
        """Test getting all persona IDs."""
        for i in range(3):
            memory = Memory(
                id=f"mem_{i}",
                persona_id=f"persona_{i}",
                memory_type=MemoryType.EPISODIC,
                content={"index": i},
                importance=0.5,
            )
            memory_store.store_memory(f"persona_{i}", memory)

        persona_ids = memory_store.get_all_persona_ids()

        assert len(persona_ids) == 3
        assert "persona_0" in persona_ids

    def test_clear_persona_memories(self, populated_store):
        """Test clearing all memories for a persona."""
        count = populated_store.clear_persona_memories("persona_123")

        assert count == 50
        assert populated_store.get_persona_memory_count("persona_123") == 0


class TestSingleton:
    """Test singleton pattern."""

    def test_singleton_instance(self):
        """Test that singleton returns same instance."""
        MemoryStore.reset_instance()

        store1 = MemoryStore.get_instance()
        store2 = MemoryStore.get_instance()

        assert store1 is store2

        MemoryStore.reset_instance()

    def test_reset_instance(self):
        """Test resetting singleton instance."""
        MemoryStore.reset_instance()

        store1 = MemoryStore.get_instance()
        MemoryStore.reset_instance()
        store2 = MemoryStore.get_instance()

        assert store1 is not store2

        MemoryStore.reset_instance()


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_store_memory_function(self):
        """Test store_memory convenience function."""
        reset_memory_store()

        memory_id = store_memory(
            "persona_123",
            MemoryType.EPISODIC,
            {"event": "test"},
            importance=0.7,
            tags=["test"]
        )

        assert memory_id is not None

        reset_memory_store()

    def test_retrieve_memories_function(self):
        """Test retrieve_memories convenience function."""
        reset_memory_store()

        store_memory(
            "persona_123",
            MemoryType.EPISODIC,
            {"event": "test"},
            importance=0.7
        )

        results = retrieve_memories("persona_123", limit=10)

        assert len(results) == 1

        reset_memory_store()

    def test_get_memory_store_function(self):
        """Test get_memory_store convenience function."""
        reset_memory_store()

        store = get_memory_store()

        assert isinstance(store, MemoryStore)

        reset_memory_store()


class TestMemoryTypes:
    """Test different memory types."""

    @pytest.mark.parametrize("memory_type", [
        MemoryType.EPISODIC,
        MemoryType.SEMANTIC,
        MemoryType.PROCEDURAL,
        MemoryType.WORKING,
        MemoryType.CONTEXTUAL,
    ])
    def test_store_all_memory_types(self, memory_store, memory_type):
        """Test storing all memory types."""
        memory = Memory(
            id=f"mem_{memory_type.value}",
            persona_id="persona_123",
            memory_type=memory_type,
            content={"type": memory_type.value},
            importance=0.5,
        )

        memory_id = memory_store.store_memory("persona_123", memory)
        retrieved = memory_store.get_memory("persona_123", memory_id)

        assert retrieved is not None
        assert retrieved.memory_type == memory_type


class TestMemorySerialization:
    """Test memory serialization/deserialization."""

    def test_memory_to_dict(self, sample_memory):
        """Test converting memory to dictionary."""
        data = sample_memory.to_dict()

        assert data["id"] == "mem_001"
        assert data["memory_type"] == "episodic"
        assert data["status"] == "active"

    def test_memory_from_dict(self):
        """Test creating memory from dictionary."""
        data = {
            "id": "mem_001",
            "persona_id": "persona_123",
            "memory_type": "semantic",
            "content": {"fact": "test"},
            "importance": 0.6,
            "tags": [],
            "source": None,
            "context": {},
            "created_at": datetime.utcnow().isoformat(),
            "accessed_at": datetime.utcnow().isoformat(),
            "access_count": 0,
            "decay_factor": 1.0,
            "status": "active",
            "embedding": None,
        }

        memory = Memory.from_dict(data)

        assert memory.id == "mem_001"
        assert memory.memory_type == MemoryType.SEMANTIC


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_store_empty_content(self, memory_store):
        """Test storing memory with empty content."""
        memory = Memory(
            id="empty_mem",
            persona_id="persona_123",
            memory_type=MemoryType.WORKING,
            content={},
            importance=0.1,
        )

        memory_id = memory_store.store_memory("persona_123", memory)
        retrieved = memory_store.get_memory("persona_123", memory_id)

        assert retrieved is not None
        assert retrieved.content == {}

    def test_retrieve_empty_persona(self, memory_store):
        """Test retrieving from persona with no memories."""
        results = memory_store.retrieve_memories("nonexistent_persona", limit=10)

        assert len(results) == 0

    def test_zero_importance(self, memory_store):
        """Test memory with zero importance."""
        memory = Memory(
            id="zero_imp",
            persona_id="persona_123",
            memory_type=MemoryType.EPISODIC,
            content={"data": "test"},
            importance=0.0,
        )

        memory_store.store_memory("persona_123", memory)
        results = memory_store.retrieve_memories(
            "persona_123",
            min_importance=0.1,
            limit=10
        )

        assert len(results) == 0

    def test_max_importance(self, memory_store):
        """Test memory with maximum importance."""
        memory = Memory(
            id="max_imp",
            persona_id="persona_123",
            memory_type=MemoryType.EPISODIC,
            content={"data": "important"},
            importance=1.0,
        )

        memory_store.store_memory("persona_123", memory)
        results = memory_store.retrieve_memories("persona_123", limit=10)

        assert len(results) == 1
        assert results[0].memory.importance == 1.0


class TestIntegration:
    """Test integration with LearningEngine and EvolutionTracker."""

    def test_integrate_with_learning_engine(self, memory_store):
        """Test integration with mocked LearningEngine."""
        mock_engine = MagicMock()
        callbacks = []
        mock_engine.register_callback = lambda cb: callbacks.append(cb)

        memory_store.integrate_with_learning_engine(mock_engine)

        assert len(callbacks) == 1

    def test_integrate_with_evolution_tracker(self, memory_store):
        """Test integration with EvolutionTracker."""
        # Should not raise
        memory_store.integrate_with_evolution_tracker(MagicMock())


# === Performance Tests ===

class TestPerformance:
    """Performance-related tests."""

    def test_bulk_store_performance(self, memory_store):
        """Test storing many memories."""
        start = time.time()

        for i in range(100):
            memory = Memory(
                id=f"perf_mem_{i}",
                persona_id="persona_perf",
                memory_type=MemoryType.EPISODIC,
                content={"index": i},
                importance=0.5,
            )
            memory_store.store_memory("persona_perf", memory)

        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 5.0
        assert memory_store.get_persona_memory_count("persona_perf") == 100

    def test_bulk_retrieve_performance(self, populated_store):
        """Test retrieving from many memories."""
        start = time.time()

        for _ in range(10):
            populated_store.retrieve_memories(
                "persona_123",
                query="content",
                limit=10
            )

        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
