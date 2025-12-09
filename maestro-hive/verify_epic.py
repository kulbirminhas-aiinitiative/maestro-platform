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

epic_key = "MD-2842"
print(f"Verifying tickets in {epic_key}...")

query = f'parent = {epic_key}'
payload = {
    "jql": query,
    "maxResults": 50,
    "fields": ["key"]
}

resp = requests.post(f"{c.base_url}/rest/api/3/search/jql", auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})

if resp.status_code == 200:
    issues = resp.json().get('issues', [])
    print(f"Found {len(issues)} tickets in {epic_key}.")
    keys = sorted([i['key'] for i in issues])
    print(f"Tickets: {keys}")
    
    expected = [f"MD-{i}" for i in range(2813, 2831)]
    missing = [t for t in expected if t not in keys]
    
    if not missing:
        print("SUCCESS: All 18 tickets are in the EPIC.")
    else:
        print(f"WARNING: Missing tickets: {missing}")
else:
    print(f"Error: {resp.status_code}")
