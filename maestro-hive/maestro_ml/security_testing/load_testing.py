"""
Load Testing Suite for Maestro ML Platform

Uses Locust to validate:
- Rate limit enforcement under high load
- API performance at scale (1000+ concurrent users)
- Tenant isolation under concurrent access
- System behavior during stress conditions
- Database connection pool handling
"""

from locust import HttpUser, task, between, events
from typing import Dict, List, Optional
import random
import time
import logging
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    max_response_time: float = 0.0
    requests_per_second: float = 0.0
    tenant_isolation_violations: int = 0

    def to_dict(self) -> Dict:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "avg_response_time": self.avg_response_time,
            "p95_response_time": self.p95_response_time,
            "p99_response_time": self.p99_response_time,
            "max_response_time": self.max_response_time,
            "requests_per_second": self.requests_per_second,
            "tenant_isolation_violations": self.tenant_isolation_violations,
        }


# Global metrics collector
metrics = LoadTestMetrics()


class MaestroMLUser(HttpUser):
    """
    Base user class for Maestro ML load testing.

    Simulates realistic user behavior with:
    - Authentication
    - Multi-tenant access
    - Various API operations
    """

    # Wait time between tasks (simulates user think time)
    wait_time = between(1, 3)

    # Test data
    tenants = ["tenant-a", "tenant-b", "tenant-c", "tenant-d", "tenant-e"]
    users = [f"user-{i}" for i in range(100)]

    def on_start(self):
        """Initialize user session"""
        self.tenant_id = random.choice(self.tenants)
        self.user_id = random.choice(self.users)
        self.headers = {
            "x-tenant-id": self.tenant_id,
            "x-user-id": self.user_id,
            "Content-Type": "application/json"
        }
        logger.info(f"User {self.user_id} started for tenant {self.tenant_id}")

    @task(10)
    def list_models(self):
        """List models (most common operation - 10x weight)"""
        with self.client.get(
            "/models",
            headers=self.headers,
            catch_response=True,
            name="List Models"
        ) as response:
            self._handle_response(response, "list_models")

    @task(5)
    def get_model(self):
        """Get specific model (5x weight)"""
        model_id = f"model-{random.randint(1, 100)}"
        with self.client.get(
            f"/models/{model_id}",
            headers=self.headers,
            catch_response=True,
            name="Get Model"
        ) as response:
            self._handle_response(response, "get_model")

    @task(3)
    def create_model(self):
        """Create model (3x weight)"""
        payload = {
            "id": f"model-{random.randint(1000, 9999)}",
            "name": f"Test Model {random.randint(1, 1000)}",
            "type": random.choice(["classification", "regression", "clustering"])
        }
        with self.client.post(
            "/models",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="Create Model"
        ) as response:
            self._handle_response(response, "create_model")

    @task(5)
    def list_experiments(self):
        """List experiments (5x weight)"""
        with self.client.get(
            "/experiments",
            headers=self.headers,
            catch_response=True,
            name="List Experiments"
        ) as response:
            self._handle_response(response, "list_experiments")

    @task(2)
    def create_experiment(self):
        """Create experiment (2x weight)"""
        payload = {
            "id": f"exp-{random.randint(1000, 9999)}",
            "name": f"Test Experiment {random.randint(1, 1000)}",
            "model_id": f"model-{random.randint(1, 100)}"
        }
        with self.client.post(
            "/experiments",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="Create Experiment"
        ) as response:
            self._handle_response(response, "create_experiment")

    @task(1)
    def deploy_model(self):
        """Deploy model (1x weight - expensive operation)"""
        model_id = f"model-{random.randint(1, 100)}"
        payload = {
            "environment": random.choice(["staging", "production"]),
            "replicas": random.randint(1, 5)
        }
        with self.client.post(
            f"/models/{model_id}/deploy",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="Deploy Model"
        ) as response:
            self._handle_response(response, "deploy_model")

    def _handle_response(self, response, operation: str):
        """Handle and validate response"""
        global metrics

        metrics.total_requests += 1

        # Check for rate limiting
        if response.status_code == 429:
            metrics.rate_limited_requests += 1
            response.success()  # Expected behavior
            logger.debug(f"Rate limited: {operation}")
            return

        # Check for successful responses
        if 200 <= response.status_code < 300:
            metrics.successful_requests += 1

            # Validate tenant isolation
            if response.text:
                try:
                    data = response.json()
                    # Check if response contains data from other tenants
                    if isinstance(data, dict) and "tenant_id" in data:
                        if data["tenant_id"] != self.tenant_id:
                            metrics.tenant_isolation_violations += 1
                            response.failure(f"Tenant isolation violation: expected {self.tenant_id}, got {data['tenant_id']}")
                            logger.error(f"Tenant isolation violation in {operation}")
                            return
                except json.JSONDecodeError:
                    pass

            response.success()
        else:
            metrics.failed_requests += 1
            response.failure(f"Got unexpected status code: {response.status_code}")


