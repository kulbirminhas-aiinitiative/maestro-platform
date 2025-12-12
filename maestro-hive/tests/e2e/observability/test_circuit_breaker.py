"""
E2E Tests for Circuit Breaker State Monitoring.

EPIC: MD-3037 - Observability & Tracing E2E Tests
Acceptance Criteria:
- AC3: Circuit breaker state monitoring tested

IMPORTANT: These tests import from REAL implementation modules.
NO local mock classes are defined in this file.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

# Import from REAL implementation modules
import sys
sys.path.insert(0, 'src')

from maestro_hive.enterprise.resilience.circuit_breaker import (
    CircuitState,
    CircuitBreakerConfig,
    CircuitStats,
    CircuitBreakerError,
    CircuitBreaker,
    CircuitBreakerRegistry,
)


# =============================================================================
# Test Class: Circuit Breaker State Monitoring (AC3)
# =============================================================================

class TestCircuitBreakerStateMonitoring:
    """Tests for circuit breaker state monitoring (AC3)."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with test configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1,  # Short timeout for testing
            half_open_max_calls=2,
        )
        return CircuitBreaker("test_circuit", config)

    @pytest.fixture
    def registry(self):
        """Create a fresh circuit breaker registry."""
        # Reset singleton for clean tests
        CircuitBreakerRegistry._instance = None
        CircuitBreakerRegistry._breakers = {}
        return CircuitBreakerRegistry.get_instance()

    def test_initial_state_is_closed(self, circuit_breaker):
        """
        Test: Circuit breaker starts in CLOSED state.
        AC3: State monitoring - initial state.
        """
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.is_closed is True
        assert circuit_breaker.is_open is False

    def test_state_transition_closed_to_open(self, circuit_breaker):
        """
        Test: Circuit transitions from CLOSED to OPEN after failures.
        AC3: State monitoring - failure transitions.
        """
        # Record failures to reach threshold
        for _ in range(3):
            circuit_breaker._record_failure()

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.is_open is True
        assert circuit_breaker.is_closed is False

    @pytest.mark.asyncio
    async def test_state_transition_open_to_half_open(self, circuit_breaker):
        """
        Test: Circuit transitions from OPEN to HALF_OPEN after timeout.
        AC3: State monitoring - timeout transitions.
        """
        # Force to OPEN state
        for _ in range(3):
            circuit_breaker._record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.5)

        # Accessing state should trigger transition to HALF_OPEN
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_state_transition_half_open_to_closed(self, circuit_breaker):
        """
        Test: Circuit transitions from HALF_OPEN to CLOSED after successes.
        AC3: State monitoring - recovery transitions.
        """
        # Force to OPEN, then wait for HALF_OPEN
        for _ in range(3):
            circuit_breaker._record_failure()

        await asyncio.sleep(1.5)
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        # Record successes
        circuit_breaker._record_success()
        circuit_breaker._record_success()

        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_state_transition_half_open_to_open(self, circuit_breaker):
        """
        Test: Circuit returns to OPEN from HALF_OPEN on failure.
        AC3: State monitoring - half-open failure.
        """
        # Force to OPEN, then wait for HALF_OPEN
        for _ in range(3):
            circuit_breaker._record_failure()

        await asyncio.sleep(1.5)
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        # A failure in HALF_OPEN should revert to OPEN
        circuit_breaker._record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

    def test_get_status_returns_correct_data(self, circuit_breaker):
        """
        Test: get_status returns comprehensive state information.
        AC3: State monitoring - status reporting.
        """
        status = circuit_breaker.get_status()

        assert status["name"] == "test_circuit"
        assert status["state"] == "closed"
        assert "failure_count" in status
        assert "success_count" in status
        assert "stats" in status
        assert "total_calls" in status["stats"]

    def test_get_stats_tracks_calls(self, circuit_breaker):
        """
        Test: Statistics are correctly tracked.
        AC3: State monitoring - statistics.
        """
        # Record some activity
        circuit_breaker._record_success()
        circuit_breaker._record_success()
        circuit_breaker._record_failure()

        stats = circuit_breaker.get_stats()

        assert stats.total_calls == 3
        assert stats.successful_calls == 2
        assert stats.failed_calls == 1

    def test_state_change_listener(self, circuit_breaker):
        """
        Test: State change listeners are notified.
        AC3: State monitoring - event notifications.
        """
        state_changes = []

        def listener(name, old_state, new_state):
            state_changes.append({
                "name": name,
                "old": old_state,
                "new": new_state,
                "timestamp": datetime.utcnow(),
            })

        circuit_breaker.add_listener(listener)

        # Trigger state change
        for _ in range(3):
            circuit_breaker._record_failure()

        assert len(state_changes) == 1
        assert state_changes[0]["old"] == CircuitState.CLOSED
        assert state_changes[0]["new"] == CircuitState.OPEN

    def test_rejected_calls_tracking(self, circuit_breaker):
        """
        Test: Rejected calls are tracked when circuit is open.
        AC3: State monitoring - rejection tracking.
        """
        # Force to OPEN
        for _ in range(3):
            circuit_breaker._record_failure()

        # Record rejections
        circuit_breaker._record_rejection()
        circuit_breaker._record_rejection()

        stats = circuit_breaker.get_stats()
        assert stats.rejected_calls == 2

    def test_manual_reset(self, circuit_breaker):
        """
        Test: Circuit can be manually reset.
        AC3: State monitoring - manual control.
        """
        # Force to OPEN
        for _ in range(3):
            circuit_breaker._record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        # Manual reset
        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker._failure_count == 0


