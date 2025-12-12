#!/usr/bin/env python3
"""
JIRA Ticket Creator
Reads the markdown ticket definitions and creates them in JIRA.
"""
import os
import re
import json
import subprocess
from pathlib import Path

# Configuration
JIRA_BASE_URL = "https://fifth9.atlassian.net"
JIRA_EMAIL = "kulbir.minhas@fifth-9.com"
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT_KEY = "MD"

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
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error calling JIRA: {e}")
        print(f"Output: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON response: {result.stdout}")
        return None

def parse_ticket_file(file_path):
    content = Path(file_path).read_text()
    
    # Extract metadata
    summary_match = re.search(r'\*\*Summary:\*\*\s*(.+)', content)
    type_match = re.search(r'\*\*Type:\*\*\s*(.+)', content)
    priority_match = re.search(r'\*\*Priority:\*\*\s*(.+)', content)
    epic_match = re.search(r'\*\*Epic:\*\*\s*(.+)', content)
    
    summary = summary_match.group(1).strip() if summary_match else "No Summary"
    issue_type = type_match.group(1).strip() if type_match else "Story"
    priority = priority_match.group(1).strip() if priority_match else "Medium"
    
    # Clean up description (remove metadata header)
    description = content.split('---', 2)[-1].strip()
    
    # Convert markdown to Atlassian Document Format (simplified)
    # For now, we'll just use the raw markdown as text, JIRA might render it or we might need a converter.
    # Better approach: Use the ADF builder or just send as string and hope JIRA handles it or use a simple converter.
    # JIRA Cloud API v3 uses ADF for description.
    
    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description[:30000] # Truncate if too long
                    }
                ]
            }
        ]
    }

    return {
        "summary": summary,
        "issuetype": {"name": issue_type},
        "priority": {"name": priority.split(' ')[0]}, # "High (Blocker)" -> "High"
        "description": adf_description,
        "project": {"key": PROJECT_KEY}
    }

def create_ticket(file_path, epic_link=None):
    print(f"Creating ticket from {file_path}...")
    data = parse_ticket_file(file_path)
    
    # Create the issue
    payload = {
        "fields": {
            "project": data["project"],
            "summary": data["summary"],
            "issuetype": data["issuetype"],
            "description": data["description"],
            # "priority": data["priority"] # Priority often requires ID, skipping for simplicity unless critical
        }
    }
    
    if epic_link:
        payload["fields"]["parent"] = {"key": epic_link}

    response = jira_request("/rest/api/3/issue", "POST", payload)
    
    if response and 'key' in response:
        print(f"✅ Created {response['key']}")
        return response['key']
    else:
        print(f"❌ Failed to create ticket: {response}")
        return None

def main():
    # 1. Create Epic
    epic_key = create_ticket("docs/tickets/MD-3200_GOVERNANCE_EPIC.md")
    if not epic_key:
        print("Aborting: Could not create Epic.")
        return

    # 2. Create Stories linked to Epic
    stories = [
        "docs/tickets/MD-3201_ENFORCER.md",
        "docs/tickets/MD-3202_AUDITOR.md",
        "docs/tickets/MD-3203_REPUTATION.md",
        "docs/tickets/MD-3204_CHAOS.md",
        "docs/tickets/MD-3205_OVERRIDE.md"
    ]
    
    for story_path in stories:
        create_ticket(story_path, epic_link=epic_key)

if __name__ == "__main__":
    main()
