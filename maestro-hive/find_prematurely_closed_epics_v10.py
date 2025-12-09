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

def main():
    client = JiraClient()
    
    # 1. Find all Done EPICs
    logger.info("Searching for Done EPICs...")
    jql_epics = f'project = {client.config.project_key} AND issuetype = Epic AND statusCategory = Done'
    done_epics = client.search_issues(jql_epics)
    logger.info(f"Found {len(done_epics)} Done EPICs.")
    
    prematurely_closed = []
    
    # 2. Check each EPIC for open children
    # Optimization: Search for ALL open tickets that have a parent which is in our done_epics list
    # But JQL 'parent in (...)' has limits.
    # Better: Iterate but print progress.
    
    count = 0
    for epic in done_epics:
        count += 1
        if count % 10 == 0:
            print(f"Processed {count}/{len(done_epics)} EPICs...", end='\r')
            
        epic_key = epic['key']
        jql_children = f'parent = {epic_key} AND statusCategory != Done'
        
        # Use maxResults=1 because we only need to know if ANY exist
        url = f"{client.config.base_url}/rest/api/3/search/jql"
        payload = {"jql": jql_children, "fields": ["key"], "maxResults": 1}
        try:
            resp = requests.post(url, json=payload, auth=client.auth, headers=client.headers)
            if resp.status_code == 200 and resp.json().get('total', 0) > 0:
                logger.info(f"🚨 EPIC {epic_key} is Done but has open tickets.")
                prematurely_closed.append(epic)
        except: pass
    
    if not prematurely_closed:
        logger.info("No prematurely closed EPICs found.")
        return

    # 3. Reopen them
    logger.info(f"\nReopening {len(prematurely_closed)} EPICs...")
    for epic in prematurely_closed:
        client.transition_issue(epic['key'], "In Progress")

if __name__ == "__main__":
    main()
