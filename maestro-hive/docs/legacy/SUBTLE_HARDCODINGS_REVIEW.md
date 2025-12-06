# Subtle Hardcodings Review & Fixes

## Overview

Even though V2 eliminated obvious hardcodings (templates), several subtle hardcodings remain that violate the DRY principle and reduce maintainability.

---

## Issues Found

### ✅ Issue 1: Deliverables Mapping (FIXED)

**Location:** `autonomous_sdlc_engine_v2.py:489`

**Problem:**
```python
def _get_deliverables_for_agent(self, agent_id: str) -> List[str]:
    deliverables_map = {
        "requirement_analyst": ["requirements_document", "user_stories"],
        # ... hardcoded for every persona
    }
    return deliverables_map.get(agent_id, [])
```

**Why It's Bad:**
- Duplicates information from `team_organization.py`
- Must be manually updated in multiple places
- Violates single source of truth

**Fix:**
```python
# team_organization.py - Added central function
def get_deliverables_for_persona(persona_id: str) -> List[str]:
    deliverables_map = {
        "requirement_analyst": [...],
        # ...
    }
    return deliverables_map.get(persona_id, [])

# autonomous_sdlc_engine_v2.py - Use central function
from team_organization import get_deliverables_for_persona

def _get_deliverables_for_agent(self, agent_id: str) -> List[str]:
    return get_deliverables_for_persona(agent_id)
```

---

### ❌ Issue 2: State→Agents Mapping (NOT FIXED YET)

**Location:** `autonomous_sdlc_engine_v2.py:322-330`

**Problem:**
```python
class DynamicWorkflowEngine:
    def __init__(self):
        self.state_agents = {
            "requirements": ["requirement_analyst", "ui_ux_designer"],
            "design": ["solution_architect"],
            "security_review": ["security_specialist"],
            "implementation": ["backend_developer", "frontend_developer", "devops_engineer"],
            # ... hardcoded
        }
```

**Why It's Bad:**
- Duplicates information from `team_organization.py` which has `primary_personas` for each phase
- If we add/remove a persona from a phase in team_organization.py, must manually update here too

**Should Be:**
```python
# team_organization.py already has this!
SDLCPhase.REQUIREMENTS: {
    "primary_personas": [
        "requirement_analyst",
        "ui_ux_designer"
    ],
    # ...
}

# DynamicWorkflowEngine should use it
from team_organization import TeamOrganization

class DynamicWorkflowEngine:
    def __init__(self):
        org = TeamOrganization()
        phase_structure = org.get_phase_structure()

        # Build state_agents from phase_structure
        self.state_agents = {}
        for phase, config in phase_structure.items():
            state_name = phase.value  # Convert SDLCPhase enum to string
            self.state_agents[state_name] = config["primary_personas"]
```

---

### ❌ Issue 3: Workflow States & Transitions (NOT FIXED YET)

**Location:** `autonomous_sdlc_engine_v2.py:311-319`

**Problem:**
```python
class DynamicWorkflowEngine:
    def __init__(self):
        self.states = {
            "requirements": {"next": ["design"], "can_loop_to": []},
            "design": {"next": ["security_review"], "can_loop_to": ["requirements"]},
            # ... hardcoded workflow
        }
```

**Why It's Bad:**
- Workflow structure should be data, not code
- Can't be modified without changing code
- Should be configurable or loaded from config

**Should Be:**
```python
# workflow_config.yaml or workflow_config.py
WORKFLOW_CONFIG = {
    "states": {
        "requirements": {
            "next": ["design"],
            "can_loop_to": [],
            "can_parallel": []
        },
        "design": {
            "next": ["security_review"],
            "can_loop_to": ["requirements"],
            "can_parallel": []
        },
        # ...
    }
}

# DynamicWorkflowEngine loads from config
class DynamicWorkflowEngine:
    def __init__(self, workflow_config: Dict = None):
        if workflow_config is None:
            from workflow_config import WORKFLOW_CONFIG
            workflow_config = WORKFLOW_CONFIG

        self.states = workflow_config["states"]
```

---

### ❌ Issue 4: Persona List (NOT FIXED YET)

**Location:** `autonomous_sdlc_engine_v2.py:390-395`

