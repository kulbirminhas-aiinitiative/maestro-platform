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
        payload = {"jql": jql, "fields": ["status", "issuetype", "subtasks"], "maxResults": 100}
        results = []
        while True:
            try:
                resp = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
                if resp.status_code != 200: break
                data = resp.json()
                results.extend(data.get('issues', []))
                if len(results) >= data.get('total', 0): break
                payload['startAt'] = len(results)
            except: break
        return results

    def get_children(self, parent_key):
        jql = f"parent = {parent_key}"
        return self.search(jql)

    def transition_to_inprogress(self, issue_key):
        # Get transitions
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
            
        # Transition
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
    
    # 1. Find all Done issues (Epics and Stories/Tasks with subtasks)
    logger.info("Searching for Done issues...")
    # We check Epics separately from standard issues with subtasks
    
    # Check Epics
    jql_epics = f"project = {client.config.project_key} AND issuetype = Epic AND statusCategory = Done"
    epics = client.search(jql_epics)
    logger.info(f"Found {len(epics)} Done Epics.")
    
    for epic in epics:
        children = client.get_children(epic['key'])
        open_children = [c for c in children if c['fields']['status']['statusCategory']['key'] != 'done']
        
        if open_children:
            logger.info(f"Epic {epic['key']} is Done but has {len(open_children)} open children.")
            client.transition_to_inprogress(epic['key'])

    # Check Standard Issues with Subtasks
    jql_issues = f"project = {client.config.project_key} AND issuetype != Epic AND statusCategory = Done"
    issues = client.search(jql_issues)
    logger.info(f"Found {len(issues)} Done standard issues.")
    
    for issue in issues:
        subtasks = issue['fields'].get('subtasks', [])
        if not subtasks: continue
        
        # Need to fetch subtask status details if not fully present, but usually 'subtasks' field has status
        # Actually 'subtasks' in search result usually contains minimal info.
        # Let's check if any subtask is not done.
        
        has_open_subtask = False
        for st in subtasks:
            # We might need to fetch the subtask to be sure of its status category, 
            # but let's see what's in the field.
            # Usually it has 'status'.
            if 'status' in st['fields']:
                # We need statusCategory. If not present, we might need to fetch.
                # Let's assume we need to fetch if we want to be robust.
                pass
        
        # Better approach: Search for open subtasks of this issue
        jql_open_subtasks = f"parent = {issue['key']} AND statusCategory != Done"
        open_subtasks = client.search(jql_open_subtasks)
        
        if open_subtasks:
            logger.info(f"Issue {issue['key']} is Done but has {len(open_subtasks)} open subtasks.")
            client.transition_to_inprogress(issue['key'])

if __name__ == "__main__":
    main()