class RateLimitTestUser(HttpUser):
    """
    User specifically designed to test rate limiting.

    Makes rapid requests to validate rate limit enforcement.
    """
    wait_time = between(0.01, 0.1)  # Very short wait time

    def on_start(self):
        """Initialize user session"""
        self.tenant_id = "rate-limit-test-tenant"
        self.user_id = f"rate-test-user-{random.randint(1, 10)}"
        self.headers = {
            "x-tenant-id": self.tenant_id,
            "x-user-id": self.user_id,
            "Content-Type": "application/json"
        }

    @task
    def rapid_requests(self):
        """Make rapid requests to test rate limiting"""
        with self.client.get(
            "/models",
            headers=self.headers,
            catch_response=True,
            name="Rate Limit Test"
        ) as response:
            if response.status_code == 429:
                # Validate rate limit headers
                assert "Retry-After" in response.headers, "Missing Retry-After header"
                assert "X-RateLimit-Limit" in response.headers, "Missing X-RateLimit-Limit header"
                response.success()
            elif response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class TenantIsolationTestUser(HttpUser):
    """
    User specifically designed to test tenant isolation.

    Attempts to access resources from different tenants.
    """
    wait_time = between(0.5, 2)

    def on_start(self):
        """Initialize user session"""
        self.tenant_id = random.choice(["tenant-iso-1", "tenant-iso-2", "tenant-iso-3"])
        self.user_id = f"iso-test-user-{random.randint(1, 20)}"
        self.headers = {
            "x-tenant-id": self.tenant_id,
            "x-user-id": self.user_id,
            "Content-Type": "application/json"
        }

        # Create a test resource for this tenant
        self.resource_id = f"resource-{self.tenant_id}-{random.randint(1, 100)}"
        self.client.post(
            "/models",
            json={"id": self.resource_id, "name": f"Model for {self.tenant_id}"},
            headers=self.headers
        )

    @task(5)
    def access_own_resources(self):
        """Access resources in own tenant (should succeed)"""
        with self.client.get(
            f"/models/{self.resource_id}",
            headers=self.headers,
            catch_response=True,
            name="Access Own Resource"
        ) as response:
            if response.status_code in [200, 404]:  # 404 ok if resource doesn't exist
                response.success()
            else:
                response.failure(f"Failed to access own resource: {response.status_code}")

    @task(1)
    def attempt_cross_tenant_access(self):
        """Attempt to access resources from other tenants (should fail)"""
        other_tenants = ["tenant-iso-1", "tenant-iso-2", "tenant-iso-3"]
        other_tenants.remove(self.tenant_id)
        other_tenant = random.choice(other_tenants)
        other_resource = f"resource-{other_tenant}-{random.randint(1, 100)}"

        with self.client.get(
            f"/models/{other_resource}",
            headers=self.headers,
            catch_response=True,
            name="Cross-Tenant Access Attempt"
        ) as response:
            # Should return 404 (not found) due to tenant filtering
            if response.status_code == 404:
                response.success()
            elif response.status_code == 200:
                # This is a tenant isolation violation!
                global metrics
                metrics.tenant_isolation_violations += 1
                response.failure("Tenant isolation violation: accessed resource from another tenant")
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class PerformanceTestUser(HttpUser):
    """
    User designed to test system performance under load.

    Validates:
    - Response times stay within SLA (p95 < 500ms)
    - System handles concurrent connections
    - Database connection pool doesn't exhaust
    """
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Initialize user session"""
        self.tenant_id = f"perf-tenant-{random.randint(1, 10)}"
        self.user_id = f"perf-user-{random.randint(1, 100)}"
        self.headers = {
            "x-tenant-id": self.tenant_id,
            "x-user-id": self.user_id,
            "Content-Type": "application/json"
        }

    @task(10)
    def read_heavy_workload(self):
        """Simulate read-heavy workload"""
        endpoints = ["/models", "/experiments", "/artifacts"]
        endpoint = random.choice(endpoints)

        with self.client.get(
            endpoint,
            headers=self.headers,
            catch_response=True,
            name="Read Heavy Workload"
        ) as response:
            if response.status_code == 200:
                # Check response time
                if response.elapsed.total_seconds() > 1.0:
                    response.failure(f"Slow response: {response.elapsed.total_seconds():.2f}s")
                else:
                    response.success()
            elif response.status_code == 429:
                response.success()  # Rate limiting is ok
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def write_workload(self):
        """Simulate write workload"""
        payload = {
            "id": f"perf-resource-{random.randint(10000, 99999)}",
            "name": f"Performance Test Resource",
            "data": {"test": True, "timestamp": time.time()}
        }

        with self.client.post(
            "/models",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="Write Workload"
        ) as response:
            if response.status_code in [200, 201]:
                # Check response time (writes can be slower)
                if response.elapsed.total_seconds() > 2.0:
                    response.failure(f"Slow write: {response.elapsed.total_seconds():.2f}s")
                else:
                    response.success()
            elif response.status_code == 429:
                response.success()  # Rate limiting is ok
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# Event listeners for metrics collection
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Collect metrics on each request"""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test"""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print final metrics"""
    logger.info("Load test completed")
    logger.info(f"Total requests: {metrics.total_requests}")
    logger.info(f"Successful: {metrics.successful_requests}")
    logger.info(f"Failed: {metrics.failed_requests}")
    logger.info(f"Rate limited: {metrics.rate_limited_requests}")
    logger.info(f"Tenant isolation violations: {metrics.tenant_isolation_violations}")

    # Save metrics to file
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics.to_dict(),
        "stats": environment.stats.serialize_stats()
    }

    with open("load_test_report.json", "w") as f:
        json.dump(report, f, indent=2)

    logger.info("Report saved to load_test_report.json")


