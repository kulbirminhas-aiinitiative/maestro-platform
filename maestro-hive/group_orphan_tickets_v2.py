#!/usr/bin/env python3
"""
Group orphan tickets into new EPICs based on summary matching.
"""

import os
import sys
import logging
import requests
import json
import time

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

    def get_epic_by_summary(self, summary):
        jql = f'project = {self.config.project_key} AND issuetype = Epic AND summary ~ "{summary}"'
        issues = self.search_orphan_issues_generic(jql) # Need a generic search
        for issue in issues:
            if issue['fields']['summary'] == summary:
                return issue['key']
        return None

    def search_orphan_issues_generic(self, jql):
        results = []
        start_at = 0
        max_results = 100
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            payload = {"jql": jql, "fields": ["summary"]}
            params = {"startAt": start_at, "maxResults": max_results}
            try:
                response = requests.post(url, json=payload, params=params, auth=self.auth, headers=self.headers)
                if response.status_code != 200: break
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                if start_at + len(issues) >= data.get('total', 0): break
                start_at += len(issues)
            except: break
        return results

    def create_epic(self, summary, description):
        existing_key = self.get_epic_by_summary(summary)
        if existing_key:
            logger.info(f"ℹ️ EPIC already exists: {existing_key}")
            return existing_key

        url = self._url("issue")
        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                },
                "issuetype": {"name": "Epic"}
            }
        }
        try:
            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 201:
                data = response.json()
                logger.info(f"✅ Created EPIC {data['key']}: {summary}")
                return data['key']
            else:
                logger.error(f"❌ Failed to create EPIC: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception creating EPIC: {e}")
            return None

    def search_orphan_issues(self):
        jql = f'project = {self.config.project_key} AND statusCategory != Done AND parent is EMPTY AND issuetype != Epic'
        return self.search_orphan_issues_generic(jql)

    def search_orphan_issues_generic(self, jql):
        results = []
        start_at = 0
        max_results = 100
        while True:
            url = f"{self.config.base_url}/rest/api/3/search/jql"
            payload = {"jql": jql, "fields": ["summary"]}
            params = {"startAt": start_at, "maxResults": max_results}
            
            try:
                response = requests.post(url, json=payload, params=params, auth=self.auth, headers=self.headers)
                if response.status_code != 200: break
                
                data = response.json()
                issues = data.get('issues', [])
                results.extend(issues)
                
                if start_at + len(issues) >= data.get('total', 0): break
                start_at += len(issues)
            except: break
        return results

    def set_parent(self, issue_key, parent_key):
        url = self._url(f"issue/{issue_key}")
        payload = {
            "fields": {
                "parent": {"key": parent_key}
            }
        }
        try:
            response = requests.put(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code == 204:
                logger.info(f"🔗 Linked {issue_key} to {parent_key}")
                return True
            else:
                logger.error(f"❌ Failed to link {issue_key}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception linking {issue_key}: {e}")
            return False

def main():
    client = JiraClient()
    
    # 1. Define Groups
    groups = [
        {
            "name": "[Gateway] Kong API Gateway Implementation",
            "description": "Configuration of Kong API Gateway routes, plugins, and security.",
            "keywords": ["Kong", "API Gateway"]
        },
        {
            "name": "[QA] Testing & Validation",
            "description": "Testing tasks, validation frameworks, and test design.",
            "keywords": ["[Test]", "Test Task", "Integration Framework Validation", "Unit Tests"]
        },
        {
            "name": "[Maintenance] Code Quality & Tech Debt",
            "description": "Code formatting, linting, refactoring, and technical debt reduction.",
            "keywords": ["formatting", "linting", "Poetry", "logger", "TypeScript", "Tech Debt", "camelCase", "Zod"]
        },
        {
            "name": "[Analysis] Gap Analysis & Research",
            "description": "Gap analysis tasks and research items.",
            "keywords": ["[Gap Analysis]"]
        },
        {
            "name": "[Ops] Environment Synchronization",
            "description": "Tasks related to synchronizing environments and data.",
            "keywords": ["Sync", "Environment Version"]
        },
        {
            "name": "[Bugs] Known Issues & Fixes",
            "description": "Bug fixes and issue resolution.",
            "keywords": ["Bug:"]
        },
        {
            "name": "[Workflow] Human-in-the-Loop Controls",
            "description": "Implementation of human approval workflows, overrides, and escalation paths (MD-2158).",
            "keywords": ["MD-2158", "human approval", "pause and review", "contract amendment", "escalation path", "agent override", "manual quality gate"]
        },
        {
            "name": "[AI] Transparency & Agents",
            "description": "AI transparency and agent configuration tasks.",
            "keywords": ["AI transparency", "AI Agent"]
        }
    ]
    
    # 2. Fetch Orphans
    logger.info("Fetching orphan tickets...")
    orphans = client.search_orphan_issues()
    logger.info(f"Found {len(orphans)} orphan tickets.")
    
    # 3. Process Groups
    for group in groups:
        logger.info(f"\nProcessing Group: {group['name']}")
        
        # Find matching tickets first
        matches = []
        for i, issue in enumerate(orphans):
            # logger.info(f"DEBUG ISSUE: {issue}")
            fields = issue.get('fields', {})
            summary = fields.get('summary', '')
            if i == 0: logger.info(f"Sample Summary: {summary}")
            if any(kw.lower() in summary.lower() for kw in group['keywords']):
                matches.append(issue)
        
        if not matches:
            logger.info("No matching tickets found. Skipping EPIC creation.")
            continue
            
        logger.info(f"Found {len(matches)} tickets matching keywords: {group['keywords']}")
        
        # Create EPIC
        epic_key = client.create_epic(group['name'], group['description'])
        if not epic_key:
            logger.error("Failed to create EPIC. Skipping group.")
            continue
            
        # Link Tickets
        for issue in matches:
            client.set_parent(issue['key'], epic_key)
            # Remove from orphans list to avoid double matching (though unlikely with these keywords)
            # orphans.remove(issue) # Modifying list while iterating is bad, but we are iterating matches.
            
        # Small delay to be nice to API
        time.sleep(1)

if __name__ == "__main__":
    main()
