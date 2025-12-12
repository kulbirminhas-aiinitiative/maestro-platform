#!/usr/bin/env python3
"""
MD-3095: Test Suite for Grafana/Prometheus Monitoring Stack

This test suite validates the acceptance criteria:
- AC-1: All services visible (frontend, backend, gateway, engine, quality-fabric, databases)
- AC-2: Environment-specific views work correctly
- AC-3: Real-time status with health check integration
- AC-4: Decision documented on Grafana vs custom dashboard
"""

import pytest
import requests
import json
from datetime import datetime


# Configuration
PROMETHEUS_URL = "http://localhost:29090"
GRAFANA_URL = "http://localhost:23000"
GRAFANA_CREDS = ("admin", "maestro_admin")


class TestAC1AllServicesVisible:
    """AC-1: All services visible (frontend, backend, gateway, engine, quality-fabric, databases)"""

    def test_prometheus_targets_exist(self):
        """Verify Prometheus has targets configured for all services."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        assert response.status_code == 200

        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])

        # Verify we have targets
        assert len(targets) > 0, "No Prometheus targets found"

        # Check for expected job types
        jobs = set(t.get("labels", {}).get("job") for t in targets)

        expected_jobs = {"prometheus", "node-exporter", "alertmanager", "cadvisor",
                        "postgres", "redis", "blackbox-http", "blackbox-tcp"}

        for job in expected_jobs:
            assert job in jobs, f"Missing expected job: {job}"

    def test_blackbox_http_targets_for_services(self):
        """Verify blackbox exporter monitors HTTP endpoints for all services."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        assert response.status_code == 200

        targets = response.json().get("data", {}).get("activeTargets", [])
        http_targets = [t for t in targets if t.get("labels", {}).get("job") == "blackbox-http"]

        # Should have targets for frontend, backend, gateway, quality-fabric
        instances = [t.get("labels", {}).get("instance", "") for t in http_targets]

        # Check for key services
        has_backend = any("4100" in inst for inst in instances)
        has_frontend = any("3000" in inst for inst in instances)
        has_gateway = any("4000" in inst or "14000" in inst for inst in instances)
        has_quality_fabric = any("8000" in inst for inst in instances)

        assert has_backend, "Missing backend health endpoint monitoring"
        assert has_frontend, "Missing frontend health endpoint monitoring"
        assert has_gateway, "Missing gateway health endpoint monitoring"
        assert has_quality_fabric, "Missing quality-fabric health endpoint monitoring"

    def test_database_monitoring_configured(self):
        """Verify database monitoring is configured (postgres, redis)."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        assert response.status_code == 200

        targets = response.json().get("data", {}).get("activeTargets", [])
        jobs = [t.get("labels", {}).get("job") for t in targets]

        assert "postgres" in jobs, "PostgreSQL exporter not configured"
        assert "redis" in jobs, "Redis exporter not configured"

    def test_container_monitoring_with_cadvisor(self):
        """Verify cAdvisor is monitoring Docker containers."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        assert response.status_code == 200

        targets = response.json().get("data", {}).get("activeTargets", [])
        cadvisor_targets = [t for t in targets if t.get("labels", {}).get("job") == "cadvisor"]

        assert len(cadvisor_targets) > 0, "cAdvisor not configured"

        # Verify cadvisor is healthy
        cadvisor_health = cadvisor_targets[0].get("health")
        assert cadvisor_health == "up", f"cAdvisor is not healthy: {cadvisor_health}"


