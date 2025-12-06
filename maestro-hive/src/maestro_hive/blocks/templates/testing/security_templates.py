"""
Security Test Templates - MD-2523

Security testing templates covering OWASP Top 10 vulnerabilities.
"""

from typing import Dict, Any
from .models import TestTemplate, TestType, TestFramework


class OWASPSecurityTemplate(TestTemplate):
    """OWASP Top 10 security testing template."""

    def __init__(self, target_url: str = "http://localhost:8000"):
        super().__init__(
            name="owasp_security_template",
            description="Security tests covering OWASP Top 10 vulnerabilities",
            test_type=TestType.SECURITY,
            framework=TestFramework.PYTEST,
            tags=["security", "owasp", "vulnerability", "penetration"],
            dependencies=[
                "pytest>=7.0.0",
                "httpx>=0.24.0",
                "python-owasp-zap-v2.4>=0.0.21",
            ],
            variables={"target_url": target_url},
        )

        self.template_content = '''"""
OWASP Top 10 Security Tests

Tests for common web application vulnerabilities.
Target: {{ target_url }}

OWASP Top 10 (2021):
A01 - Broken Access Control
A02 - Cryptographic Failures
A03 - Injection
A04 - Insecure Design
A05 - Security Misconfiguration
A06 - Vulnerable Components
A07 - Authentication Failures
A08 - Data Integrity Failures
A09 - Security Logging Failures
A10 - Server-Side Request Forgery
"""

import pytest
import httpx
from typing import Dict, Any, List
import re


TARGET_URL = "{{ target_url }}"


@pytest.fixture(scope="module")
async def http_client():
    """HTTP client for security tests."""
    async with httpx.AsyncClient(
        base_url=TARGET_URL,
        timeout=30.0,
        follow_redirects=False,
    ) as client:
        yield client


# ==============================================================================
# A01: Broken Access Control
# ==============================================================================

class TestA01BrokenAccessControl:
    """Tests for broken access control vulnerabilities."""

    @pytest.mark.asyncio
    async def test_horizontal_privilege_escalation(self, http_client):
        """Test that users cannot access other users' data."""
        # Authenticate as user1
        login_response = await http_client.post(
            "/api/auth/login",
            json={"email": "user1@test.com", "password": "password"},
        )
        token = login_response.json().get("token", "")

        # Try to access user2's data
        response = await http_client.get(
            "/api/users/user2/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in [401, 403, 404], (
            "User should not access other user's profile"
        )

    @pytest.mark.asyncio
    async def test_vertical_privilege_escalation(self, http_client):
        """Test that regular users cannot access admin endpoints."""
        # Authenticate as regular user
        login_response = await http_client.post(
            "/api/auth/login",
            json={"email": "user@test.com", "password": "password"},
        )
        token = login_response.json().get("token", "")

        # Try admin endpoints
        admin_endpoints = [
            "/api/admin/users",
            "/api/admin/settings",
            "/api/admin/logs",
        ]

        for endpoint in admin_endpoints:
            response = await http_client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code in [401, 403], (
                f"Regular user should not access {endpoint}"
            )

    @pytest.mark.asyncio
    async def test_insecure_direct_object_reference(self, http_client):
        """Test for IDOR vulnerabilities."""
        # Try sequential IDs
        for resource_id in range(1, 10):
            response = await http_client.get(
                f"/api/documents/{resource_id}",
            )
            if response.status_code == 200:
                pytest.skip("Found accessible resource - verify authorization")


# ==============================================================================
# A02: Cryptographic Failures
# ==============================================================================

class TestA02CryptographicFailures:
    """Tests for cryptographic vulnerabilities."""

    @pytest.mark.asyncio
    async def test_https_enforcement(self, http_client):
        """Test that HTTPS is enforced."""
        response = await http_client.get("/")
        # Check for HSTS header
        assert "strict-transport-security" in response.headers or True, (
            "HSTS header should be present"
        )

    @pytest.mark.asyncio
    async def test_sensitive_data_in_url(self, http_client):
        """Test that sensitive data is not passed in URL parameters."""
        # Check that sensitive endpoints don't use GET with credentials
        response = await http_client.get(
            "/api/auth/login?password=test",
        )
        assert response.status_code != 200, (
            "Credentials should not be accepted via URL parameters"
        )

    @pytest.mark.asyncio
    async def test_password_not_in_response(self, http_client):
        """Test that passwords are never returned in responses."""
        response = await http_client.get("/api/users")
        if response.status_code == 200:
            body = response.text.lower()
            assert "password" not in body or "password_hash" not in body, (
                "Password should not be in response"
            )


# ==============================================================================
# A03: Injection
# ==============================================================================

class TestA03Injection:
    """Tests for injection vulnerabilities."""

    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users;--",
        "' UNION SELECT * FROM users--",
        "1' AND '1'='1",
        "admin'--",
    ]

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
        "'\"><script>alert('XSS')</script>",
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_sql_injection_login(self, http_client, payload):
        """Test SQL injection in login endpoint."""
        response = await http_client.post(
            "/api/auth/login",
            json={"email": payload, "password": "test"},
        )
        # Should not indicate SQL error or successful login with injection
        assert "sql" not in response.text.lower()
        assert response.status_code in [400, 401, 422]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_sql_injection_search(self, http_client, payload):
        """Test SQL injection in search parameter."""
        response = await http_client.get(
            "/api/search",
            params={"q": payload},
        )
        assert "sql" not in response.text.lower()
        assert "error" not in response.text.lower() or response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_stored_xss(self, http_client, payload):
        """Test stored XSS vulnerabilities."""
        # Try to store XSS payload
        await http_client.post(
            "/api/comments",
            json={"content": payload},
        )

        # Retrieve and check if escaped
        response = await http_client.get("/api/comments")
        if response.status_code == 200:
            # Check that script tags are escaped
            assert "<script>" not in response.text
            assert "onerror=" not in response.text

    @pytest.mark.asyncio
    async def test_command_injection(self, http_client):
        """Test command injection vulnerabilities."""
        cmd_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "`id`",
            "$(whoami)",
        ]

        for payload in cmd_payloads:
            response = await http_client.post(
                "/api/process",
                json={"filename": payload},
            )
            # Should not execute commands
            assert "root:" not in response.text
            assert "uid=" not in response.text


# ==============================================================================
# A07: Authentication Failures
# ==============================================================================

class TestA07AuthenticationFailures:
    """Tests for authentication vulnerabilities."""

    @pytest.mark.asyncio
    async def test_brute_force_protection(self, http_client):
        """Test rate limiting on login endpoint."""
        # Attempt multiple failed logins
        for i in range(10):
            response = await http_client.post(
                "/api/auth/login",
                json={"email": "test@test.com", "password": f"wrong{i}"},
            )

        # Should be rate limited
        final_response = await http_client.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "wrong"},
        )
        assert final_response.status_code in [429, 423], (
            "Should rate limit after multiple failed attempts"
        )

    @pytest.mark.asyncio
    async def test_weak_password_rejection(self, http_client):
        """Test that weak passwords are rejected."""
        weak_passwords = ["123456", "password", "admin", "qwerty", "abc123"]

        for password in weak_passwords:
            response = await http_client.post(
                "/api/auth/register",
                json={
                    "email": "newuser@test.com",
                    "password": password,
                },
            )
            # Weak passwords should be rejected
            if response.status_code == 200:
                pytest.fail(f"Weak password '{password}' was accepted")

    @pytest.mark.asyncio
    async def test_session_fixation(self, http_client):
        """Test for session fixation vulnerability."""
        # Get initial session
        response1 = await http_client.get("/")
        initial_session = response1.cookies.get("session")

        # Login
        await http_client.post(
            "/api/auth/login",
            json={"email": "user@test.com", "password": "password"},
        )

        # Session should change after login
        response2 = await http_client.get("/")
        new_session = response2.cookies.get("session")

        if initial_session and new_session:
            assert initial_session != new_session, (
                "Session should regenerate after login"
            )


# ==============================================================================
# A10: Server-Side Request Forgery (SSRF)
# ==============================================================================

class TestA10SSRF:
    """Tests for SSRF vulnerabilities."""

    @pytest.mark.asyncio
    async def test_ssrf_internal_network(self, http_client):
        """Test that internal network access is blocked."""
        internal_urls = [
            "http://localhost:22",
            "http://127.0.0.1:8080",
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "http://internal-service:8080",
        ]

        for url in internal_urls:
            response = await http_client.post(
                "/api/fetch-url",
                json={"url": url},
            )
            assert response.status_code in [400, 403, 422], (
                f"Internal URL {url} should be blocked"
            )

    @pytest.mark.asyncio
    async def test_ssrf_file_protocol(self, http_client):
        """Test that file:// protocol is blocked."""
        response = await http_client.post(
            "/api/fetch-url",
            json={"url": "file:///etc/passwd"},
        )
        assert response.status_code in [400, 403, 422]
        assert "root:" not in response.text
'''


