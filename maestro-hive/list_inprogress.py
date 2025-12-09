#!/usr/bin/env python3
import os
import requests
import json
import logging

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

def main():
    c = JiraConfig()
    auth = (c.email, c.api_token)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    # JQL to find In Progress tickets
    jql = f'project = {c.project_key} AND statusCategory = "In Progress"'
    
    url = f"{c.base_url}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "status", "parent"],
        "maxResults": 100
    }
    
    logger.info(f"Searching with JQL: {jql}")
    
    try:
        response = requests.post(url, json=payload, auth=auth, headers=headers)
        if response.status_code == 200:
            issues = response.json().get('issues', [])
            logger.info(f"Found {len(issues)} In Progress tickets.")
            for issue in issues:
                parent = issue['fields'].get('parent', {})
                parent_key = parent.get('key', 'None') if parent else 'None'
                print(f"[{issue['key']}] Parent: {parent_key} - {issue['fields']['summary']}")
        else:
            logger.error(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Exception: {e}")

if __name__ == "__main__":
    main()
