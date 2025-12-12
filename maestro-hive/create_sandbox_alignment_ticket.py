#!/usr/bin/env python3
"""
Create JIRA ticket for Sandbox Directory Alignment
"""
import os
import json
import subprocess

# Configuration
JIRA_BASE_URL = "https://fifth9.atlassian.net"
JIRA_EMAIL = "kulbir.minhas@fifth-9.com"
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT_KEY = "MD"

TICKET_DATA = {
    "summary": "Align Sandbox Directory Structure with Dev/Demo Environments",
    "description": """h2. Description

The sandbox environment uses a different directory structure than dev and demo servers, causing confusion and maintenance overhead.

h3. Current State (Sandbox)

||Service||Sandbox Path||Expected Path||
|Frontend|~/projects/maestro-frontend-production|~/projects/maestro-platform/maestro-frontend|
|Engine|~/projects/maestro-engine-new|~/projects/maestro-platform/maestro-engine|

h3. Target State

All environments should follow:
{code}
~/projects/maestro-platform/
├── maestro-frontend/
├── maestro-engine/
├── maestro-hive/
├── gateway/
└── ... (other services)
{code}

h2. Problem Statement

* *Inconsistent paths* - Scripts and CI/CD reference different paths per environment
* *Maintenance overhead* - Environment-specific configs for identical services
* *Developer confusion* - Onboarding complicated by non-standard paths
* *Deployment risk* - Copy-paste errors across environments

h2. Acceptance Criteria

# Create migration plan for sandbox directory restructure
# Migrate maestro-frontend-production to maestro-platform/maestro-frontend
# Migrate maestro-engine-new to maestro-platform/maestro-engine
# Update systemd services / process managers
# Update nginx/reverse proxy configurations
# Update SERVICE_PORT_REGISTRY.md with sandbox ports (13000 range)
# Verify all services start correctly
# E2E tests (MD-3111) passing

h2. Port Alignment Reference

||Environment||Frontend||Gateway||Engine||
|Dev|4200|8080|5000|
|Demo|4200|8080|5000|
|Sandbox|13000|14000|15000|
|Production|443|443|Internal|

h2. Implementation Plan

*Phase 1: Discovery*
* Audit running services and paths
* Document configs referencing old paths
* Create rollback plan

*Phase 2: Migration*
* Stop services gracefully
* Create temporary symlinks for backward compatibility
* Update service configurations
* Test each service

*Phase 3: Validation*
* Run health checks
* Execute E2E test suite
* Verify frontend and API endpoints

---
*Estimated Effort:* 4-6 hours
*Requires Maintenance Window:* Yes (15-30 min)
""",
    "issuetype": "Task",
    "priority": "Medium",
    "labels": ["sandbox", "infrastructure", "alignment", "tech-debt"],
    "components": ["Infrastructure"]
}


def create_jira_ticket():
    """Create the ticket in JIRA"""

    if not JIRA_API_TOKEN:
        print("ERROR: JIRA_API_TOKEN environment variable not set")
        print("\nTo create this ticket manually, use the markdown file at:")
        print("  docs/tickets/MD-SANDBOX-DIRECTORY-ALIGNMENT.md")
        print("\nOr set JIRA_API_TOKEN and run again.")
        return None

    # Build the ADF description
    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": TICKET_DATA["description"]
                    }
                ]
            }
        ]
    }

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": TICKET_DATA["summary"],
            "description": adf_description,
            "issuetype": {"name": TICKET_DATA["issuetype"]},
            "priority": {"name": TICKET_DATA["priority"]},
            "labels": TICKET_DATA["labels"]
        }
    }

    # Write payload to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        temp_file = f.name

    cmd = [
        'curl', '-s', '-X', 'POST',
        '-H', 'Content-Type: application/json',
        '-u', f'{JIRA_EMAIL}:{JIRA_API_TOKEN}',
        '-d', f'@{temp_file}',
        f'{JIRA_BASE_URL}/rest/api/3/issue'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(temp_file)

        response = json.loads(result.stdout)

        if 'key' in response:
            ticket_key = response['key']
            print(f"SUCCESS: Created ticket {ticket_key}")
            print(f"URL: {JIRA_BASE_URL}/browse/{ticket_key}")
            return ticket_key
        else:
            print(f"ERROR: Failed to create ticket")
            print(f"Response: {result.stdout}")
            return None

    except Exception as e:
        print(f"ERROR: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Sandbox Directory Alignment Ticket Creator")
    print("=" * 60)
    print(f"\nSummary: {TICKET_DATA['summary']}")
    print(f"Type: {TICKET_DATA['issuetype']}")
    print(f"Priority: {TICKET_DATA['priority']}")
    print(f"Labels: {', '.join(TICKET_DATA['labels'])}")
    print()

    create_jira_ticket()
