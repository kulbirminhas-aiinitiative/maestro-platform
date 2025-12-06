"""
Tests for BDVOrchestrator (MD-2094)

Validates:
- BDVOrchestrator initialization
- RetryConfig behavior
- Hook registration and execution
- Sequential and parallel execution
- Result aggregation
"""

import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bdv.bdv_runner import (
    BDVOrchestrator,
    BDVRunner,
    BDVResult,
    ScenarioResult,
    RetryConfig
)


class TestRetryConfig:
    """Tests for RetryConfig class"""

    def test_default_values(self):
        """Test default configuration values"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0

    def test_custom_values(self):
        """Test custom configuration"""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0

    def test_get_delay_exponential(self):
        """Test exponential backoff calculation"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=100.0)

        # Attempt 0: 1 * 2^0 = 1
        assert config.get_delay(0) == 1.0

        # Attempt 1: 1 * 2^1 = 2
        assert config.get_delay(1) == 2.0

        # Attempt 2: 1 * 2^2 = 4
        assert config.get_delay(2) == 4.0

        # Attempt 3: 1 * 2^3 = 8
        assert config.get_delay(3) == 8.0

    def test_get_delay_max_cap(self):
        """Test that delay is capped at max_delay"""
        config = RetryConfig(base_delay=10.0, exponential_base=2.0, max_delay=30.0)

        # Attempt 3: 10 * 2^3 = 80, but capped at 30
        assert config.get_delay(3) == 30.0


class TestScenarioResult:
    """Tests for ScenarioResult class"""

    def test_creation(self):
        """Test ScenarioResult creation"""
        result = ScenarioResult(
            feature_file="test.feature",
            scenario_name="Test scenario",
            status="passed",
            duration=1.5
        )
        assert result.feature_file == "test.feature"
        assert result.scenario_name == "Test scenario"
        assert result.status == "passed"
        assert result.duration == 1.5
        assert result.retry_count == 0
        assert result.worker_id is None

    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = ScenarioResult(
            feature_file="test.feature",
            scenario_name="Test scenario",
            status="passed",
            duration=1.5,
            retry_count=2,
            worker_id="worker-0"
        )
        d = result.to_dict()
        assert d['feature_file'] == "test.feature"
        assert d['retry_count'] == 2
        assert d['worker_id'] == "worker-0"


