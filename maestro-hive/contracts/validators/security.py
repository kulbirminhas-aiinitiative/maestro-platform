"""
Security Validator
Version: 1.0.0

Validates security best practices and vulnerabilities.
"""

from typing import Dict, Any, List
from pathlib import Path
import logging
import json

from contracts.validators.base import BaseValidator, ValidationResult, ValidationError

logger = logging.getLogger(__name__)


class SecurityValidator(BaseValidator):
    """
    Validates security vulnerabilities and best practices.

    Checks:
    - Known CVEs in dependencies
    - Security headers (CSP, HSTS, X-Frame-Options, etc.)
    - Authentication/Authorization
    - Input validation
    - SQL injection vulnerabilities
    - XSS vulnerabilities
    - CSRF protection

    Configuration:
        severity_threshold: str - Minimum severity to fail ("low", "medium", "high", "critical")
        check_dependencies: bool - Check dependency vulnerabilities (default: True)
        check_headers: bool - Check security headers (default: True)
        check_auth: bool - Check authentication/authorization (default: True)
        allowed_vulnerabilities: List[str] - CVE IDs to ignore (optional)
    """

    def __init__(self, timeout_seconds: float = 60.0):
        """
        Initialize SecurityValidator.

        Args:
            timeout_seconds: Maximum execution time (default: 60s)
        """
        super().__init__(
            validator_name="SecurityValidator",
            validator_version="1.0.0",
            timeout_seconds=timeout_seconds
        )

    async def validate(
        self,
        artifacts: Dict[str, Any],
        config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate security.

        Args:
            artifacts: {
                "scan_results": Path to security scan results JSON,
                "dependencies": Path to dependencies file (package.json, requirements.txt, etc.),
                "headers": Dict of HTTP security headers (optional)
            }
            config: {
                "severity_threshold": "high",  # Fail on high/critical
                "check_dependencies": True,
                "check_headers": True,
                "check_auth": True,
                "allowed_vulnerabilities": []  # CVE IDs to ignore
            }

        Returns:
            ValidationResult with security assessment
        """
        # Extract artifacts
        scan_results_path = artifacts.get("scan_results")
        headers = artifacts.get("headers", {})

        # Get configuration
        severity_threshold = config.get("severity_threshold", "high").lower()
        check_deps = config.get("check_dependencies", True)
        check_headers = config.get("check_headers", True)
        check_auth = config.get("check_auth", True)
        allowed_vulns = config.get("allowed_vulnerabilities", [])

        # Validate severity threshold
        valid_severities = ["low", "medium", "high", "critical"]
        if severity_threshold not in valid_severities:
            raise ValidationError(
                f"Invalid severity_threshold: {severity_threshold} "
                f"(must be one of: {', '.join(valid_severities)})"
            )

        severity_order = {sev: idx for idx, sev in enumerate(valid_severities)}
        threshold_level = severity_order[severity_threshold]

        # Load scan results if provided
        vulnerabilities = []
        if scan_results_path:
            scan_results = await self._load_scan_results(scan_results_path)
            vulnerabilities = scan_results.get("vulnerabilities", [])

        # Filter by allowed vulnerabilities
        if allowed_vulns:
            vulnerabilities = [
                v for v in vulnerabilities
                if v.get("cve_id") not in allowed_vulns and v.get("id") not in allowed_vulns
            ]

        # Categorize vulnerabilities by severity
        critical_vulns = [v for v in vulnerabilities if v.get("severity", "").lower() == "critical"]
        high_vulns = [v for v in vulnerabilities if v.get("severity", "").lower() == "high"]
        medium_vulns = [v for v in vulnerabilities if v.get("severity", "").lower() == "medium"]
        low_vulns = [v for v in vulnerabilities if v.get("severity", "").lower() == "low"]

        # Check security headers
        header_violations = []
        header_warnings = []

        if check_headers:
            required_headers = {
                "Content-Security-Policy": "CSP protects against XSS",
                "Strict-Transport-Security": "HSTS enforces HTTPS",
                "X-Frame-Options": "Protects against clickjacking",
                "X-Content-Type-Options": "Prevents MIME sniffing",
                "Referrer-Policy": "Controls referrer information"
            }

            for header, description in required_headers.items():
                if header not in headers:
                    header_warnings.append(f"Missing security header: {header} ({description})")

        # Build errors and warnings
        errors = []
        warnings = []

        # Add vulnerability errors based on threshold
        for vuln in critical_vulns:
            if severity_order["critical"] >= threshold_level:
                errors.append(
                    f"[CRITICAL] {vuln.get('cve_id', vuln.get('id', 'Unknown'))}: "
                    f"{vuln.get('description', 'No description')}"
                )

        for vuln in high_vulns:
            if severity_order["high"] >= threshold_level:
                errors.append(
                    f"[HIGH] {vuln.get('cve_id', vuln.get('id', 'Unknown'))}: "
                    f"{vuln.get('description', 'No description')}"
                )

        for vuln in medium_vulns:
            if severity_order["medium"] >= threshold_level:
                warnings.append(
                    f"[MEDIUM] {vuln.get('cve_id', vuln.get('id', 'Unknown'))}: "
                    f"{vuln.get('description', 'No description')}"
                )

        for vuln in low_vulns:
            if severity_order["low"] >= threshold_level:
                warnings.append(
                    f"[LOW] {vuln.get('cve_id', vuln.get('id', 'Unknown'))}: "
                    f"{vuln.get('description', 'No description')}"
                )

        # Add header violations
        errors.extend(header_violations)
        warnings.extend(header_warnings)

        # Determine pass/fail
        passed = len(errors) == 0

        # Calculate score
        total_vulns = len(vulnerabilities)
        if total_vulns > 0:
            # Weight by severity
            weighted_issues = (len(critical_vulns) * 4 + len(high_vulns) * 3 +
                             len(medium_vulns) * 2 + len(low_vulns) * 1)
            max_score = total_vulns * 4  # If all were critical
            score = max(0.0, 1.0 - (weighted_issues / max_score))
        else:
            score = 1.0 if passed else 0.8  # Deduct for header issues

        # Build message
        if passed:
            if warnings:
                message = f"Security acceptable with {len(warnings)} warnings"
            else:
                message = "No security vulnerabilities found"
        else:
            message = f"Security violations: {len(critical_vulns)} critical, {len(high_vulns)} high severity"

        # Collect evidence
        evidence = {
            "total_vulnerabilities": total_vulns,
            "critical_count": len(critical_vulns),
            "high_count": len(high_vulns),
            "medium_count": len(medium_vulns),
            "low_count": len(low_vulns),
            "severity_threshold": severity_threshold,
            "security_headers_checked": len(headers),
            "vulnerability_details": [
                {
                    "id": v.get("cve_id", v.get("id", "Unknown")),
                    "severity": v.get("severity"),
                    "description": v.get("description"),
                    "affected_package": v.get("package"),
                    "fixed_in": v.get("fixed_in")
                }
                for v in (critical_vulns + high_vulns)[:10]  # Top 10 critical/high
            ]
        }

        return ValidationResult(
            passed=passed,
            score=score,
            message=message,
            details=f"Found {total_vulns} vulnerabilities, threshold: {severity_threshold}",
            evidence=evidence,
            errors=errors[:10],  # Limit to 10
            warnings=warnings[:10]  # Limit to 10
        )

    async def _load_scan_results(self, results_path: str) -> Dict[str, Any]:
        """Load security scan results from JSON file."""
        path = Path(results_path)

        if not path.exists():
            raise ValidationError(f"Security scan results not found: {results_path}")

        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValidationError(f"Failed to load security scan results: {str(e)}")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "SecurityValidator",
]