# =============================================================================
# Test Class: Circuit Breaker Call Protection
# =============================================================================

class TestCircuitBreakerCallProtection:
    """Tests for circuit breaker call protection."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with test configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=1,
            half_open_max_calls=2,
        )
        return CircuitBreaker("protection_test", config)

    @pytest.mark.asyncio
    async def test_call_success_tracking(self, circuit_breaker):
        """Test: Successful calls are tracked."""
        async def successful_operation():
            return "success"

        result = await circuit_breaker.call(successful_operation)

        assert result == "success"
        stats = circuit_breaker.get_stats()
        assert stats.successful_calls == 1

    @pytest.mark.asyncio
    async def test_call_failure_tracking(self, circuit_breaker):
        """Test: Failed calls are tracked."""
        async def failing_operation():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

        stats = circuit_breaker.get_stats()
        assert stats.failed_calls == 1

    @pytest.mark.asyncio
    async def test_circuit_open_rejects_calls(self, circuit_breaker):
        """Test: Open circuit rejects new calls."""
        async def operation():
            raise ValueError("Failure")

        # Trigger failures to open circuit
        for _ in range(2):
            try:
                await circuit_breaker.call(operation)
            except ValueError:
                pass

        assert circuit_breaker.state == CircuitState.OPEN

        # Next call should be rejected
        async def new_operation():
            return "should not execute"

        with pytest.raises(CircuitBreakerError) as exc_info:
            await circuit_breaker.call(new_operation)

        assert "protection_test" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator(self, circuit_breaker):
        """Test: Circuit breaker can be used as decorator."""
        @circuit_breaker
        async def decorated_operation():
            return "decorated_result"

        result = await decorated_operation()
        assert result == "decorated_result"

    @pytest.mark.asyncio
    async def test_sync_function_support(self, circuit_breaker):
        """Test: Circuit breaker supports sync functions."""
        def sync_operation():
            return "sync_result"

        result = await circuit_breaker.call(sync_operation)
        assert result == "sync_result"


# =============================================================================
# Test Class: Circuit Breaker Registry
# =============================================================================

class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        CircuitBreakerRegistry._instance = None
        CircuitBreakerRegistry._breakers = {}
        yield
        CircuitBreakerRegistry._instance = None
        CircuitBreakerRegistry._breakers = {}

    def test_singleton_instance(self):
        """Test: Registry is a singleton."""
        registry1 = CircuitBreakerRegistry.get_instance()
        registry2 = CircuitBreakerRegistry.get_instance()

        assert registry1 is registry2

    def test_get_or_create_circuit_breaker(self):
        """Test: Can create and retrieve circuit breakers."""
        registry = CircuitBreakerRegistry.get_instance()

        cb1 = registry.get_or_create("service_a")
        cb2 = registry.get_or_create("service_a")

        assert cb1 is cb2
        assert cb1.name == "service_a"

    def test_get_nonexistent_circuit_breaker(self):
        """Test: Getting nonexistent circuit breaker returns None."""
        registry = CircuitBreakerRegistry.get_instance()

        result = registry.get("nonexistent")
        assert result is None

    def test_list_all_circuit_breakers(self):
        """Test: Can list all circuit breakers status."""
        registry = CircuitBreakerRegistry.get_instance()

        registry.get_or_create("service_a")
        registry.get_or_create("service_b")
        registry.get_or_create("service_c")

        status_list = registry.list_all()

        assert len(status_list) == 3
        names = {s["name"] for s in status_list}
        assert names == {"service_a", "service_b", "service_c"}

    def test_reset_all_circuit_breakers(self):
        """Test: Can reset all circuit breakers."""
        registry = CircuitBreakerRegistry.get_instance()

        # Create and open circuit breakers
        for name in ["a", "b", "c"]:
            cb = registry.get_or_create(name)
            cb._transition_to(CircuitState.OPEN)

        # Verify all are open
        for cb in registry._breakers.values():
            assert cb.state == CircuitState.OPEN

        # Reset all
        registry.reset_all()

        # Verify all are closed
        for cb in registry._breakers.values():
            assert cb.state == CircuitState.CLOSED


# =============================================================================
# Test Class: Circuit Breaker Configuration
# =============================================================================

class TestCircuitBreakerConfiguration:
    """Tests for circuit breaker configuration."""

    def test_default_configuration(self):
        """Test: Default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_seconds == 30
        assert config.half_open_max_calls == 3

    def test_custom_configuration(self):
        """Test: Custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=5,
            timeout_seconds=60,
            half_open_max_calls=5,
        )

        cb = CircuitBreaker("custom", config)

        assert cb.config.failure_threshold == 10
        assert cb.config.success_threshold == 5
        assert cb.config.timeout_seconds == 60

    def test_exception_filtering(self):
        """Test: Specific exceptions can be excluded."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            exception_types=(ValueError,),
            exclude_exceptions=(KeyError,),
        )

        cb = CircuitBreaker("filtered", config)

        # ValueError should be tracked
        assert cb._is_tracked_exception(ValueError("test")) is True

        # KeyError should be excluded
        assert cb._is_tracked_exception(KeyError("test")) is False

        # Other exceptions not in exception_types
        assert cb._is_tracked_exception(RuntimeError("test")) is False


