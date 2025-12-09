#!/usr/bin/env python3
"""
License Reporter: Generate license compliance reports.

Creates comprehensive license reports for audits and compliance reviews.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .license_scanner import LicenseScanner, ScanResult, LicenseRisk

logger = logging.getLogger(__name__)


@dataclass
class LicenseReport:
    """A license compliance report."""
    id: str
    project_id: str
    generated_at: str
    scan_result: ScanResult
    compliance_rate: float
    risk_summary: Dict[str, int]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['scan_result'] = self.scan_result.to_dict()
        return data


class LicenseReporter:
    """Generates license compliance reports."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        scanner: Optional[LicenseScanner] = None
    ):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'reports'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scanner = scanner or LicenseScanner()
        self._report_counter = 0

    def generate_report(
        self,
        project_path: str,
        project_id: Optional[str] = None,
        include_dev: bool = False
    ) -> LicenseReport:
        """Generate a license compliance report."""
        # Run scan
        result = self.scanner.scan(project_path, project_id, include_dev)

        # Calculate compliance rate
        total = len(result.packages)
        compliant = sum(1 for p in result.packages if p.risk_level == LicenseRisk.ALLOWED)
        compliance_rate = (compliant / total * 100) if total > 0 else 100.0

        # Risk summary
        risk_summary = {
            'allowed': sum(1 for p in result.packages if p.risk_level == LicenseRisk.ALLOWED),
            'restricted': sum(1 for p in result.packages if p.risk_level == LicenseRisk.RESTRICTED),
            'banned': sum(1 for p in result.packages if p.risk_level == LicenseRisk.BANNED),
            'unknown': sum(1 for p in result.packages if p.risk_level == LicenseRisk.UNKNOWN)
        }

        # Generate recommendations
        recommendations = []
        if risk_summary['banned'] > 0:
            recommendations.append("CRITICAL: Remove or replace banned license packages immediately")
        if risk_summary['restricted'] > 0:
            recommendations.append("HIGH: Request approval for restricted license packages")
        if risk_summary['unknown'] > 0:
            recommendations.append("MEDIUM: Review and classify unknown licenses")
        if compliance_rate < 100:
            recommendations.append(f"Target: Achieve 100% license compliance (current: {compliance_rate:.1f}%)")

        self._report_counter += 1
        report_id = f"LIC-RPT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._report_counter:04d}"

        report = LicenseReport(
            id=report_id,
            project_id=result.project_id,
            generated_at=datetime.utcnow().isoformat(),
            scan_result=result,
            compliance_rate=compliance_rate,
            risk_summary=risk_summary,
            recommendations=recommendations
        )

        # Save report
        output_file = self.output_dir / f"{report_id}.json"
        with open(output_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Generated license report: {report_id} ({compliance_rate:.1f}% compliant)")

        return report

    def generate_html_report(self, report: LicenseReport) -> str:
        """Generate HTML version of report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>License Compliance Report - {report.project_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #333; color: white; padding: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; margin: 20px 0; }}
        .critical {{ color: #d32f2f; }}
        .warning {{ color: #f57c00; }}
        .success {{ color: #388e3c; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #333; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>License Compliance Report</h1>
        <p>Project: {report.project_id} | Generated: {report.generated_at}</p>
    </div>
    <div class="summary">
        <h2>Summary</h2>
        <p>Compliance Rate: <strong class="{'success' if report.compliance_rate >= 95 else 'warning'}">{report.compliance_rate:.1f}%</strong></p>
        <p>Packages Scanned: {report.scan_result.packages_scanned}</p>
        <p>Violations: {len(report.scan_result.violations)}</p>
    </div>
    <h2>Risk Distribution</h2>
    <ul>
        <li class="success">Allowed: {report.risk_summary['allowed']}</li>
        <li class="warning">Restricted: {report.risk_summary['restricted']}</li>
        <li class="critical">Banned: {report.risk_summary['banned']}</li>
        <li>Unknown: {report.risk_summary['unknown']}</li>
    </ul>
    <h2>Recommendations</h2>
    <ul>
        {''.join(f'<li>{r}</li>' for r in report.recommendations)}
    </ul>
</body>
</html>"""

        output_file = self.output_dir / f"{report.id}.html"
        with open(output_file, 'w') as f:
            f.write(html)

        return str(output_file)


def get_license_reporter(**kwargs) -> LicenseReporter:
    """Get license reporter instance."""
    return LicenseReporter(**kwargs)
