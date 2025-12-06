"""
Tests for State Management - MD-2528

Tests all acceptance criteria:
- AC-1: Unified state store (JSON -> PostgreSQL migration path)
- AC-2: State synchronization between components
- AC-3: State versioning and history
- AC-4: State recovery on restart
"""

import shutil
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from maestro_hive.maestro.state import (
    JSONStateStore,
    PostgreSQLStateStore,
    StateEntry,
    StateManager,
    StateStore,
    StateSync,
    StateVersioning,
)
from maestro_hive.maestro.state.sync import SyncEvent, SyncStatus


class TestStateEntry:
    """Tests for StateEntry dataclass."""

    def test_entry_creation(self):
        """Test entry can be created with required fields."""
        entry = StateEntry(
            key="test/key",
            value={"data": "value"},
        )

        assert entry.key == "test/key"
        assert entry.value == {"data": "value"}
        assert entry.version == 1

    def test_entry_to_dict(self):
        """Test entry serialization."""
        timestamp = datetime.utcnow()
        entry = StateEntry(
            key="test/key",
            value={"data": "value"},
            version=5,
            timestamp=timestamp,
            component_id="comp-1",
            metadata={"meta": "data"},
        )

        data = entry.to_dict()

        assert data["key"] == "test/key"
        assert data["version"] == 5
        assert data["component_id"] == "comp-1"

    def test_entry_from_dict(self):
        """Test entry deserialization."""
        data = {
            "key": "test/key",
            "value": {"data": "value"},
            "version": 3,
            "timestamp": "2025-01-01T00:00:00",
            "component_id": "comp-1",
            "metadata": {},
        }

        entry = StateEntry.from_dict(data)

        assert entry.key == "test/key"
        assert entry.version == 3
        assert entry.component_id == "comp-1"


