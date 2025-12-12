import os
import sys
import json
import requests
import getpass

# Configuration
JIRA_BASE_URL = "https://fifth9.atlassian.net"
PROJECT_KEY = "MD"
AUTH_EMAIL = os.environ.get("JIRA_EMAIL")
AUTH_TOKEN = os.environ.get("JIRA_TOKEN")

if not AUTH_EMAIL or not AUTH_TOKEN:
    print("Please set JIRA_EMAIL and JIRA_TOKEN environment variables.")
    sys.exit(1)

AUTH = (AUTH_EMAIL, AUTH_TOKEN)
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def text_to_adf(text):
    """Convert simple text to Atlassian Document Format."""
    content = []
    for paragraph in text.split('\n\n'):
        if not paragraph.strip():
            continue
        content.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": paragraph.strip()
                }
            ]
        })
    
    return {
        "type": "doc",
        "version": 1,
        "content": content
    }

def create_issue(summary, description, issuetype, parent_key=None, labels=None):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    
    payload = {
        "fields": {
            "project": {
                "key": PROJECT_KEY
            },
            "summary": summary,
            "description": text_to_adf(description),
            "issuetype": {
                "name": issuetype
            }
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
        return data['key']
    else:
        print(f"Failed to create {issuetype}: {summary}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def main():
    print(f"Creating Phased Execution tickets in project {PROJECT_KEY}...")

    # 1. Create EPIC
    epic_summary = "Phased Execution & Rerunnability Implementation"
    epic_description = """Implement the Phased Execution architecture (SplitMode) as the default execution engine for Maestro Hive. 

This initiative aims to:
1. Enable phase-by-phase execution (Requirements -> Design -> Implementation).
2. Provide robust resume-from-failure capabilities using checkpoints.
3. Unify the execution engine architecture around `TeamExecutionEngineV2SplitMode`.
4. Expose these capabilities via API for better control.

Reference: DESIGN_REVIEW_PHASED_EXECUTION.md"""
    
    epic_key = create_issue(epic_summary, epic_description, "Epic", labels=["architecture", "execution-engine", "split-mode"])
    
    if not epic_key:
        print("Aborting due to EPIC creation failure.")
        return

    # 2. Create Stories
    stories = [
        {
            "summary": "Standardize SDLC Phases across SplitMode and Resume Scripts",
            "description": """Create a single source of truth for SDLC phases (e.g., `src/maestro_hive/config/phases.py`). 

Tasks:
1. Define `SDLC_PHASES` constant.
2. Update `TeamExecutionEngineV2SplitMode` to use this constant.
3. Update `resume_failed_workflow.py` to use this constant.
4. Resolve the mismatch between 'backend_development' and 'implementation' (alias or rename)."""
        },
        {
            "summary": "Refactor resume_failed_workflow.py to use SplitMode Engine",
            "description": """Update `resume_failed_workflow.py` to instantiate `TeamExecutionEngineV2SplitMode` and call `resume_from_checkpoint()` instead of the current placeholder logic.

Tasks:
1. Import `TeamExecutionEngineV2SplitMode`.
2. Replace the manual context loading logic with `engine.resume_from_checkpoint(path)`.
3. Ensure the script accepts a checkpoint path argument."""
        },
        {
            "summary": "Add execute_jira_task wrapper to SplitMode Engine",
            "description": """Implement `execute_jira_task()` in `TeamExecutionEngineV2SplitMode` to support JIRA-driven workflows.

Tasks:
1. Add `execute_jira_task(task_key, ...)` method.
2. Use `JiraTaskAdapter` to fetch requirements.
3. Update JIRA status to 'inProgress'.
4. Call `execute_batch()` for the actual work.
5. Update JIRA status to 'done' on success."""
        },
        {
            "summary": "Expose Resume Capability via API",
            "description": """Add `POST /api/workflow/{id}/resume` endpoint to `workflow_api_v2.py`.

Tasks:
1. Define the API route.
2. Implement logic to find the latest checkpoint for the given workflow ID.
3. Instantiate `TeamExecutionEngineV2SplitMode`.
4. Call `resume_from_checkpoint`."""
        },
        {
            "summary": "Create Synthetic Checkpoint Generator for Partial Execution",
            "description": """Develop a utility class `SyntheticCheckpointBuilder` that can generate a valid `checkpoint_{phase}.json` from external inputs.

Use Case: Starting execution from 'Implementation' phase using an uploaded Design Doc, skipping the actual 'Design' phase execution."""
        },
        {
            "summary": "Implement Checkpoint Rotation and Cleanup",
            "description": """Add logic to manage checkpoint files to prevent disk exhaustion.

Tasks:
1. Implement a policy to keep only the last N checkpoints per workflow.
2. Or implement a TTL mechanism.
3. Ensure cleanup happens automatically or via a scheduled job."""
        },
        {
            "summary": "Create Integration Tests for Phased Execution",
            "description": """Develop an integration test suite that validates the full lifecycle.

Scenarios:
1. Run a phase and verify checkpoint creation.
2. Simulate a failure/stop.
3. Resume from checkpoint and verify completion.
4. Verify JIRA status updates (mocked)."""
        }
    ]

    for story in stories:
        create_issue(story["summary"], story["description"], "Story", parent_key=epic_key, labels=["split-mode"])

if __name__ == "__main__":
    main()
