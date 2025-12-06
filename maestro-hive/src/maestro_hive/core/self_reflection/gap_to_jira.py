#!/usr/bin/env python3
"""
Gap-to-JIRA Automation: Self-Improvement Loop

Connects the GapDetector to JIRA to automatically create
remediation tasks for identified gaps.

This implements the "Self-Improving AI Platform" vision where
detected gaps are converted into actionable JIRA tickets.

Usage:
    # Using environment variables (recommended)
    export JIRA_BASE_URL="https://your-instance.atlassian.net"
    export JIRA_EMAIL="your-email@example.com"
    export JIRA_API_TOKEN="your-api-token"
    export JIRA_PROJECT_KEY="MD"
    python gap_to_jira.py

    # Or with direct Confluence API
    python gap_to_jira.py --dry-run  # Preview without creating tickets
"""

import json
import os
import sys
import argparse
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import requests
from base64 import b64encode

# Import the GapDetector
from gap_detector import GapDetector, Gap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class JiraConfig:
    """JIRA configuration from config file or environment variables"""
    base_url: str
    email: str
    api_token: str
    project_key: str

    @classmethod
    def from_env(cls) -> 'JiraConfig':
        """Load configuration from config file or environment variables"""
        # Search paths for config file
        search_paths = [
            Path.cwd() / ".jira-config",
            Path.home() / ".jira-config",
            Path("/home/ec2-user/projects/maestro-frontend-production/.jira-config")
        ]
        
        config_values = {}
        config_found = False
        
        for config_path in search_paths:
            if config_path.exists():
                logger.info(f"Loading config from {config_path}")
                try:
                    with open(config_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                config_values[key.strip()] = value.strip()
                    config_found = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to read config at {config_path}: {e}")

        # Environment variables override config file
        base_url = os.environ.get('JIRA_BASE_URL', config_values.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'))
        email = os.environ.get('JIRA_EMAIL', config_values.get('JIRA_EMAIL', ''))
        api_token = os.environ.get('JIRA_API_TOKEN', config_values.get('JIRA_API_TOKEN', ''))
        project_key = os.environ.get('JIRA_PROJECT_KEY', config_values.get('JIRA_PROJECT_KEY', 'MD'))

        if not email or not api_token:
            raise ValueError(
                f"JIRA credentials not found.\n"
                f"Either set environment variables or create {cls.CONFIG_FILE} with:\n"
                f"  JIRA_EMAIL=your-email@example.com\n"
                f"  JIRA_API_TOKEN=your-api-token"
            )

        return cls(
            base_url=base_url,
            email=email,
            api_token=api_token,
            project_key=project_key
        )


class GapToJira:
    """
    Converts detected gaps into JIRA tickets.

    This class implements the automation loop:
    1. Run GapDetector to find missing capabilities
    2. Check if a ticket already exists for each gap
    3. Create new tickets for untracked gaps
    4. Link related gaps to a parent EPIC
    """

    SEVERITY_TO_PRIORITY = {
        'HIGH': 'High',
        'MEDIUM': 'Medium',
        'LOW': 'Low'
    }

    GAP_TYPE_TO_LABEL = {
        'MISSING_FILE': 'gap-missing-file',
        'MISSING_CAPABILITY': 'gap-missing-capability',
        'MISSING_TEST': 'gap-missing-test'
    }

    def __init__(self, config: JiraConfig, parent_epic: Optional[str] = None):
        """
        Initialize GapToJira.

        Args:
            config: JIRA configuration
            parent_epic: Optional parent EPIC key to link tickets to
        """
        self.config = config
        self.parent_epic = parent_epic
        self._auth = b64encode(f"{config.email}:{config.api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {self._auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _api_url(self, endpoint: str) -> str:
        """Build full API URL"""
        return f"{self.config.base_url}/rest/api/3/{endpoint}"

    def get_all_open_tickets(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all open tickets created by GapDetector.
        
        Returns:
            Dictionary mapping block_id -> ticket details
        """
        jql = (
            f'project = {self.config.project_key} AND '
            f'labels = "gap-detector" AND '
            f'statusCategory != Done'
        )
        
        url = self._api_url("search/jql")
        payload = {
            "jql": jql,
            "maxResults": 100,  # Adjust pagination if needed
            "fields": ["summary", "status", "labels"]
        }
        
        mapping = {}
        start_at = 0
        
        while True:
            try:
                # Rate limiting
                time.sleep(0.2)
                
                payload["startAt"] = start_at
                response = requests.post(url, headers=self._headers, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch open tickets: {response.status_code}")
                    break
                    
                data = response.json()
                issues = data.get("issues", [])
                
                if not issues:
                    break
                    
                for issue in issues:
                    # Extract block_id from labels
                    block_id = None
                    for label in issue["fields"]["labels"]:
                        if label.startswith("gap-") and label != "gap-detector" and not label.startswith("gap-missing-"):
                            block_id = label[4:]  # Remove 'gap-' prefix
                            break
                    
                    if block_id:
                        mapping[block_id] = {
                            "key": issue["key"],
                            "summary": issue["fields"]["summary"],
                            "status": issue["fields"]["status"]["name"]
                        }
                
                start_at += len(issues)
                if start_at >= data.get("total", 0):
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching tickets: {e}")
                break
                
        return mapping

    def mark_ticket_for_review(self, issue_key: str, current_summary: str, reason: str) -> bool:
        """
        Mark a ticket for review (prefix title, add comment).
        
        Args:
            issue_key: JIRA issue key
            current_summary: Current ticket summary
            reason: Reason for marking for review
            
        Returns:
            True if successful
        """
        prefix = "**REVIEW** "
        new_summary = current_summary
        
        # Avoid double prefixing
        if not current_summary.startswith(prefix):
            new_summary = f"{prefix}{current_summary}"
            
        # 1. Update Summary
        url = self._api_url(f"issue/{issue_key}")
        payload = {
            "fields": {
                "summary": new_summary
            }
        }
        
        try:
            time.sleep(0.5) # Rate limiting
            response = requests.put(url, headers=self._headers, json=payload)
            if response.status_code != 204:
                logger.warning(f"Failed to update summary for {issue_key}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error updating ticket {issue_key}: {e}")
            return False

        # 2. Add Comment
        comment_url = self._api_url(f"issue/{issue_key}/comment")
        comment_payload = {
            "body": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": f"⚠️ {reason}", "marks": [{"type": "strong"}]},
                            {"type": "text", "text": "\n\nThis gap is no longer detected in the latest scan. Please review if this is a valid fix or a configuration change. If valid, please close this ticket."}
                        ]
                    }
                ]
            }
        }
        
        try:
            time.sleep(0.5)
            response = requests.post(comment_url, headers=self._headers, json=comment_payload)
            if response.status_code == 201:
                logger.info(f"Marked {issue_key} for review")
                return True
            else:
                logger.warning(f"Failed to add comment to {issue_key}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error commenting on {issue_key}: {e}")
            
        return False

    def search_existing_tickets(self, gap: Gap) -> List[Dict[str, Any]]:
        """
        Search for existing tickets that might cover this gap.

        Args:
            gap: The gap to search for

        Returns:
            List of matching JIRA issues
        """
        # Search by block_id in summary or labels
        jql = (
            f'project = {self.config.project_key} AND '
            f'(summary ~ "{gap.block_id}" OR labels = "gap-{gap.block_id}")'
        )

        url = self._api_url("search/jql")
        payload = {
            "jql": jql,
            "maxResults": 10,
            "fields": ["summary", "status", "labels"]
        }

        try:
            response = requests.post(url, headers=self._headers, json=payload)
            if response.status_code == 200:
                return response.json().get("issues", [])
        except Exception as e:
            logger.warning(f"Failed to search for existing tickets: {e}")

        return []

    def get_last_closed_ticket(self, gap_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if this gap was previously closed/resolved.
        
        Returns:
            Dict with ticket details if found, else None
        """
        jql = (
            f'project = {self.config.project_key} AND '
            f'labels = "gap-{gap_id}" AND '
            f'statusCategory = Done'
        )
        
        # Sort by resolution date desc to get latest decision
        url = self._api_url("search/jql")
        payload = {
            "jql": jql,
            "maxResults": 1,
            "fields": ["summary", "status", "resolution", "resolutiondate"],
            "orderBy": "resolutiondate DESC"
        }
        
        try:
            time.sleep(0.2)
            response = requests.post(url, headers=self._headers, json=payload)
            if response.status_code == 200:
                issues = response.json().get("issues", [])
                if issues:
                    return issues[0]
        except Exception as e:
            logger.warning(f"Failed to check history for gap {gap_id}: {e}")
            
        return None

    def create_ticket(self, gap: Gap, dry_run: bool = False, prefix: str = "") -> Optional[str]:
        """
        Create a JIRA ticket for a gap.

        Args:
            gap: The gap to create a ticket for
            dry_run: If True, don't actually create the ticket
            prefix: Optional prefix for the summary (e.g. "[REGRESSION]")

        Returns:
            Created ticket key or None
        """
        # Build ticket data
        summary = f"{prefix}[{gap.gap_type}] {gap.block_name}: {gap.description[:100]}"

        description = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Gap Details"}]
                },
                {
                    "type": "table",
                    "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Field"}]}]},
                                {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Value"}]}]}
                            ]
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Block ID"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.block_id}]}]}
                            ]
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Block Name"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.block_name}]}]}
                            ]
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Gap Type"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.gap_type}]}]}
                            ]
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Severity"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": gap.severity}]}]}
                            ]
                        }
                    ]
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Description"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": gap.description}]
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
                {
                    "type": "rule"
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Auto-generated by ", "marks": [{"type": "em"}]},
                        {"type": "text", "text": "GapDetector Self-Reflection Engine", "marks": [{"type": "strong"}, {"type": "em"}]},
                        {"type": "text", "text": f" on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "marks": [{"type": "em"}]}
                    ]
                }
            ]
        }

        labels = [
            "auto-generated",
            "gap-detector",
            self.GAP_TYPE_TO_LABEL.get(gap.gap_type, "gap-unknown"),
            f"gap-{gap.block_id}"
        ]

        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},
                "priority": {"name": self.SEVERITY_TO_PRIORITY.get(gap.severity, "Medium")},
                "labels": labels
            }
        }

        # Add parent epic if specified
        if self.parent_epic:
            payload["fields"]["parent"] = {"key": self.parent_epic}

        if dry_run:
            logger.info(f"[DRY RUN] Would create ticket: {summary}")
            logger.info(f"  Priority: {self.SEVERITY_TO_PRIORITY.get(gap.severity, 'Medium')}")
            logger.info(f"  Labels: {labels}")
            return f"DRY-RUN-{gap.block_id}"

        url = self._api_url("issue")
        try:
            time.sleep(0.5) # Rate limiting
            response = requests.post(url, headers=self._headers, json=payload)
            if response.status_code == 201:
                key = response.json().get("key")
                logger.info(f"Created ticket: {key} - {summary[:50]}...")
                return key
            else:
                logger.error(f"Failed to create ticket: {response.status_code}")
                logger.error(response.text)
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")

        return None

    def sync_gaps(
        self,
        gaps: List[Gap],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Sync gaps with JIRA:
        1. Create tickets for new gaps
        2. Mark tickets for review if gaps are resolved
        
        Args:
            gaps: List of currently detected gaps
            dry_run: If True, don't make changes
            
        Returns:
            Summary of actions
        """
        results = {
            "total_gaps": len(gaps),
            "tickets_created": 0,
            "tickets_skipped": 0,
            "tickets_failed": 0,
            "tickets_marked_review": 0,
            "created_keys": [],
            "review_keys": [],
            "skipped_reasons": []
        }
        
        # 1. Get all currently open tickets for gaps
        logger.info("Fetching existing open tickets...")
        existing_tickets = self.get_all_open_tickets()
        logger.info(f"Found {len(existing_tickets)} open gap tickets")
        
        # 2. Process current gaps (Create or Skip)
        current_gap_ids = set()
        for gap in gaps:
            current_gap_ids.add(gap.block_id)
            
            if gap.block_id in existing_tickets:
                ticket = existing_tickets[gap.block_id]
                results["tickets_skipped"] += 1
                results["skipped_reasons"].append({
                    "gap": gap.block_id,
                    "reason": f"Existing ticket: {ticket['key']}"
                })
                # logger.info(f"Skipping gap '{gap.block_id}' - existing ticket: {ticket['key']}")
                continue
                
            # Check history for closed tickets
            last_closed = self.get_last_closed_ticket(gap.block_id)
            if last_closed:
                resolution = last_closed["fields"].get("resolution")
                resolution_name = resolution["name"] if resolution else "Done"
                
                # Case 1: Explicitly marked as Won't Do / Out of Scope
                if resolution_name in ["Won't Do", "Won't Fix", "Declined", "Out of Scope", "Not A Bug"]:
                    results["tickets_skipped"] += 1
                    results["skipped_reasons"].append({
                        "gap": gap.block_id,
                        "reason": f"Previously resolved as '{resolution_name}' in {last_closed['key']}"
                    })
                    continue
                    
                # Case 2: Marked as Done/Fixed, but gap reappeared -> REGRESSION
                if resolution_name in ["Done", "Fixed", "Resolved", "Complete"]:
                    logger.warning(f"Gap {gap.block_id} reappeared after being fixed in {last_closed['key']}!")
                    key = self.create_ticket(gap, dry_run=dry_run, prefix="[REGRESSION] ")
                    if key:
                        results["tickets_created"] += 1
                        results["created_keys"].append(key)
                    continue

            # Create new ticket (Standard)
            key = self.create_ticket(gap, dry_run=dry_run)
            if key:
                results["tickets_created"] += 1
                results["created_keys"].append(key)
            else:
                results["tickets_failed"] += 1
                
        # 3. Identify Resolved Gaps (Tickets that exist but gap is gone)
        for block_id, ticket in existing_tickets.items():
            if block_id not in current_gap_ids:
                # This gap is no longer detected!
                if dry_run:
                    logger.info(f"[DRY RUN] Would mark {ticket['key']} for REVIEW (Gap {block_id} resolved)")
                    results["tickets_marked_review"] += 1
                    results["review_keys"].append(ticket['key'])
                else:
                    if self.mark_ticket_for_review(ticket['key'], ticket['summary'], f"Gap '{block_id}' no longer detected"):
                        results["tickets_marked_review"] += 1
                        results["review_keys"].append(ticket['key'])
                        
        return results

    def process_gaps(
        self,
        gaps: List[Gap],
        dry_run: bool = False,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """Legacy method, delegates to sync_gaps"""
        return self.sync_gaps(gaps, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Gap-to-JIRA Automation: Create JIRA tickets from detected gaps"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview tickets without creating them"
    )
    parser.add_argument(
        "--workspace",
        default="/home/ec2-user/projects/maestro-platform/maestro-hive",
        help="Workspace root to scan"
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Path to registry.json (default: alongside gap_detector.py)"
    )
    parser.add_argument(
        "--parent-epic",
        default=None,
        help="Parent EPIC key to link tickets to (e.g., MD-2481)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file for results (JSON format)"
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = JiraConfig.from_env()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Set up paths
    current_dir = Path(__file__).parent
    workspace_root = Path(args.workspace)
    registry_path = Path(args.registry) if args.registry else current_dir / "registry.json"

    if not registry_path.exists():
        logger.error(f"Registry not found at {registry_path}")
        sys.exit(1)

    # Run gap detection
    logger.info(f"Scanning workspace: {workspace_root}")
    detector = GapDetector(str(workspace_root), str(registry_path))
    gaps = detector.scan()

    if not gaps:
        logger.info("No gaps detected. System is healthy!")
        return

    logger.info(f"Found {len(gaps)} gaps")

    # Process gaps
    gap_to_jira = GapToJira(config, parent_epic=args.parent_epic)
    results = gap_to_jira.sync_gaps(gaps, dry_run=args.dry_run)

    # Output results
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"Total gaps detected:      {results['total_gaps']}")
    logger.info(f"Tickets created:          {results['tickets_created']}")
    logger.info(f"Tickets skipped:          {results['tickets_skipped']}")
    logger.info(f"Tickets marked for REVIEW:{results['tickets_marked_review']}")
    logger.info(f"Tickets failed:           {results['tickets_failed']}")

    if results["created_keys"]:
        logger.info(f"\nCreated tickets: {', '.join(results['created_keys'])}")
        
    if results["review_keys"]:
        logger.info(f"\nMarked for REVIEW: {', '.join(results['review_keys'])}")

    if results["skipped_reasons"]:
        logger.info(f"\nSkipped {len(results['skipped_reasons'])} existing tickets.")

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