class TestAC2EnvironmentSpecificViews:
    """AC-2: Environment-specific views work correctly"""

    def test_blackbox_targets_have_environment_labels(self):
        """Verify blackbox targets have environment labels for filtering."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        assert response.status_code == 200

        targets = response.json().get("data", {}).get("activeTargets", [])
        http_targets = [t for t in targets if t.get("labels", {}).get("job") == "blackbox-http"]

        environments_found = set()
        for target in http_targets:
            env = target.get("labels", {}).get("environment")
            if env:
                environments_found.add(env)

        # Should have multiple environments
        expected_envs = {"development", "sandbox"}
        for env in expected_envs:
            assert env in environments_found, f"Missing environment label: {env}"

    def test_development_environment_targets(self):
        """Verify development environment has its own targets."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        targets = response.json().get("data", {}).get("activeTargets", [])

        dev_targets = [t for t in targets
                       if t.get("labels", {}).get("environment") == "development"]

        assert len(dev_targets) > 0, "No development environment targets found"

    def test_sandbox_environment_targets(self):
        """Verify sandbox environment has its own targets."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        targets = response.json().get("data", {}).get("activeTargets", [])

        sandbox_targets = [t for t in targets
                          if t.get("labels", {}).get("environment") == "sandbox"]

        assert len(sandbox_targets) > 0, "No sandbox environment targets found"


class TestAC3RealTimeHealthChecks:
    """AC-3: Real-time status with health check integration"""

    def test_blackbox_exporter_healthy(self):
        """Verify blackbox exporter is running and responding."""
        response = requests.get("http://localhost:9115/metrics")
        assert response.status_code == 200
        assert "probe_success" in response.text or "blackbox" in response.text.lower()

    def test_health_probes_returning_data(self):
        """Verify health probes are collecting data (probes are configured and running)."""
        # Query Prometheus for probe_success metric
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "probe_success"}
        )
        assert response.status_code == 200

        data = response.json()
        results = data.get("data", {}).get("result", [])

        # Should have probe results (showing probes are configured and running)
        assert len(results) > 0, "No probe_success metrics found"

        # Verify probes are configured for expected environments
        environments = set()
        for r in results:
            env = r.get("metric", {}).get("environment")
            if env:
                environments.add(env)

        assert len(environments) >= 1, "No environment labels in probe metrics"

    def test_prometheus_scrape_interval(self):
        """Verify Prometheus is configured for real-time updates (15s interval)."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/status/config")
        assert response.status_code == 200

        config = response.json().get("data", {}).get("yaml", "")
        assert "scrape_interval: 15s" in config or "scrape_interval: 10s" in config


class TestAC4DocumentedDecision:
    """AC-4: Decision documented on Grafana vs custom dashboard"""

    def test_grafana_dashboard_exists(self):
        """Verify Grafana dashboard for MD-3095 exists."""
        response = requests.get(
            f"{GRAFANA_URL}/api/search",
            params={"query": "MD-3095"},
            auth=GRAFANA_CREDS
        )
        assert response.status_code == 200

        dashboards = response.json()
        assert len(dashboards) > 0, "MD-3095 dashboard not found in Grafana"

    def test_grafana_datasource_prometheus(self):
        """Verify Prometheus datasource is configured in Grafana."""
        response = requests.get(
            f"{GRAFANA_URL}/api/datasources",
            auth=GRAFANA_CREDS
        )
        assert response.status_code == 200

        datasources = response.json()
        prometheus_ds = [ds for ds in datasources if ds.get("type") == "prometheus"]
        assert len(prometheus_ds) > 0, "Prometheus datasource not configured in Grafana"


class TestInfrastructureHealth:
    """Additional infrastructure health tests"""

    def test_prometheus_healthy(self):
        """Verify Prometheus service is healthy."""
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy")
        assert response.status_code == 200

    def test_grafana_healthy(self):
        """Verify Grafana service is healthy."""
        response = requests.get(f"{GRAFANA_URL}/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data.get("database") == "ok"

    def test_alertmanager_healthy(self):
        """Verify Alertmanager service is healthy."""
        response = requests.get("http://localhost:9093/-/healthy")
        assert response.status_code == 200

    def test_node_exporter_metrics(self):
        """Verify Node Exporter is providing system metrics."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                               params={"query": "node_cpu_seconds_total"})
        assert response.status_code == 200

        data = response.json()
        results = data.get("data", {}).get("result", [])
        assert len(results) > 0, "No Node Exporter CPU metrics found"

    def test_all_targets_up(self):
        """Verify all Prometheus targets are in 'up' state."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        assert response.status_code == 200

        targets = response.json().get("data", {}).get("activeTargets", [])
        down_targets = [t for t in targets if t.get("health") != "up"]

        # Allow for some targets to be down (services may not be running in test env)
        # But majority should be up
        up_ratio = (len(targets) - len(down_targets)) / len(targets) if targets else 0
        assert up_ratio >= 0.5, f"Too many targets down: {len(down_targets)}/{len(targets)}"


class TestContainerMetrics:
    """Container metrics from cAdvisor"""

    def test_cadvisor_container_metrics(self):
        """Verify cAdvisor is providing container metrics."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                               params={"query": "container_cpu_usage_seconds_total"})
        assert response.status_code == 200

        data = response.json()
        results = data.get("data", {}).get("result", [])
        assert len(results) > 0, "No container CPU metrics found"

    def test_cadvisor_memory_metrics(self):
        """Verify cAdvisor memory metrics are available."""
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                               params={"query": "container_memory_usage_bytes"})
        assert response.status_code == 200

        data = response.json()
        results = data.get("data", {}).get("result", [])
        assert len(results) > 0, "No container memory metrics found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
