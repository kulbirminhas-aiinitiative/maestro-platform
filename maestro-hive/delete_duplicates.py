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

to_delete = ["MD-2850", "MD-2851", "MD-2854", "MD-2853", "MD-2852"]

print(f"Deleting {len(to_delete)} duplicate tickets...")

for ticket in to_delete:
    print(f"Deleting {ticket}...")
    resp = requests.delete(f"{c.base_url}/rest/api/3/issue/{ticket}", auth=auth)
    if resp.status_code == 204:
        print(f"Deleted {ticket}")
    else:
        print(f"Failed to delete {ticket}: {resp.status_code}")

print("Done.")