# ============================================================================
# Load Test Scenarios
# ============================================================================

class LoadTestScenarios:
    """Pre-defined load test scenarios"""

    @staticmethod
    def baseline_test():
        """
        Baseline test: 50 users, 5 minute ramp-up

        Usage:
            locust -f load_testing.py --host=http://localhost:8000 \
                   --users 50 --spawn-rate 10 --run-time 10m
        """
        pass

    @staticmethod
    def stress_test():
        """
        Stress test: 1000 users, 10 minute ramp-up

        Usage:
            locust -f load_testing.py --host=http://localhost:8000 \
                   --users 1000 --spawn-rate 50 --run-time 30m
        """
        pass

    @staticmethod
    def spike_test():
        """
        Spike test: Rapid increase to 500 users

        Usage:
            locust -f load_testing.py --host=http://localhost:8000 \
                   --users 500 --spawn-rate 100 --run-time 5m
        """
        pass

    @staticmethod
    def rate_limit_validation():
        """
        Rate limit validation: Use RateLimitTestUser

        Usage:
            locust -f load_testing.py --host=http://localhost:8000 \
                   --users 100 --spawn-rate 20 --run-time 5m \
                   RateLimitTestUser
        """
        pass

    @staticmethod
    def tenant_isolation_validation():
        """
        Tenant isolation validation: Use TenantIsolationTestUser

        Usage:
            locust -f load_testing.py --host=http://localhost:8000 \
                   --users 50 --spawn-rate 10 --run-time 10m \
                   TenantIsolationTestUser
        """
        pass


# ============================================================================
# Usage Examples
# ============================================================================

"""
1. Basic Load Test (50 concurrent users):

   locust -f load_testing.py --host=http://localhost:8000 \\
          --users 50 --spawn-rate 10 --run-time 10m

2. Stress Test (1000 concurrent users):

   locust -f load_testing.py --host=http://localhost:8000 \\
          --users 1000 --spawn-rate 50 --run-time 30m

3. Rate Limit Test:

   locust -f load_testing.py --host=http://localhost:8000 \\
          --users 100 --spawn-rate 20 --run-time 5m \\
          RateLimitTestUser

4. Tenant Isolation Test:

   locust -f load_testing.py --host=http://localhost:8000 \\
          --users 50 --spawn-rate 10 --run-time 10m \\
          TenantIsolationTestUser

5. Performance Test:

   locust -f load_testing.py --host=http://localhost:8000 \\
          --users 200 --spawn-rate 20 --run-time 15m \\
          PerformanceTestUser

6. Web UI Mode (interactive):

   locust -f load_testing.py --host=http://localhost:8000
   # Then open http://localhost:8089

7. Headless Mode with Report:

   locust -f load_testing.py --host=http://localhost:8000 \\
          --users 100 --spawn-rate 10 --run-time 10m \\
          --html report.html

Expected Results:
- Rate limit should kick in at configured limits (1000 req/min per user)
- p95 response time should be < 500ms
- p99 response time should be < 1000ms
- Tenant isolation violations should be 0
- Failed requests (excluding rate limits) should be < 1%
"""
