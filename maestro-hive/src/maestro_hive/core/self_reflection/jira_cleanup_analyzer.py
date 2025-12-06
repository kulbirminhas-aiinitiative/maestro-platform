#!/usr/bin/env python3
"""
JIRA Cleanup Analyzer: Identify Misaligned Tickets

Compares existing JIRA tickets against the maturity roadmap
to identify orphaned, duplicate, or misaligned tickets.

Usage:
    python jira_cleanup_analyzer.py                    # Full analysis
    python jira_cleanup_analyzer.py --output report.json  # Save to file
    python jira_cleanup_analyzer.py --auto-close      # Close orphaned tickets (careful!)
"""

import json
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import requests
from base64 import b64encode
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class JiraConfig:
    """JIRA configuration"""
    base_url: str
    email: str
    api_token: str
    project_key: str

    CONFIG_FILE = "/home/ec2-user/projects/maestro-frontend-production/.jira-config"

    @classmethod
    def from_env(cls) -> 'JiraConfig':
        config_values = {}
        if os.path.exists(cls.CONFIG_FILE):
            with open(cls.CONFIG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config_values[key.strip()] = value.strip()

        return cls(
            base_url=config_values.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'),
            email=config_values.get('JIRA_EMAIL', ''),
            api_token=config_values.get('JIRA_API_TOKEN', ''),
            project_key=config_values.get('JIRA_PROJECT_KEY', 'MD')
        )


@dataclass
class TicketAnalysis:
    """Analysis result for a single ticket"""
    key: str
    summary: str
    issue_type: str
    status: str
    created: str
    updated: str
    labels: List[str]
    parent_key: Optional[str]

    # Analysis results
    alignment_status: str = "UNKNOWN"  # ALIGNED, MISALIGNED, ORPHANED, DUPLICATE, STALE
    aligned_capability: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    recommendation: str = ""


# Keywords mapping to capabilities
CAPABILITY_KEYWORDS = {
    "cap1.orchestration": [
        "orchestr", "workflow", "dag", "state", "rollback", "parallel",
        "scheduling", "lifecycle", "event bus", "async", "execution engine"
    ],
    "cap2.team_management": [
        "team", "persona", "agent", "collaborat", "role", "skill",
        "composition", "conflict", "scaling", "context sharing"
    ],
    "cap3.requirements": [
        "requirement", "jira", "decompos", "acceptance criteria", "story",
        "epic", "ambiguity", "feasibility", "priorit", "traceability"
    ],
    "cap4.code_generation": [
        "code gen", "codegen", "scaffold", "template", "refactor",
        "implementation", "security", "api design", "schema"
    ],
    "cap5.quality_assurance": [
        "test", "qa", "quality", "bdv", "acc", "dde", "coverage",
        "validation", "bug", "regression", "security scan"
    ],
    "cap6.knowledge_learning": [
        "rag", "vector", "knowledge", "learning", "embedding", "pattern",
        "feedback", "ml", "ai", "context retrieval"
    ],
    "cap7.compliance": [
        "compliance", "governance", "audit", "policy", "license",
        "gdpr", "eu ai act", "cost", "risk", "rbac", "access control"
    ],
    "cap8.devops": [
        "devops", "cicd", "ci/cd", "terraform", "docker", "kubernetes",
        "monitoring", "prometheus", "grafana", "deploy", "infrastructure"
    ],
    "cap9.self_reflection": [
        "self-reflect", "gap", "health", "anomaly", "self-heal",
        "improvement", "optimization", "metric"
    ],
    "cap10.user_interface": [
        "ui", "cli", "dashboard", "frontend", "interface", "notification",
        "interactive", "onboarding", "ux"
    ]
}

# Keywords that indicate deprecated/old approaches
DEPRECATED_KEYWORDS = [
    "deprecated", "old", "legacy", "v1", "backup", "archive",
    "experimental", "poc", "prototype", "sunday_com"
]

# Keywords for platform foundation (always relevant)
FOUNDATION_KEYWORDS = [
    "foundry", "platform", "core", "infrastructure", "gateway",
    "authentication", "mib", "block", "registry"
]


class JiraCleanupAnalyzer:
    """Analyzes JIRA tickets for alignment with maturity roadmap"""

    def __init__(self, config: JiraConfig):
        self.config = config
        self._auth = b64encode(f"{config.email}:{config.api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {self._auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Load registry for capability reference
        self.registry = self._load_registry()

        # Track analysis results
        self.epics: List[TicketAnalysis] = []
        self.tickets: List[TicketAnalysis] = []
        self.summary: Dict[str, Any] = {}

    def _load_registry(self) -> Dict[str, Any]:
        """Load the capability registry"""
        registry_path = Path(__file__).parent / "registry.json"
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                return json.load(f)
        return {"blocks": []}

    def _api_url(self, endpoint: str) -> str:
        return f"{self.config.base_url}/rest/api/3/{endpoint}"

    def fetch_all_issues(self, issue_type: str = None) -> List[Dict[str, Any]]:
        """Fetch all issues from JIRA using cursor-based pagination"""
        all_issues = []
        next_page_token = None
        max_results = 100

        jql = f"project = {self.config.project_key}"
        if issue_type:
            jql += f" AND issuetype = '{issue_type}'"
        jql += " ORDER BY created DESC"

        while True:
            url = self._api_url("search/jql")
            payload = {
                "jql": jql,
                "maxResults": max_results,
                "fields": ["summary", "status", "issuetype", "labels", "created", "updated", "parent", "description"]
            }

            if next_page_token:
                payload["nextPageToken"] = next_page_token

            response = requests.post(url, headers=self._headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Failed to fetch issues: {response.status_code} - {response.text[:200]}")
                break

            data = response.json()
            issues = data.get("issues", [])
            all_issues.extend(issues)

            logger.info(f"  Fetched {len(all_issues)} issues so far...")

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return all_issues

    def _match_capability(self, text: str) -> Tuple[Optional[str], float]:
        """Match text to a capability, return capability and confidence score"""
        text_lower = text.lower()
        best_match = None
        best_score = 0

        for cap_id, keywords in CAPABILITY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_match = cap_id

        # Normalize score (0-1)
        confidence = min(best_score / 3, 1.0) if best_score > 0 else 0
        return best_match, confidence

    def _is_deprecated(self, text: str, labels: List[str]) -> bool:
        """Check if ticket appears deprecated"""
        text_lower = text.lower()
        labels_lower = [l.lower() for l in labels]

        for kw in DEPRECATED_KEYWORDS:
            if kw in text_lower or kw in labels_lower:
                return True
        return False

    def _is_foundation(self, text: str, labels: List[str]) -> bool:
        """Check if ticket is foundational (always relevant)"""
        text_lower = text.lower()
        labels_lower = [l.lower() for l in labels]

        for kw in FOUNDATION_KEYWORDS:
            if kw in text_lower or any(kw in l for l in labels_lower):
                return True
        return False

    def _is_stale(self, updated: str, days_threshold: int = 90) -> bool:
        """Check if ticket is stale (not updated recently)"""
        try:
            updated_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            age = (datetime.now(updated_date.tzinfo) - updated_date).days
            return age > days_threshold
        except:
            return False

    def analyze_ticket(self, issue: Dict[str, Any]) -> TicketAnalysis:
        """Analyze a single ticket for alignment"""
        fields = issue.get("fields", {})

        analysis = TicketAnalysis(
            key=issue["key"],
            summary=fields.get("summary", ""),
            issue_type=fields.get("issuetype", {}).get("name", ""),
            status=fields.get("status", {}).get("name", ""),
            created=fields.get("created", ""),
            updated=fields.get("updated", ""),
            labels=fields.get("labels", []),
            parent_key=fields.get("parent", {}).get("key") if fields.get("parent") else None
        )

        # Combine summary and description for analysis
        description = fields.get("description")
        desc_text = ""
        if description and isinstance(description, dict):
            # ADF format
            content = description.get("content", [])
            for block in content:
                if block.get("type") == "paragraph":
                    for item in block.get("content", []):
                        if item.get("type") == "text":
                            desc_text += item.get("text", "") + " "
        elif isinstance(description, str):
            desc_text = description

        full_text = f"{analysis.summary} {desc_text}"

        # Check various conditions
        issues = []

        # 1. Check for deprecated keywords
        if self._is_deprecated(full_text, analysis.labels):
            issues.append("Contains deprecated/legacy keywords")
            analysis.alignment_status = "DEPRECATED"
            analysis.recommendation = "ARCHIVE or CLOSE - appears to be legacy/deprecated work"

        # 2. Check capability alignment
        capability, confidence = self._match_capability(full_text)
        analysis.aligned_capability = capability

        if capability and confidence >= 0.3:
            if analysis.alignment_status != "DEPRECATED":
                analysis.alignment_status = "ALIGNED"
                analysis.recommendation = f"KEEP - aligns with {capability} (confidence: {confidence:.0%})"
        elif self._is_foundation(full_text, analysis.labels):
            analysis.alignment_status = "FOUNDATION"
            analysis.recommendation = "KEEP - foundational platform work"
        else:
            if analysis.alignment_status != "DEPRECATED":
                issues.append("Does not clearly align with any capability")
                analysis.alignment_status = "ORPHANED"
                analysis.recommendation = "REVIEW - may need to be re-categorized or closed"

        # 3. Check for staleness
        if self._is_stale(analysis.updated):
            issues.append("Not updated in 90+ days")
            if analysis.status not in ["Done", "Closed"]:
                if analysis.alignment_status == "ORPHANED":
                    analysis.alignment_status = "STALE_ORPHANED"
                    analysis.recommendation = "CLOSE - stale and misaligned"
                else:
                    issues.append("Stale but aligned - may need attention")

        # 4. Check status
        if analysis.status in ["Done", "Closed"]:
            analysis.alignment_status = "COMPLETED"
            analysis.recommendation = "KEEP - completed work"

        analysis.issues = issues
        return analysis

    def find_duplicates(self) -> List[Tuple[str, str, float]]:
        """Find potential duplicate tickets based on summary similarity"""
        duplicates = []
        all_tickets = self.epics + self.tickets

        for i, t1 in enumerate(all_tickets):
            for t2 in all_tickets[i+1:]:
                # Simple word overlap similarity
                words1 = set(t1.summary.lower().split())
                words2 = set(t2.summary.lower().split())

                if len(words1) < 3 or len(words2) < 3:
                    continue

                overlap = len(words1 & words2)
                similarity = overlap / min(len(words1), len(words2))

                if similarity > 0.7:
                    duplicates.append((t1.key, t2.key, similarity))

        return duplicates

    def run_analysis(self) -> Dict[str, Any]:
        """Run full analysis on all JIRA tickets"""
        logger.info("Fetching EPICs...")
        epics_raw = self.fetch_all_issues("Epic")
        logger.info(f"Found {len(epics_raw)} EPICs")

        logger.info("Fetching all other tickets...")
        all_issues = self.fetch_all_issues()
        tickets_raw = [i for i in all_issues if i["fields"]["issuetype"]["name"] != "Epic"]
        logger.info(f"Found {len(tickets_raw)} tickets")

        # Analyze EPICs
        logger.info("Analyzing EPICs...")
        for epic in epics_raw:
            analysis = self.analyze_ticket(epic)
            self.epics.append(analysis)

        # Analyze tickets
        logger.info("Analyzing tickets...")
        for ticket in tickets_raw:
            analysis = self.analyze_ticket(ticket)
            self.tickets.append(analysis)

        # Find duplicates
        logger.info("Finding duplicates...")
        duplicates = self.find_duplicates()

        # Build summary
        epic_stats = defaultdict(int)
        ticket_stats = defaultdict(int)
        capability_coverage = defaultdict(lambda: {"epics": [], "tickets": []})

        for epic in self.epics:
            epic_stats[epic.alignment_status] += 1
            if epic.aligned_capability:
                capability_coverage[epic.aligned_capability]["epics"].append(epic.key)

        for ticket in self.tickets:
            ticket_stats[ticket.alignment_status] += 1
            if ticket.aligned_capability:
                capability_coverage[ticket.aligned_capability]["tickets"].append(ticket.key)

        self.summary = {
            "analysis_date": datetime.now().isoformat(),
            "total_epics": len(self.epics),
            "total_tickets": len(self.tickets),
            "epic_breakdown": dict(epic_stats),
            "ticket_breakdown": dict(ticket_stats),
            "potential_duplicates": len(duplicates),
            "duplicates": [{"ticket1": d[0], "ticket2": d[1], "similarity": f"{d[2]:.0%}"} for d in duplicates[:20]],
            "capability_coverage": {k: {"epic_count": len(v["epics"]), "ticket_count": len(v["tickets"])}
                                   for k, v in capability_coverage.items()},
            "cleanup_candidates": {
                "epics_to_review": [asdict(e) for e in self.epics if e.alignment_status in ["ORPHANED", "DEPRECATED", "STALE_ORPHANED"]],
                "tickets_to_review": [asdict(t) for t in self.tickets if t.alignment_status in ["ORPHANED", "DEPRECATED", "STALE_ORPHANED"]]
            }
        }

        return self.summary

    def generate_report(self) -> str:
        """Generate a human-readable report"""
        lines = [
            "=" * 70,
            "JIRA CLEANUP ANALYSIS REPORT",
            "=" * 70,
            f"Analysis Date: {self.summary.get('analysis_date', 'N/A')}",
            "",
            "OVERVIEW",
            "-" * 40,
            f"Total EPICs:   {self.summary.get('total_epics', 0)}",
            f"Total Tickets: {self.summary.get('total_tickets', 0)}",
            "",
            "EPIC BREAKDOWN",
            "-" * 40,
        ]

        for status, count in self.summary.get("epic_breakdown", {}).items():
            lines.append(f"  {status}: {count}")

        lines.extend([
            "",
            "TICKET BREAKDOWN",
            "-" * 40,
        ])

        for status, count in self.summary.get("ticket_breakdown", {}).items():
            lines.append(f"  {status}: {count}")

        lines.extend([
            "",
            "CAPABILITY COVERAGE",
            "-" * 40,
        ])

        for cap, counts in self.summary.get("capability_coverage", {}).items():
            cap_name = cap.replace("cap", "Cap ").replace("_", " ").title()
            lines.append(f"  {cap_name}: {counts['epic_count']} EPICs, {counts['ticket_count']} tickets")

        lines.extend([
            "",
            "POTENTIAL DUPLICATES",
            "-" * 40,
            f"Found {self.summary.get('potential_duplicates', 0)} potential duplicates",
        ])

        for dup in self.summary.get("duplicates", [])[:10]:
            lines.append(f"  {dup['ticket1']} <-> {dup['ticket2']} ({dup['similarity']} similar)")

        cleanup = self.summary.get("cleanup_candidates", {})
        epics_to_review = cleanup.get("epics_to_review", [])
        tickets_to_review = cleanup.get("tickets_to_review", [])

        lines.extend([
            "",
            "CLEANUP RECOMMENDATIONS",
            "-" * 40,
            f"EPICs to review:   {len(epics_to_review)}",
            f"Tickets to review: {len(tickets_to_review)}",
            "",
            "EPICs RECOMMENDED FOR REVIEW/CLOSURE:",
        ])

        for epic in epics_to_review[:20]:
            lines.append(f"  [{epic['key']}] {epic['summary'][:50]}...")
            lines.append(f"    Status: {epic['alignment_status']} | Recommendation: {epic['recommendation']}")

        lines.extend([
            "",
            "TICKETS RECOMMENDED FOR REVIEW/CLOSURE:",
        ])

        for ticket in tickets_to_review[:30]:
            lines.append(f"  [{ticket['key']}] {ticket['summary'][:50]}...")
            lines.append(f"    Status: {ticket['alignment_status']} | Recommendation: {ticket['recommendation']}")

        lines.extend([
            "",
            "=" * 70,
            "END OF REPORT",
            "=" * 70,
        ])

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="JIRA Cleanup Analyzer")
    parser.add_argument("--output", "-o", help="Output file for JSON report")
    parser.add_argument("--report", "-r", help="Output file for text report")
    args = parser.parse_args()

    config = JiraConfig.from_env()
    analyzer = JiraCleanupAnalyzer(config)

    summary = analyzer.run_analysis()

    # Print text report
    report = analyzer.generate_report()
    print(report)

    # Save JSON if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"JSON report saved to: {args.output}")

    # Save text report if requested
    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)
        logger.info(f"Text report saved to: {args.report}")


if __name__ == "__main__":
    main()
