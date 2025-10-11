"""
Automated Test Suite for Health Check API Endpoint

This module contains automated tests for the /health endpoint
using pytest framework.

Test Coverage:
- HTTP status code validation
- JSON response structure
- Field presence and values
- Response time performance
- HTTP method validation
- Concurrent request handling

Requirements:
- pytest
- requests
- pytest-timeout

Usage:
    pytest test_automation.py -v
"""

import pytest
import requests
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configuration
BASE_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{BASE_URL}/health"
RESPONSE_TIME_THRESHOLD_MS = 200


class TestHealthEndpointFunctional:
    """Functional tests for /health endpoint"""

    def test_tc001_health_endpoint_returns_200(self):
        """TC001: Verify Health Endpoint Returns 200 Status Code"""
        response = requests.get(HEALTH_ENDPOINT)
        assert response.status_code == 200, \
            f"Expected status code 200, got {response.status_code}"

    def test_tc002_response_is_valid_json(self):
        """TC002: Verify Health Endpoint Returns Valid JSON Response"""
        response = requests.get(HEALTH_ENDPOINT)

        # Verify Content-Type header
        content_type = response.headers.get('Content-Type', '')
        assert 'application/json' in content_type.lower(), \
            f"Expected Content-Type to contain 'application/json', got '{content_type}'"

        # Verify JSON can be parsed
        try:
            json_data = response.json()
            assert isinstance(json_data, dict), \
                "Response should be a JSON object (dictionary)"
        except json.JSONDecodeError as e:
            pytest.fail(f"Response is not valid JSON: {e}")

    def test_tc003_response_contains_required_fields(self):
        """TC003: Verify Response Contains Required Fields"""
        response = requests.get(HEALTH_ENDPOINT)
        json_data = response.json()

        # Check required fields are present
        assert 'status' in json_data, "Response missing 'status' field"
        assert 'timestamp' in json_data, "Response missing 'timestamp' field"

        # Verify only expected fields are present
        expected_fields = {'status', 'timestamp'}
        actual_fields = set(json_data.keys())
        assert actual_fields == expected_fields, \
            f"Unexpected fields in response. Expected: {expected_fields}, Got: {actual_fields}"

    def test_tc004_status_field_value(self):
        """TC004: Verify Status Field Value"""
        response = requests.get(HEALTH_ENDPOINT)
        json_data = response.json()

        assert json_data['status'] == 'ok', \
            f"Expected status value 'ok', got '{json_data['status']}'"

    def test_tc005_timestamp_field_format(self):
        """TC005: Verify Timestamp Field Format"""
        response = requests.get(HEALTH_ENDPOINT)
        json_data = response.json()

        timestamp_value = json_data['timestamp']

        # Verify timestamp is a string
        assert isinstance(timestamp_value, str), \
            f"Timestamp should be a string, got {type(timestamp_value)}"

        # Verify timestamp is not empty
        assert len(timestamp_value) > 0, "Timestamp should not be empty"

        # Try to parse as ISO 8601 format (most common)
        # This accepts various formats: 2025-10-09T12:34:56.123456, etc.
        valid_format = False
        error_messages = []

        # Try ISO 8601 format
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ]:
            try:
                datetime.strptime(timestamp_value, fmt)
                valid_format = True
                break
            except ValueError as e:
                error_messages.append(str(e))

        assert valid_format, \
            f"Timestamp '{timestamp_value}' is not in a recognized format. Errors: {error_messages}"

    def test_tc011_content_type_header(self):
        """TC011: Verify Content-Type Header"""
        response = requests.get(HEALTH_ENDPOINT)
        content_type = response.headers.get('Content-Type', '')

        assert 'application/json' in content_type.lower(), \
            f"Expected Content-Type to contain 'application/json', got '{content_type}'"


