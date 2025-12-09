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

    def get_issue_details(self, issue_id_or_key):
        url = self._url(f"issue/{issue_id_or_key}")
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            logger.error(f"Failed to get issue: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            logger.error(f"Exception getting issue: {e}")
            return None

def main():
    client = JiraClient()
    issue_key = "MD-1791"
    logger.info(f"Fetching details for {issue_key}...")
    issue = client.get_issue_details(issue_key)
    
    if issue:
        fields = issue.get('fields', {})
        summary = fields.get('summary', 'No summary')
        description = fields.get('description', 'No description')
        status = fields.get('status', {}).get('name', 'Unknown')
        
        print(f"\n=== {issue_key} ===\n")
        print(f"Summary: {summary}")
        print(f"Status: {status}")
        print(f"Description: {json.dumps(description, indent=2)}")
    else:
        print(f"Could not fetch {issue_key}")

if __name__ == "__main__":
    main()