class TestBDVOrchestrator:
    """Tests for BDVOrchestrator class"""

    def test_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = BDVOrchestrator(
            base_url="http://localhost:8000",
            max_workers=4
        )
        assert orchestrator.max_workers == 4
        assert orchestrator.retry_config.max_retries == 3
        assert len(orchestrator._hooks) == 6

    def test_custom_retry_config(self):
        """Test orchestrator with custom retry config"""
        config = RetryConfig(max_retries=5, base_delay=0.5)
        orchestrator = BDVOrchestrator(
            base_url="http://localhost:8000",
            retry_config=config
        )
        assert orchestrator.retry_config.max_retries == 5
        assert orchestrator.retry_config.base_delay == 0.5

    def test_hook_registration(self):
        """Test hook registration"""
        orchestrator = BDVOrchestrator(base_url="http://localhost:8000")

        callback = MagicMock()
        orchestrator.register_hook('before_suite', callback)

        assert callback in orchestrator._hooks['before_suite']

    def test_hook_execution(self):
        """Test hook execution"""
        orchestrator = BDVOrchestrator(base_url="http://localhost:8000")

        callback = MagicMock()
        orchestrator.register_hook('before_suite', callback)

        orchestrator._execute_hooks('before_suite', iteration_id='test-001')

        callback.assert_called_once_with(iteration_id='test-001')

    def test_hook_failure_handling(self):
        """Test that hook failures don't break execution"""
        orchestrator = BDVOrchestrator(base_url="http://localhost:8000")

        def failing_hook(**kwargs):
            raise Exception("Hook failed")

        orchestrator.register_hook('before_suite', failing_hook)

        # Should not raise exception
        orchestrator._execute_hooks('before_suite', iteration_id='test-001')

    @patch.object(BDVRunner, 'discover_features')
    def test_run_suite_empty(self, mock_discover):
        """Test run_suite with no features"""
        mock_discover.return_value = []

        orchestrator = BDVOrchestrator(base_url="http://localhost:8000")
        result = orchestrator.run_suite(iteration_id='test-empty')

        assert result.total_scenarios == 0
        assert result.passed == 0

    @patch.object(BDVRunner, 'run')
    @patch.object(BDVRunner, 'discover_features')
    def test_run_suite_sequential(self, mock_discover, mock_run):
        """Test sequential suite execution"""
        mock_discover.return_value = [Path("test1.feature"), Path("test2.feature")]
        mock_run.return_value = BDVResult(
            iteration_id='test',
            total_scenarios=2,
            passed=2,
            failed=0,
            skipped=0,
            duration=1.0,
            timestamp='2025-01-01T00:00:00Z',
            scenarios=[],
            summary={}
        )

        orchestrator = BDVOrchestrator(
            base_url="http://localhost:8000",
            retry_config=RetryConfig(max_retries=0)  # Disable retries for test
        )
        result = orchestrator.run_suite(iteration_id='test-seq', parallel=False)

        assert result.summary.get('execution_mode') == 'sequential'
        assert mock_run.call_count == 2

    @patch.object(BDVRunner, 'run')
    @patch.object(BDVRunner, 'discover_features')
    def test_run_suite_parallel(self, mock_discover, mock_run):
        """Test parallel suite execution"""
        mock_discover.return_value = [
            Path("test1.feature"),
            Path("test2.feature"),
            Path("test3.feature")
        ]
        mock_run.return_value = BDVResult(
            iteration_id='test',
            total_scenarios=1,
            passed=1,
            failed=0,
            skipped=0,
            duration=1.0,
            timestamp='2025-01-01T00:00:00Z',
            scenarios=[],
            summary={}
        )

        orchestrator = BDVOrchestrator(
            base_url="http://localhost:8000",
            max_workers=2,
            retry_config=RetryConfig(max_retries=0)
        )
        result = orchestrator.run_suite(iteration_id='test-par', parallel=True)

        assert result.summary.get('execution_mode') == 'parallel'
        assert result.summary.get('workers') == 2

    @patch.object(BDVRunner, 'run')
    def test_retry_on_failure(self, mock_run):
        """Test retry logic on failure"""
        # First call fails, second succeeds
        mock_run.side_effect = [
            BDVResult(
                iteration_id='test',
                total_scenarios=1,
                passed=0,
                failed=1,
                skipped=0,
                duration=1.0,
                timestamp='2025-01-01T00:00:00Z',
                scenarios=[],
                summary={}
            ),
            BDVResult(
                iteration_id='test',
                total_scenarios=1,
                passed=1,
                failed=0,
                skipped=0,
                duration=1.0,
                timestamp='2025-01-01T00:00:00Z',
                scenarios=[],
                summary={}
            )
        ]

        orchestrator = BDVOrchestrator(
            base_url="http://localhost:8000",
            retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        )

        result = orchestrator._run_with_retry(
            feature='test.feature',
            iteration_id='test-retry',
            tags=None
        )

        assert result.passed == 1
        assert result.failed == 0
        assert mock_run.call_count == 2


class TestIntegration:
    """Integration tests with quality-fabric API"""

    @pytest.mark.integration
    def test_orchestrator_with_real_features(self):
        """Test orchestrator with real feature files"""
        orchestrator = BDVOrchestrator(
            base_url="http://localhost:8000",
            features_path="features/",
            retry_config=RetryConfig(max_retries=1, base_delay=0.1)
        )

        # Discover features
        features = orchestrator.runner.discover_features()

        if features:
            # Run single feature for quick test
            result = orchestrator.run_suite(
                features=[str(features[0])],
                iteration_id='integration-test'
            )

            assert result.iteration_id == 'integration-test'
            assert isinstance(result.duration, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