class TestJSONStateStore:
    """Tests for JSONStateStore (AC-1)."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def store(self, temp_dir):
        """Create JSON state store."""
        return JSONStateStore(state_dir=temp_dir)

    def test_store_initialization(self, store, temp_dir):
        """Test store creates directory."""
        assert Path(temp_dir).exists()

    def test_save_state(self, store):
        """Test state can be saved."""
        entry = store.save(
            key="test/key",
            value={"data": "value"},
            component_id="comp-1",
        )

        assert entry.key == "test/key"
        assert entry.version == 1
        assert entry.component_id == "comp-1"

    def test_load_state(self, store):
        """Test state can be loaded."""
        store.save(key="test/key", value={"data": "value"})

        entry = store.load("test/key")

        assert entry is not None
        assert entry.value == {"data": "value"}

    def test_load_nonexistent(self, store):
        """Test loading nonexistent key returns None."""
        entry = store.load("nonexistent")

        assert entry is None

    def test_version_increment(self, store):
        """Test version auto-increments on save."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})
        store.save(key="test/key", value={"v": 3})

        entry = store.load("test/key")

        assert entry.version == 3
        assert entry.value == {"v": 3}

    def test_load_specific_version(self, store):
        """Test loading specific version."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})
        store.save(key="test/key", value={"v": 3})

        entry = store.load("test/key", version=2)

        assert entry is not None
        assert entry.version == 2
        assert entry.value == {"v": 2}

    def test_list_keys(self, store):
        """Test listing keys."""
        store.save(key="alpha/one", value={})
        store.save(key="alpha/two", value={})
        store.save(key="beta/one", value={})

        keys = store.list_keys()

        assert len(keys) == 3
        assert "alpha/one" in keys or "alpha_one" in keys

    def test_list_keys_with_prefix(self, store):
        """Test listing keys with prefix filter."""
        store.save(key="alpha_one", value={})
        store.save(key="alpha_two", value={})
        store.save(key="beta_one", value={})

        keys = store.list_keys(prefix="alpha")

        assert len(keys) == 2

    def test_list_versions(self, store):
        """Test listing version history."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})
        store.save(key="test/key", value={"v": 3})

        versions = store.list_versions("test/key")

        assert len(versions) == 3
        assert versions[0].version == 1
        assert versions[2].version == 3

    def test_delete_state(self, store):
        """Test deleting state."""
        store.save(key="test/key", value={"data": "value"})

        result = store.delete("test/key")

        assert result is True
        assert store.load("test/key") is None

    def test_exists(self, store):
        """Test exists check."""
        assert store.exists("test/key") is False

        store.save(key="test/key", value={})

        assert store.exists("test/key") is True

    def test_prune_versions(self, store):
        """Test pruning old versions."""
        for i in range(10):
            store.save(key="test/key", value={"v": i})

        pruned = store.prune_versions("test/key", keep_count=3)

        assert pruned == 7
        versions = store.list_versions("test/key")
        assert len(versions) == 3

    def test_compare_and_swap_success(self, store):
        """Test CAS with matching version."""
        store.save(key="test/key", value={"v": 1})

        entry = store.compare_and_swap(
            key="test/key",
            expected_version=1,
            new_value={"v": 2},
        )

        assert entry is not None
        assert entry.version == 2
        assert entry.value == {"v": 2}

    def test_compare_and_swap_failure(self, store):
        """Test CAS with version mismatch."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})

        entry = store.compare_and_swap(
            key="test/key",
            expected_version=1,  # Wrong version
            new_value={"v": 3},
        )

        assert entry is None

    def test_thread_safety(self, store):
        """Test concurrent access is thread-safe."""
        results = []
        errors = []

        def writer(n):
            try:
                for i in range(10):
                    store.save(key=f"key_{n}", value={"writer": n, "iteration": i})
                results.append(n)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 5


class TestPostgreSQLStateStore:
    """Tests for PostgreSQLStateStore (AC-1)."""

    def test_fallback_without_psycopg2(self):
        """Test store handles missing psycopg2."""
        store = PostgreSQLStateStore(connection_string=None)

        # Should be unavailable without connection
        assert store.is_available() is False

    def test_store_interface_methods(self):
        """Test store implements required interface."""
        store = PostgreSQLStateStore()

        # All interface methods should exist
        assert hasattr(store, "save")
        assert hasattr(store, "load")
        assert hasattr(store, "delete")
        assert hasattr(store, "exists")
        assert hasattr(store, "list_keys")
        assert hasattr(store, "list_versions")


class TestStateSync:
    """Tests for StateSync (AC-2)."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def store(self, temp_dir):
        """Create JSON state store."""
        return JSONStateStore(state_dir=temp_dir)

    @pytest.fixture
    def sync(self, store):
        """Create state sync."""
        return StateSync(
            store=store,
            component_id="test-component",
            sync_interval=0.1,
        )

    def test_sync_initialization(self, sync):
        """Test sync initializes correctly."""
        assert sync.component_id == "test-component"
        assert sync.status == SyncStatus.IDLE

    def test_subscribe_and_notify(self, sync, store):
        """Test subscription receives updates."""
        received = []

        def callback(event):
            received.append(event)

        sync.subscribe("test/*", callback)

        # Save state directly to store
        store.save(key="test/key", value={"data": "value"})

        # Trigger sync
        events = sync.sync_now()

        assert len(events) > 0
        assert sync.status == SyncStatus.SYNCED

    def test_publish_update(self, sync):
        """Test publishing update."""
        entry = sync.publish_update(
            key="test/key",
            value={"data": "value"},
        )

        assert entry.component_id == "test-component"
        assert entry.version == 1

    def test_detect_external_changes(self, sync, store):
        """Test detecting changes from other components."""
        # Save initial state
        sync.sync_now()  # Build cache

        # External component saves
        store.save(key="new/key", value={"from": "external"})

        # Sync should detect change
        events = sync.sync_now()

        assert any(e.key == "new/key" for e in events)

    def test_start_stop_sync(self, sync):
        """Test starting and stopping sync thread."""
        sync.start()

        time.sleep(0.2)  # Let it run

        sync.stop()

        # Should be idle after stop
        assert sync.status == SyncStatus.IDLE

    def test_pattern_matching(self, sync):
        """Test key pattern matching."""
        assert sync._matches_pattern("test/key", "test/*") is True
        assert sync._matches_pattern("test/key", "other/*") is False
        assert sync._matches_pattern("any/key", "*") is True


