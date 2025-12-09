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
            return None
        except:
            return None

    def search_issues(self, jql: str):
        results = []
        start_at = 0
        max_results = 100
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            payload = {
                "jql": jql,
                "fields": ["summary", "status", "issuetype"]
            }
            params = {"startAt": start_at, "maxResults": max_results}
            try:
                response = requests.post(url, json=payload, params=params, auth=self.auth, headers=self.headers)
                if response.status_code != 200: 
                    logger.error(f"Search failed: {response.status_code} - {response.text}")
                    break
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                if start_at + len(issues) >= data.get('total', 0): break
                start_at += len(issues)
            except Exception as e: 
                logger.error(f"Search exception: {e}")
                break
        return results

def main():
    client = JiraClient()
    issue_key = "MD-1791"
    logger.info(f"Fetching details for {issue_key}...")
    issue = client.get_issue_details(issue_key)
    
    if issue:
        fields = issue.get('fields', {})
        parent = fields.get('parent')
        
        print(f"\n=== {issue_key} Details ===")
        print(f"Summary: {fields.get('summary')}")
        print(f"Status: {fields.get('status', {}).get('name')}")
        
        if parent:
            parent_key = parent.get('key')
            parent_summary = parent.get('fields', {}).get('summary')
            parent_status = parent.get('fields', {}).get('status', {}).get('name')
            print(f"\n=== Parent EPIC: {parent_key} ===")
            print(f"Summary: {parent_summary}")
            print(f"Status: {parent_status}")
            
            # Find siblings
            print(f"\n=== Sibling Tickets in {parent_key} ===")
            siblings = client.search_issues(f'parent = "{parent_key}"')
            if siblings:
                print(f"DEBUG RAW ISSUE: {json.dumps(siblings[0], indent=2)}")
            for s in siblings:
                # print(f"DEBUG: {json.dumps(s, indent=2)}")
                key = s.get('key', 'UNKNOWN')
                fields = s.get('fields', {})
                summary = fields.get('summary', 'No Summary')
                status = fields.get('status', {}).get('name', 'Unknown')
                print(f"{key}: {summary} [{status}]")
        else:
            print("\nNo parent EPIC found.")
            
    else:
        print(f"Could not fetch {issue_key}")

if __name__ == "__main__":
    main()
