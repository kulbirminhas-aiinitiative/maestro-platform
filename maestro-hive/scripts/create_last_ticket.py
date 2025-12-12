import os
import sys
import requests

# Configuration
JIRA_BASE_URL = "https://fifth9.atlassian.net"
PROJECT_KEY = "MD"
AUTH_EMAIL = os.environ.get("JIRA_EMAIL")
AUTH_TOKEN = os.environ.get("JIRA_TOKEN")
EPIC_KEY = "MD-3131"

if not AUTH_EMAIL or not AUTH_TOKEN:
    print("Please set JIRA_EMAIL and JIRA_TOKEN environment variables.")
    sys.exit(1)

AUTH = (AUTH_EMAIL, AUTH_TOKEN)
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def text_to_adf(text):
    content = []
    for paragraph in text.split('\n\n'):
        if not paragraph.strip():
            continue
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": paragraph.strip()}]
        })
    return {"type": "doc", "version": 1, "content": content}

def create_issue(summary, description, issuetype, parent_key=None, labels=None):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": text_to_adf(description),
            "issuetype": {"name": issuetype}
        }
    }
    if parent_key:
        payload["fields"]["parent"] = {"key": parent_key}
    if labels:
        payload["fields"]["labels"] = labels

    response = requests.post(url, json=payload, auth=AUTH, headers=HEADERS)
    if response.status_code == 201:
        data = response.json()
        print(f"Created {issuetype}: {data['key']} - {summary}")
    else:
        print(f"Failed to create {issuetype}: {summary}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

def main():
    story = {
        "summary": "RIQ: Cleanup Cron Job",
        "description": """Implement a background job to clean up old completed requests.

Requirements:
1. Scheduled task.
2. Delete completed/failed > 7 days.
3. Preserve dead letters.

Acceptance Criteria:
* Script deletes old records correctly.""",
    }
    create_issue(story["summary"], story["description"], "Story", parent_key=EPIC_KEY, labels=["architecture", "resilience"])

if __name__ == "__main__":
    main()
