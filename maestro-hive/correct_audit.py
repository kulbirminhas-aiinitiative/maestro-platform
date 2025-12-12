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

def transition_to_done(key):
    # 1. Get transitions
    url = f"{c.base_url}/rest/api/3/issue/{key}/transitions"
    resp = requests.get(url, auth=auth, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to get transitions for {key}")
        return

    transitions = resp.json().get('transitions', [])
    # Look for "Done" or "Close"
    target_id = None
    for t in transitions:
        name = t['name'].lower()
        if 'done' in name or 'close' in name or 'resolve' in name:
            target_id = t['id']
            print(f"Found transition: {t['name']} ({target_id})")
            break
    
    if target_id:
        payload = {"transition": {"id": target_id}}
        resp = requests.post(url, auth=auth, headers=headers, json=payload)
        print(f"Transitioned {key} to Done: {resp.status_code}")
    else:
        print(f"No suitable transition found for {key}. Available: {[t['name'] for t in transitions]}")

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

if __name__ == "__main__":
    print("Correcting audit findings...")
    
    # MD-3031
    add_comment("MD-3031", "CORRECTION: Implementation found in `src/maestro_hive/execution/fix_verification.py`. The previous audit missed this file. Closing ticket as Verified.")
    transition_to_done("MD-3031")
    
    # MD-3032
    add_comment("MD-3032", "CORRECTION: Implementation found in `src/maestro_hive/execution/history_logger.py`. SQLite persistence is implemented. Closing ticket as Verified.")
    transition_to_done("MD-3032")
    
    # Update Epic MD-3027
    add_comment("MD-3027", "CORRECTION: All child tickets have been verified. The previous audit was incorrect regarding MD-3031 and MD-3032. The code exists in `src/maestro_hive/execution/`. Epic is fully implemented.")
