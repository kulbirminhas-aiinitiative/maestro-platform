#!/usr/bin/env python3
import os
import requests
import json
import glob
import re

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

def get_issue_description_text(issue):
    """Extract text from ADF description"""
    desc = issue['fields'].get('description')
    if not desc:
        return ""
    
    text_content = []
    
    def extract_text(node):
        if isinstance(node, dict):
            if node.get('type') == 'text':
                text_content.append(node.get('text', ''))
            elif 'content' in node:
                for child in node['content']:
                    extract_text(child)
        elif isinstance(node, list):
            for child in node:
                extract_text(child)
                
    extract_text(desc)
    return " ".join(text_content)

def append_to_description(key, current_desc_adf, new_text):
    url = f"{c.base_url}/rest/api/3/issue/{key}"
    
    # If no current description, create new
    if not current_desc_adf:
        current_desc_adf = {
            "type": "doc",
            "version": 1,
            "content": []
        }
    
    # Append new paragraph
    new_paragraph = {
        "type": "paragraph",
        "content": [{"type": "text", "text": new_text}]
    }
    
    current_desc_adf['content'].append(new_paragraph)
    
    payload = {
        "fields": {
            "description": current_desc_adf
        }
    }
    
    resp = requests.put(url, auth=auth, headers=headers, json=payload)
    if resp.status_code == 204:
        print(f"  -> Appended to description for {key}")
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

def enrich_backlog_v2():
    print("🔍 Scanning JIRA Backlog for documentation links...")
    
    # 1. Get all Epics
    epics = search_jql("issuetype = Epic AND status != Done")
    print(f"Found {len(epics)} active Epics.")
    
    for epic in epics:
        key = epic['key']
        summary = epic['fields']['summary']
        desc_adf = epic['fields'].get('description')
        desc_text = get_issue_description_text(epic)
        
        print(f"\nProcessing {key}: {summary}")
        
        # Try to find MD file
        md_file = find_md_file_for_epic(key)
        
        # Manual Mapping for Strategic Epics
        manual_mapping = {
            "MD-3027": "SELF_IMPROVEMENT_PLAN.md",
            "MD-2148": "IMPROVED_ARCHITECTURE_PLAN.md",
            "MD-3024": "EXECUTION_PLATFORM_DOCUMENTATION.md", # Assumption based on title
            "MD-2889": "MATURITY_ASSESSMENT_AND_ROADMAP.md", # Assumption
        }
        
        if not md_file and key in manual_mapping:
            md_file = manual_mapping[key]
            
        if md_file:
            print(f"  -> Found matching documentation: {md_file}")
            
            # Check if already linked
            if md_file in desc_text:
                print("  -> Documentation already linked.")
            else:
                print("  -> Linking documentation...")
                append_to_description(key, desc_adf, f"\n\nDocumentation Reference: {md_file}")
        else:
            print("  -> No specific documentation found.")

if __name__ == "__main__":
    enrich_backlog_v2()