**Problem:**
```python
def _initialize_agents(self):
    persona_methods = [
        'requirement_analyst', 'ui_ux_designer', 'solution_architect',
        'security_specialist', 'backend_developer', 'frontend_developer',
        'devops_engineer', 'qa_engineer', 'technical_writer',
        'deployment_specialist'
    ]
```

**Why It's Bad:**
- Must manually list all personas
- If we add a new persona to `personas.py`, must remember to add here too
- No single source of truth

**Should Be:**
```python
# personas.py - Add helper function
class SDLCPersonas:
    @staticmethod
    def get_all_persona_ids() -> List[str]:
        """Get list of all available persona IDs"""
        return [
            'requirement_analyst',
            'ui_ux_designer',
            'solution_architect',
            # ...
        ]

    # Or better - dynamically discover all persona methods
    @classmethod
    def get_all_personas(cls) -> List[Dict]:
        """Dynamically discover all personas"""
        personas = []
        for method_name in dir(cls):
            if not method_name.startswith('_') and method_name != 'get_all_personas':
                method = getattr(cls, method_name)
                if callable(method) and not isinstance(method, type):
                    try:
                        persona_config = method()
                        if isinstance(persona_config, dict) and 'id' in persona_config:
                            personas.append(persona_config)
                    except:
                        pass
        return personas

# autonomous_sdlc_engine_v2.py
def _initialize_agents(self):
    agents = {}

    all_personas = personas.SDLCPersonas.get_all_personas()
    for persona_config in all_personas:
        agent = ToolBasedSDLCAgent(
            persona_id=persona_config['id'],
            persona_config=persona_config,
            output_dir=self.output_dir
        )
        agents[persona_config['id']] = agent

    return agents
```

---

### ❌ Issue 5: Model Name (MINOR)

**Location:** `autonomous_sdlc_engine_v2.py:181`

**Problem:**
```python
options = ClaudeCodeOptions(
    system_prompt=self.persona_config['system_prompt'],
    model="claude-sonnet-4-20250514",  # Hardcoded
    cwd=self.output_dir,
    permission_mode="acceptEdits"
)
```

**Why It's Bad:**
- Model name is hardcoded
- If we want to use a different model, must change code

**Should Be:**
```python
# config.py
CLAUDE_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "permission_mode": "acceptEdits",
    "timeout": 600000
}

# autonomous_sdlc_engine_v2.py
from config import CLAUDE_CONFIG

options = ClaudeCodeOptions(
    system_prompt=self.persona_config['system_prompt'],
    model=CLAUDE_CONFIG["model"],
    cwd=self.output_dir,
    permission_mode=CLAUDE_CONFIG["permission_mode"]
)
```

---

## Priority Fixes

### High Priority
1. ✅ **Deliverables mapping** - FIXED
2. ❌ **State→Agents mapping** - Pull from team_organization.py
3. ❌ **Persona list** - Dynamic discovery

### Medium Priority
4. ❌ **Workflow states** - Move to config file
5. ❌ **Model configuration** - Move to config file

### Low Priority
- Output directory naming patterns
- File naming conventions
- Default values

---

## Implementation Plan

### Step 1: Add Helper Functions to team_organization.py

```python
# team_organization.py

def get_agents_for_phase(phase: SDLCPhase) -> List[str]:
    """
    Get list of agent IDs for a specific phase

    Uses the primary_personas from phase structure
    """
    org = TeamOrganization()
    structure = org.get_phase_structure()

    if phase not in structure:
        return []

    return structure[phase].get("primary_personas", [])


def get_workflow_transitions() -> Dict[str, Dict[str, List[str]]]:
    """
    Generate workflow transitions from phase dependencies

    Returns:
        {
            "requirements": {"next": ["design"], "can_loop_to": []},
            "design": {"next": ["implementation"], "can_loop_to": ["requirements"]},
            ...
        }
    """
    # Define explicit transition rules based on SDLC logic
    transitions = {
        "requirements": {
            "next": ["design"],
            "can_loop_to": []
        },
        "design": {
            "next": ["security_review"],
            "can_loop_to": ["requirements"]
        },
        "security_review": {
            "next": ["implementation"],
            "can_loop_to": ["design"]
        },
        "implementation": {
            "next": ["testing"],
            "can_loop_to": ["design"]
        },
        "testing": {
            "next": ["documentation"],
            "can_loop_to": ["implementation"]
        },
        "documentation": {
            "next": ["deployment"],
            "can_loop_to": []
        },
        "deployment": {
            "next": ["complete"],
            "can_loop_to": []
        }
    }

    return transitions
```

