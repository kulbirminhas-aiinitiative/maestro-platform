"""
Report Generator Module
=======================

Generates audit reports in various formats (PDF, HTML, JSON).
Provides templates and notifications for audit findings.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import html


class ReportFormat(Enum):
    """Supported report formats."""
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class AuditFinding:
    """Individual audit finding."""
    id: str
    rule_id: str
    rule_name: str
    severity: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class AuditSummary:
    """Summary statistics for an audit."""
    total_rules_evaluated: int = 0
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    pass_rate: float = 0.0

    @classmethod
    def from_findings(cls, findings: List[AuditFinding], total_rules: int) -> 'AuditSummary':
        """Create summary from list of findings."""
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }

        for finding in findings:
            sev = finding.severity.lower()
            if sev in severity_counts:
                severity_counts[sev] += 1

        passed = total_rules - len(findings)
        pass_rate = (passed / total_rules * 100) if total_rules > 0 else 100.0

        return cls(
            total_rules_evaluated=total_rules,
            total_findings=len(findings),
            critical_count=severity_counts["critical"],
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
            info_count=severity_counts["info"],
            pass_rate=round(pass_rate, 2)
        )


@dataclass
class AuditReport:
    """Complete audit report."""
    id: str
    audit_id: str
    title: str
    target_name: str
    target_type: str
    generated_at: str
    audit_started_at: str
    audit_completed_at: str
    summary: AuditSummary
    findings: List[AuditFinding]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "id": self.id,
            "audit_id": self.audit_id,
            "title": self.title,
            "target": {
                "name": self.target_name,
                "type": self.target_type
            },
            "generated_at": self.generated_at,
            "audit_started_at": self.audit_started_at,
            "audit_completed_at": self.audit_completed_at,
            "summary": asdict(self.summary),
            "findings": [asdict(f) for f in self.findings],
            "metadata": self.metadata
        }


class TemplateEngine:
    """Simple template engine for report generation."""

    def __init__(self):
        self.templates: Dict[str, str] = {
            "html_report": self._get_html_template(),
            "markdown_report": self._get_markdown_template(),
        }

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with context."""
        template = self.templates.get(template_name, "")
        return self._substitute(template, context)

    def _substitute(self, template: str, context: Dict[str, Any]) -> str:
        """Substitute placeholders in template."""
        result = template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            result = result.replace(placeholder, str(value))
        return result

    def _get_html_template(self) -> str:
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary { background: #ecf0f1; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
        .stat { text-align: center; padding: 15px; background: white; border-radius: 5px; }
        .stat-value { font-size: 24px; font-weight: bold; }
        .stat-label { color: #7f8c8d; font-size: 12px; }
        .critical { color: #e74c3c; }
        .high { color: #e67e22; }
        .medium { color: #f1c40f; }
        .low { color: #3498db; }
        .finding { border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }
        .finding-header { display: flex; justify-content: space-between; align-items: center; }
        .severity-badge { padding: 3px 10px; border-radius: 3px; color: white; font-size: 12px; }
        .severity-critical { background: #e74c3c; }
        .severity-high { background: #e67e22; }
        .severity-medium { background: #f1c40f; color: #333; }
        .severity-low { background: #3498db; }
        .evidence { background: #f8f9fa; padding: 10px; margin-top: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; }
        .remediation { background: #e8f6e8; padding: 10px; margin-top: 10px; border-radius: 4px; border-left: 3px solid #27ae60; }
        .meta { color: #7f8c8d; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>{{title}}</h1>
    <p>Target: <strong>{{target_name}}</strong> ({{target_type}})</p>
    <p class="meta">Generated: {{generated_at}} | Audit: {{audit_started_at}} - {{audit_completed_at}}</p>

    <div class="summary">
        <h2>Summary</h2>
        <div class="summary-grid">
            <div class="stat">
                <div class="stat-value">{{total_rules}}</div>
                <div class="stat-label">Rules Evaluated</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{pass_rate}}%</div>
                <div class="stat-label">Pass Rate</div>
            </div>
            <div class="stat">
                <div class="stat-value critical">{{critical_count}}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat">
                <div class="stat-value high">{{high_count}}</div>
                <div class="stat-label">High</div>
            </div>
        </div>
    </div>

    <h2>Findings ({{total_findings}})</h2>
    {{findings_html}}

    <p class="meta">Report ID: {{report_id}} | Audit ID: {{audit_id}}</p>
</body>
</html>'''

    def _get_markdown_template(self) -> str:
        return '''# {{title}}

**Target:** {{target_name}} ({{target_type}})
**Generated:** {{generated_at}}
**Audit Period:** {{audit_started_at}} - {{audit_completed_at}}

## Summary

| Metric | Value |
|--------|-------|
| Rules Evaluated | {{total_rules}} |
| Pass Rate | {{pass_rate}}% |
| Critical Findings | {{critical_count}} |
| High Findings | {{high_count}} |
| Medium Findings | {{medium_count}} |
| Low Findings | {{low_count}} |

## Findings

{{findings_markdown}}

---
*Report ID: {{report_id}} | Audit ID: {{audit_id}}*
'''


class ReportGenerator:
    """
    Generates audit reports in various formats.

    Supports PDF, HTML, JSON, and Markdown output formats.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("/tmp/audit-reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_engine = TemplateEngine()

    def generate(
        self,
        report: AuditReport,
        format: ReportFormat = ReportFormat.HTML,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate a report in the specified format.

        Args:
            report: The audit report to generate
            format: Output format (PDF, HTML, JSON, Markdown)
            output_path: Optional custom output path

        Returns:
            Path to the generated report
        """
        if output_path is None:
            filename = f"audit_report_{report.id}.{format.value}"
            output_path = self.output_dir / filename

        if format == ReportFormat.JSON:
            content = self._generate_json(report)
        elif format == ReportFormat.HTML:
            content = self._generate_html(report)
        elif format == ReportFormat.MARKDOWN:
            content = self._generate_markdown(report)
        elif format == ReportFormat.PDF:
            # For PDF, generate HTML first then convert
            content = self._generate_html(report)
            output_path = output_path.with_suffix('.html')
            # PDF conversion would require external library like weasyprint

        with open(output_path, 'w') as f:
            f.write(content)

        return output_path

    def _generate_json(self, report: AuditReport) -> str:
        """Generate JSON format report."""
        return json.dumps(report.to_dict(), indent=2, default=str)

    def _generate_html(self, report: AuditReport) -> str:
        """Generate HTML format report."""
        # Generate findings HTML
        findings_html = ""
        for finding in report.findings:
            severity_class = f"severity-{finding.severity.lower()}"
            evidence_html = ""
            if finding.evidence:
                evidence_json = json.dumps(finding.evidence, indent=2)
                evidence_html = f'<div class="evidence"><pre>{html.escape(evidence_json)}</pre></div>'

            remediation_html = ""
            if finding.remediation:
                remediation_html = f'<div class="remediation"><strong>Remediation:</strong> {html.escape(finding.remediation)}</div>'

            findings_html += f'''
            <div class="finding">
                <div class="finding-header">
                    <strong>{html.escape(finding.rule_name)}</strong>
                    <span class="severity-badge {severity_class}">{finding.severity.upper()}</span>
                </div>
                <p>{html.escape(finding.description)}</p>
                {evidence_html}
                {remediation_html}
            </div>
            '''

        context = {
            "title": report.title,
            "target_name": report.target_name,
            "target_type": report.target_type,
            "generated_at": report.generated_at,
            "audit_started_at": report.audit_started_at,
            "audit_completed_at": report.audit_completed_at,
            "total_rules": report.summary.total_rules_evaluated,
            "pass_rate": report.summary.pass_rate,
            "critical_count": report.summary.critical_count,
            "high_count": report.summary.high_count,
            "medium_count": report.summary.medium_count,
            "low_count": report.summary.low_count,
            "total_findings": report.summary.total_findings,
            "findings_html": findings_html,
            "report_id": report.id,
            "audit_id": report.audit_id
        }

        return self.template_engine.render("html_report", context)

    def _generate_markdown(self, report: AuditReport) -> str:
        """Generate Markdown format report."""
        # Generate findings markdown
        findings_md = ""
        for i, finding in enumerate(report.findings, 1):
            findings_md += f'''
### {i}. {finding.rule_name} [{finding.severity.upper()}]

**Rule ID:** {finding.rule_id}

{finding.description}

'''
            if finding.evidence:
                findings_md += f'''**Evidence:**
```json
{json.dumps(finding.evidence, indent=2)}
```

'''
            if finding.remediation:
                findings_md += f'''**Remediation:** {finding.remediation}

'''

        context = {
            "title": report.title,
            "target_name": report.target_name,
            "target_type": report.target_type,
            "generated_at": report.generated_at,
            "audit_started_at": report.audit_started_at,
            "audit_completed_at": report.audit_completed_at,
            "total_rules": report.summary.total_rules_evaluated,
            "pass_rate": report.summary.pass_rate,
            "critical_count": report.summary.critical_count,
            "high_count": report.summary.high_count,
            "medium_count": report.summary.medium_count,
            "low_count": report.summary.low_count,
            "total_findings": report.summary.total_findings,
            "findings_markdown": findings_md,
            "report_id": report.id,
            "audit_id": report.audit_id
        }

        return self.template_engine.render("markdown_report", context)

    def create_report(
        self,
        audit_id: str,
        target_name: str,
        target_type: str,
        findings: List[Dict[str, Any]],
        total_rules: int,
        audit_started: datetime,
        audit_completed: datetime,
        title: Optional[str] = None
    ) -> AuditReport:
        """
        Create an AuditReport from audit results.

        Args:
            audit_id: ID of the audit
            target_name: Name of the audited target
            target_type: Type of the audited target
            findings: List of finding dictionaries
            total_rules: Total number of rules evaluated
            audit_started: When the audit started
            audit_completed: When the audit completed
            title: Optional custom title

        Returns:
            AuditReport object
        """
        import uuid

        # Convert dictionaries to AuditFinding objects
        finding_objects = [
            AuditFinding(
                id=f.get('id', str(uuid.uuid4())),
                rule_id=f.get('rule_id', 'unknown'),
                rule_name=f.get('rule_name', 'Unknown Rule'),
                severity=f.get('severity', 'medium'),
                description=f.get('description', ''),
                evidence=f.get('evidence', {}),
                remediation=f.get('remediation', ''),
                timestamp=f.get('timestamp', datetime.utcnow().isoformat())
            )
            for f in findings
        ]

        summary = AuditSummary.from_findings(finding_objects, total_rules)

        return AuditReport(
            id=str(uuid.uuid4()),
            audit_id=audit_id,
            title=title or f"Compliance Audit Report - {target_name}",
            target_name=target_name,
            target_type=target_type,
            generated_at=datetime.utcnow().isoformat(),
            audit_started_at=audit_started.isoformat(),
            audit_completed_at=audit_completed.isoformat(),
            summary=summary,
            findings=finding_objects
        )
