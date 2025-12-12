#!/usr/bin/env python3
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
    
    summary = summary_match.group(1).strip() if summary_match else "No Summary"
    issue_type = type_match.group(1).strip() if type_match else "Task"
    priority = priority_match.group(1).strip() if priority_match else "Medium"
    
    # Clean up description (remove metadata header)
    description = content.split('---', 2)[-1].strip()
    
    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description[:30000]
                    }
                ]
            }
        ]
    }

    return {
        "summary": summary,
        "issuetype": {"name": issue_type},
        "priority": {"name": priority.split(' ')[0]},
        "description": adf_description,
        "project": {"key": PROJECT_KEY}
    }

def create_ticket(file_path):
    print(f"Creating ticket from {file_path}...")
    data = parse_ticket_file(file_path)
    
    payload = {
        "fields": {
            "project": data["project"],
            "summary": data["summary"],
            "issuetype": data["issuetype"],
            "description": data["description"]
        }
    }
    
    response = jira_request("/rest/api/3/issue", "POST", payload)
    
    if response and 'key' in response:
        print(f"✅ Created {response['key']}")
        return response['key']
    else:
        print(f"❌ Failed to create ticket: {response}")
        return None

if __name__ == "__main__":
    create_ticket("temp_ticket_md3162_strict.md")