### Step 2: Add Helper Function to personas.py

```python
# personas.py

class SDLCPersonas:
    # ... existing persona methods ...

    @classmethod
    def get_all_personas(cls) -> List[Dict[str, Any]]:
        """
        Dynamically discover all persona configurations

        Returns list of all persona configs without hardcoding the list
        """
        personas = []

        # Get all methods of the class
        for attr_name in dir(cls):
            # Skip private methods and special methods
            if attr_name.startswith('_') or attr_name in ['get_all_personas']:
                continue

            attr = getattr(cls, attr_name)

            # Check if it's a callable static method
            if callable(attr):
                try:
                    # Try to call it
                    result = attr()

                    # Check if it returns a persona config
                    if isinstance(result, dict) and 'id' in result and 'name' in result:
                        personas.append(result)
                except:
                    # Not a persona method
                    pass

        return personas

    @classmethod
    def get_persona_by_id(cls, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get specific persona by ID"""
        all_personas = cls.get_all_personas()
        for persona in all_personas:
            if persona['id'] == persona_id:
                return persona
        return None
```

### Step 3: Update DynamicWorkflowEngine

```python
# autonomous_sdlc_engine_v2.py

from team_organization import get_agents_for_phase, get_workflow_transitions, SDLCPhase

class DynamicWorkflowEngine:
    """
    Dynamic workflow engine - NO HARDCODING

    All configuration pulled from team_organization.py
    """

    def __init__(self):
        # Load workflow transitions from central config
        self.states = get_workflow_transitions()

        # Build state→agents mapping from phase structure
        self.state_agents = {}
        for phase in SDLCPhase:
            state_name = phase.value
            self.state_agents[state_name] = get_agents_for_phase(phase)

    # ... rest of methods unchanged ...
```

### Step 4: Update _initialize_agents

```python
# autonomous_sdlc_engine_v2.py

def _initialize_agents(self) -> Dict[str, ToolBasedSDLCAgent]:
    """
    Initialize all SDLC agents - NO HARDCODING

    Dynamically discovers all personas from personas.py
    """
    agents = {}

    # Get all personas dynamically
    all_personas = personas.SDLCPersonas.get_all_personas()

    for persona_config in all_personas:
        agent = ToolBasedSDLCAgent(
            persona_id=persona_config['id'],
            persona_config=persona_config,
            output_dir=self.output_dir
        )
        agents[persona_config['id']] = agent

    return agents
```

### Step 5: Create config.py

```python
# config.py

"""
Central configuration for Autonomous SDLC Engine

All configurable values in one place
"""

# Claude Configuration
CLAUDE_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "permission_mode": "acceptEdits",
    "timeout": 600000,
    "max_retries": 3
}

# Workflow Configuration
WORKFLOW_CONFIG = {
    "max_iterations": 20,
    "enable_parallel_execution": False,
    "enable_rollback": True
}

# Output Configuration
OUTPUT_CONFIG = {
    "default_output_dir": "./generated_project_v2",
    "preserve_history": True,
    "create_summary": True
}
```

---

## Benefits of Removing Subtle Hardcodings

### Maintainability
- Single source of truth for all configuration
- Changes in one place propagate everywhere
- Easier to understand system structure

### Extensibility
- Add new persona: Just add method to personas.py
- Modify workflow: Just update team_organization.py
- No code changes needed

### Testability
- Easy to test with different configurations
- Mock configurations for unit tests
- Validate configuration separately

### Flexibility
- Different projects can use different workflows
- Different personas for different domains
- Easy to customize

---

## Conclusion

Subtle hardcodings are insidious because they:
1. Look reasonable at first
2. Accumulate over time
3. Create maintenance burden
4. Violate DRY principle

The fix is always the same:
1. **Identify** the duplicated/hardcoded data
2. **Centralize** it in one authoritative location
3. **Reference** it from that location everywhere else

This transforms code from:
```python
# Hardcoded (BAD)
persona_methods = ['analyst', 'developer', 'qa']  # Must update here
```

To:
```python
# Dynamic (GOOD)
all_personas = personas.SDLCPersonas.get_all_personas()  # Auto-discovers
```

---

## Next Steps

1. Fix state→agents mapping
2. Fix persona list discovery
3. Create config.py
4. Test all changes
5. Update documentation
