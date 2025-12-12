#!/usr/bin/env python3
"""
JIRA Ticket Updater
Updates existing JIRA tickets with improved content from markdown files.
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

# Mapping of Local File -> JIRA ID (Based on previous creation)
TICKET_MAP = {
    "docs/tickets/MD-3201_ENFORCER.md": "MD-3116",
    "docs/tickets/MD-3202_AUDITOR.md": "MD-3117",
    "docs/tickets/MD-3203_REPUTATION.md": "MD-3118",
    "docs/tickets/MD-3204_CHAOS.md": "MD-3119",
    "docs/tickets/MD-3205_OVERRIDE.md": "MD-3120"
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
            return {} # Success with no content
            
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error calling JIRA: {e}")
        return None

def parse_ticket_file(file_path):
    content = Path(file_path).read_text()
    
    # Extract description (everything after the metadata header)
    description_text = content.split('---', 2)[-1].strip()
    
    # Convert to ADF (Atlassian Document Format)
    # We will parse headers to make it look nice
    
    adf_content = []
    
    lines = description_text.split('\n')
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('## '):
            # Flush paragraph
            if current_paragraph:
                adf_content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": " ".join(current_paragraph)}]
                })
                current_paragraph = []
            
            # Add Heading
            adf_content.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": line[3:]}]
            })
        elif line.startswith('### '):
             # Flush paragraph
            if current_paragraph:
                adf_content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": " ".join(current_paragraph)}]
                })
                current_paragraph = []
            
            # Add Heading
            adf_content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": line[4:]}]
            })
        elif line.startswith('* ') or line.startswith('- '):
             # Flush paragraph
            if current_paragraph:
                adf_content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": " ".join(current_paragraph)}]
                })
                current_paragraph = []
            
            # Add Bullet Item (Simplified: JIRA requires bulletList wrapper, doing simple text for now to avoid complexity)
            adf_content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": "• " + line[2:]}]
            })
        else:
            current_paragraph.append(line)
            
    if current_paragraph:
        adf_content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": " ".join(current_paragraph)}]
        })

    return {
        "type": "doc",
        "version": 1,
        "content": adf_content
    }

def update_ticket(file_path, jira_key):
    print(f"Updating {jira_key} from {file_path}...")
    description_adf = parse_ticket_file(file_path)
    
    payload = {
        "fields": {
            "description": description_adf
        }
    }
    
    response = jira_request(f"/rest/api/3/issue/{jira_key}", "PUT", payload)
    
    if response is None: # PUT returns 204 No Content on success usually, or empty JSON
        print(f"✅ Updated {jira_key}")
    else:
        # If it returns something, it might be an error or success details
        print(f"ℹ️ Response for {jira_key}: {response}")

def main():
    for file_path, jira_key in TICKET_MAP.items():
        update_ticket(file_path, jira_key)

if __name__ == "__main__":
    main()
