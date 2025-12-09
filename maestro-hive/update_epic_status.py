#!/usr/bin/env python3
"""
Update EPIC status to 'In Progress' if it has open child tasks.
"""

import os
import sys
import logging
import requests
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JiraConfig:
    """JIRA configuration"""
    CONFIG_FILE = "/home/ec2-user/projects/maestro-frontend-production/.jira-config"

    def __init__(self):
        self.config_values = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.config_values[key.strip()] = value.strip()
        
        self.base_url = os.environ.get('JIRA_BASE_URL', self.config_values.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'))
        self.email = os.environ.get('JIRA_EMAIL', self.config_values.get('JIRA_EMAIL', ''))
        self.api_token = os.environ.get('JIRA_API_TOKEN', self.config_values.get('JIRA_API_TOKEN', ''))
        self.project_key = os.environ.get('JIRA_PROJECT_KEY', self.config_values.get('JIRA_PROJECT_KEY', 'MD'))

class JiraClient:
    def __init__(self):
        self.config = JiraConfig()
        self.auth = (self.config.email, self.config.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    def _url(self, path: str) -> str:
        return f"{self.config.base_url}/rest/api/3/{path}"

    def search_issues(self, jql: str, fields: list = None):
        """Search for issues using JQL"""
        results = []
        start_at = 0
        max_results = 100
        
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            payload = {"jql": jql}
            params = {"startAt": start_at, "maxResults": max_results}
            if fields:
                params["fields"] = ",".join(fields)
            
            try:
                response = requests.post(url, json=payload, params=params, auth=self.auth, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"❌ Search failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                
                if start_at + len(issues) >= data.get('total', 0):
                    break
                    
                start_at += len(issues)
                
            except Exception as e:
                logger.error(f"❌ Exception searching issues: {e}")
                break
                
        return results

    def get_issue_details(self, issue_id_or_key):
        url = self._url(f"issue/{issue_id_or_key}")
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def get_transitions(self, issue_key):
        url = self._url(f"issue/{issue_key}/transitions")
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers)
            if response.status_code == 200:
                return response.json().get('transitions', [])
            return []
        except:
            return []

    def transition_issue(self, issue_key, transition_name):
        transitions = self.get_transitions(issue_key)
        target = next((t for t in transitions if t['name'].lower() == transition_name.lower()), None)
        
        if not target:
            # Try partial match or common variations
            if transition_name.lower() == "in progress":
                target = next((t for t in transitions if t['name'].lower() in ["in progress", "start progress", "reopen issue"]), None)
            
        if not target:
            logger.warning(f"Transition '{transition_name}' not found for {issue_key}. Available: {[t['name'] for t in transitions]}")
            return False
            
        url = self._url(f"issue/{issue_key}/transitions")
        payload = {"transition": {"id": target['id']}}
        
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"✅ Transitioned {issue_key} to '{target['name']}'")
                return True
            else:
                logger.error(f"❌ Failed to transition {issue_key}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception transitioning {issue_key}: {e}")
            return False

def main():
    client = JiraClient()
    
    # 1. Find all EPICs
    logger.info("Searching for all EPICs...")
    epics = client.search_issues(f'project = {client.config.project_key} AND issuetype = Epic')
    logger.info(f"Found {len(epics)} EPICs.")
    
    for i, epic_stub in enumerate(epics):
        epic_id = epic_stub.get('id')
        epic = client.get_issue_details(epic_id)
        if not epic:
            logger.warning(f"Could not fetch details for EPIC ID {epic_id}")
            continue

        epic_key = epic.get('key')
        logger.info(f"Processing EPIC {i+1}/{len(epics)}: {epic_key}")
        
        fields = epic.get('fields', {})
        status_field = fields.get('status', {})
        epic_status = status_field.get('name', 'Unknown')
        
        # 2. Find child tasks that are NOT Done
        jql_open_children = f'parent = "{epic_key}" AND statusCategory != Done'
        # logger.info(f"Checking children for {epic_key} with JQL: {jql_open_children}")
        # search_issues returns stubs, but we only need count, so that's fine.
        open_children = client.search_issues(jql_open_children)
        
        if open_children:
            logger.info(f"[{epic_key}] has {len(open_children)} open tasks. Current status: {epic_status}")
            
            if epic_status.lower() != "in progress":
                logger.info(f"[{epic_key}] Updating status to In Progress...")
                client.transition_issue(epic_key, "In Progress")
        else:
             logger.info(f"[{epic_key}] has 0 open tasks. Current status: {epic_status}")

if __name__ == "__main__":
    main()
