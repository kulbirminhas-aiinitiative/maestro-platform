#!/usr/bin/env python3
"""
Create JIRA ticket for epic-execute.md review and enhancement.
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
    
    summary = "Review and Enhance epic-execute.md for Anti-Mockup Robustness"
    description = (
        "Based on the review of ~/.claude/commands/epic-execute.md, the following enhancements are recommended to further prevent 'Mockup/Simulation' results:\n\n"
        "1. Expand 'Mock Indicator' List: Add terms like NotImplementedError, pass (with context), return True (blind returns), TODO, and FIXME to the negative scoring logic in Phase 8.\n"
        "2. Dynamic Execution Checks: Implement timestamp verification for output files to ensure they were generated during the current run.\n"
        "3. Reinforce Two-Agent Verification: Ensure the agent running the script is different from the agent validating the results.\n"
        "4. Network Validation: Add a pre-flight check (Phase 0) to explicitly verify localhost:8000 is reachable.\n\n"
        "This ticket tracks the implementation of these improvements."
    )
    
    client.create_issue(summary, description, issue_type="Task")

if __name__ == "__main__":
    main()
