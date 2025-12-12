#!/usr/bin/env python3
import requests
import os
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
headers = {"Accept": "application/json", "Content-Type": "application/json"}

def reopen_issue(key):
    # 1. Get transitions
    url = f"{c.base_url}/rest/api/3/issue/{key}/transitions"
    resp = requests.get(url, auth=auth, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to get transitions for {key}")
        return

    transitions = resp.json().get('transitions', [])
    # Look for "To Do", "In Progress", or "Reopen"
    target_id = None
    for t in transitions:
        name = t['name'].lower()
        if 'to do' in name or 'reopen' in name or 'backlog' in name:
            target_id = t['id']
            print(f"Found transition: {t['name']} ({target_id})")
            break
    
    if target_id:
        payload = {"transition": {"id": target_id}}
        resp = requests.post(url, auth=auth, headers=headers, json=payload)
        print(f"Reopened {key}: {resp.status_code}")
    else:
        print(f"No suitable transition found for {key}. Available: {[t['name'] for t in transitions]}")

if __name__ == "__main__":
    print("Reopening incomplete tickets...")
    reopen_issue("MD-3031")
    reopen_issue("MD-3032")
