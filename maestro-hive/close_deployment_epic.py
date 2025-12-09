#!/usr/bin/env python3
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

    def transition_issue(self, issue_key, transition_id):
        url = self._url(f"issue/{issue_key}/transitions")
        payload = {"transition": {"id": transition_id}}
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"✅ Successfully transitioned {issue_key} to Done")
                return True
            else:
                logger.error(f"❌ Failed to transition {issue_key}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception transitioning {issue_key}: {e}")
            return False

def main():
    client = JiraClient()
    
    # 1. Close MD-1791 (Portainer Setup)
    logger.info("Closing MD-1791 (Portainer Setup)...")
    client.transition_issue("MD-1791", "31") # 31 is Done
    
    # 2. Close MD-1790 (Parent EPIC)
    logger.info("Closing MD-1790 (Unified Deployment Management GUI EPIC)...")
    client.transition_issue("MD-1790", "31") # 31 is Done

if __name__ == "__main__":
    main()
