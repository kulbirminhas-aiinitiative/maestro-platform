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

def append_absolute_path(key, filename):
    abs_path = os.path.abspath(filename)
    
    url = f"{c.base_url}/rest/api/3/issue/{key}"
    
    # We will append a new paragraph
    # First, get current description to avoid overwriting if possible, but here we are just appending via a new PUT
    # Actually, PUT replaces fields. So we need to be careful.
    # The previous script used a "get then append" logic. I should replicate that or just add a comment with the full path if I want to be safe.
    # But the user asked for "ticket description should be elaborate".
    
    # Let's fetch first
    resp = requests.get(url, auth=auth, headers=headers)
    data = resp.json()
    current_desc = data['fields'].get('description')
    
    if not current_desc:
        current_desc = {"type": "doc", "version": 1, "content": []}
        
    # Check if path already exists
    text_content = json.dumps(current_desc)
    if abs_path in text_content:
        print(f"Path already in description for {key}")
        return

    # Append
    new_paragraph = {
        "type": "paragraph",
        "content": [
            {"type": "text", "text": "\n\nFull Documentation Path: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": abs_path, "marks": [{"type": "code"}]}
        ]
    }
    
    current_desc['content'].append(new_paragraph)
    
    payload = {"fields": {"description": current_desc}}
    resp = requests.put(url, auth=auth, headers=headers, json=payload)
    print(f"Updated {key}: {resp.status_code}")

if __name__ == "__main__":
    append_absolute_path("MD-3027", "SELF_IMPROVEMENT_PLAN.md")
