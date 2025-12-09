#!/usr/bin/env python3
import os
import requests
import json

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

c = JiraConfig()
auth = (c.email, c.api_token)

# Check both potential EPICs
for epic_key in ["MD-2843", "MD-2845"]:
    print(f"Checking tickets in {epic_key}...")
    query = f'parent = {epic_key}'
    payload = {
        "jql": query,
        "maxResults": 50,
        "fields": ["key", "summary", "status"]
    }

    resp = requests.post(f"{c.base_url}/rest/api/3/search/jql", auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})

    if resp.status_code == 200:
        issues = resp.json().get('issues', [])
        print(f"Found {len(issues)} tickets in {epic_key}:")
        for issue in issues:
            print(f"{issue['key']}: {issue['fields']['summary']} ({issue['fields']['status']['name']})")
    else:
        print(f"Error checking {epic_key}: {resp.status_code}")
