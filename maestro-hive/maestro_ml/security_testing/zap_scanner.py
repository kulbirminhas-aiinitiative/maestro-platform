"""
OWASP ZAP Security Scanner Integration

Provides automated security scanning using OWASP ZAP:
- Spider/crawl the application
- Active security scanning
- Passive security scanning
- API security testing
- Generate security reports

Requires OWASP ZAP running in daemon mode:
    docker run -u zap -p 8090:8090 -i owasp/zap2docker-stable zap.sh \
        -daemon -host 0.0.0.0 -port 8090 -config api.disablekey=true
"""

from zapv2 import ZAPv2
from typing import Dict, List, Optional, Set
import time
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ScanStatus(Enum):
    """Scan status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(Enum):
    """Alert severity levels"""
    INFORMATIONAL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SecurityAlert:
    """Represents a security alert found by ZAP"""
    alert_id: str
    name: str
    risk: str  # High, Medium, Low, Informational
    confidence: str  # High, Medium, Low
    description: str
    url: str
    solution: str
    reference: str = ""
    cwe_id: Optional[int] = None
    wasc_id: Optional[int] = None
    evidence: str = ""
    attack: str = ""
    other_info: str = ""

    @property
    def severity(self) -> Severity:
        """Get severity level"""
        mapping = {
            "High": Severity.HIGH,
            "Medium": Severity.MEDIUM,
            "Low": Severity.LOW,
            "Informational": Severity.INFORMATIONAL
        }
        return mapping.get(self.risk, Severity.INFORMATIONAL)

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "risk": self.risk,
            "confidence": self.confidence,
            "description": self.description,
            "url": self.url,
            "solution": self.solution,
            "reference": self.reference,
            "cwe_id": self.cwe_id,
            "wasc_id": self.wasc_id,
            "evidence": self.evidence,
            "attack": self.attack,
            "other_info": self.other_info
        }


@dataclass
class ScanReport:
    """Security scan report"""
    scan_id: str
    target_url: str
    scan_type: str  # spider, active, passive, api
    start_time: str
    end_time: Optional[str] = None
    status: ScanStatus = ScanStatus.NOT_STARTED
    alerts: List[SecurityAlert] = field(default_factory=list)
    urls_scanned: int = 0
    duration_seconds: float = 0.0

    @property
    def high_severity_count(self) -> int:
        return len([a for a in self.alerts if a.severity == Severity.HIGH])

    @property
    def medium_severity_count(self) -> int:
        return len([a for a in self.alerts if a.severity == Severity.MEDIUM])

    @property
    def low_severity_count(self) -> int:
        return len([a for a in self.alerts if a.severity == Severity.LOW])

    @property
    def informational_count(self) -> int:
        return len([a for a in self.alerts if a.severity == Severity.INFORMATIONAL])

    def to_dict(self) -> Dict:
        return {
            "scan_id": self.scan_id,
            "target_url": self.target_url,
            "scan_type": self.scan_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "alerts": [a.to_dict() for a in self.alerts],
            "urls_scanned": self.urls_scanned,
            "duration_seconds": self.duration_seconds,
            "summary": {
                "high": self.high_severity_count,
                "medium": self.medium_severity_count,
                "low": self.low_severity_count,
                "informational": self.informational_count,
                "total": len(self.alerts)
            }
        }


class ZAPScanner:
    """
    OWASP ZAP Security Scanner Integration

    Usage:
        scanner = ZAPScanner(zap_url="http://localhost:8090")
        report = scanner.full_scan("http://localhost:8000")
        print(f"Found {report.high_severity_count} high severity issues")
    """

    def __init__(
        self,
        zap_url: str = "http://localhost:8090",
        api_key: Optional[str] = None
    ):
        """
        Initialize ZAP scanner

        Args:
            zap_url: URL where ZAP is running (default: http://localhost:8090)
            api_key: ZAP API key (optional, use if ZAP has API key enabled)
        """
        self.zap_url = zap_url
        self.zap = ZAPv2(proxies={'http': zap_url, 'https': zap_url}, apikey=api_key)
        self.api_key = api_key

        # Verify ZAP is accessible
        try:
            version = self.zap.core.version
            logger.info(f"Connected to ZAP {version} at {zap_url}")
        except Exception as e:
            logger.error(f"Failed to connect to ZAP at {zap_url}: {e}")
            raise

    def spider_scan(
        self,
        target_url: str,
        max_depth: int = 5,
        max_children: int = 10
    ) -> ScanReport:
        """
        Spider/crawl the target application

        Args:
            target_url: Base URL to spider
            max_depth: Maximum depth to crawl
            max_children: Maximum children per node

        Returns:
            ScanReport with discovered URLs
        """
        logger.info(f"Starting spider scan of {target_url}")
        start_time = datetime.utcnow()

        # Configure spider
        self.zap.spider.set_option_max_depth(max_depth)
        self.zap.spider.set_option_max_children(max_children)

        # Start spider
        scan_id = self.zap.spider.scan(target_url)
        logger.info(f"Spider scan started with ID: {scan_id}")

        # Wait for spider to complete
        while int(self.zap.spider.status(scan_id)) < 100:
            progress = int(self.zap.spider.status(scan_id))
            logger.info(f"Spider progress: {progress}%")
            time.sleep(2)

        # Get results
        urls = self.zap.spider.results(scan_id)
        end_time = datetime.utcnow()

        report = ScanReport(
            scan_id=scan_id,
            target_url=target_url,
            scan_type="spider",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            status=ScanStatus.COMPLETED,
            urls_scanned=len(urls),
            duration_seconds=(end_time - start_time).total_seconds()
        )

        logger.info(f"Spider scan completed: {len(urls)} URLs discovered")
        return report

    def active_scan(
        self,
        target_url: str,
        recurse: bool = True,
        in_scope_only: bool = False
    ) -> ScanReport:
        """
        Perform active security scan

        Active scanning sends attacks to the target to discover vulnerabilities.
        This can be intrusive and should only be run against systems you own.

        Args:
            target_url: URL to scan
            recurse: Scan child nodes
            in_scope_only: Only scan URLs in scope

        Returns:
            ScanReport with discovered vulnerabilities
        """
        logger.info(f"Starting active scan of {target_url}")
        start_time = datetime.utcnow()

        # Start active scan
        scan_id = self.zap.ascan.scan(target_url, recurse=recurse, inscopeonly=in_scope_only)
        logger.info(f"Active scan started with ID: {scan_id}")

        # Wait for scan to complete
        while int(self.zap.ascan.status(scan_id)) < 100:
            progress = int(self.zap.ascan.status(scan_id))
            logger.info(f"Active scan progress: {progress}%")
            time.sleep(5)

        # Get alerts
        alerts = self._get_alerts(target_url)
        end_time = datetime.utcnow()

        report = ScanReport(
            scan_id=scan_id,
            target_url=target_url,
            scan_type="active",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            status=ScanStatus.COMPLETED,
            alerts=alerts,
            duration_seconds=(end_time - start_time).total_seconds()
        )

        logger.info(f"Active scan completed: {len(alerts)} alerts found")
        return report

    def passive_scan(self, target_url: str, wait_time: int = 30) -> ScanReport:
        """
        Perform passive security scan

        Passive scanning analyzes traffic without sending attacks.
        Safe to run in production.

        Args:
            target_url: URL to analyze
            wait_time: Time to wait for passive scan (seconds)

        Returns:
            ScanReport with findings
        """
        logger.info(f"Starting passive scan of {target_url}")
        start_time = datetime.utcnow()

        # Access the URL to generate traffic
        self.zap.urlopen(target_url)

        # Wait for passive scan
        logger.info(f"Waiting {wait_time}s for passive scan...")
        time.sleep(wait_time)

        # Get alerts
        alerts = self._get_alerts(target_url)
        end_time = datetime.utcnow()

        report = ScanReport(
            scan_id="passive",
            target_url=target_url,
            scan_type="passive",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            status=ScanStatus.COMPLETED,
            alerts=alerts,
            duration_seconds=(end_time - start_time).total_seconds()
        )

        logger.info(f"Passive scan completed: {len(alerts)} alerts found")
        return report

    def api_scan(
        self,
        target_url: str,
        openapi_spec_url: Optional[str] = None
    ) -> ScanReport:
        """
        Scan REST API

        Args:
            target_url: API base URL
            openapi_spec_url: URL to OpenAPI/Swagger spec (optional)

        Returns:
            ScanReport with API security findings
        """
        logger.info(f"Starting API scan of {target_url}")
        start_time = datetime.utcnow()

        # Import OpenAPI spec if provided
        if openapi_spec_url:
            logger.info(f"Importing OpenAPI spec from {openapi_spec_url}")
            self.zap.openapi.import_url(openapi_spec_url, target_url)
            time.sleep(5)  # Wait for import

        # Spider the API
        spider_report = self.spider_scan(target_url)

        # Run active scan
        scan_id = self.zap.ascan.scan(target_url, recurse=True)
        logger.info(f"API scan started with ID: {scan_id}")

        # Wait for scan to complete
        while int(self.zap.ascan.status(scan_id)) < 100:
            progress = int(self.zap.ascan.status(scan_id))
            logger.info(f"API scan progress: {progress}%")
            time.sleep(5)

        # Get alerts
        alerts = self._get_alerts(target_url)
        end_time = datetime.utcnow()

        report = ScanReport(
            scan_id=scan_id,
            target_url=target_url,
            scan_type="api",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            status=ScanStatus.COMPLETED,
            alerts=alerts,
            urls_scanned=spider_report.urls_scanned,
            duration_seconds=(end_time - start_time).total_seconds()
        )

        logger.info(f"API scan completed: {len(alerts)} alerts found")
        return report

    def full_scan(
        self,
        target_url: str,
        openapi_spec_url: Optional[str] = None
    ) -> ScanReport:
        """
        Perform comprehensive security scan

        Combines:
        1. Spider scan (discovery)
        2. Passive scan (safe analysis)
        3. Active scan (vulnerability detection)

        Args:
            target_url: URL to scan
            openapi_spec_url: OpenAPI spec URL (for APIs)

        Returns:
            Combined ScanReport
        """
        logger.info(f"Starting full security scan of {target_url}")
        start_time = datetime.utcnow()

        # Step 1: Spider
        logger.info("Step 1/3: Spidering...")
        spider_report = self.spider_scan(target_url)

        # Step 2: Passive scan
        logger.info("Step 2/3: Passive scanning...")
        passive_report = self.passive_scan(target_url, wait_time=30)

        # Step 3: Active scan
        logger.info("Step 3/3: Active scanning...")
        active_report = self.active_scan(target_url)

        # Combine results
        all_alerts = self._deduplicate_alerts(
            passive_report.alerts + active_report.alerts
        )

        end_time = datetime.utcnow()

        report = ScanReport(
            scan_id="full",
            target_url=target_url,
            scan_type="full",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            status=ScanStatus.COMPLETED,
            alerts=all_alerts,
            urls_scanned=spider_report.urls_scanned,
            duration_seconds=(end_time - start_time).total_seconds()
        )

        logger.info(f"Full scan completed: {len(all_alerts)} unique alerts found")
        self._log_summary(report)
        return report

    def _get_alerts(self, base_url: Optional[str] = None) -> List[SecurityAlert]:
        """Get alerts from ZAP"""
        raw_alerts = self.zap.core.alerts(baseurl=base_url)
        alerts = []

        for alert in raw_alerts:
            alerts.append(SecurityAlert(
                alert_id=alert.get('id', ''),
                name=alert.get('alert', ''),
                risk=alert.get('risk', ''),
                confidence=alert.get('confidence', ''),
                description=alert.get('description', ''),
                url=alert.get('url', ''),
                solution=alert.get('solution', ''),
                reference=alert.get('reference', ''),
                cwe_id=int(alert.get('cweid')) if alert.get('cweid') else None,
                wasc_id=int(alert.get('wascid')) if alert.get('wascid') else None,
                evidence=alert.get('evidence', ''),
                attack=alert.get('attack', ''),
                other_info=alert.get('other', '')
            ))

        return alerts

    def _deduplicate_alerts(self, alerts: List[SecurityAlert]) -> List[SecurityAlert]:
        """Remove duplicate alerts"""
        seen: Set[str] = set()
        unique_alerts = []

        for alert in alerts:
            # Create unique key from alert name and URL
            key = f"{alert.name}:{alert.url}"
            if key not in seen:
                seen.add(key)
                unique_alerts.append(alert)

        return unique_alerts

    def _log_summary(self, report: ScanReport):
        """Log scan summary"""
        logger.info("=" * 60)
        logger.info("Security Scan Summary")
        logger.info("=" * 60)
        logger.info(f"Target: {report.target_url}")
        logger.info(f"Duration: {report.duration_seconds:.1f}s")
        logger.info(f"URLs Scanned: {report.urls_scanned}")
        logger.info(f"Total Alerts: {len(report.alerts)}")
        logger.info(f"  High: {report.high_severity_count}")
        logger.info(f"  Medium: {report.medium_severity_count}")
        logger.info(f"  Low: {report.low_severity_count}")
        logger.info(f"  Informational: {report.informational_count}")
        logger.info("=" * 60)

    def generate_html_report(self, report: ScanReport, output_path: str):
        """Generate HTML report"""
        html_report = self.zap.core.htmlreport()
        with open(output_path, 'w') as f:
            f.write(html_report)
        logger.info(f"HTML report saved to {output_path}")

    def generate_json_report(self, report: ScanReport, output_path: str):
        """Generate JSON report"""
        with open(output_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"JSON report saved to {output_path}")

    def clear_session(self):
        """Clear ZAP session"""
        self.zap.core.new_session()
        logger.info("ZAP session cleared")


# ============================================================================
# Convenience Functions
# ============================================================================

def quick_scan(target_url: str, zap_url: str = "http://localhost:8090") -> ScanReport:
    """
    Quick security scan (passive only - safe for production)

    Args:
        target_url: URL to scan
        zap_url: ZAP instance URL

    Returns:
        ScanReport
    """
    scanner = ZAPScanner(zap_url=zap_url)
    return scanner.passive_scan(target_url)


def comprehensive_scan(
    target_url: str,
    zap_url: str = "http://localhost:8090",
    openapi_spec_url: Optional[str] = None
) -> ScanReport:
    """
    Comprehensive security scan (includes active scanning)

    WARNING: Active scanning sends attacks. Only use on systems you own.

    Args:
        target_url: URL to scan
        zap_url: ZAP instance URL
        openapi_spec_url: OpenAPI spec URL (optional)

    Returns:
        ScanReport
    """
    scanner = ZAPScanner(zap_url=zap_url)
    return scanner.full_scan(target_url, openapi_spec_url)


# ============================================================================
# Usage Examples
# ============================================================================

"""
1. Start ZAP in Docker:

   docker run -u zap -p 8090:8090 -i owasp/zap2docker-stable \\
       zap.sh -daemon -host 0.0.0.0 -port 8090 -config api.disablekey=true

2. Run Quick Scan (passive only - safe):

   from security_testing.zap_scanner import quick_scan
   report = quick_scan("http://localhost:8000")
   print(f"Found {report.high_severity_count} high severity issues")

3. Run Comprehensive Scan (includes active attacks):

   from security_testing.zap_scanner import comprehensive_scan
   report = comprehensive_scan(
       "http://localhost:8000",
       openapi_spec_url="http://localhost:8000/openapi.json"
   )

4. Use Scanner Class Directly:

   from security_testing.zap_scanner import ZAPScanner

   scanner = ZAPScanner(zap_url="http://localhost:8090")

   # Spider scan
   spider_report = scanner.spider_scan("http://localhost:8000")

   # Passive scan (safe)
   passive_report = scanner.passive_scan("http://localhost:8000")

   # Active scan (intrusive - only on test systems!)
   active_report = scanner.active_scan("http://localhost:8000")

   # API scan
   api_report = scanner.api_scan(
       "http://localhost:8000",
       openapi_spec_url="http://localhost:8000/openapi.json"
   )

   # Generate reports
   scanner.generate_html_report(api_report, "security_report.html")
   scanner.generate_json_report(api_report, "security_report.json")

5. CI/CD Integration:

   # In your CI/CD pipeline
   report = comprehensive_scan("http://staging.example.com")

   # Fail build if high severity issues found
   if report.high_severity_count > 0:
       print(f"FAILED: Found {report.high_severity_count} high severity issues")
       exit(1)

   # Warn on medium severity
   if report.medium_severity_count > 5:
       print(f"WARNING: Found {report.medium_severity_count} medium severity issues")

Expected Results:
- Passive scan: 0-5 findings (mostly informational)
- Active scan on secure API: 0-2 findings (configuration recommendations)
- Active scan on unsecured API: Multiple findings requiring fixes

Common Findings:
- Missing security headers (X-Frame-Options, CSP, etc.)
- SQL injection vulnerabilities
- XSS vulnerabilities
- Authentication/session issues
- CSRF protection missing
- Sensitive data exposure
"""
