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

def transition_issue(key, transition_id):
    url = f"{c.base_url}/rest/api/3/issue/{key}/transitions"
    payload = {
        "transition": {
            "id": transition_id
        }
    }
    resp = requests.post(url, auth=auth, headers=headers, json=payload)
    print(f"Transition {key}: {resp.status_code}")

def add_comment(key, body):
    url = f"{c.base_url}/rest/api/3/issue/{key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": body}
                    ]
                }
            ]
        }
    }
    resp = requests.post(url, auth=auth, headers=headers, json=payload)
    print(f"Comment {key}: {resp.status_code}")

# 1. Add comment
comment = """
Implemented IterativeExecutor in `src/maestro_hive/core/execution/iterative_executor.py`.
- Wraps command execution.
- Integrates with SelfHealingEngine.
- Implements retry loop (default 3 retries).
- Falls back to JIRA creation on failure.
"""
add_comment("MD-3028", comment)

# 2. Transition to Done (assuming ID 31 is Done, need to check available transitions first usually, but I'll guess based on standard workflows or just leave it for now if I can't verify)
# I'll just leave the comment for now as I don't want to guess the transition ID blindly without checking.
