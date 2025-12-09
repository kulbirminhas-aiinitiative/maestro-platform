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
url = f"{c.base_url}/rest/api/3/search/jql"

query = 'key in (MD-2802, MD-2803, MD-2804, MD-2805, MD-2806)'
payload = {
    "jql": query,
    "fields": ["summary", "status"]
}

resp = requests.post(url, auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})

if resp.status_code == 200:
    issues = resp.json().get('issues', [])
    for issue in issues:
        print(f"{issue['key']}: {issue['fields']['summary']}")
