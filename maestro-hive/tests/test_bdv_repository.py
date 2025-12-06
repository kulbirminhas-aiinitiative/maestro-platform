"""
Tests for BDV Repository (MD-2097)

Validates:
- Database model creation
- Execution saving/retrieval
- Scenario result operations
- Contract fulfillment tracking
- Flake history operations
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdv.db.models import (
    BDVExecution,
    BDVScenarioResult,
    BDVContractFulfillment,
    BDVFlakeHistory
)
from bdv.db.repository import BDVRepository


@pytest.fixture
def repository():
    """Create a test repository with SQLite"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    repo = BDVRepository(f"sqlite:///{db_path}")
    repo.create_tables()
    yield repo

    # Cleanup
    import os
    os.unlink(db_path)


class TestBDVExecutionModel:
    """Tests for BDVExecution model"""

    def test_pass_rate_calculation(self):
        """Test pass rate calculation"""
        execution = BDVExecution(
            execution_id="test",
            iteration_id="iter",
            started_at=datetime.utcnow(),
            total_scenarios=10,
            passed=8,
            failed=2,
            skipped=0
        )
        assert execution.pass_rate == 0.8

    def test_pass_rate_zero_scenarios(self):
        """Test pass rate with zero scenarios"""
        execution = BDVExecution(
            execution_id="test",
            iteration_id="iter",
            started_at=datetime.utcnow(),
            total_scenarios=0,
            passed=0,
            failed=0,
            skipped=0
        )
        assert execution.pass_rate == 0.0

    def test_is_successful(self):
        """Test is_successful property"""
        execution = BDVExecution(
            execution_id="test",
            iteration_id="iter",
            started_at=datetime.utcnow(),
            total_scenarios=10,
            passed=10,
            failed=0,
            skipped=0
        )
        assert execution.is_successful is True

    def test_is_not_successful(self):
        """Test is_successful with failures"""
        execution = BDVExecution(
            execution_id="test",
            iteration_id="iter",
            started_at=datetime.utcnow(),
            total_scenarios=10,
            passed=8,
            failed=2,
            skipped=0
        )
        assert execution.is_successful is False


class TestBDVScenarioResultModel:
    """Tests for BDVScenarioResult model"""

    def test_duration_seconds_conversion(self):
        """Test duration conversion from ms to seconds"""
        result = BDVScenarioResult(
            execution_id="test",
            feature_file="test.feature",
            scenario_name="Test",
            status="passed",
            duration_ms=1500
        )
        assert result.duration_seconds == 1.5


