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

# Check MD-2820
print("Checking MD-2820...")
resp = requests.get(f"{c.base_url}/rest/api/3/issue/MD-2820", auth=auth, headers={"Accept": "application/json"})
if resp.status_code == 200:
    fields = resp.json()['fields']
    parent = fields.get('parent')
    print(f"MD-2820 Parent: {parent['key'] if parent else 'None'}")
else:
    print(f"Error checking MD-2820: {resp.status_code}")

# Check MD-2841
print("Checking MD-2841...")
query = 'parent = MD-2841'
payload = {"jql": query, "fields": ["key"]}
resp = requests.post(f"{c.base_url}/rest/api/3/search/jql", auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
if resp.status_code == 200:
    issues = resp.json().get('issues', [])
    print(f"Tickets in MD-2841: {[i['key'] for i in issues]}")
