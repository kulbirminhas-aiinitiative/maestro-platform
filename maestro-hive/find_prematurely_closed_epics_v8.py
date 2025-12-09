#!/usr/bin/env python3
import os
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        self.project_key = os.environ.get('JIRA_PROJECT_KEY', self.config_values.get('JIRA_PROJECT_KEY', 'MD'))

class JiraClient:
    def __init__(self):
        self.config = JiraConfig()
        self.auth = (self.config.email, self.config.api_token)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
    def _url(self, path: str) -> str:
        return f"{self.config.base_url}/rest/api/3/{path}"

    def search_issues(self, jql, fields=["summary", "status"]):
        results = []
        start_at = 0
        max_results = 100
        
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            # Back to POST, but without startAt/maxResults if they are causing issues, or fix them
            # The issue might be that startAt/maxResults must be integers, which they are.
            # Let's try sending them as query params with POST? No, that's weird.
            # Let's try sending ONLY jql and fields in body, and handle pagination manually if needed?
            # Or maybe the API version 3 requires specific structure.
            # Let's try to use `nextPageToken` if available.
            
            # Reverting to simple payload that worked in debug_payload_v2.py
            # But we need pagination.
            # Let's try to send startAt/maxResults again but ensure they are ints.
            
            payload = {
                "jql": jql,
                "fields": fields,
                "startAt": int(start_at),
                "maxResults": int(max_results)
            }
            
            try:
                response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
                if response.status_code != 200: 
                    logger.error(f"Search failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                
                if start_at + len(issues) >= data.get('total', 0): break
                start_at += len(issues)
            except Exception as e:
                logger.error(f"Search exception: {e}")
                break
        return results

    def transition_issue(self, issue_key, target_status_name="In Progress"):
        url = self._url(f"issue/{issue_key}/transitions")
        try:
            resp = requests.get(url, auth=self.auth, headers=self.headers)
            if resp.status_code != 200: return False
            
            transitions = resp.json().get('transitions', [])
            target_id = None
            for t in transitions:
                if t['name'].lower() == target_status_name.lower():
                    target_id = t['id']
                    break
            
            if not target_id:
                logger.warning(f"⚠️ No transition to '{target_status_name}' found for {issue_key}")
                return False
                
            payload = {"transition": {"id": target_id}}
            resp = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if resp.status_code == 204:
                logger.info(f"✅ Transitioned {issue_key} to '{target_status_name}'")
                return True
            else:
                logger.error(f"❌ Failed to transition {issue_key}: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception transitioning {issue_key}: {e}")
            return False

def main():
    client = JiraClient()
    
    # 1. Find all Done EPICs
    logger.info("Searching for Done EPICs...")
    jql_epics = f'project = {client.config.project_key} AND issuetype = Epic AND statusCategory = Done'
    done_epics = client.search_issues(jql_epics)
    logger.info(f"Found {len(done_epics)} Done EPICs.")
    
    prematurely_closed = []
    
    # 2. Check each EPIC for open children
    for epic in done_epics:
        epic_key = epic['key']
        jql_children = f'parent = {epic_key} AND statusCategory != Done'
        open_children = client.search_issues(jql_children)
        
        if open_children:
            logger.info(f"🚨 EPIC {epic_key} is Done but has {len(open_children)} open tickets.")
            prematurely_closed.append(epic)
            for child in open_children[:3]:
                print(f"   - {child['key']}: {child['fields']['status']['name']}")
    
    if not prematurely_closed:
        logger.info("No prematurely closed EPICs found.")
        return

    # 3. Reopen them
    logger.info(f"\nReopening {len(prematurely_closed)} EPICs...")
    for epic in prematurely_closed:
        client.transition_issue(epic['key'], "In Progress")

if __name__ == "__main__":
    main()
