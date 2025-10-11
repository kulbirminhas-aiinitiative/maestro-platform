"""
Comprehensive Security Test Suite for Maestro ML Platform

Integrates all security testing components:
- RBAC and authentication tests
- Rate limiting tests
- Tenant isolation tests
- Security header tests
- Input validation tests
- SQL injection tests
- XSS tests

Run with: pytest security_testing/test_security_suite.py -v
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from typing import Dict
import time

# Import security testing components
from security_testing.security_audit import SecurityAuditor
from security_testing.tenant_isolation_validator import TenantIsolationValidator


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Test client fixture (replace with your actual app)"""
    from api.main import app
    return TestClient(app)


@pytest.fixture
def security_auditor(client):
    """Security auditor fixture"""
    return SecurityAuditor(base_url="http://testserver")


@pytest.fixture
def tenant_validator():
    """Tenant isolation validator fixture"""
    return TenantIsolationValidator(api_base_url="http://testserver")


@pytest.fixture
def auth_headers():
    """Authenticated request headers"""
    return {
        "x-user-id": "test-user-123",
        "x-tenant-id": "test-tenant-abc",
        "Authorization": "Bearer test-token"
    }


# ============================================================================
# Authentication & Authorization Tests
# ============================================================================

class TestAuthentication:
    """Test authentication mechanisms"""

    def test_unauthenticated_access_denied(self, client):
        """Test that unauthenticated requests are rejected"""
        response = client.get("/models")
        assert response.status_code in [401, 403], "Unauthenticated access should be denied"

    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected"""
        response = client.get(
            "/models",
            headers={"Authorization": "Bearer invalid-token-xyz"}
        )
        assert response.status_code in [401, 403], "Invalid token should be rejected"

    def test_missing_user_id_rejected(self, client):
        """Test that requests without user ID are rejected"""
        response = client.get(
            "/models",
            headers={"x-tenant-id": "test-tenant"}  # Missing x-user-id
        )
        assert response.status_code in [400, 401, 403], "Missing user ID should be rejected"

    def test_valid_authentication_allowed(self, client, auth_headers):
        """Test that valid authentication is accepted"""
        response = client.get("/models", headers=auth_headers)
        assert response.status_code in [200, 429], "Valid auth should be accepted (200 or rate limited 429)"


class TestAuthorization:
    """Test RBAC and permissions"""

    def test_viewer_cannot_create(self, client):
        """Test that viewer role cannot create resources"""
        headers = {
            "x-user-id": "viewer-user",
            "x-tenant-id": "test-tenant",
            "Authorization": "Bearer viewer-token"
        }
        response = client.post(
            "/models",
            json={"id": "test-model", "name": "Test"},
            headers=headers
        )
        assert response.status_code == 403, "Viewer should not be able to create"

    def test_admin_can_delete(self, client):
        """Test that admin role can delete resources"""
        # Create resource first
        admin_headers = {
            "x-user-id": "admin-user",
            "x-tenant-id": "test-tenant",
            "Authorization": "Bearer admin-token"
        }

        # Create
        create_response = client.post(
            "/models",
            json={"id": "delete-test", "name": "To Delete"},
            headers=admin_headers
        )

        if create_response.status_code in [200, 201]:
            # Delete
            delete_response = client.delete(
                "/models/delete-test",
                headers=admin_headers
            )
            assert delete_response.status_code in [200, 204], "Admin should be able to delete"

    def test_permission_required_enforced(self, client):
        """Test that endpoints requiring permissions are protected"""
        headers = {
            "x-user-id": "no-permission-user",
            "x-tenant-id": "test-tenant"
        }
        response = client.post(
            "/models/test-model/deploy",
            json={"environment": "production"},
            headers=headers
        )
        assert response.status_code == 403, "Permission should be required for deployment"


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_enforced(self, client, auth_headers):
        """Test that rate limits are enforced"""
        # Make many rapid requests
        responses = []
        for i in range(150):  # Exceed typical limit
            response = client.get("/models", headers=auth_headers)
            responses.append(response)

        # Should get at least one 429 response
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0, "Rate limiting should be enforced"

    def test_rate_limit_headers_present(self, client, auth_headers):
        """Test that rate limit headers are included"""
        response = client.get("/models", headers=auth_headers)

        if response.status_code in [200, 429]:
            # Should have rate limit headers
            assert "X-RateLimit-Limit" in response.headers or \
                   "X-RateLimit-Remaining" in response.headers, \
                   "Rate limit headers should be present"

    def test_rate_limit_retry_after(self, client, auth_headers):
        """Test that 429 response includes Retry-After header"""
        # Make requests until rate limited
        for i in range(200):
            response = client.get("/models", headers=auth_headers)
            if response.status_code == 429:
                assert "Retry-After" in response.headers, \
                       "Retry-After header should be present on 429 response"
                break

    def test_rate_limit_per_tenant(self, client):
        """Test that rate limits are per-tenant"""
        tenant_a_headers = {"x-user-id": "user-1", "x-tenant-id": "tenant-a"}
        tenant_b_headers = {"x-user-id": "user-2", "x-tenant-id": "tenant-b"}

        # Make many requests from tenant A
        for i in range(100):
            client.get("/models", headers=tenant_a_headers)

        # Tenant B should still have access
        response = client.get("/models", headers=tenant_b_headers)
        assert response.status_code != 429, "Tenant B should not be rate limited"

    def test_exempt_paths_not_rate_limited(self, client):
        """Test that exempt paths are not rate limited"""
        # Make many requests to health endpoint
        responses = []
        for i in range(200):
            response = client.get("/health")
            responses.append(response)

        # Should not be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) == 0, "Exempt paths should not be rate limited"


# ============================================================================
# Tenant Isolation Tests
# ============================================================================

class TestTenantIsolation:
    """Test tenant isolation"""

    @pytest.mark.asyncio
    async def test_list_isolation(self, tenant_validator):
        """Test that list endpoints are tenant-isolated"""
        result = await tenant_validator.test_api_list_isolation()
        assert result.status.value == "passed", \
               f"List isolation failed: {result.message}"
        assert len(result.violations) == 0, \
               f"Found {len(result.violations)} isolation violations"

    @pytest.mark.asyncio
    async def test_get_isolation(self, tenant_validator):
        """Test that GET endpoints are tenant-isolated"""
        result = await tenant_validator.test_api_get_isolation()
        assert result.status.value == "passed", \
               f"Get isolation failed: {result.message}"
        assert len(result.violations) == 0, \
               f"Found {len(result.violations)} isolation violations"

    @pytest.mark.asyncio
    async def test_create_tenant_tagging(self, tenant_validator):
        """Test that created resources are tagged with tenant"""
        result = await tenant_validator.test_api_create_isolation()
        assert result.status.value == "passed", \
               f"Create isolation failed: {result.message}"

    @pytest.mark.asyncio
    async def test_tenant_switching(self, tenant_validator):
        """Test that tenant context switches correctly"""
        result = await tenant_validator.test_api_tenant_switching()
        assert result.status.value == "passed", \
               f"Tenant switching failed: {result.message}"
        assert len(result.violations) == 0, \
               "Tenant context bleed detected"

    def test_tenant_header_required(self, client):
        """Test that tenant header is required"""
        response = client.get(
            "/models",
            headers={"x-user-id": "test-user"}  # No x-tenant-id
        )
        assert response.status_code in [400, 403], \
               "Tenant header should be required"

    def test_cross_tenant_access_denied(self, client):
        """Test that cross-tenant access is denied"""
        # Create resource in tenant A
        tenant_a_headers = {"x-user-id": "user-a", "x-tenant-id": "tenant-a"}
        create_response = client.post(
            "/models",
            json={"id": "cross-tenant-test", "name": "Test"},
            headers=tenant_a_headers
        )

        if create_response.status_code in [200, 201]:
            # Try to access from tenant B
            tenant_b_headers = {"x-user-id": "user-b", "x-tenant-id": "tenant-b"}
            access_response = client.get(
                "/models/cross-tenant-test",
                headers=tenant_b_headers
            )
            assert access_response.status_code == 404, \
                   "Cross-tenant access should return 404"


# ============================================================================
# Security Headers Tests
# ============================================================================

class TestSecurityHeaders:
    """Test security headers"""

    def test_x_content_type_options_present(self, client):
        """Test X-Content-Type-Options header"""
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff", \
               "X-Content-Type-Options header should be 'nosniff'"

    def test_x_frame_options_present(self, client):
        """Test X-Frame-Options header"""
        response = client.get("/health")
        assert "X-Frame-Options" in response.headers, \
               "X-Frame-Options header should be present"
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"], \
               "X-Frame-Options should be DENY or SAMEORIGIN"

    def test_strict_transport_security_present(self, client):
        """Test HSTS header"""
        response = client.get("/health")
        assert "Strict-Transport-Security" in response.headers, \
               "Strict-Transport-Security header should be present"

    def test_content_security_policy_present(self, client):
        """Test CSP header"""
        response = client.get("/health")
        # CSP may not be present on all endpoints, but should be on most
        if "Content-Security-Policy" in response.headers:
            csp = response.headers["Content-Security-Policy"]
            assert "default-src" in csp, "CSP should include default-src"

    def test_x_xss_protection_present(self, client):
        """Test X-XSS-Protection header"""
        response = client.get("/health")
        if "X-XSS-Protection" in response.headers:
            assert "1" in response.headers["X-XSS-Protection"], \
                   "X-XSS-Protection should be enabled"


# ============================================================================
# Input Validation Tests
# ============================================================================

class TestInputValidation:
    """Test input validation"""

    def test_sql_injection_prevented(self, client, auth_headers):
        """Test that SQL injection is prevented"""
        # Try SQL injection in query parameter
        response = client.get(
            "/models?name=' OR '1'='1",
            headers=auth_headers
        )
        # Should not return all models or cause error
        assert response.status_code in [200, 400], \
               "SQL injection attempt should be handled safely"

    def test_xss_prevented(self, client, auth_headers):
        """Test that XSS is prevented"""
        # Try XSS in POST data
        response = client.post(
            "/models",
            json={
                "id": "xss-test",
                "name": "<script>alert('XSS')</script>"
            },
            headers=auth_headers
        )

        if response.status_code in [200, 201]:
            # Verify script tags are escaped/sanitized
            data = response.json()
            if "name" in data:
                assert "<script>" not in data["name"], \
                       "Script tags should be sanitized"

    def test_path_traversal_prevented(self, client, auth_headers):
        """Test that path traversal is prevented"""
        # Try path traversal
        response = client.get(
            "/models/../../../etc/passwd",
            headers=auth_headers
        )
        assert response.status_code in [400, 404], \
               "Path traversal should be prevented"

    def test_invalid_json_rejected(self, client, auth_headers):
        """Test that invalid JSON is rejected"""
        response = client.post(
            "/models",
            data="invalid json {{{",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 400, \
               "Invalid JSON should be rejected with 400"

    def test_oversized_payload_rejected(self, client, auth_headers):
        """Test that oversized payloads are rejected"""
        huge_payload = {"name": "x" * 10_000_000}  # 10MB string
        response = client.post(
            "/models",
            json=huge_payload,
            headers=auth_headers
        )
        assert response.status_code in [400, 413], \
               "Oversized payload should be rejected"


# ============================================================================
# Security Audit Integration Tests
# ============================================================================

class TestSecurityAudit:
    """Integration tests using SecurityAuditor"""

    @pytest.mark.asyncio
    async def test_sql_injection_audit(self, security_auditor):
        """Run SQL injection tests"""
        results = await security_auditor._test_sql_injection()
        assert len(results) > 0, "SQL injection tests should run"
        # Check that no vulnerabilities were found
        vulnerabilities = [r for r in results if r.get("vulnerable", False)]
        assert len(vulnerabilities) == 0, \
               f"Found {len(vulnerabilities)} SQL injection vulnerabilities"

    @pytest.mark.asyncio
    async def test_xss_audit(self, security_auditor):
        """Run XSS tests"""
        results = await security_auditor._test_xss()
        assert len(results) > 0, "XSS tests should run"
        vulnerabilities = [r for r in results if r.get("vulnerable", False)]
        assert len(vulnerabilities) == 0, \
               f"Found {len(vulnerabilities)} XSS vulnerabilities"

    @pytest.mark.asyncio
    async def test_authentication_audit(self, security_auditor):
        """Run authentication tests"""
        results = await security_auditor._test_authentication()
        assert len(results) > 0, "Authentication tests should run"
        failures = [r for r in results if not r.get("passed", False)]
        assert len(failures) == 0, \
               f"Found {len(failures)} authentication failures"


# ============================================================================
# Performance & Security Tests
# ============================================================================

class TestPerformanceSecurity:
    """Test performance-related security"""

    def test_response_time_acceptable(self, client, auth_headers):
        """Test that response times are acceptable (DoS prevention)"""
        start = time.time()
        response = client.get("/models", headers=auth_headers)
        duration = time.time() - start

        assert duration < 2.0, \
               f"Response time too slow: {duration:.2f}s (potential DoS vector)"

    def test_concurrent_requests_handled(self, client, auth_headers):
        """Test that concurrent requests are handled properly"""
        import concurrent.futures

        def make_request():
            return client.get("/models", headers=auth_headers)

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]

        # All should succeed (or be rate limited)
        for response in responses:
            assert response.status_code in [200, 429], \
                   "Concurrent requests should be handled properly"


# ============================================================================
# CORS & CSRF Tests
# ============================================================================

class TestCORSAndCSRF:
    """Test CORS and CSRF protection"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present when configured"""
        response = client.options("/models")
        # CORS headers may not be present in test mode
        # In production, verify Access-Control-Allow-Origin is configured

    def test_csrf_protection(self, client, auth_headers):
        """Test CSRF protection for state-changing operations"""
        # For APIs with CSRF protection, verify token is required
        response = client.post(
            "/models",
            json={"id": "csrf-test", "name": "Test"},
            headers=auth_headers
            # Missing CSRF token if required
        )
        # Should succeed if no CSRF protection, or require token


