"""
Phase 1 Smoke Tests - Quick validation of all infrastructure components
Run these tests first to verify basic deployment health
"""

import pytest
import requests
import time
from subprocess import run


@pytest.mark.smoke
class TestMLflowSmoke:
    """MLflow smoke tests"""

    def test_mlflow_ui_accessible(self, minikube_ip):
        """Test MLflow UI is accessible"""
        url = f"http://{minikube_ip}:30500"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200, f"MLflow UI returned {response.status_code}"
        except requests.RequestException as e:
            pytest.fail(f"MLflow UI not accessible: {e}")

    def test_mlflow_health_endpoint(self, minikube_ip):
        """Test MLflow health endpoint"""
        url = f"http://{minikube_ip}:30500/health"
        response = requests.get(url, timeout=10)
        assert response.status_code == 200
        # MLflow health endpoint returns JSON or HTML depending on version
        assert response.text is not None


@pytest.mark.smoke
class TestFeastSmoke:
    """Feast smoke tests"""

    def test_feast_ui_accessible(self, minikube_ip):
        """Test Feast UI is accessible"""
        url = f"http://{minikube_ip}:30501"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302], f"Feast UI returned {response.status_code}"
        except requests.RequestException as e:
            pytest.fail(f"Feast UI not accessible: {e}")


@pytest.mark.smoke
class TestAirflowSmoke:
    """Airflow smoke tests"""

    def test_airflow_ui_accessible(self, minikube_ip):
        """Test Airflow UI is accessible"""
        url = f"http://{minikube_ip}:30502"
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            assert response.status_code == 200, f"Airflow UI returned {response.status_code}"
        except requests.RequestException as e:
            pytest.fail(f"Airflow UI not accessible: {e}")

    def test_airflow_health_endpoint(self, minikube_ip):
        """Test Airflow health endpoint"""
        url = f"http://{minikube_ip}:30502/health"
        response = requests.get(url, timeout=10)
        assert response.status_code == 200
        health_data = response.json()
        assert "metadatabase" in health_data
        assert health_data["metadatabase"]["status"] == "healthy"


@pytest.mark.smoke
class TestPrometheusSmoke:
    """Prometheus smoke tests"""

    def test_prometheus_ui_accessible(self, minikube_ip):
        """Test Prometheus UI is accessible"""
        url = f"http://{minikube_ip}:30503"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
        except requests.RequestException as e:
            pytest.fail(f"Prometheus UI not accessible: {e}")

    def test_prometheus_targets(self, minikube_ip):
        """Test Prometheus has active targets"""
        url = f"http://{minikube_ip}:30503/api/v1/targets"
        response = requests.get(url, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["activeTargets"]) > 0


@pytest.mark.smoke
class TestGrafanaSmoke:
    """Grafana smoke tests"""

    def test_grafana_ui_accessible(self, minikube_ip):
        """Test Grafana UI is accessible"""
        url = f"http://{minikube_ip}:30504"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
        except requests.RequestException as e:
            pytest.fail(f"Grafana UI not accessible: {e}")


@pytest.mark.smoke
class TestLokiSmoke:
    """Loki smoke tests"""

    def test_loki_ready_endpoint(self, minikube_ip):
        """Test Loki ready endpoint"""
        url = f"http://{minikube_ip}:30508/ready"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
        except requests.RequestException as e:
            pytest.fail(f"Loki not accessible: {e}")


@pytest.mark.smoke
class TestContainerRegistrySmoke:
    """Container Registry smoke tests"""

    def test_registry_api_accessible(self, minikube_ip):
        """Test container registry API is accessible"""
        url = f"http://{minikube_ip}:30506/v2/"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            # Docker registry v2 API should return {}
        except requests.RequestException as e:
            pytest.fail(f"Container registry not accessible: {e}")

    def test_registry_ui_accessible(self, minikube_ip):
        """Test container registry UI is accessible"""
        url = f"http://{minikube_ip}:30507"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
        except requests.RequestException as e:
            pytest.fail(f"Container registry UI not accessible: {e}")


@pytest.mark.smoke
class TestKubernetesSmoke:
    """Kubernetes infrastructure smoke tests"""

    def test_ml_platform_namespace_exists(self):
        """Test ml-platform namespace exists"""
        result = run(
            ["kubectl", "get", "namespace", "ml-platform"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "ml-platform namespace does not exist"

    def test_airflow_namespace_exists(self):
        """Test airflow namespace exists"""
        result = run(
            ["kubectl", "get", "namespace", "airflow"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "airflow namespace does not exist"

    def test_logging_namespace_exists(self):
        """Test logging namespace exists"""
        result = run(
            ["kubectl", "get", "namespace", "logging"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "logging namespace does not exist"

    def test_all_pods_running(self):
        """Test all pods are in Running or Completed state"""
        result = run(
            ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        import json
        pods_data = json.loads(result.stdout)

        failed_pods = []
        for pod in pods_data["items"]:
            phase = pod["status"]["phase"]
            if phase not in ["Running", "Succeeded", "Completed"]:
                pod_name = pod["metadata"]["name"]
                namespace = pod["metadata"]["namespace"]
                failed_pods.append(f"{namespace}/{pod_name}: {phase}")

        assert len(failed_pods) == 0, f"Pods not in healthy state: {failed_pods}"


# Pytest fixtures
@pytest.fixture(scope="module")
def minikube_ip():
    """Get minikube IP address"""
    result = run(["minikube", "ip"], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("Minikube not running")
    return result.stdout.strip()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "smoke"])
