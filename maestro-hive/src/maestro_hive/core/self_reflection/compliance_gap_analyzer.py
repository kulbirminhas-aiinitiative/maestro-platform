#!/usr/bin/env python3
"""
Compliance Gap Analyzer

Focuses specifically on Capability 7: Compliance & Governance
to validate gaps and create JIRA tickets for remediation.

Usage:
    python compliance_gap_analyzer.py --dry-run    # Preview
    python compliance_gap_analyzer.py              # Create tickets
"""

import json
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import requests
from base64 import b64encode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ComplianceGap:
    """A compliance gap finding"""
    gap_id: str
    category: str
    sub_category: str
    description: str
    current_state: str
    target_state: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    remediation: str
    related_standards: List[str]


# Comprehensive Compliance Requirements for 95% Maturity
COMPLIANCE_REQUIREMENTS = {
    "jira_sync": {
        "name": "JIRA Synchronization",
        "target": 95,
        "current": 90,
        "checks": [
            ("jira_bidirectional_sync", "Bidirectional sync between platform and JIRA", "services/integration/adapters/jira_adapter.py"),
            ("jira_webhook_handler", "Webhook handler for real-time JIRA updates", "services/integration/webhooks/"),
            ("jira_field_mapping", "Complete field mapping configuration", "config/jira_field_mapping.json"),
        ]
    },
    "confluence_reporting": {
        "name": "Confluence Reporting",
        "target": 95,
        "current": 90,
        "checks": [
            ("confluence_auto_publish", "Automated report publishing to Confluence", "services/integration/adapters/confluence_adapter.py"),
            ("confluence_templates", "Standardized report templates", "templates/confluence/"),
            ("confluence_versioning", "Document versioning and history", "services/integration/confluence_versioning.py"),
        ]
    },
    "audit_trails": {
        "name": "Audit Trails & Logging",
        "target": 95,
        "current": 80,
        "checks": [
            ("audit_logger", "Centralized audit logging service", "src/maestro_hive/compliance/audit_logger.py"),
            ("audit_immutability", "Immutable audit log storage", "src/maestro_hive/compliance/immutable_store.py"),
            ("audit_search", "Searchable audit log interface", "src/maestro_hive/compliance/audit_search.py"),
            ("audit_retention", "Configurable retention policies", "config/audit_retention.yaml"),
        ]
    },
    "policy_enforcement": {
        "name": "Policy Enforcement",
        "target": 95,
        "current": 60,
        "checks": [
            ("policy_engine", "Policy definition and enforcement engine", "src/maestro_hive/compliance/policy_enforcer.py"),
            ("policy_rules", "Configurable policy rules", "config/policies/"),
            ("policy_violations", "Policy violation detection and alerting", "src/maestro_hive/compliance/violation_detector.py"),
            ("policy_exceptions", "Exception handling workflow", "src/maestro_hive/compliance/exception_handler.py"),
        ]
    },
    "license_checking": {
        "name": "License Compliance",
        "target": 95,
        "current": 20,
        "checks": [
            ("license_scanner", "Open source license scanner (FOSSA/Snyk)", "src/maestro_hive/compliance/license_scanner.py"),
            ("license_policy", "License policy definitions", "config/license_policy.yaml"),
            ("license_report", "License compliance report generator", "src/maestro_hive/compliance/license_reporter.py"),
            ("sbom_generator", "Software Bill of Materials generator", "src/maestro_hive/compliance/sbom_generator.py"),
        ]
    },
    "access_control": {
        "name": "Access Control (RBAC)",
        "target": 95,
        "current": 50,
        "checks": [
            ("rbac_engine", "Role-based access control engine", "src/maestro_hive/compliance/rbac_engine.py"),
            ("rbac_roles", "Role definitions and permissions", "config/rbac_roles.yaml"),
            ("rbac_audit", "Access audit logging", "src/maestro_hive/compliance/access_audit.py"),
            ("rbac_api", "RBAC API for runtime checks", "src/maestro_hive/api/rbac_api.py"),
        ]
    },
    "cost_estimation": {
        "name": "Cost Tracking & Estimation",
        "target": 95,
        "current": 10,
        "checks": [
            ("cost_tracker", "Token and API cost tracking", "src/maestro_hive/compliance/cost_tracker.py"),
            ("cost_budget", "Budget limits and alerts", "src/maestro_hive/compliance/budget_manager.py"),
            ("cost_report", "Cost reporting and analytics", "src/maestro_hive/compliance/cost_reporter.py"),
            ("cost_allocation", "Cost allocation by project/team", "src/maestro_hive/compliance/cost_allocator.py"),
        ]
    },
    "risk_assessment": {
        "name": "Risk Assessment",
        "target": 95,
        "current": 40,
        "checks": [
            ("risk_scorer", "Automated risk scoring engine", "src/maestro_hive/compliance/risk_scorer.py"),
            ("risk_factors", "Risk factor definitions", "config/risk_factors.yaml"),
            ("risk_dashboard", "Risk dashboard and reporting", "src/maestro_hive/compliance/risk_dashboard.py"),
            ("risk_mitigation", "Risk mitigation tracking", "src/maestro_hive/compliance/risk_mitigation.py"),
        ]
    },
    "standardization": {
        "name": "Standards & Templates",
        "target": 95,
        "current": 70,
        "checks": [
            ("coding_standards", "Coding standards enforcement", "config/coding_standards.yaml"),
            ("template_library", "Standard template library", "templates/standards/"),
            ("style_checker", "Automated style checking", "src/maestro_hive/compliance/style_checker.py"),
        ]
    },
    "approval_workflows": {
        "name": "Approval Workflows",
        "target": 95,
        "current": 50,
        "checks": [
            ("approval_engine", "Configurable approval workflow engine", "src/maestro_hive/compliance/approval_engine.py"),
            ("approval_rules", "Approval rules by type/risk", "config/approval_rules.yaml"),
            ("approval_notifications", "Approval request notifications", "src/maestro_hive/compliance/approval_notifier.py"),
            ("approval_audit", "Approval decision audit trail", "src/maestro_hive/compliance/approval_audit.py"),
        ]
    }
}

