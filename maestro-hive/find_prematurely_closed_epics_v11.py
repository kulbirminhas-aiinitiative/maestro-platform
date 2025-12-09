#!/usr/bin/env python3
import os
import requests
import json
import logging
import time

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

    def search_issues(self, jql, fields=["summary", "status", "parent"]):
        results = []
        next_page_token = None
        
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            payload = {"jql": jql, "fields": fields, "maxResults": 100}
            if next_page_token:
                payload["nextPageToken"] = next_page_token
            
            try:
                response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
                if response.status_code != 200: 
                    logger.error(f"Search failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token: break
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

def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def main():
    logger.info("Starting V11 - Optimized Batch Search")
    client = JiraClient()
    
    # 1. Find all Done EPICs
    logger.info("Searching for Done EPICs...")
    jql_epics = f'project = {client.config.project_key} AND issuetype = Epic AND statusCategory = Done'
    done_epics = client.search_issues(jql_epics, fields=["key"])
    logger.info(f"Found {len(done_epics)} Done EPICs.")
    
    if not done_epics:
        return

    epic_keys = [e['key'] for e in done_epics]
    prematurely_closed_keys = set()
    
    # 2. Batch check for open children
    # We will search for open tickets whose parent is in the batch
    batch_size = 50
    batches = list(chunk_list(epic_keys, batch_size))
    
    logger.info(f"Checking children in {len(batches)} batches...")
    
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)}...", end='\r')
        
        # JQL: parent in (A, B, C) AND statusCategory != Done
        parents_str = ",".join(batch)
        jql_check = f'parent in ({parents_str}) AND statusCategory != Done'
        
        # We only need the parent field to know which EPIC has open children
        open_children = client.search_issues(jql_check, fields=["parent"])
        
        for child in open_children:
            # The 'parent' field in the response usually contains the parent object
            # But sometimes it's just the ID or Key depending on expansion.
            # Standard fields response usually has 'parent': {'key': 'MD-123', ...}
            if 'fields' in child and 'parent' in child['fields']:
                parent_key = child['fields']['parent']['key']
                prematurely_closed_keys.add(parent_key)
    
    print("") # Newline after progress
    
    if not prematurely_closed_keys:
        logger.info("No prematurely closed EPICs found.")
        return

    # 3. Reopen them
    logger.info(f"Found {len(prematurely_closed_keys)} EPICs to reopen: {', '.join(prematurely_closed_keys)}")
    
    for epic_key in prematurely_closed_keys:
        client.transition_issue(epic_key, "In Progress")

if __name__ == "__main__":
    main()
