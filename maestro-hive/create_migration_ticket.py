#!/usr/bin/env python3
import requests
import os
import json

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
        self.email = os.environ.get('JIRA_EMAIL', self.config_values.get('JIRA_EMAIL', ''))
        self.api_token = os.environ.get('JIRA_API_TOKEN', self.config_values.get('JIRA_API_TOKEN', ''))

c = JiraConfig()
auth = (c.email, c.api_token)
headers = {"Accept": "application/json", "Content-Type": "application/json"}

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
        resp = requests.post(url, auth=auth, headers=headers, json=payload)
        if resp.status_code == 201:
            data = resp.json()
            key = data['key']
            print(f"✅ Created {issuetype}: {key} - {summary}")
            return key
        else:
            print(f"❌ Failed to create {summary}: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Error creating issue: {e}")
        return None

# --- TICKET CONTENT ---

migration_ticket = {
    "summary": "Migrate GitHub Repositories to Fifth-9 Corporate Environment",
    "description": """
**Context**: 
Currently, the project repositories (e.g., `maestro-platform`) are hosted in a personal GitHub account (`kulbirminhas-aiinitiative`). To ensure corporate governance, security, and proper ownership, these must be migrated to the `fifth-9` GitHub organization.

**Objective**:
Migrate all relevant repositories and update all references to point to the new corporate environment.

**Scope of Work**:
1. **Inventory**: Identify all repositories currently used by the Maestro platform.
2. **Migration**: 
   - Create new repositories in the `fifth-9` organization.
   - Push all branches, tags, and commit history to the new remotes.
3. **Relinking**:
   - Update local git remotes on all development machines/agents.
   - Update `pyproject.toml`, `package.json`, and other config files containing repo URLs.
   - Update CI/CD pipelines (Jenkins, GitHub Actions) to pull from the new location.
   - Update any submodules or dependency links.
4. **Verification**:
   - Verify that builds succeed from the new location.
   - Verify that automated agents can access the new repos.

**Acceptance Criteria**:
- All code is accessible under `github.com/fifth-9/<repo>`.
- The old repositories are archived or updated with a redirection notice.
- CI/CD pipelines are green using the new URLs.
"""
}

if __name__ == "__main__":
    print("--- CREATING MIGRATION TICKET ---")
    create_issue(migration_ticket["summary"], migration_ticket["description"], priority="High")
    print("--- DONE ---")