# Related compliance standards
COMPLIANCE_STANDARDS = {
    "SOC2": ["audit_trails", "access_control", "risk_assessment"],
    "GDPR": ["audit_trails", "access_control", "policy_enforcement"],
    "EU_AI_ACT": ["audit_trails", "risk_assessment", "policy_enforcement"],
    "ISO27001": ["access_control", "audit_trails", "policy_enforcement", "risk_assessment"],
    "HIPAA": ["audit_trails", "access_control", "policy_enforcement"],
}


class ComplianceGapAnalyzer:
    """Analyzes compliance gaps against 95% maturity target"""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.gaps: List[ComplianceGap] = []

    def scan(self) -> List[ComplianceGap]:
        """Scan for all compliance gaps"""
        logger.info("Starting Compliance Gap Analysis...")
        self.gaps = []

        for req_id, req_config in COMPLIANCE_REQUIREMENTS.items():
            logger.info(f"  Checking: {req_config['name']}")

            current = req_config["current"]
            target = req_config["target"]
            gap_percentage = target - current

            if gap_percentage <= 0:
                continue  # Already at or above target

            # Determine severity based on gap size
            if gap_percentage >= 50:
                severity = "CRITICAL"
            elif gap_percentage >= 30:
                severity = "HIGH"
            elif gap_percentage >= 15:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            # Check each sub-requirement
            for check_id, check_desc, check_path in req_config["checks"]:
                full_path = self.workspace_root / check_path

                # Check if file/directory exists
                exists = full_path.exists()

                if not exists:
                    # Find related standards
                    related = [std for std, reqs in COMPLIANCE_STANDARDS.items() if req_id in reqs]

                    gap = ComplianceGap(
                        gap_id=f"COMPLY-{req_id.upper()}-{check_id.upper()}",
                        category="Compliance & Governance",
                        sub_category=req_config["name"],
                        description=f"Missing: {check_desc}",
                        current_state=f"{current}% - File/module not found: {check_path}",
                        target_state=f"{target}% - Full implementation required",
                        severity=severity,
                        remediation=f"Implement {check_desc} at {check_path}",
                        related_standards=related
                    )
                    self.gaps.append(gap)

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        self.gaps.sort(key=lambda g: severity_order.get(g.severity, 4))

        return self.gaps

    def generate_report(self) -> str:
        """Generate text report"""
        lines = [
            "=" * 70,
            "COMPLIANCE GAP ANALYSIS REPORT",
            "=" * 70,
            f"Analysis Date: {datetime.now().isoformat()}",
            f"Workspace: {self.workspace_root}",
            f"Target Maturity: 95%",
            "",
            "CURRENT STATE SUMMARY",
            "-" * 40,
        ]

        total_current = 0
        total_target = 0
        for req_id, req_config in COMPLIANCE_REQUIREMENTS.items():
            lines.append(f"  {req_config['name']}: {req_config['current']}% -> {req_config['target']}%")
            total_current += req_config['current']
            total_target += req_config['target']

        avg_current = total_current / len(COMPLIANCE_REQUIREMENTS)
        lines.extend([
            "",
            f"  OVERALL: {avg_current:.0f}% -> 95%",
            "",
            f"GAPS IDENTIFIED: {len(self.gaps)}",
            "-" * 40,
        ])

        # Group by severity
        by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for gap in self.gaps:
            by_severity[gap.severity].append(gap)

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            gaps = by_severity[severity]
            if gaps:
                lines.append(f"\n{severity} ({len(gaps)}):")
                for gap in gaps:
                    lines.append(f"  [{gap.gap_id}] {gap.description}")
                    lines.append(f"    Remediation: {gap.remediation}")
                    if gap.related_standards:
                        lines.append(f"    Standards: {', '.join(gap.related_standards)}")

        lines.extend([
            "",
            "=" * 70,
            "END OF REPORT",
            "=" * 70,
        ])

        return "\n".join(lines)