class TestStateVersioning:
    """Tests for StateVersioning (AC-3)."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def store(self, temp_dir):
        """Create JSON state store."""
        return JSONStateStore(state_dir=temp_dir)

    @pytest.fixture
    def versioning(self, store):
        """Create state versioning."""
        return StateVersioning(store=store)

    def test_get_history(self, versioning, store):
        """Test getting version history."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})
        store.save(key="test/key", value={"v": 3})

        history = versioning.get_history("test/key")

        assert len(history) == 3
        # Newest first
        assert history[0].version == 3

    def test_get_version(self, versioning, store):
        """Test getting specific version."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})

        entry = versioning.get_version("test/key", 1)

        assert entry is not None
        assert entry.value == {"v": 1}

    def test_compare_versions(self, versioning, store):
        """Test comparing versions."""
        store.save(key="test/key", value={"a": 1, "b": 2})
        store.save(key="test/key", value={"a": 1, "c": 3})

        diff = versioning.compare_versions("test/key", 1, 2)

        assert diff is not None
        assert "b" in diff.removed_keys
        assert "c" in diff.added_keys

    def test_rollback(self, versioning, store):
        """Test rolling back to previous version."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})
        store.save(key="test/key", value={"v": 3})

        entry = versioning.rollback("test/key", to_version=1)

        assert entry is not None
        assert entry.version == 4  # New version
        assert entry.value == {"v": 1}  # Old value

    def test_create_snapshot(self, versioning, store):
        """Test creating snapshot."""
        store.save(key="a", value={"data": "a"})
        store.save(key="b", value={"data": "b"})

        snapshot = versioning.create_snapshot()

        assert len(snapshot) == 2
        assert "a" in snapshot
        assert "b" in snapshot

    def test_restore_snapshot(self, versioning, store):
        """Test restoring from snapshot."""
        store.save(key="a", value={"data": "a"})
        store.save(key="b", value={"data": "b"})

        snapshot = versioning.create_snapshot()

        # Delete state
        store.delete("a")
        store.delete("b")

        # Restore
        count = versioning.restore_snapshot(snapshot)

        assert count == 2
        assert store.exists("a")
        assert store.exists("b")

    def test_version_stats(self, versioning, store):
        """Test getting version statistics."""
        store.save(key="test/key", value={"v": 1})
        store.save(key="test/key", value={"v": 2})

        stats = versioning.get_version_stats("test/key")

        assert stats["total_versions"] == 2
        assert stats["oldest_version"] == 1
        assert stats["latest_version"] == 2


class TestStateManager:
    """Tests for StateManager (AC-4)."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create state manager."""
        return StateManager(
            component_id="test-component",
            backend="json",
            state_dir=temp_dir,
            enable_sync=False,
        )

    def test_manager_initialization(self, manager):
        """Test manager initializes correctly."""
        assert manager.component_id == "test-component"
        assert manager.backend_type == "json"

    def test_save_load_state(self, manager):
        """Test basic save and load."""
        entry = manager.save(
            key="test/key",
            value={"data": "value"},
        )

        loaded = manager.load("test/key")

        assert loaded is not None
        assert loaded.value == {"data": "value"}

    def test_get_value(self, manager):
        """Test get_value convenience method."""
        manager.save(key="test/key", value={"data": "value"})

        value = manager.get_value("test/key")

        assert value == {"data": "value"}

    def test_get_value_with_default(self, manager):
        """Test get_value returns default for missing key."""
        value = manager.get_value("missing", default={"default": True})

        assert value == {"default": True}

    def test_save_execution_state(self, manager):
        """Test execution state convenience method."""
        entry = manager.save_execution_state(
            execution_id="exec-001",
            state={"phase": "design", "status": "running"},
        )

        assert entry is not None
        assert entry.key == "execution/exec-001"

    def test_load_execution_state(self, manager):
        """Test loading execution state."""
        manager.save_execution_state(
            execution_id="exec-001",
            state={"phase": "design"},
        )

        state = manager.load_execution_state("exec-001")

        assert state == {"phase": "design"}

    def test_save_phase_state(self, manager):
        """Test phase state convenience method."""
        entry = manager.save_phase_state(
            execution_id="exec-001",
            phase_name="design",
            state={"artifacts": ["doc.md"]},
        )

        assert "phase/design" in entry.key

    def test_find_recoverable_executions(self, manager):
        """Test finding recoverable executions."""
        manager.save_execution_state("exec-001", {"phase": 1})
        manager.save_execution_state("exec-002", {"phase": 2})

        executions = manager.find_recoverable_executions()

        assert len(executions) == 2
        assert "exec-001" in executions
        assert "exec-002" in executions

    def test_recover_state(self, manager):
        """Test state recovery."""
        manager.save_execution_state(
            execution_id="exec-001",
            state={"phase": "design", "artifacts": ["file1.py"]},
        )

        # Simulate restart - load from scratch
        state = manager.recover_state("exec-001")

        assert state is not None
        assert state["phase"] == "design"

    def test_recovery_handler(self, manager):
        """Test recovery handler is called."""
        recovered = []

        def handler(exec_id, entry):
            recovered.append(exec_id)

        manager.register_recovery_handler(handler)
        manager.save_execution_state("exec-001", {"phase": 1})

        manager.recover_state("exec-001")

        assert "exec-001" in recovered

    def test_recover_all_active(self, manager):
        """Test recovering all active executions."""
        manager.save_execution_state("exec-001", {"phase": 1})
        manager.save_execution_state("exec-002", {"phase": 2})

        recovered = manager.recover_all_active()

        assert len(recovered) == 2

    def test_cleanup_execution(self, manager):
        """Test cleaning up execution state."""
        manager.save_execution_state("exec-001", {"phase": 1})
        manager.save_phase_state("exec-001", "design", {"done": True})

        count = manager.cleanup_execution("exec-001")

        assert count == 2
        assert manager.load_execution_state("exec-001") is None

    def test_history_and_rollback(self, manager):
        """Test history and rollback through manager."""
        manager.save(key="test/key", value={"v": 1})
        manager.save(key="test/key", value={"v": 2})
        manager.save(key="test/key", value={"v": 3})

        history = manager.get_history("test/key")
        assert len(history) == 3

        entry = manager.rollback("test/key", to_version=1)
        assert entry.value == {"v": 1}

    def test_create_restore_snapshot(self, manager):
        """Test snapshot creation and restoration."""
        manager.save_execution_state("exec-001", {"phase": 1})

        snapshot = manager.create_snapshot(execution_id="exec-001")

        manager.cleanup_execution("exec-001")

        count = manager.restore_snapshot(snapshot)

        assert count == 1
        assert manager.load_execution_state("exec-001") is not None

    def test_get_stats(self, manager):
        """Test getting manager statistics."""
        manager.save(key="test/key", value={})

        stats = manager.get_stats()

        assert stats["component_id"] == "test-component"
        assert stats["backend"] == "json"
        assert stats["total_keys"] >= 1


