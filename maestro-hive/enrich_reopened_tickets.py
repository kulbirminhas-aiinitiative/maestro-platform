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

def update_description(key, description_adf):
    url = f"{c.base_url}/rest/api/3/issue/{key}"
    payload = {
        "fields": {
            "description": description_adf
        }
    }
    # print(json.dumps(payload, indent=2)) # Debug
    resp = requests.put(url, auth=auth, headers=headers, json=payload)
    if resp.status_code == 204:
        print(f"Successfully updated description for {key}")
    else:
        print(f"Failed to update {key}: {resp.status_code} - {resp.text}")

# MD-3031: FixVerificationLoop
desc_3031 = {
    "type": "doc",
    "version": 1,
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Objective"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Implement a verification loop that automatically validates fixes for previously reported bugs. When a developer (or the agent) marks a JIRA bug as 'Resolved', this system should pick it up, re-run the original failing command, and verify if the fix actually works."}]
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Technical Implementation Details"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Create a new module: src/maestro_hive/core/self_reflection/fix_verification.py"}]
        },
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Required Logic"}]
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Query JIRA for tickets matching: project = MD AND labels = 'auto-created' AND status = Resolved"}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "For each ticket, extract the reproduction command and context."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Execute the command using IterativeExecutor."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "If Exit Code == 0 (Success): Transition ticket to 'Closed' and add success comment."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "If Exit Code != 0 (Failure): Transition ticket back to 'In Progress' and add failure comment."}]}]
                }
            ]
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Reference Files"}]
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "src/maestro_hive/core/execution/iterative_executor.py"}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "src/maestro_hive/core/self_reflection/gap_to_jira.py"}]}]
                }
            ]
        }
    ]
}

# MD-3032: ExecutionHistoryLogger
desc_3032 = {
    "type": "doc",
    "version": 1,
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Objective"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Implement a persistent storage mechanism for execution history. Currently, the system forgets past failures and fixes when the process restarts. We need a persistent log (JSONL or SQLite) to enable the RAG system to learn from historical data."}]
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Technical Implementation Details"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Create/Update module: src/maestro_hive/core/self_reflection/history_logger.py"}]
        },
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Requirements"}]
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Define a schema for execution records (id, timestamp, command, exit_code, stdout, stderr, failure_type, fix_applied)."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Implement ExecutionHistoryLogger class."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Store data in data/execution_history.jsonl (ensure directory exists)."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Integrate with IterativeExecutor to log every run."}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Update RAGClient to read from this persistent store instead of in-memory list."}]}]
                }
            ]
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Reference Files"}]
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "src/maestro_hive/core/execution/iterative_executor.py"}]}]
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "src/maestro_hive/core/self_reflection/refactoring_engine.py"}]}]
                }
            ]
        }
    ]
}

if __name__ == "__main__":
    print("Enriching MD-3031...")
    update_description("MD-3031", desc_3031)
    print("Enriching MD-3032...")
    update_description("MD-3032", desc_3032)