class TestHealthEndpointNegative:
    """Negative tests for /health endpoint"""

    def test_tc007_post_method_not_allowed(self):
        """TC007: Verify POST Method Not Allowed"""
        response = requests.post(HEALTH_ENDPOINT)

        # FastAPI returns 405 for method not allowed
        assert response.status_code in [404, 405], \
            f"Expected status code 404 or 405 for POST, got {response.status_code}"

    def test_tc008_put_method_not_allowed(self):
        """TC008: Verify PUT Method Not Allowed"""
        response = requests.put(HEALTH_ENDPOINT)

        # FastAPI returns 405 for method not allowed
        assert response.status_code in [404, 405], \
            f"Expected status code 404 or 405 for PUT, got {response.status_code}"

    def test_tc009_delete_method_not_allowed(self):
        """TC009: Verify DELETE Method Not Allowed"""
        response = requests.delete(HEALTH_ENDPOINT)

        # FastAPI returns 405 for method not allowed
        assert response.status_code in [404, 405], \
            f"Expected status code 404 or 405 for DELETE, got {response.status_code}"


class TestHealthEndpointPerformance:
    """Performance tests for /health endpoint"""

    @pytest.mark.timeout(5)
    def test_tc006_response_time_performance(self):
        """TC006: Verify Response Time Performance"""
        start_time = time.time()
        response = requests.get(HEALTH_ENDPOINT, timeout=1)
        end_time = time.time()

        response_time_ms = (end_time - start_time) * 1000

        assert response.status_code == 200, "Request failed"
        assert response_time_ms < RESPONSE_TIME_THRESHOLD_MS, \
            f"Response time {response_time_ms:.2f}ms exceeds threshold {RESPONSE_TIME_THRESHOLD_MS}ms"

    @pytest.mark.timeout(10)
    def test_tc010_multiple_concurrent_requests(self):
        """TC010: Verify Multiple Concurrent Requests"""
        num_requests = 10

        def make_request(request_id):
            """Make a single request and return results"""
            try:
                response = requests.get(HEALTH_ENDPOINT, timeout=5)
                return {
                    'id': request_id,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'json_valid': True,
                    'data': response.json()
                }
            except Exception as e:
                return {
                    'id': request_id,
                    'status_code': None,
                    'success': False,
                    'json_valid': False,
                    'error': str(e)
                }

        # Execute concurrent requests
        results = []
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            for future in as_completed(futures):
                results.append(future.result())

        # Verify all requests succeeded
        successful_requests = [r for r in results if r['success']]

        assert len(successful_requests) == num_requests, \
            f"Only {len(successful_requests)}/{num_requests} requests succeeded"

        # Verify all responses have correct structure
        for result in successful_requests:
            data = result['data']
            assert 'status' in data, f"Request {result['id']}: missing 'status' field"
            assert 'timestamp' in data, f"Request {result['id']}: missing 'timestamp' field"
            assert data['status'] == 'ok', f"Request {result['id']}: incorrect status value"


class TestHealthEndpointEdgeCases:
    """Edge case tests for /health endpoint"""

    def test_tc012_endpoint_with_trailing_slash(self):
        """TC012: Verify Endpoint with Trailing Slash"""
        response = requests.get(f"{HEALTH_ENDPOINT}/", allow_redirects=True)

        # Should either work directly or redirect
        assert response.status_code in [200, 307, 308], \
            f"Expected status code 200, 307, or 308, got {response.status_code}"

        # If successful, verify response structure
        if response.status_code == 200:
            json_data = response.json()
            assert 'status' in json_data, "Response missing 'status' field"
            assert 'timestamp' in json_data, "Response missing 'timestamp' field"


# Test execution summary fixture
@pytest.fixture(scope="session", autouse=True)
def test_session_info(request):
    """Print test session information"""
    print("\n" + "="*70)
    print("Health Check API - Automated Test Suite")
    print(f"Target URL: {BASE_URL}")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    yield

    print("\n" + "="*70)
    print("Test Execution Complete")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
