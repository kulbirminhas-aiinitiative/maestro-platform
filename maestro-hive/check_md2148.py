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
url = f"{c.base_url}/rest/api/3/issue/MD-2148"
resp = requests.get(url, auth=auth, headers={"Accept": "application/json"})
data = resp.json()
print(f"MD-2148 Status: {data['fields']['status']['name']}")

# Check children (if Epic) or Subtasks
if data['fields']['issuetype']['name'] == 'Epic':
    jql = f"parent = MD-2148"
    resp = requests.get(f"{c.base_url}/rest/api/3/search", params={"jql": jql}, auth=auth, headers={"Accept": "application/json"})
    print("Children:")
    for i in resp.json().get('issues', []):
        print(f"  {i['key']}: {i['fields']['status']['name']}")
else:
    print("Subtasks:")
    for st in data['fields']['subtasks']:
        print(f"  {st['key']}: {st['fields']['status']['name']}")
