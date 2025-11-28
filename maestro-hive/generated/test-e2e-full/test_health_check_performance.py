"""
Performance Tests for Health Check API

Load testing, stress testing, and performance benchmarks.

Author: Rachel - QA Engineer
Date: 2025-11-22
"""

import json
import time
import unittest
import threading
import statistics
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from health_check_api import create_server


class TestHealthCheckPerformance(unittest.TestCase):
    """Performance and load tests for the Health Check API."""

    @classmethod
    def setUpClass(cls):
        """Start the test server."""
        cls.host = "127.0.0.1"
        cls.server = create_server(cls.host, 0)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://{cls.host}:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _timed_request(self, path: str):
        """Make request and return response time in ms."""
        url = f"{self.base_url}{path}"
        start = time.perf_counter()

        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                _ = response.read()
                elapsed = (time.perf_counter() - start) * 1000
                return {"success": True, "time_ms": elapsed, "status": response.status}
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return {"success": False, "time_ms": elapsed, "error": str(e)}

    # ==================== Response Time Tests ====================

    def test_health_response_time(self):
        """Test /health responds within acceptable time."""
        result = self._timed_request("/health")

        self.assertTrue(result["success"])
        # Should respond within 100ms
        self.assertLess(result["time_ms"], 100,
            f"Response time {result['time_ms']:.2f}ms exceeds 100ms threshold")

    def test_liveness_response_time(self):
        """Test /health/live responds quickly (minimal endpoint)."""
        result = self._timed_request("/health/live")

        self.assertTrue(result["success"])
        # Liveness should be fastest - under 50ms
        self.assertLess(result["time_ms"], 50,
            f"Response time {result['time_ms']:.2f}ms exceeds 50ms threshold")

    def test_readiness_response_time(self):
        """Test /health/ready responds within acceptable time."""
        result = self._timed_request("/health/ready")

        self.assertTrue(result["success"])
        self.assertLess(result["time_ms"], 100,
            f"Response time {result['time_ms']:.2f}ms exceeds 100ms threshold")

    # ==================== Load Tests ====================

    def test_sequential_load(self):
        """Test sequential request performance (100 requests)."""
        num_requests = 100
        times = []
        failures = 0

        for _ in range(num_requests):
            result = self._timed_request("/health")
            if result["success"]:
                times.append(result["time_ms"])
            else:
                failures += 1

        # Calculate statistics
        if times:
            avg_time = statistics.mean(times)
            p95_time = sorted(times)[int(len(times) * 0.95)]
            max_time = max(times)

            # Assertions
            self.assertEqual(failures, 0, f"{failures} requests failed")
            self.assertLess(avg_time, 50, f"Average time {avg_time:.2f}ms exceeds 50ms")
            self.assertLess(p95_time, 100, f"P95 time {p95_time:.2f}ms exceeds 100ms")

            print(f"\nSequential Load Test Results:")
            print(f"  Requests: {num_requests}")
            print(f"  Avg: {avg_time:.2f}ms")
            print(f"  P95: {p95_time:.2f}ms")
            print(f"  Max: {max_time:.2f}ms")

    def test_concurrent_load(self):
        """Test concurrent request handling (50 concurrent requests)."""
        num_requests = 50
        results = []

        def make_request():
            return self._timed_request("/health")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]

        # Analyze results
        successful = [r for r in results if r["success"]]
        times = [r["time_ms"] for r in successful]

        success_rate = len(successful) / num_requests * 100
        avg_time = statistics.mean(times) if times else 0
        p95_time = sorted(times)[int(len(times) * 0.95)] if times else 0

        # Assertions
        self.assertGreaterEqual(success_rate, 95,
            f"Success rate {success_rate:.1f}% below 95%")
        self.assertLess(avg_time, 200,
            f"Average time {avg_time:.2f}ms exceeds 200ms under load")

        print(f"\nConcurrent Load Test Results:")
        print(f"  Concurrent: 10 threads")
        print(f"  Requests: {num_requests}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Avg: {avg_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")

    def test_sustained_load(self):
        """Test sustained load over time (5 seconds)."""
        duration_seconds = 5
        results = []
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            result = self._timed_request("/health/live")
            results.append(result)

        # Analyze
        successful = [r for r in results if r["success"]]
        times = [r["time_ms"] for r in successful]

        total_requests = len(results)
        requests_per_second = total_requests / duration_seconds
        success_rate = len(successful) / total_requests * 100

        # Assertions
        self.assertGreater(requests_per_second, 50,
            f"Throughput {requests_per_second:.1f} req/s below 50 req/s")
        self.assertGreaterEqual(success_rate, 99,
            f"Success rate {success_rate:.1f}% below 99%")

        print(f"\nSustained Load Test Results:")
        print(f"  Duration: {duration_seconds}s")
        print(f"  Total Requests: {total_requests}")
        print(f"  Throughput: {requests_per_second:.1f} req/s")
        print(f"  Success Rate: {success_rate:.1f}%")
        if times:
            print(f"  Avg Response: {statistics.mean(times):.2f}ms")

    # ==================== Stress Tests ====================

    def test_burst_traffic(self):
        """Test handling of sudden traffic burst."""
        burst_size = 100
        results = []

        def make_request():
            return self._timed_request("/health/live")

        # Send burst
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(burst_size)]
            results = [f.result() for f in as_completed(futures)]

        successful = len([r for r in results if r["success"]])
        success_rate = successful / burst_size * 100

        self.assertGreaterEqual(success_rate, 90,
            f"Burst success rate {success_rate:.1f}% below 90%")

        print(f"\nBurst Traffic Test Results:")
        print(f"  Burst Size: {burst_size}")
        print(f"  Workers: 20")
        print(f"  Success Rate: {success_rate:.1f}%")

    def test_mixed_endpoint_load(self):
        """Test load across all endpoints."""
        endpoints = ["/health", "/health/live", "/health/ready"]
        num_per_endpoint = 30
        results = {ep: [] for ep in endpoints}

        for endpoint in endpoints:
            for _ in range(num_per_endpoint):
                result = self._timed_request(endpoint)
                results[endpoint].append(result)

        # Analyze per endpoint
        print(f"\nMixed Endpoint Load Test Results:")
        for endpoint in endpoints:
            successful = [r for r in results[endpoint] if r["success"]]
            times = [r["time_ms"] for r in successful]
            success_rate = len(successful) / num_per_endpoint * 100
            avg_time = statistics.mean(times) if times else 0

            print(f"  {endpoint}:")
            print(f"    Success Rate: {success_rate:.1f}%")
            print(f"    Avg Response: {avg_time:.2f}ms")

            self.assertGreaterEqual(success_rate, 95)