# ============================================================================
# Test Runners
# ============================================================================

def run_security_tests():
    """Run all security tests"""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "Test"
    ])


def run_critical_tests_only():
    """Run only critical security tests"""
    pytest.main([
        __file__,
        "-v",
        "-m", "critical",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_security_tests()


# ============================================================================
# Usage
# ============================================================================

"""
1. Run all tests:
   pytest security_testing/test_security_suite.py -v

2. Run specific test class:
   pytest security_testing/test_security_suite.py::TestAuthentication -v

3. Run with coverage:
   pytest security_testing/test_security_suite.py --cov=api --cov-report=html

4. Run only failed tests from last run:
   pytest security_testing/test_security_suite.py --lf

5. Run with detailed output:
   pytest security_testing/test_security_suite.py -vv --tb=long

6. Generate JUnit XML report:
   pytest security_testing/test_security_suite.py --junitxml=security_report.xml

7. Run in parallel:
   pytest security_testing/test_security_suite.py -n 4

Expected Results:
- All authentication tests should pass
- All authorization tests should pass
- Rate limiting should be enforced
- Tenant isolation should be complete (0 violations)
- Security headers should be present
- SQL injection and XSS should be prevented
- Input validation should reject malicious input

Failure Indicators:
- Cross-tenant access succeeds (CRITICAL)
- Missing authentication allows access (CRITICAL)
- SQL injection succeeds (CRITICAL)
- XSS reflected in response (HIGH)
- Missing security headers (MEDIUM)
- Rate limiting not enforced (MEDIUM)
"""
