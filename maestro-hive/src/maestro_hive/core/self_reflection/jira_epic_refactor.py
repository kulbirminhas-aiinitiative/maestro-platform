#!/usr/bin/env python3
"""
JIRA Epic Refactor Script
Executes the consolidation plan defined in JIRA_EPIC_ANALYSIS.txt.
"""

import os
import sys
import logging
import requests
import json
from typing import List, Dict, Any

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

class JiraRefactor:
    def __init__(self):
        self.config = JiraConfig()
        self.auth = (self.config.email, self.config.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    def _url(self, path: str) -> str:
        return f"{self.config.base_url}/rest/api/3/{path}"

    def update_issue(self, key: str, fields: Dict[str, Any]):
        """Update issue fields"""
        url = self._url(f"issue/{key}")
        response = requests.put(url, json={"fields": fields}, auth=self.auth, headers=self.headers)
        if response.status_code == 204:
            logger.info(f"✅ Updated {key}")
        else:
            logger.error(f"❌ Failed to update {key}: {response.status_code} - {response.text}")

    def add_comment(self, key: str, body: str):
        """Add comment to issue"""
        url = self._url(f"issue/{key}/comment")
        payload = {
            "body": {
                "version": 1,
                "type": "doc",
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": body}]
                }]
            }
        }
        requests.post(url, json=payload, auth=self.auth, headers=self.headers)

    def delete_issue(self, key: str):
        """Delete an issue"""
        url = self._url(f"issue/{key}")
        response = requests.delete(url, auth=self.auth, headers=self.headers)
        if response.status_code == 204:
            logger.info(f"✅ Deleted {key}")
        else:
            logger.error(f"❌ Failed to delete {key}: {response.status_code}")

    def set_parent(self, child_key: str, parent_key: str):
        """Set parent epic for an issue"""
        # Try 'parent' field first (modern JIRA)
        self.update_issue(child_key, {"parent": {"key": parent_key}})

    def transition_to_done(self, key: str):
        """Attempt to transition issue to Done"""
        # 1. Get transitions
        url = self._url(f"issue/{key}/transitions")
        response = requests.get(url, auth=self.auth, headers=self.headers)
        if response.status_code != 200:
            logger.error(f"Could not fetch transitions for {key}")
            return

        transitions = response.json().get('transitions', [])
        done_trans = next((t for t in transitions if t['name'].lower() in ['done', 'closed', 'complete', 'resolved']), None)
        
        if done_trans:
            # 2. Execute transition
            t_url = self._url(f"issue/{key}/transitions")
            payload = {"transition": {"id": done_trans['id']}}
            r = requests.post(t_url, json=payload, auth=self.auth, headers=self.headers)
            if r.status_code == 204:
                logger.info(f"✅ Transitioned {key} to {done_trans['name']}")
            else:
                logger.error(f"❌ Failed to transition {key}")
        else:
            logger.warning(f"⚠️ No 'Done' transition found for {key}. Available: {[t['name'] for t in transitions]}")

    def run(self):
        logger.info("🚀 Starting JIRA Epic Refactor...")

        # 1. Rename MD-2382
        logger.info("--- Step 1: Renaming MD-2382 ---")
        new_summary = "[PLATFORM] Quality Fabric & Evolutionary Templates (Conductor Integration)"
        self.update_issue("MD-2382", {"summary": new_summary})

        # 2. Link New Tickets (MD-2700 to MD-2727)
        logger.info("--- Step 2: Linking New Tickets ---")
        # Generate list of keys
        new_tickets = [f"MD-{i}" for i in range(2700, 2728)]
        for ticket in new_tickets:
            logger.info(f"Linking {ticket} to MD-2382...")
            self.set_parent(ticket, "MD-2382")

        # 3. Merge MD-2384 and MD-2441
        logger.info("--- Step 3: Merging Old Epics ---")
        for old_epic in ["MD-2384", "MD-2441"]:
            self.add_comment(old_epic, "MERGED: This Epic has been consolidated into MD-2382 as part of the Conductor Integration strategy.")
            self.update_issue(old_epic, {"summary": f"[MERGED] {old_epic} (See MD-2382)"})
            self.transition_to_done(old_epic)

        # 4. Delete MD-2492
        logger.info("--- Step 4: Deleting Test Epic ---")
        self.delete_issue("MD-2492")

        logger.info("✨ Refactor Complete!")

if __name__ == "__main__":
    JiraRefactor().run()
