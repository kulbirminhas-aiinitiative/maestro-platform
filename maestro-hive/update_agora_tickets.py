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

def update_ticket_description(key, description_text):
    url = f"{c.base_url}/rest/api/3/issue/{key}"
    
    # JIRA ADF (Atlassian Document Format) structure
    # We will use a simplified text block for robustness
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
                                "text": description_text
                            }
                        ]
                    }
                ]
            }
        }
    }
    
    print(f"Updating {key}...")
    try:
        resp = requests.put(url, auth=auth, headers=headers, json=payload)
        if resp.status_code == 204:
            print(f"✅ Successfully updated description for {key}")
        else:
            print(f"❌ Failed to update {key}: {resp.status_code} - {resp.text}")
            # Fallback to comment if description update fails (e.g. permissions)
            add_comment(key, f"UPDATED SPECIFICATION:\n\n{description_text}")
    except Exception as e:
        print(f"Error updating {key}: {e}")

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
    try:
        resp = requests.post(url, auth=auth, headers=headers, json=payload)
        if resp.status_code == 201:
            print(f"✅ Comment added to {key}")
        else:
            print(f"❌ Failed to add comment to {key}: {resp.status_code}")
    except Exception as e:
        print(f"Error commenting on {key}: {e}")

# --- TICKET CONTENT DEFINITIONS ---

md3097_desc = """
AGORA ARCHITECTURE SPECIFICATION: DURABLE EXECUTION (EPIC-1)

REFERENCE DOCUMENTATION:
- Vision: docs/vision/AI_ECOSYSTEM.md (Section 2.1 "Persistence as Physics")
- Roadmap: docs/roadmap/AGORA_ROADMAP.md (Phase 1)
- Epics: docs/roadmap/AGORA_EPICS.md

OBJECTIVE:
Transform the PersonaExecutor from a stateless script into a durable State Machine. Agents must survive process restarts, crashes, and long sleep cycles without losing context.

TECHNICAL REQUIREMENTS:
1. StateManager Interface:
   - Create `src/maestro_hive/unified_execution/state_persistence.py`
   - Define `save_state(agent_id, state_dict)` and `load_state(agent_id)`
   - Implement a FileSystemBackend (MVP) storing states in `maestro-hive/data/states/{agent_id}.json`

2. Integration Hooks:
   - Modify `PersonaExecutor.run()` in `src/maestro_hive/unified_execution/persona_executor.py`
   - ON START: Check if state exists. If yes, hydrate `self.memory` and `self.history`.
   - ON STEP: After every LLM interaction, call `save_state()`.

3. Schema:
   - State object must include: `memory` (list), `history` (list), `wallet_balance` (float), `config` (dict).

ACCEPTANCE CRITERIA:
- An agent can be started, perform 3 steps, be killed (Ctrl+C), and restarted.
- Upon restart, it resumes from Step 4, remembering the context of Steps 1-3.
"""

md3099_desc = """
AGORA ARCHITECTURE SPECIFICATION: TOKEN ECONOMY (EPIC-2)

REFERENCE DOCUMENTATION:
- Vision: docs/vision/AI_ECOSYSTEM.md (Section 2.3 "Resource Scarcity")
- Roadmap: docs/roadmap/AGORA_ROADMAP.md (Phase 1)

OBJECTIVE:
Implement the "Physics of Energy". Agents must pay for every inference token. This drives evolutionary pressure for efficiency and prevents infinite loops.

TECHNICAL REQUIREMENTS:
1. TokenBudget Class:
   - Create `src/maestro_hive/unified_execution/cost.py` (or similar)
   - Attributes: `total_budget`, `current_spend`, `hard_limit`.

2. Budget Decorator:
   - Create `@check_budget` decorator.
   - Apply to `call_llm` methods in `PersonaExecutor`.
   - Logic: 
     - Estimate cost of input + max_output.
     - If `current_spend + cost > total_budget`: Raise `BudgetExceededException`.
     - Else: Proceed, and update `current_spend` with actual cost after call.

3. Bankruptcy Handling:
   - If `BudgetExceededException` is caught, the agent must gracefully terminate with status `BANKRUPT`.

ACCEPTANCE CRITERIA:
- Configure an agent with a low budget ($0.01).
- Run a task that requires $0.05.
- Verify the agent halts execution before completion with a specific error message.
"""

md3096_desc = """
AGORA ARCHITECTURE SPECIFICATION: SECURITY & GOVERNANCE (ETHOS)

REFERENCE DOCUMENTATION:
- Vision: docs/vision/AI_ECOSYSTEM.md (Section 11.2 "Governance")
- Roadmap: docs/roadmap/AGORA_ROADMAP.md (Phase 1)

OBJECTIVE:
Implement the "Immune System". Prevent Prompt Injection and unauthorized tool usage.

TECHNICAL REQUIREMENTS:
1. Input Sanitization:
   - Scan all user inputs for known jailbreak patterns (e.g., "Ignore previous instructions").
   - Use a lightweight classifier or regex set before passing to the LLM.

2. Tool Whitelisting:
   - Enforce strict `allowed_tools` lists in `persona_config.json`.
   - If an agent tries to call a tool not in its manifest, block execution and log a security violation.

ACCEPTANCE CRITERIA:
- Attempt a "DAN" (Do Anything Now) prompt injection. System should reject it.
- Attempt to use a tool (e.g., `delete_file`) that is not in the agent's config. System should block it.
"""

md3098_desc = """
AGORA ARCHITECTURE SPECIFICATION: CRITICS GUILD (QUALITY)

REFERENCE DOCUMENTATION:
- Vision: docs/vision/AI_ECOSYSTEM.md (Section 5.1 "The Critics Guild")
- Roadmap: docs/roadmap/AGORA_ROADMAP.md (Phase 1)

OBJECTIVE:
Automate the "Review" phase. Code produced by agents must be verified by machine tools before being accepted.

TECHNICAL REQUIREMENTS:
1. Linter Integration:
   - Integrate `flake8` and `mypy` into the `PersonaExecutor` workflow.
   - If `output_type == 'code'`, automatically run linters on the generated block.

2. Feedback Loop:
   - If linting fails, feed the error message BACK to the agent as a new prompt: "Your code failed linting with errors: X, Y. Please fix."
   - Allow max 3 retry loops.

ACCEPTANCE CRITERIA:
- Agent generates code with a syntax error.
- System detects error, prompts agent to fix.
- Agent generates corrected code.
- System accepts corrected code.
"""

# --- EXECUTION ---

updates = {
    "MD-3097": md3097_desc,
    "MD-3099": md3099_desc,
    "MD-3096": md3096_desc,
    "MD-3098": md3098_desc
}

print("Starting Agora Ticket Updates...")
for ticket, desc in updates.items():
    update_ticket_description(ticket, desc)
    # Also add a comment to notify watchers
    add_comment(ticket, "Ticket updated with full Agora Architecture Specification. See Description for details.")

print("All updates complete.")
