#!/usr/bin/env python3
"""
Group orphan tickets into logical EPICs.
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

    def create_epic(self, summary, description):
        """Create a new EPIC"""
        url = self._url("issue")
        
        description_adf = {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
        }

        fields = {
            "project": {"key": self.config.project_key},
            "summary": summary,
            "description": description_adf,
            "issuetype": {"name": "Epic"},
        }

        try:
            response = requests.post(url, json={"fields": fields}, auth=self.auth, headers=self.headers)
            if response.status_code == 201:
                key = response.json().get('key')
                logger.info(f"✅ Created EPIC: {key} - {summary}")
                return key
            else:
                logger.error(f"❌ Failed to create EPIC: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception creating EPIC: {e}")
            return None

    def link_to_epic(self, issue_key, epic_key):
        """Link an issue to an EPIC (using 'parent' field for JIRA Cloud)"""
        url = self._url(f"issue/{issue_key}")
        
        # For JIRA Cloud, setting the parent links it to the Epic
        payload = {
            "fields": {
                "parent": {"key": epic_key}
            }
        }
        
        try:
            response = requests.put(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"✅ Linked {issue_key} to {epic_key}")
                return True
            else:
                logger.error(f"❌ Failed to link {issue_key} to {epic_key}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception linking issue: {e}")
            return False

def main():
    client = JiraClient()
    
    # 1. Define Groups
    groups = {
        "MD-2385": ["MD-2769", "MD-2770", "MD-2771", "MD-2772"],
        "MD-2482": ["MD-2766", "MD-2767", "MD-2768", "MD-2761", "MD-2762", "MD-2763"],
        "MD-2383": ["MD-2765"],
        # "MD-1837": ["MD-2455", "MD-2456", "MD-2457"] # Assuming MD-1837 exists
    }
    
    # 2. Create New EPICs
    qa_epic = client.create_epic(
        "Quality Assurance & Testing Gaps", 
        "Container for all missing QA capabilities and test files identified by Gap Detector."
    )
    
    infra_epic = client.create_epic(
        "Maestro Core Infrastructure Gaps",
        "Container for missing core infrastructure files and capabilities identified by Gap Detector."
    )
    
    if qa_epic:
        # Add QA tickets
        # Range MD-2678 to MD-2696 + MD-2618
        qa_tickets = [f"MD-{i}" for i in range(2678, 2697)] + ["MD-2618"]
        groups[qa_epic] = qa_tickets
        
    if infra_epic:
        # Add Infra tickets
        # Range MD-2614 to MD-2623 (excluding 2618) + MD-2764
        infra_tickets = [f"MD-{i}" for i in range(2614, 2624) if i != 2618] + ["MD-2764"]
        groups[infra_epic] = infra_tickets

    # 3. Execute Linking
    for epic_key, tickets in groups.items():
        logger.info(f"Linking {len(tickets)} tickets to {epic_key}...")
        for ticket in tickets:
            client.link_to_epic(ticket, epic_key)

if __name__ == "__main__":
    main()
