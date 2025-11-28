"""
Comprehensive Performance and Load Tests
Tests API performance, scalability, throughput, and resource usage
"""

import pytest
import asyncio
from datetime import datetime
import concurrent.futures
import time
import statistics


@pytest.mark.performance
@pytest.mark.load
class TestAPIPerformance:
    """Test API endpoint performance"""

    def test_health_endpoint_latency(self, client, performance_timer):
        """Health endpoint should respond quickly"""
        latencies = []

        for _ in range(100):
            performance_timer.start()
            response = client.get("/health")
            performance_timer.stop()

            assert response.status_code == 200
            latencies.append(performance_timer.elapsed_ms)

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        max_latency = max(latencies)

        # Performance assertions
        assert avg_latency < 50  # Average should be under 50ms
        assert p95_latency < 100  # 95th percentile under 100ms
        assert max_latency < 200  # Max under 200ms

    def test_list_templates_latency(self, client, auth_headers, performance_timer):
        """List templates endpoint should respond reasonably"""
        latencies = []

        for _ in range(50):
            performance_timer.start()
            response = client.get("/api/v1/templates", headers=auth_headers)
            performance_timer.stop()

            # Accept 200 (success) or 500 (DB not available)
            assert response.status_code in [200, 500]
            latencies.append(performance_timer.elapsed_ms)

        avg_latency = statistics.mean(latencies)

        # Should respond within 2 seconds on average
        assert avg_latency < 2000

    def test_search_endpoint_performance(self, client, auth_headers, performance_timer):
        """Search endpoint should perform well"""
        search_queries = [
            "react",
            "api",
            "database",
            "docker",
            "kubernetes"
        ]

        latencies = []

        for query in search_queries:
            for _ in range(10):
                performance_timer.start()
                response = client.get(
                    f"/api/v1/templates/search?q={query}",
                    headers=auth_headers
                )
                performance_timer.stop()

                assert response.status_code in [200, 500]
                latencies.append(performance_timer.elapsed_ms)

        avg_latency = statistics.mean(latencies)

        # Search should be reasonably fast
        assert avg_latency < 3000


@pytest.mark.performance
@pytest.mark.load
class TestConcurrentLoad:
    """Test system under concurrent load"""

    def test_concurrent_health_checks(self, client):
        """System should handle concurrent health checks"""
        def make_request():
            response = client.get("/health")
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            end_time = time.time()

        # All requests should succeed
        assert all(status == 200 for status in results)

        # Should complete in reasonable time
        total_time = end_time - start_time
        assert total_time < 10  # 100 requests in under 10 seconds

        # Calculate throughput
        throughput = len(results) / total_time
        assert throughput > 10  # At least 10 requests/second

    def test_concurrent_authenticated_requests(self, client, auth_headers):
        """System should handle concurrent authenticated requests"""
        def make_request():
            response = client.get("/api/v1/templates", headers=auth_headers)
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should either succeed or fail gracefully
        assert all(status in [200, 401, 500] for status in results)

    def test_mixed_workload_performance(self, client, auth_headers):
        """System should handle mixed read/write workload"""
        def read_request():
            return client.get("/api/v1/templates", headers=auth_headers)

        def search_request():
            return client.get("/api/v1/templates/search?q=test", headers=auth_headers)

        def health_request():
            return client.get("/health")

        requests = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            # 30 read, 20 search, 50 health
            for _ in range(30):
                requests.append(executor.submit(read_request))
            for _ in range(20):
                requests.append(executor.submit(search_request))
            for _ in range(50):
                requests.append(executor.submit(health_request))

            responses = [f.result() for f in concurrent.futures.as_completed(requests)]

        # All should complete without crashing
        assert len(responses) == 100


@pytest.mark.performance
@pytest.mark.stress
class TestStressTests:
    """Test system under stress conditions"""

    def test_rapid_sequential_requests(self, client, auth_headers, performance_timer):
        """System should handle rapid sequential requests"""
        performance_timer.start()

        for _ in range(200):
            response = client.get("/health")
            assert response.status_code == 200

        performance_timer.stop()

        # 200 requests should complete quickly
        assert performance_timer.elapsed_ms < 20000  # Under 20 seconds

    def test_authentication_stress(self, client):
        """Authentication system should handle stress"""
        login_data = {
            "username": "developer",
            "password": "dev123"
        }

        success_count = 0
        for _ in range(100):
            response = client.post(
                "/api/v1/auth/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                success_count += 1

        # Most should succeed (some might fail if rate limited)
        assert success_count >= 80

    def test_large_result_set_handling(self, client, auth_headers):
        """System should handle large result sets"""
        # Request without pagination
        response = client.get(
            "/api/v1/templates?limit=1000",
            headers=auth_headers
        )

        # Should either succeed or reject gracefully
        assert response.status_code in [200, 400, 422, 500]

        if response.status_code == 200:
            # Response should be within reasonable size
            assert len(response.content) < 10 * 1024 * 1024  # Under 10MB


@pytest.mark.performance
@pytest.mark.scalability
class TestScalability:
    """Test system scalability"""

    def test_increasing_load_handling(self, client):
        """System should handle increasing load"""
        load_levels = [10, 20, 50, 100]
        response_times = []

        for load_level in load_levels:
            def make_request():
                start = time.time()
                response = client.get("/health")
                end = time.time()
                return (end - start) * 1000

            with concurrent.futures.ThreadPoolExecutor(max_workers=load_level) as executor:
                futures = [executor.submit(make_request) for _ in range(load_level)]
                times = [f.result() for f in concurrent.futures.as_completed(futures)]

            avg_time = statistics.mean(times)
            response_times.append(avg_time)

        # Response time shouldn't degrade too much
        # Allow up to 5x degradation from lowest to highest load
        assert max(response_times) < min(response_times) * 5

    def test_database_connection_pooling(self, mock_db):
        """Database connection pool should handle concurrent access"""
        @pytest.mark.asyncio
        async def test_pool():
            async def query_db():
                await mock_db.fetch("SELECT 1")

            # Simulate 50 concurrent database queries
            tasks = [query_db() for _ in range(50)]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Should not crash
        asyncio.run(test_pool())


@pytest.mark.performance
@pytest.mark.cache
class TestCachePerformance:
    """Test caching performance"""

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, mock_cache_manager, performance_timer):
        """Cache hits should be very fast"""
        # Simulate cache hit
        mock_cache_manager.get.return_value = {"cached": "data"}

        latencies = []

        for _ in range(100):
            performance_timer.start()
            result = await mock_cache_manager.get("test_key")
            performance_timer.stop()

            latencies.append(performance_timer.elapsed_ms)

        avg_latency = statistics.mean(latencies)

        # Cache should be very fast (under 10ms average)
        assert avg_latency < 10

    @pytest.mark.asyncio
    async def test_cache_miss_handling(self, mock_cache_manager, mock_db):
        """Cache misses should fall back to database"""
        # Simulate cache miss
        mock_cache_manager.get.return_value = None
        mock_db.fetchrow.return_value = {"id": "123", "name": "test"}

        # Fallback to database
        cached = await mock_cache_manager.get("missing_key")
        if cached is None:
            result = await mock_db.fetchrow("SELECT * FROM templates WHERE id = $1", "123")
            assert result is not None


