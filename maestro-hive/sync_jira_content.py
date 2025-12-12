#!/usr/bin/env python3
"""
Sync JIRA Content
Updates JIRA tickets with the FULL content of local markdown files.
Ensures JIRA is the central repository and source of truth.
"""
import os
import json
import subprocess
from pathlib import Path

# Configuration
JIRA_BASE_URL = "https://fifth9.atlassian.net"
JIRA_EMAIL = "kulbir.minhas@fifth-9.com"
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

# Mapping Local File -> JIRA Key
# Based on recent creation logs
TICKET_MAP = {
    "docs/tickets/MD-3200_GOVERNANCE_EPIC.md": "MD-3115",
    "docs/tickets/MD-3201_ENFORCER.md": "MD-3116",
    "docs/tickets/MD-3202_AUDITOR.md": "MD-3117",
    "docs/tickets/MD-3203_REPUTATION.md": "MD-3118",
    "docs/tickets/MD-3204_CHAOS.md": "MD-3119",
    "docs/tickets/MD-3205_OVERRIDE.md": "MD-3120",
    "docs/tickets/MD-3206_UPGRADE_ENGINE.md": "MD-3123",
    "docs/tickets/MD-3207_TRAINING_VALIDATION.md": "MD-3124",
    "docs/tickets/MD-3208_INTEGRATE_EVENT_BUS.md": "MD-3125",
    "docs/tickets/MD-3209_INTEGRATE_ENFORCER.md": "MD-3126",
    "docs/tickets/MD-3210_PERSONA_UNIVERSITY.md": "MD-3127"
}

def jira_request(endpoint, method='GET', body=None):
    url = f"{JIRA_BASE_URL}{endpoint}"
    cmd = [
        'curl', '-s', '-X', method,
        '-H', 'Content-Type: application/json',
        '-u', f'{JIRA_EMAIL}:{JIRA_API_TOKEN}'
    ]
    
    if body:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(body, f)
            temp_file = f.name
        cmd.extend(['-d', f'@{temp_file}'])
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if body:
            os.unlink(temp_file)
        if not result.stdout:
            return {}
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error calling JIRA: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON response: {result.stdout}")
        return None

def update_ticket_description(jira_key, file_path):
    print(f"Syncing {file_path} -> {jira_key}...")
    content = Path(file_path).read_text()
    
    # JIRA Atlassian Document Format (ADF)
    # We will use a single code block for the markdown content to preserve formatting perfectly,
    # OR we can try to pass it as a text block. 
    # Passing as a simple text paragraph is safest for now, but we won't truncate.
    # JIRA Cloud limit is ~32k chars.
    
    payload = {
        "fields": {
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": content 
                            }
                        ]
                    }
                ]
            }
        }
    }

    response = jira_request(f"/rest/api/3/issue/{jira_key}", "PUT", payload)
    
    if response is not None:
        print(f"✅ Updated {jira_key}")
    else:
        print(f"❌ Failed to update {jira_key}")

def main():
    print("Starting JIRA Sync...")
    for file_path, jira_key in TICKET_MAP.items():
        if os.path.exists(file_path):
            update_ticket_description(jira_key, file_path)
        else:
            print(f"⚠️ File not found: {file_path}")

if __name__ == "__main__":
    main()