class TestBDVRepository:
    """Tests for BDVRepository class"""

    def test_initialization(self, repository):
        """Test repository initialization"""
        assert repository is not None
        assert repository.engine is not None

    def test_save_execution(self, repository):
        """Test saving an execution"""
        execution = repository.save_execution(
            execution_id="exec-001",
            iteration_id="iter-001",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            total_scenarios=5,
            passed=4,
            failed=1,
            skipped=0,
            duration_seconds=10.5
        )

        assert execution is not None

    def test_get_execution(self, repository):
        """Test retrieving an execution"""
        repository.save_execution(
            execution_id="exec-002",
            iteration_id="iter-001",
            started_at=datetime.utcnow(),
            total_scenarios=3
        )

        result = repository.get_execution("exec-002")
        assert result is not None
        assert result['total_scenarios'] == 3

    def test_get_execution_not_found(self, repository):
        """Test retrieving non-existent execution"""
        result = repository.get_execution("non-existent")
        assert result is None

    def test_get_execution_history(self, repository):
        """Test getting execution history"""
        # Save multiple executions
        for i in range(5):
            repository.save_execution(
                execution_id=f"hist-{i}",
                iteration_id="iter-001",
                started_at=datetime.utcnow(),
                total_scenarios=i + 1
            )

        history = repository.get_execution_history(days=1, limit=10)
        assert len(history) == 5

    def test_update_execution(self, repository):
        """Test updating an execution"""
        repository.save_execution(
            execution_id="exec-update",
            iteration_id="iter-001",
            started_at=datetime.utcnow(),
            total_scenarios=5,
            passed=0
        )

        repository.update_execution("exec-update", passed=5)

        result = repository.get_execution("exec-update")
        assert result['passed'] == 5

    def test_save_scenario_result(self, repository):
        """Test saving scenario result"""
        repository.save_execution(
            execution_id="exec-scen",
            iteration_id="iter-001",
            started_at=datetime.utcnow()
        )

        result = repository.save_scenario_result(
            execution_id="exec-scen",
            feature_file="auth.feature",
            scenario_name="Login",
            status="passed",
            duration_ms=500
        )

        assert result is not None

    def test_save_scenario_results_batch(self, repository):
        """Test batch saving scenario results"""
        repository.save_execution(
            execution_id="exec-batch",
            iteration_id="iter-001",
            started_at=datetime.utcnow()
        )

        results = [
            {'feature_file': 'auth.feature', 'scenario_name': 'Login', 'status': 'passed', 'duration': 0.5},
            {'feature_file': 'auth.feature', 'scenario_name': 'Logout', 'status': 'passed', 'duration': 0.3},
            {'feature_file': 'user.feature', 'scenario_name': 'Profile', 'status': 'failed', 'duration': 1.0}
        ]

        count = repository.save_scenario_results_batch("exec-batch", results)
        assert count == 3

    def test_get_scenario_results(self, repository):
        """Test getting scenario results for an execution"""
        repository.save_execution(
            execution_id="exec-results",
            iteration_id="iter-001",
            started_at=datetime.utcnow()
        )

        repository.save_scenario_result(
            execution_id="exec-results",
            feature_file="test.feature",
            scenario_name="Test 1",
            status="passed",
            duration_ms=100
        )
        repository.save_scenario_result(
            execution_id="exec-results",
            feature_file="test.feature",
            scenario_name="Test 2",
            status="failed",
            duration_ms=200
        )

        results = repository.get_scenario_results("exec-results")
        assert len(results) == 2

    def test_save_contract_fulfillment(self, repository):
        """Test saving contract fulfillment"""
        repository.save_execution(
            execution_id="exec-contract",
            iteration_id="iter-001",
            started_at=datetime.utcnow()
        )

        fulfillment = repository.save_contract_fulfillment(
            execution_id="exec-contract",
            contract_id="auth-api",
            is_fulfilled=True,
            pass_rate=1.0,
            scenarios_passed=5,
            scenarios_failed=0
        )

        assert fulfillment is not None
        assert fulfillment['is_fulfilled'] is True

    def test_get_contract_fulfillment_history(self, repository):
        """Test getting contract fulfillment history"""
        repository.save_execution(
            execution_id="exec-contract-hist",
            iteration_id="iter-001",
            started_at=datetime.utcnow()
        )

        repository.save_contract_fulfillment(
            execution_id="exec-contract-hist",
            contract_id="test-contract",
            is_fulfilled=True
        )

        history = repository.get_contract_fulfillment_history("test-contract")
        assert len(history) == 1

    def test_save_flake_history(self, repository):
        """Test saving flake history"""
        history = repository.save_flake_history(
            scenario_id="auth::login",
            scenario_name="Login",
            feature_file="auth.feature",
            flake_rate=0.15,
            run_count=3,
            passed_runs=2,
            failed_runs=1
        )

        assert history is not None
        assert history['flake_rate'] == 0.15

    def test_get_historical_flake_rate(self, repository):
        """Test getting historical flake rate"""
        # Save multiple flake history entries
        for i in range(3):
            repository.save_flake_history(
                scenario_id="flaky-test",
                scenario_name="Flaky",
                feature_file="flaky.feature",
                flake_rate=0.10 + (i * 0.05),
                run_count=3
            )

        rate = repository.get_historical_flake_rate("flaky-test")
        assert rate > 0

    def test_get_quarantined_scenarios(self, repository):
        """Test getting quarantined scenarios"""
        repository.save_flake_history(
            scenario_id="quarantined-test",
            scenario_name="Quarantined",
            feature_file="test.feature",
            flake_rate=0.50,
            is_quarantined=True,
            quarantine_reason="Too flaky"
        )

        quarantined = repository.get_quarantined_scenarios()
        assert len(quarantined) == 1
        assert quarantined[0]['scenario_id'] == "quarantined-test"

    def test_update_quarantine_status(self, repository):
        """Test updating quarantine status"""
        repository.save_flake_history(
            scenario_id="toggle-quarantine",
            scenario_name="Toggle",
            feature_file="test.feature",
            flake_rate=0.20,
            is_quarantined=False
        )

        repository.update_quarantine_status(
            "toggle-quarantine",
            is_quarantined=True,
            reason="Manual quarantine"
        )

        quarantined = repository.get_quarantined_scenarios()
        found = [q for q in quarantined if q['scenario_id'] == "toggle-quarantine"]
        assert len(found) == 1

    def test_get_execution_stats(self, repository):
        """Test getting execution statistics"""
        # Save some test data
        repository.save_execution(
            execution_id="stat-1",
            iteration_id="iter-001",
            started_at=datetime.utcnow(),
            total_scenarios=10,
            passed=8,
            failed=2,
            duration_seconds=30.0
        )
        repository.save_execution(
            execution_id="stat-2",
            iteration_id="iter-001",
            started_at=datetime.utcnow(),
            total_scenarios=10,
            passed=10,
            failed=0,
            duration_seconds=25.0
        )

        stats = repository.get_execution_stats(days=1)

        assert stats['total_executions'] == 2
        assert stats['total_scenarios'] == 20
        assert stats['total_passed'] == 18
        assert stats['total_failed'] == 2

    def test_scenario_history(self, repository):
        """Test getting scenario history"""
        for i in range(3):
            repository.save_execution(
                execution_id=f"exec-hist-{i}",
                iteration_id="iter-001",
                started_at=datetime.utcnow()
            )
            repository.save_scenario_result(
                execution_id=f"exec-hist-{i}",
                feature_file="history.feature",
                scenario_name="History Test",
                status="passed" if i % 2 == 0 else "failed",
                duration_ms=100
            )

        history = repository.get_scenario_history("history.feature", "History Test")
        assert len(history) == 3


class TestModelToDictConversions:
    """Tests for model to_dict conversions"""

    def test_execution_to_dict(self, repository):
        """Test BDVExecution to_dict"""
        repository.save_execution(
            execution_id="dict-test",
            iteration_id="iter-001",
            started_at=datetime.utcnow(),
            total_scenarios=10,
            passed=8,
            failed=2
        )

        d = repository.get_execution("dict-test")

        assert 'execution_id' in d
        assert 'pass_rate' in d
        assert d['total_scenarios'] == 10

    def test_contract_fulfillment_to_dict(self):
        """Test BDVContractFulfillment to_dict"""
        fulfillment = BDVContractFulfillment(
            execution_id="test",
            contract_id="api-v1",
            is_fulfilled=True,
            scenarios_passed=5,
            scenarios_failed=0
        )

        d = fulfillment.to_dict()
        assert d['contract_id'] == "api-v1"
        assert d['total_scenarios'] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
