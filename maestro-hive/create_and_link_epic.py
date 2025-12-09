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

# 1. Create the EPIC
create_url = f"{c.base_url}/rest/api/3/issue"
epic_payload = {
    "fields": {
        "project": {"key": c.project_key},
        "summary": "[EPIC] Gap Analysis Remediation - Quality & Templates",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "This EPIC tracks the remediation of gaps identified by the automated gap analysis tool, specifically focusing on Quality Gates and Code Generation Templates."
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Epic"}
    }
}

print("Creating EPIC...")
resp = requests.post(create_url, auth=auth, json=epic_payload, headers={"Accept": "application/json", "Content-Type": "application/json"})

if resp.status_code not in [200, 201]:
    print(f"Failed to create EPIC: {resp.status_code} - {resp.text}")
    exit(1)

epic_key = resp.json()['key']
print(f"Created EPIC: {epic_key}")

# 2. Link tickets to the EPIC
# Tickets are MD-2813 to MD-2830
tickets = [f"MD-{i}" for i in range(2813, 2831)]

print(f"Linking {len(tickets)} tickets to {epic_key}...")

# For JIRA Cloud, we usually set the 'parent' field for the issue to the EPIC key
# Or use the 'epic link' field if it's an older configuration, but 'parent' is standard for Next-Gen and increasingly Classic.
# Let's try updating the 'parent' field first.

success_count = 0
for ticket in tickets:
    update_url = f"{c.base_url}/rest/api/3/issue/{ticket}"
    update_payload = {
        "fields": {
            "parent": {"key": epic_key}
        }
    }
    
    r = requests.put(update_url, auth=auth, json=update_payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
    
    if r.status_code == 204:
        print(f"Linked {ticket} to {epic_key}")
        success_count += 1
    else:
        print(f"Failed to link {ticket}: {r.status_code} - {r.text}")

print(f"Successfully linked {success_count}/{len(tickets)} tickets.")
