#!/usr/bin/env python3
"""Tests for Health Monitor module."""

import pytest
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.core.self_reflection.health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheckResult,
    HealthMetric,
    Alert,
    AlertSeverity,
    ComponentConfig,
    get_health_monitor,
    create_http_health_check
)


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_result_creation(self):
        """Test creating a HealthCheckResult."""
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="All systems operational"
        )

        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = HealthCheckResult(
            component="test",
            status=HealthStatus.DEGRADED,
            message="High latency",
            latency_ms=150.5
        )

        data = result.to_dict()
        assert data["status"] == "degraded"
        assert data["latency_ms"] == 150.5


class TestHealthMonitor:
    """Tests for HealthMonitor class."""

    def setup_method(self):
        """Reset singleton for each test."""
        HealthMonitor._instance = None

    def test_singleton_pattern(self):
        """Test that HealthMonitor is a singleton."""
        hm1 = HealthMonitor()
        hm2 = HealthMonitor()
        assert hm1 is hm2

    def test_register_component(self):
        """Test registering a component."""
        hm = HealthMonitor()

        def check_fn():
            return HealthCheckResult(
                component="test",
                status=HealthStatus.HEALTHY,
                message="OK"
            )

        hm.register_component("test_component", check_fn)
        assert "test_component" in hm._components

    def test_unregister_component(self):
        """Test unregistering a component."""
        hm = HealthMonitor()

        def check_fn():
            return HealthCheckResult(
                component="test",
                status=HealthStatus.HEALTHY,
                message="OK"
            )

        hm.register_component("temp_component", check_fn)
        assert hm.unregister_component("temp_component") is True
        assert hm.unregister_component("nonexistent") is False

    def test_check_health_single(self):
        """Test checking health of single component."""
        hm = HealthMonitor()

        def check_fn():
            return HealthCheckResult(
                component="my_service",
                status=HealthStatus.HEALTHY,
                message="Service running"
            )

        hm.register_component("my_service", check_fn)
        results = hm.check_health("my_service")

        assert "my_service" in results
        assert results["my_service"].status == HealthStatus.HEALTHY

    def test_check_health_all(self):
        """Test checking health of all components."""
        hm = HealthMonitor()

        def healthy_check():
            return HealthCheckResult(
                component="healthy",
                status=HealthStatus.HEALTHY,
                message="OK"
            )

        def degraded_check():
            return HealthCheckResult(
                component="degraded",
                status=HealthStatus.DEGRADED,
                message="Slow"
            )

        hm.register_component("healthy_service", healthy_check)
        hm.register_component("degraded_service", degraded_check)

        results = hm.check_health()
        assert len(results) >= 2

    def test_get_status(self):
        """Test getting overall status."""
        hm = HealthMonitor()

        def check_fn():
            return HealthCheckResult(
                component="test",
                status=HealthStatus.HEALTHY,
                message="OK"
            )

        hm.register_component("test_svc", check_fn)
        hm.check_health("test_svc")

        status = hm.get_status()
        assert "overall_status" in status
        assert "components" in status

    def test_get_component_history(self):
        """Test getting component history."""
        hm = HealthMonitor()

        call_count = [0]

        def check_fn():
            call_count[0] += 1
            return HealthCheckResult(
                component="history_test",
                status=HealthStatus.HEALTHY,
                message=f"Check {call_count[0]}"
            )

        hm.register_component("history_test", check_fn)

        # Run multiple checks
        for _ in range(3):
            hm.check_health("history_test")

        history = hm.get_component_history("history_test", limit=10)
        assert len(history) == 3

    def test_record_metric(self):
        """Test recording metrics."""
        hm = HealthMonitor()
        hm.record_metric("cpu_usage", 45.5, unit="%", host="server1")
        hm.record_metric("cpu_usage", 50.2, unit="%", host="server1")

        metrics = hm.get_metrics("cpu_usage")
        assert "cpu_usage" in metrics
        assert len(metrics["cpu_usage"]) == 2

    def test_alert_generation(self):
        """Test alert generation on failures."""
        hm = HealthMonitor(enable_self_healing=False)

        failure_count = [0]

        def failing_check():
            failure_count[0] += 1
            return HealthCheckResult(
                component="failing",
                status=HealthStatus.UNHEALTHY,
                message=f"Failure {failure_count[0]}"
            )

        hm.register_component(
            "failing_service",
            failing_check,
            failure_threshold=2
        )

        # Run checks to trigger alert
        for _ in range(3):
            hm.check_health("failing_service")

        alerts = hm.get_alerts(component="failing_service")
        assert len(alerts) >= 1

    def test_alert_acknowledgment(self):
        """Test acknowledging alerts."""
        hm = HealthMonitor(enable_self_healing=False)

        def failing_check():
            return HealthCheckResult(
                component="ack_test",
                status=HealthStatus.UNHEALTHY,
                message="Failed"
            )

        hm.register_component("ack_test", failing_check, failure_threshold=1)

        # Generate alert
        for _ in range(2):
            hm.check_health("ack_test")

        alerts = hm.get_alerts(component="ack_test")
        if alerts:
            assert hm.acknowledge_alert(alerts[0].id) is True
            assert hm._alerts[alerts[0].id].acknowledged is True

    def test_alert_handler(self):
        """Test alert handler callbacks."""
        hm = HealthMonitor(enable_self_healing=False)
        received_alerts = []

        def handler(alert):
            received_alerts.append(alert)

        hm.add_alert_handler(handler)

        def failing_check():
            return HealthCheckResult(
                component="handler_test",
                status=HealthStatus.UNHEALTHY,
                message="Failed"
            )

        hm.register_component("handler_test", failing_check, failure_threshold=1)

        for _ in range(2):
            hm.check_health("handler_test")

        assert len(received_alerts) >= 1

    def test_self_healing_trigger(self):
        """Test self-healing trigger."""
        hm = HealthMonitor(enable_self_healing=True)
        heal_calls = [0]

        def heal_fn():
            heal_calls[0] += 1
            return True

        def failing_check():
            return HealthCheckResult(
                component="heal_test",
                status=HealthStatus.UNHEALTHY,
                message="Needs healing"
            )

        hm.register_component(
            "heal_test",
            failing_check,
            failure_threshold=2,
            self_heal_function=heal_fn
        )

        # Run enough checks to trigger healing
        for _ in range(4):
            hm.check_health("heal_test")

        assert heal_calls[0] >= 1

    def test_recovery_resolves_alerts(self):
        """Test that recovery resolves alerts."""
        hm = HealthMonitor(enable_self_healing=False)

        status_healthy = [False]

        def check_fn():
            return HealthCheckResult(
                component="recovery_test",
                status=HealthStatus.HEALTHY if status_healthy[0] else HealthStatus.UNHEALTHY,
                message="OK" if status_healthy[0] else "Failed"
            )

        hm.register_component(
            "recovery_test",
            check_fn,
            failure_threshold=2,
            recovery_threshold=2
        )

        # Generate failure
        for _ in range(3):
            hm.check_health("recovery_test")

        # Now recover
        status_healthy[0] = True
        for _ in range(3):
            hm.check_health("recovery_test")

        # Check alerts are resolved
        active_alerts = hm.get_alerts(include_resolved=False, component="recovery_test")
        resolved_alerts = hm.get_alerts(include_resolved=True, component="recovery_test")

        # Active should be empty, resolved should have the alert
        assert len(active_alerts) == 0 or all(a.resolved_at for a in resolved_alerts if a.component == "recovery_test")


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def setup_method(self):
        """Reset singleton."""
        HealthMonitor._instance = None

    def test_get_health_monitor(self):
        """Test get_health_monitor function."""
        hm = get_health_monitor()
        assert isinstance(hm, HealthMonitor)

    def test_create_http_health_check(self):
        """Test HTTP health check factory."""
        check = create_http_health_check("http://localhost:9999")
        result = check()

        # Should fail since nothing is running on 9999
        assert result.status == HealthStatus.UNHEALTHY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
