#!/usr/bin/env python3
import os
import requests
import json
import glob

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

def search_jql(jql, fields=["summary", "status", "issuetype", "description"]):
    url = f"{c.base_url}/rest/api/3/search/jql"
    results = []
    start_at = 0
    max_results = 50
    
    while True:
        payload = {
            "jql": jql,
            "fields": fields
        }
        params = {
            "startAt": start_at,
            "maxResults": max_results
        }
        
        try:
            resp = requests.post(url, auth=auth, headers=headers, json=payload, params=params)
            if resp.status_code != 200:
                print(f"Error searching JQL: {resp.status_code} - {resp.text}")
                break
            
            data = resp.json()
            issues = data.get('issues', [])
            results.extend(issues)
            
            if start_at + len(issues) >= data.get('total', 0):
                break
            
            start_at += len(issues)
        except Exception as e:
            print(f"Exception during search: {e}")
            break
            
    return results

def update_issue_description(key, description_text):
    url = f"{c.base_url}/rest/api/3/issue/{key}"
    
    desc_adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": description_text}]
            }
        ]
    }
    
    payload = {
        "fields": {
            "description": desc_adf
        }
    }
    
    resp = requests.put(url, auth=auth, headers=headers, json=payload)
    if resp.status_code == 204:
        print(f"  -> Updated description for {key}")
        return True
    else:
        print(f"  -> Failed to update {key}: {resp.status_code}")
        return False

def find_md_file_for_epic(epic_key):
    # 1. Check for exact match in filename
    files = glob.glob(f"**/*{epic_key}*.md", recursive=True)
    if files:
        return files[0]
    return None

def read_file_content(filepath):
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except:
        return None

def enrich_backlog():
    print("🔍 Scanning JIRA Backlog for missing information...")
    
    # 1. Get all Epics
    epics = search_jql("issuetype = Epic AND status != Done")
    print(f"Found {len(epics)} active Epics.")
    
    for epic in epics:
        key = epic['key']
        summary = epic['fields']['summary']
        desc = epic['fields'].get('description')
        
        print(f"\nProcessing {key}: {summary}")
        
        # Check Description
        if not desc:
            print("  -> Description is MISSING.")
            # Try to find MD file
            md_file = find_md_file_for_epic(key)
            if md_file:
                print(f"  -> Found matching documentation: {md_file}")
                content = read_file_content(md_file)
                if content:
                    # Truncate if too large (JIRA limit ~32k chars, keep safe at 10k)
                    if len(content) > 10000:
                        content = content[:10000] + "\n\n... (Truncated)"
                    update_issue_description(key, f"Documentation imported from {md_file}:\n\n{content}")
            else:
                print("  -> No documentation found. Adding template.")
                template = f"""
Objective:
Implement {summary}.

Technical Approach:
- TBD

Acceptance Criteria:
- [ ] Requirement 1
- [ ] Requirement 2
"""
                update_issue_description(key, template)
        else:
            print("  -> Description exists.")

        # Check Children
        children = search_jql(f"parent = {key}")
        if not children:
            print("  -> ⚠️  No child tasks found!")
            # In a real agent, we might create them, but here we just flag it.
        else:
            print(f"  -> Found {len(children)} children.")
            for child in children:
                c_key = child['key']
                c_summary = child['fields']['summary']
                c_desc = child['fields'].get('description')
                
                if not c_desc:
                    print(f"    -> Child {c_key} missing description. Updating...")
                    child_template = f"""
Task: {c_summary}
Parent Epic: {summary} ({key})

Implementation Details:
- Implement the logic required for {c_summary}.
- Ensure unit tests are added.

Acceptance Criteria:
- [ ] Code implemented
- [ ] Tests passed
- [ ] Code reviewed
"""
                    update_issue_description(c_key, child_template)

if __name__ == "__main__":
    enrich_backlog()
