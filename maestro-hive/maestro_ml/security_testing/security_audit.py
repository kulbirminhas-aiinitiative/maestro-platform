"""
Security Audit Framework

Automated security testing and vulnerability scanning for the Maestro ML platform.
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class VulnerabilitySeverity(str, Enum):
    """Vulnerability severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(str, Enum):
    """Types of vulnerabilities"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    AUTH_BYPASS = "auth_bypass"
    RATE_LIMIT_BYPASS = "rate_limit_bypass"
    TENANT_ISOLATION_BREACH = "tenant_isolation_breach"
    PERMISSION_ESCALATION = "permission_escalation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    INSECURE_HEADERS = "insecure_headers"
    WEAK_CRYPTO = "weak_crypto"


@dataclass
class Vulnerability:
    """Vulnerability finding"""
    id: str
    type: VulnerabilityType
    severity: VulnerabilitySeverity
    title: str
    description: str
    endpoint: str
    method: str
    evidence: Optional[str] = None
    remediation: Optional[str] = None
    cve: Optional[str] = None
    cvss_score: Optional[float] = None


@dataclass
class AuditReport:
    """Security audit report"""
    timestamp: str
    duration_seconds: float
    target_url: str
    total_tests: int
    vulnerabilities: List[Vulnerability]
    passed_tests: int
    failed_tests: int
    summary: Dict[str, int]


class SecurityAuditor:
    """
    Automated security auditor for the Maestro ML platform.

    Performs comprehensive security testing including:
    - SQL injection detection
    - XSS vulnerability scanning
    - Authentication bypass attempts
    - Rate limiting validation
    - Tenant isolation verification
    - Permission escalation checks
    - Security header validation
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize security auditor.

        Args:
            base_url: Base URL of the API to test
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.vulnerabilities: List[Vulnerability] = []
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0

    async def run_full_audit(self) -> AuditReport:
        """
        Run complete security audit.

        Returns:
            Detailed audit report
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting security audit on {self.base_url}")

        # Run all security tests
        await self._test_sql_injection()
        await self._test_xss()
        await self._test_authentication()
        await self._test_authorization()
        await self._test_rate_limiting()
        await self._test_tenant_isolation()
        await self._test_security_headers()
        await self._test_csrf()
        await self._test_input_validation()

        # Generate report
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Summarize by severity
        summary = {
            VulnerabilitySeverity.CRITICAL: 0,
            VulnerabilitySeverity.HIGH: 0,
            VulnerabilitySeverity.MEDIUM: 0,
            VulnerabilitySeverity.LOW: 0,
            VulnerabilitySeverity.INFO: 0
        }

        for vuln in self.vulnerabilities:
            summary[vuln.severity] += 1

        report = AuditReport(
            timestamp=start_time.isoformat(),
            duration_seconds=duration,
            target_url=self.base_url,
            total_tests=self.test_count,
            vulnerabilities=self.vulnerabilities,
            passed_tests=self.passed_count,
            failed_tests=self.failed_count,
            summary={k.value: v for k, v in summary.items()}
        )

        logger.info(f"Security audit completed in {duration:.2f}s")
        logger.info(f"Found {len(self.vulnerabilities)} vulnerabilities")

        return report

    async def _test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        logger.info("Testing SQL injection vulnerabilities...")

        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users--",
            "' UNION SELECT NULL--",
            "admin'--",
            "' OR 1=1--"
        ]

        test_endpoints = [
            "/models",
            "/experiments",
            "/users"
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in test_endpoints:
                for payload in payloads:
                    self.test_count += 1

                    # Test in query parameters
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            params={"id": payload}
                        )

                        # Check for SQL error messages
                        if any(err in response.text.lower() for err in [
                            'sql', 'mysql', 'postgresql', 'syntax error',
                            'sqlite', 'database error'
                        ]):
                            self._add_vulnerability(
                                type=VulnerabilityType.SQL_INJECTION,
                                severity=VulnerabilitySeverity.CRITICAL,
                                title="SQL Injection Vulnerability",
                                description=f"Endpoint vulnerable to SQL injection via query parameter",
                                endpoint=endpoint,
                                method="GET",
                                evidence=f"Payload: {payload}, Response contains SQL errors",
                                remediation="Use parameterized queries and ORM properly"
                            )
                        else:
                            self.passed_count += 1

                    except Exception as e:
                        logger.debug(f"SQL injection test error: {e}")

    async def _test_xss(self):
        """Test for XSS vulnerabilities"""
        logger.info("Testing XSS vulnerabilities...")

        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
        ]

        test_endpoints = [
            "/models",
            "/experiments"
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in test_endpoints:
                for payload in payloads:
                    self.test_count += 1

                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            params={"search": payload}
                        )

                        # Check if payload is reflected without encoding
                        if payload in response.text:
                            self._add_vulnerability(
                                type=VulnerabilityType.XSS,
                                severity=VulnerabilitySeverity.HIGH,
                                title="Cross-Site Scripting (XSS)",
                                description="User input reflected without proper encoding",
                                endpoint=endpoint,
                                method="GET",
                                evidence=f"Payload {payload} reflected in response",
                                remediation="Implement proper output encoding and CSP headers"
                            )
                        else:
                            self.passed_count += 1

                    except Exception as e:
                        logger.debug(f"XSS test error: {e}")

    async def _test_authentication(self):
        """Test authentication mechanisms"""
        logger.info("Testing authentication...")

        protected_endpoints = [
            "/models",
            "/experiments",
            "/admin/users"
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in protected_endpoints:
                self.test_count += 1

                # Test without authentication
                try:
                    response = await client.get(f"{self.base_url}{endpoint}")

                    if response.status_code != 401:
                        self._add_vulnerability(
                            type=VulnerabilityType.AUTH_BYPASS,
                            severity=VulnerabilitySeverity.CRITICAL,
                            title="Authentication Bypass",
                            description="Endpoint accessible without authentication",
                            endpoint=endpoint,
                            method="GET",
                            evidence=f"Status code: {response.status_code}",
                            remediation="Enforce authentication on all protected endpoints"
                        )
                    else:
                        self.passed_count += 1

                except Exception as e:
                    logger.debug(f"Auth test error: {e}")

    async def _test_authorization(self):
        """Test authorization and permission checks"""
        logger.info("Testing authorization...")

        # Test with low-privilege user
        headers = {
            "x-user-id": "test-viewer",
            "x-tenant-id": "test-tenant"
        }

        admin_endpoints = [
            ("/admin/users", "POST"),
            ("/models/delete", "DELETE"),
            ("/system/config", "PUT")
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint, method in admin_endpoints:
                self.test_count += 1

                try:
                    if method == "GET":
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            headers=headers
                        )
                    elif method == "POST":
                        response = await client.post(
                            f"{self.base_url}{endpoint}",
                            headers=headers,
                            json={}
                        )
                    elif method == "DELETE":
                        response = await client.delete(
                            f"{self.base_url}{endpoint}",
                            headers=headers
                        )
                    else:
                        response = await client.put(
                            f"{self.base_url}{endpoint}",
                            headers=headers,
                            json={}
                        )

                    if response.status_code != 403:
                        self._add_vulnerability(
                            type=VulnerabilityType.PERMISSION_ESCALATION,
                            severity=VulnerabilitySeverity.CRITICAL,
                            title="Permission Escalation",
                            description="Low-privilege user can access admin endpoint",
                            endpoint=endpoint,
                            method=method,
                            evidence=f"Viewer role got status {response.status_code}",
                            remediation="Enforce RBAC on all admin endpoints"
                        )
                    else:
                        self.passed_count += 1

                except Exception as e:
                    logger.debug(f"Authorization test error: {e}")

    async def _test_rate_limiting(self):
        """Test rate limiting implementation"""
        logger.info("Testing rate limiting...")

        self.test_count += 1

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {"x-user-id": "rate-limit-test"}

            # Make 150 requests (should hit limit at 100)
            responses = []
            for i in range(150):
                try:
                    response = await client.get(
                        f"{self.base_url}/models",
                        headers=headers
                    )
                    responses.append(response.status_code)
                except Exception:
                    pass

            # Check if 429 was returned
            if 429 not in responses:
                self._add_vulnerability(
                    type=VulnerabilityType.RATE_LIMIT_BYPASS,
                    severity=VulnerabilitySeverity.HIGH,
                    title="Rate Limiting Not Enforced",
                    description="API does not enforce rate limits",
                    endpoint="/models",
                    method="GET",
                    evidence=f"Made 150 requests, no 429 status received",
                    remediation="Implement and enforce rate limiting"
                )
            else:
                self.passed_count += 1

    async def _test_tenant_isolation(self):
        """Test tenant isolation"""
        logger.info("Testing tenant isolation...")

        self.test_count += 1

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Create resource in tenant A
            headers_a = {
                "x-user-id": "user-a",
                "x-tenant-id": "tenant-a"
            }

            try:
                create_response = await client.post(
                    f"{self.base_url}/models",
                    headers=headers_a,
                    json={"id": "test-model", "name": "Test"}
                )

                if create_response.status_code == 200:
                    # Try to access from tenant B
                    headers_b = {
                        "x-user-id": "user-b",
                        "x-tenant-id": "tenant-b"
                    }

                    access_response = await client.get(
                        f"{self.base_url}/models/test-model",
                        headers=headers_b
                    )

                    if access_response.status_code == 200:
                        self._add_vulnerability(
                            type=VulnerabilityType.TENANT_ISOLATION_BREACH,
                            severity=VulnerabilitySeverity.CRITICAL,
                            title="Tenant Isolation Breach",
                            description="User can access resources from other tenants",
                            endpoint="/models",
                            method="GET",
                            evidence="Cross-tenant access successful",
                            remediation="Enforce tenant filtering on all queries"
                        )
                    else:
                        self.passed_count += 1

            except Exception as e:
                logger.debug(f"Tenant isolation test error: {e}")

    async def _test_security_headers(self):
        """Test security headers"""
        logger.info("Testing security headers...")

        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "Strict-Transport-Security": None,  # Just check presence
            "Content-Security-Policy": None
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/health")

                for header, expected_value in required_headers.items():
                    self.test_count += 1

                    if header not in response.headers:
                        self._add_vulnerability(
                            type=VulnerabilityType.INSECURE_HEADERS,
                            severity=VulnerabilitySeverity.MEDIUM,
                            title=f"Missing Security Header: {header}",
                            description=f"Response missing {header} security header",
                            endpoint="/health",
                            method="GET",
                            evidence=f"Header {header} not present",
                            remediation=f"Add {header} header to all responses"
                        )
                    elif expected_value:
                        actual = response.headers[header]
                        if isinstance(expected_value, list):
                            if actual not in expected_value:
                                self._add_vulnerability(
                                    type=VulnerabilityType.INSECURE_HEADERS,
                                    severity=VulnerabilitySeverity.LOW,
                                    title=f"Incorrect Security Header: {header}",
                                    description=f"Header {header} has unexpected value",
                                    endpoint="/health",
                                    method="GET",
                                    evidence=f"Expected one of {expected_value}, got {actual}",
                                    remediation=f"Set {header} to recommended value"
                                )
                        else:
                            self.passed_count += 1
                    else:
                        self.passed_count += 1

            except Exception as e:
                logger.debug(f"Security headers test error: {e}")

    async def _test_csrf(self):
        """Test CSRF protection"""
        logger.info("Testing CSRF protection...")

        self.test_count += 1

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Try state-changing operation without CSRF token
            try:
                response = await client.post(
                    f"{self.base_url}/models",
                    json={"name": "test"},
                    headers={"x-user-id": "test-user"}
                )

                # If accepted without CSRF token, it's vulnerable
                # (This is a simplified test - real CSRF testing is more complex)
                if response.status_code == 200:
                    self._add_vulnerability(
                        type=VulnerabilityType.CSRF,
                        severity=VulnerabilitySeverity.MEDIUM,
                        title="CSRF Protection Missing",
                        description="State-changing operation lacks CSRF protection",
                        endpoint="/models",
                        method="POST",
                        evidence="Request accepted without CSRF token",
                        remediation="Implement CSRF token validation"
                    )

            except Exception as e:
                logger.debug(f"CSRF test error: {e}")

    async def _test_input_validation(self):
        """Test input validation"""
        logger.info("Testing input validation...")

        malicious_inputs = [
            {"id": "A" * 10000},  # Oversized input
            {"id": "../../../etc/passwd"},  # Path traversal
            {"id": "<?xml version='1.0'?><!DOCTYPE foo>"},  # XXE
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for payload in malicious_inputs:
                self.test_count += 1

                try:
                    response = await client.post(
                        f"{self.base_url}/models",
                        json=payload,
                        headers={"x-user-id": "test"}
                    )

                    # Should reject with 400
                    if response.status_code not in [400, 422]:
                        self._add_vulnerability(
                            type=VulnerabilityType.INFORMATION_DISCLOSURE,
                            severity=VulnerabilitySeverity.MEDIUM,
                            title="Insufficient Input Validation",
                            description="Malicious input not properly rejected",
                            endpoint="/models",
                            method="POST",
                            evidence=f"Payload accepted: {payload}",
                            remediation="Implement strict input validation"
                        )
                    else:
                        self.passed_count += 1

                except Exception as e:
                    logger.debug(f"Input validation test error: {e}")

    def _add_vulnerability(
        self,
        type: VulnerabilityType,
        severity: VulnerabilitySeverity,
        title: str,
        description: str,
        endpoint: str,
        method: str,
        evidence: Optional[str] = None,
        remediation: Optional[str] = None
    ):
        """Add vulnerability to report"""
        vuln = Vulnerability(
            id=f"VULN-{len(self.vulnerabilities) + 1:04d}",
            type=type,
            severity=severity,
            title=title,
            description=description,
            endpoint=endpoint,
            method=method,
            evidence=evidence,
            remediation=remediation
        )
        self.vulnerabilities.append(vuln)
        self.failed_count += 1

        logger.warning(
            f"Vulnerability found: {severity.value.upper()} - {title} "
            f"at {method} {endpoint}"
        )

    def export_report(self, report: AuditReport, filepath: str):
        """Export report to JSON file"""
        report_dict = asdict(report)

        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Report exported to {filepath}")


async def main():
    """Run security audit"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python security_audit.py <base_url>")
        sys.exit(1)

    base_url = sys.argv[1]

    auditor = SecurityAuditor(base_url)
    report = await auditor.run_full_audit()

    # Print summary
    print("\n" + "="*60)
    print("SECURITY AUDIT REPORT")
    print("="*60)
    print(f"Target: {report.target_url}")
    print(f"Duration: {report.duration_seconds:.2f}s")
    print(f"Total Tests: {report.total_tests}")
    print(f"Passed: {report.passed_tests}")
    print(f"Failed: {report.failed_tests}")
    print("\nVulnerabilities by Severity:")
    for severity, count in report.summary.items():
        if count > 0:
            print(f"  {severity.upper()}: {count}")

    # Export report
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_file = f"security_audit_{timestamp}.json"
    auditor.export_report(report, report_file)

    print(f"\nDetailed report: {report_file}")

    # Return exit code based on critical/high vulnerabilities
    critical_high = (
        report.summary.get('critical', 0) +
        report.summary.get('high', 0)
    )
    sys.exit(1 if critical_high > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
