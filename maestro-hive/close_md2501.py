#!/usr/bin/env python3
"""
Update JIRA ticket MD-2501 to Done.
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

    def transition_issue(self, issue_key: str, transition_name: str = "Done"):
        """Transition a JIRA issue to a new status"""
        # 1. Get available transitions
        url = self._url(f"issue/{issue_key}/transitions")
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"❌ Failed to get transitions for {issue_key}: {response.status_code}")
                return False
            
            transitions = response.json().get('transitions', [])
            target_transition = next((t for t in transitions if t['name'].lower() == transition_name.lower()), None)
            
            if not target_transition:
                logger.error(f"❌ Transition '{transition_name}' not found for {issue_key}. Available: {[t['name'] for t in transitions]}")
                return False
            
            # 2. Perform transition
            transition_id = target_transition['id']
            payload = {"transition": {"id": transition_id}}
            
            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"✅ Transitioned {issue_key} to {transition_name}")
                return True
            else:
                logger.error(f"❌ Failed to transition {issue_key}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception transitioning issue: {e}")
            return False

def main():
    client = JiraClient()
    client.transition_issue("MD-2501", "Done")

if __name__ == "__main__":
    main()
