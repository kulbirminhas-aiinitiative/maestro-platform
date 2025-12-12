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
    if resp.status_code == 201:
        print(f"✅ Comment added to {key}")
    else:
        print(f"❌ Failed to add comment to {key}: {resp.status_code} - {resp.text}")

tickets = ["MD-3091", "MD-3092", "MD-3093", "MD-3094"]
message = (
    "⚠️ CRITICAL ARCHITECTURE REVIEW UPDATE (2025-12-11) ⚠️\n\n"
    "A comprehensive review has been conducted by the Architecture Team (Gemini 3 Pro).\n"
    "Please refer to the file `MD-3091_3094_TICKETS.md` in the `maestro-hive` repository for the latest detailed gap analysis, status updates, and implementation plan.\n\n"
    "Summary of Findings:\n"
    "- MD-3091: INCOMPLETE (Missing State Persistence). Correction ticket MD-3091-CORRECTION created.\n"
    "- MD-3092: PARTIAL (Syntax check only, missing linting).\n"
    "- MD-3093: FAILED (Missing prompt injection for constraints).\n"
    "- MD-3094: FAILED (Token budget check not wired up).\n\n"
    "Please align all future work with the specifications in `MD-3091_3094_TICKETS.md`."
)

print("Updating JIRA tickets with reference to MD-3091_3094_TICKETS.md...")
for ticket in tickets:
    add_comment(ticket, message)