# =============================================================================
# Test Class: Circuit Breaker Timing
# =============================================================================

class TestCircuitBreakerTiming:
    """Tests for circuit breaker timing behavior."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with short timing for tests."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=1,
        )
        return CircuitBreaker("timing_test", config)

    def test_opened_at_timestamp(self, circuit_breaker):
        """Test: Opening timestamp is recorded."""
        assert circuit_breaker._opened_at is None

        # Force to open
        for _ in range(2):
            circuit_breaker._record_failure()

        assert circuit_breaker._opened_at is not None
        assert isinstance(circuit_breaker._opened_at, datetime)

    def test_last_failure_time(self, circuit_breaker):
        """Test: Last failure time is recorded."""
        assert circuit_breaker._last_failure_time is None

        circuit_breaker._record_failure()

        assert circuit_breaker._last_failure_time is not None
        assert isinstance(circuit_breaker._last_failure_time, datetime)

    def test_stats_track_time_in_open(self, circuit_breaker):
        """Test: Time spent in open state is tracked."""
        # Force to open
        for _ in range(2):
            circuit_breaker._record_failure()

        # Wait a bit
        import time
        time.sleep(0.1)

        # Close the circuit
        circuit_breaker.reset()

        stats = circuit_breaker.get_stats()
        assert stats.time_in_open.total_seconds() > 0

    def test_retry_after_in_error(self, circuit_breaker):
        """Test: CircuitBreakerError includes retry_after."""
        # Force to open
        for _ in range(2):
            circuit_breaker._record_failure()

        error = CircuitBreakerError(
            circuit_breaker.name,
            circuit_breaker._opened_at + timedelta(seconds=circuit_breaker.config.timeout_seconds)
        )

        assert error.retry_after is not None
        assert "retry after" in str(error)
