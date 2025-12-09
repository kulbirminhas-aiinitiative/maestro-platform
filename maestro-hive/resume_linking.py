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

epic_key = "MD-2841"
# Resume from MD-2816
tickets = [f"MD-{i}" for i in range(2816, 2831)]

print(f"Resuming linking {len(tickets)} tickets to {epic_key}...")

success_count = 0
for ticket in tickets:
    update_url = f"{c.base_url}/rest/api/3/issue/{ticket}"
    update_payload = {
        "fields": {
            "parent": {"key": epic_key}
        }
    }
    
    try:
        r = requests.put(update_url, auth=auth, json=update_payload, headers={"Accept": "application/json", "Content-Type": "application/json"}, timeout=10)
        
        if r.status_code == 204:
            print(f"Linked {ticket} to {epic_key}")
            success_count += 1
        else:
            print(f"Failed to link {ticket}: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Error linking {ticket}: {e}")
    
    # Small delay to avoid rate limits or connection issues
    time.sleep(0.5)

print(f"Successfully linked {success_count}/{len(tickets)} tickets.")