class TestHealthCheckMemoryStability(unittest.TestCase):
    """Memory stability tests for the Health Check API."""

    @classmethod
    def setUpClass(cls):
        cls.host = "127.0.0.1"
        cls.server = create_server(cls.host, 0)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://{cls.host}:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_memory_stability_under_load(self):
        """Test memory doesn't grow excessively under load."""
        url = f"{self.base_url}/health"

        # Get initial memory from health check
        with urllib.request.urlopen(url) as response:
            initial_data = json.loads(response.read())
            initial_mem = initial_data["checks"]["memory"].get("max_rss_mb", 0)

        # Make many requests
        for _ in range(500):
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    _ = response.read()
            except Exception:
                pass

        # Check final memory
        with urllib.request.urlopen(url) as response:
            final_data = json.loads(response.read())
            final_mem = final_data["checks"]["memory"].get("max_rss_mb", 0)

        if initial_mem > 0 and final_mem > 0:
            mem_growth = final_mem - initial_mem
            growth_percent = (mem_growth / initial_mem) * 100 if initial_mem > 0 else 0

            print(f"\nMemory Stability Test:")
            print(f"  Initial: {initial_mem:.2f}MB")
            print(f"  Final: {final_mem:.2f}MB")
            print(f"  Growth: {mem_growth:.2f}MB ({growth_percent:.1f}%)")

            # Memory shouldn't grow more than 50%
            self.assertLess(growth_percent, 50,
                f"Memory grew {growth_percent:.1f}% which exceeds 50% threshold")


if __name__ == "__main__":
    # Run with verbosity for performance output
    unittest.main(verbosity=2)
