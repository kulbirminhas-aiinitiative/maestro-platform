#!/usr/bin/env python3
"""
Create Remediation Tickets based on Compliance Findings for MD-2383, MD-2482, MD-2385.
"""

import os
import sys
import logging
import requests
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JiraConfig:
    """JIRA configuration"""
    CONFIG_FILE = "/home/ec2-user/projects/maestro-frontend-production/.jira-config"

    def __init__(self):
        self.config_values = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.config_values[key.strip()] = value.strip()
        
        self.base_url = os.environ.get('JIRA_BASE_URL', self.config_values.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'))
        self.email = os.environ.get('JIRA_EMAIL', self.config_values.get('JIRA_EMAIL', ''))
        self.api_token = os.environ.get('JIRA_API_TOKEN', self.config_values.get('JIRA_API_TOKEN', ''))
        self.project_key = os.environ.get('JIRA_PROJECT_KEY', self.config_values.get('JIRA_PROJECT_KEY', 'MD'))

class JiraClient:
    def __init__(self):
        self.config = JiraConfig()
        self.auth = (self.config.email, self.config.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    def _url(self, path: str) -> str:
        return f"{self.config.base_url}/rest/api/3/{path}"

    def create_issue(self, summary: str, description: str, issue_type: str = "Task", parent_key: str = None):
        """Create a JIRA issue"""
        url = self._url("issue")
        
        # Construct ADF description
        description_adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": description
                        }
                    ]
                }
            ]
        }

        fields = {
            "project": {"key": self.config.project_key},
            "summary": summary,
            "description": description_adf,
            "issuetype": {"name": issue_type},
        }

        if parent_key:
            fields["parent"] = {"key": parent_key}

        try:
            response = requests.post(url, json={"fields": fields}, auth=self.auth, headers=self.headers)
            if response.status_code == 201:
                data = response.json()
                key = data.get('key')
                logger.info(f"✅ Created {issue_type}: {key} - {summary}")
                return key
            else:
                logger.error(f"❌ Failed to create {issue_type}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception creating issue: {e}")
            return None

def main():
    client = JiraClient()
    
    # MD-2383 Remediation
    logger.info("Creating tickets for MD-2383 (Tri-Modal Validation Routing)...")
    client.create_issue(
        summary="Create Operational Runbook for Tri-Modal Validation Routing (MD-2383)",
        description="Compliance finding: Missing operational runbook (-1.15 points). Required to achieve PASS status for MD-2383.",
        issue_type="Task"
    )

    # MD-2482 Remediation
    logger.info("Creating tickets for MD-2482 (Core Validation Framework)...")
    client.create_issue(
        summary="Deploy Validation Module to Production (MD-2482)",
        description="Critical finding: ALL IMPLEMENTATION IS MOCKUP. Deploy code from proof directory to /home/ec2-user/projects/maestro-platform/maestro-hive/src/maestro_hive/validation/.",
        issue_type="Task"
    )
    client.create_issue(
        summary="Integrate Validation Framework with Build System (MD-2482)",
        description="Critical finding: Integrate validation framework with build system.",
        issue_type="Task"
    )
    client.create_issue(
        summary="Create Operational Documentation for Validation Framework (MD-2482)",
        description="High priority finding: Create operational documentation for Validation Framework.",
        issue_type="Task"
    )

    # MD-2385 Remediation
    logger.info("Creating tickets for MD-2385 (Team Performance Tracking)...")
    client.create_issue(
        summary="Implement Team Performance Aggregation Service (MD-2385)",
        description="Missing core feature: Team Performance Aggregation Service.",
        issue_type="Task"
    )
    client.create_issue(
        summary="Implement Velocity Calculator (MD-2385)",
        description="Missing core feature: Velocity Calculator (JIRA story points).",
        issue_type="Task"
    )
    client.create_issue(
        summary="Implement Team Ranking/A-F Grading System (MD-2385)",
        description="Missing core feature: Team Ranking/A-F Grading System.",
        issue_type="Task"
    )
    client.create_issue(
        summary="Implement Gamification Engine (MD-2385)",
        description="Missing core feature: Gamification Engine (leaderboard, badges).",
        issue_type="Task"
    )

if __name__ == "__main__":
    main()
