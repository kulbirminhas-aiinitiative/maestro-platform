#!/usr/bin/env python3
import os
import requests
import json
import time

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

target_epic = "MD-2842"
duplicate_epic = "MD-2841"

# 1. Link remaining tickets (MD-2829, MD-2830) to MD-2842
remaining_tickets = ["MD-2829", "MD-2830"]
print(f"Linking remaining tickets to {target_epic}...")

for ticket in remaining_tickets:
    update_url = f"{c.base_url}/rest/api/3/issue/{ticket}"
    update_payload = {
        "fields": {
            "parent": {"key": target_epic}
        }
    }
    try:
        r = requests.put(update_url, auth=auth, json=update_payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
        if r.status_code == 204:
            print(f"Linked {ticket} to {target_epic}")
        else:
            print(f"Failed to link {ticket}: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Error linking {ticket}: {e}")

# 2. Check if MD-2841 is empty
print(f"Checking if {duplicate_epic} is empty...")
query = f'"Epic Link" = {duplicate_epic} OR parent = {duplicate_epic}'
search_url = f"{c.base_url}/rest/api/3/search/jql"
payload = {
    "jql": query,
    "maxResults": 1
}
resp = requests.post(search_url, auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})

if resp.status_code == 200:
    issues = resp.json().get('issues', [])
    if len(issues) == 0:
        print(f"{duplicate_epic} is empty. Deleting...")
        delete_url = f"{c.base_url}/rest/api/3/issue/{duplicate_epic}"
        del_resp = requests.delete(delete_url, auth=auth)
        if del_resp.status_code == 204:
            print(f"Deleted duplicate EPIC {duplicate_epic}")
        else:
            print(f"Failed to delete {duplicate_epic}: {del_resp.status_code}")
    else:
        print(f"{duplicate_epic} is NOT empty. It has {resp.json()['total']} issues. Not deleting.")
        # If not empty, move them to MD-2842
        print(f"Moving remaining issues from {duplicate_epic} to {target_epic}...")
        # We need to fetch all of them
        payload['maxResults'] = 50
        resp = requests.post(search_url, auth=auth, json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
        issues = resp.json().get('issues', [])
        for issue in issues:
            key = issue['key']
            print(f"Moving {key} to {target_epic}...")
            update_url = f"{c.base_url}/rest/api/3/issue/{key}"
            update_payload = {"fields": {"parent": {"key": target_epic}}}
            requests.put(update_url, auth=auth, json=update_payload, headers={"Accept": "application/json", "Content-Type": "application/json"})
        
        # Now delete
        print(f"Deleting {duplicate_epic} after move...")
        requests.delete(f"{c.base_url}/rest/api/3/issue/{duplicate_epic}", auth=auth)
        print("Done.")

else:
    print(f"Error checking {duplicate_epic}: {resp.status_code}")

