#!/usr/bin/env python3
"""
Create Persona University Ticket
Creates MD-3210 in JIRA.
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
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON response: {result.stdout}")
        return None

def parse_ticket_file(file_path):
    content = Path(file_path).read_text()
    
    # Extract metadata
    summary_match = re.search(r'\*\*Summary:\*\*\s*(.+)', content)
    type_match = re.search(r'\*\*Type:\*\*\s*(.+)', content)
    
    if not summary_match or not type_match:
        print(f"Skipping {file_path}: Missing Summary or Type")
        return None
        
    summary = summary_match.group(1).strip()
    issue_type = type_match.group(1).strip()
    
    description = content
    
    return {
        "project": {"key": PROJECT_KEY},
        "summary": summary,
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": description[:3000]
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": issue_type}
    }

def create_ticket(file_path, epic_link=None):
    print(f"Processing {file_path}...")
    data = parse_ticket_file(file_path)
    if not data:
        return None
        
    payload = {
        "fields": {
            "project": data["project"],
            "summary": data["summary"],
            "issuetype": data["issuetype"],
            "description": data["description"]
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
    stories = [
        "docs/tickets/MD-3210_PERSONA_UNIVERSITY.md"
    ]
    
    for story_path in stories:
        create_ticket(story_path)

if __name__ == "__main__":
    main()
