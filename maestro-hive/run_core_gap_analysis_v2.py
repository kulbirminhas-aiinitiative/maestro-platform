#!/usr/bin/env python3
import os
import requests
import json
import subprocess
import sys

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

epic_key = "MD-2845"

# Verify EPIC exists
print(f"Verifying EPIC {epic_key}...")
resp = requests.get(f"{c.base_url}/rest/api/3/issue/{epic_key}", auth=auth)
if resp.status_code != 200:
    print(f"EPIC {epic_key} not found. Creating new one...")
    # Create new EPIC if missing
    create_url = f"{c.base_url}/rest/api/3/issue"
    epic_payload = {
        "fields": {
            "project": {"key": c.project_key},
            "summary": "[EPIC] Gap Analysis Remediation - Core Capabilities",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Remediation of Core Capability gaps."}]}]
            },
            "issuetype": {"name": "Epic"}
        }
    }
    resp = requests.post(create_url, auth=auth, json=epic_payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
    if resp.status_code in [200, 201]:
        epic_key = resp.json()['key']
        print(f"Created new EPIC: {epic_key}")
    else:
        print(f"Failed to create EPIC: {resp.status_code}")
        sys.exit(1)
else:
    print(f"EPIC {epic_key} found.")

# Run gap_to_jira.py
print(f"Running gap_to_jira.py for scope 'core' linked to {epic_key}...")

cmd = [
    "python3",
    "src/maestro_hive/core/self_reflection/gap_to_jira.py",
    "--scope", "core",
    "--parent-epic", epic_key
]

env = os.environ.copy()
env['JIRA_BASE_URL'] = c.base_url
env['JIRA_EMAIL'] = c.email
env['JIRA_API_TOKEN'] = c.api_token
env['JIRA_PROJECT_KEY'] = c.project_key

# Run and stream output
process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

for line in process.stdout:
    print(line, end='')

process.wait()

if process.returncode != 0:
    print("gap_to_jira.py failed!")
    sys.exit(process.returncode)

print("Done.")