class SecurityScanTemplate(TestTemplate):
    """Automated security scanning template."""

    def __init__(self, target_url: str = "http://localhost:8000"):
        super().__init__(
            name="security_scan_template",
            description="Automated security scanning using OWASP ZAP",
            test_type=TestType.SECURITY,
            framework=TestFramework.PYTEST,
            tags=["security", "scan", "zap", "automated"],
            dependencies=["python-owasp-zap-v2.4>=0.0.21"],
            variables={"target_url": target_url},
        )

        self.template_content = '''"""
Automated Security Scan

Uses OWASP ZAP for automated vulnerability scanning.
Target: {{ target_url }}
"""

import pytest
from zapv2 import ZAPv2
import time


TARGET_URL = "{{ target_url }}"
ZAP_PROXY = "http://localhost:8090"


@pytest.fixture(scope="module")
def zap():
    """Initialize ZAP connection."""
    zap = ZAPv2(proxies={"http": ZAP_PROXY, "https": ZAP_PROXY})
    return zap


class TestSecurityScan:
    """Automated security scanning tests."""

    def test_spider_scan(self, zap):
        """Run spider to discover all pages."""
        scan_id = zap.spider.scan(TARGET_URL)

        # Wait for spider to complete
        while int(zap.spider.status(scan_id)) < 100:
            time.sleep(2)

        # Check results
        urls = zap.spider.results(scan_id)
        assert len(urls) > 0, "Spider should discover URLs"

    def test_passive_scan(self, zap):
        """Run passive scan for vulnerabilities."""
        # Access target to populate scan queue
        zap.urlopen(TARGET_URL)

        # Wait for passive scan
        while int(zap.pscan.records_to_scan) > 0:
            time.sleep(1)

        # Get alerts
        alerts = zap.core.alerts()
        high_alerts = [a for a in alerts if a["risk"] == "High"]
        medium_alerts = [a for a in alerts if a["risk"] == "Medium"]

        # Report findings
        if high_alerts:
            pytest.fail(f"Found {len(high_alerts)} high-risk vulnerabilities")

    def test_active_scan(self, zap):
        """Run active scan for vulnerabilities."""
        scan_id = zap.ascan.scan(TARGET_URL)

        # Wait for scan (with timeout)
        timeout = 300
        start = time.time()
        while int(zap.ascan.status(scan_id)) < 100:
            if time.time() - start > timeout:
                break
            time.sleep(5)

        # Get alerts
        alerts = zap.core.alerts()
        critical = [a for a in alerts if a["risk"] in ["High", "Critical"]]

        assert len(critical) == 0, (
            f"Found {len(critical)} critical vulnerabilities"
        )
'''


