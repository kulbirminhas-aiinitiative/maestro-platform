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
        self.project_key = os.environ.get('JIRA_PROJECT_KEY', self.config_values.get('JIRA_PROJECT_KEY', 'MD'))

c = JiraConfig()
auth = (c.email, c.api_token)
jql = f"project = {c.project_key}"
url = f"{c.base_url}/rest/api/3/search/jql"
payload = {"jql": jql, "fields": ["summary", "status"], "maxResults": 5}
resp = requests.post(url, json=payload, auth=auth, headers={"Accept": "application/json"})
print(f"Total: {resp.json().get('total', 0)}")
for i in resp.json().get('issues', []):
    print(f"{i['key']}: {i['fields']['status']['name']}")
