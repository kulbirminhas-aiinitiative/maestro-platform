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

    def search(self, jql):
        url = self._url("search/jql")
        payload = {"jql": jql, "fields": ["status", "parent"], "maxResults": 100}
        results = []
        start_at = 0
        while True:
            payload['startAt'] = start_at
            try:
                resp = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
                if resp.status_code != 200: break
                data = resp.json()
                issues = data.get('issues', [])
                results.extend(issues)
                if len(issues) == 0: break
                start_at += len(issues)
                if start_at >= data.get('total', 0): break
            except: break
        return results

    def get_issue(self, key):
        url = self._url(f"issue/{key}")
        try:
            resp = requests.get(url, auth=self.auth, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
        except: pass
        return None

    def transition_to_inprogress(self, issue_key):
        url = self._url(f"issue/{issue_key}/transitions")
        resp = requests.get(url, auth=self.auth, headers=self.headers)
        if resp.status_code != 200: return False
        
        transitions = resp.json().get('transitions', [])
        target_id = None
        for t in transitions:
            if t['name'].lower() == 'in progress':
                target_id = t['id']
                break
        
        if not target_id:
            logger.warning(f"No 'In Progress' transition found for {issue_key}")
            return False
            
        payload = {"transition": {"id": target_id}}
        resp = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
        if resp.status_code == 204:
            logger.info(f"✅ Moved {issue_key} to In Progress")
            return True
        else:
            logger.error(f"❌ Failed to move {issue_key}: {resp.status_code}")
            return False

def main():
    client = JiraClient()
    
    # 1. Find all OPEN tickets that have a parent
    logger.info("Searching for Open tickets with parents...")
    jql = f"project = {client.config.project_key} AND statusCategory != Done AND parent is not EMPTY"
    open_children = client.search(jql)
    logger.info(f"Found {len(open_children)} open children.")
    
    # 2. Collect unique parent keys
    parent_keys = set()
    for child in open_children:
        if 'parent' in child['fields']:
            parent_keys.add(child['fields']['parent']['key'])
            
    logger.info(f"Checking {len(parent_keys)} unique parents...")
    
    # 3. Check status of parents
    # We can do this efficiently by searching for parents that are DONE
    if not parent_keys:
        logger.info("No parents to check.")
        return

    # Chunking because JQL has length limits
    parents_list = list(parent_keys)
    chunk_size = 50
    
    for i in range(0, len(parents_list), chunk_size):
        chunk = parents_list[i:i+chunk_size]
        jql_parents = f"key in ({','.join(chunk)}) AND statusCategory = Done"
        done_parents = client.search(jql_parents)
        
        for parent in done_parents:
            logger.info(f"Parent {parent['key']} is Done but has open children.")
            client.transition_to_inprogress(parent['key'])

if __name__ == "__main__":
    main()
