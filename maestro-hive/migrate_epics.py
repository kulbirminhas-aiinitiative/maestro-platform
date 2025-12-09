#!/usr/bin/env python3
import os
import requests
import json
import logging
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
                data = response.json()
                logger.info(f"✅ Created EPIC {data['key']}: {summary}")
                return data['key']
            else:
                logger.error(f"❌ Failed to create EPIC: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception creating EPIC: {e}")
            return None

    def get_tickets_in_epic(self, epic_key):
        jql = f'parent = {epic_key} AND statusCategory != Done'
        url = f"{self.config.base_url}/rest/api/3/search/jql"
        payload = {"jql": jql, "fields": ["summary"], "maxResults": 100}
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 200:
                return response.json().get('issues', [])
        except: pass
        return []

    def set_parent(self, issue_key, parent_key):
        url = self._url(f"issue/{issue_key}")
        payload = {"fields": {"parent": {"key": parent_key}}}
        try:
            response = requests.put(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"🔗 Moved {issue_key} to {parent_key}")
                return True
            else:
                logger.error(f"❌ Failed to move {issue_key}: {response.status_code} - {response.text}")
                return False
        except: return False

def main():
    client = JiraClient()
    
    migrations = [
        {"old": "MD-2781", "new_name": "[Remediation] Core Services & CLI Compliance (Batch 2)", "desc": "Continued remediation of core services."},
        {"old": "MD-2782", "new_name": "[Infrastructure] Service Mesh & Network Security (Batch 2)", "desc": "Continued infrastructure security work."},
        {"old": "MD-2783", "new_name": "[Gateway] Kong API Gateway Implementation (Batch 2)", "desc": "Continued Gateway implementation."},
        {"old": "MD-2784", "new_name": "[Workflow] Human-in-the-Loop Controls (Batch 2)", "desc": "Continued workflow controls."},
        {"old": "MD-2785", "new_name": "[BAU] Operational Deployment & Compliance (Batch 2)", "desc": "Continued BAU operations."}
    ]
    
    for mig in migrations:
        logger.info(f"\nProcessing migration for {mig['old']}...")
        tickets = client.get_tickets_in_epic(mig['old'])
        if not tickets:
            logger.info(f"No active tickets in {mig['old']}. Skipping.")
            continue
            
        logger.info(f"Found {len(tickets)} tickets to move.")
        new_epic_key = client.create_epic(mig['new_name'], mig['desc'])
        
        if new_epic_key:
            for ticket in tickets:
                client.set_parent(ticket['key'], new_epic_key)
                time.sleep(0.5)

if __name__ == "__main__":
    main()