class ComplianceGapToJira:
    """Creates JIRA tickets for compliance gaps"""

    CONFIG_FILE = "/home/ec2-user/projects/maestro-frontend-production/.jira-config"

    def __init__(self, parent_epic: str = None):
        self.parent_epic = parent_epic or "MD-2633"  # Compliance & Governance Gaps EPIC
        self._load_config()

    def _load_config(self):
        config_values = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config_values[key.strip()] = value.strip()

        self.base_url = config_values.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net')
        self.email = config_values.get('JIRA_EMAIL', '')
        self.api_token = config_values.get('JIRA_API_TOKEN', '')
        self.project_key = config_values.get('JIRA_PROJECT_KEY', 'MD')

        auth = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def search_existing(self, gap_id: str) -> bool:
        """Check if ticket already exists for this gap"""
        url = f"{self.base_url}/rest/api/3/search/jql"
        payload = {
            "jql": f'project = {self.project_key} AND summary ~ "{gap_id}"',
            "maxResults": 1
        }

        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return len(response.json().get("issues", [])) > 0
        return False

    def create_ticket(self, gap: ComplianceGap, dry_run: bool = False) -> Optional[str]:
        """Create JIRA ticket for a compliance gap"""

        summary = f"[{gap.gap_id}] {gap.description}"

        # Build rich description
        description = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Compliance Gap Details"}]
                },
                {
                    "type": "table",
                    "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
                    "content": [
                        {"type": "tableRow", "content": [
                            {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Field"}]}]},
                            {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Value"}]}]}
                        ]},
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Category"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.sub_category}]}]}
                        ]},
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Severity"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.severity}]}]}
                        ]},
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Current State"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.current_state}]}]}
                        ]},
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Target State"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.target_state}]}]}
                        ]},
                    ]
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Remediation"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": gap.remediation}]
                },
            ]
        }

        # Add related standards if any
        if gap.related_standards:
            description["content"].append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Related Compliance Standards"}]
            })
            description["content"].append({
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": std}]}]}
                    for std in gap.related_standards
                ]
            })

        # Map severity to priority
        priority_map = {"CRITICAL": "Highest", "HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}

        labels = [
            "compliance",
            "gap-detector",
            "auto-generated",
            f"severity-{gap.severity.lower()}",
            gap.sub_category.lower().replace(" ", "-").replace("&", "and")
        ]

        if dry_run:
            logger.info(f"[DRY RUN] Would create: {summary}")
            logger.info(f"  Priority: {priority_map.get(gap.severity, 'Medium')}")
            logger.info(f"  Labels: {labels}")
            return f"DRY-RUN-{gap.gap_id}"

        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Story"},  # Stories can have EPIC as parent
                "priority": {"name": priority_map.get(gap.severity, "Medium")},
                "labels": labels,
                "parent": {"key": self.parent_epic}  # EPIC parent
            }
        }

        url = f"{self.base_url}/rest/api/3/issue"
        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 201:
            key = response.json().get("key")
            logger.info(f"Created: {key} - {summary[:50]}...")
            return key
        else:
            logger.error(f"Failed to create ticket: {response.status_code} - {response.text[:200]}")
            return None

    def process_gaps(self, gaps: List[ComplianceGap], dry_run: bool = False) -> Dict[str, Any]:
        """Process all compliance gaps"""
        results = {
            "total_gaps": len(gaps),
            "tickets_created": 0,
            "tickets_skipped": 0,
            "tickets_failed": 0,
            "created_keys": [],
            "skipped": [],
        }

        for gap in gaps:
            # Check for existing
            if self.search_existing(gap.gap_id):
                results["tickets_skipped"] += 1
                results["skipped"].append(gap.gap_id)
                logger.info(f"Skipping {gap.gap_id} - ticket already exists")
                continue

            key = self.create_ticket(gap, dry_run=dry_run)
            if key:
                results["tickets_created"] += 1
                results["created_keys"].append(key)
            else:
                results["tickets_failed"] += 1

        return results


def main():
    parser = argparse.ArgumentParser(description="Compliance Gap Analyzer")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating tickets")
    parser.add_argument("--workspace", default="/home/ec2-user/projects/maestro-platform/maestro-hive")
    parser.add_argument("--parent-epic", default="MD-2633", help="Parent EPIC for compliance gaps")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    # Run gap analysis
    analyzer = ComplianceGapAnalyzer(args.workspace)
    gaps = analyzer.scan()

    # Print report
    print(analyzer.generate_report())

    if not gaps:
        logger.info("No compliance gaps found!")
        return

    # Create JIRA tickets
    jira = ComplianceGapToJira(parent_epic=args.parent_epic)
    results = jira.process_gaps(gaps, dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("JIRA TICKET SUMMARY")
    print("=" * 60)
    print(f"Total gaps:       {results['total_gaps']}")
    print(f"Tickets created:  {results['tickets_created']}")
    print(f"Tickets skipped:  {results['tickets_skipped']}")
    print(f"Tickets failed:   {results['tickets_failed']}")

    if results["created_keys"]:
        print(f"\nCreated: {', '.join(results['created_keys'])}")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                "gaps": [asdict(g) for g in gaps],
                "results": results
            }, f, indent=2)
        logger.info(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
