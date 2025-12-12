#!/usr/bin/env python3
import requests
import os
import json

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
headers = {"Accept": "application/json", "Content-Type": "application/json"}

def add_comment(key, body):
    url = f"{c.base_url}/rest/api/3/issue/{key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": body}
                    ]
                }
            ]
        }
    }
    resp = requests.post(url, auth=auth, headers=headers, json=payload)
    print(f"Comment {key}: {resp.status_code}")

def update_description(key, new_content_adf):
    url = f"{c.base_url}/rest/api/3/issue/{key}"
    payload = {"fields": {"description": new_content_adf}}
    resp = requests.put(url, auth=auth, headers=headers, json=payload)
    print(f"Update Description {key}: {resp.status_code}")

# Audit Findings
audit_report = """
h2. Execution Readiness Audit Report (MD-3027)

The following gaps were identified during the code verification process:

*   ✅ **MD-3028 (IterativeExecutor)**: Implemented in `src/maestro_hive/core/execution/iterative_executor.py`. Verified working.
*   ✅ **MD-3029 (ErrorPatternAnalyzer)**: Implemented via `FailureDetector` in `src/maestro_hive/core/self_reflection/failure_detector.py`.
*   ✅ **MD-3030 (JiraBugReporter)**: Implemented via `GapToJira` in `src/maestro_hive/core/self_reflection/gap_to_jira.py`.
*   ❌ **MD-3031 (FixVerificationLoop)**: **GAP DETECTED**. Ticket is Closed/Done, but no implementation exists for polling JIRA resolved tickets to trigger re-verification.
*   ❌ **MD-3032 (ExecutionHistoryLogger)**: **GAP DETECTED**. Ticket is Closed/Done, but `RAGClient` uses in-memory storage only. No JSON/DB persistence implementation found in `src/maestro_hive/core/self_reflection/refactoring_engine.py`.

**Action Required:**
1.  Reopen MD-3031 and MD-3032.
2.  Implement persistence for Execution History.
3.  Implement JIRA polling loop for Fix Verification.
"""

# We need to construct the ADF for the comment/description.
# For simplicity, I'll just add a comment to the Epic.
# Updating the description is complex with ADF if we want to preserve existing content easily without fetching it first.
# The user asked to "add the details to the EPIC". A comment is safer and effective.

comment_adf = {
    "type": "doc",
    "version": 1,
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Execution Readiness Audit Report (MD-3027)"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "The following gaps were identified during the code verification process:"}]
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "✅ MD-3028 (IterativeExecutor): Implemented in src/maestro_hive/core/execution/iterative_executor.py. Verified working."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "✅ MD-3029 (ErrorPatternAnalyzer): Implemented via FailureDetector."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "✅ MD-3030 (JiraBugReporter): Implemented via GapToJira."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "❌ MD-3031 (FixVerificationLoop): GAP DETECTED. Ticket is Done, but no implementation exists for polling JIRA resolved tickets."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "❌ MD-3032 (ExecutionHistoryLogger): GAP DETECTED. Ticket is Done, but RAGClient uses in-memory storage only. No persistence found."}]}]
                }
            ]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Action Required: Reopen MD-3031 and MD-3032 to address these gaps."}]
        }
    ]
}

def add_audit_comment(key, adf_body):
    url = f"{c.base_url}/rest/api/3/issue/{key}/comment"
    payload = {"body": adf_body}
    resp = requests.post(url, auth=auth, headers=headers, json=payload)
    print(f"Audit Comment {key}: {resp.status_code}")

if __name__ == "__main__":
    add_audit_comment("MD-3027", comment_adf)
