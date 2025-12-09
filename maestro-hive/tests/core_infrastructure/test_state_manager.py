#!/usr/bin/env python3
"""Tests for StateManager module."""

import pytest
import threading
import tempfile
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.core.state_manager import StateManager, StateChange, get_state_manager


class TestStateManager:
    """Tests for StateManager class."""

    def setup_method(self):
        """Reset singleton for each test."""
        StateManager._instance = None

    def test_singleton_pattern(self):
        """Test that StateManager is a singleton."""
        sm1 = StateManager()
        sm2 = StateManager()
        assert sm1 is sm2

    def test_get_set_state(self):
        """Test basic state get/set operations."""
        sm = StateManager()
        sm.set_state("key1", "value1")
        assert sm.get_state("key1") == "value1"

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        sm = StateManager()
        assert sm.get_state("nonexistent") is None

    def test_namespace_isolation(self):
        """Test that namespaces are isolated."""
        sm = StateManager()
        sm.set_state("key", "default_value", namespace="default")
        sm.set_state("key", "other_value", namespace="other")

        assert sm.get_state("key", namespace="default") == "default_value"
        assert sm.get_state("key", namespace="other") == "other_value"

    def test_delete_state(self):
        """Test deleting state entries."""
        sm = StateManager()
        sm.set_state("key1", "value1")
        assert sm.delete_state("key1") is True
        assert sm.get_state("key1") is None
        assert sm.delete_state("key1") is False

    def test_get_all_state(self):
        """Test getting all state."""
        sm = StateManager()
        sm.set_state("key1", "value1")
        sm.set_state("key2", "value2")

        all_state = sm.get_all_state(namespace="default")
        assert "key1" in all_state
        assert "key2" in all_state

    def test_clear_state(self):
        """Test clearing state."""
        sm = StateManager()
        sm.set_state("key1", "value1")
        sm.set_state("key2", "value2")
        sm.clear(namespace="default")

        assert sm.get_all_state(namespace="default") == {}

    def test_subscribe_callback(self):
        """Test subscription callbacks."""
        sm = StateManager()
        changes = []

        def callback(change: StateChange):
            changes.append(change)

        sm.subscribe(callback)
        sm.set_state("key1", "value1")

        assert len(changes) == 1
        assert changes[0].key == "key1"
        assert changes[0].new_value == "value1"

    def test_checkpoint_and_restore(self):
        """Test checkpoint creation and restoration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            StateManager._instance = None
            sm = StateManager(persistence_dir=tmpdir)

            sm.set_state("key1", "value1")
            sm.set_state("key2", "value2")

            cp_info = sm.checkpoint("test_checkpoint")
            assert cp_info["checkpoint_id"] == "test_checkpoint"

            # Modify state
            sm.set_state("key1", "modified")
            sm.delete_state("key2")

            # Restore
            assert sm.restore("test_checkpoint") is True
            assert sm.get_state("key1") == "value1"
            assert sm.get_state("key2") == "value2"

    def test_thread_safety(self):
        """Test thread-safe operations."""
        sm = StateManager()
        errors = []

        def writer(n):
            try:
                for i in range(100):
                    sm.set_state(f"key_{n}_{i}", f"value_{n}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_get_namespaces(self):
        """Test listing namespaces."""
        sm = StateManager()
        sm.set_state("key", "value", namespace="ns1")
        sm.set_state("key", "value", namespace="ns2")

        namespaces = sm.get_namespaces()
        assert "default" in namespaces
        assert "ns1" in namespaces
        assert "ns2" in namespaces

    def test_get_state_manager_function(self):
        """Test convenience function."""
        sm = get_state_manager()
        assert isinstance(sm, StateManager)


class TestStateChange:
    """Tests for StateChange dataclass."""

    def test_state_change_creation(self):
        """Test creating a StateChange."""
        change = StateChange(
            key="test_key",
            old_value="old",
            new_value="new",
            namespace="default",
            timestamp="2025-01-01T00:00:00",
            change_type="set"
        )

        assert change.key == "test_key"
        assert change.old_value == "old"
        assert change.new_value == "new"
        assert change.change_type == "set"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
