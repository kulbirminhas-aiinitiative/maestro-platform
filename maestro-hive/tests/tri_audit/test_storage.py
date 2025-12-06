"""
Tests for tri_audit/storage.py (MD-2078)

Tests persistent storage for tri-modal audit results:
- Save and retrieve audit results
- Query by verdict type
- Query by time range
- History tracking
- Statistics calculation
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import storage module
from tri_audit.storage import (
    TriAuditStorage,
    StorageConfig,
    StorageBackend,
    AuditHistoryEntry,
    get_storage,
    save_audit_result,
    get_audit_result,
    query_failures,
    get_audit_statistics,
    get_audit_history
)

# Import tri-audit types
from tri_audit.tri_audit import (
    TriAuditResult,
    TriModalVerdict,
    DDEAuditResult,
    BDVAuditResult,
    ACCAuditResult
)


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage_dir):
    """Create storage instance with temp directory."""
    config = StorageConfig(
        backend=StorageBackend.JSON_FILE,
        base_dir=temp_storage_dir,
        max_history_entries=100,
        auto_prune_days=30
    )
    return TriAuditStorage(config)


@pytest.fixture
def sample_audit_result():
    """Create sample TriAuditResult for testing."""
    return TriAuditResult(
        iteration_id="test-iter-001",
        verdict=TriModalVerdict.ALL_PASS,
        timestamp=datetime.utcnow().isoformat() + "Z",
        dde_passed=True,
        bdv_passed=True,
        acc_passed=True,
        can_deploy=True,
        diagnosis="All audits passed. Safe to deploy.",
        recommendations=["No action required - ready to deploy!"],
        dde_details={"score": 0.95},
        bdv_details={"total_scenarios": 10, "passed": 10},
        acc_details={"blocking_violations": 0}
    )


@pytest.fixture
def sample_failure_result():
    """Create sample failed audit result."""
    return TriAuditResult(
        iteration_id="test-iter-002",
        verdict=TriModalVerdict.SYSTEMIC_FAILURE,
        timestamp=datetime.utcnow().isoformat() + "Z",
        dde_passed=False,
        bdv_passed=False,
        acc_passed=False,
        can_deploy=False,
        diagnosis="All three audits failed.",
        recommendations=["HALT. Conduct retrospective."],
        dde_details={"score": 0.45},
        bdv_details={"total_scenarios": 10, "passed": 3},
        acc_details={"blocking_violations": 5}
    )


class TestTriAuditStorage:
    """Tests for TriAuditStorage class."""

    def test_init_creates_storage_dirs(self, temp_storage_dir):
        """Test storage initialization creates directories and files."""
        config = StorageConfig(base_dir=temp_storage_dir)
        storage = TriAuditStorage(config)

        # Check directories and files created
        assert Path(temp_storage_dir).exists()
        assert (Path(temp_storage_dir) / "audit_results.json").exists()
        assert (Path(temp_storage_dir) / "audit_history.json").exists()

    def test_save_result(self, storage, sample_audit_result):
        """Test saving audit result."""
        result = storage.save(sample_audit_result)
        assert result is True

        # Verify saved
        retrieved = storage.get(sample_audit_result.iteration_id)
        assert retrieved is not None
        assert retrieved.iteration_id == sample_audit_result.iteration_id
        assert retrieved.verdict == sample_audit_result.verdict
        assert retrieved.can_deploy == sample_audit_result.can_deploy

    def test_save_none_returns_false(self, storage):
        """Test saving None returns False."""
        result = storage.save(None)
        assert result is False

    def test_get_nonexistent(self, storage):
        """Test getting non-existent result returns None."""
        result = storage.get("nonexistent-id")
        assert result is None

    def test_save_and_retrieve_multiple(self, storage):
        """Test saving and retrieving multiple results."""
        results = []
        for i in range(5):
            result = TriAuditResult(
                iteration_id=f"test-iter-{i:03d}",
                verdict=TriModalVerdict.ALL_PASS if i % 2 == 0 else TriModalVerdict.DESIGN_GAP,
                timestamp=datetime.utcnow().isoformat() + "Z",
                dde_passed=True,
                bdv_passed=(i % 2 == 0),
                acc_passed=True,
                can_deploy=(i % 2 == 0),
                diagnosis="Test diagnosis",
                recommendations=[],
                dde_details={},
                bdv_details={},
                acc_details={}
            )
            results.append(result)
            storage.save(result)

        # Verify all can be retrieved
        for result in results:
            retrieved = storage.get(result.iteration_id)
            assert retrieved is not None
            assert retrieved.iteration_id == result.iteration_id

    def test_query_by_verdict(self, storage):
        """Test querying results by verdict type."""
        # Save results with different verdicts
        for verdict in [TriModalVerdict.ALL_PASS, TriModalVerdict.DESIGN_GAP, TriModalVerdict.ALL_PASS]:
            result = TriAuditResult(
                iteration_id=f"test-{verdict.value}-{datetime.utcnow().timestamp()}",
                verdict=verdict,
                timestamp=datetime.utcnow().isoformat() + "Z",
                dde_passed=True,
                bdv_passed=(verdict == TriModalVerdict.ALL_PASS),
                acc_passed=True,
                can_deploy=(verdict == TriModalVerdict.ALL_PASS),
                diagnosis="Test",
                recommendations=[],
                dde_details={},
                bdv_details={},
                acc_details={}
            )
            storage.save(result)

        # Query by ALL_PASS
        all_pass_results = storage.query_by_verdict(TriModalVerdict.ALL_PASS)
        assert len(all_pass_results) == 2

        # Query by DESIGN_GAP
        design_gap_results = storage.query_by_verdict(TriModalVerdict.DESIGN_GAP)
        assert len(design_gap_results) == 1

    def test_query_failures(self, storage, sample_audit_result, sample_failure_result):
        """Test querying recent failures."""
        storage.save(sample_audit_result)
        storage.save(sample_failure_result)

        failures = storage.query_failures(days=7)
        assert len(failures) == 1
        assert failures[0].iteration_id == sample_failure_result.iteration_id
        assert failures[0].can_deploy is False


class TestAuditHistory:
    """Tests for audit history tracking."""

    def test_history_added_on_save(self, storage, sample_audit_result):
        """Test history entry added when saving result."""
        storage.save(sample_audit_result)

        history = storage.get_history(limit=10)
        assert len(history) == 1
        assert history[0].iteration_id == sample_audit_result.iteration_id

    def test_history_entry_fields(self, storage, sample_audit_result):
        """Test history entry has correct fields."""
        storage.save(sample_audit_result)

        history = storage.get_history(limit=1)
        entry = history[0]

        assert entry.iteration_id == sample_audit_result.iteration_id
        assert entry.verdict == sample_audit_result.verdict.value
        assert entry.can_deploy == sample_audit_result.can_deploy
        assert entry.dde_passed == sample_audit_result.dde_passed
        assert entry.bdv_passed == sample_audit_result.bdv_passed
        assert entry.acc_passed == sample_audit_result.acc_passed

    def test_history_limit(self, storage):
        """Test history respects max entries limit."""
        config = StorageConfig(
            base_dir=storage.config.base_dir,
            max_history_entries=5
        )
        limited_storage = TriAuditStorage(config)

        # Save more than max entries
        for i in range(10):
            result = TriAuditResult(
                iteration_id=f"test-{i:03d}",
                verdict=TriModalVerdict.ALL_PASS,
                timestamp=datetime.utcnow().isoformat() + "Z",
                dde_passed=True,
                bdv_passed=True,
                acc_passed=True,
                can_deploy=True,
                diagnosis="Test",
                recommendations=[],
                dde_details={},
                bdv_details={},
                acc_details={}
            )
            limited_storage.save(result)

        history = limited_storage.get_history(limit=100)
        assert len(history) <= 5


class TestStatistics:
    """Tests for statistics calculation."""

    def test_get_statistics_empty(self, storage):
        """Test statistics with no data."""
        stats = storage.get_statistics(days=30)

        assert stats["total_audits"] == 0
        assert stats["deployable"] == 0
        assert stats["pass_rate"] == 0.0

    def test_get_statistics_with_data(self, storage):
        """Test statistics calculation with data."""
        # Save some results
        verdicts = [
            TriModalVerdict.ALL_PASS,
            TriModalVerdict.ALL_PASS,
            TriModalVerdict.DESIGN_GAP,
            TriModalVerdict.SYSTEMIC_FAILURE
        ]

        for i, verdict in enumerate(verdicts):
            result = TriAuditResult(
                iteration_id=f"stats-test-{i:03d}",
                verdict=verdict,
                timestamp=datetime.utcnow().isoformat() + "Z",
                dde_passed=(verdict != TriModalVerdict.SYSTEMIC_FAILURE),
                bdv_passed=(verdict == TriModalVerdict.ALL_PASS),
                acc_passed=(verdict != TriModalVerdict.SYSTEMIC_FAILURE),
                can_deploy=(verdict == TriModalVerdict.ALL_PASS),
                diagnosis="Test",
                recommendations=[],
                dde_details={},
                bdv_details={},
                acc_details={}
            )
            storage.save(result)

        stats = storage.get_statistics(days=30)

        assert stats["total_audits"] == 4
        assert stats["deployable"] == 2
        assert stats["blocked"] == 2
        assert stats["pass_rate"] == 0.5
        assert "all_pass" in stats["verdict_breakdown"]
        assert stats["verdict_breakdown"]["all_pass"] == 2

    def test_stream_pass_rates(self, storage):
        """Test individual stream pass rate calculation."""
        # Create results where streams fail independently
        results = [
            (True, True, True),  # All pass
            (True, False, True),  # BDV fails
            (False, True, True),  # DDE fails
            (True, True, False),  # ACC fails
        ]

        for i, (dde, bdv, acc) in enumerate(results):
            result = TriAuditResult(
                iteration_id=f"stream-test-{i:03d}",
                verdict=TriModalVerdict.ALL_PASS if all([dde, bdv, acc]) else TriModalVerdict.MIXED_FAILURE,
                timestamp=datetime.utcnow().isoformat() + "Z",
                dde_passed=dde,
                bdv_passed=bdv,
                acc_passed=acc,
                can_deploy=all([dde, bdv, acc]),
                diagnosis="Test",
                recommendations=[],
                dde_details={},
                bdv_details={},
                acc_details={}
            )
            storage.save(result)

        stats = storage.get_statistics(days=30)

        assert stats["stream_pass_rates"]["dde"] == 0.75  # 3/4 pass
        assert stats["stream_pass_rates"]["bdv"] == 0.75  # 3/4 pass
        assert stats["stream_pass_rates"]["acc"] == 0.75  # 3/4 pass


class TestStorageMaintenance:
    """Tests for storage maintenance operations."""

    def test_delete_result(self, storage, sample_audit_result):
        """Test deleting audit result."""
        storage.save(sample_audit_result)

        # Verify exists
        assert storage.get(sample_audit_result.iteration_id) is not None

        # Delete
        result = storage.delete(sample_audit_result.iteration_id)
        assert result is True

        # Verify deleted
        assert storage.get(sample_audit_result.iteration_id) is None

    def test_delete_nonexistent(self, storage):
        """Test deleting non-existent result."""
        result = storage.delete("nonexistent-id")
        assert result is False

    def test_list_all(self, storage):
        """Test listing all iteration IDs."""
        for i in range(3):
            result = TriAuditResult(
                iteration_id=f"list-test-{i:03d}",
                verdict=TriModalVerdict.ALL_PASS,
                timestamp=datetime.utcnow().isoformat() + "Z",
                dde_passed=True,
                bdv_passed=True,
                acc_passed=True,
                can_deploy=True,
                diagnosis="Test",
                recommendations=[],
                dde_details={},
                bdv_details={},
                acc_details={}
            )
            storage.save(result)

        ids = storage.list_all()
        assert len(ids) == 3
        assert "list-test-000" in ids


class TestAuditHistoryEntry:
    """Tests for AuditHistoryEntry dataclass."""

    def test_to_dict(self):
        """Test AuditHistoryEntry to_dict method."""
        entry = AuditHistoryEntry(
            iteration_id="test-123",
            timestamp="2025-12-02T12:00:00Z",
            verdict="all_pass",
            can_deploy=True,
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True
        )

        d = entry.to_dict()
        assert d["iteration_id"] == "test-123"
        assert d["verdict"] == "all_pass"
        assert d["can_deploy"] is True

    def test_from_dict(self):
        """Test AuditHistoryEntry from_dict method."""
        data = {
            "iteration_id": "test-456",
            "timestamp": "2025-12-02T12:00:00Z",
            "verdict": "design_gap",
            "can_deploy": False,
            "dde_passed": True,
            "bdv_passed": False,
            "acc_passed": True
        }

        entry = AuditHistoryEntry.from_dict(data)
        assert entry.iteration_id == "test-456"
        assert entry.verdict == "design_gap"
        assert entry.can_deploy is False
        assert entry.bdv_passed is False


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_storage_singleton(self, temp_storage_dir):
        """Test get_storage returns same instance."""
        import tri_audit.storage as storage_module

        # Reset global storage
        storage_module._storage = None

        config = StorageConfig(base_dir=temp_storage_dir)
        storage1 = get_storage(config)
        storage2 = get_storage()

        # Should be same instance
        assert storage1 is storage2

        # Cleanup
        storage_module._storage = None