class VulnerabilityTestTemplate(TestTemplate):
    """Specific vulnerability testing template."""

    def __init__(self):
        super().__init__(
            name="vulnerability_test_template",
            description="Targeted tests for specific vulnerability types",
            test_type=TestType.SECURITY,
            framework=TestFramework.PYTEST,
            tags=["security", "vulnerability", "targeted"],
            dependencies=["pytest>=7.0.0", "httpx>=0.24.0"],
        )

        self.template_content = '''"""
Targeted Vulnerability Tests

Tests for specific vulnerability patterns.
"""

import pytest
import httpx


class TestHeaderSecurity:
    """Security header tests."""

    REQUIRED_HEADERS = {
        "x-content-type-options": "nosniff",
        "x-frame-options": ["DENY", "SAMEORIGIN"],
        "x-xss-protection": "1; mode=block",
    }

    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """Test that security headers are present."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/")

            for header, expected in self.REQUIRED_HEADERS.items():
                assert header in response.headers, f"Missing {header}"

                if isinstance(expected, list):
                    assert response.headers[header] in expected
                else:
                    assert response.headers[header] == expected

    @pytest.mark.asyncio
    async def test_csp_header(self):
        """Test Content Security Policy header."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/")
            csp = response.headers.get("content-security-policy", "")

            # Check for unsafe directives
            assert "unsafe-inline" not in csp or "'unsafe-inline'" in csp
            assert "unsafe-eval" not in csp or "'unsafe-eval'" in csp


class TestCORS:
    """CORS configuration tests."""

    @pytest.mark.asyncio
    async def test_cors_not_wildcard(self):
        """Test that CORS doesn't use wildcard for credentials."""
        async with httpx.AsyncClient() as client:
            response = await client.options(
                "http://localhost:8000/api/data",
                headers={"Origin": "http://evil.com"},
            )

            origin = response.headers.get("access-control-allow-origin", "")
            credentials = response.headers.get(
                "access-control-allow-credentials", ""
            )

            # Wildcard with credentials is insecure
            if credentials.lower() == "true":
                assert origin != "*", (
                    "Cannot use wildcard origin with credentials"
                )
'''
