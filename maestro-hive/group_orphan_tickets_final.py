#!/usr/bin/env python3
"""
Final pass to group remaining orphan tickets.
"""

import os
import sys
import logging
import requests
import json
import time

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
        url = self._url("issue")
        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
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

    def search_orphan_issues(self):
        results = []
        start_at = 0
        max_results = 100
        jql = f'project = {self.config.project_key} AND statusCategory != Done AND parent is EMPTY AND issuetype != Epic'
        
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            payload = {"jql": jql, "fields": ["summary", "issuetype"]}
            params = {"startAt": start_at, "maxResults": max_results}
            
            try:
                response = requests.post(url, json=payload, params=params, auth=self.auth, headers=self.headers)
                if response.status_code != 200: break
                
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                
                if start_at + len(issues) >= data.get('total', 0): break
                start_at += len(issues)
            except: break
        return results

    def set_parent(self, issue_key, parent_key):
        url = self._url(f"issue/{issue_key}")
        payload = {
            "fields": {
                "parent": {"key": parent_key}
            }
        }
        try:
            response = requests.put(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"🔗 Linked {issue_key} to {parent_key}")
                return True
            else:
                logger.error(f"❌ Failed to link {issue_key}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception linking {issue_key}: {e}")
            return False

def main():
    client = JiraClient()
    
    # 1. Define Groups
    groups = [
        {
            "name": "[Infrastructure] Resilience & Observability",
            "description": "Implementation of resilience patterns (Circuit Breaker, Canary) and observability.",
            "keywords": ["Canary", "Observability", "Circuit Breaker", "Traffic Splitting"]
        },
        {
            "name": "[Gateway] API Gateway Configuration",
            "description": "General API Gateway configuration and documentation.",
            "keywords": ["Gateway"]
        },
        {
            "name": "[Admin] Project Administration",
            "description": "Administrative tasks for project repositories and accounts.",
            "keywords": ["Cancel Google One", "Move Maestro repositories"]
        },
        {
            "name": "[Backend] Database & API Architecture",
            "description": "Backend architecture updates, database schema changes, and API endpoints.",
            "keywords": ["Team Ratings", "User Onboarding", "FK Architecture"]
        },
        {
            "name": "[QA] Testing & Validation",
            "description": "Additional testing tasks.",
            "keywords": ["unit test", "Test"]
        }
    ]
    
    # 2. Fetch Orphans
    logger.info("Fetching orphan tickets...")
    orphans = client.search_orphan_issues()
    logger.info(f"Found {len(orphans)} orphan tickets.")
    
    # 3. Process Keyword Groups
    for group in groups:
        logger.info(f"\nProcessing Group: {group['name']}")
        
        matches = []
        for issue in orphans:
            summary = issue['fields']['summary']
            if any(kw.lower() in summary.lower() for kw in group['keywords']):
                matches.append(issue)
        
        if not matches:
            logger.info("No matching tickets found.")
            continue
            
        logger.info(f"Found {len(matches)} tickets.")
        epic_key = client.create_epic(group['name'], group['description'])
        if epic_key:
            for issue in matches:
                client.set_parent(issue['key'], epic_key)
        time.sleep(1)

    # 4. Process Bugs
    logger.info("\nProcessing Bugs...")
    bugs = [i for i in orphans if i['fields']['issuetype']['name'] == 'Bug']
    if bugs:
        logger.info(f"Found {len(bugs)} bugs.")
        epic_key = client.create_epic("[Bugs] Known Issues & Fixes", "Collection of known bugs and issues.")
        if epic_key:
            for issue in bugs:
                client.set_parent(issue['key'], epic_key)
    else:
        logger.info("No bugs found.")

if __name__ == "__main__":
    main()