class TestIntegration:
    """Integration tests for complete state management flow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_full_execution_lifecycle(self, temp_dir):
        """Test complete execution state lifecycle."""
        # Initialize manager
        manager = StateManager(
            component_id="orchestrator",
            state_dir=temp_dir,
            enable_sync=False,
        )

        execution_id = "exec-lifecycle-001"

        # Phase 1: Start execution
        manager.save_execution_state(
            execution_id=execution_id,
            state={
                "status": "running",
                "current_phase": 0,
                "phases": ["requirements", "design", "implementation"],
            },
        )

        # Phase 2: Progress through phases
        for i, phase in enumerate(["requirements", "design", "implementation"]):
            manager.save_phase_state(
                execution_id=execution_id,
                phase_name=phase,
                state={"completed": True, "artifacts": [f"{phase}.md"]},
            )
            manager.save_execution_state(
                execution_id=execution_id,
                state={"status": "running", "current_phase": i + 1},
            )

        # Phase 3: Complete
        manager.save_execution_state(
            execution_id=execution_id,
            state={"status": "completed", "current_phase": 3},
        )

        # Verify history
        history = manager.get_history(f"execution/{execution_id}")
        assert len(history) == 5  # Initial + 3 phase updates + final completion

        # Simulate failure and recovery
        manager2 = StateManager(
            component_id="orchestrator-new",
            state_dir=temp_dir,
            enable_sync=False,
        )

        recovered_state = manager2.recover_state(execution_id)
        assert recovered_state is not None
        assert recovered_state["status"] == "completed"

    def test_version_conflict_resolution(self, temp_dir):
        """Test version conflict handling."""
        store = JSONStateStore(state_dir=temp_dir)
        versioning = StateVersioning(store=store)

        # Create initial state
        store.save(key="shared/config", value={"setting": "original"})

        # Simulate concurrent updates
        store.save(key="shared/config", value={"setting": "update1"})
        store.save(key="shared/config", value={"setting": "update2"})

        # Check history
        history = versioning.get_history("shared/config")
        assert len(history) == 3

        # Rollback to resolve conflict
        entry = versioning.rollback("shared/config", to_version=1)
        assert entry.value == {"setting": "original"}
        assert entry.version == 4  # New version created
