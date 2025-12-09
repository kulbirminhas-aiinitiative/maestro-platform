#!/usr/bin/env python3
"""
Find open JIRA tickets that do not have a parent EPIC.
"""

import os
import sys
import logging
import requests
import json
from collections import defaultdict

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

    def search_issues(self, jql: str):
        """Search for issues using JQL (returns IDs only)"""
        results = []
        start_at = 0
        max_results = 100
        
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            payload = {"jql": jql}
            params = {"startAt": start_at, "maxResults": max_results}
            
            try:
                response = requests.post(url, json=payload, params=params, auth=self.auth, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"❌ Search failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                
                if start_at + len(issues) >= data.get('total', 0):
                    break
                    
                start_at += len(issues)
                
            except Exception as e:
                logger.error(f"❌ Exception searching issues: {e}")
                break
                
        return results

    def get_issue_details(self, issue_id_or_key):
        """Fetch details for a single issue"""
        url = f"{self.config.base_url}/rest/api/3/issue/{issue_id_or_key}"
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get issue {issue_id_or_key}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception getting issue: {e}")
            return None

def main():
    client = JiraClient()
    
    # JQL to find open tickets without a parent EPIC
    jql = f'project = {client.config.project_key} AND statusCategory != Done AND parent is EMPTY AND issuetype != Epic ORDER BY created DESC'
    
    logger.info(f"Searching for orphan tickets with JQL: {jql}")
    issues = client.search_issues(jql)
    
    logger.info(f"Found {len(issues)} orphan tickets. Fetching details...")
    
    print("\n=== ORPHAN TICKETS ===")
    for i, issue in enumerate(issues):
        # if i >= 20: break # Limit to 20 for speed
        
        issue_id = issue.get('id')
        if not issue_id: continue
        
        details = client.get_issue_details(issue_id)
        if not details: continue
        
        key = details.get('key')
        fields = details.get('fields', {})
        summary = fields.get('summary', 'No Summary')
        issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
        created = fields.get('created', 'Unknown')
        
        print(f"[{key}] {issue_type}: {summary}")

if __name__ == "__main__":
    main()
