#!/usr/bin/env python3
import requests
import os
import json
import sys

# --- CONFIGURATION ---
PROJECT_KEY = "MD"
TICKET_SUMMARY = "Test Persona Creation, RAG Ingestion, and Chat from Frontend"

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

def search_issue(summary):
    url = f"{c.base_url}/rest/api/3/search"
    jql = f'project = {PROJECT_KEY} AND summary ~ "{summary}"'
    params = {
        "jql": jql,
        "fields": "key,summary,status"
    }
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("issues", [])
    except Exception as e:
        print(f"Error searching for issue: {e}")
        return []

def create_issue(summary, description, issuetype="Task", priority="High"):
    url = f"{c.base_url}/rest/api/3/issue"
    
    description_adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description
                    }
                ]
            }
        ]
    }

    payload = {
        "fields": {
            "project": {
                "key": PROJECT_KEY
            },
            "summary": summary,
            "description": description_adf,
            "issuetype": {
                "name": issuetype
            },
            "priority": {
                "name": priority
            }
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        issue_key = response.json()['key']
        print(f"Successfully created issue {issue_key}: {summary}")
        return issue_key
    except Exception as e:
        print(f"Failed to create issue: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def main():
    print(f"Checking for existing ticket: '{TICKET_SUMMARY}'...")
    existing_issues = search_issue(TICKET_SUMMARY)
    
    if existing_issues:
        print(f"Found {len(existing_issues)} existing issue(s):")
        for issue in existing_issues:
            print(f"- {issue['key']}: {issue['fields']['summary']} (Status: {issue['fields']['status']['name']})")
        print("Skipping creation to avoid duplicates.")
    else:
        print("No existing ticket found. Creating new ticket...")
        description = (
            "Comprehensive testing of the frontend integration with the backend services.\n\n"
            "Scope:\n"
            "1. Verify Persona Creation flow from the UI.\n"
            "2. Verify Persona Building process.\n"
            "3. Verify RAG Pipeline Ingestion (uploading documents, processing).\n"
            "4. Verify Communication with Agent (Chat interface) from the frontend.\n\n"
            "Ensure end-to-end functionality works as expected."
        )
        create_issue(TICKET_SUMMARY, description)

if __name__ == "__main__":
    main()
