#!/usr/bin/env python3
import requests
import os
import json
import sys

# --- CONFIGURATION ---
PROJECT_KEY = "MD"

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
        self.email = os.environ.get('JIRA_EMAIL', self.config_values.get('JIRA_EMAIL', 'kulbir.minhas@fifth-9.com'))
        self.api_token = os.environ.get('JIRA_API_TOKEN', self.config_values.get('JIRA_API_TOKEN', ''))

c = JiraConfig()
auth = (c.email, c.api_token)
headers = {"Accept": "application/json", "Content-Type": "application/json"}

def search_issue(summary):
    url = f"{c.base_url}/rest/api/3/search"
    jql = f'project = {PROJECT_KEY} AND summary ~ "{summary}"'
    params = {
        "jql": jql,
        "fields": "key,summary,description,status"
    }
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("issues", [])
    except Exception as e:
        print(f"Error searching for issue: {e}")
        return []

def main():
    print("Searching for 'Demo server hardening'...")
    issues = search_issue("Demo server hardening")
    if issues:
        for issue in issues:
            print(f"Found: {issue['key']} - {issue['fields']['summary']}")
            print("Description:")
            print(json.dumps(issue['fields']['description'], indent=2))
    else:
        print("No 'Demo server hardening' ticket found.")

    print("\nSearching for 'Dev server hardening' or 'Harden Dev Environment'...")
    issues = search_issue("Harden Dev Environment")
    if issues:
        for issue in issues:
            print(f"Found: {issue['key']} - {issue['fields']['summary']}")
    else:
        print("No 'Harden Dev Environment' ticket found.")

if __name__ == "__main__":
    main()
