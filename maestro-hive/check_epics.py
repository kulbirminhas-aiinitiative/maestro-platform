#!/usr/bin/env python3
"""
Check status of potential parent EPICs and find suitable EPICs for grouping.
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

    def get_issue(self, key):
        url = self._url(f"issue/{key}")
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def search_epics(self, query):
        jql = f'project = {self.config.project_key} AND issuetype = Epic AND summary ~ "{query}"'
        url = self._url("search/jql")
        payload = {"jql": jql}
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 200:
                return response.json().get('issues', [])
            return []
        except:
            return []

def main():
    client = JiraClient()
    
    # Check specific EPICs
    epics_to_check = ["MD-2383", "MD-2482", "MD-2385"]
    print("=== TARGET EPIC STATUS ===")
    for key in epics_to_check:
        issue = client.get_issue(key)
        if issue:
            summary = issue['fields']['summary']
            status = issue['fields']['status']['name']
            print(f"[{key}] {status}: {summary}")
        else:
            print(f"[{key}] NOT FOUND")

    # Search for other suitable EPICs
    print("\n=== POTENTIAL GROUPING EPICS ===")
    queries = ["Quality", "Technical Debt", "Infrastructure", "Process"]
    for q in queries:
        epics = client.search_epics(q)
        for epic in epics:
            key = epic['key']
            summary = epic['fields']['summary']
            status = epic['fields']['status']['name']
            print(f"[{key}] {status}: {summary}")

if __name__ == "__main__":
    main()
