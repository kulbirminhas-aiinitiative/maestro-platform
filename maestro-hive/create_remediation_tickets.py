#!/usr/bin/env python3
"""
Create Remediation Tickets for Compliance Gaps (MD-2487, MD-2488, MD-2489)
"""

import os
import sys
import logging
import requests
import json
from typing import List, Dict, Any

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
    
    # 1. Create Parent BAU Task for Compliance Remediation
    parent_summary = "BAU: Global Compliance Remediation (26 EPICs Audit)"
    parent_desc = "Remediation of compliance gaps identified in the global audit of 26 EPICs. Focus on deploying MOCKUP code and fixing deployment issues."
    
    parent_key = client.create_issue(parent_summary, parent_desc, issue_type="Task")
    
    if not parent_key:
        logger.error("Failed to create parent task. Aborting.")
        return

    # 2. Create Subtasks for MOCKUP Remediation
    subtasks = [
        {
            "summary": "Remediate MD-2156: Personal Data & Privacy (GDPR)",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (62/100)."
        },
        {
            "summary": "Remediate MD-2159: Technical Documentation (Art 11)",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (45/100)."
        },
        {
            "summary": "Remediate MD-2332: EU AI Act & GDPR Initiative",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (45/100)."
        },
        {
            "summary": "Remediate MD-2334: AI Security and Robustness",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (15/100)."
        },
        {
            "summary": "Remediate MD-2371: Team-Based Artifact Generation",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (15/100)."
        },
        {
            "summary": "Remediate MD-2387: Automated Compliance Audit",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (35/100)."
        },
        {
            "summary": "Remediate MD-2484: Enterprise Features",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (15/100)."
        },
        {
            "summary": "Remediate MD-2502: CLI Slash Command Interface",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (35/100)."
        },
        {
            "summary": "Remediate MD-2510: Block Promotion Pipeline",
            "description": "Fix deployment location. Current status: WRONG REPO (75/100)."
        },
        {
            "summary": "Remediate MD-2554: Persona Schema Definition",
            "description": "Deploy code from proof directory to production codebase. Current status: MOCKUP (15/100)."
        }
    ]

    for task in subtasks:
        client.create_issue(
            summary=task["summary"],
            description=task["description"],
            issue_type="Subtask",
            parent_key=parent_key
        )

    print(f"\nSuccessfully created Global Compliance Remediation ticket {parent_key} with {len(subtasks)} subtasks.")

if __name__ == "__main__":
    main()
