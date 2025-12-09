#!/usr/bin/env python3
import os
import requests
import json
import time

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

source_epic = "MD-2841"
target_epic = "MD-2842"

print(f"Moving tickets from {source_epic} to {target_epic}...")

# Get tickets in source epic
query = f'parent = {source_epic}'
payload = {"jql": query, "maxResults": 50, "fields": ["key"]}
resp = requests.post(f"{c.base_url}/rest/api/3/search/jql", auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})

if resp.status_code == 200:
    issues = resp.json().get('issues', [])
    print(f"Found {len(issues)} tickets to move.")
    
    for issue in issues:
        key = issue['key']
        print(f"Moving {key}...")
        update_url = f"{c.base_url}/rest/api/3/issue/{key}"
        update_payload = {"fields": {"parent": {"key": target_epic}}}
        
        try:
            r = requests.put(update_url, auth=auth, json=update_payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
            if r.status_code == 204:
                print(f"Moved {key}")
            else:
                print(f"Failed to move {key}: {r.status_code}")
        except Exception as e:
            print(f"Error moving {key}: {e}")
        time.sleep(0.2)
        
    # Verify source is empty
    resp = requests.post(f"{c.base_url}/rest/api/3/search/jql", auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
    remaining = len(resp.json().get('issues', []))
    if remaining == 0:
        print(f"{source_epic} is empty. Deleting...")
        requests.delete(f"{c.base_url}/rest/api/3/issue/{source_epic}", auth=auth)
        print(f"Deleted {source_epic}")
    else:
        print(f"{source_epic} still has {remaining} tickets.")

else:
    print(f"Error searching source epic: {resp.status_code}")
