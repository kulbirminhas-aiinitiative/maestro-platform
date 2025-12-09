#!/usr/bin/env python3
import os
import sys
import logging
import requests
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JiraConfig:
    CONFIG_FILE = "/home/ec2-user/projects/maestro-frontend-production/.jira-config"
    def __init__(self):
        self.config_values = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        self.config_values[k.strip()] = v.strip()
        self.base_url = os.environ.get('JIRA_BASE_URL', self.config_values.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'))
        self.email = os.environ.get('JIRA_EMAIL', self.config_values.get('JIRA_EMAIL', ''))
        self.api_token = os.environ.get('JIRA_API_TOKEN', self.config_values.get('JIRA_API_TOKEN', ''))
        self.project_key = os.environ.get('JIRA_PROJECT_KEY', self.config_values.get('JIRA_PROJECT_KEY', 'MD'))

class JiraClient:
    def __init__(self):
        self.config = JiraConfig()
        self.auth = (self.config.email, self.config.api_token)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
    def _url(self, path: str) -> str:
        return f"{self.config.base_url}/rest/api/3/{path}"

    def create_epic(self, summary, description):
        url = self._url("issue")
        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
                },
                "issuetype": {"name": "Epic"}
            }
        }
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 201:
                return response.json()['key']
        except: pass
        return None

    def set_parent(self, issue_key, parent_key):
        url = self._url(f"issue/{issue_key}")
        payload = {"fields": {"parent": {"key": parent_key}}}
        requests.put(url, json=payload, auth=self.auth, headers=self.headers)

def main():
    client = JiraClient()
    # Hardcoded for the last orphan
    epic_key = client.create_epic("[AI] Agents & Personas", "Configuration for AI Agents and Personas.")
    if epic_key:
        print(f"Created EPIC {epic_key}")
        client.set_parent("MD-2002", epic_key)
        print("Linked MD-2002")

if __name__ == "__main__":
    main()
