#!/usr/bin/env python3
import requests
import os
import json
import time

# --- CONFIGURATION ---
PROJECT_KEY = "MD"  # Assumed based on existing tickets

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

def create_issue(summary, description, issuetype="Story", parent_key=None, priority="Medium"):
    url = f"{c.base_url}/rest/api/3/issue"
    
    # Construct ADF description
    # For simplicity in this script, we'll use a basic paragraph structure.
    # In a real robust script, we might parse markdown to ADF.
    # Here we just dump the text.
    
    description_adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description
                    }
                ]
            }
        ]
    }

    payload = {
        "fields": {
            "project": {
                "key": PROJECT_KEY
            },
            "summary": summary,
            "description": description_adf,
            "issuetype": {
                "name": issuetype
            },
            "priority": {
                "name": priority
            }
        }
    }
    
    # Link to Epic if provided (and if issuetype is not Epic)
    if parent_key and issuetype != "Epic":
        # Note: The field for Epic Link varies by JIRA instance. 
        # Modern JIRA uses 'parent' field for Next-Gen or hierarchy.
        # Classic JIRA uses 'customfield_XXXXX'.
        # We will try the standard 'parent' field first.
        payload["fields"]["parent"] = {"key": parent_key}

    try:
        resp = requests.post(url, auth=auth, headers=headers, json=payload)
        if resp.status_code == 201:
            data = resp.json()
            key = data['key']
            print(f"✅ Created {issuetype}: {key} - {summary}")
            return key
        else:
            print(f"❌ Failed to create {summary}: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Error creating issue: {e}")
        return None

# --- DATA DEFINITIONS ---

# 1. EPIC: The Town Square
epic_town_square = {
    "summary": "Agora Phase 2: The Town Square (Event Bus)",
    "description": """
EPIC GOAL: Decouple agents using a Pub/Sub architecture to enable dynamic swarming and discovery.

REFERENCE: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md
VISION: docs/vision/AI_ECOSYSTEM.md

This Epic covers the implementation of the Event Bus, the Agent Communication Language (ACL), and the initial InMemory implementation.
"""
}

stories_town_square = [
    {
        "summary": "Design Event Bus Interface (Pub/Sub)",
        "priority": "High",
        "description": """
**Context**: The Agora architecture relies on decoupling agents. Currently, the Orchestrator calls agents directly.
**Problem**: Direct function calls create tight coupling.
**Requirements**:
1. Create `src/maestro_hive/core/event_bus.py`.
2. Define abstract base class `EventBus`.
3. Define methods: `publish`, `subscribe`, `unsubscribe`.
**Acceptance Criteria**:
- Interface defined using `abc`.
- Strict type hints.
"""
    },
    {
        "summary": "Implement InMemoryEventBus",
        "priority": "High",
        "description": """
**Context**: Need reference implementation for local testing.
**Requirements**:
1. Create `src/maestro_hive/core/event_bus_memory.py`.
2. Implement `InMemoryEventBus` using `asyncio.Queue`.
3. Thread-safe/Async-safe.
**Acceptance Criteria**:
- Unit tests for publish/subscribe routing.
- Latency < 1ms.
"""
    },
    {
        "summary": "Define Agent Communication Language (ACL) Schema",
        "priority": "High",
        "description": """
**Context**: Agents need a standardized way to speak.
**Requirements**:
1. Create `src/maestro_hive/core/acl.py`.
2. Define `AgoraMessage` dataclass with fields: `message_id`, `sender`, `performative`, `content`.
**Acceptance Criteria**:
- Valid messages serialize/deserialize correctly.
"""
    }
]

# 2. EPIC: Identity & Trust
epic_identity = {
    "summary": "Agora Phase 2: Identity & Trust",
    "description": """
EPIC GOAL: Establish Self-Sovereign Identity (SSI) for agents to enable trust and non-repudiation.

REFERENCE: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md
"""
}

stories_identity = [
    {
        "summary": "Implement Agent Identity & Key Generation",
        "priority": "Medium",
        "description": """
**Context**: Identity is everything in a marketplace.
**Requirements**:
1. Create `src/maestro_hive/core/identity.py`.
2. Implement `IdentityManager`.
3. Generate Ed25519 keypairs.
**Acceptance Criteria**:
- Keys generated securely.
- Private keys never exposed.
"""
    },
    {
        "summary": "Implement Message Signing",
        "priority": "Medium",
        "description": """
**Context**: Trust requires verification.
**Requirements**:
1. Update `AgoraMessage` to include signature.
2. Sign messages on publish.
3. Verify messages on receipt.
**Acceptance Criteria**:
- Signed messages processed.
- Tampered messages rejected.
"""
    }
]

# 3. EPIC: Guilds & Registry
epic_guilds = {
    "summary": "Agora Phase 2: Guilds & Registry",
    "description": """
EPIC GOAL: Enable dynamic discovery of agent capabilities.

REFERENCE: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md
"""
}

stories_guilds = [
    {
        "summary": "Create Agent Registry Service",
        "priority": "Medium",
        "description": """
**Context**: Agents need to find each other based on skills.
**Requirements**:
1. Create `src/maestro_hive/core/registry.py`.
2. Implement `AgentRegistry`.
3. Methods: `register`, `find_agents`.
**Acceptance Criteria**:
- Can register and query agents by Guild.
"""
    }
]

# --- EXECUTION LOOP ---

def run():
    print("--- CREATING AGORA PHASE 2 TICKETS ON JIRA ---")
    
    # 1. Town Square
    epic_key = create_issue(epic_town_square["summary"], epic_town_square["description"], issuetype="Epic", priority="High")
    if epic_key:
        for story in stories_town_square:
            create_issue(story["summary"], story["description"], parent_key=epic_key, priority=story["priority"])
            time.sleep(1) # Rate limit niceness

    # 2. Identity
    epic_key = create_issue(epic_identity["summary"], epic_identity["description"], issuetype="Epic", priority="High")
    if epic_key:
        for story in stories_identity:
            create_issue(story["summary"], story["description"], parent_key=epic_key, priority=story["priority"])
            time.sleep(1)

    # 3. Guilds
    epic_key = create_issue(epic_guilds["summary"], epic_guilds["description"], issuetype="Epic", priority="Medium")
    if epic_key:
        for story in stories_guilds:
            create_issue(story["summary"], story["description"], parent_key=epic_key, priority=story["priority"])
            time.sleep(1)

    print("--- DONE ---")

if __name__ == "__main__":
    run()