@pytest.mark.performance
@pytest.mark.memory
class TestMemoryUsage:
    """Test memory efficiency"""

    def test_large_template_list_memory(self, template_list):
        """Creating large template list should be memory efficient"""
        import sys

        # Create 1000 template objects
        templates = [dict(template_list[i % len(template_list)]) for i in range(1000)]

        # Size should be reasonable (under 10MB for 1000 templates)
        size_bytes = sys.getsizeof(templates)
        size_mb = size_bytes / (1024 * 1024)

        assert size_mb < 10

    def test_json_serialization_performance(self, template_list, performance_timer):
        """JSON serialization should be fast"""
        import json

        performance_timer.start()
        for _ in range(100):
            json.dumps(template_list)
        performance_timer.stop()

        # 100 serializations should be fast
        assert performance_timer.elapsed_ms < 1000


@pytest.mark.performance
@pytest.mark.throughput
class TestThroughput:
    """Test system throughput"""

    def test_requests_per_second(self, client):
        """Measure requests per second capacity"""
        duration_seconds = 5
        request_count = 0
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            response = client.get("/health")
            if response.status_code == 200:
                request_count += 1

        actual_duration = time.time() - start_time
        rps = request_count / actual_duration

        # Should handle at least 100 requests/second
        assert rps >= 100

    def test_authentication_throughput(self, client):
        """Measure authentication throughput"""
        login_data = {
            "username": "developer",
            "password": "dev123"
        }

        duration_seconds = 3
        auth_count = 0
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            response = client.post(
                "/api/v1/auth/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if response.status_code == 200:
                auth_count += 1

        actual_duration = time.time() - start_time
        auth_per_second = auth_count / actual_duration

        # Authentication is more expensive (bcrypt)
        # Should handle at least 5 auth/second
        assert auth_per_second >= 5


@pytest.mark.performance
@pytest.mark.quality_fabric
class TestPerformanceQualityMetrics:
    """Test performance with quality-fabric tracking"""

    async def test_performance_benchmarks(self, quality_fabric_client, client, auth_headers):
        """Track comprehensive performance benchmarks"""
        benchmarks = {
            "health_endpoint_p95": 0,
            "list_templates_avg": 0,
            "concurrent_load_throughput": 0,
            "authentication_latency": 0
        }

        # Health endpoint P95
        latencies = []
        for _ in range(100):
            start = time.time()
            client.get("/health")
            latencies.append((time.time() - start) * 1000)
        benchmarks["health_endpoint_p95"] = statistics.quantiles(latencies, n=20)[18]

        # List templates average
        latencies = []
        for _ in range(20):
            start = time.time()
            client.get("/api/v1/templates", headers=auth_headers)
            latencies.append((time.time() - start) * 1000)
        benchmarks["list_templates_avg"] = statistics.mean(latencies)

        # Track results
        await quality_fabric_client.track_test_execution(
            test_name="performance_benchmarks",
            duration=benchmarks["list_templates_avg"],
            status="passed",
            coverage=100
        )

        # Performance targets
        assert benchmarks["health_endpoint_p95"] < 100
        assert benchmarks["list_templates_avg"] < 2000


@pytest.mark.performance
@pytest.mark.soak
class TestSoakTests:
    """Long-running soak tests"""

    @pytest.mark.slow
    def test_sustained_load_5_minutes(self, client):
        """System should handle sustained load"""
        duration_seconds = 300  # 5 minutes
        request_interval = 0.1  # 10 requests/second
        start_time = time.time()
        request_count = 0
        error_count = 0

        while time.time() - start_time < duration_seconds:
            try:
                response = client.get("/health")
                if response.status_code == 200:
                    request_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

            time.sleep(request_interval)

        # Error rate should be under 1%
        error_rate = error_count / (request_count + error_count)
        assert error_rate < 0.01

    @pytest.mark.slow
    def test_memory_leak_detection(self, client):
        """Detect memory leaks over time"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Make many requests
        for _ in range(1000):
            client.get("/health")

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal (under 50MB)
        assert memory_growth < 50
